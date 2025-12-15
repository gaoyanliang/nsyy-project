import concurrent.futures
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import redis
import requests
from apscheduler.executors.pool import ThreadPoolExecutor
from ping3 import ping
import asyncio

from gylmodules import global_config
from gylmodules.composite_appointment.ca_server import run_everyday
from gylmodules.composite_appointment.update_doc_scheduling import do_update, update_today_doc_info
from gylmodules.critical_value import cv_config
from gylmodules.critical_value.critical_value import write_cache, \
    call_third_systems_obtain_data, notiaction_alert_man, alert, query_baogao_sj
from apscheduler.schedulers.background import BackgroundScheduler

from gylmodules.critical_value.cv_manage import fetch_cv_record
from gylmodules.eye_util.eye_util import flush_token, auto_fetch_eye_data
from gylmodules.parking.parking_server import auto_freeze_car, auto_fetch_data
from gylmodules.questionnaire.sq_server import fetch_ai_result
from gylmodules.shift_change.shift_change_server import fetch_doctor_title
from gylmodules.utils.db_utils import DbUtil
from gylmodules.utils.event_loop import GlobalEventLoop
from gylmodules.workstation.mail.mail_server import cache_flags, close_idle_connections
from gylmodules.workstation.message.message_server import flush_msg_cache, batch_flush_worker

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

# 配置调度器，设置执行器，ThreadPoolExecutor 管理线程池并发
executors = {'default': ThreadPoolExecutor(10), }
gylmodule_scheduler = BackgroundScheduler(timezone="Asia/Shanghai", executors=executors)

logger = logging.getLogger(__name__)

# check_time 检查字段
# timeout_file 超时时间配置字段
# timeout_msg 超时通知信息
# ward_id 病区id 字段
# dept_id 科室id 字段
# timeout_flag 超时标识字段
timeout_d = {1: {'check_time': 'time', 'timeout_filed': 'doctor_recv_timeout',
                 'timeout_msg': '有危机值医生超时未处理，请及时通知医生',
                 'ward_id': 'ward_id', 'dept_id': '', 'timeout_flag': 'is_doctor_recv_timeout'},
             2: {'check_time': 'time', 'timeout_filed': 'nurse_recv_timeout',
                 'timeout_msg': '危机值超时未接收，请及时查看并处理',
                 'ward_id': 'ward_id', 'dept_id': 'dept_id', 'timeout_flag': 'is_nurse_recv_timeout'},
             4: {'check_time': 'nurse_recv_time', 'timeout_filed': 'nurse_send_timeout',
                 'timeout_msg': '危机值超时未发送，请及将危机值发送给医生处理',
                 'ward_id': 'ward_id', 'dept_id': '', 'timeout_flag': 'is_nurse_send_timeout'},
             5: {'check_time': 'nurse_send_time', 'timeout_filed': 'doctor_recv_timeout',
                 'timeout_msg': '危机值超时未接收，请及时查看并处理',
                 'ward_id': 'ward_id', 'dept_id': 'dept_id', 'timeout_flag': 'is_doctor_recv_timeout'},
             7: {'check_time': 'doctor_recv_time', 'timeout_filed': 'doctor_handle_timeout',
                 'timeout_msg': '医生处理危机值超时，请及时查看并处理',
                 'ward_id': 'ward_id', 'dept_id': 'dept_id', 'timeout_flag': 'is_doctor_handle_timeout'}}


def handle_timeout_cv():
    # 初始化时间和 Redis 连接
    cur_time = datetime.now()
    redis_client = redis.Redis(connection_pool=pool)

    # 批量获取并处理数据
    values = redis_client.hvals(cv_config.RUNNING_CVS_REDIS_KEY)
    timeout_records = defaultdict(list)
    first_timeout_records = defaultdict(list)
    alert_messages = []
    redis_updates = {}
    timeout_updates = []

    try:
        # 预处理配置字典
        state_processors = {
            state: timeout_d[state]
            for state in (1, 2, 4, 5, 7)
        }

        for value_bytes in values:
            value = json.loads(value_bytes)
            state = int(value.get('state'))

            # 跳过不需要处理的状态
            if state not in state_processors:
                continue

            processor = state_processors[state]
            check_time_str = value.get(processor['check_time'])
            if not check_time_str:
                continue

            check_time = datetime.strptime(check_time_str, "%Y-%m-%d %H:%M:%S")
            timeout = value.get(processor['timeout_filed'], 600)
            if (cur_time - check_time).seconds <= timeout:
                continue

            # 信息提取优化
            patient_info = {
                'name': value.get('patient_name', 'unknown'),
                'docno': value.get('req_docno', 'unknown'),
                'treat_id': value.get('patient_treat_id', '0'),
                'bed_num': value.get('patient_bed_num', '0')
            }
            msg = f"[{patient_info['name']} - " \
                  f"{patient_info['docno']} - " \
                  f"{patient_info['treat_id']} - " \
                  f"{patient_info['bed_num']}]"

            # 记录超时信息
            dept_ward_key = (value.get('dept_id'), value.get('ward_id'))
            timeout_records[dept_ward_key].append(msg)

            # 特殊科室处理
            if state in (1, 2) and str(value.get('alert_dept_id', '0')) != '144':
                alert_dept = str(value.get('alert_dept_id', '0'))
                first_timeout_records[alert_dept].append(msg)

            # 报警信息收集
            if value.get('alertman_pers_id'):
                msg = f"患者 {patient_info['name']} 的危急值，超时未处理，请通知相关人员处理"
                alert_messages.append((msg, int(value.get('alertman_pers_id')), value.get('alertman_name')))

            # 更新超时状态
            if value.get(processor['timeout_flag']) == 0:
                cv_id = value.get('cv_id')
                cv_source = value.get('cv_source')
                update_sql = f"""
                    UPDATE nsyy_gyl.cv_info SET {processor['timeout_flag']} = 1 {', state = 2' if state == 1 else ''}
                    WHERE cv_id = '{cv_id}' and cv_source = {cv_source} and state != 0
                """
                timeout_updates.append(update_sql)

                # Redis 更新缓存
                value[processor['timeout_flag']] = 1
                redis_updates[f"{cv_id}_{cv_source}"] = json.dumps(value, default=str)

        # 批量处理数据库更新
        if timeout_updates:
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            for update_sql in timeout_updates:
                db.execute(update_sql, need_commit=True)
            del db

        # 批量更新 Redis
        if redis_updates:
            with redis_client.pipeline() as pipe:
                for key, val in redis_updates.items():
                    pipe.hset(cv_config.RUNNING_CVS_REDIS_KEY, key, val)
                pipe.execute()

    except Exception as e:
        logger.error(e)

    # 使用 ThreadPoolExecutor 来并行执行
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(notiaction_alert_man, msg, pers_id, pers_name) for msg, pers_id, pers_name in alert_messages]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # 如果任务抛出异常会在此处被捕获
            except Exception as e:
                logger.error(f"Error during notification: {e}")

    # 构建报警列表
    alert_list = []
    for (dept, ward), msgs in timeout_records.items():
        alert_list.append((dept, ward,
                           f"超时危急值，请及时处理<br>[患者-主管医生-住院/门诊号-床号]<br>" +
                           "<br>".join(msgs) + "<br><br><br>点击 [确认] 跳转至危急值页面"))

    for dept, msgs in first_timeout_records.items():
        alert_list.append((dept, None,
                           f"超时危急值，请及时通知科室处理<br>[患者-主管医生-住院/门诊号-床号]<br>" +
                           "<br>".join(msgs) + "<br><br><br>点击 [确认] 跳转至危急值页面"))

    if alert_list:
        # 使用全局事件循环处理异步任务
        loop = GlobalEventLoop().get_loop()
        future = asyncio.run_coroutine_threadsafe(run_alert(alert_list), loop)
        try:
            future.result(timeout=30)  # 设置合理超时
        except TimeoutError:
            logger.warning("处理危急值超时")


async def run_alert(alert_list):
    tasks = []
    for alert_info in alert_list:
        task = asyncio.create_task(alert(alert_info[0], alert_info[1], alert_info[2]))
        tasks.append(task)
    try:
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"超时危急值通知异常 task execution: {e}")


def regular_update_dept_info():
    # dept_type 1 临床科室 2 护理单元 0 全部
    param = {"type": "his_dept", "dept_type": 0, "comp_id": 12,
             "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"}
    call_third_systems_obtain_data('cache_all_dept_info', param)


"""
每日凌晨更新最近七天的可预约数量
"""


def update_appt_capacity():
    url = "http://127.0.0.1:6092/gyl/appt/update_capacity"
    if global_config.run_in_local:
        url = "http://127.0.0.1:8080/gyl/appt/update_capacity"
    response = requests.post(url)
    if response.status_code == 200:
        logger.info("定时任务：更新可预约数量成功")
    else:
        logger.error("定时任务：更新可预约数量失败")


def re_alert_fail_ip_log():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 使用连接池和上下文管理器确保资源正确释放
    with redis.Redis(connection_pool=pool) as redis_client:
        pipe = redis_client.pipeline()
        pipe.delete(cv_config.ALERT_FAIL_IPS_REDIS_KEY)

        # 获取所有失败 IP
        all_fail_ip = db.query_all('select * from nsyy_gyl.alert_fail_log')
        if not all_fail_ip:
            return
        # 批量添加所有 IP 到 Redis 集合
        for ip in all_fail_ip:
            pipe.sadd(cv_config.ALERT_FAIL_IPS_REDIS_KEY, ip['ip'])
        pipe.execute()

        # 使用线程池并行检查 IP 可用性
        def check_ip(ip_info):
            try:
                ip_addr = ip_info['ip']
                # 先尝试 ping
                response_time = ping(ip_addr)
                if response_time is None:
                    return None

                response = requests.get(f"http://{ip_addr}:8085/echo", timeout=3)
                if response.status_code == 200:
                    return ip_addr
            except Exception:
                return None
            return None

        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(check_ip, all_fail_ip)

            # 收集需要删除的 IP
            ips_to_remove = [ip for ip in results if ip is not None]

            if ips_to_remove:
                # 批量从 Redis 中删除可用的 IP
                pipe = redis_client.pipeline()
                for ip in ips_to_remove:
                    pipe.srem(cv_config.ALERT_FAIL_IPS_REDIS_KEY, ip)
                pipe.execute()

                # 批量从数据库中删除可用的 IP
                placeholders = tuple(ips_to_remove)
                delete_sql = f"DELETE FROM nsyy_gyl.alert_fail_log WHERE ip IN {placeholders}"
                db.execute(delete_sql, need_commit=True, print_log=False)

    del db


def auto_shift_change():
    url = "http://127.0.0.1:6092/gyl/scs/shift_change"
    if global_config.run_in_local:
        url = "http://127.0.0.1:8080/gyl/scs/shift_change"
    response = requests.post(url)
    if response.status_code != 200:
        logger.error("交接班任务执行失败", response.text)


def auto_tingchechang():
    url = "http://127.0.0.1:6092/gyl/parking/auto_op_vip"
    if global_config.run_in_local:
        url = "http://127.0.0.1:8080/gyl/parking/auto_op_vip"
    response = requests.post(url)


def schedule_task():
    # ====================== 危机值系统定时任务 ======================
    logger.info("=============== 注册定时任务 =====================")
    # 定时判断危机值是否超时
    logger.info('1. 危急值模块定时任务')
    if global_config.schedule_task['cv_timeout']:
        logger.info("    1.1 危机值超时管理 ")
        gylmodule_scheduler.add_job(handle_timeout_cv, trigger='interval', seconds=40, coalesce=True, id='cv_timeout')
        logger.info("    1.2 查询危机值报告时间 ")
        gylmodule_scheduler.add_job(query_baogao_sj, trigger='interval', seconds=5 * 60 * 60, id='query_baogao_sj')
        logger.info("    1.3 ip 地址是否可用校验")
        gylmodule_scheduler.add_job(re_alert_fail_ip_log, 'cron', hour=2, minute=20, id='re_alert_fail_ip_log')
        logger.info("    1.4 每日同步危急值处理报告")
        gylmodule_scheduler.add_job(fetch_cv_record, 'cron', hour=2, minute=40, id='fetch_cv_record')
        logger.info("    1.5 危机值部门信息更新 ")
        gylmodule_scheduler.add_job(regular_update_dept_info, trigger='interval', seconds=6 * 60 * 60,
                                    id='cv_dept_update')

    # 项目启动时，执行一次，初始化数据。 之后每天凌晨执行
    logger.info("2. 综合预约模块定时任务 ")
    if global_config.schedule_task['appt_daily']:
        run_time = datetime.now() + timedelta(seconds=15)
        gylmodule_scheduler.add_job(run_everyday, trigger='date', run_date=run_time)
        gylmodule_scheduler.add_job(update_today_doc_info, 'cron', hour=1, minute=1, id='update_today_doc_info')
        gylmodule_scheduler.add_job(update_appt_capacity, 'cron', hour=1, minute=5, id='update_appt_capacity')
        gylmodule_scheduler.add_job(run_everyday, 'cron', hour=1, minute=10, id='appt_daily')
        gylmodule_scheduler.add_job(do_update, trigger='interval', seconds=5*60, coalesce=True, id='do_update_doc')

    logger.info("3. 消息模块定时任务 ")
    gylmodule_scheduler.add_job(flush_msg_cache, trigger='date', run_date=datetime.now())
    gylmodule_scheduler.add_job(batch_flush_worker, trigger='interval', seconds=10 * 60)
    gylmodule_scheduler.add_job(cache_flags, trigger='interval', seconds=10 * 60)
    gylmodule_scheduler.add_job(close_idle_connections, trigger='interval', seconds=9 * 60)


    # logger.info("4. 高压氧模块定时任务 ")
    # gylmodule_scheduler.add_job(hbot_run_everyday, 'cron', hour=4, minute=30, id='hbot_run_everyday')

    logger.info("6. 问卷调查模块定时任务 ")
    gylmodule_scheduler.add_job(fetch_ai_result, trigger='interval', seconds=20 * 60, id='fetch_ai_result')

    logger.info("7. 交接班模块定时任务 ")
    # 改用 cron 执行
    # gylmodule_scheduler.add_job(auto_shift_change, trigger='cron', minute='0,30')
    # 定时同步医生职称
    gylmodule_scheduler.add_job(fetch_doctor_title, 'cron', hour='0,12,20', minute=15)

    logger.info("8. 停车场模块定时任务 ")
    gylmodule_scheduler.add_job(auto_tingchechang, trigger='cron', minute='*/4')
    # 尝试多次，防止服务器临时故障
    gylmodule_scheduler.add_job(auto_fetch_data, 'cron', hour='3,16', minute=10)
    gylmodule_scheduler.add_job(auto_fetch_data, 'cron', hour='3,16', minute=34)
    gylmodule_scheduler.add_job(auto_fetch_data, 'cron', hour='4,17', minute=14)
    gylmodule_scheduler.add_job(auto_freeze_car, 'cron', hour=3, minute=50)

    logger.info("9. 眼科医院定时任务 ")
    # 定时刷新token
    gylmodule_scheduler.add_job(flush_token, trigger='interval', seconds=20 * 60)
    gylmodule_scheduler.add_job(auto_fetch_eye_data, trigger='interval', seconds=10 * 60)

    # ======================  Start ======================
    gylmodule_scheduler.start()

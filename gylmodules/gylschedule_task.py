import json
from datetime import datetime, timedelta
import redis
import requests

from gylmodules import global_config
from gylmodules.composite_appointment.ca_server import run_everyday
from gylmodules.critical_value import cv_config
from gylmodules.critical_value.critical_value import write_cache, \
    call_third_systems_obtain_data, async_alert, cache_single_cv, invalid_history_cv, notiaction_alert_man
from apscheduler.schedulers.background import BackgroundScheduler

from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)
gylmodule_scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

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
    cur_time = datetime.now()
    redis_client = redis.Redis(connection_pool=pool)
    values = redis_client.hvals(cv_config.RUNNING_CVS_REDIS_KEY)

    # 存储所有超时记录
    timeout_record = {}
    for value in values:
        value = json.loads(value)
        if value.get('state') not in (1, 2, 4, 5, 7):
            continue
        needd = timeout_d[value['state']]
        check_time = value[needd['check_time']]
        check_time = datetime.strptime(check_time, "%Y-%m-%d %H:%M:%S")
        if (cur_time - check_time).seconds > value.get(needd['timeout_filed'], 600):
            msg = '[{} - {} - {} - {}]'.format(value.get('patient_name', 'unknown'), value.get('req_docno', 'unknown'),
                                               value.get('patient_treat_id', '0'), value.get('patient_bed_num', '0'))

            timeout_key = (value.get('dept_id'), value.get('ward_id'))
            if timeout_key in timeout_record:
                timeout_record[timeout_key].append(msg)
            else:
                timeout_record[timeout_key] = [msg]

            # socket   通知上报人
            if value.get('alertman_pers_id'):
                msg = '患者 {} 的危急值，超时未处理，请通知相关人员处理'.format(value.get('patient_name'))
                notiaction_alert_man(msg, int(value['alertman_pers_id']))

            # 更新超时状态
            if value[needd['timeout_flag']] == 0:
                # 修改数据库状态
                db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                            global_config.DB_DATABASE_GYL)

                # 新建状态超时后，默认通知护士
                update_state_sql = ''
                if int(value.get('state')) == 1:
                    update_state_sql = ', state = 2'
                    value['state'] = cv_config.NOTIFICATION_NURSE_STATE

                update_field = needd['timeout_flag']
                cv_id = value.get('cv_id')
                cv_source = value.get('cv_source')
                update_sql = f'UPDATE nsyy_gyl.cv_info SET {update_field} = 1 {update_state_sql} ' \
                             f'WHERE cv_id = \'{cv_id}\' and cv_source = {cv_source} and state != 0'
                db.execute(update_sql, need_commit=True)
                del db

                # 更新 redis 状态
                value[needd['timeout_flag']] = 1
                key = str(cv_id) + '_' + str(cv_source)
                write_cache(key, value)
    if timeout_record:
        for ids, msgs in timeout_record.items():
            alertmsg = f'超时危急值，请及时处理 <br> [患者-主管医生-住院/门诊号-床号] <br> ' + ' <br> '.join(msgs)
            async_alert(ids[0], ids[1], alertmsg)


def regular_update_dept_info():
    # dept_type 1 临床科室 2 护理单元 0 全部
    param = {
        "type": "his_dept",
        "dept_type": 0,
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }
    call_third_systems_obtain_data('cache_all_dept_info', param)


"""
每日凌晨更新最近七天的可预约数量
"""


def update_appt_capacity():
    url = "http://127.0.0.1:6092/gyl/appt/update_capacity"
    # url = "http://127.0.0.1:8080/gyl/appt/update_capacity"
    response = requests.post(url)
    if response.status_code == 200:
        print("Successfully updated appointment capacity.")
    else:
        print("Failed to update appointment capacity. Status code:", response.status_code)


"""
每小时打印一次任务状态
"""


def task_state():
    print('========   gyl schedule task state   ========')
    print('cur time = ', datetime.now())
    print('schedule is_running = ', gylmodule_scheduler.running)
    print('schedule state = ', gylmodule_scheduler.state)
    print('schedule jobs:  len = ', len(gylmodule_scheduler.get_jobs()))
    jobs = gylmodule_scheduler.get_jobs()
    for job in jobs:
        job_info = {
            'id': job.id,
            'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
        }
        print(job_info)
    print('======== gyl schedule task state end ========')


def schedule_task():
    # ====================== 危机值系统定时任务 ======================
    # 定时判断危机值是否超时
    if global_config.schedule_task['cv_timeout']:
        print("危机值超时管理 定时任务启动 ", datetime.now())
        gylmodule_scheduler.add_job(handle_timeout_cv, trigger='interval', seconds=100, max_instances=20,
                                    id='cv_timeout')

        print("缓存单次上报危机值信息 定时任务启动 ", datetime.now())
        gylmodule_scheduler.add_job(cache_single_cv, trigger='date', run_date=datetime.now())
        gylmodule_scheduler.add_job(cache_single_cv, 'cron', hour=2, minute=10, id='cache_single_cv')

        print("作废超过一天未处理的危机值 定时任务启动 ", datetime.now())
        gylmodule_scheduler.add_job(invalid_history_cv, 'cron', hour=2, minute=20, id='invalid_history_cv')

    # 定时更新所有部门信息
    if global_config.schedule_task['cv_dept_update']:
        print("危机值部门信息更新 定时任务 ", datetime.now())
        one_hour = 60 * 60
        gylmodule_scheduler.add_job(regular_update_dept_info, trigger='interval', seconds=one_hour, max_instances=10,
                                    id='cv_dept_update')

    # ======================  综合预约定时任务  ======================
    # 项目启动时，执行一次，初始化数据。 之后每天凌晨执行
    if global_config.schedule_task['appt_daily']:
        run_time = datetime.now() + timedelta(seconds=20)
        gylmodule_scheduler.add_job(run_everyday, trigger='date', run_date=run_time)
        gylmodule_scheduler.add_job(run_everyday, 'cron', hour=1, minute=20, id='appt_daily')
        gylmodule_scheduler.add_job(update_appt_capacity, 'cron', hour=1, minute=10, id='update_appt_capacity')

    six_hour = 6 * 60 * 60
    # one_min = 60
    gylmodule_scheduler.add_job(task_state, trigger='interval', seconds=six_hour, max_instances=10,
                                id='sched_state')

    # ======================  Start ======================
    gylmodule_scheduler.start()

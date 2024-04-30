import json
from datetime import datetime, timedelta
import redis

from gylmodules import global_config
from gylmodules.composite_appointment.composite_appointment import load_appt_data_into_cache
from gylmodules.critical_value import cv_config
from gylmodules.critical_value.critical_value import write_cache, \
    call_third_systems_obtain_data, async_alert
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
    for value in values:
        value = json.loads(value)
        if value.get('state') not in (1, 2, 4, 5, 7):
            return
        needd = timeout_d[value['state']]
        check_time = value[needd['check_time']]
        check_time = datetime.strptime(check_time, "%Y-%m-%d %H:%M:%S")
        if (cur_time-check_time).seconds > value.get(needd['timeout_filed'], 600):
            if needd['ward_id'] != '':
                async_alert(1, value[needd['ward_id']], needd['timeout_msg'])
            if needd['dept_id'] != '':
                async_alert(2, value[needd['dept_id']], needd['timeout_msg'])

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
                db.execute(update_sql, (), need_commit=True)

                # 更新 redis 状态
                value[needd['timeout_flag']] = 1
                key = str(cv_id) + '_' + str(cv_source)
                write_cache(key, value)


def regular_update_dept_info():
    # dept_type 1 临床科室 2 护理单元 0 全部
    param = {
        "type": "his_dept",
        "dept_type": 0,
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }
    call_third_systems_obtain_data('cache_all_dept_info', param)


def schedule_task():
    # ====================== 危机值系统定时任务 ======================
    # 定时判断危机值是否超时
    if global_config.schedule_task['cv_timeout']:
        gylmodule_scheduler.add_job(handle_timeout_cv, trigger='interval', seconds=60, max_instances=10)
    # 定时更新所有部门信息
    if global_config.schedule_task['cv_dept_update']:
        one_hour = 60 * 60
        gylmodule_scheduler.add_job(regular_update_dept_info, trigger='interval', seconds=one_hour, max_instances=10)

    # ======================  综合预约定时任务  ======================
    # 添加每天凌晨执行
    if global_config.schedule_task['appt_daily']:
        gylmodule_scheduler.add_job(load_appt_data_into_cache, 'cron', hour=23, minute=10)

    # ======================  Start ======================
    gylmodule_scheduler.start()


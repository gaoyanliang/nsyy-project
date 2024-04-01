from datetime import datetime, timedelta
import redis
from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.critical_value.critical_value import push_notice, read_cv_from_system, cache_all_dept_info
from gylmodules.utils.db_utils import DbUtil
from apscheduler.schedulers.background import BackgroundScheduler


pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)
cv_scheduler = BackgroundScheduler()

tt_wait_nurse_ack_first_run = True
tt_wait_doctor_ack_first_run = True
tt_wait_doctor_handle_first_run = True


"""
定时从系统中抓取危机值
"""


def pull_cv_from_system():
    read_cv_from_system()


"""
定时更新所有部门信息
"""


def cache_dept():
    cache_all_dept_info()


# 检查时间字断，超时时间，超时打印内容，有值：护理单元发，有值：给科室发
timeout_d = {2: ['time', 'nurse_timeout','护理接收超时，请及时处理', 'ward_id', ''],
             5: ['nurse_recv_time', 'doctor_timeout','医生接收超时，请及时处理', 'ward_id', 'dept_id'],
             7: ['doctor_recv_time', 'doctor_handle_timeout','医生处理超时，请及时处理', 'ward_id', 'dept_id'],
             9: ['handle_time', 'total_timeout','危机值处理超时', 'ward_id', 'dept_id']}


def handle_timeout_cv():
    timer = datetime.now()
    for key, value in cv_config.all_running_cv.items():
        if value.get('state') not in (2,5,7,9):
            return
        check_time = value[timeout_d[value['state']][0]]
        if (timer-check_time).seconds > value.get(timeout_d[value['state']][1], 600):
            if timeout_d[value['state']][3] != '':
                push(1, value[timeout_d[value['state']][3]], timeout_d[value['state']][2])
            if timeout_d[value['state']][4] != '':
                push(2, value[timeout_d[value['state']][4]], timeout_d[value['state']][2])


# 弹框通知护理
def push(type, id, msg):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 弹框提升护理，及时接收
    key = 'site_ward_id = {}'.format(id) if type == 1 else 'site_dept_id = {}'.format(id)
    query_sql = f'select * from nsyy_gyl.cv_site where {key} '
    sites = db.query_all(query_sql)
    if sites:
        for site in sites:
            push_notice('http://{}:8085/opera_wiki'.format(site.get('site_ip')), msg)


def schedule_task():
    # 危机值系统定时任务
    one_hour = 60 * 60
    cv_scheduler.add_job(handle_timeout_cv, trigger='interval', seconds=10)
    cv_scheduler.add_job(pull_cv_from_system, trigger='interval', seconds=10)
    cv_scheduler.add_job(cache_dept, trigger='interval', seconds=one_hour)
    cv_scheduler.add_job(cache_dept, 'date', run_date=datetime.now() + timedelta(seconds=2))

    # Start the scheduler
    return cv_scheduler


import redis
import json
import threading
import requests

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.utils.common_utils import run_in_local
from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)

scheduler = BackgroundScheduler()
cv_id_lock = threading.Lock()


"""
调用第三方系统获取数据
"""


def call_third_systems_obtain_data(type: str, param: dict):
    data = []
    if run_in_local():
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'data_feedback':
            # 数据回传
            from tools import orcl_db_update
            orcl_db_update(param)
        elif type == 'get_dept_info_by_emp_num':
            # 根据员工号，查询科室信息
            from tools import his_dept_pers
            data = his_dept_pers(param)
        elif type == 'cache_all_dept_info':
            from tools import his_dept
            data = his_dept(param)

    if type == 'get_dept_info_by_emp_num':
        # 使用列表推导式提取 "缺省" 值为 1 的元素
        if data and len(data) > 0:
            result = [item for item in data if item.get("缺省") == 1]
            return result[0].get('HIS_DEPT_ID'), result[0].get('DEPT_NAME'), result[0].get('PERS_NAME')
        else:
            raise Exception('根据员工号抓取部门信息失败 ' + str(param))
    elif type == 'cache_all_dept_info':
        # 缓存所有科室信息
        redis_client = redis.Redis(connection_pool=pool)
        if len(data) > 0:
            for d in data:
                redis_client.hset(cv_config.DEPT_INFO_REDIS_KEY, d.get('his_dept_id'), d.get('dept_name'))


"""
操作缓存
"""


def write_cache(key, value):
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hset(cv_config.RUNNING_CVS_REDIS_KEY, key, json.dumps(value, default=str))


def read_cache(key):
    redis_client = redis.Redis(connection_pool=pool)
    value = redis_client.hget(cv_config.RUNNING_CVS_REDIS_KEY, key)
    return json.loads(value)


def delete_cache(key):
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hdel(cv_config.RUNNING_CVS_REDIS_KEY, key)


"""
缓存所有站点信息
"""


def cache_all_site_and_timeout():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)

    # 缓存所有站点信息
    query_sql = 'select * from nsyy_gyl.cv_site'
    sites = db.query_all(query_sql)
    for site in sites:
        if site.get('site_dept_id'):
            key = cv_config.CV_SITES_REDIS_KEY[2] + str(site.get('site_dept_id'))
            redis_client.sadd(key, site.get('site_ip'))
        if site.get('site_ward_id'):
            key = cv_config.CV_SITES_REDIS_KEY[1] + str(site.get('site_ward_id'))
            redis_client.sadd(key, site.get('site_ip'))

    # 将超时时间配置加载至 redis 缓存
    query_sql = 'select * from nsyy_gyl.cv_timeout where type = \'cv\' '
    timeout_sets = db.query_one(query_sql)
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_recv'], timeout_sets.get('nurse_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_send'], timeout_sets.get('nurse_send_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_recv'], timeout_sets.get('doctor_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_handle'], timeout_sets.get('doctor_handle_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['total'], timeout_sets.get('total_timeout'))

    del db


"""
启动时加载数据
1. 超时配置
2. 所有部门信息
3. 所有未完成的危机值
4. 缓存所有站点信息 
"""


def pull_running_cv():
    # 清空危机值相关的缓存, 重新加载数据
    redis_client = redis.Redis(connection_pool=pool)
    # 删除上一天的所有预约
    keys = redis_client.keys('CV_*')
    for key in keys:
        redis_client.delete(key)

    # 缓存所有部门信息
    # dept_type 1 临床科室 2 护理单元 0 全部
    param = {
        "type": "his_dept",
        "dept_type": 0,
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }
    call_third_systems_obtain_data('cache_all_dept_info', param)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 加载所有处理中的危机值到内存
    states = (cv_config.INVALID_STATE, cv_config.DOCTOR_HANDLE_STATE)
    query_sql = f'select * from nsyy_gyl.cv_info where state not in {states} '
    cvs = db.query_all(query_sql)
    for cv in cvs:
        key = cv.get('cv_id') + '_' + str(cv.get('cv_source'))
        write_cache(key, cv)
    del db

    # 子线程执行： 缓存所有站点信息 & 超时时间配置
    thread_b = threading.Thread(target=cache_all_site_and_timeout)
    thread_b.start()


# 启动时先运行该方法，加载数据
pull_running_cv()


"""
查询所有运行中的危机值id列表
"""


def get_running_cvs():
    redis_client = redis.Redis(connection_pool=pool)
    processing_cvs = redis_client.hkeys(cv_config.RUNNING_CVS_REDIS_KEY) or []
    running_ids = {}
    for item in processing_cvs:
        d = item.split('_')
        cv_id = d[0]
        cv_source = d[1]
        if cv_source not in running_ids:
            running_ids[cv_source] = []
        running_ids[cv_source].append(cv_id)

    query_sql = """
            select a.*, 2 cv_source from inter_lab_resultalert a 
            where (idrs_2 alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss')) and VALIDFLAG=1 and HISCHECKDT1 is NULL
            union 
            select b.*, 3 cv_source from NS_EXT.PACS危急值上报表 b 
            where (idrs_3 alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss')) and VALIDFLAG=1 and HISCHECKDT1 is NULL
            """

    systeml = [2, 3]

    return running_ids, query_sql, systeml


def create_cv(cvd):
    # cvd {cv_id_cv_source: cv}
    new_cvs = [key for key in cvd.keys()]
    redis_client = redis.Redis(connection_pool=pool)
    running_cvs = redis_client.hkeys(cv_config.RUNNING_CVS_REDIS_KEY)

    del_idl = list(set(running_cvs) - set(new_cvs))
    new_idl = list(set(new_cvs) - set(running_cvs))

    # 作废危机值
    cv_idd = {}
    for key in del_idl:
        cv_id, cv_source = key.split('_')
        cv_source = int(cv_source)
        if cv_source not in cv_idd:
            cv_idd[cv_source] = []
        cv_idd[cv_source].append(cv_id)
    for cv_source, cv_ids in cv_idd.items():
        invalid_crisis_value(cv_ids, cv_source)

    # 新增危机值
    for key in new_idl:
        cv_source = key.split('_')[1]
        cv_data = cvd[key]
        create_cv_by_system(cv_data, int(cv_source))


"""
作废危机值
"""


def invalid_crisis_value(cv_ids, cv_source):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 更新危机值状态未作废
    ids = ','.join(cv_ids)
    new_state = cv_config.INVALID_STATE
    states = (cv_config.INVALID_STATE, cv_config.DOCTOR_HANDLE_STATE)
    update_sql = f'UPDATE nsyy_gyl.cv_info SET state = {new_state}' \
                 f' WHERE cv_id in ({ids}) and cv_source = {cv_source} and state not in {states}'
    db.execute(update_sql, (), need_commit=True)

    # 从内存中移除
    for cv_id in cv_ids:
        key = cv_id + '_' + str(cv_source)
        delete_cache(key)

    del db


"""
系统创建危机值
"""


def create_cv_by_system(json_data, cv_source):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    cvd = {'dept_id': json_data.get('REQ_DEPTNO')}
    if cvd['dept_id'] and not cvd['dept_id'].isdigit():
        print('当前危机值病人科室不是数字，跳过。 ' + str(json_data))
        return

    # 解析危机值上报信息
    cvd['cv_id'] = json_data.get('RESULTALERTID')
    cvd['cv_source'] = cv_source
    cvd['alertman'] = json_data.get('ALERTMAN')
    cvd['alertdt'] = json_data.get('ALERTDT')
    cvd['time'] = str(datetime.now())[:19]
    cvd['state'] = cv_config.CREATED_STATE
    # 根据员工号查询部门信息
    param = {
        "type": "his_dept_pers",
        "pers_no": cvd['alertman'],
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }
    cvd['alert_dept_id'], cvd['alert_dept_name'], cvd['alertman_name'] = \
        call_third_systems_obtain_data('get_dept_info_by_emp_num', param)

    # 解析危机值病人信息
    cvd['patient_type'] = json_data.get('PAT_TYPECODE')
    cvd['patient_treat_id'] = json_data.get('PAT_NO')
    cvd['patient_name'] = json_data.get('PAT_NAME')
    cvd['patient_gender'] = json_data.get('PAT_SEX')
    cvd['patient_age'] = json_data.get('PAT_AGESTR')
    cvd['patient_bed_num'] = json_data.get('REQ_BEDNO')
    cvd['req_docno'] = json_data.get('REQ_DOCNO')
    cvd['ward_id'] = json_data.get('REQ_WARDNO')
    cvd['ward_name'] = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, cvd['ward_id']) or ''
    cvd['dept_name'] = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, cvd['dept_id']) or ''

    # 解析危机值内容信息
    cvd['cv_name'] = json_data.get('RPT_ITEMNAME')
    cvd['cv_result'] = json_data.get('RESULT_STR')
    if int(cv_source) == cv_config.CV_SOURCE_INSPECTION_SYSTEM:
        cvd['cv_flag'] = json_data.get('RESULT_FLAG')
        cvd['cv_unit'] = json_data.get('RESULT_UNIT')
        # 结果参考值 H偏高 HH偏高报警 L偏低 LL偏低报警 P阳性 E错误
        cvd['cv_ref'] = json_data.get('RESULT_REF')
        # 复查标志 0无需复查 1需要复查 2已经复查
        cvd['redo_flag'] = json_data.get('REDO_FLAG')
        cvd['alertrules'] = json_data.get('ALERTRULES')

    # 超时时间配置
    redis_client = redis.Redis(connection_pool=pool)
    cvd['nurse_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_recv']) or 300
    cvd['nurse_send_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_send']) or 120
    cvd['doctor_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_recv']) or 300
    cvd['doctor_handle_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_handle']) or 300
    cvd['total_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['total']) or 600

    # 插入危机值
    fileds = ','.join(cvd.keys())
    args = str(tuple(cvd.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.cv_info ({fileds}) " \
                 f"VALUES {args}"
    last_rowid = db.execute(insert_sql, (), need_commit=True)
    if last_rowid == -1:
        raise Exception("系统危机值入库失败! " + str(args))

    # 发送危机值 直接通知医生和护士
    pat_name = cvd['patient_name']
    async_alert(1, cvd['ward_id'], f'病人 [{pat_name}] 出现危机值, 请及时查看并处理')
    async_alert(2, cvd['dept_id'], f'病人 [{pat_name}] 出现危机值, 请及时查看并处理')

    # 将危机值放入 redis cache
    query_sql = 'select * from nsyy_gyl.cv_info where id = {} '.format(last_rowid)
    record = db.query_one(query_sql)
    key = cvd['cv_id'] + '_' + str(cv_source)
    write_cache(key, record)

    del db


"""
查询危机值
"""


def get_cv_list(dept_id, ward_id, json_data):
    # type =1 未处理， type =2 已处理
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    states = (cv_config.DOCTOR_HANDLE_STATE, cv_config.INVALID_STATE)
    state_sql = ' state not in {} '.format(states)
    if int(json_data.get('type')) == 2:
        state_sql = ' state in {} '.format(states)

    start_time = json_data.get("start_time")
    end_time = json_data.get("end_time")
    time_sql = ''
    if start_time and end_time:
        time_sql = f' and (time BETWEEN \'{start_time}\' AND \'{end_time}\') '

    if not dept_id:
        condition_sql = f' and ward_id = {ward_id} '
    elif not ward_id:
        condition_sql = f' and dept_id = {dept_id} '
    else:
        condition_sql = f' and (dept_id = {dept_id} or ward_id = {ward_id}) '

    query_sql = f'select * from nsyy_gyl.cv_info where {state_sql} {time_sql} {condition_sql} '
    cv_list = db.query_all(query_sql)
    del db

    page_number = json_data.get("page_number")
    page_size = json_data.get("page_size")
    if not page_number:
        page_number = 1
        page_size = 10
    # 计算要查询的起始索引和结束索引
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    total = len(cv_list)
    # 使用切片操作从数据集中获取特定范围的数据
    cv_list = cv_list[start_index:end_index]

    return cv_list, total


"""
查询处理中的危机值并通知
"""


def query_process_cv_and_notice(dept_id, ward_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if not dept_id:
        condition_sql = f' and ward_id = {ward_id}'
    elif not ward_id:
        condition_sql = f' and dept_id = {dept_id}'
    else:
        condition_sql = f' and (dept_id = {dept_id} or ward_id = {ward_id})'

    states = (cv_config.INVALID_STATE, cv_config.DOCTOR_HANDLE_STATE)
    query_sql = f'select * from nsyy_gyl.cv_info where state not in {states} {condition_sql} '
    running = db.query_all(query_sql)
    if running:
        patient_names = [item['patient_name'] for item in running]
        patient_names = list(set(patient_names))
        names = ','.join(patient_names)
        if ward_id:
            async_alert(1, ward_id, f" {names} 存在未处理完的危机值，请及时处理")
        if dept_id:
            async_alert(2, dept_id, f" {names} 存在未处理完的危机值，请及时处理")

    del db


"""
推送弹框通知 type = 1 通知护士， type = 2 通知医生
"""


def async_alert(type, id, msg):
    def alert(type, id, msg):
        key = cv_config.CV_SITES_REDIS_KEY[type] + str(id)
        payload = {'type': 'popup', 'wiki_info': msg}
        redis_client = redis.Redis(connection_pool=pool)
        sites = redis_client.smembers(key)
        if sites:
            for ip in sites:
                url = f'http://{ip}:8085/opera_wiki'
                try:
                    requests.post(url, json=payload)
                except Exception as e:
                    return
    thread_b = threading.Thread(target=alert, args=(type, id, msg))
    thread_b.start()


"""
向医生推送危机值
"""


def push(json_data):
    """
    推送危机值
    push_type = 1 护理 -> 医生
    push_type = 2 门诊医生 -> 急诊
    """
    cv_id = json_data.get('cv_id')
    cv_source = json_data.get('cv_source')
    dept_id = json_data.get('dept_id')
    push_type = json_data.get('push_type')
    patient_name = json_data.get('patient_name')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")

    # 护理（病区护士站 门诊 急诊） -> 医生
    if push_type == 1:
        # 更新危机值状态为 【通知医生】
        update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, nurse_send_time = %s ' \
                     'WHERE cv_id = %s and cv_source = %s and state != 0'
        args = (cv_config.NOTIFICATION_DOCTOR_STATE, timer, cv_id, cv_source)
        db.execute(update_sql, args, need_commit=True)

        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        value['state'] = cv_config.NOTIFICATION_DOCTOR_STATE
        value['nurse_send_time'] = timer
        write_cache(key, value)
        # 弹框提醒医生
        async_alert(2, dept_id, f"病人 {patient_name} 出现危机值, 请及时查看并处理")

    del db


"""
确认接收危机值
"""


def confirm_receipt_cv(json_data):
    """
    确认接收危机值
    confirm_type = 0 护理确认接收
    confirm_type = 1 医生确认接收
    """
    cv_id = json_data.get("cv_id")
    cv_source = json_data.get("cv_source")
    confirmer_name = json_data.get("confirmer_name")
    confirmer_id = json_data.get("confirmer_id")
    confirm_info = json_data.get('confirm_info')
    confirm_type = json_data.get("confirm_type")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")
    if confirm_type == 0:
        # 更新危机值状态为 【护理确认接收】
        update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, nurse_recv_id = %s, nurse_recv_name = %s,' \
                     'nurse_recv_time = %s, nurse_recv_info = %s  WHERE cv_id = %s and cv_source = %s and state != 0'
        args = (cv_config.NURSE_RECV_STATE, confirmer_id, confirmer_name, timer, confirm_info, cv_id, cv_source)
        db.execute(update_sql, args, need_commit=True)

        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        value['state'] = cv_config.NURSE_RECV_STATE
        value['nurse_recv_id'] = confirmer_id
        value['nurse_recv_name'] = confirmer_name
        value['nurse_recv_time'] = timer
        value['nurse_recv_info'] = confirm_info
        write_cache(key, value)

        # 护士接收之后，进行数据回传
        data_feedback(cv_id, confirmer_id, timer, confirm_info, 1)

    elif confirm_type == 1:

        # 更新危机值状态为 【医生确认接收】
        update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, doctor_recv_id = %s, ' \
                     'doctor_recv_name = %s, doctor_recv_time = %s WHERE cv_id = %s and cv_source = %s and state != 0'
        args = (cv_config.DOCTOR_RECV_STATE, confirmer_id, confirmer_name, timer, cv_id, cv_source)
        db.execute(update_sql, args, need_commit=True)

        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        value['state'] = cv_config.DOCTOR_RECV_STATE
        value['doctor_recv_id'] = confirmer_id
        value['doctor_recv_name'] = confirmer_name
        value['doctor_recv_time'] = timer
        write_cache(key, value)

    del db


"""
书写护理记录
"""


def nursing_records(json_data):
    """
    护理记录
    """
    cv_id = json_data.get("cv_id")
    cv_source = json_data.get("cv_source")
    record = json_data.get("record")
    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = 'UPDATE nsyy_gyl.cv_info SET nursing_record = %s, nursing_record_time = %s ' \
                 'WHERE cv_id = %s and cv_source = %s and state != 0'
    args = (record, timer, cv_id, cv_source)
    db.execute(update_sql, args, need_commit=True)

    # 同步更新常量中的状态
    key = cv_id + '_' + str(cv_source)
    value = read_cache(key)
    value['nursing_record'] = record
    value['nursing_record_time'] = timer
    write_cache(key, value)

    del db


"""
医生处理危机值
"""


def doctor_handle_cv(json_data):
    cv_id = json_data.get("cv_id")
    cv_source = json_data.get("cv_source")
    handler_id = json_data.get("handler_id")
    handler_name = json_data.get("handler_name")
    analysis = json_data.get("analysis")
    method = json_data.get("method")
    create_time = json_data.get('create_time')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 从缓存中获取总流程的超时时间，如果不存在，默认 10 分钟
    redis_client = redis.Redis(connection_pool=pool)
    timeout = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['total'])
    if not timeout:
        timeout = 10 * 60

    cur_time = datetime.now()
    create_time = datetime.strptime(create_time, "%a, %d %b %Y %H:%M:%S GMT")
    update_total_timeout_sql = ''
    if (cur_time - create_time).seconds > int(timeout):
        update_total_timeout_sql = 'is_timeout = 1 , '

    timer = cur_time.strftime("%Y-%m-%d %H:%M:%S")
    # 更新危机值状态为 【医生处理】
    update_sql = f'UPDATE nsyy_gyl.cv_info SET {update_total_timeout_sql} state = %s, analysis = %s, method = %s, ' \
                 'handle_time = %s, handle_doctor_name = %s, handle_doctor_id = %s ' \
                 'WHERE cv_id = %s and cv_source = %s and state != 0'
    args = (cv_config.DOCTOR_HANDLE_STATE, analysis, method, timer, handler_name, handler_id, cv_id, cv_source)
    db.execute(update_sql, args, need_commit=True)

    # 同步更新常量中的状态
    key = cv_id + '_' + str(cv_source)
    delete_cache(key)

    # 医生处理之后，进行数据回传
    data_feedback(cv_id, handler_id, timer, method, 2)

    del db


"""
统计报表
"""


def report_form(json_data):
    start_time = json_data.get("start_time")
    end_time = json_data.get("end_time")

    page_number = json_data.get("page_number")
    page_size = json_data.get("page_size")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    time_sql = ''
    if start_time and end_time:
        time_sql = f'and (time BETWEEN \'{start_time}\' AND \'{end_time}\' )'

    state_sql = 'state != {}'.format(cv_config.DOCTOR_HANDLE_STATE)
    if int(json_data.get('type')) == 2:
        state_sql = 'state = {}'.format(cv_config.DOCTOR_HANDLE_STATE)
    query_sql = f'select * from nsyy_gyl.cv_info where {state_sql} {time_sql}'
    cv_list = db.query_all(query_sql)
    total = len(cv_list)

    # 计算要查询的起始索引和结束索引
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size
    cv_list = cv_list[start_index:end_index]

    del db

    return cv_list, total


"""
病历模版
"""


def medical_record_template(json_data):
    cv_id = json_data.get('cv_id')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_info where cv_id = \'{}\' '.format(cv_id)
    cv = db.query_one(query_sql)

    templete = []
    templete.append('危机值报告处理记录')
    if cv:
        time = cv.get('time').strftime("%Y-%m-%d %H:%M:%S")
        templete.append("于 " + time + "接收到 " + str(cv.get('alert_dept_name')) +
                        " 推送的危机值, 检查项目: " + str(cv.get('cv_name')) +
                        " 危机值: " + str(cv.get('cv_result')) + " " + str(cv.get('cv_unit')))
        string = "原因分析： "
        if cv.get('analysis'):
            string = string + cv.get("analysis")
        templete.append(string)
        string = "处理办法： "
        if cv.get('method'):
            string = string + cv.get("method")
        templete.append(string)
        templete.append("医师签名：")

    del db

    return templete


"""
数据回传
"""


def data_feedback(cv_id, confirmer_id, timer, confirm_info, type: int):
    datal = []
    updatel = []
    datel = []
    intl = []
    if type == 1:
        # 护士确认
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN": str(confirmer_id), "HISCHECKDT": timer,
                  "HISCHECKINFO": confirm_info}]
        updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO"]
        datel = ["HISCHECKDT"]
    else:
        # 医生确认
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN1": str(confirmer_id), "HISCHECKDT1": timer,
                  "HISCHECKINFO1": confirm_info}]
        updatel = ["HISCHECKMAN1", "HISCHECKDT1", "HISCHECKINFO1"]
        datel = ["HISCHECKDT1"]

    param = {
        "type": "orcl_db_update",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "table_name": "inter_lab_resultalert",
        "datal": datal,
        "updatel": updatel,
        "datel": datel,
        "intl": intl,
        "keyl": ["RESULTALERTID"]
    }

    call_third_systems_obtain_data('data_feedback', param)


"""
设置危机值系统超时时间
"""


def setting_timeout(json_data):
    timeoutd = {'nurse_recv_timeout': int(json_data.get('nurse_recv_timeout')),
                'nurse_send_timeout': int(json_data.get('nurse_send_timeout')),
                'doctor_recv_timeout': int(json_data.get('doctor_recv_timeout')),
                'doctor_handle_timeout': int(json_data.get('doctor_handle_timeout')),
                'total_timeout': int(json_data.get('total_timeout')),
                'type': 'cv'
                }

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    keys = ','.join(timeoutd.keys())
    values = tuple(timeoutd.values())
    # 将键和值按指定格式拼接成字符串
    key_string = ', '.join([f"{key} = {repr(value)}" for key, value in timeoutd.items()])

    # 存在则更新 不存在则插入
    insert_sql = f'INSERT INTO nsyy_gyl.cv_timeout ({keys}) VALUE {str(values)} ON DUPLICATE KEY UPDATE {key_string} '
    db.execute(insert_sql, (), need_commit=True)

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_recv'], timeoutd.get('nurse_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_send'], timeoutd.get('nurse_send_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_recv'], timeoutd.get('doctor_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_handle'], timeoutd.get('doctor_handle_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['total'], timeoutd.get('total_timeout'))

    del db


"""
查询危机值系统超时时间
"""


def query_timeout():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_timeout where type = \'cv\' '
    timeout_sets = db.query_one(query_sql)
    del db

    return timeout_sets


"""
维护站点信息
"""


def site_maintenance(json_data):
    sited = {'site_dept': json_data.get('site_dept'), 'site_dept_id': json_data.get('site_dept_id') or -1,
             'site_ward': json_data.get('site_ward'), 'site_ward_id': json_data.get('site_ward_id') or -1,
             'dept_phone': json_data.get('dept_phone'), 'ward_phone': json_data.get('ward_phone'),
             'doctor_phone': json_data.get('doctor_phone'), 'site_ip': json_data.get('site_ip')}

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    keys = ','.join(sited.keys())
    values = tuple(sited.values())
    # 将键和值按指定格式拼接成字符串
    key_string = ', '.join([f"{key} = {repr(value)}" for key, value in sited.items()])

    # 存在则更新 不存在则插入
    insert_sql = f'INSERT INTO nsyy_gyl.cv_site({keys}) VALUE {str(values)} ON DUPLICATE KEY UPDATE {key_string} '
    db.execute(insert_sql, (), need_commit=True)

    redis_client = redis.Redis(connection_pool=pool)
    if sited['site_dept_id'] != -1:
        key = cv_config.CV_SITES_REDIS_KEY[2] + str(sited['site_dept_id'])
        redis_client.sadd(key, sited['site_ip'])
    if sited['site_ward_id'] != -1:
        key = cv_config.CV_SITES_REDIS_KEY[1] + str(sited['site_ward_id'])
        redis_client.sadd(key, sited['site_ip'])

    del db


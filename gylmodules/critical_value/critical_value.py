import redis
import json
import threading
import requests
import socket

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)

scheduler = BackgroundScheduler()
cv_id_lock = threading.Lock()


"""
判断是否在本地运行 
"""


def run_in_local():
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到远程服务器（无需实际连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        ip_address = s.getsockname()[0]
        # '192.168.124.3' 为本地 ip
        if ip_address == '192.168.124.3':
            return True
        else:
            return False
    except Exception as e:
        print("Error:", e)
        return False


def write_cache(key, value):
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hset(cv_config.CV_REDIS_KEY, key, json.dumps(value, default=str))


def read_cache(key):
    redis_client = redis.Redis(connection_pool=pool)
    value = redis_client.hget(cv_config.CV_REDIS_KEY, key)
    if type(value) == int:
        return value
    return json.loads(value)


def deltel_cache(key):
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hdel(cv_config.CV_REDIS_KEY, key)


"""
启动时加载所有未完成的危机值，放入内存
"""


def pull_running_cv():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_timeout where type = \'cv\' '
    timeout_sets = db.query_one(query_sql)

    # 加载超时配置到内存
    if timeout_sets is None:
        nurse_timeout = 5 * 60
        doctor_timeout = 5 * 60
        total_timeout = 10 * 60
    else:
        timeout_unit = timeout_sets.get('timeout_unit')
        nurse_timeout = timeout_sets.get('nurse_timeout')
        doctor_timeout = timeout_sets.get('doctor_timeout')
        total_timeout = timeout_sets.get('total_timeout')

        # 将超时时间统一替换为 秒 存到缓存中
        if int(timeout_unit) == 1:
            # 小时
            nurse_timeout = nurse_timeout * 60 * 60
            doctor_timeout = doctor_timeout * 60 * 60
            total_timeout = total_timeout * 60 * 60
        elif int(timeout_unit) == 2:
            # 分钟
            nurse_timeout = nurse_timeout * 60
            doctor_timeout = doctor_timeout * 60
            total_timeout = total_timeout * 60

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.set(cv_config.NURSE_TIMEOUT_KEY, nurse_timeout)
    redis_client.set(cv_config.DOCTOR_TIMEOUT_KEY, doctor_timeout)
    redis_client.set(cv_config.DOCTOR_HANDLE_TIMEOUT_KEY, doctor_timeout)
    redis_client.set(cv_config.TOTAL_TIMEOUT_KEY, total_timeout)

    # 加载所有处理中的危机值到内存
    query_sql = 'select * from nsyy_gyl.cv_info where state != {} ' \
        .format(cv_config.DOCTOR_HANDLE_STATE)
    cvs = db.query_all(query_sql)
    for cv in cvs:
        key = cv.get('cv_id') + '_' + str(cv.get('cv_source'))
        write_cache(key, cv)

    del db


pull_running_cv()


"""
从系统中抓取危机值
"""


def read_cv_from_system():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    sql = ''
    # 查询所有处理中的危机值(只查询系统触发的危机值)
    query_sql = 'select cv_id, alertdt from nsyy_gyl.cv_info ' \
                'where state != {} and cv_source = {} order by alertdt '\
        .format(cv_config.DOCTOR_HANDLE_STATE, cv_config.CV_SOURCE_SYSTEM)
    processing_cvs = db.query_all(query_sql)

    start_t = processing_cvs[0].get('alertdt').strftime("%Y-%m-%d %H:%M:%S") \
        if processing_cvs else str(datetime.now()-timedelta(seconds=86400))[:19]
    resultalertids = [item['cv_id'] for item in processing_cvs]
    idrs = f"resultalertid in ({','.join(resultalertids)}) or " if resultalertids else ''
    sql = f"""
            select * from inter_lab_resultalert 
            where {idrs} alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss') and 
            VALIDFLAG=1 and HISCHECK1SYNCFLAG =0
            """

    param = {
        "type": "orcl_db_read",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": sql
    }

    data = []
    if run_in_local():
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print('从系统中抓取危机值失败： ' + e.__str__())
    else:
        # 正式环境
        # from tools import orcl_db_read
        # data = orcl_db_read(param)
        print()

    if len(data) == 0:
        print('未从危机值系统抓取到任何危机值 ' + str(param))
        return

    # 按字典格式将系统危机值存储起来
    system_cv = {}
    if data is not None and len(data) > 0:
        for d in data:
            system_cv[d.get('RESULTALERTID')] = d
    oldids = [item['cv_id'] for item in processing_cvs]
    newids = [item['RESULTALERTID'] for item in data]

    delidl = list(set(oldids) - set(newids))
    newidl = list(set(newids) - set(oldids))

    for id in delidl:
        invalid_crisis_value(id, cv_config.CV_SOURCE_SYSTEM)

    for id in newidl:
        create_cv_by_system(system_cv[id], cv_config.CV_SOURCE_SYSTEM)


"""
作废危机值
"""


def invalid_crisis_value(cv_id, cv_source):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 更新危机值状态未作废
    update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s WHERE cv_id = %s and cv_source = %s '
    args = (cv_config.INVALID_STATE, cv_id, cv_source)
    db.execute(update_sql, args, need_commit=True)

    # 从内存中移除
    key = cv_id + '_' + str(cv_source)
    deltel_cache(key)

    del db


"""
系统创建危机值
"""


def create_cv_by_system(json_data, cv_source):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 缓存所有部门信息
    if not redis_client.exists(cv_config.DEPT_INFO_REDIS_KEY):
        cache_all_dept_info()

    # 上报id
    cv_id = json_data.get('RESULTALERTID')
    query_sql = 'select * from nsyy_gyl.cv_info where cv_id = \'{}\' '.format(cv_id)
    record = db.query_one(query_sql)
    # 防止重复上报危机值
    if record:
        return

    # 上报时间
    alertdt = json_data.get('ALERTDT')
    original_datetime_obj = datetime.strptime(alertdt, '%a, %d %b %Y %H:%M:%S GMT')
    alertdt = original_datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

    # 上报人（在oa 中是员工号）
    alertman = json_data.get('ALERTMAN')
    # 病人来源 1门诊 2急诊 3住院 4 体检
    pat_typecode = json_data.get('PAT_TYPECODE')
    # 病历号
    pat_no = json_data.get('PAT_NO')
    # 姓名
    pat_name = json_data.get('PAT_NAME')
    pat_sex = json_data.get('PAT_SEX')
    pat_agestr = json_data.get('PAT_AGESTR')
    # 所属科室
    req_deptno = json_data.get('REQ_DEPTNO')

    if req_deptno is not None and not req_deptno.isdigit():
        print('当前危机值病人科室不是数字，跳过。 ' + str(json_data))
        return

    dept_name = ''
    if redis_client.hexists(cv_config.DEPT_INFO_REDIS_KEY, req_deptno):
        dept_name = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, req_deptno)
    # 所属病区
    req_wardno = json_data.get('REQ_WARDNO')
    ward_name = ''
    if redis_client.hexists(cv_config.DEPT_INFO_REDIS_KEY, req_wardno):
        ward_name = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, req_wardno)
    req_bedno = json_data.get('REQ_BEDNO')
    # 开单医生
    req_docno = json_data.get('REQ_DOCNO')
    # 报告项目名称
    rpt_itemname = json_data.get('RPT_ITEMNAME')
    # 结果
    result_num = json_data.get('RESULT_NUM')
    # 结果状态
    result_flag = json_data.get('RESULT_FLAG')
    # 结果单位
    result_unit = json_data.get('RESULT_UNIT')
    # 结果参考值 H偏高 HH偏高报警 L偏低 LL偏低报警 P阳性 E错误
    result_ref = json_data.get('RESULT_REF')
    # 复查标志 0无需复查 1需要复查 2已经复查
    redo_flag = json_data.get('REDO_FLAG')
    # 违反的规则
    alertrules = json_data.get('ALERTRULES')

    # 根据员工号查询部门信息
    alert_dept_id, alert_dept_name, alertman_name = get_dept_info_by_emp_num(alertman)
    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")

    redis_client = redis.Redis(connection_pool=pool)
    nurse_timeout = redis_client.get(cv_config.NURSE_TIMEOUT_KEY)
    doctor_timeout = redis_client.get(cv_config.DOCTOR_TIMEOUT_KEY)
    doctor_handle_timeout = redis_client.get(cv_config.DOCTOR_HANDLE_TIMEOUT_KEY)
    total_timeout = redis_client.get(cv_config.TOTAL_TIMEOUT_KEY)

    args = (cv_id, cv_source, alertman, alertman_name, alertdt, alert_dept_id, alert_dept_name,
            pat_typecode, pat_no, pat_name, pat_sex, pat_agestr, req_bedno,
            req_docno, req_wardno, ward_name, req_deptno, dept_name,
            rpt_itemname, result_num, result_unit, result_ref, result_flag, redo_flag, alertrules, timer,
            cv_config.NOTIFICATION_NURSE_STATE, nurse_timeout, doctor_timeout, doctor_handle_timeout, total_timeout)
    insert_sql = "INSERT INTO nsyy_gyl.cv_info (cv_id, cv_source, alertman, alertman_name, alertdt, " \
                 "alert_dept_id, alert_dept_name," \
                 "patient_type, patient_treat_id, patient_name, patient_gender, patient_age, patient_bed_num, " \
                 "req_docno, ward_id, ward_name, dept_id, dept_name, " \
                 "cv_name, cv_result, cv_unit, cv_ref, cv_flag, redo_flag, alertrules, time, state, " \
                 "nurse_timeout, doctor_timeout, doctor_handle_timeout, total_timeout) " \
                 "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        raise Exception("系统危机值入库失败! " + str(args))

    # TODO 这里不要查询，直接组装 危机值信息字典
    query_sql = 'select * from nsyy_gyl.cv_info where cv_id = \'{}\' '\
        .format(cv_id)
    record = db.query_one(query_sql)

    # 3. 发送危机值
    push_to_nurse(req_wardno, pat_name)

    # 4. 将危机值放入常量中
    key = cv_id + '_' + str(cv_source)
    write_cache(key, record)


"""
根据员工号，查询科室信息
"""


def get_dept_info_by_emp_num(emp_num):
    param = {
        "type": "his_dept_pers",
        "pers_no": emp_num,
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }

    data = []
    if run_in_local():
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            # # 解析内容
            # print(response.text)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            raise Exception('根据员工号抓取部门信息失败： ' + e.__str__())
    else:
        # 正式环境
        # from tools import his_dept_pers
        # data = his_dept_pers(param)
        print("正式环境 his_dept_pers")

    # 使用列表推导式提取 "缺省" 值为 1 的元素
    if len(data) > 0:
        result = [item for item in data if item.get("缺省") == 1]
        return result[0].get('HIS_DEPT_ID'), result[0].get('DEPT_NAME'), result[0].get('PERS_NAME')
    else:
        raise Exception('根据员工号抓取部门信息失败 ' + str(param))


"""
缓存科室信息
"""


def cache_all_dept_info():
    # dept_type 1 临床科室 2 护理单元 0 全部
    param = {
    "type": "his_dept",
    "dept_type": 0,
    "comp_id": 12,
    "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
}

    data = []
    if run_in_local():
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            # # 解析内容
            # print(response.text)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            raise Exception('抓取所有部门信息失败： ' + e.__str__())
    else:
        # from tools import his_dept
        # data = his_dept(param)
        print("正式环境 his_dept")

    # 缓存所有科室信息
    redis_client = redis.Redis(connection_pool=pool)
    if len(data) > 0:
        for d in data:
            redis_client.hset(cv_config.DEPT_INFO_REDIS_KEY, d.get('his_dept_id'), d.get('dept_name'))


"""
查询危机值
"""


def get_cv_list(json_data):
    """
    查询危机值列表
    """
    dept_id = json_data.get("dept_id")
    ward_id = json_data.get("ward_id")
    if dept_id == '':
        dept_id = None
    if ward_id == '':
        ward_id = None

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if dept_id is None and ward_id is None:
        raise Exception("科室id 和 病区id 不能同时为空.")

    if dept_id is None:
        query_sql = 'select * from nsyy_gyl.cv_info where ward_id = {} '.format(ward_id)
        undo_list = db.query_all(query_sql)
    elif ward_id is None:
        query_sql = 'select * from nsyy_gyl.cv_info where dept_id = {} '.format(dept_id)
        undo_list = db.query_all(query_sql)
    else:
        query_sql = 'select * from nsyy_gyl.cv_info where dept_id = {} or ward_id = {} '\
            .format(dept_id, ward_id)
        undo_list = db.query_all(query_sql)

    del db

    return undo_list


"""
查询处理中的危机值并通知
"""


def query_process_cv_and_notice(json_data):
    dept_id = json_data.get("dept_id")
    ward_id = json_data.get("ward_id")
    if dept_id == '':
        dept_id = None
    if ward_id == '':
        ward_id = None

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if dept_id is None and ward_id is None:
        raise Exception("科室id 和 病区id 不能同时为空.")

    key = ''
    if dept_id is None:
        key = f'ward_id = {ward_id}'
    elif ward_id is None:
        key = f'dept_id = {dept_id}'
    else:
        key = f'(dept_id = {dept_id} or ward_id = {ward_id})'

    query_sql = f'select * from nsyy_gyl.cv_info where state != {cv_config.DOCTOR_HANDLE_STATE} and {key} '
    running = db.query_all(query_sql)
    if running:
        patient_names = [item['patient_name'] for item in running]
        names = ','.join(patient_names)
        if ward_id is not None:
            alert(1, ward_id, f"病人 {names} 存在未处理完的危机值，请及时处理")
        if dept_id is not None:
            alert(2, dept_id, f"病人 {names} 存在未处理完的危机值，请及时处理")

    del db



"""
向护士站推送危机值
"""


def push_to_nurse(ward_id: int, patient_name: str):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 弹框提醒护士
    # if type(ward_id) != int:
    notice_msg = '病人 [{}] 出现危机值, 请及时查看并处理'.format(patient_name)
    query_sql = 'select * from nsyy_gyl.cv_site where site_ward_id = {} '\
        .format(int(ward_id))
    sites = db.query_all(query_sql)
    if sites:
        for site in sites:
            push_notice('http://{}:8085/opera_wiki'.format(site.get('site_ip')), notice_msg)

    del db


"""
推送弹框通知 type = 1 通知护士， type = 2 通知医生
"""


def alert(type, id, msg):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 弹框提升护理，及时接收
    key = 'site_ward_id = {}'.format(id) if type == 1 else 'site_dept_id = {}'.format(id)
    query_sql = f'select * from nsyy_gyl.cv_site where {key} '
    sites = db.query_all(query_sql)
    if sites:
        for site in sites:
            push_notice('http://{}:8085/opera_wiki'.format(site.get('site_ip')), msg)



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
    push_type = json_data.get('push_type')
    patient_name = json_data.get('patient_name')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = 'select * from nsyy_gyl.cv_info where cv_id = \'{}\' '.format(cv_id)
    cvinfo = db.query_one(query_sql)

    to_site_id = -1
    if cvinfo:
        to_site_id = cvinfo.get('dept_id')
    notice_msg = '病人 [{}] 出现危机值, 请及时查看并处理'.format(patient_name)

    # 护理（病区护士站 门诊 急诊） -> 医生
    if push_type == 1:
        # 更新危机值状态为 【通知医生】
        update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s WHERE cv_id = %s'
        args = (cv_config.NOTIFICATION_DOCTOR_STATE, cv_id)
        db.execute(update_sql, args, need_commit=True)

        # 同步更新常量中的状态
        key = cv_id + '_' + str(cvinfo.get('cv_source'))
        value = read_cache(key)
        value['state'] = cv_config.NOTIFICATION_DOCTOR_STATE
        write_cache(key, value)

        # 弹框提醒医生
        query_sql = 'select * from nsyy_gyl.cv_site where site_dept_id = {} ' \
            .format(to_site_id)
        sites = db.query_all(query_sql)
        if sites:
            print('查询到 ' + str(len(sites)) + ' 个ip地址')
            for site in sites:
                push_notice('http://{}:8085/opera_wiki'.format(site.get('site_ip')), notice_msg)

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
                     'nurse_recv_time = %s, nurse_recv_info = %s  WHERE cv_id = %s'
        args = (cv_config.NURSE_RECV_STATE, confirmer_id, confirmer_name, timer, confirm_info, cv_id)
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
                     'doctor_recv_name = %s, doctor_recv_time = %s WHERE cv_id = %s'
        args = (cv_config.DOCTOR_RECV_STATE, confirmer_id, confirmer_name, timer, cv_id)
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
    update_sql = 'UPDATE nsyy_gyl.cv_info SET nursing_record = %s, nursing_record_time = %s WHERE cv_id = %s'
    args = (record, timer, cv_id)
    db.execute(update_sql, args, need_commit=True)

    # 同步更新常量中的状态
    key = cv_id + '_' + str(cv_source)
    value = read_cache(key)
    value['state'] = cv_config.DOCTOR_RECV_STATE
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

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")
    # 更新危机值状态为 【医生处理】
    update_sql = 'UPDATE nsyy_gyl.cv_info ' \
                 'SET state = %s, analysis = %s, method = %s, ' \
                 'handle_time = %s, handle_doctor_name = %s, handle_doctor_id = %s  ' \
                 'WHERE cv_id = %s'
    args = (cv_config.DOCTOR_HANDLE_STATE, analysis, method, timer, handler_name, handler_id, cv_id)
    db.execute(update_sql, args, need_commit=True)

    # 同步更新常量中的状态
    key = cv_id + '_' + str(cv_source)
    value = read_cache(key)
    value['state'] = cv_config.DOCTOR_HANDLE_STATE
    value['analysis'] = analysis
    value['method'] = method
    value['handle_time'] = timer
    value['handle_doctor_name'] = handler_name
    value['handle_doctor_id'] = handler_id
    write_cache(key, value)

    # 医生处理之后，进行数据回传
    data_feedback(cv_id, handler_id, timer, method, 2)

    deltel_cache(key)

    del db


"""
推送弹框通知
"""


def push_notice(url: str, msg: str):
    try:
        # 定义要发送的字符串数据
        payload = {'type': 'popup', 'wiki_info': msg}
        # 发送 POST 请求，将字符串数据传递给 data 参数
        response = requests.post(url, json=payload)
        # # 打印响应内容
        # print(response.text)
    except Exception as e:
        print('推送弹框通知失败： ' + e.__str__())


"""
统计报表
"""


def report_form(json_data):
    start_time = json_data.get("start_time")
    end_time = json_data.get("end_time")

    # page_number: 要查询的页码，从 1 开始
    page_number = json_data.get("page_number")
    # page_size: 每页的记录数量
    page_size = json_data.get("page_size")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_info where state != {} and (time BETWEEN \'{}\' AND \'{}\' )'\
        .format(cv_config.DOCTOR_HANDLE_STATE, start_time, end_time)
    undo_list = db.query_all(query_sql)
    undo_num = 0
    if undo_list:
        undo_num = len(undo_list)
    else:
        undo_list = []

    # 计算要查询的起始索引和结束索引
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    # 使用切片操作从数据集中获取特定范围的数据
    undo_list = undo_list[start_index:end_index]

    query_sql = 'select * from nsyy_gyl.cv_info where state = {} and (time BETWEEN \'{}\' AND \'{}\' )' \
        .format(cv_config.DOCTOR_HANDLE_STATE, start_time, end_time)
    done_list = db.query_all(query_sql)
    done_num = 0
    if done_list:
        done_num = len(done_list)
    else:
        done_list = []

    # 计算要查询的起始索引和结束索引
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    # 使用切片操作从数据集中获取特定范围的数据
    done_list = done_list[start_index:end_index]

    return undo_list, undo_num, done_list, done_num


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
                  "HISCHECKINFO": confirm_info, "HISCHECKSYNCFLAG": "1"}]
        updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO", "HISCHECKSYNCFLAG"]
        datel = ["HISCHECKDT"]
    else:
        # 医生确认
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN1": str(confirmer_id), "HISCHECKDT1": timer,
                  "HISCHECKINFO1": confirm_info, "HISCHECK1SYNCFLAG": "1"}]
        updatel = ["HISCHECKMAN1", "HISCHECKDT1", "HISCHECKINFO1", "HISCHECK1SYNCFLAG"]
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

    if run_in_local():
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            # # 解析内容
            # print(response.text)
        except Exception as e:
            print('数据回传失败： param = ' + str(param) + "   " + e.__str__())
    else:
        # from tools import orcl_db_update
        # data = orcl_db_update(param)
        print("正式环境 orcl_db_update")



"""
生成危机值id
"""


def get_cv_id():
    with cv_id_lock:
        timer = datetime.now()
        timer = timer.strftime("%Y%m%d%H%M%S")
        return 'CV' + timer


"""
设置危机值系统超时时间
"""


def setting_timeout(json_data):
    nurse_timeout = int(json_data.get('nurse_timeout'))
    doctor_timeout = int(json_data.get('doctor_timeout'))
    total_timeout = int(json_data.get('total_timeout'))
    timeout_unit = int(json_data.get('timeout_unit'))

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_timeout where type = \'cv\' '
    timeout_sets = db.query_one(query_sql)
    if timeout_sets:
        # 存在即更新
        update_sql = 'UPDATE nsyy_gyl.cv_timeout SET nurse_timeout = %s, doctor_timeout = %s,' \
                     'total_timeout = %s, timeout_unit = %s WHERE type = \'cv\' '
        args = (nurse_timeout, doctor_timeout, total_timeout, timeout_unit)
        db.execute(update_sql, args, need_commit=True)
    else:
        # 不存在则插入
        args = ('cv', nurse_timeout, doctor_timeout, total_timeout, timeout_unit)
        insert_sql = "INSERT INTO nsyy_gyl.cv_timeout (type, nurse_timeout, " \
                     "doctor_timeout, total_timeout, timeout_unit) " \
                     "VALUES (%s,%s,%s,%s,%s)"
        last_rowid = db.execute(insert_sql, args, need_commit=True)
        if last_rowid == -1:
            raise Exception("危机值超时时间配置入库失败!")

    # 将超时时间统一替换为 秒 存到缓存中
    if timeout_unit == 1:
        # 小时
        nurse_timeout = nurse_timeout * 60 * 60
        doctor_timeout = doctor_timeout * 60 * 60
        total_timeout = total_timeout * 60 * 60
    elif timeout_unit == 2:
        # 分钟
        nurse_timeout = nurse_timeout * 60
        doctor_timeout = doctor_timeout * 60
        total_timeout = total_timeout * 60

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.set(cv_config.NURSE_TIMEOUT_KEY, nurse_timeout)
    redis_client.set(cv_config.DOCTOR_TIMEOUT_KEY, doctor_timeout)
    redis_client.set(cv_config.DOCTOR_HANDLE_TIMEOUT_KEY, doctor_timeout)
    redis_client.set(cv_config.TOTAL_TIMEOUT_KEY, total_timeout)

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
    site_dept = json_data.get('site_dept')
    site_dept_id = json_data.get('site_dept_id')
    if site_dept_id == '':
        site_dept_id = -1
    site_ward = json_data.get('site_ward')
    site_ward_id = json_data.get('site_ward_id')
    if site_ward_id == '':
        site_ward_id = -1
    # 科室主任电话
    dept_phone = json_data.get('dept_phone')
    # 病区电话
    ward_phone = json_data.get('ward_phone')
    # 值班医生电话
    doctor_phone = json_data.get('doctor_phone')
    site_ip = json_data.get('site_ip')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_site where site_ip = \'{}\' ' \
        .format(site_ip)
    cv_site = db.query_one(query_sql)

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")

    if cv_site:
        # 存在即更新
        update_sql = 'UPDATE nsyy_gyl.cv_site ' \
                     'SET site_dept = %s, site_dept_id = %s, ' \
                     'site_ward = %s, site_ward_id = %s, time = %s,' \
                     'dept_phone = %s, ward_phone = %s, doctor_phone = %s' \
                     ' WHERE site_ip = %s '
        args = (site_dept, site_dept_id, site_ward, site_ward_id, timer,
                dept_phone, ward_phone, doctor_phone, site_ip)
        db.execute(update_sql, args, need_commit=True)
    else:
        # 不存在则插入
        args = (site_dept, site_dept_id, site_ward, site_ward_id, site_ip, timer,
                dept_phone, ward_phone, doctor_phone)
        insert_sql = "INSERT INTO nsyy_gyl.cv_site (site_dept, site_dept_id, " \
                     "site_ward, site_ward_id, site_ip, time, dept_phone, ward_phone, doctor_phone) " \
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        last_rowid = db.execute(insert_sql, args, need_commit=True)
        if last_rowid == -1:
            print(args)
            raise Exception("站点信息添加失败, site info: " + json_data)

    del db


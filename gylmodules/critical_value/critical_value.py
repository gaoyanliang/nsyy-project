import pymssql
import redis
import json
import threading
import requests
from aiohttp import ClientTimeout
from suds.client import Client
from contextlib import suppress

from datetime import datetime, timedelta
import time

from apscheduler.schedulers.background import BackgroundScheduler

from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.utils.db_utils import DbUtil
import asyncio
import aiohttp
from ping3 import ping

pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)

scheduler = BackgroundScheduler()
cv_id_lock = threading.Lock()

"""
调用第三方系统获取数据
"""


def call_third_systems_obtain_data(type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            # response = requests.post("http://192.168.3.12:6080/int_api", json=param)
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print(datetime.now(),
                  '调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
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
        elif type == 'orcl_db_read':
            # 根据住院号/门诊号查询 病人id 主页id
            from tools import orcl_db_read
            data = orcl_db_read(param)
        elif type == 'his_procedure':
            # 危机值病历回写
            from tools import his_procedure
            data = his_procedure(param)
        elif type == 'send_wx_msg':
            # 向企业微信推送消息
            from tools import send_wx_msg
            data = send_wx_msg(param)

    if type == 'get_dept_info_by_emp_num':
        # 使用列表推导式提取 "缺省" 值为 1 的元素
        if data and len(data) > 0:
            result = [item for item in data if item.get("缺省") == 1]
            return result[0].get('HIS_DEPT_ID'), result[0].get('DEPT_NAME'), \
                result[0].get('PERS_NAME'), result[0].get('oa_pers_id')
        else:
            print(datetime.now(), '根据员工号抓取部门信息失败 ', str(param))
            return -1, 'unknow', 'unkonw', -1

    elif type == 'cache_all_dept_info':
        # 缓存所有科室信息
        redis_client = redis.Redis(connection_pool=pool)
        if len(data) > 0:
            for d in data:
                redis_client.hset(cv_config.DEPT_INFO_REDIS_KEY, d.get('his_dept_id'), json.dumps(d, default=str))
                redis_client.hset(cv_config.DEPT_INFO_REDIS_KEY, d.get('dept_code'), json.dumps(d, default=str))

    return data


"""
操作缓存
"""


def write_cache(key, value):
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hset(cv_config.RUNNING_CVS_REDIS_KEY, key, json.dumps(value, default=str))


def read_cache(key):
    redis_client = redis.Redis(connection_pool=pool)
    value = redis_client.hget(cv_config.RUNNING_CVS_REDIS_KEY, key)
    if not value:
        print(datetime.now(), f'key = {key} , value is nil')
        return None
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
            dept_idl = str(site.get('site_dept_id')).split(',')
            for dept_id in dept_idl:
                key = cv_config.CV_SITES_REDIS_KEY[2].format(str(dept_id))
                redis_client.sadd(key, site.get('site_ip'))
        if site.get('site_ward_id'):
            ward_idl = str(site.get('site_ward_id')).split(',')
            for ward_id in ward_idl:
                key = cv_config.CV_SITES_REDIS_KEY[1].format(str(ward_id))
                redis_client.sadd(key, site.get('site_ip'))

    # 将超时时间配置加载至 redis 缓存
    query_sql = 'select * from nsyy_gyl.cv_timeout where type = \'cv\' '
    timeout_sets = db.query_one(query_sql)
    del db
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_recv'], timeout_sets.get('nurse_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_send'], timeout_sets.get('nurse_send_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_recv'], timeout_sets.get('doctor_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_handle'], timeout_sets.get('doctor_handle_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['total'], timeout_sets.get('total_timeout'))


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
    keys = redis_client.keys('CV_*')
    for key in keys:
        redis_client.delete(key)

    # 缓存所有部门信息 dept_type 1 临床科室 2 护理单元 0 全部
    call_third_systems_obtain_data('cache_all_dept_info', {
        "type": "his_dept",
        "dept_type": 0,
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    })

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 加载所有处理中的危机值到内存
    states = (cv_config.INVALID_STATE, cv_config.DOCTOR_HANDLE_STATE)
    query_sql = f'select * from nsyy_gyl.cv_info where state not in {states} or cv_source = {cv_config.CV_SOURCE_MANUAL} '
    cvs = db.query_all(query_sql)
    for cv in cvs:
        key = cv.get('cv_id') + '_' + str(cv.get('cv_source'))
        write_cache(key, cv)
        if cv.get('cv_source') == cv_config.CV_SOURCE_MANUAL and str(
                cv.get('patient_treat_id')) != cv_config.cv_manual_default_treat_id:
            # 手工上报的，单独存储
            redis_client.hset(cv_config.MANUAL_CVS_REDIS_KEY, cv['patient_treat_id'], json.dumps(cv, default=str))

    # 加载危机值模版
    try:
        cv_template = db.query_all(f'select * from nsyy_gyl.cv_template')
        for t in cv_template:
            redis_client.hset(cv_config.CV_TEMPLATE_REDIS_KEY, t['id'], json.dumps(t, default=str))

        alert_fail_logs = db.query_all(f'select * from nsyy_gyl.alert_fail_log')
        for log in alert_fail_logs:
            redis_client.sadd(cv_config.ALERT_FAIL_IPS_REDIS_KEY, log.get('ip'))
        del db
    except Exception as e:
        del db
        print(datetime.now(), '缓存危机值模版异常', e)

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
        # 手工上报的不查询
        if int(cv_source) == cv_config.CV_SOURCE_MANUAL:
            continue

        if cv_source not in running_ids:
            running_ids[cv_source] = []
        running_ids[cv_source].append(cv_id)

    query_sql = """
            select a.resultalertid,
                a.alertdt,
                a.alertman,
                a.reportid,
                to_char(a.resultid) resultid,
                a.rptunitname,
                a.pat_typecode,
                a.pat_no,
                a.pat_name,
                a.pat_sex,
                a.pat_agestr,
                a.pat_ageyear,
                a.req_deptno,
                a.req_wardno,
                a.req_bedno,
                a.req_docno,
                a.specimen_name,
                a.barcode,
                a.recievedt,
                a.rpt_itemid,
                a.itemcode_en,
                a.rpt_itemname,
                a.result_num,
                a.result_str,
                a.result1,
                a.result2,
                a.result3,
                a.result_flag,
                a.result_unit,
                a.result_ref,
                a.instrna,
                a.redo_flag,
                a.redo_result,
                a.alertrules,
                a.descriptions,
                a.hischeckman,
                a.hischeckdt,
                a.hischeckinfo,
                a.validflag,
                a.hischecksyncflag,
                a.hischeckman1,
                a.hischeckdt1,
                a.hischeckinfo1,
                a.hischeck1syncflag,
            2 cv_source from inter_lab_resultalert a 
            where (idrs_2 alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss'))
            union 
            select b.resultalertid,
                    b.alertdt,
                    b.alertman,
                    b.reportid,
                    b.resultid,
                    b.rptunitname,
                    b.pat_typecode,
                    b.pat_no,
                    b.pat_name,
                    b.pat_sex,
                    b.pat_agestr,
                    b.pat_ageyear,
                    b.req_deptno,
                    b.req_wardno,
                    b.req_bedno,
                    b.req_docno,
                    b.specimen_name,
                    b.barcode,
                    b.recievedt,
                    b.rpt_itemid,
                    b.itemcode_en,
                    b.rpt_itemname,
                    b.result_num,
                    b.result_str,
                    b.result1,
                    b.result2,
                    b.result3,
                    b.result_flag,
                    b.result_unit,
                    b.result_ref,
                    b.instrna,
                    b.redo_flag,
                    b.redo_result,
                    b.alertrules,
                    b.descriptions,
                    b.hischeckman,
                    b.hischeckdt,
                    b.hischeckinfo,
                    b.validflag,
                    b.hischecksyncflag,
                    b.hischeckman1,
                    b.hischeckdt1,
                    b.hischeckinfo1,
                    b.hischeck1syncflag,
                    b."cv_source" from NS_EXT.PACS危急值上报表 b 
            where (idrs_3 alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss')) 
            """

    systeml = [0, 1, 2, 3, 4, 5]

    return running_ids, query_sql, systeml


def create_cv(cvd):
    # cvd {cv_id_cv_source: cv}
    redis_client = redis.Redis(connection_pool=pool)
    running_cvs = redis_client.hkeys(cv_config.RUNNING_CVS_REDIS_KEY)

    # 过滤出需要作废/新增的危急值
    del_idl, new_idl = [], []
    for key, value in cvd.items():
        if int(value.get('VALIDFLAG')) == 0:
            # 作废的危急值
            del_idl.append(key)
            continue
        if value.get('HISCHECKMAN1') or key in running_cvs:
            # HISCHECKMAN1 不为空说明已经处理过了 / 处理中
            continue
        new_idl.append(key)

    # # 作废列表不能包含手工上报的
    # filtered_data = [item for item in running_cvs if not item.endswith(f'_{cv_config.CV_SOURCE_MANUAL}')]
    # del_idl = list(set(filtered_data) - set(new_cvs))
    # new_idl = list(set(new_cvs) - set(filtered_data))

    # 作废危机值
    cv_idd = {}
    for key in del_idl:
        cv_id, cv_source = key.split('_')
        cv_source = int(cv_source)
        if cv_source not in cv_idd:
            cv_idd[cv_source] = []
        cv_idd[cv_source].append(cv_id)
    for cv_source, cv_ids in cv_idd.items():
        try:
            invalid_crisis_value(cv_ids, cv_source)
        except Exception as e:
            print(datetime.now(), "作废危急值异常：cv_ids = ", cv_ids, ' cv_source = ', cv_source, 'Exception = ', e)

    # 新增的危急值有可能是之前手工上报的危急值，需要更新信息，不需要再插入一条新纪录
    # 新增危急值
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    for key in new_idl:
        try:
            cv_source = key.split('_')[1]
            cv_data = cvd[key]

            # 新增之前先匹配一下是否之前手工上报过
            if redis_client.hexists(cv_config.MANUAL_CVS_REDIS_KEY, str(cv_data['PAT_NO'])):
                manual_record = redis_client.hget(cv_config.MANUAL_CVS_REDIS_KEY, str(cv_data['PAT_NO']))
                manual_record = json.loads(manual_record)
                # 如果是同类型的危急值记录，默认匹配， 匹配完成之后移除手工上报记录
                if int(manual_record['cv_type']) == int(cv_source):
                    condation_sql = " , cv_name = '{}', cv_result = '{}' ".format(cv_data.get('RPT_ITEMNAME'),
                                                                                  cv_data.get('RESULT_STR'))
                    if int(cv_source) == cv_config.CV_SOURCE_INSPECTION_SYSTEM:
                        condation_sql += " , cv_flag = '{}', cv_unit = '{}', cv_ref = '{}', alertrules = '{}', redo_flag = {} ". \
                            format(cv_data.get('RESULT_FLAG'), cv_data.get('RESULT_UNIT'), cv_data.get('RESULT_REF'),
                                   cv_data.get('ALERTRULES'), cv_data.get('REDO_FLAG'))

                    if int(cv_source) == cv_config.CV_SOURCE_XUETANG_SYSTEM:
                        condation_sql += " , cv_flag = '{}', cv_unit = '{}'". \
                            format(cv_data.get('RESULT_FLAG'), cv_data.get('RESULT_UNIT'))

                    update_sql = "UPDATE nsyy_gyl.cv_info SET cv_id = '{}', cv_source = {}, patient_type = {}, " \
                                 " patient_gender = '{}', patient_age = '{}', patient_bed_num = '{}' {} WHERE id = {}".format(
                        cv_data['RESULTALERTID'], int(cv_source), cv_data['PAT_TYPECODE'], cv_data['PAT_SEX'],
                        cv_data['PAT_AGESTR'], cv_data['REQ_BEDNO'], condation_sql, manual_record['id'])
                    db.execute(update_sql, need_commit=True)

                    query_sql = 'select * from nsyy_gyl.cv_info WHERE id = {}'.format(manual_record['id'])
                    record = db.query_one(query_sql)

                    # 更新完成之后移除手工上报记录
                    redis_client.hdel(cv_config.MANUAL_CVS_REDIS_KEY, str(cv_data['PAT_NO']))
                    redis_client.hdel(cv_config.RUNNING_CVS_REDIS_KEY,
                                      str(manual_record['cv_id']) + '_' + str(manual_record['cv_source']))
                    if cv_config.DOCTOR_HANDLE_STATE > int(record.get('state')) > cv_config.INVALID_STATE:
                        redis_client.hset(cv_config.RUNNING_CVS_REDIS_KEY, key, json.dumps(record, default=str))

                    # 合并危急值时，如果危急值已经处理，回写数据
                    manual_cv_feedback(record)

                    continue
            create_cv_by_system(cv_data, int(cv_source))
        except Exception as e:
            print(datetime.now(), "新增危急值异常：cv_data = ", cv_data, ' key = ', key, 'Exception = ', e.__str__())
    del db


def manual_cv_feedback(record):
    try:
        if int(record.get('state')) == cv_config.DOCTOR_HANDLE_STATE:
            # 如果危机值已经处理，回写数据（有可能手工上报时没有正确填写住院号，导致数据回写失败，如果不再次回写，会一直抓取该条危急值）
            # 病历回写
            pat_no = record.get('patient_treat_id')
            pat_type = int(record.get('patient_type'))
            handle_doc = record.get('handle_doctor_name')
            handle_time = record.get('handle_time').strftime("%Y-%m-%d %H:%M:%S")
            method = record.get('method') if record.get('method') else '/'
            param = {
                "pat_no": pat_no,
                "pat_type": pat_type,
                "record": record,
                "handler_name": handle_doc,
                "timer": handle_time,
                "method": method,
                "analysis": record.get('analysis') if record.get('analysis') else ''
            }
            # 1. 回写病历
            medical_record_writing_back(param)

            # 2. 回写数据
            data_feedback(record.get('cv_id'), int(record.get('cv_source')), handle_doc, handle_time, method, 3)
    except Exception as e:
        print(datetime.now(), "合并危急值时，回写数据异常：record = ", record, 'Exception = ', e)


"""
作废危急值
"""


def invalid_crisis_value(cv_ids, cv_source, invalid_remote: bool = False):
    print(datetime.now(), '作废危急值： cv_source=', cv_source, " cv_ids=", cv_ids, invalid_remote)
    # 从内存中移除
    for cv_id in cv_ids:
        key = cv_id + '_' + str(cv_source)
        delete_cache(key)
        if invalid_remote and not global_config.run_in_local:
            invalid_remote_crisis_value(cv_id, cv_source)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 更新危急值状态未作废
    cv_ids = [f"'{item}'" for item in cv_ids]
    ids = ','.join(cv_ids)
    update_sql = f'UPDATE nsyy_gyl.cv_info SET state = {cv_config.INVALID_STATE}' \
                 f' WHERE cv_id in ({ids}) and cv_source = {cv_source} and state != 0'
    db.execute(update_sql, need_commit=True)
    del db


"""
作废远程危机值(主要针对仅需要上报一次的危机值)
"""


def invalid_remote_crisis_value(cv_id, cv_source):
    try:
        if int(cv_source) == 2:
            table_name = "inter_lab_resultalert"
        else:
            table_name = "NS_EXT.PACS危急值上报表"
        param = {
            "type": "orcl_db_update", "db_source": "ztorcl", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "table_name": table_name, "datal": [{"RESULTALERTID": cv_id, "VALIDFLAG": "0"}],
            "updatel": ["VALIDFLAG"], "datel": [], "intl": [], "keyl": ["RESULTALERTID"]
        }
        call_third_systems_obtain_data('data_feedback', param)
    except Exception as e:
        print(datetime.now(), '作废远程危机值异常', e)


"""
通过 socket 向危急值上报人员推送消息
"""


def notiaction_alert_man(msg: str, pers_id):
    try:
        if not int(pers_id):
            return

        data = {'msg_list': [{'socket_data': {
            "type": 400,
            "data": {
                "title": "危急值上报反馈",
                "context": msg
            }},
            'pers_id': int(pers_id)}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
        # print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", data, "user_id: ", pers_id)

        call_third_systems_obtain_data('send_wx_msg', {
            "type": "send_wx_msg",
            "key_d": {"type": 71, "process_id": 11527, "action": 4, "title": "危急值上报反馈", "content": msg},
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "pers_id": pers_id,
            "force_notice": 1
        })
    except Exception as e:
        print(datetime.now(), "通知危急值上报人员时出现异常, pers_id = ", pers_id, " 异常 = ", e)


# 查询患者最近半小时内是否上报过危急值
def have_cv_been_reported_recently(patient_name, patient_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"SELECT * FROM nsyy_gyl.cv_info " \
                f"WHERE time >= DATE_SUB(NOW(), INTERVAL 30 MINUTE) and patient_name = '{patient_name}'"
    records = db.query_all(query_sql)
    del db
    if records:
        cv_data = ''
        for record in records:
            if record.get('patient_treat_id') and int(record.get('patient_treat_id')) != int(patient_id):
                continue
            cv_data += record.get('cv_name') + " : " + record.get('cv_result') + "  "
        if cv_data:
            return True, cv_data
    return False, ''


"""
手工上报危急值
    # 必填字段
    # type 危急值来源 2 3 4 5
    # 上报人信息 alertman 员工号
    # 主治医生 req_docno
    # 科室和病区 dept_id dept_name ward_id ward_name
    # 危急值内容 cv_name cv_result cv_unit cv_ref cv_flag
"""


def manual_report_cv(json_data):
    redis_client = redis.Redis(connection_pool=pool)
    # 根据员工号查询部门信息
    param = {
        "type": "his_dept_pers",
        "pers_no": json_data['alertman'],
        "comp_id": 12,
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
    }
    json_data['alert_dept_id'], json_data['alert_dept_name'], \
        json_data['alertman_name'], json_data['alertman_pers_id'] = \
        call_third_systems_obtain_data('get_dept_info_by_emp_num', param)
    if not json_data.get('alertman_pers_id'):
        json_data['alertman_pers_id'] = 0

    if json_data['alert_dept_id'] == -1:
        raise Exception('员工号 [{}] 异常, 未找到相关人员'.format(json_data['alertman']))

    patient_treat_id = json_data.get('patient_treat_id')
    if patient_treat_id:
        if int(json_data['patient_type']) == 1:
            # 门诊
            sql = f"""
                SELECT 姓名, 年龄,
                   CASE 
                       WHEN 性别 = '男' THEN 1 
                       WHEN 性别 = '女' THEN 2 
                       ELSE NULL 
                   END AS 性别, 
                   接收时间, 执行部门ID as 入院科室ID 
                FROM 病人挂号记录 
                WHERE 门诊号 = '{patient_treat_id}' 
                ORDER BY 接收时间 DESC
            """
        else:
            sql = f"""
                SELECT 入院病床, 姓名, 年龄,
                   CASE 
                       WHEN 性别 = '男' THEN 1 
                       WHEN 性别 = '女' THEN 2 
                       ELSE NULL 
                   END AS 性别, 
                   入院日期, 出院日期, 入院病区ID, 当前病区ID, 入院科室ID, 出院科室ID
                FROM 病案主页 
                WHERE 住院号 = '{patient_treat_id}' 
                ORDER BY 入院日期 DESC
            """
        param = {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": sql
        }
        data = call_third_systems_obtain_data('orcl_db_read', param)
        if data and data[0]:
            json_data['patient_type'] = cv_config.PATIENT_TYPE_HOSPITALIZATION if not json_data.get(
                'patient_type') else json_data.get('patient_type')
            json_data['patient_name'] = data[0].get('姓名')
            json_data['patient_gender'] = data[0].get('性别')
            json_data['patient_age'] = data[0].get('年龄')
            json_data['patient_bed_num'] = data[0].get('入院病床', 0)
            # 判断科室/病区和 最新的科室/病区是否一致
            latest_dept = data[0].get('出院科室ID') if data[0].get('出院科室ID') else data[0].get('入院科室ID')
            if latest_dept:
                dept = int(json_data.get('dept_id', 0))
                if latest_dept != dept:
                    json_data['dept_id'] = latest_dept
                    dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, latest_dept)
                    if dept_info:
                        json_data['dept_name'] = json.loads(dept_info).get('dept_name')
            latest_ward = data[0].get('当前病区ID') if data[0].get('当前病区ID') else data[0].get('入院病区ID')
            if latest_ward:
                ward = int(json_data.get('ward_id', 0))
                if latest_ward != ward:
                    json_data['ward_id'] = latest_ward
                    ward_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, latest_ward)
                    if ward_info:
                        json_data['ward_name'] = json.loads(ward_info).get('dept_name')
        else:
            print(patient_treat_id, "住院号/门诊号异常，未查到病人信息, param: ", json_data)
            raise Exception(patient_treat_id, "住院号/门诊号异常，未查到病人信息")
    else:
        print(datetime.now(), patient_treat_id, '未填写病人住院号/门诊号, 使用默认数据 120, param: ', json_data)
        json_data['patient_treat_id'] = int(cv_config.cv_manual_default_treat_id)
        json_data['patient_type'] = cv_config.PATIENT_TYPE_OTHER

    # 是否强制提交，如果不是，查询患者最近半小时内是否上报过危急值
    if 'forced' in json_data and not json_data.get('forced'):
        try:
            is_repted, cv_data = have_cv_been_reported_recently(json_data['patient_name'], json_data['patient_treat_id'])
            if is_repted:
                return True, cv_data
        except Exception as e:
            print(datetime.now(), '判断近半小时内是否上报过危急值异常, param: ', json_data, e)

    if 'forced' in json_data:
        json_data.pop('forced')
    json_data['cv_id'] = str(int(time.time() * 1000))
    json_data['cv_source'] = cv_config.CV_SOURCE_MANUAL
    json_data['alertdt'] = str(datetime.now())[:19]
    json_data['time'] = str(datetime.now())[:19]
    json_data['state'] = cv_config.CREATED_STATE

    if not json_data.get('patient_name'):
        json_data['patient_name'] = '未知'

    # 超时时间配置
    json_data['nurse_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_recv']) or 120
    json_data['nurse_send_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_send']) or 60
    json_data['doctor_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_recv']) or 120
    json_data['doctor_handle_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_handle']) or 120
    json_data['total_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['total']) or 600

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 插入危机值
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.cv_info ({fileds}) VALUES {args}"
    last_rowid = db.execute(insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("系统危急值入库失败! " + str(args))

    # 发送危机值 直接通知医生和护士
    msg = '[{} - {} - {} - {}]'.format(json_data.get('patient_name', 'unknown'), json_data.get('req_docno', 'unknown'),
                                       json_data.get('patient_treat_id', '0'), json_data.get('patient_bed_num', '0'))
    main_alert(json_data.get('dept_id'), json_data.get('ward_id'),
               f'发现新危急值, 请及时查看并处理 <br> [患者-主管医生-住院/门诊号-床号] <br> {msg} <br> <br> <br> 点击 [确认] 跳转至危急值页面')

    # 通知医技科室
    if json_data.get('alertman_pers_id'):
        msg = '患者 {} 的危急值，已通知 {} - {}'.format(json_data.get('patient_name', 'unknown'),
                                                       json_data.get('dept_name', ' '), json_data.get('ward_name', ' '))
        notiaction_alert_man(msg, int(json_data.get('alertman_pers_id')))

    # 将危机值放入 redis cache
    query_sql = 'select * from nsyy_gyl.cv_info where id = {} '.format(last_rowid)
    record = db.query_one(query_sql)
    del db

    # 这里一定把 type 加上，用于匹配
    key = json_data['cv_id'] + f'_{cv_config.CV_SOURCE_MANUAL}'
    write_cache(key, record)
    # 手工上报的还需要 单独再存一份，用于匹配， todo 这里仅关注有住院号
    if int(json_data['patient_treat_id']) != int(cv_config.cv_manual_default_treat_id):
        redis_client.hset(cv_config.MANUAL_CVS_REDIS_KEY, str(json_data['patient_treat_id']),
                          json.dumps(record, default=str))

    return False, None


"""
系统创建危机值
"""


def create_cv_by_system(json_data, cv_source):
    redis_client = redis.Redis(connection_pool=pool)

    # 判断相同 cv_id cv_source 的危机值是否存在
    if redis_client.hexists(cv_config.RUNNING_CVS_REDIS_KEY, json_data.get('RESULTALERTID') + '_' + str(cv_source)):
        return

    cvd = {'dept_id': json_data.get('REQ_DEPTNO')}
    if cvd['dept_id'] and not cvd['dept_id'].isdigit():
        # print('当前危机值病人科室不是数字，跳过。 ' + str(json_data))
        return
    # 如果是社区门诊/康复中医院，跳过(不是总院的科室，不处理)
    if cvd['dept_id'] and cvd['dept_id'].isdigit() and \
            (int(cvd['dept_id']) == 462 or int(cvd['dept_id']) == 1000760 or
             str(cvd['dept_id']) == '0812' or str(cvd['dept_id']) == '08012'):
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
    cvd['alert_dept_id'], cvd['alert_dept_name'], cvd['alertman_name'], cvd['alertman_pers_id'] = \
        call_third_systems_obtain_data('get_dept_info_by_emp_num', param)

    if not cvd.get('alertman_pers_id'):
        cvd['alertman_pers_id'] = 0

    # 解析危机值病人信息
    cvd['patient_type'] = json_data.get('PAT_TYPECODE')
    cvd['patient_treat_id'] = json_data.get('PAT_NO')
    cvd['patient_name'] = json_data.get('PAT_NAME')
    cvd['patient_gender'] = json_data.get('PAT_SEX')
    cvd['patient_age'] = json_data.get('PAT_AGESTR')
    cvd['patient_bed_num'] = json_data.get('REQ_BEDNO')
    cvd['req_docno'] = json_data.get('REQ_DOCNO')
    if json_data.get('REQ_WARDNO'):
        cvd['ward_id'] = json_data.get('REQ_WARDNO')

    # 心电系统传的 dept_id 是 dept_code 而不是 his_dept_id， 为了保持逻辑一致性，这里特殊处理下
    if cvd.get('ward_id') and redis_client.hexists(cv_config.DEPT_INFO_REDIS_KEY, cvd['ward_id']):
        dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, cvd['ward_id'])
        if dept_info:
            dept_info = json.loads(dept_info)
            cvd['ward_name'] = dept_info.get('dept_name')
            cvd['ward_id'] = dept_info.get('his_dept_id')
    if cvd.get('dept_id') and redis_client.hexists(cv_config.DEPT_INFO_REDIS_KEY, cvd['dept_id']):
        dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, cvd['dept_id'])
        if dept_info:
            dept_info = json.loads(dept_info)
            cvd['dept_name'] = dept_info.get('dept_name')
            cvd['dept_id'] = dept_info.get('his_dept_id')

    if cvd['patient_treat_id']:
        sql = f"SELECT * FROM 病案主页 WHERE 住院号 = '{cvd['patient_treat_id']}' ORDER BY 主页ID DESC"
        param = {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": sql
        }
        data = call_third_systems_obtain_data('orcl_db_read', param)
        if data and data[0]:
            # 判断科室/病区和 最新的科室/病区是否一致
            latest_dept = data[0].get('出院科室ID') if data[0].get('出院科室ID') else data[0].get('入院科室ID')
            if latest_dept:
                dept = cvd.get('dept_id') if cvd.get('dept_id') else 0
                if latest_dept != dept:
                    cvd['dept_id'] = latest_dept
                    dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, latest_dept)
                    if dept_info:
                        cvd['dept_name'] = json.loads(dept_info).get('dept_name')
            latest_ward = data[0].get('当前病区ID') if data[0].get('当前病区ID') else data[0].get('入院病区ID')
            if latest_ward:
                ward = cvd.get('ward_id') if cvd.get('ward_id') else 0
                if latest_ward != ward:
                    cvd['ward_id'] = latest_ward
                    ward_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, latest_ward)
                    if ward_info:
                        cvd['ward_name'] = json.loads(ward_info).get('dept_name')

    # 解析危机值内容信息
    cvd['cv_name'] = json_data.get('RPT_ITEMNAME')
    cvd['cv_result'] = json_data.get('RESULT_STR') if json_data.get('RESULT_STR') else json_data.get('RPT_ITEMNAME')
    if int(cv_source) == cv_config.CV_SOURCE_INSPECTION_SYSTEM:
        cvd['cv_flag'] = json_data.get('RESULT_FLAG')
        cvd['cv_unit'] = json_data.get('RESULT_UNIT')
        # 结果参考值 H偏高 HH偏高报警 L偏低 LL偏低报警 P阳性 E错误
        cvd['cv_ref'] = json_data.get('RESULT_REF')
        # 复查标志 0无需复查 1需要复查 2已经复查
        cvd['redo_flag'] = json_data.get('REDO_FLAG')
        cvd['alertrules'] = json_data.get('ALERTRULES')

    if int(cv_source) == cv_config.CV_SOURCE_XUETANG_SYSTEM:
        cvd['cv_flag'] = json_data.get('RESULT_FLAG')
        cvd['cv_unit'] = json_data.get('RESULT_UNIT')

    # 超时时间配置
    cvd['nurse_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_recv']) or 120
    cvd['nurse_send_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['nurse_send']) or 60
    cvd['doctor_recv_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_recv']) or 120
    cvd['doctor_handle_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['doctor_handle']) or 120
    cvd['total_timeout'] = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['total']) or 600

    if json_data.get('INSTRNA'):
        cvd['instrna'] = json_data.get('INSTRNA')
        if json_data.get('REPORTID') and (
                cvd['instrna'].__contains__('血气仪') or cvd['instrna'].__contains__('荧光仪')):
            cvd['report_id'] = json_data.get('REPORTID')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 插入危机值
    fileds = ','.join(cvd.keys())
    args = str(tuple(cvd.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.cv_info ({fileds}) VALUES {args}"
    last_rowid = db.execute(insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("系统危急值入库失败! " + str(args))

    # 发送危机值 直接通知医生和护士
    msg = '[{} - {} - {} - {}]'.format(cvd.get('patient_name', 'unknown'), cvd.get('req_docno', 'unknown'),
                                       cvd.get('patient_treat_id', '0'), cvd.get('patient_bed_num', '0'))
    main_alert(cvd.get('dept_id'), cvd.get('ward_id'),
               f'发现新危急值, 请及时查看并处理 <br> [患者-主管医生-住院/门诊号-床号] <br> {msg}  <br> <br> <br> 点击 [确认] 跳转至危急值页面')

    # 通知医技科室
    if cvd.get('alertman_pers_id'):
        msg = '患者 {} 的危急值，已通知 {} - {}'.format(cvd.get('patient_name', 'unknown'),
                                                       cvd.get('dept_name', 'unknown'), cvd.get('ward_name', 'unknown'))
        notiaction_alert_man(msg, int(cvd.get('alertman_pers_id')))

    # 将危机值放入 redis cache
    query_sql = 'select * from nsyy_gyl.cv_info where id = {} '.format(last_rowid)
    record = db.query_one(query_sql)
    del db

    key = cvd['cv_id'] + '_' + str(cv_source)
    write_cache(key, record)


"""
查询危机值
"""


def get_cv_list(json_data):
    # type =1 未处理， type =2 已处理, type = 3 总流程超时, type = 4 所有状态
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    dept_idl = []
    ward_idl = []
    dept_id = json_data.get("dept_id")
    if dept_id:
        dept_idl = [dept_id]
    ward_id = json_data.get("ward_id")
    if ward_id:
        ward_idl = [ward_id]

    if not dept_idl:
        dept_idl = json_data.get("dept_idl") if json_data.get("dept_idl") else []
    if not ward_idl:
        ward_idl = json_data.get("ward_idl") if json_data.get("ward_idl") else []

    states = (cv_config.DOCTOR_HANDLE_STATE, cv_config.INVALID_STATE)
    state_sql = ' state not in {} '.format(states)
    if int(json_data.get('type')) == 2:
        state_sql = ' state in {} and is_timeout = 0 '.format(states)
    if int(json_data.get('type')) == 3:
        state_sql = ' is_timeout = 1 '
    if int(json_data.get('type')) == 4:
        state_sql = ' state >= 0 '

    alert_dept_id = json_data.get('alert_dept_id')
    alert_dept_id_sql = ''
    if alert_dept_id:
        alert_dept_id_sql = f' and alert_dept_id = {alert_dept_id} '

    cv_source = json_data.get('cv_source')
    cv_source_sql = ''
    if cv_source:
        cv_source_sql = f' and cv_source = {cv_source} '

    start_time = json_data.get("start_time")
    end_time = json_data.get("end_time")
    time_sql = ''
    if start_time and end_time:
        time_sql = f' and (time BETWEEN \'{start_time}\' AND \'{end_time}\') '

    condation_sql = ''
    if dept_idl and ward_idl:
        dept_idl = ', '.join(map(str, dept_idl))
        ward_idl = ', '.join(map(str, ward_idl))
        condation_sql = f'and (dept_id in ({dept_idl}) or ward_id in ({ward_idl}) )'
    else:
        if dept_idl:
            dept_idl = ', '.join(map(str, dept_idl))
            condation_sql = f' and dept_id in ({dept_idl}) '
        if ward_idl:
            ward_idl = ', '.join(map(str, ward_idl))
            condation_sql = f' and ward_id in ({ward_idl}) '

    if json_data.get('cv_id'):
        condation_sql += ' and cv_id = \'{}\' '.format(json_data.get('cv_id'))

    if json_data.get('patient_name'):
        condation_sql += ' and patient_name = \'{}\' '.format(json_data.get('patient_name'))

    if json_data.get('patient_treat_id'):
        condation_sql += ' and patient_treat_id = \'{}\' '.format(json_data.get('patient_treat_id'))

    alertman = json_data.get('alertman')
    if alertman:
        if str(alertman).isdigit():
            condation_sql += ' and alertman = \'{}\' '.format(alertman)
        else:
            condation_sql += ' and alertman_name like \'%{}%\' '.format(alertman)

    query_sql = f'select * from nsyy_gyl.cv_info where {state_sql} {time_sql} {condation_sql} {alert_dept_id_sql} {cv_source_sql} order by alertdt desc'
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
        condition_sql = f" and ward_id in ({','.join(map(str, ward_id))})" if type(
            ward_id) == list else f' and ward_id = {ward_id}'
    elif not ward_id:
        condition_sql = f" and dept_id in ({','.join(map(str, dept_id))})" if type(
            dept_id) == list else f' and dept_id = {dept_id}'
    else:
        condition_sql = f" and (dept_id in ({','.join(map(str, dept_id))}) or ward_id in ({','.join(map(str, ward_id))}) )" if type(
            dept_id) == list else f' and (dept_id = {dept_id} or ward_id = {ward_id})'

    states = (cv_config.INVALID_STATE, cv_config.DOCTOR_HANDLE_STATE)
    query_sql = f'select * from nsyy_gyl.cv_info where state not in {states} {condition_sql} '
    running = db.query_all(query_sql)
    del db

    if running:
        timeout_record = []
        for item in running:
            msg = '[{} - {} - {} - {}]'.format(item.get('patient_name', 'unknown'), item.get('req_docno', 'unknown'),
                                               item.get('patient_treat_id', '0'), item.get('patient_bed_num', '0'))
            timeout_record.append(msg)
        msgs = list(set(timeout_record))
        if dept_id and type(dept_id) == list:
            dept_id = dept_id[0]
        if ward_id and type(ward_id) == list:
            ward_id = ward_id[0]
        main_alert(dept_id, ward_id,
                   f'以下危急值未及时处理 <br> [患者-主管医生-住院/门诊号-床号] <br> ' + ' <br> '.join(
                       msgs) + ' <br> <br> <br> 点击 [确认] 跳转至危急值页面')


"""
推送弹框通知 type = 1 通知护士， type = 2 通知医生
"""


def write_alert_fail_log(fail_ips, fail_log):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    try:
        failed_log = []
        for ip in fail_ips:
            if redis_client.sismember(cv_config.ALERT_FAIL_IPS_REDIS_KEY, ip):
                continue
            failed_log.append({"ip": ip, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "log": fail_log})

        for log in failed_log:
            keys = ','.join(log.keys())
            values = tuple(log.values())
            # 存在则更新 不存在则插入
            insert_sql = f'INSERT INTO nsyy_gyl.alert_fail_log ({keys}) VALUE {str(values)} '
            db.execute(insert_sql, need_commit=True)
            redis_client.sadd(cv_config.ALERT_FAIL_IPS_REDIS_KEY, ip)
        del db
    except Exception:
        del db
        pass


async def call_remote_auto_start_script(ip, url, payload):
    try:
        timeout = ClientTimeout(total=3)  # 设置总超时时间为3秒
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = str(url).replace('8085', '8091')
            async with session.post(url, json=payload, timeout=2) as response:
                response.raise_for_status()
    except Exception:
        with suppress(Exception):
            write_alert_fail_log([ip], "调用自动启动程序失败")


async def send_request(ip, url, payload):
    try:
        timeout = ClientTimeout(total=3)  # 设置总超时时间为3秒
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, timeout=2) as response:
                response.raise_for_status()
    except Exception:
        if payload.get('type') == 'popup':
            await call_remote_auto_start_script(ip, url, payload)


async def alert(dept_id, ward_id, msg):
    redis_client = redis.Redis(connection_pool=pool)
    dept_sites = set()
    if dept_id is not None and dept_id != '' and int(dept_id):
        dept_sites = redis_client.smembers(cv_config.CV_SITES_REDIS_KEY[2].format(str(dept_id)))
    ward_sites = set()
    if ward_id is not None and ward_id != '' and int(ward_id):
        ward_sites = redis_client.smembers(cv_config.CV_SITES_REDIS_KEY[1].format(str(ward_id)))
    merged_set = dept_sites.union(ward_sites)

    if merged_set:
        popup_tasks = []
        for ip in merged_set:
            try:
                # ping 不通直接跳过
                response_time = ping(ip)
                if response_time is None:
                    continue
            except Exception:
                continue
            url = f'http://{ip}:8085/opera_wiki'
            popup_tasks.append(asyncio.create_task(send_request(ip, url, {'type': 'popup', 'wiki_info': msg})))

        if popup_tasks:
            await asyncio.wait(popup_tasks)


def main_alert(dept_id, ward_id, msg):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    try:
        if loop and loop.is_running():
            asyncio.create_task(alert(dept_id, ward_id, msg))
        else:
            asyncio.run(alert(dept_id, ward_id, msg))
    except Exception as e:
        print(datetime.now(), f"在执行 alert 时发生错误: {e}")


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
        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        if not value:
            return
        if int(value['state']) < cv_config.NOTIFICATION_DOCTOR_STATE:
            # 更新危机值状态为 【通知医生】
            update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, nurse_send_time = %s ' \
                         'WHERE cv_id = %s and cv_source = %s and state != 0'
            args = (cv_config.NOTIFICATION_DOCTOR_STATE, timer, cv_id, cv_source)
            db.execute(update_sql, args, need_commit=True)

            value['state'] = cv_config.NOTIFICATION_DOCTOR_STATE
            value['nurse_send_time'] = timer
            write_cache(key, value)
        # 弹框提醒医生
        msg = '[{} - {} - {} - {}]'.format(patient_name, value.get('req_docno', 'unknown'),
                                           value.get('patient_treat_id', '0'), value.get('patient_bed_num', '0'))
        main_alert(dept_id, None,
                   f"发现新危机值, 护理已确认，请医生及时查看并处理, <br> [患者-主管医生-住院/门诊号-床号] <br> {msg}  <br> <br> <br> 点击 [确认] 跳转至危急值页面")
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
        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        if not value:
            return
        if int(value['state']) < cv_config.NURSE_RECV_STATE:
            # 更新危机值状态为 【护理确认接收】
            update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, nurse_recv_id = %s, nurse_recv_name = %s,' \
                         'nurse_recv_time = %s, nurse_recv_info = %s  WHERE cv_id = %s and cv_source = %s and state != 0'
            args = (cv_config.NURSE_RECV_STATE, confirmer_id, confirmer_name, timer, confirm_info, cv_id, cv_source)
            db.execute(update_sql, args, need_commit=True)

            value['state'] = cv_config.NURSE_RECV_STATE
            value['nurse_recv_id'] = confirmer_id
            value['nurse_recv_name'] = confirmer_name
            value['nurse_recv_time'] = timer
            value['nurse_recv_info'] = confirm_info
            write_cache(key, value)

        # 护士接收之后，进行数据回传
        data_feedback(cv_id, int(cv_source), confirmer_name, timer, confirm_info, 1)

    elif confirm_type == 1:
        # 同步更新常量中的状态
        key = cv_id + '_' + str(cv_source)
        value = read_cache(key)
        if not value:
            return

        if int(value['state']) < cv_config.DOCTOR_RECV_STATE:
            # 更新危机值状态为 【医生确认接收】
            update_sql = 'UPDATE nsyy_gyl.cv_info SET state = %s, doctor_recv_id = %s, ' \
                         'doctor_recv_name = %s, doctor_recv_time = %s WHERE cv_id = %s and cv_source = %s and state != 0'
            args = (cv_config.DOCTOR_RECV_STATE, confirmer_id, confirmer_name, timer, cv_id, cv_source)
            db.execute(update_sql, args, need_commit=True)

            value['state'] = cv_config.DOCTOR_RECV_STATE
            value['doctor_recv_id'] = confirmer_id
            value['doctor_recv_name'] = confirmer_name
            value['doctor_recv_time'] = timer
            write_cache(key, value)

        # 医生接收之后，进行数据回传
        data_feedback(cv_id, int(cv_source), confirmer_name, timer, '已确认', 2)
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
                 'WHERE cv_id = %s and cv_source = %s '
    args = (record, timer, cv_id, cv_source)
    db.execute(update_sql, args, need_commit=True)
    del db


"""
医生处理危机值
"""


def doctor_handle_cv(json_data):
    cv_source = json_data.get("cv_source")
    handler_id = json_data.get("handler_id")
    handler_name = json_data.get("handler_name")
    cvs = json_data.get('cvs')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 从缓存中获取总流程的超时时间，如果不存在，默认 10 分钟
    redis_client = redis.Redis(connection_pool=pool)
    timeout = redis_client.get(cv_config.TIMEOUT_REDIS_KEY['total'])
    if not timeout:
        timeout = 10 * 60
    cur_time = datetime.now()
    timer = cur_time.strftime("%Y-%m-%d %H:%M:%S")

    for cv in cvs:
        cv_id = cv.get("cv_id")
        method = cv.get('method')
        create_time = cv.get('create_time')
        query_sql = f'select * from nsyy_gyl.cv_info where cv_id = \'{cv_id}\' and cv_source = {cv_source}'
        record = db.query_one(query_sql)
        if int(record.get('state')) < cv_config.DOCTOR_HANDLE_STATE:
            create_time = datetime.strptime(create_time, "%a, %d %b %Y %H:%M:%S GMT")
            update_total_timeout_sql = ''
            if (cur_time - create_time).seconds > int(timeout):
                update_total_timeout_sql = 'is_timeout = 1 , '
            # 更新危机值状态为 【医生处理】
            update_sql = f'UPDATE nsyy_gyl.cv_info SET {update_total_timeout_sql} state = %s, ' \
                         f' method = %s, handle_time = %s, handle_doctor_name = %s, handle_doctor_id = %s ' \
                         'WHERE cv_id = %s and cv_source = %s '
            args = (cv_config.DOCTOR_HANDLE_STATE, method, timer, handler_name, handler_id, cv_id, cv_source)
            db.execute(update_sql, args, need_commit=True)
            # 从缓存中移除
            key = cv_id + '_' + str(cv_source)
            delete_cache(key)

            try:
                # 病历回写
                pat_no = record.get('patient_treat_id')
                pat_type = int(record.get('patient_type'))
                medical_record_writing_back({
                    "pat_no": pat_no, "pat_type": pat_type, "record": record,
                    "handler_name": handler_name, "timer": timer, "method": method, "analysis": ''
                })

                if not record.get('nurse_recv_id'):
                    # 如果护士没有接收，由医生接收，回传接收数据
                    data_feedback(cv_id, int(cv_source), handler_name, timer, '已确认', 2)
                # 所有 cv source 类型都需要执行 data feedback，为了防止抓取到重复的危急值
                data_feedback(cv_id, int(cv_source), handler_name, timer, method, 3)
                # 心电系统和 pacs 系统单独回写对应的系统
                if int(cv_source) == 4:
                    # 心电危机值特殊处理
                    xindian_data_feedback(
                        {"cv_id": cv_id, "doc_id": handler_id, "doc_name": handler_name, "body": method})
                elif int(cv_source) == 3:
                    # pacs 危机值特殊处理
                    pacs_data_feedback({"cv_id": cv_id, "doc_name": handler_name, "body": method, "handle_time": timer})
                # 通知医技科室
                if record.get('alertman_pers_id'):
                    msg = '患者 {} 的危急值，医生 {} 已处理'.format(record.get('patient_name', 'unknown'), handler_name)
                    notiaction_alert_man(msg, int(record.get('alertman_pers_id')))
            except Exception as e:
                print(datetime.now(), f'数据回写失败，错误信息：{e}')
    del db


"""
病历回写
"""


def medical_record_writing_back(json_data):
    try:
        sql = ''
        pat_type = int(json_data.get('pat_type'))
        pat_no = int(json_data.get('pat_no'))
        if pat_type in (1, 2):
            # 门诊/急诊
            sql = f'select 病人ID as pid, NO as hid from 病人挂号记录 where 门诊号 = \'{pat_no}\' order by 登记时间 desc'
        elif pat_type == 3:
            # 住院
            sql = f'select 病人id as pid, 主页id as hid from 病案主页 where 住院号 = \'{pat_no}\' order by 主页id desc '

        param = {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": sql
        }
        data = call_third_systems_obtain_data('orcl_db_read', param)
        if data:
            record = json_data.get('record')
            body = ''
            recv_time = record.get('time').strftime("%Y-%m-%d %H:%M:%S")
            body = body + "于 " + recv_time + "接收到 " + str(record.get('alert_dept_name')) \
                   + " 推送的危机值: [" + str(record.get('cv_name')) + "]"
            body = body + " " + str(record.get('cv_result'))
            if record.get('cv_unit'):
                body = body + " " + record.get('cv_unit')

            if record.get('nurse_recv_name') and record.get('nurse_recv_time'):
                body = body + "护士 " + record.get('nurse_recv_name') + " 于 " + record.get('nurse_recv_time').strftime(
                    "%Y-%m-%d %H:%M:%S") + "接收了危机值"

            body = body + " 医生 " + json_data.get('handler_name') + " " + json_data.get('timer') + "处理了该危机值"
            if json_data.get('analysis'):
                body = body + " 原因分析: " + json_data.get('analysis')
            if json_data.get('method'):
                body = body + " 处理方法: " + json_data.get('method')
            pid = data[0].get('PID', 0)
            hid = data[0].get('HID', 0)

            # 转换审核时间
            dt = datetime.strptime(json_data.get('timer'), "%Y-%m-%d %H:%M:%S")
            review_time = dt.strftime("%Y.%m.%d %H:%M:%S")
            param = {
                "type": "his_procedure",
                "procedure": "jk_p_Pat_List",
                "病人id": pid,
                "主页id": hid,
                "内容": body,
                "分类": "3",
                "记录人": json_data.get('handler_name'),
                "审核时间": review_time,
                "医嘱ID": "",
                "医嘱名称": record.get('cv_name'),
                "分类名": "危机值记录",
                "标签说明": record.get('cv_name'),
                "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC"
            }
            call_third_systems_obtain_data('his_procedure', param)
        else:
            print(datetime.now(), '未找到病人信息，无法回写病历数据 pat_no = ', pat_no)
    except Exception as e:
        print(datetime.now(), "病历回写异常 = ", e)


"""
统计报表
query_by： 
- dept        根据科室/病区查询报表
- alert_dept  根据医技科室查询报表
- cv_source     根据危急值类型查询报表
"""


def report_form(json_data):
    start_time = json_data.get("start_time")
    end_time = json_data.get("end_time")
    patient_type = json_data.get("patient_type")
    query_by = json_data.get("query_by")

    if not query_by:
        raise Exception('query_by 参数不能为空, 请刷新重试')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    time_condition = ''
    if start_time and end_time:
        time_condition = f' WHERE time BETWEEN \'{start_time}\' AND \'{end_time}\' '

    ptype = ''
    if patient_type:
        ptype = f' AND patient_type = {int(patient_type)} '

    if query_by == 'dept':
        # 根据处理科室/病区查询
        query_sql = f'SELECT ' \
                    f'max(dept_id) AS id, ' \
                    f'dept_name AS name, ' \
                    f"1 type, 'dept' query_by, " \
                    f'COUNT(*) AS total_cv_count, ' \
                    f'SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) AS handled_count, ' \
                    f'SUM(CASE WHEN (handle_time IS NULL and state != 0) THEN 1 ELSE 0 END) AS handled_undo_count, ' \
                    f'SUM(CASE WHEN is_timeout = 1 and state != 0 THEN 1 ELSE 0 END) AS handled_timeout_count, ' \
                    f'ROUND((SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_rate, ' \
                    f'ROUND((SUM(CASE WHEN (is_timeout = 1 and state != 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_timeout_rate ' \
                    f'FROM nsyy_gyl.cv_info {time_condition} {ptype} GROUP BY dept_name ' \
                    f'UNION ALL ' \
                    f'SELECT ' \
                    f'max(ward_id) AS id, ' \
                    f'ward_name AS name, ' \
                    f"2 type, 'dept' query_by, " \
                    f'COUNT(*) AS total_cv_count, ' \
                    f'SUM(CASE WHEN nurse_recv_time IS NOT NULL OR (nurse_recv_time IS NULL AND handle_time IS NOT NULL) OR state = 0 THEN 1 ELSE 0 END ) AS handled_count, ' \
                    f'SUM(CASE WHEN nurse_recv_time IS NULL AND handle_time IS NULL AND state != 0 THEN 1 ELSE 0 END ) AS handled_undo_count, ' \
                    f'SUM(CASE WHEN is_timeout = 1 AND state != 0 THEN 1 ELSE 0 END) AS handled_timeout_count, ' \
                    f'ROUND((SUM(CASE WHEN nurse_recv_time IS NOT NULL OR (nurse_recv_time IS NULL AND handle_time IS NOT NULL) OR state = 0 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_rate, ' \
                    f'ROUND((SUM(CASE WHEN (is_timeout = 1 and state != 0) THEN 1 ELSE 0 END ) / COUNT(*)) * 100, 2) AS handling_timeout_rate ' \
                    f'FROM nsyy_gyl.cv_info {time_condition} {ptype} GROUP BY ward_name '
    elif query_by == 'alert_dept':
        # 根据上报科室查询
        query_sql = f"SELECT max(alert_dept_id) AS id, alert_dept_name AS name, 'alert_dept' query_by, " \
                    f'COUNT(*) AS total_cv_count, ' \
                    f'SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) AS handled_count, ' \
                    f'SUM(CASE WHEN (handle_time IS NULL and state != 0) THEN 1 ELSE 0 END) AS handled_undo_count, ' \
                    f'SUM(CASE WHEN is_timeout = 1 and state != 0 THEN 1 ELSE 0 END) AS handled_timeout_count, ' \
                    f'ROUND((SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_rate, ' \
                    f'ROUND((SUM(CASE WHEN (is_timeout = 1 and state != 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_timeout_rate ' \
                    f'FROM nsyy_gyl.cv_info {time_condition} GROUP BY alert_dept_name '
    elif query_by == 'cv_source':
        # 根据危急值类型查询
        query_sql = f"SELECT cv_source AS id, 'cv_source' query_by, " \
                    f'CASE ' \
                    f"WHEN cv_source = 2 THEN '检验系统' " \
                    f"WHEN cv_source = 3 THEN '影像系统' " \
                    f"WHEN cv_source = 4 THEN '心电图系统' " \
                    f"WHEN cv_source = 5 THEN '床旁血糖' " \
                    f"WHEN cv_source = 10 THEN '手工上报' " \
                    f"ELSE '未知来源' " \
                    f"END AS name , " \
                    f'COUNT(*) AS total_cv_count, ' \
                    f'SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) AS handled_count, ' \
                    f'SUM(CASE WHEN (handle_time IS NULL and state != 0) THEN 1 ELSE 0 END) AS handled_undo_count, ' \
                    f'SUM(CASE WHEN is_timeout = 1 and state != 0 THEN 1 ELSE 0 END) AS handled_timeout_count, ' \
                    f'ROUND((SUM(CASE WHEN (state = 9 or state = 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_rate, ' \
                    f'ROUND((SUM(CASE WHEN (is_timeout = 1 and state != 0) THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS handling_timeout_rate ' \
                    f'FROM nsyy_gyl.cv_info {time_condition} GROUP BY cv_source '
    else:
        raise Exception('query_by 参数错误, 无法处理 ', query_by)

    report = db.query_all(query_sql)
    del db

    report = sorted(report, key=lambda x: (x['handling_rate'], x['handling_timeout_rate']))
    return report


"""
病历模版
"""


def medical_record_template(json_data):
    cv_id = json_data.get('cv_id')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.cv_info where cv_id = \'{}\' '.format(cv_id)
    cv = db.query_one(query_sql)
    del db

    templete = []
    templete.append('危机值报告处理记录')
    if cv:
        time = cv.get('time').strftime("%Y-%m-%d %H:%M:%S")
        templete.append("于 " + time + "接收到 " + str(cv.get('alert_dept_name')) +
                        " 推送的危机值, 检查项目: " + str(cv.get('cv_name')) +
                        " 危机值: " + str(cv.get('cv_result')) + " " + str(cv.get('cv_unit')))
        if cv.get('analysis'):
            string = "原因分析： "
            string = string + cv.get("analysis")
            templete.append(string)
        if cv.get('method'):
            string = "处理办法： "
            string = string + cv.get("method")
            templete.append(string)
        templete.append("医师签名：")
    return templete


"""
数据回传
"""


def data_feedback(cv_id, cv_source, confirmer, timer, confirm_info, type: int):
    datal = []
    updatel = []
    datel = []
    intl = []
    if type == 1:
        # 护士确认
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN": confirmer, "HISCHECKDT": timer,
                  "HISCHECKINFO": confirm_info}]
        updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO"]
        datel = ["HISCHECKDT"]
    elif type == 2:
        # 医生确认
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN": confirmer, "HISCHECKDT": timer,
                  "HISCHECKINFO": confirm_info}]
        updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO"]
        datel = ["HISCHECKDT"]
    elif type == 3:
        # 医生处理
        datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN1": confirmer, "HISCHECKDT1": timer,
                  "HISCHECKINFO1": confirm_info}]
        updatel = ["HISCHECKMAN1", "HISCHECKDT1", "HISCHECKINFO1"]
        datel = ["HISCHECKDT1"]

    if cv_source == 2:
        table_name = "inter_lab_resultalert"
    else:
        table_name = "NS_EXT.PACS危急值上报表"
    param = {
        "type": "orcl_db_update",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "table_name": table_name,
        "datal": datal,
        "updatel": updatel,
        "datel": datel,
        "intl": intl,
        "keyl": ["RESULTALERTID"]
    }

    call_third_systems_obtain_data('data_feedback', param)


"""
心电系统数据回写
"""


def xindian_data_feedback(json_data):
    try:
        cv_id = json_data.get('cv_id')
        doc_id = json_data.get('doc_id')
        doc_name = json_data.get('doc_name')
        body = json_data.get('body')
        param = "<Root>" \
                f"<repGuid>{cv_id}</repGuid>" \
                f"<HandleDoctorCode>{doc_id}</HandleDoctorCode>" \
                f"<HandleDoctorName>{doc_name}</HandleDoctorName>" \
                f"<HandleDoctorNote>{body}</HandleDoctorNote>" \
                "</Root>"

        client = Client('http://192.168.3.43:8082?wsdl')
        res = client.service.SendCriricalHandelInfo(param)
        # 关闭客户端对象
        client.options.cache.clear()  # 清除缓存
        return res
    except Exception as e:
        print(datetime.now(), "心电系统数据回写失败, cv_id = ", cv_id, " 异常： ", e)
        return ''


"""
pacs 系统数据回写
"""


def pacs_data_feedback(json_data):
    # 数据库连接信息
    server = '192.168.3.53'
    database = 'VisionCenter'
    username = 'jiekou'
    password = 'jiekou'

    conn, cursor = None, None
    try:
        # 建立数据库连接
        conn = pymssql.connect(server, username, password, database)
        cursor = conn.cursor()

        main_key = json_data.get('cv_id')  # BG号 报告号
        doctor = json_data.get('doc_name')  # 处理医生
        wjzjg = json_data.get('body')  # 处理结果
        clsj = json_data.get('handle_time')  # 处理时间

        # 调用存储过程
        cursor.callproc('sp_wjz_jg', (main_key, doctor, wjzjg, clsj))
        conn.commit()
    except Exception as e:
        print(datetime.now(), "PACS 数据回写失败, cv_id = ", main_key, " 异常： ", e)
    finally:
        # 关闭连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
    db.execute(insert_sql, need_commit=True)
    del db

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_recv'], timeoutd.get('nurse_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['nurse_send'], timeoutd.get('nurse_send_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_recv'], timeoutd.get('doctor_recv_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['doctor_handle'], timeoutd.get('doctor_handle_timeout'))
    redis_client.set(cv_config.TIMEOUT_REDIS_KEY['total'], timeoutd.get('total_timeout'))


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
    sited = {'dept_phone': json_data.get('dept_phone'), 'ward_phone': json_data.get('ward_phone'),
             'doctor_phone': json_data.get('doctor_phone'), 'site_ip': json_data.get('site_ip')}

    if json_data.get('site_dept_id') and json_data.get('site_dept'):
        sited['site_dept_id'] = json_data.get('site_dept_id')
        sited['site_dept'] = json_data.get('site_dept')
    if json_data.get('site_ward_id') and json_data.get('site_ward'):
        sited['site_ward_id'] = json_data.get('site_ward_id')
        sited['site_ward'] = json_data.get('site_ward')

    if json_data.get('deptl'):
        dept_idl = [item.get('dept_id') for item in json_data.get('deptl')]
        sited['site_dept_id'] = ','.join(map(str, dept_idl))
        dept_namel = [item.get('dept_name') for item in json_data.get('deptl')]
        sited['site_dept'] = ','.join(dept_namel)
    if json_data.get('wardl'):
        ward_idl = [item.get('ward_id') for item in json_data.get('wardl')]
        sited['site_ward_id'] = ','.join(map(str, ward_idl))
        ward_namel = [item.get('ward_name') for item in json_data.get('wardl')]
        sited['site_ward'] = ','.join(ward_namel)

    if 'site_dept_id' not in sited:
        sited['site_dept_id'] = ''
        sited['site_dept'] = ''
    if 'site_ward_id' not in sited:
        sited['site_ward_id'] = ''
        sited['site_ward'] = ''

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    keys = ','.join(sited.keys())
    values = tuple(sited.values())
    # 将键和值按指定格式拼接成字符串
    key_string = ', '.join([f"{key} = {repr(value)}" for key, value in sited.items()])

    # 存在则更新 不存在则插入
    insert_sql = f'INSERT INTO nsyy_gyl.cv_site({keys}) VALUE {str(values)} ON DUPLICATE KEY UPDATE {key_string} '
    db.execute(insert_sql, need_commit=True)
    del db

    redis_client = redis.Redis(connection_pool=pool)
    if sited.get('site_dept_id'):
        deptl = sited.get('site_dept_id')
        deptl = str(deptl).split(',')
        for dept in deptl:
            key = cv_config.CV_SITES_REDIS_KEY[2].format(str(dept))
            redis_client.sadd(key, sited['site_ip'])

    if sited.get('site_ward_id'):
        ward_idl = sited.get('site_ward_id')
        ward_idl = str(ward_idl).split(',')
        for ward in ward_idl:
            key = cv_config.CV_SITES_REDIS_KEY[1].format(str(ward))
            redis_client.sadd(key, sited['site_ip'])


def query_alert_dept_list():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = 'select alert_dept_id, alert_dept_name from nsyy_gyl.cv_info GROUP BY alert_dept_id, alert_dept_name'
    dept_list = db.query_all(query_sql)
    del db
    return dept_list


# 更新危机值模版
def update_cv_template():
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 加载危机值模版
    query_sql = f'select * from nsyy_gyl.cv_template'
    cv_template = db.query_all(query_sql)
    del db
    for t in cv_template:
        redis_client.hset(cv_config.CV_TEMPLATE_REDIS_KEY, t['id'], json.dumps(t, default=str))


# 查询危机值模版
def query_cv_template(key):
    redis_client = redis.Redis(connection_pool=pool)
    data = redis_client.hgetall(cv_config.CV_TEMPLATE_REDIS_KEY)
    all_template = []
    for _, value in data.items():
        all_template.append(json.loads(value))

    if key is not None:
        return [item for item in all_template if key in item.get("cv_name", "")
                or key in item.get("cv_result", "")
                or key in item.get("cv_result_abb", "")
                or key in item.get("cv_result_pinyin_abb", "")
                or key in str(item.get("cv_source", ""))]

    return all_template

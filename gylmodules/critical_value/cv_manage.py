from gylmodules import global_config
from gylmodules.critical_value.critical_value import call_third_systems_obtain_data
from gylmodules.medical_record_analysis.record_parse import progress_note_parse, cv_record_parse
from gylmodules.utils.db_utils import DbUtil
import requests
import json
from datetime import datetime

"""
校验危急值数量
"""


def check_crisis_value_count(json_data):
    if not json_data:
        raise Exception("json_data is None")
    if not json_data.get("start_dt"):
        raise Exception("start_dt is None")

    start_dt = json_data.get("start_dt")
    # 查询中间表中的危急值
    ora_dt_condation = f" ALERTDT > to_date('{start_dt}', 'yyyy-mm-dd hh24:mi:ss')"
    mysql_dt_condation = f" time > '{start_dt}' "
    if json_data.get("end_dt"):
        end_dt = json_data.get("end_dt")
        ora_dt_condation = f" ALERTDT BETWEEN to_date('{start_dt}', 'yyyy-mm-dd hh24:mi:ss') " \
                           f"AND to_date('{end_dt}', 'yyyy-mm-dd hh24:mi:ss')"
        mysql_dt_condation = f" time BETWEEN '{start_dt}' AND '{end_dt}' "
    param = {
        "type": "orcl_db_read",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"SELECT inter_lab_resultalert.*, 2 AS \"cv_source\"  FROM inter_lab_resultalert WHERE {ora_dt_condation}"
    }
    lis_cv = call_third_systems('orcl_db_read', param)
    if not lis_cv:
        lis_cv = []

    param = {
        "type": "orcl_db_read",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"SELECT * FROM NS_EXT.PACS危急值上报表 WHERE {ora_dt_condation}"
    }
    oth_cv = call_third_systems('orcl_db_read', param)
    if not oth_cv:
        oth_cv = []

    # 所有远程危急值
    remote_cv = lis_cv + oth_cv
    remote_dict = {}
    for cv in remote_cv:
        remote_dict[cv['RESULTALERTID'] + '_' + str(cv['cv_source'])] = cv

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"SELECT * FROM nsyy_gyl.cv_info where {mysql_dt_condation} "
    local_cv = db.query_all(query_sql)
    del db

    remote_cv_set = [cv['RESULTALERTID'] + '_' + str(cv['cv_source']) for cv in remote_cv]
    local_cv_set = [cv['cv_id'] + '_' + str(cv['cv_source']) for cv in local_cv]

    # 是否有遗漏的危急值未抓取到
    miss_cvs = list(set(remote_cv_set) - set(local_cv_set))

    miss_list = []
    if miss_cvs:
        # print('遗漏危急值：', miss_cvs)
        for cv_key in miss_cvs:
            misscv = remote_dict.get(cv_key)
            if misscv:
                if misscv.get('REQ_DEPTNO') and not misscv.get('REQ_DEPTNO').isdigit():
                    continue
                flag = misscv.get('VALIDFLAG') if misscv.get('VALIDFLAG') else 0
                if int(flag) == 0:
                    continue
                # 过滤社区门诊/康复中医院
                if misscv['REQ_DEPTNO'] and misscv['REQ_DEPTNO'].isdigit() and \
                        (int(misscv['REQ_DEPTNO']) == 462 or int(misscv['REQ_DEPTNO']) == 1000760 or
                         str(misscv['REQ_DEPTNO']) == '0812' or str(misscv['REQ_DEPTNO']) == '08012'):
                    continue
                miss_list.append(misscv)
    return miss_list


# data = check_crisis_value_count({
#     "start_dt": "2024-03-01 11:11:11",
#     "end_dt": "2024-08-13 11:11:11"
# })
#
# for d in data:
#     print(d)


"""
从病历中抓取 危急值报告处理记录 （近三天）
"""


def fetch_cv_record():
    print(datetime.now(), '===> Start 开始抓取并解析危急值报告处理记录')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # db = DbUtil('192.168.3.12', 'gyl', '123456', global_config.DB_DATABASE_GYL)

    query_sql = f"select * from nsyy_gyl.cv_info where alertdt >= DATE_SUB(NOW(), INTERVAL 3 DAY) " \
                f"and (record is NULL or record = '') " \
                f"and patient_type in (1, 2, 3) " \
                f"and patient_treat_id not in ('0', '120') and state != 0 order by alertdt"
    cvs = db.query_all(query_sql)
    # 住院危急值
    zy_patient = [item for item in cvs if item['patient_type'] == 3]
    # print('住院危急值患者共 ', len(zy_patient), ' 人')
    zy_patient_dict = {}
    for item in zy_patient:
        if item['patient_treat_id'] not in zy_patient_dict:
            zy_patient_dict[item['patient_treat_id']] = []
        zy_patient_dict[item['patient_treat_id']].append(item)

    for patient_treat_id, cv_list in zy_patient_dict.items():
        records = get_zy_cv_records(patient_treat_id)
        # print('患者 ', patient_treat_id, ' 出现 ', len(cv_list), '次危急值， 查询到 ', len(records), ' 条记录')
        # 未找到病历
        if not records:
            continue
        cv_info_dict = {}
        for rec in records:
            info = progress_note_parse.parse_cv_by_str(rec.get('CONTENT'))
            if info:
                cv_info_dict.update(info)
        if not cv_info_dict:
            continue
        sorted_dict = dict(sorted(cv_info_dict.items()))

        for cv in cv_list:
            alertdt = cv.get('alertdt')
            alertdt = alertdt.strftime("%Y%m%d%H%M%S")
            # print('患者信息: ', cv.get('patient_name'), cv.get('patient_treat_id'), alertdt)
            # print('危急值信息: ', cv_info_dict)
            for k, v in sorted_dict.items():
                if len(k) == 12:
                    k = k + '00'
                if alertdt <= k:
                    # print('update', k, cv.get('id'))
                    update_sql = "UPDATE nsyy_gyl.cv_info SET record = '{}', record_time = '{}' WHERE id = {}"\
                        .format(v, k, cv.get('id'))
                    db.execute(update_sql, need_commit=True)
                    break

    # 门急诊危急值
    mz_patient = [item for item in cvs if item['patient_type'] == 1 or item['patient_type'] == 2]
    mz_patient_dict = {}
    for item in mz_patient:
        if item['patient_treat_id'] not in mz_patient_dict:
            mz_patient_dict[item['patient_treat_id']] = []
        mz_patient_dict[item['patient_treat_id']].append(item)

    for patient_treat_id, cv_list in mz_patient_dict.items():
        records = get_mz_cv_records(patient_treat_id)
        # print('患者 ', patient_treat_id, ' 出现 ', len(cv_list), '次危急值， 查询到 ', len(records), ' 条记录')
        # 未找到病历
        if not records:
            continue
        cv_info_dict = {}
        for rec in records:
            info = cv_record_parse.parse_cv_by_str(rec.get('CONTENT'))
            if info:
                cv_info_dict.update(info)
        if not cv_info_dict:
            continue
        sorted_dict = dict(sorted(cv_info_dict.items()))

        for cv in cv_list:
            alertdt = cv.get('alertdt')
            alertdt = alertdt.strftime("%Y%m%d%H%M%S")
            # print('患者信息: ', cv.get('patient_name'), cv.get('patient_treat_id'), alertdt)
            # print('危急值信息: ', cv_info_dict)
            for k, v in sorted_dict.items():
                if len(k) == 12:
                    k = k + '00'
                if alertdt <= k:
                    # print('update', k, cv.get('id'))
                    update_sql = "UPDATE nsyy_gyl.cv_info SET record = '{}', record_time = '{}' WHERE id = {}"\
                        .format(v, k, cv.get('id'))
                    db.execute(update_sql, need_commit=True)
                    break

    print(datetime.now(), '===> End 抓取并解析危急值报告处理记录完成')
    del db


# # =========================  查询病历


def get_zy_cv_records(patient_treat_id):
    return call_third_systems({
        "type": "orcl_db_read", "db_source": "nsbingli",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "clob": ['CONTENT'],
        "sql": f"""
                    select * from (select * from (Select b.病人id, g.姓名, g.住院号, b.主页id,
                                           t.title      文档名称,
                                           t.creat_time 创建时间,
                                           t.edit_time  编辑时间,
                                           t.content.getclobval() content
                                      From Bz_Doc_Log t
                                      left join Bz_Act_Log a  on a.Id = t.Actlog_Id
                                      left join 病人变动记录@HISINTERFACE b on a.extend_tag = 'BD_' || to_char(b.id)
                                      join 病案主页@HISINTERFACE g on b.病人ID = g.病人ID and b.主页ID = g.主页ID
                                     where t.title like '%病程记录%') order by 创建时间)
                     where 编辑时间 >= sysdate - 3 and 住院号 = {patient_treat_id}
                """
    })


def get_mz_cv_records(patient_treat_id):
    return call_third_systems({
        "type": "orcl_db_read", "db_source": "nsbingli",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "clob": ['CONTENT'],
        "sql": f"""
                    Select b.病人id,  b.姓名, b.门诊号, a.extend_tag,
                               t.title      文档名称,
                               t.creat_time 创建时间,
                               t.edit_time  编辑时间,
                               t.content.getclobval() content
                          From Bz_Doc_Log t
                          join Bz_Act_Log a on a.Id = t.Actlog_Id
                          join 病人挂号记录@HISINTERFACE b on a.extend_tag = 'MZ_' || to_char(b.id)
                         where t.title like '%危急值报告处理记录%' and t.edit_time >= sysdate - 3 and 门诊号 = {patient_treat_id}
                """
    })


def call_third_systems(param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            data = []
            print('调用第三方系统方法失败：type = orcl_db_read ' + ' param = ' + str(param) + "   " + e.__str__())
    else:
        # 根据住院号/门诊号查询 病人id 主页id
        from tools import orcl_db_read
        try:
            data = orcl_db_read(param)
        except Exception as e:
            data = []
            print('调用第三方系统方法失败：type = orcl_db_read ' + ' param = ' + str(param) + "   " + e.__str__())

    return data





# fetch_cv_record()


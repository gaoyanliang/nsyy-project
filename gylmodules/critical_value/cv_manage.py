import logging

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils import DbUtil
import requests
import json
from datetime import datetime

logger = logging.getLogger(__name__)


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
            logger.error(f'调用第三方系统方法失败：type = orcl_db_read {param}, {e}')
    else:
        # 根据住院号/门诊号查询 病人id 主页id
        from tools import orcl_db_read
        try:
            data = orcl_db_read(param)
        except Exception as e:
            data = []
            logger.error(f'调用第三方系统方法失败：type = orcl_db_read {param}, {e}')

    return data


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
    lis_cv = call_third_systems(param)
    if not lis_cv:
        lis_cv = []

    param = {
        "type": "orcl_db_read",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"SELECT * FROM NS_EXT.PACS危急值上报表 WHERE {ora_dt_condation}"
    }
    oth_cv = call_third_systems(param)
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
    logger.info('开始抓取并解析危急值报告处理记录')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # db = DbUtil('192.168.3.12', 'gyl', '123456', global_config.DB_DATABASE_GYL)

    query_sql = f"select * from nsyy_gyl.cv_info where alertdt >= DATE_SUB(NOW(), INTERVAL 3 DAY) " \
                f"and (record is NULL or record = '') " \
                f"and patient_type in (1, 2, 3) " \
                f"and patient_treat_id not in ('0', '120') and state != 0 order by alertdt"
    cvs = db.query_all(query_sql)

    for cv in cvs:
        if not cv.get('patient_treat_id'):
            continue
        try:
            records = query_cv_medical_record(int(cv['patient_type']), cv.get('patient_treat_id'))
        except Exception as e:
            logger.error(f"抓取危急值报告处理记录失败：cv_id = {cv.get('cv_id')}, {cv.get('patient_treat_id')}, {e}")
            records = []
        if not records:
            continue
        record = records[0]
        for r in records:
            if cv.get('cv_name') in r[1] and cv.get('cv_result') in r[1]:
                record = r

        # 解析日期字符串
        date_object = datetime.strptime(record[0], "%a, %d %b %Y %H:%M:%S %Z")
        record_time = date_object.strftime("%Y-%m-%d %H:%M:%S")
        update_sql = "UPDATE nsyy_gyl.cv_info SET record = '{}', record_time = '{}' WHERE id = {}" \
            .format(record[1], record_time, cv.get('id'))
        db.execute(update_sql, need_commit=True)

    logger.info('End 抓取并解析危急值报告处理记录完成')
    del db


# # =========================  查询病历

def query_cv_medical_record(patient_type, patient_id):
    sql = f"""
        SELECT t2.bingrenid AS 病人ID, t.xingming AS 姓名, t.zhuyuanhao AS 住院号, t.zhuyuancs AS 主页id, 
        t2.bingrenzyid AS 病人住院ID, t2.binglimc AS 文档名称, t2.chuangjiansj AS "创建时间", t2.jilusj AS 编辑时间,
        t3.wenjiannr AS "CONTENT" FROM df_bingli.ws_binglijl t2 JOIN df_bingli.ws_binglijlnr t3
        ON t2.binglijlid = t3.binglijlid LEFT JOIN df_jj_zhuyuan.zy_bingrenxx t ON t2.bingrenzyid = t.bingrenzyid
        WHERE t2.binglimc = '危急值报告处置记录' AND t2.zuofeibz = 0 AND t2.menzhenzybz = 2
        AND t.zhuyuanhao = '{patient_id}' AND t2.jilusj >= sysdate - 3 order by t2.chuangjiansj desc
    """
    if patient_type != 3:
        sql = f"""
            SELECT t2.bingrenid AS 病人ID, t.xingming AS 姓名, t2.jiuzhenid AS 就诊ID, t2.binglimc AS 文档名称, 
            t2.chuangjiansj AS "创建时间", t2.jilusj AS 编辑时间, t3.wenjiannr AS "CONTENT", 
            t.jiuzhenkh, a.jiuzhenkh, b.jiuzhenkh FROM df_bingli.ws_binglijl t2 
            JOIN df_bingli.ws_binglijlnr t3 ON t2.binglijlid = t3.binglijlid
            LEFT JOIN df_bingrenzsy.gy_bingrenxx t ON t2.bingrenid = t.bingrenid LEFT JOIN df_lc_menzhen.zj_jiuzhenxx a 
            ON t2.jiuzhenid = a.jiuzhenid LEFT JOIN df_jj_menzhen.mz_guahao b 
            ON a.guahaoid = b.guahaoid WHERE t2.binglimc = '危急值报告处置记录'
            AND t2.zuofeibz = 0 AND t2.menzhenzybz = 1
            AND (a.jiuzhenkh = '{patient_id}' or a.bingrenid = '{patient_id}' or a.jiuzhenid = '{patient_id}')
        """
    data = global_tools.call_new_his(sql, ['CONTENT'])
    if not data:
        return []
    ret_data = []
    for d in data:
        sentence = parse_xml_to_sentence(d.get('CONTENT'))
        ret_data.append((d.get('编辑时间'), sentence))

    return ret_data


def parse_xml_to_sentence(xml_string):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_string)

    # 提取XML中的关键信息
    patient_info = {
        'name': root.find('.//node[@name="患者姓名"]').text,
        'critical_value_nr': root.find('.//node[@name="报告内容"]').text,
        'critical_value_advice': root.find('.//node[@name="危急值处理医嘱"]').text,
        'communication_situation': root.find('.//node[@name="沟通情况"]').text
    }
    # 拼接成一句话
    sentence = (
        f"患者 {patient_info['name']}，"
        f"危急值内容: {patient_info['critical_value_nr']}，"
        f"沟通情况为: {patient_info['communication_situation']}，"
        f"危急值处理医嘱: {patient_info['critical_value_advice']}"
    )
    return sentence



# fetch_cv_record()


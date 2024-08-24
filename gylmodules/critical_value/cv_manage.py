from gylmodules import global_config
from gylmodules.critical_value.critical_value import call_third_systems_obtain_data
from gylmodules.utils.db_utils import DbUtil

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
    lis_cv = call_third_systems_obtain_data('orcl_db_read', param)
    if not lis_cv:
        lis_cv = []

    param = {
        "type": "orcl_db_read",
        "db_source": "ztorcl",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"SELECT * FROM NS_EXT.PACS危急值上报表 WHERE {ora_dt_condation}"
    }
    oth_cv = call_third_systems_obtain_data('orcl_db_read', param)
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

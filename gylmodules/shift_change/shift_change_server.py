import json
import logging
import time
import traceback
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Dict, List

from gylmodules import global_config, global_tools
from gylmodules.shift_change import shift_change_config
from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def delete_shift_data(record_id):
    """删除科室交接班数据 患者信息"""
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(f"delete from nsyy_gyl.scs_patients where id = {record_id}", need_commit=True)
    del db


def query_shift_change_date(json_data):
    """查询科室交接班数据"""
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    shift_date = json_data.get('shift_date')
    dept_id = json_data.get('dept_id')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if int(shift_type) == 1:
        # 医生交接班
        shift_classes = f"{shift_type}-{shift_classes}"
        shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                                  f"and shift_classes = '{shift_classes}' and dept_id = {dept_id} and archived = 1")
        is_archived = [shift_classes] if shift_info else []

        query_sql = f"select * from nsyy_gyl.scs_patients where shift_date = '{shift_date}' " \
                    f"and shift_classes = '{shift_classes}' and patient_dept_id = {dept_id}"
        patients = db.query_all(query_sql)

        count_info = db.query_all(f"select * from nsyy_gyl.scs_patient_count where shift_date = '{shift_date}' "
                                  f"and shift_classes = '{shift_classes}' and patient_dept_id = {dept_id}")
        patient_count = {"1": {}, "2": {}, "3": {}}
        for item in count_info:
            patient_count[item['shift_classes'].split("-")[1]][item.get('patient_type')] = item.get('count')
        patient_bed_info = []
    else:
        # 护士交接班
        shift_classes = f"{shift_type}-{shift_classes}"
        classes_list = ['2-1']
        if shift_classes.endswith('-3'):
            classes_list = ['2-1', '2-2', '2-3']
        elif shift_classes.endswith('-2'):
            classes_list = ['2-1', '2-2']

        classes_str = ', '.join(f"'{item}'" for item in classes_list)
        query_sql = f"select * from nsyy_gyl.scs_patients where shift_date = '{shift_date}' " \
                    f"and patient_ward_id = {dept_id} and shift_classes in ({classes_str})"
        patients = db.query_all(query_sql)

        patient_count_list = db.query_all(f"select * from nsyy_gyl.scs_patient_count where shift_date = '{shift_date}' "
                                          f" and patient_ward_id = {dept_id}")

        shift_info_list = db.query_all(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}'"
                                       f" and dept_id = {dept_id} and archived = 1")

        is_archived = []
        shift_info = {"1": {}, "2": {}, "3": {}}
        for item in shift_info_list:
            is_archived.append(item['shift_classes'])
            shift_info[item['shift_classes'].split("-")[1]] = json.loads(item.get('shift_info')) \
                if item.get('shift_info') else {}

        patient_count = {"1": {}, "2": {}, "3": {}}
        for item in patient_count_list:
            patient_count[item['shift_classes'].split("-")[1]][item.get('patient_type')] = item.get('count')

        if shift_classes.endswith('-3'):
            patient_bed_info = db.query_all(
                f"select * from nsyy_gyl.scs_patient_bed_info where shift_date = '{shift_date}'"
                f"and shift_classes = '{shift_classes}' and patient_ward_id = {dept_id}")

            default_bed_info = shift_change_config.default_bed_info_list.copy()
            for item in patient_bed_info:
                default_bed_info.pop(item.get('patient_type'))
            if patient_bed_info:
                patient_bed_info = patient_bed_info + [v for k, v in default_bed_info.items()]
            else:
                patient_bed_info = [v for k, v in default_bed_info.items()]
        else:
            patient_bed_info = []

        total = {}
        # 遍历所有分项
        for key, values in patient_count.items():
            # 只处理非空字典
            if isinstance(values, dict) and values:
                for k, v in values.items():
                    if k in ['特护', '一级护理', '病危', '病重', '现有']:
                        total[k] = v
                    else:
                        total[k] = total.get(k, 0) + v
        patient_count['0'] = total

    del db

    patients = merge_ret_patient_list(patients, is_archived)

    def get_patient_type_key(patient):
        """返回用于排序的元组：(类型1优先级, 类型2优先级, ..., bed_no)"""
        types = [t.strip() for t in patient['patient_type'].split(',')]
        priorities = [PATIENT_TYPE_ORDER.get(t, float('inf')) for t in types]
        max_types = 14  # 假设最多14个类型
        priorities += [float('inf')] * (max_types - len(priorities))
        return tuple(priorities + [int(patient['bed_no'])])

    sorted_patients = sorted(patients, key=get_patient_type_key)
    return {
        'patient_count': patient_count,
        'patient_bed_info': patient_bed_info,
        'patients': sorted_patients,
    }


def merge_ret_patient_list(patient_list, is_archived):
    """
    护理交接班返回的时候 全天的交班记录合并返回
    合并同一患者的不同班次记录
    :param patient_list:
    :param is_archived:
    :return:
    """

    # 使用defaultdict分组存储患者记录
    patients = defaultdict(lambda: {
        'records': [],  # 存储该患者所有记录
        'latest_record': None  # 存储最新记录
    })

    # 1. 按患者分组并找出最新记录
    for record in patient_list:
        patient_id = record['zhuyuanhao']
        patients[patient_id]['records'].append(record)

        # 更新最新记录（根据create_at时间判断）
        if (patients[patient_id]['latest_record'] is None or
                record['id'] > patients[patient_id]['latest_record']['id']):
            patients[patient_id]['latest_record'] = record

    # 2. 构建合并后的结果
    merged = []
    for patient_id, data in patients.items():
        latest = data['latest_record']

        # 初始化patient_info结构
        patient_info = {'1': None, '2': None, '3': None}

        # 填充各班次信息
        types = []
        for record in data['records']:
            types.append(record.get('patient_type'))
            shift_class = record['shift_classes'].split('-')[1]
            patient_info[shift_class] = {'id': record['id'], 'info': record['patient_info'],
                                         'is_archived': 1 if record['shift_classes'] in is_archived else 0}

        types = ','.join(types).replace(' ', '')

        items = types.split(',')
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        types = ','.join(result)
        # 创建合并后的记录
        merged_record = latest.copy()
        merged_record['patient_info'] = patient_info
        merged_record['patient_type'] = types
        merged.append(merged_record)
        types = []

    return merged


def update_shift_change_data(json_data):
    """更新/新增交接班患者数据"""
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = int(json_data.get('patient_dept_id')) if json_data.get('patient_dept_id') else int(
        json_data.get('patient_ward_id'))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{json_data.get('shift_date')}' "
                    f"and dept_id = {dept_id} and shift_classes = '{shift_classes}' and archived = 1"):
        del db
        raise Exception("该班次已归档无法在修改或新增数据")

    if 'id' in json_data:
        # 更新交班数据
        set_condition = []
        for key, value in json_data.items():
            if key in ['zhenduan', 'patient_type', 'doctor_name', 'patient_info']:
                set_condition.append(f"{key} = '{value}'")
        sql = f"UPDATE nsyy_gyl.scs_patients SET {','.join(set_condition)} where id = {json_data.get('id')}"
        args = ()
    else:

        sql = f"""INSERT INTO nsyy_gyl.scs_patients(shift_date, shift_classes, bingrenzyid, zhuyuanhao, bed_no, 
                        patient_name, patient_sex, patient_age, zhenduan, patient_type, patient_dept_id, patient_dept,
                        patient_ward_id, patient_ward, doctor_name, patient_info, create_at) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        args = (json_data.get('shift_date'), f"{json_data.get('shift_type')}-{json_data.get('shift_classes')}",
                json_data.get('bingrenzyid', ''),
                json_data.get('zhuyuanhao', ''), json_data.get('bed_no', ''), json_data.get('patient_name', ''),
                json_data.get('patient_sex', ''), json_data.get('patient_age', ''), json_data.get('zhenduan', ''),
                json_data.get('patient_type'), json_data.get('patient_dept_id', '0'),
                json_data.get('patient_dept', '0'), json_data.get('patient_ward_id'), json_data.get('patient_ward'),
                json_data.get('doctor_name'), json_data.get('patient_info'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    db.execute(sql, args, need_commit=True)
    del db


def update_shift_change_bed_data(json_data):
    """
    更新或新增交班床位信息
    :param json_data:
    :return:
    """
    if 'id' in json_data:
        # 更新交班数据
        set_condition = []
        for key, value in json_data.items():
            if key in ['patient_type', 'patient_info']:
                set_condition.append(f"{key} = '{value}'")
        sql = f"UPDATE nsyy_gyl.scs_patient_bed_info SET {','.join(set_condition)} where id = {json_data.get('id')}"
        args = ()
    else:
        sql = f"""INSERT INTO nsyy_gyl.scs_patient_bed_info(shift_date, shift_classes, patient_type, 
                        patient_ward_id, patient_ward, patient_info, create_at) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        args = (json_data.get('shift_date'), f"2-{json_data.get('shift_classes')}",
                json_data.get('patient_type'), json_data.get('patient_ward_id'), json_data.get('patient_ward'),
                json_data.get('patient_info'), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(sql, args, need_commit=True)
    del db


def query_patient_info(zhuyuanhao):
    """
    根据住院号查询患者信息
    :param zhuyuanhao:
    :return:
    """
    sql = f"""select zb.xingming patient_name, zb.dangqiancwbm bed_no, zb.zhuyuanhao zhuyuanhao, 
    zb.xingbiemc patient_sex, zb.nianling patient_age, zb.bingrenzyid, zb.zhuzhiysxm doctor_name from
	df_jj_zhuyuan.zy_bingrenxx zb where zb.zaiyuanzt = 0 and zb.quxiaorybz = 0 and zb.yingerbz = 0
	and zb.zhuyuanhao = '{zhuyuanhao}'"""

    patient_info_list = global_tools.call_new_his_pg(sql)
    return patient_info_list[0] if patient_info_list else {}


# ============================= 查询交接班数据 =============================

def postoperative_situation(shift_classes, dept_list, zhuyuanhao_list):
    if int(shift_classes) != 3 or not zhuyuanhao_list:
        return []

    ydhl_dept_list = []
    for did in dept_list:
        if shift_change_config.ydhl_dept_dict.get(str(did)):
            ydhl_dept_list.append(shift_change_config.ydhl_dept_dict.get(str(did)))

    dept_str = ', '.join(f"'{item}'" for item in ydhl_dept_list)
    bingrenzyid_str = ', '.join(f"'{item}'" for item in zhuyuanhao_list)

    sql = """select zy.bingrenzyid "住院id",zy.bed_no 床号,zy.dept_name 所在病区,dnr.illness_measures 患者情况
            from kyeecis.docs_normal_report_rec dnr join kyeecis.V_HIS_PATS_IN_HOSPITAL zy 
            on dnr.patient_id=zy.patient_id and dnr.visit_id=zy.visit_id and dept_code in ({dept_code}) 
            and bingrenzyid in ({bingrenzyid}) where dnr.time_point = trunc(sysdate)+ 7/24
            and dnr.theme_code like '%一般护理记录单%' and dnr.enabled_value = 'Y'
            """
    sql = sql.replace('{dept_code}', dept_str)
    sql = sql.replace('{bingrenzyid}', bingrenzyid_str)

    start_time = time.time()
    result = global_tools.call_new_his(sql=sql, sys='ydhl', clobl=None)
    logger.info(f"术后信息查询: 术后数量 {len(result)} 执行时间: {time.time() - start_time} s")
    return result


def discharge_situation():
    sql = """select 住院号,疾病转归 from (select report_id,住院号,疾病转归 from (
    select t2.item_name, t2.item_value, t.report_id from kyeecis.docs_eval_report_rec t
    join kyeecis.docs_eval_report_detail_rec t2  on t.report_id = t2.report_id
    where t2.item_name in ('疾病转归', '住院号') and t2.enabled_value = 'Y' and t.theme_code = '出院小结'
    and t.create_time > sysdate - 1) pivot (max(item_value) 
    for item_name in ('疾病转归' as 疾病转归, '住院号' as 住院号))) where 疾病转归 is not null"""
    start_time = time.time()
    result = global_tools.call_new_his(sql=sql, sys='ydhl', clobl=None)
    logger.info(f"出院信息查询：数量 {len(result)} 执行时间: {time.time() - start_time} s")
    if not result:
        return None
    result = {item.get('住院号'): '自动' if str(item.get('疾病转归', '')).strip() == '自动出院' else str(
        item.get('疾病转归', '')) for item in result}
    return result


def doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list, flush: bool = False):
    """
    医生交接班数据查询
    :param reg_sqls:
    :param shift_classes:
    :param time_slot:
    :param dept_id_list:
    :return:
    """
    start_time = time.time()
    shift_start, shift_end = get_complete_time_slot(time_slot)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}'"
    all_cvs = db.query_all(query_sql)
    del db

    patients, patient_count = [], []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 查询医生交接班 患者数据
        tasks = {
            "patients": executor.submit(timed_execution, "医生交接班数据查询 1 ", global_tools.call_new_his_pg,
                                        reg_sqls.get(1).get('sql_nhis').replace("{start_time}", shift_start)
                                        .replace("{end_time}", shift_end)),
            "patient_count": executor.submit(timed_execution, "医生交接班人数查询 2 ", global_tools.call_new_his_pg,
                                             reg_sqls.get(2).get('sql_nhis')
                                             .replace("{start_time}", shift_start).replace("{end_time}", shift_end))
        }
        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patients = results["patients"]
        patient_count = results["patient_count"]

    filtered_patients = [dept for dept in patients if dept['所在科室id'] in dept_id_list]
    filtered_patient_count = [dept for dept in patient_count if dept['所在科室id'] in dept_id_list]
    all_patients = merge_patient_cv_data(all_cvs, filtered_patients, 1, dept_id_list)
    if flush:
        patient_count_list = []
    else:
        patient_count_list = fill_missing_types(filtered_patient_count, shift_change_config.dept_people_count, 1)
    save_data(f"1-{shift_classes}", all_patients, patient_count_list, None)
    logger.info(f"医生交接班数据查询完成 ✅ 总耗时 {time.time() - start_time} 秒")


def aicu_shift_change(reg_sqls, shift_classes, time_slot, shoushu, flush: bool = False):
    """
    AICU 1000965 CCU 1001120  交班信息查询
    :param reg_sqls:
    :param shift_classes:
    :param time_slot:
    :return:
    """
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id in (1000965, 1001120)"
    all_cvs = db.query_all(query_sql)
    del db

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, pg_patients, \
        ydhl_patients, shuhou_patients = [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "AICU/CCU 患者人数统计 1 ",
                                             global_tools.call_new_his_pg, reg_sqls.get(5).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "teshu_patients": executor.submit(timed_execution, "AICU/CCU 出院转出死亡患者情况 2 ",
                                              global_tools.call_new_his_pg, reg_sqls.get(14).get('sql_nhis')
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end)),
            "pg_patients": executor.submit(timed_execution, "AICU/CCU 护理单元患者情况 pg 5 ",
                                           global_tools.call_new_his_pg, reg_sqls.get(15).get('sql_base')
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)),
            "ydhl_patients": executor.submit(timed_execution, "AICU/CCU 护理单元患者情况 ydhl 6 ",
                                             global_tools.call_new_his, reg_sqls.get(15).get('sql_ydhl')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end), 'ydhl', None)
        }
        if int(shift_classes) == 3:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "AICU/CCU 特殊患者床位信息 3 ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(8).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "AICU/CCU 特殊患者床位信息 4 ",
                                                       global_tools.call_new_his, reg_sqls.get(8).get('sql_ydhl'),
                                                       'ydhl', None)
            if shoushu:
                tasks["shuhou_patients"] = executor.submit(postoperative_situation, 3, ['1000965', '1001120'],
                                                           [item.get('bingrenzyid') for item in shoushu])

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]
        shuhou_patients = results.get("shuhou_patients", [])

    start_time = time.time()
    all_patient_info = teshu_patients if teshu_patients else []

    # 分组
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    if ydhl_patient.get("转入时间") == patient.get("转入时间"):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1001120', "所在病区": 'AICU/CCU护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000965", "1001120"])
    all_patients = merge_patient_shuhou_data(shuhou_patients, all_patients, shoushu)
    if flush:
        patient_count = []
    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"AICU/CCU 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


def ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu, flush: bool = False):
    """
    妇产科 1000961 交班信息查询
    :param reg_sqls:
    :param shift_classes:
    :param time_slot:
    :return:
    """
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id = 1000961"
    all_cvs = db.query_all(query_sql)
    del db

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, pg_patients, \
        ydhl_patients, shuhou_patients = [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "妇产科患者人数统计 1 ",
                                             global_tools.call_new_his_pg, reg_sqls.get(7).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "teshu_patients": executor.submit(timed_execution, "妇产科 出院转出死亡患者情况 2 ",
                                              global_tools.call_new_his_pg, reg_sqls.get(16).get('sql_nhis')
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end)),
            "pg_patients": executor.submit(timed_execution, "妇产科 护理单元患者情况 pg 5 ",
                                           global_tools.call_new_his_pg, reg_sqls.get(17).get('sql_base')
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)),
            "ydhl_patients": executor.submit(timed_execution, "妇产科 护理单元患者情况 ydhl 6 ",
                                             global_tools.call_new_his, reg_sqls.get(17).get('sql_ydhl')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end), 'ydhl', None)
        }
        if int(shift_classes) == 3:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "妇产科 特殊患者床位信息 3 ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(9).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "妇产科 特殊患者床位信息 4 ",
                                                       global_tools.call_new_his, reg_sqls.get(9).get('sql_ydhl'),
                                                       'ydhl', None)
            if shoushu:
                tasks["shuhou_patients"] = executor.submit(postoperative_situation, 3, ['1000961'],
                                                           [item.get('bingrenzyid') for item in shoushu])

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]
        shuhou_patients = results.get("shuhou_patients", [])

    all_patient_info = teshu_patients if teshu_patients else []

    # 分组
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                tmp_info = tmp_info + (
                    str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000961', "所在病区": '妇产科护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count + ['顺生'], 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000961"])
    all_patients = merge_patient_shuhou_data(shuhou_patients, all_patients, shoushu)
    if flush:
        patient_count = []
    save_data(f"2-{shift_classes}", all_patient_info, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"妇产科 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


def icu_shift_change(reg_sqls, shift_classes, time_slot, flush: bool = False):
    """
    重症科室 1000962 交班信息查询
    :param reg_sqls:
    :param shift_classes:
    :param time_slot:
    :return:
    """
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id = 1000962"
    all_cvs = db.query_all(query_sql)
    del db

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, temp_patients = [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "重症科室 患者人数统计 1 ",
                                             global_tools.call_new_his_pg, reg_sqls.get(6).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "teshu_patients": executor.submit(timed_execution, "重症科室 出院转出死亡患者情况 2 ",
                                              global_tools.call_new_his_pg, reg_sqls.get(18).get('sql_nhis')
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end)),
            # "temp_patients": executor.submit(timed_execution, "AICU/CCU 护理单元患者情况 5 ",
            #                                  global_tools.call_new_his_pg, reg_sqls.get(15).get('sql_base')
            #                                  .replace("{start_time}", shift_start)
            #                                  .replace("{end_time}", shift_end))
        }
        if int(shift_classes) == 3:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "重症科室 特殊患者床位信息 3 ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(10).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "重症科室 特殊患者床位信息 4 ",
                                                       global_tools.call_new_his, reg_sqls.get(10).get('sql_ydhl'),
                                                       'ydhl',
                                                       None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        # temp_patients = results["temp_patients"]

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000962', "所在病区": 'ICU护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, teshu_patients, 2, ["1000962"])
    if flush:
        patient_count = []
    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"重症科室 交接班数据查询完成 ✅ 耗时: {time.time() - start}")


def general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list, shoushu, flush: bool = False):
    """
    普通科室交接班数据查询
    :param reg_sqls:
    :param shift_classes:
    :param time_slot:
    :param dept_list:
    :return:
    """
    if not dept_list:
        return
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}'"
    all_cvs = db.query_all(query_sql)
    del db

    patient_count, siwang_patients, chuangwei_info1, chuangwei_info2, \
        teshu_ydhl_patients, teshu_pg_patients, ydhl_patients, pg_patients, \
        eye_pg_patients, eye_ydhl_patients, shuhou_patients, chuyuan_ydhl = [], [], [], [], [], [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=12) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "普通病区 患者人数统计 1 ",
                                             global_tools.call_new_his_pg, reg_sqls.get(3).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "siwang_patients": executor.submit(timed_execution, "普通病区 出院转出死亡患者情况 2 ",
                                               global_tools.call_new_his_pg, reg_sqls.get(11).get('sql_nhis')
                                               .replace("{start_time}", shift_start)
                                               .replace("{end_time}", shift_end)),
            "teshu_ydhl_patients": executor.submit(timed_execution, "普通病区 患者信息(特殊处理) ydhl 5 ",
                                                   global_tools.call_new_his, reg_sqls.get(13).get('sql_ydhl')
                                                   .replace("{start_time}", shift_start)
                                                   .replace("{end_time}", shift_end),
                                                   'ydhl', ['患者情况']),
            "teshu_pg_patients": executor.submit(timed_execution, "普通病区 患者信息(特殊处理) pg 6",
                                                 global_tools.call_new_his_pg, reg_sqls.get(13).get('sql_nhis')
                                                 .replace("{start_time}", shift_start)
                                                 .replace("{end_time}", shift_end)
                                                 .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "pg_patients": executor.submit(timed_execution, "普通病区 患者信息 pg 7",
                                           global_tools.call_new_his_pg, reg_sqls.get(12).get('sql_base')
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)
                                           .replace("{特殊病区}",
                                                    """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元','眼科护理单元'""")
                                           .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "ydhl_patients": executor.submit(timed_execution, "普通病区 患者信息 ydhl 8",
                                             global_tools.call_new_his, reg_sqls.get(12).get('sql_ydhl')
                                             .replace("{特殊病区}",
                                                      """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元','眼科护理单元'""")
                                             .replace("{start_time}", shift_start).replace("{end_time}", shift_end)
                                             , 'ydhl', None),
            "eye_pg_patients": executor.submit(timed_execution, "眼科病区 患者信息 pg 9",
                                               global_tools.call_new_his_pg, reg_sqls.get(19).get('sql_base')
                                               .replace("{start_time}", shift_start)
                                               .replace("{end_time}", shift_end)),
            "eye_ydhl_patients": executor.submit(timed_execution, "眼科病区 患者信息 ydhl 10",
                                                 global_tools.call_new_his, reg_sqls.get(19).get('sql_ydhl')
                                                 .replace("{start_time}", shift_start).replace("{end_time}", shift_end)
                                                 , 'ydhl', None),
            "chuyuan_ydhl": executor.submit(discharge_situation)

        }
        if int(shift_classes) == 3:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 3 ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(4).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 4 ",
                                                       global_tools.call_new_his, reg_sqls.get(4).get('sql_ydhl'),
                                                       'ydhl', None)
            if shoushu:
                dept_set = set()
                for item in shoushu:
                    dept_set.add(item.get('patient_ward_id'))
                tasks["shuhou_patients"] = executor.submit(postoperative_situation, 3, list(dept_set),
                                                           [item.get('bingrenzyid') for item in shoushu])


        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        siwang_patients = results["siwang_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        teshu_ydhl_patients = results["teshu_ydhl_patients"]
        teshu_pg_patients = results["teshu_pg_patients"]
        ydhl_patients = results["ydhl_patients"]
        pg_patients = results["pg_patients"]
        eye_pg_patients = results["eye_pg_patients"]
        eye_ydhl_patients = results["eye_ydhl_patients"]
        shuhou_patients = results.get("shuhou_patients", [])
        chuyuan_ydhl = results["chuyuan_ydhl"]

    if chuyuan_ydhl:
        for patient in siwang_patients:
            if patient.get('患者类别') == '出院':
                patient['患者情况'] = patient['患者情况'].replace('###', chuyuan_ydhl.get(patient.get('住院号'), ''))

    all_patient_info = siwang_patients
    teshu_pg_patient_dict = {}
    for patient in teshu_pg_patients:
        teshu_pg_patient_dict[patient['bingrenzyid']] = patient
    for item in teshu_ydhl_patients:
        p = teshu_pg_patient_dict.get(item.get('bingrenzyid'))
        if not p:
            continue
        p['患者情况'] = item.get('患者情况', '')
        all_patient_info.append(p)

    # 分组
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    if ydhl_patient.get("所在病区") == patient.get("所在病区"):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    groups = defaultdict(list)
    for patient in eye_ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in eye_pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    if ydhl_patient.get("所在病区") == patient.get("所在病区"):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                elif patient.get("患者类别") == '入院':
                    split_info = tmp_info.split('###')
                    if len(split_info) == 1:
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                    else:
                        tmp_info = split_info[0] + str(ydhl_patient.get("患者情况", '')).replace('***', split_info[1])
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    filtered_patient_count = [dept for dept in patient_count if dept['所在病区id'] in dept_list]
    patient_count_list = fill_missing_types(filtered_patient_count, shift_change_config.ward_people_count, 2)

    chuangwei_info_list = chuangwei_info1 + chuangwei_info2
    for item in chuangwei_info_list:
        item['所在病区id'] = str(shift_change_config.his_dept_dict.get(item['所在病区'], ''))
    filtered_chuangwei_info = [dept for dept in chuangwei_info_list if dept['所在病区id'] in dept_list]

    filtered_patients = [dept for dept in all_patient_info if dept['所在病区id'] in dept_list]
    all_patients = merge_patient_cv_data(all_cvs, filtered_patients, 2, dept_list)
    all_patients = merge_patient_shuhou_data(shuhou_patients, all_patients, shoushu)
    if flush:
        patient_count_list = []
    save_data(f"2-{shift_classes}", all_patients, patient_count_list, filtered_chuangwei_info)
    logger.info(f"普通科室 通用交接班数据查询完成 ✅ 耗时: {time.time() - start}")


def get_complete_time_slot(shift_slot: str) -> tuple:
    """根据输入的时间段返回完整的开始和结束时间"""
    start_str, end_str = shift_slot.split('-')
    start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
    end_time = datetime.strptime(end_str.strip(), '%H:%M').time()

    # 获取当前日期
    today = datetime.now().date()

    # 判断是否需要跨天
    if start_time < end_time:
        # 同一天内
        start_datetime = datetime.combine(today, start_time)
        end_datetime = datetime.combine(today, end_time)
    else:
        # 跨天情况（开始时间是前一天）
        start_datetime = datetime.combine(today - timedelta(days=1), start_time)
        end_datetime = datetime.combine(today, end_time)

    return f"{start_datetime.strftime('%Y-%m-%d %H:%M')}:01.000", f"{end_datetime.strftime('%Y-%m-%d %H:%M')}:00.999"


def merge_patient_records(patient_list):
    """
    合并相同患者的记录（根据shift_date, shift_classes, zhuyuanhao, ward_id）
    合并规则：
    - patient_type 用逗号连接
    - patient_info 用换行符连接
    - 其他字段保留第一条记录的值
    """

    patient_list = sorted(patient_list, key=lambda x: PATIENT_TYPE_ORDER.get(x[9], float('inf')))

    # 使用复合键分组
    def key_func(x):
        # shift_date, shift_classes, zhuyuanhao, ward_id
        return (x[0], x[1], x[3], x[12])

    # 分组s
    groups = defaultdict(list)
    for patient in patient_list:
        groups[key_func(patient)].append(patient)

    merged_records = []
    # 合并每组记录
    for group_key, patients in groups.items():
        if len(patients) == 1:
            merged_records.append(patients[0])
            continue

        # 合并字段
        base_patient = patients[0]

        # 合并patient_type（去重）
        types = {p[9] for p in patients if p[9]}
        sorted_types = sorted(types, key=lambda x: PATIENT_TYPE_ORDER.get(x, float('inf')))
        merged_type = ', '.join(sorted_types) if sorted_types else base_patient[9]

        # 按时间排序后合并info
        try:
            sorted_patients = sorted(patients,
                                     key=lambda x: datetime.strptime(x[16], '%Y-%m-%d %H:%M:%S'))
            merged_info = '\n\n--------\n\n'.join(f"{p[15]}" for p in sorted_patients if p[15])
            latest_time = sorted_patients[-1][16]
        except (IndexError, ValueError) as e:
            logger.warning(f"处理记录时出错: {e}")
            merged_info = "合并记录时发生错误"
            latest_time = base_patient[16]

        # 构建合并后的新元组（保持原始结构）
        base_patient = (
            base_patient[0],  # shift_date
            base_patient[1],  # shift_classes
            base_patient[2],  # bingrenzyid
            base_patient[3],  # zhuyuanhao
            base_patient[4],  # bed_no
            base_patient[5],  # patient_name
            base_patient[6],  # patient_sex
            base_patient[7],  # patient_age
            base_patient[8],  # zhenduan
            merged_type,  # patient_type (合并后)
            base_patient[10],  # patient_dept_id
            base_patient[11],  # patient_dept
            base_patient[12],  # patient_ward_id
            base_patient[13],  # patient_ward
            base_patient[14],  # doctor_name
            merged_info,  # patient_info (合并后)
            latest_time  # create_at (取最新)
        )
        merged_records.append(base_patient)

    return merged_records


def query_cv_zhenduan(zhuyuanhao_list):
    start_time = time.time()
    id_list = ','.join(f"'{zhuyuanhao}'" for zhuyuanhao in zhuyuanhao_list)
    sql = f"""
    select zb.zhuyuanhao 住院号,case when (xpath('string(//node[@name="初步诊断"])', 
    wb2.wenjiannr::xml))[1]::text ~ '2[\.、]' then regexp_replace((xpath('string(//node[@name="初步诊断"])', 
    wb2.wenjiannr::xml))[1]::text, '2[\.、].*$', '\1') else (xpath('string(//node[@name="初步诊断"])', 
    wb2.wenjiannr::xml))[1]::text end as 主要诊断 from df_bingli.ws_binglijl wb 
    join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid
    join df_jj_zhuyuan.zy_bingrenxx zb on zb.bingrenzyid=wb.bingrenzyid and zb.zaiyuanzt=0 and zb.rukebz=1 
    and zb.yingerbz=0 and zb.quxiaorybz=0 where wb.binglimc = '首次病程记录'  and wb.zuofeibz=0 and wb.wenshuzt=2
    and zb.zhuyuanhao in ({id_list})
    """
    ret = global_tools.call_new_his_pg(sql)
    if not ret:
        return {}
    ret = {str(r.get("住院号")): r.get('主要诊断', '') for r in ret}
    logger.info(f"查询危机值数据完成 ✅ 耗时: {time.time() - start_time}")
    return ret


def merge_patient_cv_data(cv_list, patient_list, shift_type, dept_list):
    """
    合并交接班危机值数据
    :param cv_list:
    :param patient_list:
    :param shift_type:
    :param dept_list:
    :return:
    """
    try:
        if not cv_list or not patient_list:
            return patient_list

        # 查询危机值患者诊断
        zhuyuanhao_list = [str(cv.get('patient_treat_id')) for cv in cv_list if cv.get('patient_treat_id')]
        cv_zhenduan = query_cv_zhenduan(zhuyuanhao_list)

        cv_dict = {(str(cv.get('patient_treat_id')), str(cv.get('dept_id'))): cv for cv in cv_list if
                   cv.get('dept_id') and cv.get('patient_treat_id')}
        if int(shift_type) == 2:
            # 护理交接班
            cv_dict = {(str(cv.get('patient_treat_id')), str(cv.get('ward_id'))): cv for cv in cv_list if
                       cv.get('ward_id') and cv.get('patient_treat_id')}

        patient_dict = defaultdict(list)
        for patient in patient_list:
            key = (str(patient.get('住院号')), str(patient.get('所在病区id'))) if int(shift_type) == 2 \
                else (str(patient.get('住院号')), str(patient.get('所在科室id')))
            patient_dict[key].append(patient)

        for (zhuyuanhao, dpid), cv in cv_dict.items():
            if str(dpid) not in dept_list or not cv.get('patient_treat_id'):
                continue

            if patient_dict.get((zhuyuanhao, dpid)):
                ps = patient_dict.get((zhuyuanhao, dpid))
                ps[0]['患者类别'] = ps[0]['患者类别'] + ', 危急值'
                ps[0]['患者情况'] = ps[0]['患者情况'] + f"  {cv.get('alertdt')} 接危急值系统报 {cv.get('cv_name')} " \
                                                        f"{cv.get('cv_result') if cv.get('cv_result') else ''} {cv.get('cv_unit') if cv.get('cv_unit') else ''}, " \
                                                        f"遵医嘱给予 {cv.get('method') if cv.get('method') else ''} 处理"
            else:
                sex = '未知'
                if str(cv.get('patient_gender')) == '1':
                    sex = '男'
                if str(cv.get('patient_gender')) == '2':
                    sex = '女'

                p = {'bingrenzyid': '', '住院号': zhuyuanhao, '床号': cv.get('patient_bed_num'),
                     '姓名': cv.get('patient_name'), '性别': sex, '年龄': cv.get('patient_age'),
                     '主要诊断': cv_zhenduan.get(zhuyuanhao, ''), '患者类别': '危急值', '主治医生姓名': cv.get('req_docno'),
                     '患者情况': f"{cv.get('alertdt')} 接危急值系统报 {cv.get('cv_name')} "
                                 f"{cv.get('cv_result') if cv.get('cv_result') else ''} {cv.get('cv_unit') if cv.get('cv_unit') else ''}, "
                                 f"遵医嘱给予 {cv.get('method') if cv.get('method') else ''} 处理"
                     }
                if int(shift_type) == 1:
                    p['所在科室id'] = cv.get('dept_id') if cv.get('dept_id') else ''
                    p['所在科室'] = cv.get('dept_name') if cv.get('dept_name') else ''
                else:
                    p['所在病区id'] = cv.get('ward_id') if cv.get('ward_id') else ''
                    p['所在病区'] = cv.get('ward_name') if cv.get('ward_name') else ''
                patient_dict[(zhuyuanhao, dpid)].append(p)

        ret_list = []
        for l in patient_dict.values():
            ret_list = ret_list + l
        return ret_list
    except Exception as e:
        logger.warning(f"合并危机值数据异常: {e}")
        return patient_list


def merge_patient_shuhou_data(shuhou_list, patient_list, shoushu_list):
    """
    合并交接班术后数据
    :param shuhou_list:
    :param patient_list:
    :param shoushu_list:
    :return:
    """
    try:
        if not shuhou_list or not shoushu_list:
            return patient_list

        shuhou_dict = defaultdict(list)
        for patient in shuhou_list:
            shuhou_dict[str(patient.get('住院id'))].append(patient)
        patient_dict = defaultdict(list)
        for patient in patient_list:
            patient_dict[str(patient.get('bingrenzyid'))].append(patient)

        for patient in shoushu_list:
            if not patient.get('bingrenzyid'):
                continue

            if patient_dict.get(str(patient.get('bingrenzyid'))):
                ps = patient_dict.get(str(patient.get('bingrenzyid')))
                ps[0]['患者情况'] = str(ps[0]['患者情况']) + str(shuhou_dict.get(str(patient.get('bingrenzyid')),
                                                                                 [{}])[0].get('患者情况', ''))
            else:
                p_shuhou = shuhou_dict.get(str(patient.get('bingrenzyid')), '')
                if not p_shuhou:
                    continue

                p_shuhou = p_shuhou[0]
                p = {'bingrenzyid': patient.get('bingrenzyid'), '住院号': patient.get('zhuyuanhao'),
                     '床号': p_shuhou.get('床号', ''), '姓名': patient.get('patient_name'),
                     '性别': patient.get('patient_sex'), '年龄': patient.get('patient_age'),
                     '主要诊断': patient.get('zhenduan'), '患者类别': patient.get('patient_type'),
                     '主治医生姓名': patient.get('doctor_name'), '患者情况': p_shuhou.get('患者情况', '')
                     }

                dept_name = p_shuhou.get('所在病区', '')
                p['所在病区id'] = shift_change_config.his_dept_dict.get(dept_name, '0')
                p['所在病区'] = dept_name
                patient_dict[str(patient.get('bingrenzyid'))].append(p)

        ret_list = []
        for l in patient_dict.values():
            ret_list = ret_list + l
        return ret_list
    except Exception as e:
        logger.warning(f"合并术后数据异常: {e}")
        return patient_list


def timed_execution(log_info, func, *args):
    """带执行时间统计的函数包装器"""
    start_time = time.time()
    result = func(*args)
    logger.debug(f"{log_info} 执行时间: {time.time() - start_time} s")
    return result


def save_data(shift_classes, patients, patient_count, patient_bed_info):
    """
    持久化交接班数据
    :param shift_classes:
    :param patients:
    :param patient_count:
    :param patient_bed_info:
    :return:
    """
    today_date = datetime.now().strftime("%Y-%m-%d")
    if str(shift_classes).endswith('-3'):
        # 晚班属于前一天的交班
        today_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if patients:
        patient_list = [(today_date, shift_classes,
                         patient.get('bingrenzyid') if patient.get('bingrenzyid') else '0',
                         patient.get('住院号') if patient.get('住院号') else '0',
                         patient.get('床号') if patient.get('床号') else '0',
                         patient.get('姓名') if patient.get('姓名') else '0',
                         patient.get('性别') if patient.get('性别') else '0',
                         patient.get('年龄') if patient.get('年龄') else '0',
                         patient.get('主要诊断') if patient.get('主要诊断') else '',
                         patient.get('患者类别') if patient.get('患者类别') else '',
                         patient.get('所在科室id') if patient.get('所在科室id') else '0',
                         patient.get('所在科室') if patient.get('所在科室') else '',
                         patient.get('所在病区id') if patient.get('所在病区id') else '0',
                         patient.get('所在病区') if patient.get('所在病区') else '',
                         patient.get('主治医生姓名') if patient.get('主治医生姓名') else '',
                         patient.get('患者情况') if patient.get('患者情况') else '',
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")) for patient in patients]

        if str(shift_classes).startswith('2-'):
            patient_list = merge_patient_records(patient_list)

        # 生成插入的 SQL
        insert_sql = f"""INSERT INTO nsyy_gyl.scs_patients(shift_date, shift_classes, bingrenzyid, 
                        zhuyuanhao, bed_no, patient_name, patient_sex, patient_age, zhenduan, patient_type, 
                        patient_dept_id, patient_dept, patient_ward_id, patient_ward, doctor_name, patient_info, 
                        create_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ON DUPLICATE KEY UPDATE zhuyuanhao = VALUES(zhuyuanhao), bed_no = VALUES(bed_no), 
                        patient_name = VALUES(patient_name), patient_sex = VALUES(patient_sex), 
                        patient_age = VALUES(patient_age), zhenduan = VALUES(zhenduan), patient_type = VALUES(patient_type), 
                        patient_dept_id = VALUES(patient_dept_id), patient_dept = VALUES(patient_dept), 
                        patient_ward_id = VALUES(patient_ward_id), patient_ward = VALUES(patient_ward),
                        doctor_name = VALUES(doctor_name), patient_info = VALUES(patient_info), 
                        create_at = VALUES(create_at)"""

        db.execute_many(insert_sql, patient_list, need_commit=True)

    if patient_count:
        count_list = [(today_date, shift_classes, item.get('患者类别'),
                       item.get('所在科室id') if item.get('所在科室id') else 0,
                       item.get('所在科室') if item.get('所在科室') else '0',
                       item.get('所在病区id') if item.get('所在病区id') else 0,
                       item.get('所在病区') if item.get('所在病区') else '0',
                       item.get('人数'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for item in patient_count]
        insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_count(shift_date, shift_classes, patient_type, 
                        patient_dept_id, patient_dept, patient_ward_id, patient_ward, count, create_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE count = VALUES(count)"""
        db.execute_many(insert_sql, count_list, need_commit=True)

    if patient_bed_info:
        bed_info_list = [
            (today_date, shift_classes, item.get('患者类别'),
             shift_change_config.his_dept_dict.get(item.get('所在病区'), 0),
             item.get('所在病区'), item.get('患者信息'),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for item in patient_bed_info]
        insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_bed_info(shift_date, shift_classes, 
                        patient_type, patient_ward_id, patient_ward, patient_info, create_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) 
                        ON DUPLICATE KEY UPDATE patient_info = VALUES(patient_info)"""
        db.execute_many(insert_sql, bed_info_list, need_commit=True)
    del db


def check_shift_time(shift_slot: str) -> bool:
    """检查当前时间是否到交班时间了"""
    if not shift_slot:
        return False

    # 解析时间区间字符串
    start_str, end_str = shift_slot.split('-')
    start = datetime.strptime(start_str.strip(), '%H:%M').time()
    end = datetime.strptime(end_str.strip(), '%H:%M').time()
    if not start or not end:
        return False

    input_time = datetime.strptime(end_str, "%H:%M").time()
    now = datetime.now()
    current_time = now.time()

    # 创建时间范围（前后2分钟）
    time_min = (now - timedelta(minutes=5)).time()
    time_max = (now + timedelta(minutes=5)).time()

    # 处理跨日情况（如23:59-00:01）
    if time_min > time_max:
        # 当前时间接近午夜，范围跨越两天
        return input_time >= time_min or input_time <= time_max
    else:
        # 正常情况
        return time_min <= input_time <= time_max


def upcoming_shifts_grouped() -> Dict[Tuple[str, str], List[Dict]]:
    """获取按班次分组的即将交班的科室列表"""
    now = datetime.now().time()

    # 获取所有配置
    configs = query_shift_config()

    # 使用字典按班次类型和时间段分组
    shift_groups = defaultdict(list)

    for config in configs:
        if not config.get('shift_status'):
            continue
        # 检查早班
        if config['early_shift'] and config['early_shift_slot'] and check_shift_time(config['early_shift_slot']):
            shift_key = ('1', config['early_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

        # 检查中班
        if config['middle_shift'] and config['middle_shift_slot'] and check_shift_time(config['middle_shift_slot']):
            shift_key = ('2', config['middle_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

        # 检查晚班
        if config['night_shift'] and config['night_shift_slot'] and check_shift_time(config['night_shift_slot']):
            shift_key = ('3', config['night_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

    return shift_groups


def timed_shift_change():
    """ 定时执行交接班 """
    shift_groups = []
    try:
        shift_groups = upcoming_shifts_grouped()
    except Exception as e:
        logger.error(f"获取即将交班科室列表失败：{e}")
        return

    if not shift_groups:
        logger.info(f"没有即将交班科室")
        return

    doctor_shift_groups = defaultdict(list)
    nursing_shift_groups = defaultdict(list)

    shift_classes = 1
    # 按班次类型和时间段排序输出
    for (shift_class, time_slot), departments in sorted(shift_groups.items()):
        shift_classes = shift_class
        for dept in departments:
            if int(dept['shift_type']) == 1:
                doctor_shift_groups[time_slot].append(dept['dept_id'])
            else:
                nursing_shift_groups[time_slot].append(dept['dept_id'])

    if not doctor_shift_groups and not nursing_shift_groups:
        return

    shoushu_patients = []
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
    if int(shift_classes) == 3:
        dd = datetime.today().date() - timedelta(days=1)
        shoushu_patients = db.query_all(f"""SELECT * FROM nsyy_gyl.scs_patients WHERE 
        shift_date = '{dd.strftime('%Y-%m-%d')}' and shift_classes in ('2-1', '2-2') and patient_type like '%手术%' and
        bingrenzyid IN (SELECT bingrenzyid FROM nsyy_gyl.scs_patients where shift_date = '{dd.strftime('%Y-%m-%d')}' 
        and shift_classes in ('2-1', '2-2') and patient_type like '%手术%' GROUP BY bingrenzyid)""")
    del db
    reg_sqls = {item.get('sid'): item for item in all_sqls}

    # 抓取医生交接班数据
    if doctor_shift_groups:
        for time_slot, dept_list in doctor_shift_groups.items():
            try:
                doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list)
            except Exception as e:
                logger.warning(f"医生 {time_slot} 交班异常: {e}")

    if nursing_shift_groups:
        for time_slot, dept_list in nursing_shift_groups.items():
            if '1000961' in dept_list:
                # 妇产科
                try:
                    shoushu = [item for item in shoushu_patients if item.get('patient_ward_id') == 1000961]
                    ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu)
                except Exception as e:
                    logger.warning(f"妇产科 {time_slot} 交接班异常: {e}")

            if '1000962' in dept_list:
                # ICU 重症
                try:
                    icu_shift_change(reg_sqls, shift_classes, time_slot)
                except Exception as e:
                    logger.warning(f"重症 ICU {time_slot} 交接班异常: {e}")

            if '1000965' in dept_list or '1001120' in dept_list:
                # AICU CCU
                try:
                    shoushu = [item for item in shoushu_patients if item.get('patient_ward_id') in (1000965, 1001120)]
                    aicu_shift_change(reg_sqls, shift_classes, time_slot, shoushu)
                except Exception as e:
                    logger.warning(f"AICU/CCU {time_slot} 交接班异常: {e}")

            dept_id_list = [dept_id for dept_id in dept_list if
                            dept_id not in ['1000961', '1000962', '1000965', '1001120']]
            try:
                shoushu = [item for item in shoushu_patients if str(item.get('patient_ward_id')) in dept_id_list]
                general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list, shoushu)
            except Exception as e:
                logger.warning(f"护理 {time_slot} 交班异常: {e}")


def single_run_shift_change(json_data):
    shift_type = json_data.get('shift_type')
    shift_date = json_data.get('shift_date')
    shift_classes = json_data.get('shift_classes')
    time_slot = json_data.get('time_slot')
    dept_id = json_data.get('dept_id')
    dept_list = [str(dept_id)]

    if not dept_id:
        raise Exception("请选择科室")
    input_date = datetime.strptime(shift_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    previous_day = today - timedelta(days=1)
    if input_date != previous_day and int(shift_classes) == 3:
        raise Exception("仅支持刷新前一天的晚班")
    if input_date != today and int(shift_classes) in [1, 2]:
        raise Exception("仅支持刷新当天的早班 和 中班")

    shoushu_patients = []
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
    shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info "
                              f"where shift_classes = '{shift_type}-{shift_classes}' "
                              f"and shift_date = '{shift_date}' and dept_id = {int(dept_id)}")
    if int(shift_classes) == 3:
        dd = datetime.today().date() - timedelta(days=1)
        shoushu_patients = db.query_all(f"""SELECT * FROM nsyy_gyl.scs_patients WHERE 
        shift_date = '{dd.strftime('%Y-%m-%d')}' and shift_classes in ('2-1', '2-2') and patient_type like '%手术%' and
        bingrenzyid IN (SELECT bingrenzyid FROM nsyy_gyl.scs_patients where shift_date = '{dd.strftime('%Y-%m-%d')}' 
        and shift_classes in ('2-1', '2-2') and patient_type like '%手术%' GROUP BY bingrenzyid)""")
    del db
    reg_sqls = {item.get('sid'): item for item in all_sqls}

    try:

        if shift_type == 1:
            # 医生交接班
            doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list, True)
        elif shift_type == 2:
            if len(dept_list) == 1 and ('1000965' in dept_list or '1001120' in dept_list):
                # AICU/CCU交接班
                shoushu = [item for item in shoushu_patients if item.get('patient_ward_id') in (1000965, 1001120)]
                aicu_shift_change(reg_sqls, shift_classes, time_slot, shoushu, True)
                return
            if len(dept_list) == 1 and '1000961' in dept_list:
                # 妇产科交接班
                shoushu = [item for item in shoushu_patients if item.get('patient_ward_id') == 1000961]
                ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu, True)
                return
            if len(dept_list) == 1 and '1000962' in dept_list:
                # 重症 ICU 交接班
                icu_shift_change(reg_sqls, shift_classes, time_slot, True)
                return
            # 普通护理交接班
            shoushu = [item for item in shoushu_patients if str(item.get('patient_ward_id')) in dept_list]
            general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list, shoushu, True)
        else:
            raise Exception("未知的交接班类型")
    except Exception as e:
        logger.warning(f"{time_slot} 交班异常: {e}")


def fill_missing_types(data, dept_people_count, shift_type):
    # sql 没有统计的患者类别，人数默认为 0
    dept_map = defaultdict(dict)

    for item in data:
        key = (item['所在科室id'], item['所在科室']) if shift_type == 1 else (item['所在病区id'], item['所在病区'])
        dept_map[key][item['患者类别']] = item['人数']

    # 填充缺失的类型
    result = []
    for (dept_id, dept_name), type_count_map in dept_map.items():
        for t in dept_people_count:
            count = type_count_map.get(t, 0)
            result.append({
                "患者类别": t, "人数": count,
                "所在科室id": dept_id if shift_type == 1 else 0,
                "所在科室": dept_name if shift_type == 1 else '',
                "所在病区id": dept_id if shift_type == 2 else 0,
                "所在病区": dept_name if shift_type == 2 else '',
            })

    return result


# ============================= 交接班配置 =============================

def create_or_update_shift_config(json_data):
    """新增或者更新交接班配置"""
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if json_data.get('id'):
        args = (json_data.get('shift_type'), json_data.get('dept_id'), json_data.get('dept_name'),
                json_data.get('early_shift'), json_data.get('early_shift_slot'),
                json_data.get('middle_shift'), json_data.get('middle_shift_slot'),
                json_data.get('night_shift'), json_data.get('night_shift_slot'),
                json_data.get('shift_status'), json_data.get('id'))
        db.execute("UPDATE nsyy_gyl.scs_shift_config SET shift_type=%s, dept_id=%s, dept_name=%s, "
                   "early_shift=%s, early_shift_slot=%s, middle_shift=%s, middle_shift_slot=%s,"
                   "night_shift=%s, night_shift_slot=%s, shift_status=%s WHERE id=%s",
                   args=args, need_commit=True)
    else:
        db.execute("INSERT INTO nsyy_gyl.scs_shift_config (shift_type, dept_id, dept_name, early_shift,"
                   "early_shift_slot, middle_shift, middle_shift_slot, night_shift, night_shift_slot, "
                   "shift_status, create_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                   args=(json_data.get('shift_type'), json_data.get('dept_id'), json_data.get('dept_name'),
                         json_data.get('early_shift'), json_data.get('early_shift_slot'),
                         json_data.get('middle_shift'), json_data.get('middle_shift_slot'),
                         json_data.get('night_shift'), json_data.get('night_shift_slot'),
                         json_data.get('shift_status')), need_commit=True)
    del db


def query_shift_config():
    """查询交接班配置"""
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    shift_configs = db.query_all("select * from nsyy_gyl.scs_shift_config")
    del db
    return shift_configs


def query_shift_info(json_data):
    shift_date = json_data.get('shift_date')
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    shift_config = db.query_one(f"select * from nsyy_gyl.scs_shift_config where dept_id = '{str(dept_id)}' ")

    shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                              f"and shift_classes = '{shift_type}-{shift_classes}' and dept_id = {int(dept_id)}")
    if shift_info:
        shift_info.pop('outgoing_data')
        shift_info.pop('incoming_data')
        shift_info.pop('head_nurse_data')
    del db
    return {"bed_info_list": shift_change_config.bed_info_list,
            "patient_type_list": shift_change_config.patient_type_list,
            "dept_shift_config": shift_config,
            "shift_info": shift_info}


# ============================= 签名相关 =============================


def save_shift_info(json_data):
    """
    后端直接触发 医生/护士 签名， 随后保存签名返回信息
    :param json_data:
    :return:
    """
    shift_date = json_data.get('shift_date')
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')
    dept_name = json_data.get('dept_name')
    sign_type = json_data.get('sign_type')  # 1=交班人 2=接班人 3=护士长
    user_id = json_data.get('user_id', "")  # 医生/护士 云医签 id
    user_name = json_data.get('user_name')

    sign_img = ''
    params = (shift_date, f"{shift_type}-{shift_classes}", dept_id, dept_name, 1,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if int(sign_type) != 4:
        # 获取医生签名图片
        sign_img = get_doctor_sign_img(user_id)

        # 签名业务字段 随机生成 保证唯一即可
        biz_sn = uuid.uuid4().__str__()
        # 文件摘要
        sign_msg = f"{dept_name} - {shift_date} {shift_classes} 交班"

        if not user_id:
            raise Exception('医生/护士不存在, 请先联系信息科配置【云医签】', user_name)
        try:
            sign_param = {"type": "sign_push", "user_id": user_id, "bizSn": biz_sn, "msg": sign_msg,
                          "desc": "交接班签名"}
            sign_ret = global_tools.call_yangcheng_sign_serve(sign_param)

            # 时间戳签名
            ts_sign_param = {"sign_org": sign_msg, "type": "ts_gene"}
            ts_sign_ret = global_tools.call_yangcheng_sign_serve(ts_sign_param, ts_sign=True)
        except Exception as e:
            raise Exception('签名服务器异常', e)

        sign_data = {"sign_ret": sign_ret, "ts_sign_ret": ts_sign_ret}
        params = (shift_date, f"{shift_type}-{shift_classes}", dept_id, dept_name, user_name,
                  user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(sign_data), sign_img)

    if int(sign_type) == 1:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, 
        outgoing, outgoing_user_id, outgoing_time, outgoing_data, outgoing_img)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE outgoing = VALUES(outgoing), 
            outgoing_user_id = VALUES(outgoing_user_id), outgoing_time = VALUES(outgoing_time), 
            outgoing_data = VALUES(outgoing_data), outgoing_img = VALUES(outgoing_img)
        """
    elif int(sign_type) == 2:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, 
        incoming, incoming_user_id, incoming_time, incoming_data, incoming_img)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE incoming = VALUES(incoming), 
            incoming_user_id = VALUES(incoming_user_id), incoming_time = VALUES(incoming_time), 
            incoming_data = VALUES(incoming_data), incoming_img = VALUES(incoming_img)
        """
    elif int(sign_type) == 3:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, 
        head_nurse, head_nurse_user_id, head_nurse_time, head_nurse_data, head_nurse_img)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE head_nurse = VALUES(head_nurse), 
            head_nurse_user_id = VALUES(head_nurse_user_id), head_nurse_time = VALUES(head_nurse_time), 
            head_nurse_data = VALUES(head_nurse_data), head_nurse_img = VALUES(head_nurse_img)
        """
    elif int(sign_type) == 4:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, 
        archived, archived_time) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE archived = VALUES(archived), 
            archived_time = VALUES(archived_time) """
    else:
        raise Exception('签名类型错误 1=交班人 2=接班人 3=护士长 4=归档')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(insert_sql, params, need_commit=True)
    del db
    return sign_img


def get_doctor_sign_img(user_id):
    """
    获取医生签名图片，如果是首次签名，从云医签中获取签名
    :param user_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    record = db.query_one(f"select * from nsyy_gyl.scs_doc_sign_img where user_id = '{user_id}'")
    if record:
        del db
        return record.get('sign_img')

    img_base64 = global_tools.fetch_yun_sign_img(user_id)
    sign_img = None
    if img_base64:
        sign_img = global_tools.upload_sign_file(img_base64, is_pdf=False)

    if not sign_img:
        raise Exception('云医签获取签名图片失败, 请先配置云医签')

    db.execute("insert into nsyy_gyl.scs_doc_sign_img (user_id, sign_img) values (%s, %s)",
               (user_id, sign_img), need_commit=True)
    del db

    return sign_img

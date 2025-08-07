import json
import logging
import time
import traceback
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
        shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                                  f"and shift_classes = '{shift_classes}' and dept_id = {dept_id}")
        shift_info = shift_info.get('shift_info') if shift_info else {}
        # 医生交接班
        shift_classes = f"{shift_type}-{shift_classes}"
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
        query_sql = f"select * from nsyy_gyl.scs_patients where shift_date = '{shift_date}' " \
                    f"and shift_classes = '{shift_classes}' and patient_ward_id = {dept_id}"
        patients = db.query_all(query_sql)

        patient_count_list = db.query_all(f"select * from nsyy_gyl.scs_patient_count where shift_date = '{shift_date}' "
                                          f" and patient_ward_id = {dept_id}")

        shift_info_list = db.query_all(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}'"
                                       f" and dept_id = {dept_id}")

        is_archived = []
        shift_info = {"1": {}, "2": {}, "3": {}}
        for item in shift_info_list:
            is_archived.append(f"2-{item['shift_classes']}")
            shift_info[item['shift_classes']] = json.loads(item.get('shift_info')) if item.get('shift_info') else {}

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
                    total[k] = total.get(k, 0) + v
        patient_count['0'] = total

    del db

    patients = merge_ret_patient_list(patients, is_archived)
    sorted_patients = sorted(patients, key=lambda x: (x['patient_type'], x['bed_no']))
    return {
        'patient_count': patient_count,
        'patient_bed_info': patient_bed_info,
        'patients': sorted_patients,
        'shift_info': shift_info
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
        patient_id = record['bingrenzyid']
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
        for record in data['records']:
            shift_class = record['shift_classes'].split('-')[1]
            patient_info[shift_class] = {'id': record['id'], 'info': record['patient_info'],
                                         'is_archived': 1 if record['shift_classes'] in is_archived else 0}

        # 创建合并后的记录
        merged_record = latest.copy()
        merged_record['patient_info'] = patient_info
        merged.append(merged_record)

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
                    f"and dept_id = {dept_id} and shift_classes = '{shift_classes}' "):
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


def submit_shift_change(json_data):
    """
    提交本班次的交接班数据
    :param json_data:
    :return:
    """
    insert_sql = f"""INSERT INTO nsyy_gyl.scs_shift_info(shift_date, shift_classes, dept_id, dept_name, shift_info,  
                    create_at) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE shift_date = VALUES(shift_date), 
                    shift_classes = VALUES(shift_classes), dept_id = VALUES(dept_id), dept_name = VALUES(dept_name), 
                    create_at = VALUES(create_at)"""
    args = (json_data.get('shift_date'), json_data.get('shift_classes'), json_data.get('dept_id'),
            json_data.get('dept_name'), json.dumps(json_data.get('shift_info'), default=str, ensure_ascii=False),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(insert_sql, args, need_commit=True)
    del db


# ============================= 查询交接班数据 =============================


def doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list):
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

    patient_count_list = fill_missing_types(filtered_patient_count, shift_change_config.dept_people_count, 1)
    save_data(f"1-{shift_classes}", all_patients, patient_count_list, None)
    logger.info(f"医生交接班数据查询完成 ✅ 总耗时 {time.time() - start_time} 秒")


def aicu_shift_change(reg_sqls, shift_classes, time_slot):
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

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, pg_patients, ydhl_patients = [], [], [], [], [], []
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
                                                       'ydhl',
                                                       None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]

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
                              "所在病区id": 1001120, "所在病区": 'CCU/AICU护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000965", "1001120"])
    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"AICU/CCU 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


def ob_gyn_shift_change(reg_sqls, shift_classes, time_slot):
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

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, pg_patients, ydhl_patients = [], [], [], [], [], []
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
                                               global_tools.call_new_his, reg_sqls.get(9).get('sql_ydhl'), 'ydhl',
                                               None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]

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
                              "所在病区id": 1000961, "所在病区": '妇产科护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count + ['顺生'], 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000961"])
    save_data(f"2-{shift_classes}", all_patient_info, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"妇产科 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


def icu_shift_change(reg_sqls, shift_classes, time_slot):
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
                                               global_tools.call_new_his, reg_sqls.get(10).get('sql_ydhl'), 'ydhl',
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
                              "所在病区id": 1000962, "所在病区": 'ICU护理单元'})
        patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, teshu_patients, 2, ["1000962"])
    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2)
    logger.info(f"重症科室 交接班数据查询完成 ✅ 耗时: {time.time() - start}")


def general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list):
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
        teshu_ydhl_patients, teshu_pg_patients, ydhl_patients, pg_patients = [], [], [], [], [], [], [], []
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
                                                   'ydhl', None),
            "teshu_pg_patients": executor.submit(timed_execution, "普通病区 患者信息(特殊处理) pg 6",
                                                 global_tools.call_new_his_pg, reg_sqls.get(13).get('sql_nhis')
                                                 .replace("{start_time}", shift_start)
                                                 .replace("{end_time}", shift_end)
                                                 .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "pg_patients": executor.submit(timed_execution, "普通病区 患者信息 pg 7",
                                           global_tools.call_new_his_pg, reg_sqls.get(12).get('sql_base')
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)
                                           .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "ydhl_patients": executor.submit(timed_execution, "普通病区 患者信息 ydhl 8",
                                             global_tools.call_new_his, reg_sqls.get(12).get('sql_ydhl')
                                             .replace("{start_time}", shift_start).replace("{end_time}", shift_end)
                                             , 'ydhl', None)

        }
        if int(shift_classes) == 3:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 3 ",
                                               global_tools.call_new_his_pg, reg_sqls.get(4).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 4 ",
                                               global_tools.call_new_his, reg_sqls.get(4).get('sql_ydhl'), 'ydhl',
                                               None)

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

    patient_count_list = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)
    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, dept_list)
    save_data(f"2-{shift_classes}", all_patients, patient_count_list, chuangwei_info1 + chuangwei_info2)
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

    return start_datetime.strftime('%Y-%m-%d %H:%M:%S'), end_datetime.strftime('%Y-%m-%d %H:%M:%S')


def merge_patient_records(patient_list):
    """
    合并相同患者的记录（根据shift_date, shift_classes, zhuyuanhao, ward_id）
    合并规则：
    - patient_type 用逗号连接
    - patient_info 用换行符连接
    - 其他字段保留第一条记录的值
    """

    # 使用复合键分组
    def key_func(x):
        # shift_date, shift_classes, zhuyuanhao, ward_id
        return (x[0], x[1], x[3], x[12])

    # 分组
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
            merged_info = '\n\n--------\n\n'.join(
                f"{p[16]}:\n{p[15]}"
                for p in sorted_patients
                if p[15]
            )
            latest_time = sorted_patients[-1][16]
        except (IndexError, ValueError) as e:
            logger.warning(f"处理记录时出错: {e}")
            merged_info = "合并记录时发生错误"
            latest_time = base_patient[16]

        # 构建合并后的新元组（保持原始结构）
        merged_patient = (
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
                patient.get('bingrenzyid') if patient.get('bingrenzyid') else '0',
                patient.get('住院号') if patient.get('住院号') else '0',
                patient.get('床号') if patient.get('床号') else '0',
                patient.get('姓名') if patient.get('姓名') else '0',
                patient.get('性别') if patient.get('性别') else '0',
                patient.get('年龄') if patient.get('年龄') else '0',
                patient.get('主要诊断') if patient.get('主要诊断') else '',
                patient.get('患者类别') if patient.get('患者类别') else '',
                patient.get('所在科室id') if patient.get('所在科室id') else '',
                patient.get('所在科室') if patient.get('所在科室') else '',
                patient.get('所在病区id') if patient.get('所在病区id') else '',
                patient.get('所在病区') if patient.get('所在病区') else '',
                patient.get('主治医生姓名') if patient.get('主治医生姓名') else '',
                patient.get('患者情况') if patient.get('患者情况') else '',

                sex = '未知'
                if str(cv.get('patient_gender')) == 1:
                    sex = '男'
                if str(cv.get('patient_gender')) == 2:
                    sex = '女'

                patient_dict[(zhuyuanhao, dpid)].append({
                    'bingrenzyid': '',
                    '住院号': zhuyuanhao,
                    '床号': cv.get('patient_bed_num'),
                    '姓名': cv.get('patient_name'),
                    '性别': sex,
                    '年龄': cv.get('patient_age'),
                    '主要诊断': '',
                    '患者类别': '危急值',
                    '所在科室id': cv.get('dept_id') if cv.get('dept_id') else '',
                    '所在科室': cv.get('dept_name') if cv.get('dept_name') else '',
                    '所在病区id': cv.get('ward_id') if cv.get('ward_id') else '',
                    '所在病区': cv.get('ward_name') if cv.get('ward_name') else '',
                    '主治医生姓名': cv.get('req_docno'),
                    '患者情况': f"  {cv.get('alertdt')} 接危急值系统报 {cv.get('cv_name')} "
                                f"{cv.get('cv_result') if cv.get('cv_result') else ''} {cv.get('cv_unit') if cv.get('cv_unit') else ''}, "
                                f"遵医嘱给予 {cv.get('method') if cv.get('method') else ''} 处理"
                })

        ret_list = []
        for l in patient_dict.values():
            ret_list = ret_list + l
        return ret_list
    except Exception as e:
        logger.warning(f"合并危机值数据异常: {e}")
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
            (today_date, shift_classes, item.get('患者类别'), shift_change_config.his_dept_dict.get(item.get('所在病区'), 0),
             item.get('所在病区'), item.get('患者信息'),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for item in patient_bed_info]
        insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_bed_info(shift_date, shift_classes, 
                        patient_type, patient_ward_id, patient_ward, patient_info, create_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) 
                        ON DUPLICATE KEY UPDATE patient_info = VALUES(patient_info)"""
        db.execute_many(insert_sql, bed_info_list, need_commit=True)
    del db


def check_shift_time(shift_slot: str) -> bool:
    """检查当前时间是否在交班前20分钟内"""
    if not shift_slot:
        return False

    # 解析时间区间字符串
    start_str, end_str = shift_slot.split('-')
    start = datetime.strptime(start_str.strip(), '%H:%M').time()
    end = datetime.strptime(end_str.strip(), '%H:%M').time()
    if not start or not end:
        return False

    # 计算交班前20分钟的时间窗口
    end_dt = datetime.combine(datetime.today(), end)
    reminder_time = (end_dt - timedelta(minutes=20)).time()

    return reminder_time <= datetime.now().time() <= end


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
    if datetime.now().hour in [1, 2, 3, 4, 5, 9, 10, 11, 12, 15, 22, 23, 24]:
        # 以上时间不在交班时间段内
        return

    shift_groups = []
    try:
        shift_groups = upcoming_shifts_grouped()
    except Exception as e:
        logger.error(f"获取即将交班科室列表失败：{e}")
        return

    if not shift_groups:
        logger.debug(f"没有即将交班科室")
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

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
    del db
    reg_sqls = {item.get('sid'): item for item in all_sqls}

    # 抓取医生交接班数据
    if doctor_shift_groups:
        for time_slot, dept_list in doctor_shift_groups.items():
            try:
                doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list)
            except Exception as e:
                logger.warning(f"医生 {time_slot} 交班异常: {e}", traceback.print_exc())

    if nursing_shift_groups:
        for time_slot, dept_list in nursing_shift_groups.items():
            if '1000961' in dept_list:
                # 妇产科
                try:
                    ob_gyn_shift_change(reg_sqls, shift_classes, time_slot)
                except Exception as e:
                    logger.warning(f"妇产科 {time_slot} 交接班异常: {e}", traceback.print_exc())

            if '1000962' in dept_list:
                # ICU 重症
                try:
                    icu_shift_change(reg_sqls, shift_classes, time_slot)
                except Exception as e:
                    logger.warning(f"重症 ICU {time_slot} 交接班异常: {e}", traceback.print_exc())

            if '1000965' in dept_list or '1001120' in dept_list:
                # AICU CCU
                try:
                    aicu_shift_change(reg_sqls, shift_classes, time_slot)
                except Exception as e:
                    logger.warning(f"AICU/CCU {time_slot} 交接班异常: {e}", traceback.print_exc())

            dept_id_list = [dept_id for dept_id in dept_list if
                            dept_id not in ['1000961', '1000962', '1000965', '1001120']]
            try:
                general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list)
            except Exception as e:
                logger.warning(f"护理 {time_slot} 交班异常: {e}", traceback.print_exc())


def balanced_split_three(lst, piece):
    """平分列表：平衡分配余数"""
    n = len(lst)
    if n < 10:
        return [lst]
    size, rem = divmod(n, piece)
    sizes = [size + (1 if i < rem else 0) for i in range(piece)]

    result = []
    start = 0
    for s in sizes:
        result.append(lst[start:start + s])
        start += s
    return result


def single_run_shift_change(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
    del db
    reg_sqls = {item.get('sid'): item for item in all_sqls}

    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    time_slot = json_data.get('time_slot')
    dept_list = json_data.get('dept_list')

    try:

        if shift_type == 1:
            # 医生交接班
            doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list)
        elif shift_type == 2:
            # 普通护理交接班
            general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list)
        elif shift_type == 3:
            # AICU/CCU交接班
            aicu_shift_change(reg_sqls, shift_classes, time_slot)
        elif shift_type == 4:
            # 妇产科交接班
            ob_gyn_shift_change(reg_sqls, shift_classes, time_slot)
        elif shift_type == 5:
            # ICU 重症交接班
            icu_shift_change(reg_sqls, shift_classes, time_slot)
        else:
            raise Exception("未知的交接班类型")
    except Exception as e:
        logger.warning(f"{time_slot} 交班异常: {e}", traceback.print_exc())


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


def shift_info(dept_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    shift_config = db.query_one(f"select * from nsyy_gyl.scs_shift_config where dept_id = '{str(dept_id)}' ")
    del db
    return {"bed_info_list": shift_change_config.bed_info_list,
            "patient_type_list": shift_change_config.patient_type_list,
            "dept_shift_config": shift_config}


def save_sign_info(json_data):
    """
    后端直接触发 医生/护士 签名， 随后保存签名返回信息
    :param json_data:
    :return:
    """
    shift_date = json_data.get('shift_date')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')
    dept_name = json_data.get('dept_name')
    biz_sn = json_data.get('biz_sn')

    sign_msg = json_data.get('sign_msg')  # 文件摘要
    user_id = json_data.get('user_id', "")  # 医生/护士 云医签 id
    user_name = json_data.get('user_name')

    if not user_id:
        raise Exception('医生/护士不存在, 请先联系信息科配置【云医签】', user_name)

    try:
        # 构造签名数据bizSn 业务流水号 需要唯一 登记记录签名用 register_id 治疗记录签名用 register_id + patient_id + record_date
        sign_param = {"type": "sign_push", "user_id": user_id, "bizSn": biz_sn, "msg": sign_msg, "desc": "交接班签名"}
        sign_ret = global_tools.call_yangcheng_sign_serve(sign_param)

        # 时间戳签名
        ts_sign_param = {"sign_org": sign_msg, "type": "ts_gene"}
        ts_sign_ret = global_tools.call_yangcheng_sign_serve(ts_sign_param, ts_sign=True)
    except Exception as e:
        raise Exception('签名服务器异常', e)

    save_sign_info = dict()
    save_sign_info['shift_date'] = shift_date
    save_sign_info['shift_classes'] = shift_classes
    save_sign_info['dept_id'] = dept_id
    save_sign_info['dept_name'] = dept_name
    save_sign_info['doc_id'] = user_id
    save_sign_info['doctor_name'] = user_name
    save_sign_info['doc_sign'] = json.dumps(sign_ret, default=str)
    save_sign_info['doc_ts_sign'] = json.dumps(ts_sign_ret, default=str)
    save_sign_info['sign_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = """
            INSERT INTO nsyy_gyl.scs_sign_info (shift_date, shift_classes, dept_id, dept_name, doc_id, doc_name, 
            doc_sign, doc_ts_sign, sign_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE 
            shift_date = VALUES(shift_date), shift_classes = VALUES(shift_classes), dept_id = VALUES(dept_id), 
            dept_name = VALUES(dept_name), doc_id = VALUES(doc_id), doc_name = VALUES(doc_name), 
            doc_sign = VALUES(doc_sign), doc_ts_sign = VALUES(doc_ts_sign), sign_time = VALUES(sign_time)  
    """
    db.execute(insert_sql, tuple(save_sign_info.values()), need_commit=True)
    del db
    return biz_sn


def query_patient_info(zhuyuanhao):
    sql = f"""select zb.xingming patient_name, zb.dangqiancwbm bed_no, zb.zhuyuanhao zhuyuanhao, 
    zb.xingbiemc patient_sex, zb.nianling patient_age, zb.bingrenzyid, zb.zhuzhiysxm doctor_name from
	df_jj_zhuyuan.zy_bingrenxx zb where zb.zaiyuanzt = 0 and zb.quxiaorybz = 0 and zb.yingerbz = 0
	and zb.zhuyuanhao = '{zhuyuanhao}'"""

    patient_info_list = global_tools.call_new_his_pg(sql)
    return patient_info_list[0] if patient_info_list else {}

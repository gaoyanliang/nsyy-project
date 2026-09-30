import json
import logging
import re
import time
import uuid
import redis
from collections import defaultdict
from itertools import groupby

from gylmodules import global_config, global_tools
from gylmodules.shift_change import shift_change_config
from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER, LOCK_KEY_DEPT_LIST, CACHE_KEY_DEPT_LIST, \
    LOCK_EXPIRE_SECONDS, CACHE_EXPIRE_SECONDS, CACHE_KEY_SINGLE_CONFIG, CACHE_KEY_ALL_CONFIG
from gylmodules.utils.db_utils_new import DbUtil
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

"""删除科室交接班数据 患者信息"""
def delete_shift_data(record_id):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        record = db.query_one(f"select * from nsyy_gyl.scs_patients where id = {record_id} and is_deleted = 0 ")
        if not record:
            raise Exception("不存在此交接班数据")

        shift_classes = record.get('shift_classes')
        dept_id = record.get('patient_dept_id') if shift_classes and str(shift_classes).startswith('1-') else record.get('patient_ward_id')
        if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{record.get('shift_date')}' "
                        f"and dept_id = {dept_id} and shift_classes = '{shift_classes}' and archived = 1"):
            raise Exception("该班次已归档无法在修改或新增数据")

        db.execute(f"UPDATE nsyy_gyl.scs_patients SET is_deleted = 1, "
                   f"zhuyuanhao = '{record.get('zhuyuanhao')}-{int(time.time())}' where id = {record_id} ",
                   need_commit=True)


"""查询科室交接班数据"""
def query_shift_change_date(json_data):
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    shift_date = json_data.get('shift_date')
    dept_id = json_data.get('dept_id')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if int(shift_type) == 1:
            dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
                if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id
            # 医生交接班
            shift_classes = f"{shift_type}-{shift_classes}"
            shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                                      f"and shift_classes = '{shift_classes}' and dept_id = {dept_id} and archived = 1")
            is_archived = [shift_classes] if shift_info else []

            shift_classes = f"{shift_type}-{shift_classes}"
            classes_list = ['1-1']
            if shift_classes.endswith('-3'):
                classes_list = ['1-1', '1-2', '1-3']
            elif shift_classes.endswith('-2'):
                classes_list = ['1-1', '1-2']

            classes_str = ', '.join(f"'{item}'" for item in classes_list)
            query_sql = f"select * from nsyy_gyl.scs_patients where is_deleted = 0 and shift_date = '{shift_date}' " \
                        f"and shift_classes in ({classes_str}) and patient_dept_id = {dept_id}"
            patients = db.query_all(query_sql)

            count_info = db.query_all(f"select * from nsyy_gyl.scs_patient_count where shift_date = '{shift_date}' "
                                      f"and shift_classes in ({classes_str}) and patient_dept_id = {dept_id}")
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
            query_sql = f"select * from nsyy_gyl.scs_patients where is_deleted = 0 and shift_date = '{shift_date}' " \
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

                default_bed_info = shift_change_config.default_bed_info_dict.copy()
                for item in patient_bed_info:
                    default_bed_info.pop(item.get('patient_type'))

                # 将患者类别转换为 带顺序前缀的患者类别
                for item in patient_bed_info:
                    item['patient_type'] = shift_change_config.bed_info_convert.get(item['patient_type']) or item[
                        'patient_type']

                if patient_bed_info:
                    patient_bed_info = patient_bed_info + [v for k, v in default_bed_info.items()]
                else:
                    patient_bed_info = [v for k, v in default_bed_info.items()]
            else:
                patient_bed_info = []

    total = {}
    # 除了几个特殊类型，其他类型的人数要展示累计数量
    for key, values in patient_count.items():
        if isinstance(values, dict) and values:
            for k, v in values.items():
                if k in ['特护', '一级护理', '病危', '病重', '现有', '预术']:
                    total[k] = v
                else:
                    total[k] = total.get(k, 0) + v
    patient_count['0'] = total

    # 同一天多个班次的患者情况进行合并
    patients = merge_ret_patient_list(patients, is_archived)

    def get_patient_type_key(patient):
        """返回用于排序的元组：(类型1优先级, 类型2优先级, ..., bed_no)"""
        types = [t.strip() for t in patient['patient_type'].split(',')]
        priorities = [PATIENT_TYPE_ORDER.get(t, float('inf')) for t in types]
        max_types = 14  # 假设最多14个类型
        priorities += [float('inf')] * (max_types - len(priorities))

        # 直接使用 datetime 对象，Python 的 datetime 可以直接比较
        create_at = patient.get('create_at') or datetime.max  # 如果没有 create_at，使用最大时间
        return tuple(priorities + [create_at, int(patient['bed_no'])])

    sorted_patients = sorted(patients, key=get_patient_type_key)

    def extract_sort_key(item):
        try:
            type_str = item.get("patient_type", "")
            num_part = "".join(filter(str.isdigit, type_str))
            return int(num_part) if num_part else 0
        except:
            return 0  # 异常情况返回 0

    patient_bed_info = sorted(patient_bed_info, key=extract_sort_key)
    return {'patient_count': patient_count, 'patient_bed_info': patient_bed_info, 'patients': sorted_patients}


"""根据患者住院号/主治医生检索交班数据"""
def query_shift_change_date_by_key(json_data):
    # 必传
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    shift_date = json_data.get('shift_date')

    # 可选
    dept_id = json_data.get('dept_id')
    zhuyuanhao = json_data.get('zhuyuanhao')
    doctor_name = json_data.get('doctor_name')
    if not dept_id and not zhuyuanhao and not doctor_name:
        raise Exception("请选择科室/住院号/主治医生")
    condition_sql = (f"and patient_dept_id = {dept_id}" if int(shift_type) == 1 else f"and patient_ward_id = {dept_id}") if dept_id else ''
    condition_sql += f"and zhuyuanhao = '{zhuyuanhao}'" if zhuyuanhao else ''
    condition_sql += f"and doctor_name like '%{doctor_name}%'" if doctor_name else ''

    if int(shift_type) == 1:
        dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
            if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id
        # 医生交接班
        shift_classes = f"{shift_type}-{shift_classes}"
        classes_list = ['1-1']
        if shift_classes.endswith('-3'):
            classes_list = ['1-1', '1-2', '1-3']
        elif shift_classes.endswith('-2'):
            classes_list = ['1-1', '1-2']
        classes_str = ', '.join(f"'{item}'" for item in classes_list)
    else:
        # 护士交接班
        shift_classes = f"{shift_type}-{shift_classes}"
        classes_list = ['2-1']
        if shift_classes.endswith('-3'):
            classes_list = ['2-1', '2-2', '2-3']
        elif shift_classes.endswith('-2'):
            classes_list = ['2-1', '2-2']
        classes_str = ', '.join(f"'{item}'" for item in classes_list)

    query_sql = f"select * from nsyy_gyl.scs_patients where is_deleted = 0 and shift_date = '{shift_date}' " \
                f"and shift_classes in ({classes_str}) {condition_sql} "

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        patients = db.query_all(query_sql)

    # 同一天多个班次的患者情况进行合并
    patients = merge_ret_patient_list(patients, [1,2,3])
    return patients


"""护理交接班返回的时候 全天的交班记录合并返回  合并同一患者的不同班次记录"""
def merge_ret_patient_list(patient_list, is_archived):
    # 使用defaultdict分组存储患者记录
    patients = defaultdict(lambda: {
        'records': [],  # 存储该患者所有记录
        'latest_record': None  # 存储最新记录
    })

    # 1. 按患者分组并找出最新记录
    for record in patient_list:
        if record.get('patient_name'):
            record['patient_name'] = record['patient_name'].replace('$四级手术$', '')
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

        sorted_types = sorted(result, key=lambda x: PATIENT_TYPE_ORDER.get(x, float('inf')))
        types = ', '.join(sorted_types)
        # 创建合并后的记录
        merged_record = latest.copy()
        merged_record['patient_info'] = patient_info
        merged_record['patient_type'] = types
        merged.append(merged_record)
        types = []

    return merged


"""更新/新增交接班患者数据"""
def update_shift_change_data(json_data):
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = int(json_data.get('patient_dept_id')) if json_data.get('patient_dept_id') else int(
        json_data.get('patient_ward_id'))
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{json_data.get('shift_date')}' "
                        f"and dept_id = {dept_id} and shift_classes = '{shift_classes}' and archived = 1"):
            raise Exception("该班次已归档无法在修改或新增数据")

        if 'id' in json_data:
            # 更新交班数据
            set_fields = []
            args = []
            for key, value in json_data.items():
                if key in ['zhenduan', 'patient_type', 'doctor_name', 'patient_info', 'bed_no']:
                    set_fields.append(f"{key} = %s")
                    args.append(value)
            args.append(json_data.get('id'))
            sql = f"UPDATE nsyy_gyl.scs_patients SET {','.join(set_fields)} where id = %s"
        else:
            sql = f"""INSERT INTO nsyy_gyl.scs_patients(shift_date, shift_classes, bingrenzyid, zhuyuanhao, bed_no, 
                            patient_name, patient_sex, patient_age, zhenduan, patient_type, patient_dept_id, patient_dept,
                            patient_ward_id, patient_ward, doctor_name, patient_info, create_at, update_at) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            args = (json_data.get('shift_date'), f"{json_data.get('shift_type')}-{json_data.get('shift_classes')}",
                    json_data.get('bingrenzyid', ''),
                    json_data.get('zhuyuanhao', ''), safe_bed_no(json_data.get('bed_no', '')), json_data.get('patient_name', ''),
                    json_data.get('patient_sex', ''), json_data.get('patient_age', ''), json_data.get('zhenduan', ''),
                    json_data.get('patient_type'), json_data.get('patient_dept_id', '0'),
                    json_data.get('patient_dept', '0'), json_data.get('patient_ward_id'), json_data.get('patient_ward'),
                    json_data.get('doctor_name'), json_data.get('patient_info').replace("%", "%"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        db.execute(sql, args=args, need_commit=True)


def safe_bed_no(bed_no):
    try:
        if not bed_no:
            return '0'
        bed_no = str(bed_no).replace(' ', '')
        if not bed_no:
            return '0'
        numbers = re.findall(r'\d+', bed_no)
        return ''.join(numbers)
    except Exception as e:
        logger.error(f" 床号 {bed_no} 转换异常: {e}")
        return '0'


"""更新/新增交接班人数数据"""
def update_patient_count(json_data):
    shift_type = json_data.get('shift_type')
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{json_data.get('shift_date')}' "
                        f"and dept_id = {int(json_data.get('dept_id'))} "
                        f"and shift_classes = '{json_data.get('shift_type')}-{json_data.get('shift_classes')}' and archived = 1"):
            raise Exception("该班次已归档无法再刷新数据，如需刷新数据请先取消归档。慎重操作")

        if int(shift_type) == 1:
            args = (json_data.get('shift_date'), f"{json_data.get('shift_type')}-{json_data.get('shift_classes')}",
                    json_data.get('patient_type'), int(json_data.get('dept_id')), json_data.get('dept_name'), 0, '0',
                    json_data.get('count'), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            args = (json_data.get('shift_date'), f"{json_data.get('shift_type')}-{json_data.get('shift_classes')}",
                    json_data.get('patient_type'), 0, '0', int(json_data.get('dept_id')), json_data.get('dept_name'),
                    json_data.get('count'), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_count(shift_date, shift_classes, patient_type, 
                        patient_dept_id, patient_dept, patient_ward_id, patient_ward, count, create_at, update_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE 
                        count = VALUES(count), update_at = VALUES(update_at) """
        db.execute(insert_sql, args=args, need_commit=True)


"""更新或新增交班床位信息"""
def update_shift_change_bed_data(json_data):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{json_data.get('shift_date')}' "
                        f"and dept_id = {int(json_data.get('patient_ward_id'))} "
                        f"and shift_classes = '2-{json_data.get('shift_classes')}' and archived = 1"):
            raise Exception("该班次已归档无法再刷新数据，如需刷新数据请先取消归档。慎重操作")

        if json_data.get('patient_type'):
            json_data['patient_type'] = re.sub(r'^\d+', '', json_data['patient_type'])  # 删除开头的数字
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
        db.execute(sql, args, need_commit=True)


"""根据住院号查询患者信息"""
def query_patient_info(zhuyuanhao):
    patient_info_list = global_tools.call_new_his_pg(f"""select zb.xingming patient_name, zb.dangqiancwbm bed_no, 
    zb.zhuyuanhao zhuyuanhao, zb.xingbiemc patient_sex, zb.nianling patient_age, zb.bingrenzyid, 
    zb.zhuzhiysxm doctor_name from (select zb.zhuyuanhao,max(zb.zhuyuancs) zhuyuancs 
    from df_jj_zhuyuan.zy_bingrenxx zb where zb.zhuyuanhao= '{zhuyuanhao}' group by zhuyuanhao)v 
    join df_jj_zhuyuan.zy_bingrenxx zb  on zb.zhuyuanhao =v.zhuyuanhao and zb.zhuyuancs=v.zhuyuancs""")
    return patient_info_list[0] if patient_info_list else {}


# ====================================================================
# ============================= 交接班配置 =============================
# ====================================================================


"""新增或者更新交接班配置"""


def create_or_update_shift_config(json_data):
    try:
        # 如果开启对应的交班班次 必须设置交班时间段
        slots = []
        if json_data.get('early_shift'):
            slots.append(json_data.get('early_shift_slot'))
        else:
            json_data['early_shift_slot'] = ''
        if json_data.get('middle_shift'):
            slots.append(json_data.get('middle_shift_slot'))
        else:
            json_data['middle_shift_slot'] = ''
        if json_data.get('night_shift'):
            slots.append(json_data.get('night_shift_slot'))
        else:
            json_data['night_shift_slot'] = ''

        for shift_slot in slots:
            start_str, end_str = shift_slot.split('-')
            start = datetime.strptime(start_str.strip(), '%H:%M').time()
            end = datetime.strptime(end_str.strip(), '%H:%M').time()
    except:
        raise Exception("时间格式错误")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

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

    redis_client = redis.Redis(connection_pool=pool)
    cache_key = CACHE_KEY_SINGLE_CONFIG.format(str(json_data.get('dept_id')))
    redis_client.delete(cache_key)
    cache_key = CACHE_KEY_ALL_CONFIG
    redis_client.delete(cache_key)


def query_shift_info(json_data):
    shift_date = json_data.get('shift_date')
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')
    dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
        if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        shift_config = query_shift_config(dept_id=dept_id)

        shift_info = db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                                  f"and shift_classes = '{shift_type}-{shift_classes}' and dept_id = {int(dept_id)}")
        if shift_info:
            shift_info.pop('outgoing_data')
            shift_info.pop('incoming_data')
            shift_info.pop('head_nurse_data')
            shift_info['incominger'] = json.loads(shift_info.get('incominger')) if shift_info.get('incominger') else []
            shift_info['outgoinger'] = json.loads(shift_info.get('outgoinger')) if shift_info.get('outgoinger') else []
            shift_info['head_nurser'] = json.loads(shift_info.get('head_nurser')) if shift_info.get('head_nurser') else []

    return {"bed_info_list": shift_change_config.bed_info_list,
            "patient_type_list": shift_change_config.patient_type_list,
            "dept_shift_config": shift_config,
            "shift_info": shift_info}


# ===================================================================
# ============================= 签名相关 =============================
# ===================================================================


"""后端直接触发 医生/护士 签名， 随后保存签名返回信息"""


def save_shift_info(json_data):
    shift_date = json_data.get('shift_date')
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')
    dept_name = json_data.get('dept_name')
    sign_type = json_data.get('sign_type')

    dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
        if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id

    if str(dept_id) in shift_change_config.his_dept_name_dict:
        dept_name = shift_change_config.his_dept_name_dict.get(str(dept_id))

    # 1=交班人 2=接班人 3=护士长
    if sign_type in [1, 2, 3]:
        return doctor_sign(json_data)

    # 4 归档 5 取消归档
    if int(sign_type) == 4:
        # 归档时需要有本班交班人的签名 和 上一个班次接班人的签名
        is_archiving_allowed(shift_date, shift_type, shift_classes, dept_id)

    params = (shift_date, f"{shift_type}-{shift_classes}", dept_id, dept_name,
              0 if int(sign_type) == 5 else 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if int(sign_type) in (4, 5):
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, 
        archived, archived_time) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE archived = VALUES(archived), 
            archived_time = VALUES(archived_time) """
    else:
        raise Exception('签名类型错误 1=交班人 2=接班人 3=护士长 4=归档 5=取消归档')
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        db.execute(insert_sql, params, need_commit=True)

    return ''


"""医生签名 1=交班人 2=接班人 3=护士长"""


def doctor_sign(json_data):
    shift_date = json_data.get('shift_date')
    shift_type = json_data.get('shift_type')
    shift_classes = json_data.get('shift_classes')
    dept_id = json_data.get('dept_id')
    dept_name = json_data.get('dept_name')
    sign_type = json_data.get('sign_type')
    user_id = json_data.get('user_id', '')  # 医生/护士 云医签 id
    user_name = json_data.get('user_name', '')
    # 签名列表
    sign_list = json_data.get('sign_list', [])

    dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
        if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id

    if str(dept_id) in shift_change_config.his_dept_name_dict:
        dept_name = shift_change_config.his_dept_name_dict.get(str(dept_id))

    if int(shift_type) == 1:
        # 医生签名需要校验患者信息是否需要完善补充
        doc_dept_id = shift_change_config.doc_teshu_dept_map.get(str(dept_id)) \
            if str(dept_id) in shift_change_config.doc_teshu_dept_map else dept_id
        shift_classes_str = f"{shift_type}-{shift_classes}"
        query_sql = f"select patient_name, patient_type, patient_info from nsyy_gyl.scs_patients where is_deleted = 0 and shift_date = '{shift_date}' " \
                    f"and shift_classes = '{shift_classes_str}' and patient_dept_id = {doc_dept_id} and is_deleted = 0"

        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            patients = db.query_all(query_sql)

        if patients:
            reminder_info = []
            for patient in patients:
                if (patient.get('patient_type') and patient.get('patient_type').__contains__('转入')
                        and patient.get('patient_info') and patient.get('patient_info').__contains__(
                            '患者目前病情:给予治疗方案:')):
                    reminder_info.append(patient.get('patient_name'))
                    continue
                if (patient.get('patient_type') and patient.get('patient_type').__contains__('手术')
                        and patient.get('patient_info') and patient.get('patient_info').__contains__(
                            '患者于-在下行')):
                    reminder_info.append(patient.get('patient_name'))
                    continue
                if (patient.get('patient_type') and patient.get('patient_type').__contains__('入院')
                        and patient.get('patient_info') and patient.get('patient_info').__contains__(
                            '患者以为主诉收治入院,既往史:体格检查:给予暂无辅助检查治疗方案:')):
                    reminder_info.append(patient.get('patient_name'))
                    continue
            if reminder_info:
                raise Exception(f"患者 {', '.join(reminder_info)} 信息未完善，请完善患者信息后再进行签名！")

    if user_id:
        # 如果存在医生id，说明是新的签名，如果不存在有可能是删除某一个签名，直接保存传过来的 sign——list 即可
        # 获取医生签名图片 不能放到 下面 try中，否则报错会被吃掉
        sign_img = get_doctor_sign_img(user_id)
        # 获取医生职称
        redis_client = redis.Redis(connection_pool=pool)
        zhicheng = redis_client.get(f"doctor_title:{user_id.replace('U', '').replace('u', '')}") or ''

        try:
            # 签名业务字段 随机生成 保证唯一即可
            biz_sn = uuid.uuid4().__str__()
            # 文件摘要
            sign_msg = f"{dept_name} - {shift_date} {shift_classes} 交班"

            sign_param = {"type": "sign_push", "user_id": user_id, "bizSn": biz_sn, "msg": sign_msg,
                          "desc": "交接班签名"}
            sign_ret = global_tools.call_yangcheng_sign_serve(sign_param)
            # 时间戳签名
            ts_sign_param = {"sign_org": sign_msg, "type": "ts_gene"}
            ts_sign_ret = global_tools.call_yangcheng_sign_serve(ts_sign_param, ts_sign=True)
        except Exception as e:
            raise Exception(f'签名服务器异常 {user_id} {user_name}', e)

        sign_data = {
            "user_id": user_id, "user_name": user_name, "user_title": zhicheng,
            "sign_img": sign_img, "sign_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sign_data": {"sign_ret": sign_ret, "ts_sign_ret": ts_sign_ret}
        }
        sign_list.append(sign_data)

    params = (shift_date, f"{shift_type}-{shift_classes}", dept_id, dept_name, json.dumps(sign_list))
    if int(sign_type) == 1:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, outgoinger)
                VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE outgoinger = VALUES(outgoinger)"""
    elif int(sign_type) == 2:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, incominger)
                VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE incominger = VALUES(incominger)"""
    elif int(sign_type) == 3:
        insert_sql = """INSERT INTO nsyy_gyl.scs_shift_info (shift_date, shift_classes, dept_id, dept_name, head_nurser)
                VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE head_nurser = VALUES(head_nurser)"""
    else:
        raise Exception('签名类型错误 1=交班人 2=接班人 3=护士长')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        db.execute(insert_sql, params, need_commit=True)

    return sign_list


"""校验是否允许归档"""


def is_archiving_allowed(shift_date, shift_type, shift_classes, dept_id):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        dept_info = query_shift_config(dept_id=dept_id)
        previous_shift_classes = int(shift_classes) - 1
        previous_shift_date = shift_date
        if previous_shift_classes == 0:
            previous_shift_classes = 3
            date_obj = datetime.strptime(shift_date, "%Y-%m-%d")
            previous_day = date_obj - timedelta(days=1)
            previous_shift_date = previous_day.strftime("%Y-%m-%d")

        # 如果上一个班次是中班，还需要判断这个科室是否启用了中班
        # 还需判断是否是 24小时班（只有夜班）
        if previous_shift_classes == 2:
            if not dept_info.get('middle_shift') or not dept_info.get('middle_shift_slot'):
                previous_shift_classes = 1
            if previous_shift_classes == 1 and (not dept_info.get('early_shift') or not dept_info.get('early_shift_slot')):
                previous_shift_classes = 3
                date_obj = datetime.strptime(shift_date, "%Y-%m-%d")
                previous_day = date_obj - timedelta(days=1)
                previous_shift_date = previous_day.strftime("%Y-%m-%d")

        sql = f"select incominger, archived from nsyy_gyl.scs_shift_info where shift_date = '{previous_shift_date}' " \
              f"and dept_id = {dept_id} and shift_classes = '{shift_type}-{previous_shift_classes}'"
        record = db.query_one(sql)
        if datetime.strptime(shift_date, "%Y-%m-%d").date() >= date(2026, 1, 12) and record and int(record.get('archived')) == 0:
            raise Exception('上一班未归档，请先归档')

        if not record or not record.get('incominger'):
            raise Exception('上一班接班人未签名（归档需上一个班次接班人和本班交班人的签名）')

        if str(dept_id) == "7907" and record.get('incominger'):
            # 肿瘤中心 需要两个签名
            incoming_list = record.get('incominger')
            incoming_list = json.loads(incoming_list)
            if len(incoming_list) < 2:
                raise Exception('肿瘤中心交班接班需要两位医生的签名')

        sql = f"select outgoinger from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' " \
              f"and dept_id = {dept_id} and shift_classes = '{shift_type}-{shift_classes}'"
        record = db.query_one(sql)
        if not record or not record.get('outgoinger'):
            raise Exception('本班交班人未签名（归档需上一个班次接班人和本班交班人的签名）')

        if str(dept_id) == "7907" and record.get('outgoinger'):
            # 肿瘤中心 需要两个签名
            outgoing_list = record.get('outgoinger')
            outgoing_list = json.loads(outgoing_list)
            if len(outgoing_list) < 2:
                raise Exception('肿瘤中心交班接班需要两位医生的签名')


"""获取医生签名图片，如果是首次签名，从云医签中获取签名"""


def get_doctor_sign_img(user_id):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        record = db.query_one(f"select * from nsyy_gyl.scs_doc_sign_img where user_id = '{user_id}'")
        if record:
            return record.get('sign_img')

        img_base64 = global_tools.fetch_yun_sign_img(user_id)
        sign_img = None
        if img_base64:
            sign_img = global_tools.upload_sign_file(img_base64, is_pdf=False)

        if not sign_img:
            raise Exception('云医签获取签名图片失败, 请先配置云医签')

        db.execute("insert into nsyy_gyl.scs_doc_sign_img (user_id, sign_img) values (%s, %s)",
                   (user_id, sign_img), need_commit=True)

        return sign_img


# 查询科室签名/归档及时率


def shift_change_report(start_date, end_date, shift_type):
    sql = f"""
        with recursive date_range as (
        select
            '{start_date}' as shift_date
        union all
        select
            date_add(shift_date, interval 1 day)
        from
            date_range
        where
            shift_date < '{end_date}' ),
        merged_dept as 
        (
        select 1000148 as dept_a,1000148 as dept_m,1000149 as dept_n  #神外三
        union all 
        select 1000149 as dept_a,1000148 as dept_m,1000149 as dept_n  #神外四
        union all 
        select 93163 as dept_a,93163 as dept_m,1000701 as dept_n  #中医
        union all 
        select 1000701 as dept_a,93163 as dept_m,1000701 as dept_n  #风湿免疫
        union all 
        select 169 as dept_a,169 as dept_m,7905 as dept_n  #神内六
        union all 
        select 7905 as dept_a,169 as dept_m,7905 as dept_n  #中西医结合脑病
        union all
        select 94103 as dept_a,94103 as dept_m,1000406 as dept_n  #乳腺外
        union all 
        select 1000406 as dept_a,94103 as dept_m,1000406 as dept_n  #普外
        ),
        sign_t as (
        select
            date_range.shift_date,
            substr(shift_classes, 1, 1) as shift_type,
            substr(shift_classes, 3, 1) as shift_class,
            dept_id,
            case
                when json_length(ssi.outgoinger) > 0 
                then json_unquote(json_extract(ssi.outgoinger, concat('$[', json_length(ssi.outgoinger)-1, '].sign_time')))
                else null
            end as out_sign_time,
            case
                when json_length(ssi.incominger) > 0 
                then json_unquote(json_extract(ssi.incominger, concat('$[', json_length(ssi.incominger)-1, '].sign_time')))
                else null
            end as in_sign_time,
            archived_time
        from
            nsyy_gyl.scs_shift_info ssi
        join date_range on
            ssi.shift_date = date_range.shift_date
        where ssi.dept_id not in (1000148,1000149,93163,1000701,169,7905,94103,1000406)
        union all 
        select
            date_range.shift_date,
            substr(shift_classes, 1, 1) as shift_type,
            substr(shift_classes, 3, 1) as shift_class,
            merged_dept.dept_a as dept_id,
            case
                when json_length(ssi.outgoinger) > 0 
                then json_unquote(json_extract(ssi.outgoinger, concat('$[', json_length(ssi.outgoinger)-1, '].sign_time')))
                else null
            end as out_sign_time,
            case
                when json_length(ssi.incominger) > 0 
                then json_unquote(json_extract(ssi.incominger, concat('$[', json_length(ssi.incominger)-1, '].sign_time')))
                else null
            end as in_sign_time,
            archived_time
        from
            nsyy_gyl.scs_shift_info ssi
        join merged_dept on ssi.dept_id=merged_dept.dept_m or ssi.dept_id=merged_dept.dept_n
        join date_range on
            ssi.shift_date = date_range.shift_date
        where ssi.dept_id  in (1000148,1000149,93163,1000701,169,7905,94103,1000406)
            ),
            shift_time as (
        select
            date_range.shift_date,
            ssc.shift_type,
            ssc.dept_id,
            ssc.dept_name,
            1 shift_class,
            str_to_date(concat(date_range.shift_date, ' ', substr(ssc.early_shift_slot, 7), ':00'),
            '%Y-%m-%d %H:%i:%s') as slot
        from
            nsyy_gyl.scs_shift_config ssc
        join date_range on
            1 = 1
        where
            ssc.early_shift = 1
            and ssc.shift_status = 1
        union all
        select
            date_range.shift_date,
            ssc.shift_type,
            ssc.dept_id,
            ssc.dept_name,
            2 shift_class,
            str_to_date(concat(date_range.shift_date, ' ', 
            substr(ssc.middle_shift_slot, 7), ':00'),
            '%Y-%m-%d %H:%i:%s') as slot
        from
            nsyy_gyl.scs_shift_config ssc
        join date_range on
            1 = 1
        where
            ssc.middle_shift = 1
            and ssc.shift_status = 1
        union all
        select
            date_range.shift_date,
            ssc.shift_type,
            ssc.dept_id,
            ssc.dept_name,
            3 shift_class,
            str_to_date(concat(date_add(date_range.shift_date, interval 1 day), ' ', 
            substr(ssc.night_shift_slot, 7), ':00'),
            '%Y-%m-%d %H:%i:%s') as slot
        from
            nsyy_gyl.scs_shift_config ssc
        join date_range on
            1 = 1
        where
            ssc.night_shift = 1
            and ssc.shift_status = 1)
            select
            s.shift_date,
            s.dept_id,
            s.dept_name,
            s.shift_type,
            s.shift_class,
            s.slot,
            t.out_sign_time,
            case
                when timestampdiff(hour,
                s.slot,
                t.out_sign_time)<3 then 1
                else 0
            end as out_valid_flg,
            t.in_sign_time,
            case
                when timestampdiff(hour,
                s.slot,
                t.in_sign_time)<3 then 1
                else 0
            end as in_valid_flg,
            t.archived_time,
            case
                when timestampdiff(hour,
                s.slot,
                t.archived_time)<3 then 1
                else 0
            end as archive_valid_flg,
            case
                when t.archived_time is not null then 1
                else 0
            end as archived,
            case
                when t.in_sign_time is not null then 1
                else 0
            end as in_signed,
            case
                when t.out_sign_time is not null then 1
                else 0
            end as out_signed
        from
            shift_time s
        left join sign_t t on
            s.shift_type = t.shift_type
            and s.shift_class = t.shift_class
            and s.dept_id = t.dept_id
            and s.shift_date = t.shift_date
        where
            s.shift_type = {shift_type}
        order by
            shift_date,
            dept_id,
            shift_type,
            shift_class
    """

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        records = db.query_all(sql)

    if not records:
        return []

    # 总天数（包含开始日）
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    delta = end_date - start_date
    total_days = delta.days + 1

    ret = []
    # 按部门排序并分组
    records.sort(key=lambda x: (x['dept_id'], x['shift_date']))
    for dept_id, group in groupby(records, key=lambda x: x['dept_id']):
        in_count, out_count, archive_count, archived, in_signed, out_signed = 0, 0, 0, 0, 0, 0
        class_count = set()

        group = list(group)
        dept_id = group[0].get('dept_id', '')
        dept_name = group[0].get('dept_name', '')
        for item in group:
            item.pop('dept_id')
            item.pop('dept_name')
            class_count.add(item['shift_class'])
            in_count += item.get('in_valid_flg')
            out_count += item.get('out_valid_flg')
            archive_count += item.get('archive_valid_flg')

            archived += item.get('archived')
            in_signed += item.get('in_signed')
            out_signed += item.get('out_signed')

        ret.append({
            "dept_id": dept_id,
            "dept_name": dept_name,

            # 签到 签名率
            "in_count": in_signed,
            "in_rate": in_signed / (total_days * len(class_count)),
            "out_count": out_signed,
            "out_rate": out_signed / (total_days * len(class_count)),
            "archive_count": archived,
            "archive_rate": archived / (total_days * len(class_count)),

            # 及时率
            "in_count_timely": in_count,
            "in_rate_timely": in_count / (total_days * len(class_count)),
            "out_count_timely": out_count,
            "out_rate_timely": out_count / (total_days * len(class_count)),
            "archive_count_timely": archive_count,
            "archive_rate_timely": archive_count / (total_days * len(class_count)),

            "detail_list": group
        })

    return ret


"""查询四级手术患者列表"""


def fourth_surgery(start_date, end_date, shift_type):
    shift_types = "'1-1', '1-2', '1-3'" if int(shift_type) == 1 else "'2-1', '2-2', '2-3'"
    sql = (f"select * from nsyy_gyl.scs_patients where shift_classes in ({shift_types}) and "
           f"shift_date >= '{start_date}' and shift_date <= '{end_date}' "
           f"and patient_name like '%$四级手术$%'")
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        records = db.query_all(sql)

    for record in records:
        record['patient_name'] = record['patient_name'].replace('$四级手术$', '')
    return records


"""定时同步医生职称"""
def fetch_doctor_title():
    sql = """select zhigongid 职工id,zhigonggh 职工工号,zhigongxm 姓名,zhichengmc 职称 from (
            select gz.zhigongid,gz.zhigonggh,gz.zhigongxm,gz1.zhichengmc from df_zhushuju.gy_zhigongda gz 
            join df_zhushuju.gy_zhigongxx gz1 on gz.zhigongid=gz1.zhigongid and gz1.zuofeibz=0
            where  gz.zhigonglb='1' )v where zhichengmc is not null"""
    data = global_tools.call_new_his_pg(sql)
    if not data:
        return
    redis_client = redis.Redis(connection_pool=pool)
    for item in data:
        if item.get('职工工号'):
            zhicheng = '住院医师' if item.get('职称') == '医师' else item.get('职称')
            redis_client.set(f"doctor_title:{item.get('职工工号')}", zhicheng)



"""获取部门列表 --1科室,2病区（带 Redis 缓存，缓存1小时，自动防缓存击穿）"""
def dept_list(dept_type):
    cache_key = CACHE_KEY_DEPT_LIST.format(dept_type)
    # 1. 尝试从缓存获取
    redis_client = redis.Redis(connection_pool=pool)
    cached_data = redis_client.get(cache_key)
    if cached_data is not None:
        try:
            return json.loads(cached_data)
        except json.JSONDecodeError:
            logger.warning(f"部门列表缓存数据损坏，key={cache_key}，重新查询数据库")
            # 损坏则删除缓存，继续向下执行查询
            redis_client.delete(cache_key)

    # 2. 缓存不存在或已过期，尝试获取分布式锁
    lock_key = LOCK_KEY_DEPT_LIST.format(dept_type)
    # 使用 setnx 实现分布式锁（仅当 key 不存在时设置成功）
    lock_acquired = redis_client.setnx(lock_key, "1")
    if lock_acquired:
        # 设置锁的过期时间，防止死锁
        redis_client.expire(lock_key, LOCK_EXPIRE_SECONDS)
        try:
            # 再次检查缓存，可能其他线程在等待锁期间已经更新了缓存
            cached_data = redis_client.get(cache_key)
            if cached_data is not None:
                return json.loads(cached_data)
            # 查询数据库
            data = _query_dept_list_from_db(dept_type)
            # 写入缓存，过期时间 1 小时
            redis_client.setex(cache_key, CACHE_EXPIRE_SECONDS, json.dumps(data, ensure_ascii=False))
            return data
        except Exception as e:
            logger.error(f"查询部门列表并更新缓存失败: {e}")
            # 发生异常时，降级直接查询数据库返回（不缓存）
            return _query_dept_list_from_db(dept_type)
        finally:
            # 释放锁
            redis_client.delete(lock_key)
    else:
        # 未获得锁，说明有其他线程正在更新缓存，等待一小段时间后重试读取缓存
        import time
        retry_count = 0
        while retry_count < 10:  # 最多等待 5 秒（每次 0.5 秒）
            time.sleep(0.5)
            cached_data = redis_client.get(cache_key)
            if cached_data is not None:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    pass
            retry_count += 1
        # 超时仍未获取到缓存，直接查询数据库（降级）
        logger.warning(f"获取部门列表缓存超时，直接查询数据库，dept_type={dept_type}")
        return _query_dept_list_from_db(dept_type)


"""从数据库查询部门列表（原始SQL）"""
def _query_dept_list_from_db(dept_type):
    sql = f"""select gz.zuzhibm as "dept_code", 0 as "dept_id", 0 as "dept_mng",
            coalesce(gz2.zhigongxm,'0')  as "dept_mng_name", gz.zuzhimc as "dept_name",
            gz.zuzhiid::int as "his_dept_id" from df_zhushuju.gy_zuzhidy gz
            left join df_zhushuju.gy_zhigongda gz2 on gz.lianxiren = gz2.zhigongid
            where gz.zuofeibz=0  and gz.zhuyuanbz =1 and gz.zuzhilx = '{dept_type}'"""
    return global_tools.call_new_his_pg(sql)


"""查询交接班配置"""
def query_shift_config(dept_id=None):
    """
    查询科室交接班配置
    :param dept_id: 可选，科室ID。如果传入则查询该科室配置，否则查询所有科室配置
    :return: 单个配置字典（当 dept_id 传入且存在时）或配置列表
    """
    # 1. 确定缓存 key
    if dept_id is not None:
        cache_key = CACHE_KEY_SINGLE_CONFIG.format(dept_id)
        is_single = True
    else:
        cache_key = CACHE_KEY_ALL_CONFIG
        is_single = False

    # 2. 尝试从缓存读取
    redis_client = redis.Redis(connection_pool=pool)
    cached_data = redis_client.get(cache_key)
    if cached_data is not None:
        try:
            result = json.loads(cached_data)
            logger.debug(f"从缓存读取交接班配置: {cache_key}")
            return result
        except json.JSONDecodeError:
            logger.warning(f"缓存数据损坏，key={cache_key}，重新查询数据库")
            redis_client.delete(cache_key)

    # 3. 缓存未命中，查询数据库
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if dept_id is not None:
            config = db.query_one(f"SELECT * FROM nsyy_gyl.scs_shift_config WHERE dept_id = '{str(dept_id)}' ")
            # 单个科室未找到时返回 None
            result = config
            if result:
                result.pop('create_at')
        else:
            result = db.query_all("SELECT * FROM nsyy_gyl.scs_shift_config")
            if result:
                for item in result:
                    item.pop('create_at')

    if not result:
        if is_single:
            return {}
        else:
            return []
    # 4. 将结果写入缓存
    redis_client.set(cache_key, json.dumps(result, ensure_ascii=False))
    logger.debug(f"从数据库查询交接班配置并写入缓存: {cache_key}")
    return result



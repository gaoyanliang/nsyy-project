import logging

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime


logger = logging.getLogger(__name__)


def patient_registration(json_data):
    """
    登记急救患者信息
    :param json_data:
    :return:
    """
    operater = json_data.pop('operater', '')
    operater_id = json_data.pop('operater_id', '')
    if not operater or operater not in ['admin', '屈元韦', '孙瑞莲', '张晓丽']:
        logger.info(f"操作用户不存在! 登记急救患者信息仅允许调度人员操作 {json_data}")
        raise Exception("操作用户不存在! 急救登记仅允许调度人员操作")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if 'laidiansj' in json_data and not json_data.get('laidiansj'):
        json_data.pop('laidiansj')
    if 'paichesj' in json_data and not json_data.get('paichesj'):
        json_data.pop('paichesj')

    json_data['create_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    insert_sql = f"INSERT INTO nsyy_gyl.phs_patient_registration ({','.join(json_data.keys())}) " \
                 f"VALUES {str(tuple(json_data.values()))}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("急诊患者登记失败 sql = ", insert_sql)
    del db


def delete_patient_registration(register_id):
    """
    登记急救患者信息
    :param register_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(f"UPDATE nsyy_gyl.phs_patient_registration SET status = 0 WHERE "
               f"register_id = {register_id} ", need_commit=True)
    del db


def update_patient_info(json_data, register_id):
    """
    更新急救患者信息
    :param json_data: 需要更新的字段及值的字典
    :param register_id: 患者的唯一 ID
    :return:
    """
    if 'laidiansj' in json_data and not json_data.get('laidiansj'):
        json_data.pop('laidiansj')
    if 'paichesj' in json_data and not json_data.get('paichesj'):
        json_data.pop('paichesj')
    if 'liyuansj' in json_data and not json_data.get('liyuansj'):
        json_data.pop('liyuansj')
    if 'hushishangchesj' in json_data and not json_data.get('hushishangchesj'):
        json_data.pop('hushishangchesj')
    if 'daoyuansj' in json_data and not json_data.get('daoyuansj'):
        json_data.pop('daoyuansj')
    if 'create_at' in json_data and not json_data.get('create_at'):
        json_data.pop('create_at')
    if 'update_at' in json_data and not json_data.get('update_at'):
        json_data.pop('update_at')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 生成 SET 部分的 SQL 语句
    set_clause = ', '.join([f"{key} = %s" for key in json_data.keys()])

    # 构造 SQL 语句
    update_sql = f"UPDATE nsyy_gyl.phs_patient_registration SET {set_clause} WHERE register_id = %s"
    params = tuple(json_data.values()) + (register_id,)
    db.execute(update_sql, params, need_commit=True)
    del db


def query_patient_info(register_id, record_id):
    """
    查询急救患者信息
    :param register_id: 患者的唯一 ID
    :param record_id: 病历详情
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if record_id:
        query_sql = f"SELECT * FROM nsyy_gyl.phs_record_data WHERE register_id = {int(register_id)} and record_id = {int(record_id)}"
    else:
        query_sql = f"SELECT * FROM nsyy_gyl.phs_patient_registration WHERE register_id = {int(register_id)}"

    data = db.query_all(query_sql)
    del db

    return data


def query_patient_list(key, bingli, start_date, end_date, page_number, page_size):
    """
    查询急救患者列表
    :param key:
    :param start_date:
    :param end_date:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = f"a.create_at BETWEEN '{start_date}' AND '{end_date}' "
    if key:
        condition_sql = condition_sql + f"AND (a.patient_name LIKE '%{key}%' " \
                                        f"or a.yisheng LIKE '%{key}%' or a.hushi LIKE '%{key}%') "

    if bingli:
        query_sql = f"""
                select a.*, case when b.register_id is null then 0 else 1 end as bingli1, 
                case when c.register_id is null then 0 else 1 end as bingli2 
                from nsyy_gyl.phs_patient_registration a 
                left join (select DISTINCT register_id from  nsyy_gyl.phs_record_data where record_id = 1) b on a.register_id = b.register_id
                left join (select DISTINCT register_id from  nsyy_gyl.phs_record_data where record_id = 2) c on a.register_id = c.register_id
                WHERE {condition_sql} and a.status = 1 and (b.register_id is null or c.register_id is null) order by a.create_at desc
                """
    else:
        query_sql = f"""
                select a.*, case when b.register_id is null then 0 else 1 end as bingli1, 
                case when c.register_id is null then 0 else 1 end as bingli2 
                from nsyy_gyl.phs_patient_registration a 
                left join (select DISTINCT register_id from  nsyy_gyl.phs_record_data where record_id = 1) b on a.register_id = b.register_id
                left join (select DISTINCT register_id from  nsyy_gyl.phs_record_data where record_id = 2) c on a.register_id = c.register_id
                WHERE {condition_sql} and a.status = 1 order by a.create_at desc
                """
    data = db.query_all(query_sql)
    del db

    total = len(data)
    if page_number and page_size:
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        data = data[start_index:end_index]

    return {"list": data, "total": total}


def query_record_list():
    """
    查询急救表单模版列表
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    data = db.query_all("select * from nsyy_gyl.phs_record")
    del db
    return data


def query_patient_record_list(register_id):
    """
    查询当前患者创建的急救表单列表
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    data = db.query_all(f"select DISTINCT r.id, r.record_name, r.record_type from nsyy_gyl.phs_record r "
                        f"join nsyy_gyl.phs_record_data rd on r.id = rd.record_id where rd.register_id = {register_id}")
    del db
    return data


def create_patient_record(register_id, record_id, record_data):
    """
    创建患者表单
    :param register_id:
    :param record_id:
    :param record_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    values = []
    update_condition = []
    for item in record_data:
        values.append((int(register_id), int(record_id), item.get('field_name'), item.get('field_value'), item.get('field_type')))
        if item.get('field_name') == 'patient_name' and item.get('field_value'):
            update_condition.append(f"patient_name = '{item.get('field_value')}'")
        if item.get('field_name') == 'patient_sex' and item.get('field_value'):
            update_condition.append(f"patient_sex = '{item.get('field_value')}'")
        if item.get('field_name') == 'patient_age' and item.get('field_value'):
            update_condition.append(f"patient_age = '{item.get('field_value')}'")

        if int(record_id) == 2 and item.get('field_name') in ['time', 'temperature', 'anjiahuansuan',
                                                              'pulse', 'respiration', 'blood_pressure'] \
                and item.get('field_value'):
            key = 'daoyuansj' if item.get('field_name') == 'time' else item.get('field_name')
            update_condition.append(f"{key} = '{item.get('field_value')}'")

        if int(record_id) == 2 and item.get('field_name') == 'treatments' and item.get('field_value'):
            value = item.get('field_value')
            xindiantu = '未做'
            if value.__contains__('心电图'):
                xindiantu = '已做'
            if value.__contains__('心电图-当地已做'):
                xindiantu = '当地已做'
            update_condition.append(f"xindaintu = '{xindiantu}'")
            if value.__contains__('颈椎固定'):
                update_condition.append(f"jingzhui = 1")
            if value.__contains__('骨盆带固定'):
                update_condition.append(f"gupendai = 1")

            # 方法1：使用split和isdigit检查
            parts = [p.strip() for p in value.split(',')]
            last_part = parts[-1]
            if last_part.replace('.', '', 1).isdigit():  # 允许小数
                update_condition.append(f"xuetang = '{last_part}'")

        if int(record_id) == 2 and item.get('field_name') == 'condition' and item.get('field_value'):
            condition_mapping = {"III级": 3, "IV级": 4, "II级": 2, "I级": 1}
            update_condition.append(f"bingqing_level = {condition_mapping.get(item.get('field_value'), 0)}")
        if int(record_id) == 2 and item.get('field_name') == 'venous_treatment' and item.get('field_value'):
            value_list = item.get('field_value').split(",")
            results = ''
            for value in value_list:
                if "外周静脉留置针-" in value:
                    _, _, suffix = value.partition("-")
                    results = results + suffix
            update_condition.append(f"jingmaitd = '{results}'")

    if update_condition:
        update_sql = f"UPDATE nsyy_gyl.phs_patient_registration SET {','.join(update_condition)} WHERE register_id = {register_id}"
        db.execute(update_sql, need_commit=True)

    insert_sql = """INSERT INTO nsyy_gyl.phs_record_data (register_id, record_id, field_name, field_value, field_type)
            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE field_value = VALUES(field_value), 
            field_type = VALUES(field_type)"""
    last_row = db.execute_many(insert_sql, args=values, need_commit=True)
    if last_row == -1:
        del db
        raise Exception("急救表单入库失败! ", insert_sql)
    del db



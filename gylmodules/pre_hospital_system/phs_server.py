from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime


def patient_registration(json_data):
    """
    登记急救患者信息
    :param json_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    json_data['create_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    insert_sql = f"INSERT INTO nsyy_gyl.phs_patient_registration ({','.join(json_data.keys())}) " \
                 f"VALUES {str(tuple(json_data.values()))}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("急诊患者登记失败 sql = ", insert_sql)
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
    try:
        db.execute(update_sql, params, need_commit=True)
    except Exception as e:
        del db
        raise Exception(datetime.now(), f"急诊患者更新失败，未找到登记 ID = {register_id} 的记录。SQL = {update_sql}")
    del db


def query_patient_info(register_id, record_id):
    """
    查询急救患者信息
    :param register_id: 患者的唯一 ID
    :param record_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if record_id:
        query_sql = f"SELECT * FROM nsyy_gyl.phs_record_data WHERE record_id = {int(record_id)}"
    else:
        query_sql = f"SELECT * FROM nsyy_gyl.phs_patient_registration WHERE register_id = {int(register_id)}"

    data = db.query_all(query_sql)
    del db

    return data


def query_patient_list(key, start_date, end_date, page_number, page_size):
    """
    查询急救患者列表
    :param key:
    :param start_date:
    :param end_date:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = f"create_at BETWEEN '{start_date}' AND '{end_date}' "
    if key:
        condition_sql = condition_sql + f"AND patient_name LIKE '%{key}%' "

    query_sql = f"SELECT * FROM nsyy_gyl.phs_patient_registration WHERE {condition_sql}"
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
    values = [(int(register_id), int(record_id), item.get('field_name'), item.get('field_value'),
               item.get('field_type', '')) for item in record_data]

    insert_sql = """INSERT INTO nsyy_gyl.phs_record_data (register_id, record_id, field_name, field_value, field_type)
            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE field_value = VALUES(field_value), 
            field_type = VALUES(field_type)"""
    last_row = db.execute_many(insert_sql, args=values, need_commit=True)
    if last_row == -1:
        del db
        raise Exception("急救表单入库失败! ", insert_sql)
    del db



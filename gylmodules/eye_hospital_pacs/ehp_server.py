import json
from datetime import datetime

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils import DbUtil


def query_patient_info_from_his(key):
    patient_infs = global_tools.call_new_his(f"""select 姓名 name, 性别 gender, 年龄 age, 家庭电话 my_phone_num, 
    联系人电话 family_phone_num, 身份证号 id_card_no, 家庭地址 home_address from 病人信息 where 家庭电话 like '%{key}%' 
    or 姓名 like '%{key}%' or 身份证号 like '%{key}%'""")
    return patient_infs


def patient_registration(register_data):
    """
    患者信息登记
    :param register_data:
    :return:
    """
    # 联系电话至少需要一个
    if not register_data.get('my_phone_num') and not register_data.get('family_phone_num'):
        raise Exception("至少需要填写一个联系电话")

    if not register_data.get('first_visit_time'):
        register_data['first_visit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not register_data.get('last_visit_time'):
        register_data['last_visit_time'] = register_data.get('first_visit_time')

    if register_data.get('id_card_no'):
        register_data['birth_date'] = get_birthday_from_id(register_data.get('id_card_no'))

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    register_id = register_data.get('id')
    if register_id:
        # 如果存在登记ID，则更新
        # 生成 SET 部分的 SQL 语句
        set_clause = ', '.join([f"{key} = %s" for key in register_data.keys()])
        register_sql = f"UPDATE nsyy_gyl.ehp_register_info SET {set_clause} WHERE register_id = %s"
        params = tuple(register_data.values()) + (int(register_id),)
        db.execute(register_sql, params, need_commit=True)
    else:
        register_sql = f"INSERT INTO nsyy_gyl.ehp_register_info ({','.join(register_data.keys())}) " \
                    f"VALUES {str(tuple(register_data.values()))}"
        last_row = db.execute(sql=register_sql, need_commit=True)
        if last_row == -1:
            del db
            raise Exception("患者信息登记失败! ", register_sql)
    del db


def query_patient_list(query_data):
    """
    查询患者列表（优化分页版）
    :param query_data: 查询参数
    :return: 患者列表和总数
    """
    # 构建基础查询条件
    conditions = ["1=1"]  # 基础条件，保证WHERE子句有效

    # 关键字搜索条件
    key = query_data.get('key')
    if key:
        conditions.append(f"(r.name LIKE \'%{key}%\' OR r.id_card_no LIKE \'%{key}%\' "
                          f"OR r.my_phone_num LIKE \'%{key}%\' OR r.family_phone_num LIKE \'%{key}%\')")

    # 时间范围条件
    start_time, end_time = query_data.get("start_time"), query_data.get("end_time")
    if start_time and end_time:
        conditions.append(f"r.first_visit_time BETWEEN '{start_time}' AND '{end_time}'")

    # 组合WHERE条件
    where_clause = " AND ".join(conditions)

    # 分页参数
    page_number = query_data.get("page_number", 1)
    page_size = query_data.get("page_size", 10)
    offset = (page_number - 1) * page_size

    # 查询总数
    count_sql = f"SELECT COUNT(*) FROM nsyy_gyl.ehp_register_info r WHERE {where_clause}"

    # 查询分页数据
    query_sql = f"""
        SELECT r.*, t.tid, t.zhusu, t.visit_time FROM nsyy_gyl.ehp_register_info r 
        left join nsyy_gyl.ehp_treatment_record t on r.register_id = t.register_id WHERE {where_clause}
        LIMIT {page_size} OFFSET {offset}
    """

    # 执行查询
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    try:
        # 查询总数
        total = db.query_one(count_sql).get('COUNT(*)')
        # 查询分页数据
        patient_list = db.query_all(query_sql)
        del db
    except Exception as e:
        del db
        raise Exception("查询患者列表失败! ", e)

    merged = {}
    for record in patient_list:
        key = record["register_id"]

        if key not in merged:
            # 初始化合并后的记录
            merged[key] = {
                "register_id": record["register_id"],
                "name": record["name"],
                "birth_date": record["birth_date"],
                "id_card_no": record["id_card_no"],
                "age": record["age"],
                "gender": record["gender"],
                "nationality": record["nationality"],
                "career": record["career"],
                "my_phone_num": record["my_phone_num"],
                "family_phone_num": record["family_phone_num"],
                "relationship": record["relationship"],
                "home_address": record["home_address"],
                "first_visit_time": record["first_visit_time"],
                "last_visit_time": record["last_visit_time"],
                "treatments": []  # 存储 {table_id, table_name} 字典
            }

        # 添加 tab 信息
        if record['tid']:
            merged[key]["treatments"].append({
                "tid": record["tid"],
                "zhusu": record["zhusu"],
                "visit_time": record["visit_time"]
            })

    return {"patient_list": list(merged.values()), "total": total}


def treatment_records(json_data):
    """
    新增到访记录
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    insert_sql = f"""
    INSERT INTO `nsyy_gyl`.`ehp_treatment_record` (`zhusu`, `register_id`, `visit_time`) 
    VALUES ('{json_data.get('zhusu')}', {json_data.get('register_id')}, '{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}');
    """
    last_row = db.execute(sql=insert_sql, need_commit=True)
    if last_row == -1:
        del db
        raise Exception("新增治疗记录失败! ", insert_sql)
    del db


def create_medical_record(json_data):
    """
    创建病历
    :param json_data:
    :return:
    """
    record_data = {}
    record_id = json_data.get('record_id')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    try:
        if not record_id:
            # 新增病历
            record_data['register_id'] = json_data.get('register_id')
            record_data['tid'] = json_data.get('tid')
            record_data['record_name'] = json_data.get('record_name')
            record_data['record_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record_data['last_update_time'] = record_data['record_time']

            record_sql = f"INSERT INTO nsyy_gyl.ehp_medical_record_list ({','.join(record_data.keys())}) " \
                         f"VALUES {str(tuple(record_data.values()))}"
            record_id = db.execute(sql=record_sql, need_commit=True)
            if record_id == -1:
                del db
                raise Exception("患者病历创建失败! ", record_sql)
        else:
            db.execute(f"UPDATE nsyy_gyl.ehp_medical_record_list "
                       f"SET last_update_time = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' "
                       f"WHERE record_id = {record_id}", need_commit=True)

        # 新增病历详情
        values = [(int(json_data.get('register_id')), int(record_id), item.get('table_id'), item.get('table_name'),
                   json.dumps(item, default=str), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                  for item in json_data.get('data')]

        insert_sql = """INSERT INTO nsyy_gyl.ehp_medical_record_detail (register_id, record_id, table_id, 
                        table_name, table_value, create_time) VALUES (%s, %s, %s, %s, %s, %s)"""
        last_row = db.execute_many(insert_sql, args=values, need_commit=True)
        if last_row == -1:
            del db
            raise Exception("急救表单入库失败! ", insert_sql)
        del db
    except Exception as e:
        del db
        raise Exception("新增病历异常! ", e)


def update_medical_record_detail(json_data):
    """
    更新创建过的tab表单
    :param json_data:
    :return:
    """
    if not json_data:
        return
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    try:
        for record_detail_id, table_value in json_data.items():
            update_sql = f"""UPDATE nsyy_gyl.ehp_medical_record_detail 
            SET table_value = {json.dumps(table_value, default=str)} where id = {record_detail_id}"""
            db.execute(update_sql, need_commit=True)
        del db
    except Exception as e:
        del db
        raise Exception("新增/更新病历异常! ", e)


def query_medical_list(register_id, tid):
    """
    查询病历列表
    :param register_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    record_data = db.query_all(f"SELECT r.register_id, r.record_id, r.record_name, rd.id as record_detail_id, "
                               f"rd.table_id, rd.table_name FROM nsyy_gyl.ehp_medical_record_list r "
                               f"join nsyy_gyl.ehp_medical_record_detail rd on r.register_id = rd.register_id "
                               f"and r.record_id = rd.record_id WHERE r.register_id = {register_id} and r.tid = {tid}")
    del db

    merged = {}
    for record in record_data:
        key = (record["register_id"], record["record_id"])

        if key not in merged:
            # 初始化合并后的记录
            merged[key] = {
                "register_id": record["register_id"],
                "record_id": record["record_id"],
                "record_name": record["record_name"],
                "tabs": []  # 存储 {table_id, table_name} 字典
            }

        # 添加 tab 信息
        merged[key]["tabs"].append({
            "record_detail_id": record["record_detail_id"],
            "table_id": record["table_id"],
            "table_name": record["table_name"]
        })

    return list(merged.values())


def query_medical_record(record_detail_id):
    """
    查询病历详情
    :param record_detail_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    record_data = db.query_all(f"SELECT * FROM nsyy_gyl.ehp_medical_record_detail WHERE id = {record_detail_id}")
    del db

    for d in record_data:
        d['table_value'] = json.loads(d['table_value']) if d['table_value'] else {}
    return record_data


def get_birthday_from_id(id_number):
    """根据身份证号获取出生日期"""
    if len(id_number) == 18:
        birthday = id_number[6:14]  # 截取第7位到第14位
        return birthday[:4] + birthday[4:6] + birthday[6:]
    else:
        return ''




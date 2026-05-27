import json
import logging
import traceback

import redis
import threading

from datetime import datetime, timedelta

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils_new import DbUtil

from gylmodules.workstation import ws_config
from gylmodules.workstation.message.message_server import send_message

"""
医院急诊一键通知系统
"""

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

cv_id_lock = threading.Lock()

logger = logging.getLogger(__name__)

def get_all_doctors():
    redis_client = redis.Redis(connection_pool=pool)
    doctor_schedule_data = redis_client.hgetall('doctor_schedule')
    docs = [json.loads(item) for item in doctor_schedule_data.values()]
    doctors = []
    for doc in docs:
        doctors.append({
            'doc_id': doc.get('职工工号'),
            'zhigongid': doc.get('职工id'),
            'zhigonggh': doc.get('职工工号'),
            'doc_name': doc.get('姓名'),
            'title': doc.get('职称'),
            'phone': doc.get('电话'),
            'dept_id': doc.get('科室id'),
            'dept_name': doc.get('科室')
        })
    return doctors


"""获取今日值班信息"""
def get_today_duty():
    shift_date = datetime.now().date().strftime('%Y-%m-%d')
    if datetime.now().hour >= 0 and datetime.now().hour <= 7:
        shift_date = (datetime.now() - timedelta(days=1)).date().strftime('%Y-%m-%d')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        placeholders = "'主班', '夜班', '24时班'"
        query_sql = f""" select * from nsyy_gyl.on_call_schedule where shift_date = '{shift_date}' and shift_type in ({placeholders})"""
        schedules = db.query_all(query_sql)

    if not schedules:
        return []

    redis_client = redis.Redis(connection_pool=pool)
    doctor_schedule_data = redis_client.hgetall('doctor_schedule')
    for item in schedules:
        doc = doctor_schedule_data.get(item.get('doc_id'), {})
        try:
            doc = json.loads(doc)
            item['title'] = doc.get('职称') if doc else ''
            item['phone'] = doc.get('电话') if doc else ''
        except Exception as e:
            logger.error(f"获取医生信息失败: {e}")

    # 按科室分组
    duty_by_dept = {}
    for schedule in schedules:
        if schedule.get('dept_id') not in duty_by_dept:
            duty_by_dept[schedule.get('dept_id')] = {
                'dept_name': schedule.get('dept_name', '未知'),
                'doctors': []
            }

        duty_by_dept[schedule.get('dept_id')]['doctors'].append({
            'doc_name': schedule.get('doc_name'),
            'title': schedule.get('title', ''),
            'phone':  schedule.get('phone', ''),
            'shift_type': schedule.get('shift_type')
        })

    return duty_by_dept


"""一键通知 - 创建会诊群"""
def emergency_notification(json_data):

    try:
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

            # 1. 创建会诊群
            shift_date = datetime.now().date().strftime('%Y-%m-%d')
            shift_type = 1 # 1=白班 2=夜班
            shift_type_str = "'主班', '24时班'" # 1=白班 2=夜班
            if datetime.now().hour >= 18 and datetime.now().hour <= 23:
                shift_type = 2
                shift_type_str = "'夜班', '24时班'"
            if datetime.now().hour >= 0 and datetime.now().hour <= 7:
                shift_type = 2
                shift_type_str = "'夜班', '24时班'"
                shift_date = (datetime.now() - timedelta(days=1)).date().strftime('%Y-%m-%d')

            dept_list = json_data.get('dept_list')
            dept_id_list = ','.join([str(dept.get('id')) for dept in dept_list])
            dept_name_list = ','.join([dept.get('name') for dept in dept_list])

            insert_sql = """INSERT INTO nsyy_gyl.on_call_record (shift_date, shift_type, sender_id, sender_name, 
                            patient_name, patient_info, created_at, dept_id_list, dept_name_list) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            record_id = db.execute(insert_sql, (shift_date, shift_type, json_data.get('sender_id'),
                                                json_data.get('sender_name'), json_data.get('patient_name'),
                                                json_data.get('patient_info'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                dept_id_list, dept_name_list), need_commit=True)
            if record_id < 0:
                logger.error(f"创建会诊信息失败")
                raise Exception('创建会诊信息失败')

            # 2. 获取当天所有值班医生
            query_sql = f""" SELECT doc_id, doc_name, dept_name FROM nsyy_gyl.on_call_schedule 
            WHERE shift_date = '{shift_date}' AND shift_type in ({shift_type_str}) and dept_id in ({dept_id_list}) """
            doc_list = db.query_all(query_sql)

            notification_list = ' , '.join([f"{doc['dept_name']}@{doc['doc_name']}" for doc in doc_list])

            # 4. 发送初始消息
            message_content = f"""【急诊会诊通知】
                        患者姓名：{json_data['patient_name']}
                        患者情况：{json_data.get('patient_info', '暂无')}
                        
                        请各科室值班医生查看并响应是否可以收治。"""


            insert_sql = """INSERT INTO nsyy_gyl.on_call_message (record_id, sender_id, sender_name, 
                            content, created_at) VALUES (%s, %s, %s, %s, %s)"""
            messages = [(record_id, json_data.get('sender_id'), json_data.get('sender_name'), message_content, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        (record_id, 110100, 'admin', f"已通知医生：{notification_list} 进行会诊。", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
            db.execute_many(insert_sql, messages, need_commit=True)

        # 发送消息前需要将职工共号转为 persid
        redis_client = redis.Redis(connection_pool=pool)
        doctor_schedule_data = redis_client.hgetall('doctor_schedule')
        for item in doc_list:
            dd = doctor_schedule_data.get(str(item.get('doc_id')), {})
            dd = json.loads(dd) if dd else {}
            item['pers_id'] = dd.get('pers_id') if dd else item.get('doc_id')
        # 5. 发送通知消息
        if global_config.run_in_local:
            doc_list.append({'pers_id': 110100, 'doc_name': 'admin'})
        receiver = ','.join([str(item.get('pers_id')) for item in doc_list])
        receiver_name = ','.join([item.get('doc_name') for item in doc_list])
        if len(receiver_name) > 20:
            # 计算需要保留的完整名字数量
            truncated = receiver_name[:20]
            # 确保不在名字中间截断，找到最后一个逗号位置
            last_comma = truncated.rfind(',')
            if last_comma > 20 * 0.5:  # 至少保留一半
                truncated = truncated[:last_comma] + '...'
            else:
                truncated = truncated + '...'
            receiver_name = truncated

        msg = {"type": 111, "title": "急诊会诊通知", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "description": message_content}
        send_message(ws_config.NOTIFICATION_MESSAGE, 1, json_data.get('sender_id'), json_data.get('sender_name'),
                     None, receiver, receiver_name, json.dumps(msg, default=str), audio_notification=True)

    except Exception as e:
        logger.error(f"一键会诊通知异常 {str(e)} {traceback.print_exc()}")


"""获取会诊记录"""
def get_consultation_groups(json_data):
    sql = """ select * from nsyy_gyl.on_call_record where created_at >= now() - interval 2 day order by created_at desc"""
    key = json_data.get('key')
    if key == 'all':
        sql = """ select * from nsyy_gyl.on_call_record order by created_at desc"""

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        return db.query_all(sql)


def get_consultation_detail(json_data):
    sql = f""" select * from nsyy_gyl.on_call_record where id = {json_data.get('record_id')} order by created_at desc"""
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        detail = db.query_all(sql)
        if not detail:
            return {}
        detail = detail[0]
        shift_type_str = "'主班', '24时班'" if detail['shift_type'] == 1 else "'夜班', '24时班'"
        doctors = get_schedules({"start_date": detail.get('shift_date'),
                                 "end_date": detail.get('shift_date'),
                                 "dept_id_list": detail.get('dept_id_list'),
                                 "shift_type": shift_type_str})
        detail['doctors'] = doctors
        return detail


def query_record_message(json_data):
    sql = f""" select * from nsyy_gyl.on_call_message where record_id = {json_data.get('record_id')} order by created_at desc"""
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        return db.query_all(sql)


def record_message(json_data):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        insert_sql = """INSERT INTO nsyy_gyl.on_call_message (record_id, sender_id, sender_name, 
                        content, created_at) VALUES (%s, %s, %s, %s, %s)"""
        db.execute(insert_sql, (json_data.get('record_id'), json_data.get('sender_id'), json_data.get('sender_name'), json_data.get('message'),
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)

        record = db.query_one(f"select * from nsyy_gyl.on_call_record where id = {json_data.get('record_id')}")
        if not record:
            return

        shift_date = record['shift_date']
        shift_type_str = "'主班', '24时班'" if record['shift_type'] == 1 else "'夜班', '24时班'"
        dept_id_list = record['dept_id_list']

        # 2. 获取当天所有值班医生
        query_sql = f""" SELECT doc_id, doc_name, dept_name FROM nsyy_gyl.on_call_schedule 
        WHERE shift_date = '{shift_date}' AND shift_type in ({shift_type_str}) and dept_id in ({dept_id_list}) """
        doc_list = db.query_all(query_sql)

        notification_list = ' , '.join([f"{doc['dept_name']}@{doc['doc_id']}" for doc in doc_list])

    # 5. 发送通知消息
    receiver = ','.join([item.get('doc_id') for item in doc_list])
    receiver_name = ','.join([item.get('doc_name') for item in doc_list])
    if len(receiver_name) > 20:
        # 计算需要保留的完整名字数量
        truncated = receiver_name[:20]
        # 确保不在名字中间截断，找到最后一个逗号位置
        last_comma = truncated.rfind(',')
        if last_comma > 20 * 0.5:  # 至少保留一半
            truncated = truncated[:last_comma] + '...'
        else:
            truncated = truncated + '...'
        receiver_name = truncated

    send_message(ws_config.NOTIFICATION_MESSAGE, 1, json_data.get('sender_id'), json_data.get('sender_name'),
                 None, receiver, receiver_name, json_data.get('message'))


# ==================== 排班管理接口 ====================

"""查询排班"""
def get_schedules(json_data):
    conditation_sql = ""
    if json_data.get('start_date') and json_data.get('end_date'):
        conditation_sql += f"and (shift_date >= '{json_data.get('start_date')}' " \
                           f"and shift_date <= '{json_data.get('end_date')}') "
    if json_data.get('dept_id'):
        conditation_sql += f"and dept_id = '{json_data.get('dept_id')}' "
    if json_data.get('dept_id_list'):
        dept_list = str(json_data.get('dept_id_list')).split(',')
        dept_list = ' , '.join([f"'{d}'" for d in dept_list])
        conditation_sql += f"and dept_id in ({dept_list}) "
    if json_data.get('doctor_id'):
        conditation_sql += f"and doctor_id = '{json_data.get('doctor_id')}' "
    if json_data.get('shift_type'):
        conditation_sql += f"and shift_type in ({json_data.get('shift_type')}) "

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        sql = f"SELECT * FROM nsyy_gyl.on_call_schedule where 1=1 {conditation_sql}"
        schedules = db.query_all(sql)

    if not schedules:
        return []

    redis_client = redis.Redis(connection_pool=pool)
    doctor_schedule_data = redis_client.hgetall('doctor_schedule')
    for item in schedules:
        doc = doctor_schedule_data.get(item.get('doc_id'), {})
        doc = json.loads(doc)
        item['title'] = doc.get('职称') if doc else ''
        item['phone'] = doc.get('电话') if doc else ''
    return schedules


"""新增值班"""
def create_schedule(json_data):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        insert_sql = """
                         INSERT INTO nsyy_gyl.on_call_schedule (doc_id, doc_name, dept_id, dept_name, shift_date, 
                         shift_type, notes, is_duty, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                         ON DUPLICATE KEY UPDATE doc_id = VALUES(doc_id), doc_name = VALUES(doc_name), 
                         dept_id = VALUES(dept_id), dept_name = VALUES(dept_name),
                         shift_date = VALUES(shift_date), shift_type = VALUES(shift_type), 
                         notes = VALUES(notes), is_duty = VALUES(is_duty)
                     """
        db.execute(insert_sql, (json_data.get('doc_id'), json_data.get('doc_name'),
                                json_data.get('dept_id'), json_data.get('dept_name'),
                                json_data.get('shift_date'), json_data.get('shift_type'),
                                json_data.get('notes', ''), json_data.get('is_duty', 0),
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)


"""修改排班"""
def update_schedule(json_data):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if datetime.strptime(json_data.get('shift_date'), '%Y-%m-%d') < datetime.now().date():
            raise Exception('不能修改今天之前的排班')

        if not db.query_one(f"SELECT * FROM nsyy_gyl.on_call_schedule where id = '{json_data.get('id')}' "):
            raise Exception('排班记录不存在')

        db.execute("""UPDATE nsyy_gyl.on_call_schedule SET shift_type = %s, notes = %s, is_duty = %s WHERE id = %s""",
                   (json_data.get('shift_type'), json_data.get('notes'), json_data.get('is_duty'), ), need_commit=True)


"""删除排班"""
def delete_schedule(id):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        db.execute("""DELETE FROM nsyy_gyl.on_call_schedule WHERE id = %s""", (id,), need_commit=True)


"""复制排班"""
def copy_schedules(data):
    source_start = datetime.strptime(data['source_start'], '%Y-%m-%d').date()
    source_end = datetime.strptime(data['source_end'], '%Y-%m-%d').date()
    target_start = datetime.strptime(data['target_start'], '%Y-%m-%d').date()
    target_end = datetime.strptime(data['target_end'], '%Y-%m-%d').date()

    # 目标科室（可选）
    target_dept_id = data.get('target_dept_id')
    target_dept_name = data.get('target_dept_name')
    if not target_dept_id or not target_dept_name:
        raise Exception('请选择目标科室')

    if (target_end - target_start).days != (source_end - source_start).days:
        raise Exception('源时间段和目标时间段天数不一致')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        # 1️⃣ 查询源排班
        sql_select = f""" SELECT * FROM nsyy_gyl.on_call_schedule
            WHERE dept_id = '{target_dept_id}' AND shift_date BETWEEN '{source_start}' AND '{source_end}' """
        source_schedules = db.query_all(sql_select)

        insert_data = []
        for row in source_schedules:
            shift_date_str = row['shift_date']
            shift_date_obj = datetime.strptime(shift_date_str, '%Y-%m-%d').date()
            # 2️⃣ 计算目标日期
            days_diff = (shift_date_obj - source_start).days
            new_date = target_start + timedelta(days=days_diff)

            insert_data.append((row.get('doc_id'), row.get('doc_name'), row.get('dept_id'), row.get('dept_name'),
                                new_date.strftime("%Y-%m-%d"), row.get('shift_type'), '',
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        insert_sql = """
                         INSERT INTO nsyy_gyl.on_call_schedule (doc_id, doc_name, dept_id, dept_name, shift_date, 
                         shift_type, notes, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                         ON DUPLICATE KEY UPDATE doc_id = VALUES(doc_id), doc_name = VALUES(doc_name), 
                         dept_id = VALUES(dept_id), dept_name = VALUES(dept_name),
                         shift_date = VALUES(shift_date), shift_type = VALUES(shift_type), 
                         notes = VALUES(notes)
                     """
        db.execute_many(insert_sql, insert_data, need_commit=True)


def copy_doctor_schedules(data):
    doc_id = data['doc_id']
    dept_id = data['dept_id']
    source_start = datetime.strptime(data['source_start'], '%Y-%m-%d').date()
    source_end = datetime.strptime(data['source_end'], '%Y-%m-%d').date()
    target_start = datetime.strptime(data['target_start'], '%Y-%m-%d').date()
    target_end = datetime.strptime(data['target_end'], '%Y-%m-%d').date()

    if (target_end - target_start).days != (source_end - source_start).days:
        raise Exception('源时间段和目标时间段天数不一致')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 查询源时间段内该医生的排班
        sql_select = f""" SELECT * FROM nsyy_gyl.on_call_schedule
            WHERE doc_id = '{doc_id}' AND dept_id = '{dept_id}' AND shift_date BETWEEN '{source_start}' AND '{source_end}' """
        source_schedules = db.query_all(sql_select)

        insert_data = []
        for row in source_schedules:
            shift_date_str = row['shift_date']
            shift_date_obj = datetime.strptime(shift_date_str, '%Y-%m-%d').date()
            days_diff = (shift_date_obj - source_start).days
            new_date = target_start + timedelta(days=days_diff)
            insert_data.append((
                doc_id,
                row['doc_name'],
                dept_id,
                row['dept_name'],  # 使用传入的科室名称，保持一致
                new_date.strftime('%Y-%m-%d'),
                row['shift_type'],
                row.get('notes', ''),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        insert_sql = """
            INSERT INTO nsyy_gyl.on_call_schedule
            (doc_id, doc_name, dept_id, dept_name, shift_date, shift_type, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            shift_type = VALUES(shift_type),
            notes = VALUES(notes)
        """
        db.execute_many(insert_sql, insert_data, need_commit=True)
        return f"成功复制 {len(insert_data)} 条排班记录"


def batch_delete_schedules(data):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        sql = "DELETE FROM nsyy_gyl.on_call_schedule WHERE doc_id = %s AND dept_id = %s AND shift_date BETWEEN %s AND %s"
        rows = db.execute(sql, (data['doc_id'], data['dept_id'], data['start_date'], data['end_date']), need_commit=True)
        return f"成功删除 {rows} 条记录"


""" 批量更新或插入指定医生在指定时间段内的排班 """
def batch_update_schedules(json_data):
    doctor_id = json_data.get('doc_id')
    doctor_name = json_data.get('doc_name')
    dept_id = json_data.get('dept_id')
    dept_name = json_data.get('dept_name')

    start_date = json_data.get('start_date')
    end_date = json_data.get('end_date')
    shift_type = json_data.get('shift_type')
    notes = json_data.get('notes', '')

    data = []
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    current = start
    while current <= end:
        shift_date_str = current.strftime('%Y-%m-%d')
        data.append((doctor_id, doctor_name, dept_id, dept_name, shift_date_str, shift_type, notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        current += timedelta(days=1)

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        sql = """
            INSERT INTO nsyy_gyl.on_call_schedule 
            (doc_id, doc_name, dept_id, dept_name, shift_date, shift_type, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            shift_type = VALUES(shift_type),
            notes = VALUES(notes)
        """
        result = db.execute_many(sql, data, need_commit=True)



def test():
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        doctors = db.query_all(f"SELECT distinct doc_name, dept_name FROM nsyy_gyl.on_call_schedule where doc_id is null ")

        doc_names = [item.get('doc_name') for item in doctors]
        doc_dict = {item.get('doc_name'): item.get('dept_name') for item in doctors}
        redis_client = redis.Redis(connection_pool=pool)
        for key, value in redis_client.hscan_iter('doctor_schedule'):
            value = json.loads(value)
            if value.get('姓名') in doc_names:
                print(value.get('职工工号'), value.get('姓名'), value.get('科室'), doc_dict.get(value.get('姓名')))
                # db.execute(f"UPDATE nsyy_gyl.on_call_schedule SET doc_id = '{value.get('职工工号')}' where doc_name = '{value.get('姓名')}'  ", need_commit=True)

# test()



import json

import redis

from datetime import datetime, date, timedelta
from itertools import groupby

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)

# 预约人紧急程度
APPT_URGENCY_LEVEL_KEY = 'APPT_URGENCY_LEVEL'
# 签到计数
APPT_SIGN_IN_NUM_KEY = 'APPT_SIGN_IN_NUM'
# 所有预约项目
APPT_PROJECTS_KEY = 'APPT_PROJECTS'
# 所有项目 按子类分组
APPT_PROJECTS_CATEGORY_KEY = 'APPT_PROJECTS_CATEGORY'
# 近7天所有项目剩余可预约数量
APPT_REMAINING_RESERVATION_QUANTITY_KEY = 'APPT_REMAINING_RESERVATION_QUANTITY'
# 坐诊医生
APPT_ATTENDING_DOCTOR_KEY = 'APPT_ATTENDING_DOCTOR'


"""
绑定用户
"""


def bind_user(id_card_no: str, openid: str):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select * from nsyy_gyl.appt_person_association ' \
                f'where id_card_no = \'{id_card_no}\' and openid = \'{openid}\' '
    appt_association = db.query_one(query_sql)

    fileds = 'id_card_no, openid'
    args = (id_card_no, openid)
    if not appt_association:
        insert_sql = f"INSERT INTO nsyy_gyl.appt_person_association ({fileds}) " \
                     f"VALUES {args}"
        db.execute(sql=insert_sql, need_commit=True)

    del db


"""
线上预约（微信小程序）   
"""


def online_appt(json_data):
    json_data['appt_type'] = appt_config.APPT_TYPE['online']
    json_data['urgency_level'] = appt_config.APPT_URGENCY_LEVEL['green']
    # 线上预约时自动绑定
    bind_user(json_data['id_card_no'], json_data['openid'])
    create_appt(json_data)


"""
线下预约（现场）
"""


def offline_appt(json_data):
    json_data['appt_type'] = appt_config.APPT_TYPE['offline']
    json_data['urgency_level'] = json_data.get('urgency_level') or appt_config.APPT_URGENCY_LEVEL['green']
    create_appt(json_data)


def create_appt(json_data):
    timestr = str(datetime.now())[:19]
    json_data['create_time'] = timestr
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))

    redis_client = redis.Redis(connection_pool=pool)
    quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['appt_proj_id']))
    quantity_data = json.loads(quantity_data)
    appt_date = json_data['appt_date']
    if not quantity_data[appt_date] \
            or int(quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity']) <= 0:
        raise Exception('当前时间没有可预约数量，请选择其他时间')

    json_data['state'] = appt_config.APPT_STATE['booked']
    # 线下预约时，直接签到
    if int(json_data.get('appt_type')) == appt_config.APPT_TYPE['offline']:
        json_data['sign_in_num'] = __get_signin_num(int(json_data['appt_proj_id']))
        json_data['sign_in_time'] = timestr
        json_data['state'] = appt_config.APPT_STATE['in_queue']

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = f"INSERT INTO nsyy_gyl.appt_record ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("预约记录入库失败! " + str(args))
    del db

    # 更新可预约数量
    quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity'] = \
        int(quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity']) - 1
    redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['appt_proj_id']),
                      json.dumps(quantity_data, default=str))

    # 缓存预约人的紧急程度
    key = json_data['id_card_no'] + '_' + str(json_data['appt_proj_type']) + '_' + str(json_data['appt_proj_category'])
    redis_client.hset(APPT_URGENCY_LEVEL_KEY, key, json_data['urgency_level'])

    # 如果是线上预约 直接绑定
    if json_data['appt_type'] == appt_config.APPT_TYPE['online']:
        bind_user(json_data['id_card_no'], json_data['openid'])


"""
查询预约记录, 有 openid 则根据 openid 查询，否则根据身份证号查询
"""


def query_appt(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 微信公众号查询（通过 openid）
    openid = json_data.get('openid')
    proj_id = json_data.get('proj_id')
    if openid:
        query_sql = f'select * from nsyy_gyl.appt_record where openid = \'{openid}\' '
    else:
        # oa 查询
        is_complete = int(json_data.get('is_completed')) if json_data.get('is_completed') else 0
        if is_complete:
            state_sql = 'state >= {}'.format(appt_config.APPT_STATE['completed'])
        else:
            state_sql = 'state < {}'.format(appt_config.APPT_STATE['completed'])

        today_str = str(datetime.now().date())
        proj_sql = f' and appt_proj_id = {proj_id} and appt_date = \'{today_str}\'' if proj_id else ''
        if proj_id:
            state_sql = 'state = {} '.format(appt_config.APPT_STATE['in_queue'])

        start_time = json_data.get("start_time")
        end_time = json_data.get("end_time")
        time_sql = f' and (time BETWEEN \'{start_time}\' AND \'{end_time}\') ' if start_time and end_time else ''

        id_card_no = json_data.get('id_card_no')
        id_card_no_sql = f' and id_card_no = {id_card_no}' if id_card_no else ''
        query_sql = f"select * from nsyy_gyl.appt_record where {state_sql}{proj_sql}{time_sql}{id_card_no_sql}"

    appts = db.query_all(query_sql)
    del db

    if proj_id:
        # proj_id 存在说明要查询排队列表，排队列表需要排队
        # 1. 按照紧急程度排序 降序
        # 2. 按照预约时间排序 升序
        # 3. 按照签到时间排序 升序
        appts = sorted(appts, key=lambda x: (-x['urgency_level'], x['appt_date_period'], x['sign_in_num']))

    total = len(appts)
    page_number = json_data.get("page_number")
    page_size = json_data.get("page_size")
    if page_number and page_size:
        # 计算要查询的起始索引和结束索引
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        # 使用切片操作从数据集中获取特定范围的数据
        appts = appts[start_index:end_index]

    return appts, total


"""
完成/取消/过号 预约
"""


def operate_appt(appt_id: int, type: int):
    cur_time = str(datetime.now())[:19]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if type == 1:
        # 预约完成
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['completed'])
    elif type == 2:
        # 取消
        op_sql = ' state = {}, cancel_time = \'{}\' '.format(appt_config.APPT_STATE['canceled'], cur_time)
    elif type == 3:
        # 过号
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['over_num'])

    update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)

    if type == 2:
        query_sql = f'select * from nsyy_gyl.appt_record where id = {int(appt_id)}'
        record = db.query_one(query_sql)
        if record:
            redis_client = redis.Redis(connection_pool=pool)
            proj_id = str(record.get('appt_proj_id'))
            period = str(record.get('appt_date_period'))
            appt_date = record.get('appt_date')
            quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, proj_id)
            if not quantity_data:
                return
            quantity_data = json.loads(quantity_data)
            quantity_data[appt_date][period]['quantity'] = int(quantity_data[appt_date][period].get('quantity') + 1)
            redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, proj_id, json.dumps(quantity_data, default=str))

    del db


"""
维护医生排班表
"""


def doctor_sched(json_data):
    for json in json_data:
        keys = ','.join(json.keys())
        values = tuple(json.values())
        key_string = ', '.join([f"{key} = {repr(value)}" for key, value in json.items()])

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        # 存在则更新 不存在则插入
        insert_sql = f'INSERT INTO nsyy_gyl.doctor_sched({keys}) ' \
                     f'VALUE {str(values)} ON DUPLICATE KEY UPDATE {key_string} '
        db.execute(sql=insert_sql, need_commit=True)
    del db


"""
预约签到
"""


def sign_in(appt_id: int, proj_id: int):
    sign_in_num = __get_signin_num(int(proj_id))
    sign_in_time = str(datetime.now())[:19]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    op_sql = ' sign_in_time = \'{}\', sign_in_num = {}, state = {} '.format(sign_in_time, sign_in_num, appt_config.APPT_STATE['in_queue'])
    update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db


"""
获取签到id
"""


def __get_signin_num(appt_proj_id: int):
    redis_client = redis.Redis(connection_pool=pool)
    num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, appt_proj_id) or 1
    redis_client.hset(APPT_SIGN_IN_NUM_KEY, appt_proj_id, int(num) + 1)
    return num


"""
是否是当天
"""


def __is_today(time_str):
    # 将时间字符串转换为日期对象
    time_obj = datetime.strptime(time_str, "%Y-%m-%d")
    # 获取当前日期
    current_date = date.today()
    # 如果日期相等，则是当天
    return time_obj.date() == current_date


"""
获取当前时间段
"""


def if_the_current_time_period_is_available(period):
    # 当天时间不超过 11:30 都可预约上午，时间不超过 17:30 都可预约下午
    now = datetime.now()
    if int(period) == 1 and now.hour <= 11 and now.minute < 30:
        return True
    if int(period) == 2 and now.hour <= 17 and now.minute < 30:
        return True
    return False


"""
查询所有预约项目
"""


def query_all_appt_project(type: int):
    # 1 先查询所有项目列表
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select proj_category, max(proj_name) as proj_name from nsyy_gyl.appt_project where proj_type = {type} group by proj_category'
    projectl = db.query_all(query_sql)
    del db

    # 2 查询项目剩余可预约数量
    today_date = str(datetime.today().date())
    redis_client = redis.Redis(connection_pool=pool)
    for proj in projectl:
        rooml = redis_client.hget(APPT_PROJECTS_CATEGORY_KEY, str(proj['proj_category']))
        rooml = json.loads(rooml)
        bookable_list = []
        for room in rooml:
            quantityd = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(room['id']))
            if quantityd:
                quantityd = json.loads(quantityd)
                for date, slots in quantityd.items():
                    for slot, info in slots.items():
                        if today_date == date and if_the_current_time_period_is_available(slot):
                            info['date'] = date
                            info['period'] = slot
                            bookable_list.append(info)
                            continue
                        info['date'] = date
                        info['period'] = slot
                        bookable_list.append(info)
        # 对数据按照日期进行分组
        sorted_data = sorted(bookable_list, key=lambda x: (x['date'], x['period']))

        data_list = []
        for key, group in groupby(sorted_data, key=lambda x: (x['date'], x['period'])):
            data_list.append({
                "date": key[0],
                "period": key[1],
                "list": list(group)
            })
        proj['bookable_list'] = data_list

    return projectl


"""
查询大厅列表/ 诊室列表
type=1 诊室
type=2 大厅
"""


def query_room_list(type: int):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    room_list = []
    if int(type) == 1:
        query_sql = 'select * from nsyy_gyl.appt_project '
        room_list = db.query_all(query_sql)
    elif int(type) == 2:
        query_sql = 'select proj_category as id, max(proj_name) as proj_name from nsyy_gyl.appt_project where is_group = 1 group by proj_category'
        room_list = db.query_all(query_sql)
    del db
    return room_list


"""
查询大厅/诊室等待列表 
type=1 诊室 wait_id 是 proj_id
type=2 大厅 wiat_id 是 proj_category
"""


def query_wait_list(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 微信公众号查询（通过 openid）
    wait_id = int(json_data.get('wait_id'))
    type = int(json_data.get('type'))
    wait_state = appt_config.APPT_STATE['in_queue']
    if int(type) == 1:
        condition_sql = f'appt_proj_id = {wait_id} and state = {wait_state}'
    elif int(type) == 2:
        condition_sql = f'appt_proj_category = {wait_id} and state = {wait_state}'

    query_sql = f'select * from nsyy_gyl.appt_record where {condition_sql} '
    appts = db.query_all(query_sql)
    del db

    # proj_id 存在说明要查询排队列表，排队列表需要排队
    # 1. 按照紧急程度排序 降序
    # 2. 按照预约时间排序 升序
    # 3. 按照签到时间排序 升序
    appts = sorted(appts, key=lambda x: (-x['urgency_level'], x['appt_date_period'], x['sign_in_num']))

    from collections import defaultdict
    transformed_data = defaultdict(list)
    for item in appts:
        key = (item['appt_proj_name'], item['doctor'], item['room'])
        transformed_data[key].append(item)

    result = []
    for key, value in transformed_data.items():
        appt_proj_name, doctor, room = key
        wait_list = value
        result.append({
            'appt_proj_name': appt_proj_name,
            'doctor': doctor,
            'room': room,
            'wait_list': wait_list
        })

    return result


"""
加载预约数据到内存
1. 当天预约人的紧急程度
2. 当天的签到计数
3. 近7天的可预约项目，包含剩余可预约数量
"""


def load_appt_data_into_cache():
    # 清空旧的预约数据
    redis_client = redis.Redis(connection_pool=pool)
    keys = redis_client.keys('APPT_*')
    for key in keys:
        redis_client.delete(key)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    today_str = str(datetime.now().date())
    # 查询当天所有未取消的预约, 缓存预约人的紧急情况 & 签到计数
    query_sql = f'select * from nsyy_gyl.appt_record where appt_date = \'{today_str}\' and state < 6'
    appt_record_list = db.query_all(query_sql)
    for record in appt_record_list:
        # 缓存紧急程度
        key = record['id_card_no'] + '_' + str(record['appt_proj_id'])
        redis_client.hset(APPT_URGENCY_LEVEL_KEY, key, record['urgency_level'])
        # 更新当天的签到计数
        appt_proj_id = int(record['appt_proj_id'])
        if record['sign_in_num']:
            sign_in_num = int(record['sign_in_num']) or -1
            old_num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, appt_proj_id) or 0
            old_num = int(old_num)
            if sign_in_num and old_num < sign_in_num:
                redis_client.hset(APPT_SIGN_IN_NUM_KEY, appt_proj_id, sign_in_num)

    # 缓存坐诊医生信息
    query_sql = 'select * from nsyy_gyl.appt_doctor_sched'
    doctor_schedl = db.query_all(query_sql)
    doctord = {}
    for item in doctor_schedl:
        key = f"{item['proj_id']}_{item['day_of_week']}_{item['period']}"
        if key not in doctord:
            doctord[key] = []
        doctord[key].append(item)

    for key, item in doctord.items():
        redis_client.hset(APPT_ATTENDING_DOCTOR_KEY, key, json.dumps(item, default=str))

    # 缓存所有项目
    query_sql = f'select * from nsyy_gyl.appt_project'
    appt_project_list = db.query_all(query_sql)
    group_by_categoryd = {}
    # 按 category 分组
    for item in appt_project_list:
        category = item['proj_category']
        if category not in group_by_categoryd:
            group_by_categoryd[category] = []
        group_by_categoryd[category].append(item)
    for category, list in group_by_categoryd.items():
        redis_client.hset(APPT_PROJECTS_CATEGORY_KEY, str(category), json.dumps(list, default=str))

    for appt_project in appt_project_list:
        redis_client.hset(APPT_PROJECTS_KEY, int(appt_project['id']), json.dumps(appt_project, default=str))
        # 缓存预约项目近 7 天的剩余可预约数量
        quantity = appt_project.get('proj_capacity')
        quantity_data = {}
        # 缓存近 7 天的可预约数量
        today = datetime.now().date()
        for i in range(7):
            nextday = today + timedelta(days=i)
            weekday_number = (nextday.weekday() + 1) % 8
            # 0=day 1=am 2=pm
            value = {}
            doct = redis_client.hget(APPT_ATTENDING_DOCTOR_KEY, f"{appt_project['id']}_{weekday_number}_1")
            if doct:
                doct = json.loads(doct)
                # 提取 doctor_name 字段并拼接成字符串
                doctorl = ', '.join([d['doctor_name'] for d in doct])
                value['1'] = {
                                'date': 'am',
                                'quantity': quantity,
                                'doctor': doctorl,
                                'room': appt_project.get('proj_room'),
                                'proj_name': appt_project.get('proj_name'),
                                'proj_id': appt_project.get('id'),
                                'proj_type': appt_project.get('proj_type'),
                                'proj_category': appt_project.get('proj_category')
                                }
            doct = redis_client.hget(APPT_ATTENDING_DOCTOR_KEY, f"{appt_project['id']}_{weekday_number}_2")
            if doct:
                doct = json.loads(doct)
                doctorl = ', '.join([d['doctor_name'] for d in doct])
                value['2'] = {'date': 'pm',
                              'quantity': quantity,
                              'doctor': doctorl,
                              'room': appt_project.get('proj_room'),
                              'proj_name': appt_project.get('proj_name'),
                              'proj_id': appt_project.get('id'),
                              'proj_type': appt_project.get('proj_type'),
                              'proj_category': appt_project.get('proj_category')
                              }
            if not doct and int(appt_project['proj_type']) == 2:
                # 院内项目不指定医生
                value['0'] = {'date': 'day',
                              'quantity': quantity,
                              'room': appt_project.get('proj_room'),
                              'proj_name': appt_project.get('proj_name'),
                              'proj_id': appt_project.get('id'),
                              'proj_type': appt_project.get('proj_type'),
                              'proj_category': appt_project.get('proj_category')
                              }

            if value:
                quantity_data[str(nextday)] = value
        if quantity_data:
            redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(appt_project['id']), json.dumps(quantity_data, default=str))

    # 根据已产生的预约更新剩余可预约数量
    today = datetime.now().date()
    query_sql = 'select * from nsyy_gyl.appt_record where appt_date >= {} and state < {}'.format(str(today), appt_config.APPT_STATE['canceled'])
    appt_record_list = db.query_all(query_sql)
    appt_proj_id_to_appt = {}
    for item in appt_record_list:
        appt_proj_id = item['appt_proj_id']
        if appt_proj_id not in appt_proj_id_to_appt:
            appt_proj_id_to_appt[appt_proj_id] = []
        appt_proj_id_to_appt[appt_proj_id].append(item)
    del db

    for proj_id, apptl in appt_proj_id_to_appt.items():
        data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(proj_id))
        if not data:
            continue
        data = json.loads(data)
        for appt in apptl:
            period = int(appt['appt_date_period'])
            datestr = appt['appt_date']
            if data.get(datestr):
                data[datestr][str(period)]['quantity'] = int(data[datestr][str(period)]['quantity']) - 1
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(proj_id),
                          json.dumps(data, default=str))


# 启动时直接加载数据
load_appt_data_into_cache()





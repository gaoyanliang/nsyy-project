import json

import redis
import requests

from datetime import datetime, date, timedelta
from itertools import groupby

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.composite_appointment.appt_config import \
    APPT_SIGN_IN_NUM_KEY, APPT_PROJECTS_KEY, APPT_REMAINING_RESERVATION_QUANTITY_KEY, \
    APPT_DOCTORS_KEY, APPT_EXECUTION_DEPT_INFO_KEY, APPT_ROOMS_KEY, \
    APPT_DAILY_AUTO_REG_RECORD_KEY, APPT_DOCTORS_BY_NAME_KEY, \
    APPT_ROOMS_BY_PROJ_KEY

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)

lock_redis_client = redis.Redis(connection_pool=pool)

database = 'nsyy_gyl'

# 可以预约的时间段
room_dict = {}
periodd = {'1': [1, 2, 3, 4, 5, 6, 7, 8], '2': [9, 10, 11, 12, 13, 14, 15, 16]}  # 1 上午 2 下午 3 全天
periodd['3'] = periodd['1'] + periodd['2']


def cache_capacity():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    print('开始缓存房间容量: ', datetime.now())
    # 缓存门诊项目近七天的可预约情况
    projl = db.query_all(f'select * from {database}.appt_project')
    for proj in projl:
        # 近 7 天的可预约数量
        pid = int(proj.get('id'))
        today = datetime.now().date()
        for i in range(7):
            nextday = today + timedelta(days=i)
            worktime = (nextday.weekday() + 1) % 8
            quantity = proj.get('nsnum')
            # 门诊项目
            schedl = db.query_all(
                f'select * from {database}.appt_scheduling where pid = {pid} and worktime = {worktime} and state = 1')
            for item in schedl:
                if str(item.get('rid')) not in room_dict:
                    room_dict[str(item.get('rid'))] = {}
                if str(nextday) not in room_dict[str(item.get('rid'))]:
                    room_dict[str(item.get('rid'))][str(nextday)] = {}
                hq = int(quantity / 8)
                if int(item.get('ampm')) == 1:
                    # 上午
                    room_dict[str(item.get('rid'))][str(nextday)]['1'] = {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq,
                                                                          '6': hq, '7': hq, '8': hq}
                else:
                    # 下午
                    room_dict[str(item.get('rid'))][str(nextday)]['2'] = {'9': hq, '10': hq, '11': hq, '12': hq,
                                                                          '13': hq, '14': hq, '15': hq,
                                                                          '16': hq}

    # 根据已产生的预约更新剩余可预约数量
    today = datetime.now().date()
    query_sql = 'select * from {}.appt_record where book_date >= \'{}\' and state < {} and is_doc_change = 0' \
        .format(database, str(today), appt_config.APPT_STATE['canceled'])
    recordl = db.query_all(query_sql)
    del db
    for record in recordl:
        period = str(record['book_period'])
        rid = str(record.get('rid'))
        datestr = record['book_date']
        time_slot = str(record['time_slot'])
        if room_dict[rid].get(datestr):
            room_dict[rid][datestr][period][time_slot] -= 1
        else:
            print('rid= ', rid, " date= ", datestr, ' period= ', period, ' slot= ', time_slot, '停诊')
    print('房间容量缓存完成: ', datetime.now())


cache_capacity()


def query_mem_data():
    return room_dict


"""
调用第三方系统
"""


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", json=param)
            data = response.text
            data = json.loads(data)
            if type != 'his_visit_reg':
                data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'his_visit_reg':
            # 门诊挂号 当天
            from tools import his_visit_reg
            data = his_visit_reg(param)
            # data = data.get('ResultCode')
        elif type == 'his_visit_check':
            # 查询当天患者挂号信息
            from tools import his_visit_check
            data = his_visit_check(param)
        elif type == 'his_yizhu_info':
            # 查询当天患者医嘱信息
            from tools import his_yizhu_info
            data = his_yizhu_info(param)
        elif type == 'his_pay_info':
            # 查询付款状态
            from tools import his_pay_info
            data = his_pay_info(param)
        elif type == 'orcl_db_read':
            # 根据 sql 查询数据
            from tools import orcl_db_read
            data = orcl_db_read(param)

    return data


"""
线上预约（微信小程序）   
"""


def online_appt(json_data):
    json_data['type'] = appt_config.APPT_TYPE['online']
    json_data['level'] = appt_config.APPT_URGENCY_LEVEL['green']
    json_data['state'] = appt_config.APPT_STATE['booked']
    json_data['pay_state'] = appt_config.appt_pay_state['oa_pay']
    create_appt(json_data)


"""
线下预约（现场）
"""


def offline_appt(json_data):
    json_data['type'] = appt_config.APPT_TYPE['offline']
    json_data['level'] = json_data.get('level') or appt_config.APPT_URGENCY_LEVEL['green']
    json_data['state'] = appt_config.APPT_STATE['booked']
    json_data['pay_state'] = appt_config.appt_pay_state['oa_pay']
    create_appt(json_data)


"""
校验是否可以继续预约
小程序预约和线下预约选择的时间段（上午/下午）不能更改
自助预约/医嘱预约可以根据容量调整时间段
"""


def check_appointment_quantity(book_info):
    def find_next_available(date, next_slot, period_list, find_in):
        capdict_am = room_dict[str(book_info['room'])][date]['1'] if room_dict[str(book_info['room'])][date].get(
            '1') else {}
        capdict_pm = room_dict[str(book_info['room'])][date]['2'] if room_dict[str(book_info['room'])][date].get(
            '2') else {}
        for s in period_list:
            if s <= 8 and int(find_in) in (1, 3):  # 上午时段
                if s >= next_slot and capdict_am.get(str(s), 0) > 0:
                    return date, s
            elif s > 8 and int(find_in) in (2, 3):  # 下午时段
                if s >= next_slot and capdict_pm.get(str(s), 0) > 0:
                    return date, s
        return None, None

    room = str(book_info['room'])
    book_date = book_info.get('date', None)
    period = str(book_info.get('period')) if book_info.get('period') else '3'

    current_slot = appt_config.appt_slot_dict[datetime.now().hour]
    if book_date and book_date != str(datetime.today().strftime("%Y-%m-%d")):
        current_slot = 9 if int(period) == 2 else 1
    # 如果指定了日期，直接在指定日期查找可用时段
    if book_date:
        next_date, next_slot = find_next_available(book_date, current_slot, periodd[period], int(period))
        if not next_slot:
            raise Exception("No available period found for the specified date and period")
        return next_date, next_slot

    today = datetime.today().strftime("%Y-%m-%d")
    last_date = book_info.get('last_date', today)
    last_slot = book_info.get('last_slot', None)
    # 查找从last_date和last_slot之后可用的时间和时间段
    for date in sorted(room_dict[room].keys()):
        if last_date and date < last_date:
            continue
        if date == last_date:
            slot_to_check = last_slot + 1 if last_slot is not None else current_slot
            next_date, next_slot = find_next_available(date, slot_to_check, periodd[period], period)
        else:
            next_date, next_slot = find_next_available(date, 1, periodd[period], period)

        if next_slot:
            return next_date, next_slot

    # return None, "No available period found"
    raise Exception("No available period found")


"""
创建预约
1. 线上小程序预约
2. 现场 oa 预约
3. 自助挂号机取号，查询预约记录时，根据挂号信息自动创建
4. 根据医嘱创建预约
"""


def create_appt(json_data, last_date=None, last_slot=None):
    json_data['create_time'] = str(datetime.now())[:19]
    if 'location_id' not in json_data:
        json_data['location_id'] = json_data['room']

    # 检查项目是否可以预约，以及获取预估时间段
    book_info = {'room': json_data['rid']}
    if last_date and last_slot:
        book_info['last_date'] = last_date
        book_info['last_slot'] = last_slot
    else:
        book_info['date'] = json_data['book_date'] if json_data.get('book_date') else str(datetime.today().strftime("%Y-%m-%d"))
        book_info['period'] = json_data['book_period'] if json_data.get('book_period') else '3'
    bdate, bslot = check_appointment_quantity(book_info)

    json_data['book_date'] = bdate
    json_data['time_slot'] = bslot
    if bslot < 9:
        json_data['book_period'] = 1
    else:
        json_data['book_period'] = 2

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 查询前方等待人数
    wait_state = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'],
                  appt_config.APPT_STATE['over_num'])
    condition_sql = ' and rid = {} '.format(int(json_data.get('rid')))
    if int(json_data['type']) >= appt_config.APPT_TYPE['advice_appt']:
        condition_sql = ' and pid = {} '.format(int(json_data.get('pid')))
    query_sql = f'select count(*) AS record_count from {database}.appt_record ' \
                f'where state in {wait_state} and book_date = \'{bdate}\' {condition_sql} '
    result = db.query_one(query_sql)
    json_data['wait_num'] = int(result.get('record_count'))

    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO {database}.appt_record ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("预约记录入库失败! sql = " + insert_sql)
    del db

    # 更新可预约数量
    date_str = json_data['book_date']
    period_str = str(json_data['book_period'])
    rid = str(json_data.get('rid'))
    room_dict[rid][date_str][period_str][str(bslot)] -= 1

    return last_rowid, bdate, bslot


"""
根据自助取号记录创建预约
    # 预约记录页面 -- 预约记录查询 -- 根据patient_id查询挂号记录
    # -- 没有挂号记录 原本预约记录
    # -- 有挂号记录  -- 已创建pass  
    #              -- 未创建：是否有预约记录 -- 有 设定预约记录为已在his付款（OA可退款） 无 创建预约
"""


def auto_create_appt_by_auto_reg(id_card_list, medical_card_list):
    condition_sql = ''
    if id_card_list and not medical_card_list:
        id_list = ', '.join(f"'{item}'" for item in id_card_list)
        condition_sql = condition_sql + f' b.身份证号 in ({id_list}) '
    elif not id_card_list and medical_card_list:
        medical_list = ', '.join(f"'{item}'" for item in medical_card_list)
        condition_sql = condition_sql + f' b.就诊卡号 in ({medical_list}) '
    elif id_card_list and medical_card_list:
        id_list = ', '.join(f"'{item}'" for item in id_card_list)
        medical_list = ', '.join(f"'{item}'" for item in medical_card_list)
        condition_sql = condition_sql + f'( b.就诊卡号 in ({medical_list}) or b.身份证号 in ({id_list}) )'

    param = {
        "type": "orcl_db_read",
        "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f'select a.*, b.身份证号 from 病人挂号记录 a left join 病人信息 b on a.病人id=b.病人id '
               f'where {condition_sql} and TRUNC(a.登记时间) = TRUNC(SYSDATE) order by a.登记时间 desc'
    }
    reg_recordl = call_third_systems_obtain_data('int_api', 'orcl_db_read', param)
    if not reg_recordl:
        # 不存在自助挂号记录
        return

    appt_recordl = []
    if id_card_list:
        id_list = ', '.join(f"'{item}'" for item in id_card_list)
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        query_sql = f'select * from {database}.appt_record ' \
                    f'where id_card_no in ({id_list}) and book_date = \'{str(date.today())}\' ' \
                    f'and doc_his_name is not null'
        appt_recordl = db.query_all(query_sql)
        del db

    # 再加一个判断条件 doc_dept_id 主要用来解决一个医生多个挂号身份的情况（例如 张方 皮肤科/烧伤科）
    record_dict = {(d['doc_his_name'], int(d['doc_dept_id']), int(d['patient_id'])): d for d in appt_recordl if d['doc_his_name']}
    redis_client = redis.Redis(connection_pool=pool)
    # 查询当天所有自助挂号的记录（pay no）集合
    created = redis_client.smembers(APPT_DAILY_AUTO_REG_RECORD_KEY)

    # 查询当天排班信息
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    worktime = (datetime.now().weekday() + 1) % 8
    query_sql = f"select * from {database}.appt_scheduling where worktime = {worktime}"
    daily_sched = db.query_all(query_sql)
    del db

    # 根据执行人和执行部门id查找项目 todo 自助挂号的项目如何做预约数量限制
    # 上午挂号的可以预约上午和下午，下午挂号的只能预约下午， 1=上午 2=下午
    period = '12' if datetime.now().hour < 12 else '2'
    for item in reg_recordl:
        # 判断是否已经创建过预约
        pay_no = item.get('NO')
        if pay_no in created:
            continue

        # 记录状态 1-正常的挂号或预约记录 ;2-退号记录；3-原始被退记录
        if int(item.get('记录状态')) == 2 or int(item.get('记录状态')) == 3:
            continue

        patient_id = item.get('病人ID')
        doc_his_name = item.get('执行人')
        doc_dept_id = item.get('执行部门ID')
        # 如果存在oa预约记录
        if (doc_his_name, int(doc_dept_id), int(patient_id)) in record_dict:
            exist_record = record_dict.get((doc_his_name, int(doc_dept_id), int(patient_id)))
            if int(exist_record.get('state')) < appt_config.APPT_STATE['in_queue'] and not exist_record.get('pay_no'):
                # oa 未签到 his中存在挂号记录 支持oa 退款
                condition_sql = ' pay_state = {} , pay_no = \'{}\' '.format(
                    appt_config.appt_pay_state['oa_his_both_pay'], pay_no)
            else:
                condition_sql = f' pay_no = \'{pay_no}\' '
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            update_sql = f'UPDATE {database}.appt_record SET {condition_sql} ' + \
                         ' WHERE id = {} '.format(exist_record.get('id'))
            db.execute(update_sql, need_commit=True)
            del db
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, pay_no)
            continue

        # 这里的 doctor 是 his name
        doctor_in_cache = redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, doc_his_name)
        if not doctor_in_cache:
            print('Exception: ', '预约系统中不存在 {} 医生，请联系护士及时维护门诊医生信息'.format(item.get('执行人')),
                  '医嘱信息: ', item)
            continue
            # raise Exception()
        doctor_in_cache = json.loads(doctor_in_cache)
        if type(doctor_in_cache) == dict:
            doctor_in_cache = [doctor_in_cache]

        doctor = doctor_in_cache[0]
        doctord = {int(dd['id']): dd for dd in doctor_in_cache}
        doc_ids = list(doctord.keys())
        if len(doc_ids) > 1:
            for doc_key, doc_value in doctord.items():
                if int(doc_value.get('dept_id')) == int(item.get('执行部门ID')):
                    doc_ids = [doc_value['id']]
                    break

        # 根据医生找到医生当天的坐诊项目
        target_proj = ''
        target_room = ''
        book_period = ''
        for s in daily_sched:
            if not s.get('did'):
                continue
            if int(s.get('did')) in doc_ids and str(s.get('ampm')) in period:
                target_proj = redis_client.hget(APPT_PROJECTS_KEY, str(s.get('pid')))
                target_proj = json.loads(target_proj)
                target_room = redis_client.hget(APPT_ROOMS_KEY, str(s.get('rid')))
                target_room = json.loads(target_room)
                book_period = s.get('ampm')
                doctor = doctord[int(s.get('did'))]
                break
        if not target_proj or not target_room:
            print('Exception: ', '未找到 {} 医生今天的坐诊信息'.format(item.get('执行人')), '医嘱信息: ', item)
            continue
            # raise Exception('未找到 {} 医生今天的坐诊信息'.format(item.get('执行人')))

        # 根据上面的信息，创建预约
        record = {'type': appt_config.APPT_TYPE['auto_appt'], 'patient_id': int(item.get('病人ID')),
                  'id_card_no': item.get('身份证号'), 'patient_name': item.get('姓名'),
                  'state': appt_config.APPT_STATE['booked'], 'pid': target_proj.get('id'),
                  'pname': target_proj.get('proj_name'), 'ptype': target_proj.get('proj_type'),
                  'rid': target_room.get('id'), 'room': target_room.get('no'), 'book_date': str(date.today()),
                  'book_period': book_period, 'level': 1, 'price': doctor.get('fee'), 'doc_id': doctor.get('id'),
                  'doc_his_name': doctor.get('his_name'), 'doc_dept_id': doctor.get('dept_id'), 'pay_no': pay_no,
                  'pay_state': appt_config.appt_pay_state['his_pay'],
                  'location_id': target_proj.get('location_id') if target_proj.get('location_id') else target_room.get(
                      'no')}
        create_appt(record)
        redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, pay_no)


"""
查询预约记录
过滤条件有： 是否完成，openid，id_card_no, name, proj_id, doctor, patient_id
query_from = 1 oa 所有预约记录查询
query_from = 2 oa 医生页面预约记录查询
query_from = 3 oa 分诊页面预约记录查询
query_from = 4 小程序查询
"""


def query_appt_record(json_data):
    # 查询预约记录时，如果患者是在远途自助机或者诊室找医生帮忙取号的，自动创建预约
    # 根据 patient_id 查询自助挂号信息
    query_from = json_data.get('query_from')
    id_card_list = json_data.get('id_card_list')
    medical_card_list = json_data.get('medical_card_list')
    if id_card_list or medical_card_list:
        auto_create_appt_by_auto_reg(id_card_list, medical_card_list)

    if not id_card_list and not medical_card_list and query_from == 4 and 'id_card_no' not in json_data:
        return [], 0

    is_completed = int(json_data.get('is_completed')) if json_data.get('is_completed') else 0
    condition_sql = ''
    if int(query_from) == 1:
        if is_completed:
            # 查询已完成的
            condition_sql = ' state >= {} '.format(appt_config.APPT_STATE['completed'])
        else:
            condition_sql = ' state > {} and state < {} '.format(appt_config.APPT_STATE['new'],
                                                                 appt_config.APPT_STATE['completed'])
    elif int(query_from) == 2:
        condition_sql = ' state = {} '.format(appt_config.APPT_STATE['completed']) \
            if is_completed else ' state > {} and state < {} '.format(appt_config.APPT_STATE['booked'],
                                                                      appt_config.APPT_STATE['over_num'])
    elif int(query_from) == 3:
        # 还需要pid
        condition_sql = ' state = {} and book_date = \'{}\' '.format(appt_config.APPT_STATE['booked'],
                                                                     str(date.today()))
    elif int(query_from) == 4:
        # 需要 patient id
        condition_sql = ' state >= {} '.format(appt_config.APPT_STATE['new'])

    rid = json_data.get('rid')
    condition_sql += f' and rid = {rid} ' if rid else ''
    openid = json_data.get('openid')
    condition_sql += f' and openid = \'{openid}\' ' if openid else ''
    if id_card_list:
        id_card_list = ', '.join(f"'{item}'" for item in id_card_list)
        condition_sql += f' and id_card_no in ({id_card_list}) '
    else:
        id_card_no = json_data.get('id_card_no')
        condition_sql += f' and id_card_no LIKE \'%{id_card_no}%\' ' if id_card_no else ''

    name = json_data.get('name')
    condition_sql += f" and patient_name LIKE \'%{name}%\' " if name else ''
    pid = json_data.get('pid')
    condition_sql += f' and pid = {pid}' if pid else ''
    doctor = json_data.get('doctor')
    condition_sql += f' and doc_his_name LIKE \'%{doctor}%\' ' if doctor else ''
    start_time, end_time = json_data.get("start_time"), json_data.get("end_time")
    condition_sql += f' and (book_date BETWEEN \'{start_time}\' AND \'{end_time}\') ' if start_time and end_time else ''
    patient_id = json_data.get('patient_id')
    condition_sql += f' and patient_id = \'{patient_id}\' ' if patient_id else ''

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from {database}.appt_record where {condition_sql}"
    appts = db.query_all(query_sql)
    del db

    total = len(appts)
    page_number, page_size = json_data.get("page_number"), json_data.get("page_size")
    if page_number and page_size:
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        appts = appts[start_index:end_index]

    return appts, total


"""
预约有修改，通过 socket 通知前端
"""


def push_patient(patient_name: str, socket_id: str):
    socket_data = {"patient_name": patient_name, "type": 300}
    data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", socket_data,
          "socket_id: ", socket_id)


"""
完成/取消/过号/报道 预约
"""


def operate_appt(appt_id: int, type: int):
    cur_time = str(datetime.now())[:19]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select * from {database}.appt_record where id = {int(appt_id)}'
    record = db.query_one(query_sql)
    if not record:
        raise Exception(f'预约id {appt_id} 预约记录不存在，请检查入参.')

    op_sql = ''
    if type == 1:
        if int(record.get('state')) == appt_config.APPT_STATE['completed']:
            # 已经完成的不再处理，防止重复点击
            return
        # 预约完成
        op_sql = ' state = {}, wait_num = 0 '.format(appt_config.APPT_STATE['completed'])
    elif type == 2:
        if int(record.get('state')) == appt_config.APPT_STATE['canceled']:
            # 已经完成的不再处理，防止重复点击
            return
        # 取消
        op_sql = ' state = {}, cancel_time = \'{}\' , wait_num = 0 '.format(appt_config.APPT_STATE['canceled'],
                                                                            cur_time)
    elif type == 3:
        # 过号
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['over_num'])
    elif type == 4:
        # 报道 医嘱项目分诊前有用户在小程序上点击
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['booked'])
    elif type == 5:
        # 修改退款状态
        op_sql = ' pay_state = {} '.format(appt_config.appt_pay_state['oa_refunded'])

    update_sql = f'UPDATE {database}.appt_record SET {op_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db

    # 预约完成，查询医嘱打印 引导单
    if type == 1 and int(record.get('type')) < 4:
        create_appt_by_doctor_advice(record.get('patient_id'),
                                     record.get('doc_his_name'), record.get('id_card_no'), appt_id,
                                     int(record.get('level')))

    # 取消预约，可预约数量 + 1
    if type == 2:
        period, appt_date, rid, slot = str(record.get('book_period')), record.get('book_date'), \
            str(record.get('rid')), str(record.get('time_slot'))
        if appt_date < str(date.today()):
            return
        if room_dict.get(rid) and room_dict.get(rid).get(appt_date) and room_dict.get(rid).get(appt_date).get(period):
            room_dict[rid][appt_date][period][slot] += 1

    # 过号，重新取号，排在最后
    if type == 3:
        sign_in({
            'appt_id': record.get('id'),
            'type': record.get('type'),
            'patient_id': record.get('patient_id'),
            'patient_name': record.get('patient_name'),
            'pid': record.get('pid'),
            'rid': record.get('rid')
        }, over_num=True)

    if type == 4:
        # 报道时需要给分诊护士发送 socket
        socket_id = 'w' + str(record.get('pid'))
        push_patient('', socket_id)
        return

    socket_id = 'd' + str(record.get('pid'))
    push_patient('', socket_id)
    socket_id = 'z' + str(record.get('rid'))
    push_patient('', socket_id)
    if type < 4:
        # 1=完成 2=取消 3=过号 都需要更新前方等待人数
        update_wait_num(int(record.get('rid')), int(record.get('pid')))


"""
根据医嘱创建预约
"""


def create_appt_by_doctor_advice(patient_id: str, doc_name: str, id_card_no, appt_id, level):
    param = {"type": "his_yizhu_info", 'patient_id': patient_id, 'doc_name': doc_name}
    doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)
    if not doctor_advice:
        # 没有医嘱直接返回
        return

    redis_client = redis.Redis(connection_pool=pool)
    # 按执行科室分组
    advice_dict = {}
    for item in doctor_advice:
        key = item.get('执行部门ID')
        if key not in advice_dict:
            advice_dict[key] = []
        advice_dict[key].append(item)

    last_date, last_slot = None, None
    other_advice = []
    for dept_id, advicel in advice_dict.items():
        # 根据医嘱中的执行科室id 查询出院内项目
        proj = redis_client.hget(APPT_EXECUTION_DEPT_INFO_KEY, str(dept_id))
        if not proj:
            # 所有未维护的执行科室 统一集合处理
            print('当前医嘱没有可预约项目，暂时使用默认项目创建预约，待后续维护', dept_id, ' ', param)
            other_advice += advicel
            continue
        else:
            proj = json.loads(proj)

        room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, proj.get('id')))
        record = {
            'father_id': int(appt_id),
            'id_card_no': id_card_no,
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": appt_config.APPT_TYPE['advice_appt'],
            "patient_id": patient_id,
            "patient_name": advicel[0].get('姓名'),
            "pid": proj.get('id'),
            "pname": proj.get('proj_name'),
            "ptype": proj.get('proj_type'),
            'rid': room.get('id'),
            'room': room.get('no'),
            "state": 0,
            "level": int(level),
            "location_id": proj.get('location_id') if proj.get('location_id') else room.get('no'),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdate, bslot = create_appt(record, last_date, last_slot)
        last_slot = bslot
        last_date = bdate

        # 按 pay_id 排序，后按 pay_id 分组
        advicel.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(advicel, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_doc_advice = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }

            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            fileds = ','.join(new_doc_advice.keys())
            args = str(tuple(new_doc_advice.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                del db
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)
            del db

    if other_advice:
        advice_record = {
            'father_id': int(appt_id),
            'id_card_no': id_card_no,
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": appt_config.APPT_TYPE['advice_appt'],
            "patient_id": patient_id,
            "patient_name": other_advice[0].get('姓名'),
            "pid": 79,
            "pname": "其他项目",
            'rid': 153,
            'room': '当前诊室',
            "ptype": 2,
            "state": 0,
            "level": int(level),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdata, bslot = create_appt(advice_record, last_date, last_slot)
        # 按 pay_id 排序，后按 pay_id 分组
        other_advice.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        for key, group in groupby(other_advice, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_doc_advice1 = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }
            fileds = ','.join(new_doc_advice1.keys())
            args = str(tuple(new_doc_advice1.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                print("医嘱记录入库失败! sql = " + insert_sql)
        del db


"""
更新医嘱
"""


def update_advice(json_data):
    father_appt_id = int(json_data.get('appt_id'))
    patient_id = int(json_data.get('patient_id'))
    doc_name = json_data.get('doc_name')
    param = {"type": "his_yizhu_info", 'patient_id': patient_id, 'doc_name': doc_name}
    new_doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)
    if not new_doctor_advice:
        # 没有医嘱直接返回
        return

    level = json_data.get('level')
    redis_client = redis.Redis(connection_pool=pool)

    # 按执行科室分组
    new_advicel = {}
    for item in new_doctor_advice:
        key = item.get('执行部门ID')
        if key not in new_advicel:
            new_advicel[key] = []
        new_advicel[key].append(item)

    # 取之前创建的预约的最后一条
    last_slot, last_date = None, None
    other_advice = []
    for dept_id, advicel in new_advicel.items():
        # 根据医嘱中的执行科室id 查询出院内项目
        proj = redis_client.hget(APPT_EXECUTION_DEPT_INFO_KEY, str(dept_id))
        if not proj:
            pid = 79
        else:
            proj = json.loads(proj)
            pid = int(proj.get('id'))

        # 判断是否需要更新
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        query_sql = f'select * from {database}.appt_record ' \
                    f'where book_date = \'{str(date.today())}\' and patient_id = {patient_id} and pid = {pid} '
        created = db.query_one(query_sql)
        del db

        if created:
            # 更新医嘱
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            appt_id = int(created.get('id'))
            data = db.query_all(f'select pay_id from {database}.appt_doctor_advice where appt_id = {appt_id}')
            pay_ids = [item['pay_id'] for item in data]
            advicel.sort(key=lambda x: x['NO'])
            for key, group in groupby(advicel, key=lambda x: x['NO']):
                if key in pay_ids:
                    continue
                group_list = list(group)
                combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
                total_price = sum(item['实收金额'] for item in group_list)
                # 使用第一个元素的字典结构来创建合并后的记录
                new_json_data = {
                    'appt_id': appt_id,
                    'pay_id': group_list[0].get('NO'),
                    'advice_desc': combined_advice_desc,
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': total_price
                }

                fileds = ','.join(new_json_data.keys())
                args = str(tuple(new_json_data.values()))
                insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
                last_rowid = db.execute(sql=insert_sql, need_commit=True)
                if last_rowid == -1:
                    del db
                    raise Exception("医嘱记录入库失败! sql = " + insert_sql)
            del db
        else:
            # 新增医嘱
            if not proj:
                other_advice += advicel
                continue

            room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, pid))
            record = {
                'father_id': father_appt_id,
                "book_date": str(date.today()),
                "book_period": 1 if datetime.now().hour < 12 else 2,
                "type": appt_config.APPT_TYPE['advice_appt'],
                "patient_id": patient_id,
                "patient_name": advicel[0].get('姓名'),
                "pid": pid,
                "pname": proj.get('proj_name'),
                "ptype": proj.get('proj_type'),
                'rid': room.get('id'),
                'room': room.get('no'),
                "state": 0,
                "level": int(level),
                "location_id": proj.get('location_id') if proj.get('location_id') else room.get('no'),
            }
            # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
            new_appt_id, bdate, bslot = create_appt(record, last_date, last_slot)
            last_slot = bslot
            last_date = bdate
            # 按 pay_id 排序，后按 pay_id 分组
            advicel.sort(key=lambda x: x['NO'])
            # 根据 pay_id 分组并计算每个分组的 price 总和
            for key, group in groupby(advicel, key=lambda x: x['NO']):
                group_list = list(group)
                combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
                total_price = sum(item['实收金额'] for item in group_list)
                # 使用第一个元素的字典结构来创建合并后的记录
                new_data = {
                    'appt_id': new_appt_id,
                    'pay_id': group_list[0].get('NO'),
                    'advice_desc': combined_advice_desc,
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': total_price
                }

                db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                            global_config.DB_DATABASE_GYL)
                fileds = ','.join(new_data.keys())
                args = str(tuple(new_data.values()))
                insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
                last_rowid = db.execute(sql=insert_sql, need_commit=True)
                if last_rowid == -1:
                    del db
                    raise Exception("医嘱记录入库失败! sql = " + insert_sql)
                del db

    if other_advice:
        record = {
            'father_id': father_appt_id,
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": appt_config.APPT_TYPE['advice_appt'],
            "patient_id": patient_id,
            "patient_name": other_advice[0].get('姓名'),
            "pid": 79,
            "pname": "其他项目",
            "ptype": 2,
            'rid': 153,
            'room': '当前诊室',
            "state": 0,
            "level": int(level),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdate, bslot = create_appt(record, last_date, last_slot)
        # 按 pay_id 排序，后按 pay_id 分组
        other_advice.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(other_advice, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_data1 = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }

            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            fileds = ','.join(new_data1.keys())
            args = str(tuple(new_data1.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                del db
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)
            del db


"""
住院患者医嘱查询
"""


def inpatient_advice(json_data):
    advice_dict = {}
    param = {"type": "his_yizhu_info", 'patient_id': json_data.get('patient_id'),
             'doc_name': json_data.get('doc_name')}
    doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)
    if not doctor_advice:
        # 没有医嘱直接返回
        return advice_dict

    # 按执行科室分组
    for item in doctor_advice:
        key = item.get('执行部门ID')
        item['patient_id'] = json_data.get('patient_id')
        if key not in advice_dict:
            advice_dict[key] = []
        advice_dict[key].append(item)
    return advice_dict


def inpatient_advice_create(json_data):
    advicel = json_data.get('advicel')
    if not advicel:
        return
    patient_info = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read",
        "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": "select * from 病人信息 where 病人ID = '{}' ".format(advicel[0].get('patient_id'))
    })
    if patient_info:
        redis_client = redis.Redis(connection_pool=pool)
        dept_id = advicel[0].get('执行部门ID')
        proj = redis_client.hget(APPT_EXECUTION_DEPT_INFO_KEY, str(dept_id))
        if not proj:
            # 所有未维护的执行科室 统一集合处理
            print('当前医嘱没有可预约项目，暂时使用默认项目创建预约，待后续维护, dept_id = ', dept_id)
            proj = {"id": 79, "proj_name": '其他项目', "proj_type": 2}
        else:
            proj = json.loads(proj)
        room = redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, proj.get('id'))
        if not room:
            room = {'id': 153, 'no': '当前诊室'}
        else:
            room = json.loads(room)

        # todo 住院患者创建的检查预约是否直接报道 ？？？？？？
        record = {
            'father_id': 0,
            'id_card_no': patient_info.get('身份证号'),
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": appt_config.APPT_TYPE['inpatient_advice'],
            "patient_id": patient_info.get('病人ID'),
            "patient_name": advicel[0].get('姓名'),
            "pid": proj.get('id'),
            "pname": proj.get('proj_name'),
            "ptype": proj.get('proj_type'),
            'rid': room.get('id'),
            'room': room.get('no'),
            "state": 1,
            "level": json_data.get('level') if json_data.get('level') else 1,
            "location_id": proj.get('location_id') if proj.get('location_id') else room.get('no'),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdate, bslot = create_appt(record)
        # 按 pay_id 排序，后按 pay_id 分组
        advicel.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        for key, group in groupby(advicel, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_data2 = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }
            fileds = ','.join(new_data2.keys())
            args = str(tuple(new_data2.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                print("医嘱记录入库失败! sql = " + insert_sql)
        del db
    else:
        raise Exception('根据患者信息查询不到病人信息', ' 病人id = ', advicel[0].get('patient_id'))


"""
预约签到
1. 第一次签到 （his 取号/ 医嘱项目检查付款状态）
2. 过号 重新取号
"""


def sign_in(json_data, over_num: bool):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)
    appt_id = int(json_data['appt_id'])
    appt_type = int(json_data.get('type'))
    patient_id = int(json_data.get('patient_id'))

    if over_num:
        # 如果过号 直接重新取号
        sign_in_num = __get_signin_num(int(json_data.get('pid')))
        sign_in_time = str(datetime.now())[:19]
        op_sql = ' sign_in_time = \'{}\', sign_in_num = {}, state = {} '.format(sign_in_time, sign_in_num,
                                                                                appt_config.APPT_STATE['in_queue'])
        update_sql = f'UPDATE {database}.appt_record SET {op_sql} WHERE id = {appt_id} '
        db.execute(sql=update_sql, need_commit=True)
        del db
        return

    query_sql = f'select * from {database}.appt_record where id = {appt_id}'
    record = db.query_one(query_sql)
    if int(record.get('state')) > appt_config.APPT_STATE['booked']:
        # 第一次签到 如果发现已经签到过，直接返回
        del db
        return

    # 如果是医嘱预约，检查付款状态 (type = 5 住院医嘱不需要检查付款状态)
    if appt_type == appt_config.APPT_TYPE['advice_appt']:
        # 根据预约id 查询医嘱记录
        query_sql = f'select pay_id from {database}.appt_doctor_advice where appt_id = {appt_id}'
        advicel = db.query_all(query_sql)
        if advicel:
            pay_ids = [item['pay_id'] for item in advicel]
            param = {"type": "his_pay_info", "patient_id": patient_id, "no_list": pay_ids}
            his_pay_info = call_third_systems_obtain_data('his_info', 'his_pay_info', param)
            is_ok = False
            # 如果有多个付款项目，只要有一个付款的就允许签到
            for p in his_pay_info:
                if int(p.get('记录状态')) != 0:
                    is_ok = True
                    break
            if not is_ok:
                raise Exception('所有医嘱项目均未付款，请及时付款后再签到', param)

    # 签到前到 his 中取号, 小程序预约，现场预约需要取号。 自助挂号机挂号的预约不需要挂号
    pay_sql = ''
    if appt_type in (1, 2):
        # 先查询是否有挂号记录
        id_card_no = record.get('id_card_no')
        appt_doctor = record.get('doc_his_name')
        param = {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": f'select a.*, b.身份证号 from 病人挂号记录 a left join 病人信息 b on a.病人id=b.病人id '
                   f'where b.身份证号=\'{id_card_no}\' and a.执行人 = \'{appt_doctor}\' and TRUNC(a.登记时间) = TRUNC(SYSDATE) order by a.登记时间 desc'
        }
        reg_recordl = call_third_systems_obtain_data('int_api', 'orcl_db_read', param)
        if reg_recordl:
            # 如果存在挂号记录，更新 pay_state pay_no
            pay_sql = ', pay_state = {} , pay_no = \'{}\' '. \
                format(appt_config.appt_pay_state['oa_his_both_pay'],
                       reg_recordl[0].get('NO')) if int(record.get('pay_state')) != 3 else ''
        else:
            param = {"type": "his_visit_reg", "patient_id": patient_id, "AsRowid": 2116, "PayAmt": 0.01}
            doctorinfo = redis_client.hget(APPT_DOCTORS_KEY, str(json_data.get('doc_id')))
            if doctorinfo:
                doctorinfo = json.loads(doctorinfo)
                param = {"type": "his_visit_reg", "patient_id": patient_id,
                         "AsRowid": int(doctorinfo.get('appointment_id')),
                         "PayAmt": float(doctorinfo.get('fee'))}
            sign_data = call_third_systems_obtain_data('his_socket', 'his_visit_reg', param)
            his_socket_ret_code = sign_data.get('ResultCode')
            if his_socket_ret_code != '0':
                raise Exception('在 his 中取号失败， 签到失败, Result: ', sign_data)

    # 判断是否需要更换项目
    change_proj_sql = ''
    bdate, bslot = None, None
    if json_data.get('rid') and json_data.get('room'):
        # 检查项目是否可以预约
        book_info = {'room': json_data['rid']}
        book_info['date'] = json_data['book_date']
        book_info['period'] = json_data['book_period']
        bdate, bslot = check_appointment_quantity(book_info)
        change_proj_sql = ', rid = {}, room = \'{}\' , time_slot = {} '. \
            format(json_data['rid'], json_data['room'], bslot)

    sign_in_num = __get_signin_num(int(json_data.get('pid')))
    sign_in_time = str(datetime.now())[:19]
    op_sql = ' sign_in_time = \'{}\', sign_in_num = {}, state = {} '.format(sign_in_time, sign_in_num,
                                                                            appt_config.APPT_STATE['in_queue'])
    update_sql = f'UPDATE {database}.appt_record SET {op_sql}{change_proj_sql}{pay_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db

    rid = json_data.get('rid')
    proj_id = json_data.get('pid')

    # 如果更换房间，更新可预约数量
    if bdate and bslot:
        period = str(json_data.get('book_period'))
        appt_date = json_data['book_date']
        room_dict[str(rid)][appt_date][period][str(bslot)] -= 1

    # 签到后 更新等待人数
    update_wait_num(int(rid), int(proj_id))

    patient_name = json_data.get('patient_name')
    # 推送给大厅
    socket_id = 'd' + str(proj_id)
    push_patient(patient_name, socket_id)
    # 签到成功之后，将患者名字推送给诊室
    socket_id = 'z' + str(rid)
    push_patient(patient_name, socket_id)
    # 签到之后给医生发送 socket
    socket_id = 'y' + str(rid)
    push_patient('', socket_id)


"""
获取签到id
"""


def __get_signin_num(appt_proj_id: int):
    redis_client = redis.Redis(connection_pool=pool)
    num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, appt_proj_id) or 0
    redis_client.hset(APPT_SIGN_IN_NUM_KEY, appt_proj_id, int(num) + 1)
    return int(num) + 1


"""
获取当前时间段 （上午/下午）
"""


def if_the_current_time_period_is_available(period):
    # 0 全天 1 上午 2 下午
    # 当天时间不超过 11:30 都可预约上午，时间不超过 17:30 都可预约下午
    now = datetime.now()
    if int(period) == 0:
        return True
    if int(period) == 1 and now.hour <= 11:
        return True
    if int(period) == 2 and now.hour <= 23:
        return True
    return False


"""
呼叫 （通过 socket 实现）
"""


def call(json_data):
    socket_id = json_data.get('socket_id')
    room = ' '.join(list(json_data.get('proj_room')))
    socket_data = {"msg": '请患者 {} 到 {} 诊室就诊'.format(json_data.get('name'), room), "type": 200}
    data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", socket_data,
          'socket_id: ', socket_id)


"""
叫号下一个 
"""


def next_num(id, is_group):
    data_list, doctor, project = query_wait_list({'type': 1, 'wait_id': id})

    # 更新列表中第一个为处理中
    if data_list:
        wait_list = data_list[0].get('wait_list')
        if wait_list and wait_list[0].get('state') == appt_config.APPT_STATE['processing']:
            raise Exception('当前存在处理中的病患，无法执行下一个操作，请先处理当前患者')

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        update_sql = 'UPDATE {}.appt_record SET state = {} WHERE id = {} ' \
            .format(database, appt_config.APPT_STATE['processing'], data_list[0].get('wait_list')[0].get('id'))
        db.execute(sql=update_sql, need_commit=True)
        del db

        # 呼叫患者
        json_data = {
            'socket_id': 'd' + str(is_group) if is_group != -1 else 'z' + str(id),
            'name': data_list[0].get('wait_list')[0].get('patient_name'),
            'proj_room': data_list[0].get('wait_list')[0].get('room')
        }
        call(json_data)
        data_list[0].get('wait_list')[0]['state'] = appt_config.APPT_STATE['processing']

    return data_list


"""
查询所有预约项目
"""


def query_all_appt_project(type: int):
    redis_client = redis.Redis(connection_pool=pool)
    projl = redis_client.hvals(APPT_PROJECTS_KEY)
    projl = [json.loads(proj) for proj in projl]

    # 2 查询项目剩余可预约数量
    today_str = str(datetime.now().date())
    data = []
    for proj in projl:
        if int(proj.get('proj_type')) != int(type):
            continue
        data_from_last_seven = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(proj.get('id')))
        bookable_list = []
        if data_from_last_seven:
            data_from_last_seven = json.loads(data_from_last_seven)
            for date, slots in data_from_last_seven.items():
                for slot, info in slots.items():
                    if today_str == date and not if_the_current_time_period_is_available(slot):
                        continue
                    for rid, rinfo in info.items():
                        if not room_dict.get(str(rid)) or not room_dict[str(rid)].get(date) \
                                or not room_dict[str(rid)][date].get(str(slot)):
                            continue
                        quantity = room_dict[str(rid)][date][str(slot)]
                        info[rid]['hourly_quantity'] = quantity
                        current_slot = appt_config.appt_slot_dict[datetime.now().hour]
                        if quantity:
                            total_quantity = 0
                            for key, value in quantity.items():
                                if int(key) >= int(current_slot):
                                    total_quantity += int(value)
                            info[rid]['quantity'] = total_quantity
                        else:
                            info[rid]['quantity'] = 0
                        if rinfo.get('doc_id') and redis_client.hget(APPT_DOCTORS_KEY, str(rinfo.get('doc_id'))):
                            info[rid]['doctor'] = json.loads(
                                redis_client.hget(APPT_DOCTORS_KEY, str(rinfo.get('doc_id'))))
                    info['date'], info['period'] = date, slot
                    bookable_list.append(info)
        # 对数据按照日期进行分组
        sorted_data = sorted(bookable_list, key=lambda x: (x['date'], x['period']))
        data_list = []
        for key, group in groupby(sorted_data, key=lambda x: (x['date'], x['period'])):
            list_group = list(group)
            list_group[0].pop('date')
            list_group[0].pop('period')
            list_group = list(list_group[0].values())
            # data_list.append(list_group)
            for item in list_group:
                item['date'], item['period'] = key[0], key[1]
            data_list.append({
                "date": key[0],
                "period": key[1],
                "list": list_group
            })
        proj['bookable_list'] = data_list
        data.append(proj)

    return data


"""
查询大厅列表/ 诊室列表
type=1 诊室
type=2 大厅
"""


def query_room_list(type: int):
    redis_client = redis.Redis(connection_pool=pool)
    room_list = []
    if int(type) == 1:
        room_list = redis_client.hvals(APPT_ROOMS_KEY)
        room_list = [json.loads(item) for item in room_list]
    elif int(type) == 2:
        room_list = redis_client.hvals(APPT_PROJECTS_KEY)
        room_list = [json.loads(item) for item in room_list]
        room_list = [item for item in room_list if int(item['is_group']) == 1]
    return room_list


"""
查询大厅/诊室等待列表 
type=1 诊室 wait_id 是 rid 房间号
type=2 大厅 wiat_id 是 pid 项目id

"""


def query_wait_list(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)

    wait_id = int(json_data.get('wait_id'))
    type = int(json_data.get('type'))

    doctor = ''
    proj = ''
    if type == 1:
        period = 1 if datetime.now().hour < 12 else 2
        worktime = (datetime.now().weekday() + 1) % 8
        query_sql = f"select * from {database}.appt_scheduling " \
                    f"where rid = {int(wait_id)} and worktime = {worktime} and ampm = {period} and state = 1"
        daily_sched = db.query_all(query_sql)
        for item in daily_sched:
            if redis_client.hexists(APPT_PROJECTS_KEY, str(item.get('pid'))):
                proj = json.loads(redis_client.hget(APPT_PROJECTS_KEY, str(item.get('pid'))))
            if not item.get('did'):
                continue
            if redis_client.hexists(APPT_DOCTORS_KEY, str(item.get('did'))):
                doctor = json.loads(redis_client.hget(APPT_DOCTORS_KEY, str(item.get('did'))))
                if not doctor.get('photo'):
                    doctor['photo'] = appt_config.default_photo
                break
    if type == 2 and redis_client.hexists(APPT_PROJECTS_KEY, str(wait_id)):
        proj = redis_client.hget(APPT_PROJECTS_KEY, str(wait_id))
        proj = json.loads(proj)

    # proj_id 存在说明要查询排队列表，排队列表需要排队
    # 1. 按照紧急程度排序 降序
    # 2. 按照预约时间排序 升序
    # 3. 按照签到时间排序 升序
    wait_state = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'],
                  appt_config.APPT_STATE['over_num'])
    condition_sql = f' and rid = {wait_id} '
    if int(type) == 2:
        condition_sql = f' and pid = {wait_id} '
    query_sql = f'select * from {database}.appt_record ' \
                f'where state in {wait_state} and book_date = \'{str(date.today())}\' {condition_sql} '
    recordl = db.query_all(query_sql)
    recordl = sorted(recordl,
                     key=lambda x: (-x['state'], x['sort_num'], -x['level'], x['book_period'], x['sign_in_num']))

    # 查询医嘱
    if recordl:
        appt_id_list = [record.get('id') for record in recordl]
        ids = ', '.join(map(str, appt_id_list))
        query_sql = f'select * from {database}.appt_doctor_advice where appt_id in ({ids}) '
        advicel = db.query_all(query_sql)
        # 用于存储拼接后的结果
        advice_info = {}
        for record in advicel:
            appt_id, advice_desc = record['appt_id'], record['advice_desc']
            if appt_id in advice_info:
                advice_info[appt_id] += '; ' + advice_desc
            else:
                advice_info[appt_id] = advice_desc
        for record in recordl:
            record['advice_desc'] = advice_info.get(record['id']) if advice_info.get(record['id']) else ''
    del db

    from collections import defaultdict
    transformed_data = defaultdict(list)
    for item in recordl:
        transformed_data[item['room']].append(item)

    result = []
    for key, value in transformed_data.items():
        wait_list = value
        for index, item in enumerate(wait_list):
            item["sort_index"] = index + 1  # 排序字段从 1 开始, 保证前后端列表顺序一致
        if len(wait_list) > 0:
            ret = {
                'appt_proj_name': wait_list[0].get('pname'),
                'doctor': wait_list[0].get('doc_his_name'),
                'room': wait_list[0].get('room'),
                'wait_list': wait_list
            }
            result.append(ret)

    return result, doctor, proj


"""
更新医嘱付款状态
"""


def update_doctor_advice_pay_state(idl):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    ids = ", ".join(map(str, idl))
    update_sql = f'update {database}.appt_doctor_advice set state = 1 where id in ({ids})'
    db.execute(update_sql, need_commit=True)
    del db


"""
查询医嘱
"""


def query_advice_by_father_appt_id(json_data):
    father_appt_id = json_data.get('father_appt_id')
    patient_id = json_data.get('patient_id')
    condition_sql = ''
    if father_appt_id:
        condition_sql = f'father_id = {int(father_appt_id)} '
    if patient_id:
        # todo 是否仅查询当天的 today_str = str(date.today())
        condition_sql = f'type >= 4 and patient_id = {int(patient_id)}'
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = f"select * from {database}.appt_record where {condition_sql}"
    appts = db.query_all(query_sql)

    for record in appts:
        appt_id = int(record.get('id'))
        record['time_slot'] = appt_config.APPT_PERIOD_INFO.get(int(record['time_slot']))
        query_sql = f'select * from {database}.appt_doctor_advice where appt_id = {appt_id}'
        record['doctor_advice'] = db.query_all(query_sql)
    del db
    return appts


"""
查询排班信息
"""


def query_sched(rid: int):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)

    query_sql = f'select * from {database}.appt_scheduling where rid = {rid}'
    all_sched = db.query_all(query_sql)
    del db

    for schedl in all_sched:
        if schedl.get('did'):
            schedl['doctor'] = json.loads(redis_client.hget(APPT_DOCTORS_KEY, str(schedl.get('did'))))
        if schedl.get('pid'):
            schedl['project'] = json.loads(redis_client.hget(APPT_PROJECTS_KEY, str(schedl.get('pid'))))
            schedl['room'] = json.loads(redis_client.hget(APPT_ROOMS_KEY, str(schedl.get('rid'))))
    return all_sched


"""
查询医生列表
"""


def query_doc():
    redis_client = redis.Redis(connection_pool=pool)
    all_doc = redis_client.hgetall(APPT_DOCTORS_KEY)
    data = []
    for did, doc in all_doc.items():
        data.append(json.loads(doc))
    return data


"""
更新医生信息
"""


def update_doc(json_data):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = ' name = \'{}\' '.format(json_data.get('name')) if json_data.get('name') else ''
    condition_sql += ', no = {} '.format(json_data.get('no')) if json_data.get('no') else ''
    condition_sql += ', dept_id = {} '.format(json_data.get('dept_id')) if json_data.get('dept_id') else ''
    condition_sql += ', dept_name = \'{}\' '.format(json_data.get('dept_name')) if json_data.get('dept_name') else ''
    condition_sql += ', career = \'{}\' '.format(json_data.get('career')) if json_data.get('career') else ''
    condition_sql += ', fee = {} '.format(json_data.get('fee')) if json_data.get('fee') else ''
    condition_sql += ', appointment_id = {} '.format(json_data.get('appointment_id')) if json_data.get(
        'appointment_id') else ''
    condition_sql += ', photo = \'{}\' '.format(json_data.get('photo')) if json_data.get('photo') else ''
    condition_sql += ', `desc` = \'{}\' '.format(json_data.get('desc')) if json_data.get('desc') else ''
    condition_sql += ', phone = \'{}\' '.format(json_data.get('phone')) if json_data.get('phone') else ''

    id = int(json_data.get('id'))
    update_sql = f'UPDATE {database}.appt_doctor SET {condition_sql} ' \
                 f' WHERE id = {id}'
    db.execute(update_sql, need_commit=True)

    doc_info = db.query_one(f'select * from {database}.appt_doctor WHERE id = {id}')
    if doc_info:
        redis_client.hset(APPT_DOCTORS_KEY, str(id), json.dumps(doc_info, default=str))
        doc_by_hisname = redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, doc_info.get('his_name'))
        doc_by_hisname = json.loads(doc_by_hisname)
        if type(doc_by_hisname) == dict:
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, doc_info.get('his_name'), json.dumps(doc_info, default=str))
        elif type(doc_by_hisname) == list:
            doc_list = [doc_info]
            for doc in doc_by_hisname:
                if int(doc.get('id')) != int(id):
                    doc_list.append(doc)
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, doc_info.get('his_name'), json.dumps(doc_list, default=str))

    del db


"""
查询项目列表
"""


def query_proj():
    redis_client = redis.Redis(connection_pool=pool)
    all_proj = redis_client.hgetall(APPT_PROJECTS_KEY)
    data = []
    for pid, proj in all_proj.items():
        data.append(json.loads(proj))
    return data


"""
坐诊房间列表
"""


def room_list():
    redis_client = redis.Redis(connection_pool=pool)
    rooml = redis_client.hvals(APPT_ROOMS_KEY)
    parsed_values = []
    for value in rooml:
        parsed_value = json.loads(value)
        parsed_values.append(parsed_value)

    return parsed_values


"""
更换医生排班信息
房间不支持改变， 同一个房间同一天同一个时间段，仅可以做一个项目，且近坐一个医生
"""


def update_sched(json_data):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    id = int(json_data.get('id'))
    query_sql = f'select * from {database}.appt_scheduling where id = {id}'
    old_sched = db.query_one(query_sql)

    rid = int(json_data.get('rid'))
    condition_sql = f' rid = {rid} '
    condition_sql += ', did = {} '.format(int(json_data.get('did'))) if json_data.get('did') else ''
    condition_sql += ', pid = {} '.format(int(json_data.get('pid'))) if json_data.get('pid') else ''
    condition_sql += ', state = {} '.format(int(json_data.get('state'))) if json_data.get('state') else ''
    condition_sql += ', change_reason = \'{}\' '.format(json_data.get('change_reason')) if json_data.get(
        'change_reason') else ''
    update_sql = f'UPDATE {database}.appt_scheduling SET {condition_sql} ' \
                 f' WHERE id = {id}'
    db.execute(update_sql, need_commit=True)

    # 医生发生变化
    cur_worktime = (datetime.now().weekday() + 1) % 8
    cur_period = 1 if datetime.now().hour < 12 else 2
    if json_data.get('did'):
        if int(old_sched.get('ampm')) == cur_period and int(old_sched.get('worktime')) == cur_worktime:
            update_sql = f'UPDATE {database}.appt_record SET is_doc_change = 1 WHERE state = 1 ' \
                         'and book_date = \'{}\' and rid = {} and book_period = {} '. \
                format(str(date.today()), int(old_sched.get('rid')),
                       int(old_sched.get('ampm')), int(old_sched.get('did')))
            db.execute(update_sql, need_commit=True)
    del db

    socket_id = 'z' + str(rid)
    push_patient('', socket_id)
    socket_id = 'y' + str(rid)
    push_patient('', socket_id)

    # 更新项目排班信息
    old_pid = old_sched.get('pid')
    proj = redis_client.hget(APPT_PROJECTS_KEY, str(old_pid))
    if proj:
        proj = json.loads(proj)
        cache_proj_7day_sched(proj)
    new_pid = int(json_data.get('pid')) if json_data.get('pid') else 0
    if new_pid and new_pid != int(old_pid):
        proj = redis_client.hget(APPT_PROJECTS_KEY, str(new_pid))
        if proj:
            proj = json.loads(proj)
            cache_proj_7day_sched(proj)

    cache_capacity()


"""
检查项目切换房间
"""


def change_room(json_data):
    change_list = json_data.get('change_list')
    today_str = str(date.today())
    for item in change_list:
        if item.get('book_date') != today_str or int(item.get('type')) < appt_config.APPT_TYPE['advice_appt']:
            raise Exception('待切换的预约记录不是当天的，或者不是检查项目，无法切换房间')

    # 医生操作界面 - 分诊（就诊中的患者切换检查房间）
    state_sql = ''
    if len(change_list) == 1 and change_list[0].get('state') == appt_config.APPT_STATE['processing']:
        # 切换房间后需要变为等待状态
        state_sql = 'state = {} ,'.format(appt_config.APPT_STATE['in_queue'])

    # 更新可预约数量
    change_id_list = [str(item.get('id')) for item in change_list]
    current_slot = appt_config.appt_slot_dict[datetime.now().hour]
    current_period = 1 if datetime.now().hour < 13 else 2
    change_to_rid = str(json_data.get('change_to_rid'))
    change_to_room = json_data.get('change_to_room')
    for item in change_list:
        room_dict[str(item.get('rid'))][today_str][str(item.get('book_period'))][str(item.get('time_slot'))] += 1
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        update_sql = 'UPDATE {}.appt_record SET {} rid = {}, room = \'{}\', book_period = {}, time_slot = {}, sort_num = {}' \
                     ' WHERE id IN ({}) '.format(database, state_sql, change_to_rid, change_to_room, current_period,
                                                 current_slot, appt_config.default_sort_num, ', '.join(change_id_list))
        db.execute(update_sql, need_commit=True)
    except Exception as e:
        raise Exception(f"数据库操作失败: {e}") from e
    finally:
        del db  # 使用close()确保连接关闭

    room_dict[change_to_rid][today_str][str(current_period)][str(current_slot)] -= len(change_id_list)


"""
更新等待列表顺序
"""


def update_wait_list_sort(json_data):
    recordl = json_data.get('recordl')
    # 生成批量更新SQL语句
    update_sql = f"UPDATE {database}.appt_record SET sort_num = CASE id "
    ids = []
    index = 1
    for record in recordl:
        update_sql += f"WHEN {record['id']} THEN {index} "
        ids.append(record['id'])
        index = index + 1
    update_sql += "END WHERE id IN (%s)" % ','.join(map(str, ids))

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(update_sql, need_commit=True)
    del db


"""
更新调整顺序的原因
"""


def update_sort_info(appt_id, sort_info):
    # 生成批量更新SQL语句
    update_sql = 'UPDATE {}.appt_record SET sort_info = \'{}\' WHERE id = {} '.format(database, sort_info, appt_id)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(update_sql, need_commit=True)
    del db


"""
更新等待人数 （以下几种时机触发）
1. 新建预约时 自主查询前方等待人数更新
2. 取消预约 / 完成预约 
3. 过号时
4. 调整等待列表顺序时
5. 签到后
"""


def update_wait_num(rid, pid):
    # 1. 未签到的等待人数为 （等待中 处理中 过号） 的所有数量
    # 2. 已签到的等待任务树为 所在当前房间等待列表中的位置
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 查询当前项目 当天所有未完成 未取消的记录
    query_sql = 'select * from {}.appt_record where pid = {} and book_date = \'{}\' and state < {} '. \
        format(database, int(pid), str(date.today()), appt_config.APPT_STATE['completed'])
    recordl = db.query_all(query_sql)
    if not recordl:
        return

    unsign_idl = []
    pid_wait_num = 0
    rid_wait_record = []
    for record in recordl:
        if record['state'] >= appt_config.APPT_STATE['in_queue']:
            pid_wait_num = pid_wait_num + 1
            if int(record['rid']) == rid:
                rid_wait_record.append(record)
        else:
            unsign_idl.append(record.get('id'))

    # 更新未签到的预约 前方等待人数
    if unsign_idl:
        update_sql = f'UPDATE {database}.appt_record SET wait_num = {pid_wait_num} '
        update_sql += 'WHERE id IN (%s)' % ','.join(map(str, unsign_idl))
        db.execute(update_sql, need_commit=True)

    # 更新等待列表中的记录的 前方等待人数
    if rid_wait_record:
        rid_wait_record = sorted(rid_wait_record, key=lambda x: (-x['state'], x['sort_num'], -x['level'],
                                                                 x['book_period'], x['sign_in_num']))
        # 生成批量更新SQL语句
        update_sql = f"UPDATE {database}.appt_record SET wait_num = CASE id "
        ids = []
        index = 0
        for record in rid_wait_record:
            update_sql += f"WHEN {record['id']} THEN {index} "
            ids.append(record['id'])
            index = index + 1
        update_sql += "END WHERE id IN (%s)" % ','.join(map(str, ids))
        db.execute(update_sql, need_commit=True)
    del db


# 更新或者插入项目
def update_or_insert_project(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    try:
        pid = json_data.get('pid')
        if pid:
            proj_name = json_data.get('proj_name')
            if not proj_name:
                raise Exception("项目名称不能为空")
            # 如果存在pid，则更新
            update_sql = f"UPDATE {database}.appt_project SET proj_name = '{proj_name}' where id = {pid} "
            db.execute(update_sql, need_commit=True)
        else:
            proj_type = json_data.get('proj_type')
            proj_name = json_data.get('proj_name')
            nsnum = json_data.get('nsnum')
            if not proj_name or not nsnum or not proj_type:
                raise Exception("新增项目，项目名称或项目容量不能为空")
            insert_sql = f"INSERT INTO {database}.appt_project (proj_type, proj_name, nsnum) VALUES ({proj_type}, '{proj_name}', {nsnum})"
            pid = db.execute(insert_sql, need_commit=True)
            if pid == -1:
                del db
                raise Exception("新增项目失败! ", json_data)
    except Exception as e:
        del db
        raise Exception(f"项目更新/新增失败: {e}")

    worktime = (datetime.now().weekday() + 1) % 8
    schedl = db.query_all(
        f'select rid from {database}.appt_scheduling where pid = {pid} and worktime = {worktime} and state = 1')

    query_sql = f"select * from {database}.appt_project where id = {int(pid)} "
    proj = db.query_one(query_sql)
    del db
    # 更新缓存
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hset(APPT_PROJECTS_KEY, str(proj['id']), json.dumps(proj, default=str))
    # socket 通知诊室更新
    socket_id = 'd' + str(pid)
    push_patient('', socket_id)
    rid_set = set()
    for rid in schedl:
        rid_set.add(rid.get('rid'))
    for rid in rid_set:
        socket_id = 'z' + str(rid)
        push_patient('', socket_id)


"""
加载预约数据到内存
"""


def load_data_into_cache():
    print("开始加载综合预约静态数据到缓存中 - ", datetime.now())

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 缓存所有项目信息
    redis_client.delete(APPT_PROJECTS_KEY)
    redis_client.delete(APPT_EXECUTION_DEPT_INFO_KEY)
    projl = db.query_all(f'select * from {database}.appt_project')
    for proj in projl:
        if proj.get('dept_id'):
            # 执行科室信息
            redis_client.hset(APPT_EXECUTION_DEPT_INFO_KEY, str(proj['dept_id']), json.dumps(proj, default=str))
        redis_client.hset(APPT_PROJECTS_KEY, str(proj['id']), json.dumps(proj, default=str))

    # 缓存医生信息
    redis_client.delete(APPT_DOCTORS_KEY)
    redis_client.delete(APPT_DOCTORS_BY_NAME_KEY)
    doctorl = db.query_all(f'select * from {database}.appt_doctor')
    for item in doctorl:
        redis_client.hset(APPT_DOCTORS_KEY, str(item.get('id')), json.dumps(item, default=str))
        if redis_client.hexists(APPT_DOCTORS_BY_NAME_KEY, str(item.get('his_name'))):
            doc1 = redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, str(item.get('his_name')))
            doc1 = json.loads(doc1)
            docs = []
            if type(doc1) == dict:
                docs.append(doc1)
            elif type(doc1) == list:
                docs = doc1
            docs.append(item)
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, str(item.get('his_name')), json.dumps(docs, default=str))
        else:
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, str(item.get('his_name')), json.dumps(item, default=str))

    # 缓存所有房间
    redis_client.delete(APPT_ROOMS_KEY)
    rooml = db.query_all(f'select * from {database}.appt_room')
    for item in rooml:
        redis_client.hset(APPT_ROOMS_KEY, str(item.get('id')), json.dumps(item, default=str))
        if not redis_client.hexists(APPT_ROOMS_BY_PROJ_KEY, str(item.get('group_id'))):
            redis_client.hset(APPT_ROOMS_BY_PROJ_KEY, str(item.get('group_id')), json.dumps(item, default=str))

    # 加载当天自助挂号记录
    redis_client.delete(APPT_DAILY_AUTO_REG_RECORD_KEY)
    pay_nol = db.query_all(f'select pay_no from {database}.appt_record '
                           f'where book_date = \'{str(date.today())}\' and pay_no is not null and type = 3')
    if pay_nol:
        for no in pay_nol:
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, no.get('pay_no'))

    del db
    print("综合预约静态数据加载完成 - ", datetime.now())


"""
每日执行
1. 作废过期的预约
2. 缓存当日的签到号码
3. 缓存近七天的可预约项目数据
"""


def cache_proj_7day_sched(proj):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 近 7 天的可预约数量
    pid = int(proj.get('id'))
    today = datetime.now().date()
    data_from_last_seven = {}
    for i in range(7):
        nextday = today + timedelta(days=i)
        worktime = (nextday.weekday() + 1) % 8

        aml, pml = {}, {}
        # 门诊项目
        schedl = db.query_all(
            f'select * from {database}.appt_scheduling where pid = {pid} and worktime = {worktime} and state = 1')
        for item in schedl:
            room = redis_client.hget(APPT_ROOMS_KEY, str(item.get('rid')))
            room = json.loads(room)
            # if not item.get('did'):
            #     continue
            if int(proj.get('proj_type')) == 1:
                doc_info = redis_client.hget(APPT_DOCTORS_KEY, str(item.get('did')))
                if not doc_info:
                    doc_info = {'fee': 0}
                else:
                    doc_info = json.loads(doc_info)
                if int(item.get('ampm')) == 1:
                    # 上午
                    aml[item.get('rid')] = {
                        'doc_id': item.get('did'),
                        'doctor': doc_info,
                        'price': float(doc_info.get('fee')),
                        'room': room,
                        'rid': item.get('rid'),
                        'proj_name': proj.get('proj_name'),
                        'proj_type': proj.get('proj_type'),
                        'proj_id': proj.get('id')
                    }
                else:
                    # 下午
                    pml[item.get('rid')] = {
                        'doc_id': item.get('did'),
                        'doctor': doc_info,
                        'price': float(doc_info.get('fee')),
                        'room': room,
                        'rid': item.get('rid'),
                        'proj_name': proj.get('proj_name'),
                        'proj_type': proj.get('proj_type'),
                        'proj_id': proj.get('id')
                    }
            else:
                # 院内项目不指定医生
                if int(item.get('ampm')) == 1:
                    aml[item.get('rid')] = {
                        'room': room,
                        'rid': item.get('rid'),
                        'proj_name': proj.get('proj_name'),
                        'proj_type': proj.get('proj_type'),
                        'proj_id': proj.get('id')
                    }
                else:
                    pml[item.get('rid')] = {
                        'room': room,
                        'rid': item.get('rid'),
                        'proj_name': proj.get('proj_name'),
                        'proj_type': proj.get('proj_type'),
                        'proj_id': proj.get('id')
                    }
        data_from_last_seven[str(nextday)] = {'1': aml, '2': pml}
    del db
    if data_from_last_seven:
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid),
                          json.dumps(data_from_last_seven, default=str))


def run_everyday():
    load_data_into_cache()

    print("开始加载综合预约排班数据到缓存中 - ", datetime.now())
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 取消今天之前未完成的预约，小程序取消预约涉及到退款，由用户自己取消
    all_cancel_type = (appt_config.APPT_TYPE['offline'], appt_config.APPT_TYPE['auto_appt'],
                       appt_config.APPT_TYPE['advice_appt'])
    update_sql = 'UPDATE {}.appt_record SET state = {}, cancel_time = \'{}\' ' \
                 'WHERE book_date < \'{}\' AND state < {} AND type IN {}' \
        .format(database, appt_config.APPT_STATE['canceled'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                date.today().strftime('%Y-%m-%d'), appt_config.APPT_STATE['completed'], tuple(all_cancel_type))
    db.execute(update_sql, need_commit=True)

    # 查询当天所有未取消的预约 缓存签到计数
    state_cond = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'],
                  appt_config.APPT_STATE['over_num'])
    query_sql = 'select pid, max(sign_in_num) as num from {}.appt_record' \
                ' where book_date = \'{}\' and state IN {} group by pid' \
        .format(database, date.today().strftime('%Y-%m-%d'), tuple(state_cond))
    recordl = db.query_all(query_sql)
    redis_client.delete(APPT_SIGN_IN_NUM_KEY)
    for record in recordl:
        if record.get('num'):
            sign_in_num = int(record.get('num'))
            old_num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, str(record['pid'])) or 0
            if int(old_num) < sign_in_num:
                redis_client.hset(APPT_SIGN_IN_NUM_KEY, str(record['pid']), sign_in_num)
    del db
    # 缓存门诊项目近七天的可预约情况
    redis_client.delete(APPT_REMAINING_RESERVATION_QUANTITY_KEY)
    all_proj = redis_client.hgetall(APPT_PROJECTS_KEY)
    for pid, proj in all_proj.items():
        proj = json.loads(proj)
        cache_proj_7day_sched(proj)

    print("综合预约所有数据缓存完成 - ", datetime.now())

import json

import redis
import requests

from datetime import datetime, date, timedelta
from itertools import groupby

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.composite_appointment.appt_config import APPT_STATE, \
    APPT_SIGN_IN_NUM_KEY, APPT_PROJECTS_KEY, APPT_REMAINING_RESERVATION_QUANTITY_KEY, \
    APPT_DOCTORS_KEY, APPT_EXECUTION_DEPT_INFO_KEY, socket_push_url, APPT_ROOMS_KEY, \
    APPT_SCHEDULING_KEY, APPT_DAILY_AUTO_REG_RECORD_KEY, APPT_DOCTORS_BY_NAME_KEY, APPT_SCHEDULING_DAILY_KEY, \
    APPT_ROOMS_BY_PROJ_KEY

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)

lock_redis_client = redis.Redis(connection_pool=pool)

database = 'nsyy_gyl'

appt_lock_name = 'appt_lock_name'
sign_lock_name = 'sign_lock_name'


"""
调用第三方系统
"""


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post(f"http://192.168.124.53:6080/{url}", json=param)
            data = response.text
            data = json.loads(data)
            if type == 'his_visit_reg':
                data = data.get('ResultCode')
            else:
                data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'his_visit_reg':
            # 门诊挂号 当天
            from tools import his_visit_reg
            data = his_visit_reg(param)
            data = data.get('ResultCode')
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

    return data


"""
线上预约（微信小程序）   
"""


def online_appt(json_data):
    json_data['type'] = appt_config.APPT_TYPE['online']
    json_data['level'] = appt_config.APPT_URGENCY_LEVEL['green']
    json_data['state'] = appt_config.APPT_STATE['booked']
    create_appt(json_data, -1)


"""
线下预约（现场）
"""


def offline_appt(json_data):
    json_data['type'] = appt_config.APPT_TYPE['offline']
    json_data['level'] = json_data.get('level') or appt_config.APPT_URGENCY_LEVEL['green']
    json_data['state'] = appt_config.APPT_STATE['booked']
    create_appt(json_data, -1)


"""
校验是否可以继续预约
小程序预约和线下预约选择的时间段（上午/下午）不能更改
自助预约/医嘱预约可以根据容量调整时间段
"""


def check_appointment_quantity(type, rid, pid, book_date, period, last_slot):
    redis_client = redis.Redis(connection_pool=pool)
    quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid))
    if not quantity_data:
        raise Exception(f'今天不存在项目 id 为 {pid} 的可预约项目')
    quantity_data = json.loads(quantity_data)
    if book_date not in quantity_data or not quantity_data[book_date]:
        raise Exception('当前时间没有可预约数量，请选择其他时间')

    # 分配时间段
    today_str = str(date.today())
    time_slot = 1
    end_slot = 17
    if int(type) in (1, 2):
        end_slot = 9 if int(period) == 1 else 17

    if book_date == today_str:
        # 当天的预约根据当前预约时间确定起始时间段
        slot = appt_config.appt_slot_dict[datetime.now().hour]
        book_ok = False
        # 根据上一个预约的时间段，预约下一个
        if last_slot != -1 and last_slot < end_slot - 1:
            slot = last_slot + 1
        if last_slot != -1 and last_slot == end_slot - 1:
            slot = last_slot

        for i in range(slot, end_slot):
            if period == 1 and i > 8:
                period = 2
            num = quantity_data[book_date][str(period)][str(rid)]['hourly_quantity'].get(str(i))
            if num and int(num) > 0:
                book_ok = True
                time_slot = i
                break
        if not book_ok:
            raise Exception('当前项目已饱和，请选择其他时间')
    else:
        book_ok = False
        start_slot = 1 if period == 1 else 9
        for i in range(start_slot, end_slot):
            if period == 1 and i > 8:
                period = 2
            num = quantity_data[book_date][str(period)][str(rid)]['hourly_quantity'].get(str(i))
            if num and int(num) > 0:
                book_ok = True
                time_slot = i
                break
        if not book_ok:
            raise Exception('当前项目已饱和，请选择其他时间')

    return quantity_data, time_slot


"""
创建预约
1. 线上小程序预约
2. 现场 oa 预约
3. 自助挂号机取号，查询预约记录时，根据挂号信息自动创建
4. 根据医嘱创建预约
"""


def create_appt(json_data, last_slot):
    redis_client = redis.Redis(connection_pool=pool)
    lock = lock_redis_client.lock(appt_lock_name, timeout=10)
    if lock.acquire(blocking=True):
        try:
            json_data['create_time'] = str(datetime.now())[:19]
            # 检查项目是否可以预约，以及获取预估时间段
            quantity_data, time_slot = check_appointment_quantity(int(json_data.get('type')),
                                                                  int(int(json_data['rid'])), int(json_data['pid']),
                                                                  json_data['book_date'], int(json_data['book_period']),
                                                                  last_slot)
            json_data['time_slot'] = time_slot
            if time_slot < 9:
                json_data['book_period'] = 1
            else:
                json_data['book_period'] = 2

            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
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
            quantity_data[date_str][period_str][rid]['quantity'] = \
                int(quantity_data[date_str][period_str][rid]['quantity']) - 1
            quantity_data[date_str][period_str][rid]['hourly_quantity'][str(time_slot)] = \
                int(quantity_data[date_str][period_str][rid]['hourly_quantity'][str(time_slot)]) - 1

            redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['pid']),
                              json.dumps(quantity_data, default=str))
            return last_rowid, time_slot
        finally:
            lock.release()
    else:
        raise Exception('Could not acquire lock 系统繁忙，请稍后再试')


"""
根据自助取号记录创建预约
"""


def auto_create_appt_by_auto_reg(patient_id: int):
    param = {"type": "his_visit_check", "patient_id": patient_id}
    reg_recordl = call_third_systems_obtain_data('his_info', 'his_visit_check', param)
    if not reg_recordl:
        # patient_id 不存在自助挂号记录
        return

    redis_client = redis.Redis(connection_pool=pool)
    # 查询当天所有自助挂号的记录（pay no）集合
    created = redis_client.smembers(APPT_DAILY_AUTO_REG_RECORD_KEY)
    daily_sched = redis_client.get(APPT_SCHEDULING_DAILY_KEY)
    daily_sched = json.loads(daily_sched)

    # 根据执行人和执行部门id查找项目 todo 自助挂号的项目如何做预约数量限制
    # 上午挂号的可以预约上午和下午，下午挂号的只能预约下午， 1=上午 2=下午
    period = '12' if datetime.now().hour < 12 else '2'
    for item in reg_recordl:
        # 判断是否已经创建过预约
        pay_no = item.get('NO')
        if pay_no in created:
            continue
        else:
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            doc_his_name = item.get('执行人')
            today_str = str(date.today())
            query_sql = f'select * from {database}.appt_record ' \
                        f'where patient_id = {patient_id} and doc_his_name = \'{doc_his_name}\'' \
                        f' and book_date = \'{today_str}\''
            appt_record = db.query_all(query_sql)
            if appt_record:
                continue
            del db

        # 这里的doctor 是 his name
        doctor = redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, item.get('执行人'))
        if not doctor:
            raise Exception('预约系统中不存在 {} 医生，请联系护士及时维护门诊医生信息'.format(item.get('执行人')))
        doctor = json.loads(doctor)
        # 根据医生找到医生当天的坐诊项目
        target_proj = ''
        target_room = ''
        book_period = ''
        for s in daily_sched:
            if int(s.get('did')) == int(doctor.get('id')) and str(s.get('ampm')) in period:
                target_proj = redis_client.hget(APPT_PROJECTS_KEY, str(s.get('pid')))
                target_proj = json.loads(target_proj)
                target_room = redis_client.hget(APPT_ROOMS_KEY, str(s.get('rid')))
                target_room = json.loads(target_room)
                book_period = s.get('ampm')
                break
        if not target_proj or not target_room:
            raise Exception('未找到 {} 医生今天的坐诊信息'.format(item.get('执行人')))

        # 根据上面的信息，创建预约
        record = {
            'type': appt_config.APPT_TYPE['auto_appt'],
            'patient_id': patient_id,
            'patient_name': item.get('姓名'),
            'state': appt_config.APPT_STATE['booked'],
            'pid': target_proj.get('id'),
            'pname': target_proj.get('proj_name'),
            'ptype': target_proj.get('proj_type'),
            'rid': target_room.get('id'),
            'room': target_room.get('no'),
            'book_date': str(date.today()),
            'book_period': book_period,
            'level': 1,
            'price': doctor.get('fee'),
            'doc_id': doctor.get('id'),
            'doc_his_name': doctor.get('his_name'),
            'doc_dept_id': doctor.get('dept_id'),
            'pay_no': pay_no
        }
        if target_proj.get('location_id'):
            record['location_id'] = target_proj.get('location_id')
        create_appt(record, -1)
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
    patient_id = json_data.get('patient_id')
    if patient_id:
        auto_create_appt_by_auto_reg(int(patient_id))

    query_from = json_data.get('query_from')
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
    condition_sql += f' and patient_id = \'{patient_id}\' ' if patient_id else ''

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from {database}.appt_record where {condition_sql}"
    appts = db.query_all(query_sql)

    # 医嘱单独查询，不再直接组装
    # for record in appts:
    #     appt_id = record.get('id')
    #     query_sql = f"select * from {database}.appt_doctor_advice where appt_id = {appt_id}"
    #     advicel = db.query_all(query_sql)
    #     record['doctor_advice'] = advicel
    #     record['time_slot'] = appt_config.APPT_PERIOD_INFO.get(int(record['time_slot']))

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
    response = requests.post(socket_push_url, data=json.dumps(data), headers=headers)
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
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['completed'])
    elif type == 2:
        if int(record.get('state')) == appt_config.APPT_STATE['canceled']:
            # 已经完成的不再处理，防止重复点击
            return
        # 取消
        op_sql = ' state = {}, cancel_time = \'{}\' '.format(appt_config.APPT_STATE['canceled'], cur_time)
    elif type == 3:
        if int(record.get('state')) == appt_config.APPT_STATE['over_num']:
            # 已经完成的不再处理，防止重复点击
            return
        # 过号
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['over_num'])
    elif type == 4:
        # 报道 医嘱项目分诊前有用户在小程序上点击
        op_sql = ' state = {} '.format(appt_config.APPT_STATE['booked'])

    update_sql = f'UPDATE {database}.appt_record SET {op_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db

    # 预约完成，查询医嘱打印 引导单
    if type == 1 and int(record.get('type')) < 4:
        create_appt_by_doctor_advice(record.get('patient_id'),
                                     record.get('doc_his_name'), record.get('id_card_no'), appt_id, int(record.get('level')))

    # 取消预约，可预约数量 + 1
    if type == 2:
        proj_id, period, appt_date, rid = str(record.get('pid')), str(
            record.get('book_period')), record.get('book_date'), str(record.get('rid'))
        if appt_date < str(date.today()):
            return
        redis_client = redis.Redis(connection_pool=pool)
        quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(proj_id))
        if not quantity_data:
            print(f'取消预约更新可预约数量：不存在项目 id 为 {proj_id} 的预约项目')
            return
        quantity_data = json.loads(quantity_data)
        quantity_data[appt_date][period][rid]['quantity'] = int(
            quantity_data[appt_date][period][rid].get('quantity') + 1)
        quantity_data[appt_date][period][rid]['hourly_quantity'][str(record.get('time_slot'))] = \
            int(quantity_data[appt_date][period][rid]['hourly_quantity'][str(record.get('time_slot'))] + 1)
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(proj_id), json.dumps(quantity_data, default=str))

    # 过号，重新取号，排在最后
    if type == 3:
        param = {
            'appt_id': record.get('id'),
            'type': record.get('type'),
            'patient_id': record.get('patient_id'),
            'patient_name': record.get('patient_name'),
            'pid': record.get('pid'),
            'rid': record.get('rid')
        }
        sign_in(param, his_sign=False)

    if type == 4:
        # 报道时需要给分诊护士发送 socket
        socket_id = 'w' + str(record.get('pid'))
        push_patient('', socket_id)
        return

    socket_id = 'd' + str(record.get('pid'))
    push_patient('', socket_id)
    socket_id = 'z' + str(record.get('rid'))
    push_patient('', socket_id)


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
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 按执行科室分组
    advice_dict = {}
    for item in doctor_advice:
        key = item.get('执行部门ID')
        if key not in advice_dict:
            advice_dict[key] = []
        advice_dict[key].append(item)

    last_slot = -1
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
            pid = proj.get('id')
            pname = proj.get('proj_name')
            ptype = proj.get('proj_type')
            location_id = proj.get('location_id') if proj.get('location_id') else ''

        room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, pid))
        record = {
            'father_id': int(appt_id),
            'id_card_no': id_card_no,
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": 4,
            "patient_id": patient_id,
            "patient_name": advicel[0].get('姓名'),
            "pid": pid,
            "pname": pname,
            "ptype": ptype,
            'rid': room.get('id'),
            'room': room.get('no'),
            "state": 0,
            "level": int(level),
            "location_id": location_id,
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, slot = create_appt(record, last_slot)
        last_slot = slot

        # 按 pay_id 排序，后按 pay_id 分组
        advicel.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(advicel, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            json_data = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }

            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)

    if other_advice:
        record = {
            'father_id': int(appt_id),
            'id_card_no': id_card_no,
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": 4,
            "patient_id": patient_id,
            "patient_name": other_advice[0].get('姓名'),
            "pid": 79,
            "pname": "其他项目",
            'rid': 153,
            'room': '其他',
            "ptype": 2,
            "state": 0,
            "level": int(level),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, slot = create_appt(record, last_slot)
        # 按 pay_id 排序，后按 pay_id 分组
        other_advice.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(other_advice, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            json_data = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }

            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)

    del db


"""
更新医嘱
"""


def update_advice(json_data):
    patient_id = int(json_data.get('patient_id'))
    doc_name = json_data.get('doc_name')
    param = {"type": "his_yizhu_info", 'patient_id': patient_id, 'doc_name': doc_name}
    new_doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)
    if not new_doctor_advice:
        # 没有医嘱直接返回
        return

    level = json_data.get('level')
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 按执行科室分组
    new_advicel = {}
    for item in new_doctor_advice:
        key = item.get('执行部门ID')
        if key not in new_advicel:
            new_advicel[key] = []
        new_advicel[key].append(item)

    # 取之前创建的预约的最后一条
    last_slot = -1
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
        query_sql = f'select * from {database}.appt_record where book_date = \'{str(date.today())}\' and patient_id = {patient_id} and pid = {pid} '
        created = db.query_one(query_sql)
        if created:
            # 更新医嘱
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
                json_data = {
                    'appt_id': appt_id,
                    'pay_id': group_list[0].get('NO'),
                    'advice_desc': combined_advice_desc,
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': total_price
                }

                fileds = ','.join(json_data.keys())
                args = str(tuple(json_data.values()))
                insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
                last_rowid = db.execute(sql=insert_sql, need_commit=True)
                if last_rowid == -1:
                    raise Exception("医嘱记录入库失败! sql = " + insert_sql)
        else:
            # 新增医嘱
            if not proj:
                other_advice += advicel
                continue

            room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, pid))
            record = {
                'father_id': int(json_data.get('appt_id')),
                "book_date": str(date.today()),
                "book_period": 1 if datetime.now().hour < 12 else 2,
                "type": 4,
                "patient_id": patient_id,
                "patient_name": advicel[0].get('姓名'),
                "pid": pid,
                "pname": proj.get('proj_name'),
                "ptype": proj.get('proj_type'),
                'rid': room.get('id'),
                'room': room.get('no'),
                "state": 0,
                "level": int(level),
                "location_id": proj.get('location_id') if proj.get('location_id') else '',
            }
            # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
            new_appt_id, slot = create_appt(record, last_slot)
            last_slot = slot
            # 按 pay_id 排序，后按 pay_id 分组
            advicel.sort(key=lambda x: x['NO'])
            # 根据 pay_id 分组并计算每个分组的 price 总和
            for key, group in groupby(advicel, key=lambda x: x['NO']):
                group_list = list(group)
                combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
                total_price = sum(item['实收金额'] for item in group_list)
                # 使用第一个元素的字典结构来创建合并后的记录
                json_data = {
                    'appt_id': new_appt_id,
                    'pay_id': group_list[0].get('NO'),
                    'advice_desc': combined_advice_desc,
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': total_price
                }

                fileds = ','.join(json_data.keys())
                args = str(tuple(json_data.values()))
                insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
                last_rowid = db.execute(sql=insert_sql, need_commit=True)
                if last_rowid == -1:
                    raise Exception("医嘱记录入库失败! sql = " + insert_sql)

    if other_advice:
        record = {
            'father_id': int(json_data.get('appt_id')),
            "book_date": str(date.today()),
            "book_period": 1 if datetime.now().hour < 12 else 2,
            "type": 4,
            "patient_id": patient_id,
            "patient_name": other_advice[0].get('姓名'),
            "pid": 79,
            "pname": "其他项目",
            "ptype": 2,
            'rid': 153,
            'room': '其他',
            "state": 0,
            "level": int(level),
        }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, slot = create_appt(record, last_slot)
        # 按 pay_id 排序，后按 pay_id 分组
        other_advice.sort(key=lambda x: x['NO'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(other_advice, key=lambda x: x['NO']):
            group_list = list(group)
            combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
            total_price = sum(item['实收金额'] for item in group_list)
            # 使用第一个元素的字典结构来创建合并后的记录
            json_data = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': combined_advice_desc,
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': total_price
            }

            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            insert_sql = f"INSERT INTO {database}.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)

    del db


"""
预约签到
"""


def sign_in(json_data, his_sign: bool):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)
    appt_id = int(json_data['appt_id'])
    appt_type = int(json_data.get('type'))
    patient_id = int(json_data.get('patient_id'))

    # 如果是医嘱预约，检查付款状态
    if appt_type == 4:
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
                raise Exception('所有医嘱项目均未付款，请及时付款', param)

    # 签到前到 his 中取号, 小程序预约，现场预约需要取号。 自助挂号机挂号的预约不需要挂号.
    if appt_type in (1, 2) and his_sign:
        param = {"type": "his_visit_reg", "patient_id": patient_id, "AsRowid": 2116, "PayAmt": 0.01}
        doctorinfo = redis_client.hget(APPT_DOCTORS_KEY, str(json_data.get('doc_id')))
        if doctorinfo:
            doctorinfo = json.loads(doctorinfo)
            param = {"type": "his_visit_reg", "patient_id": patient_id,
                     "AsRowid": int(doctorinfo.get('appointment_id')),
                     "PayAmt": float(doctorinfo.get('fee'))}
        his_socket_ret_code = call_third_systems_obtain_data('his_socket', 'his_visit_reg', param)
        if his_socket_ret_code != '0':
            raise Exception('在 his 中取号失败， 签到失败, ResultCode: ', his_socket_ret_code)

    # 判断是否需要更换项目
    change_proj_sql = ''
    quantity_data = ''
    time_slot = 0
    if json_data.get('rid') and json_data.get('room'):
        # 检查项目是否可以预约
        quantity_data, time_slot = check_appointment_quantity(appt_type, int(json_data['rid']), int(json_data['pid']), json_data['book_date'],
                                                   int(json_data['book_period']), -1)

        change_proj_sql = ', rid = {}, room = \'{}\' '.format(json_data['rid'], json_data['room'])

    sign_in_num = __get_signin_num(int(json_data.get('pid')))
    sign_in_time = str(datetime.now())[:19]
    op_sql = ' sign_in_time = \'{}\', sign_in_num = {}, state = {} '.format(sign_in_time, sign_in_num,
                                                                            appt_config.APPT_STATE['in_queue'])
    update_sql = f'UPDATE {database}.appt_record SET {op_sql}{change_proj_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)

    proj_id = json_data.get('pid')
    patient_name = json_data.get('patient_name')

    if int(appt_type) == 4:
        # 推送给大厅
        socket_id = 'd' + str(proj_id)
        push_patient(patient_name, socket_id)
    else:
        # 签到成功之后，将患者名字推送给诊室
        socket_id = 'z' + str(json_data['rid'])
        push_patient(patient_name, socket_id)

    # 签到之后给医生发送 socket
    socket_id = 'y' + str(json_data['rid'])
    push_patient('', socket_id)

    del db

    # 如果更换房间，更新可预约数量
    if quantity_data:
        rid = str(json_data.get('rid'))
        period = str(json_data.get('book_period'))
        appt_date = json_data['book_date']
        quantity_data[appt_date][period][rid]['quantity'] = int(quantity_data[appt_date][period][rid]['quantity']) - 1
        quantity_data[appt_date][period][rid]['hourly_quantity'][str(time_slot)] = \
            int(quantity_data[appt_date][period][rid]['hourly_quantity'][str(time_slot)]) - 1
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['pid']),
                          json.dumps(quantity_data, default=str))


"""
获取签到id
"""


def __get_signin_num(appt_proj_id: int):
    redis_client = redis.Redis(connection_pool=pool)
    lock = lock_redis_client.lock(sign_lock_name, timeout=10)
    if lock.acquire(blocking=True):
        try:
            num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, appt_proj_id) or 0
            redis_client.hset(APPT_SIGN_IN_NUM_KEY, appt_proj_id, int(num) + 1)
            return int(num) + 1
        finally:
            lock.release()
    else:
        raise Exception('Could not acquire lock 系统繁忙，请稍后再试')


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
    response = requests.post(socket_push_url, data=json.dumps(data), headers=headers)
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
            'socket_id': 'd' + str(id) if is_group != -1 else 'z' + str(id),
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
    wait_state = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'])

    condition_sql = f' and rid = {wait_id} '
    if int(type) == 2:
        condition_sql = f' and pid = {wait_id} '

    query_sql = f'select * from {database}.appt_record ' \
                f'where state in {wait_state} and book_date = \'{str(date.today())}\' {condition_sql} '
    recordl = db.query_all(query_sql)
    del db

    # 根据 房间rid worktime period 从排班信息中查询值班医生
    doctor = ''
    proj = ''
    daily_sched = redis_client.get(APPT_SCHEDULING_DAILY_KEY)
    daily_sched = json.loads(daily_sched)
    worktime = (datetime.now().weekday() + 1) % 8
    period = 1 if datetime.now().hour < 12 else 2
    for item in daily_sched:
        if worktime == int(item.get('worktime')) and period == int(item.get('ampm')) and wait_id == int(item.get('rid')) and int(item.get('state')) == 1:
            if type == 1 and redis_client.hexists(APPT_DOCTORS_KEY, str(item.get('did'))):
                    doctor = json.loads(redis_client.hget(APPT_DOCTORS_KEY, str(item.get('did'))))
                    if not doctor.get('photo'):
                        doctor['photo'] = appt_config.default_photo

            proj = redis_client.hget(APPT_PROJECTS_KEY, str(item.get('pid')))
            proj = json.loads(proj)
    if type == 2:
        proj = redis_client.hget(APPT_PROJECTS_KEY, str(wait_id))
        proj = json.loads(proj)

    # proj_id 存在说明要查询排队列表，排队列表需要排队
    # 1. 按照紧急程度排序 降序
    # 2. 按照预约时间排序 升序
    # 3. 按照签到时间排序 升序
    recordl = sorted(recordl, key=lambda x: (-x['level'], x['book_period'], x['sign_in_num']))

    from collections import defaultdict
    transformed_data = defaultdict(list)
    for item in recordl:
        key = item['room']
        transformed_data[key].append(item)

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
        condition_sql = f'type = 4 and patient_id = {int(patient_id)}'
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
更新排班信息
"""

#
# def update_sched(json_data):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     id = int(json_data.get('id'))
#     rid = int(json_data.get('rid'))
#     did = int(json_data.get('did'))
#     pid = int(json_data.get('pid'))
#     state = int(json_data.get('state'))
#     update_sql = f'UPDATE {database}.appt_scheduling SET did = {did}, pid = {pid}, state = {state} ' \
#                  f' WHERE id = {id}'
#     db.execute(update_sql, need_commit=True)
#     del db
#
#     run_everyday()
#
#     # socket 通知诊室或大厅
#     socket_id = 'd' + str(pid)
#     push_patient('', socket_id)
#     socket_id = 'z' + str(rid)
#     push_patient('', socket_id)


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
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = ' name = \'{}\' '.format(json_data.get('name')) if json_data.get('name') else ''
    condition_sql += ', no = {} '.format(json_data.get('no')) if json_data.get('no') else ''
    condition_sql += ', dept_id = {} '.format(json_data.get('dept_id')) if json_data.get('dept_id') else ''
    condition_sql += ', dept_name = \'{}\' '.format(json_data.get('dept_name')) if json_data.get('dept_name') else ''
    condition_sql += ', career = \'{}\' '.format(json_data.get('career')) if json_data.get('career') else ''
    condition_sql += ', fee = {} '.format(json_data.get('fee')) if json_data.get('fee') else ''
    condition_sql += ', appointment_id = {} '.format(json_data.get('appointment_id')) if json_data.get('appointment_id') else ''
    condition_sql += ', photo = \'{}\' '.format(json_data.get('photo')) if json_data.get('photo') else ''
    condition_sql += ', `desc` = \'{}\' '.format(json_data.get('desc')) if json_data.get('desc') else ''
    condition_sql += ', phone = \'{}\' '.format(json_data.get('phone')) if json_data.get('phone') else ''

    id = int(json_data.get('id'))
    update_sql = f'UPDATE {database}.appt_doctor SET {condition_sql} ' \
                 f' WHERE id = {id}'
    db.execute(update_sql, need_commit=True)
    del db
    run_everyday()


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

    # worktime = int(old_sched.get('worktime'))
    # ampm = int(old_sched.get('ampm'))
    # query_sql = f'select * from {database}.appt_scheduling where worktime = {worktime} and ampm = {ampm} ' \
    #             f'and rid = {rid} and did = {did} and pid = {pid} and state = 1'
    # record = db.query_one(query_sql)
    # if record:
    #     raise Exception('排班信息和 {} 存在冲突'.format(record.get('id')))
    update_sql = f'UPDATE {database}.appt_scheduling SET {condition_sql} ' \
                 f' WHERE id = {id}'
    db.execute(update_sql, need_commit=True)

    # 医生发生变化
    if json_data.get('did'):
        cur_worktime = (datetime.now().weekday() + 1) % 8
        cur_period = 1 if datetime.now().hour < 12 else 2
        if int(old_sched.get('ampm')) == cur_period and int(old_sched.get('worktime')) == cur_worktime:
            update_sql = f'UPDATE {database}.appt_record SET is_doc_change = 1 WHERE state = 1 ' \
                         'and book_date = \'{}\' and rid = {} and book_period = {} '.\
                format(str(date.today()), int(old_sched.get('rid')),
                       int(old_sched.get('ampm')), int(old_sched.get('did')))
            db.execute(update_sql, need_commit=True)

    socket_id = 'z' + str(rid)
    push_patient('', socket_id)
    socket_id = 'y' + str(rid)
    push_patient('', socket_id)

    del db
    # 更新数据
    run_everyday()


"""
加载预约数据到内存
"""


def load_data_into_cache():
    print("开始加载数据到缓存中 - ", datetime.now())

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
    doctorl = db.query_all(f'select * from {database}.appt_doctor')
    for item in doctorl:
        redis_client.hset(APPT_DOCTORS_KEY, str(item.get('id')), json.dumps(item, default=str))
        redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, str(item.get('his_name')), json.dumps(item, default=str))

    # 缓存所有房间
    redis_client.delete(APPT_ROOMS_KEY)
    rooml = db.query_all(f'select * from {database}.appt_room')
    for item in rooml:
        redis_client.hset(APPT_ROOMS_KEY, str(item.get('id')), json.dumps(item, default=str))
        if not redis_client.hexists(APPT_ROOMS_BY_PROJ_KEY, str(item.get('group_id'))):
            redis_client.hset(APPT_ROOMS_BY_PROJ_KEY, str(item.get('group_id')), json.dumps(item, default=str))

    # 缓存所有排班信息, 按照项目分组
    redis_client.delete(APPT_SCHEDULING_KEY)
    schedulingl = db.query_all(f'select * from {database}.appt_scheduling')
    worktime = (datetime.now().weekday() + 1) % 8
    daily_sched = []
    for item in schedulingl:
        if int(item.get('worktime')) == worktime:
            daily_sched.append(item)
    redis_client.set(APPT_SCHEDULING_DAILY_KEY, json.dumps(daily_sched, default=str))

    projd_by_sched = {}
    for item in schedulingl:
        if str(item.get('pid')) not in projd_by_sched:
            projd_by_sched[str(item.get('pid'))] = []
        projd_by_sched[str(item.get('pid'))].append(item)
    for k, v in projd_by_sched.items():
        redis_client.hset(APPT_SCHEDULING_KEY, k, json.dumps(v, default=str))

    # 加载当天自助挂号记录
    redis_client.delete(APPT_DAILY_AUTO_REG_RECORD_KEY)
    pay_nol = db.query_all(
        f'select pay_no from {database}.appt_record where book_date = \'{str(date.today())}\' and pay_no is not null ')
    if pay_nol:
        for no in pay_nol:
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, no.get('pay_no'))

    del db
    print("数据加载完成 - ", datetime.now())


"""
每日执行
1. 作废过期的预约
2. 缓存当日的签到号码
3. 缓存近七天的可预约项目数据
"""


def run_everyday():
    load_data_into_cache()

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
    query_sql = 'select pid, max(sign_in_num) as num from {}.appt_record' \
                ' where book_date = \'{}\' and state < {} group by pid' \
        .format(database, str(datetime.now().date()), APPT_STATE['canceled'])
    recordl = db.query_all(query_sql)
    for record in recordl:
        if record.get('sign_in_num'):
            sign_in_num = int(record.get('sign_in_num'))
            old_num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, str(record['pid'])) or 0
            if int(old_num) < sign_in_num:
                redis_client.hset(APPT_SIGN_IN_NUM_KEY, str(record['pid']), sign_in_num)

    # 缓存门诊项目近七天的可预约情况
    redis_client.delete(APPT_REMAINING_RESERVATION_QUANTITY_KEY)
    projl = db.query_all(f'select * from {database}.appt_project')
    for proj in projl:
        # 近 7 天的可预约数量
        pid = int(proj.get('id'))
        today = datetime.now().date()
        data_from_last_seven = {}
        for i in range(7):
            nextday = today + timedelta(days=i)
            worktime = (nextday.weekday() + 1) % 8

            proj_info = redis_client.hget(APPT_PROJECTS_KEY, str(pid))
            proj_info = json.loads(proj_info)
            aml, pml = {}, {}
            quantity = proj.get('nsnum')
            # 门诊项目
            schedl = db.query_all(
                f'select * from {database}.appt_scheduling where pid = {pid} and worktime = {worktime} and state = 1')
            for item in schedl:
                room = redis_client.hget(APPT_ROOMS_KEY, str(item.get('rid')))
                room = json.loads(room)
                if not item.get('did'):
                    continue
                if int(proj_info.get('proj_type')) == 1:
                    hq = int(quantity / 8)
                    doc_info = redis_client.hget(APPT_DOCTORS_KEY, str(item.get('did')))
                    doc_info = json.loads(doc_info)
                    if int(item.get('ampm')) == 1:
                        # 上午
                        aml[item.get('rid')] = {
                            'quantity': quantity,
                            'max_quantity': quantity,
                            'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq, '6': hq, '7': hq, '8': hq},
                            'doctor': doc_info,
                            'price': float(doc_info.get('fee')),
                            'room': room,
                            'rid': item.get('rid'),
                            'proj_name': proj_info.get('proj_name'),
                            'proj_id': proj_info.get('id')
                        }
                    else:
                        # 下午
                        pml[item.get('rid')] = {
                            'quantity': quantity,
                            'max_quantity': quantity,
                            'hourly_quantity': {'9': hq, '10': hq, '11': hq, '12': hq, '13': hq, '14': hq, '15': hq,
                                                '16': hq},
                            'doctor': doc_info,
                            'price': float(doc_info.get('fee')),
                            'room': room,
                            'rid': item.get('rid'),
                            'proj_name': proj_info.get('proj_name'),
                            'proj_id': proj_info.get('id')
                        }
                else:
                    # 院内项目不指定医生
                    hq = int(quantity / 8)
                    if int(item.get('ampm')) == 1:
                        aml[item.get('rid')] = {
                            'quantity': quantity,
                            'max_quantity': quantity,
                            'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq, '6': hq, '7': hq, '8': hq},
                            'room': room,
                            'rid': item.get('rid'),
                            'proj_name': proj_info.get('proj_name'),
                            'proj_id': proj_info.get('id')
                        }
                    else:
                        pml[item.get('rid')] = {
                            'quantity': quantity,
                            'max_quantity': quantity,
                            'hourly_quantity': {'9': hq, '10': hq, '11': hq, '12': hq, '13': hq, '14': hq, '15': hq,
                                                '16': hq},
                            'room': room,
                            'rid': item.get('rid'),
                            'proj_name': proj_info.get('proj_name'),
                            'proj_id': proj_info.get('id')
                        }
            data_from_last_seven[str(nextday)] = {'1': aml, '2': pml}
        if data_from_last_seven:
            redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid),
                              json.dumps(data_from_last_seven, default=str))

    # 根据已产生的预约更新剩余可预约数量
    today = datetime.now().date()
    query_sql = 'select * from {}.appt_record where book_date >= {} and state < {} and is_doc_change = 0' \
        .format(database, str(today), appt_config.APPT_STATE['canceled'])
    recordl = db.query_all(query_sql)
    pid_to_record = {}
    for item in recordl:
        pid = str(item['pid'])
        if pid not in pid_to_record:
            pid_to_record[pid] = []
        pid_to_record[pid].append(item)

    for pid, recordl in pid_to_record.items():
        data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid))
        if not data:
            continue
        data = json.loads(data)
        for record in recordl:
            period = int(record['book_period'])
            rid = str(record.get('rid'))
            datestr = record['book_date']
            time_slot = str(record['time_slot'])
            if data.get(datestr):
                data[datestr][str(period)][rid]['quantity'] = int(data[datestr][str(period)][rid]['quantity']) - 1
                data[datestr][str(period)][rid]['hourly_quantity'][time_slot] = int(
                    data[datestr][str(period)][rid]['hourly_quantity'][time_slot]) - 1

        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid),
                          json.dumps(data, default=str))

    print("综合预约定时任务执行完成 - ", datetime.now())

    del db


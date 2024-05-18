import json

import redis
import requests

from datetime import datetime, date, timedelta
from itertools import groupby

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.composite_appointment.appt_config import APPT_URGENCY_LEVEL_KEY, \
    APPT_SIGN_IN_NUM_KEY, APPT_PROJECTS_KEY, \
    APPT_PROJECTS_CATEGORY_KEY, APPT_REMAINING_RESERVATION_QUANTITY_KEY, APPT_ATTENDING_DOCTOR_KEY, \
    APPT_DOCTOR_INFO_KEY, socket_push_url

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)


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
        elif type == 'his_visit_check':
            # 查询当天患者挂号信息
            from tools import his_visit_check
            data = his_visit_check(param)
        elif type == 'his_yizhu_info':
            # 查询当天患者医嘱信息
            from tools import his_yizhu_info
            data = his_yizhu_info(param)

    return data


"""
绑定用户
"""


def bind_user(patient_id: str, openid: str):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 使用 IGNORE 需要先创建唯一健约束 (patient_id, openid)
    db.execute(sql=f"INSERT IGNORE INTO nsyy_gyl.appt_person_association (patient_id, openid) "
                   f"VALUES (\'{patient_id}\', \'{openid}\')",
               need_commit=True)
    del db


"""
线上预约（微信小程序）   
"""


def online_appt(json_data):
    json_data['appt_type'] = appt_config.APPT_TYPE['online']
    json_data['urgency_level'] = appt_config.APPT_URGENCY_LEVEL['green']

    # 线上预约时自动绑定
    bind_user(json_data['patient_id'], json_data['openid'])
    create_appt(json_data)


"""
线下预约（现场）
"""


def offline_appt(json_data):
    json_data['appt_type'] = appt_config.APPT_TYPE['offline']
    json_data['urgency_level'] = json_data.get('urgency_level') or appt_config.APPT_URGENCY_LEVEL['green']

    create_appt(json_data)


"""
校验是否可以继续预约
"""


def check_appointment_quantity(proj_id, appt_date, period):
    redis_client = redis.Redis(connection_pool=pool)
    proj_id = str(proj_id)
    quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, proj_id)
    if not quantity_data:
        raise Exception(f'不存在项目 id 为 {proj_id} 的可预约项目')
    quantity_data = json.loads(quantity_data)
    # if appt_date not in quantity_data or not quantity_data[appt_date] \
    #         or int(quantity_data[appt_date][str(period)]['quantity']) <= 0:
    #     raise Exception('当前时间没有可预约数量，请选择其他时间')
    if appt_date not in quantity_data or not quantity_data[appt_date]:
        raise Exception('当前时间没有可预约数量，请选择其他时间')

    # 分配时间段
    current_date = str(date.today())
    time_slot = 1
    if appt_date == current_date:
        # 当天的预约根据当前预约时间确定起始时间段
        slot = appt_config.appt_slot_dict[datetime.now().hour]
        book_ok = False
        for i in range(slot, 17):
            num = quantity_data[appt_date][str(period)]['hourly_quantity'].get(str(i))
            if num and int(num) > 0:
                book_ok = True
                time_slot = i
                break
        if not book_ok:
            raise Exception('当前项目已饱和，请选择其他时间')
    else:
        book_ok = False
        for i in range(1, 17):
            num = quantity_data[appt_date][str(period)]['hourly_quantity'].get(str(i))
            if num and int(num) > 0:
                book_ok = True
                time_slot = i
                break
        if not book_ok:
            raise Exception('当前项目已饱和，请选择其他时间')

    return quantity_data, time_slot


def create_appt(json_data):
    json_data['create_time'] = str(datetime.now())[:19]
    # 检查项目是否可以预约，以及获取预估时间段
    quantity_data, time_slot = check_appointment_quantity(json_data['appt_proj_id'],
                                                          json_data['appt_date'],
                                                          json_data['appt_date_period'])
    json_data['time_slot'] = time_slot
    json_data['state'] = appt_config.APPT_STATE['booked']

    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = f"INSERT INTO nsyy_gyl.appt_record ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("预约记录入库失败! sql = " + insert_sql)
    del db

    # 更新可预约数量
    redis_client = redis.Redis(connection_pool=pool)
    appt_date = json_data['appt_date']
    quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity'] = \
        int(quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity']) - 1

    quantity_data[appt_date][str(json_data['appt_date_period'])]['hourly_quantity'][str(time_slot)] = \
        int(quantity_data[appt_date][str(json_data['appt_date_period'])]['hourly_quantity'][str(time_slot)]) - 1

    redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['appt_proj_id']),
                      json.dumps(quantity_data, default=str))

    # 缓存预约人的紧急程度
    key = str(json_data['patient_id']) + '_' + str(json_data['appt_proj_id'])
    redis_client.hset(APPT_URGENCY_LEVEL_KEY, key, json_data['urgency_level'])

    return last_rowid


"""
根据自助取号记录创建预约
"""


def auto_create_appt_by_self_reg(patient_id: int):
    param = {"type": "his_visit_check", "patient_id": patient_id}
    self_reg_record = call_third_systems_obtain_data('his_info', 'his_visit_check', param)
    if not self_reg_record:
        # patient_id 不存在自助挂号记录
        return

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 根据执行人和执行部门id查找项目 todo 自助挂号的项目如何做预约数量限制,
    period = '12' if datetime.now().hour < 12 else '2'
    for item in self_reg_record:

        doctor = item.get('执行人')
        # 查询是否已经创建预约了, 创建过跳过
        query_sql = f'select * from nsyy_gyl.appt_record where patient_id = {patient_id} and doctor = \'{doctor}\' and state < 5'
        appt_record = db.query_all(query_sql)
        if appt_record:
            continue

        projl = redis_client.hget(appt_config.APPT_DOCTOR_TO_PROJ_KEY, doctor)
        if not projl:
            # 未找到当天医生所属项目信息
            continue
        # todo 如果根据医生找不到项目如何处理
        appt_name = item.get('姓名')
        projl = json.loads(projl) # 包含上午和下午
        for proj in projl:
            if str(proj.get('period')) in period:
                # 创建预约
                appt_proj_info = json.loads(redis_client.get(APPT_PROJECTS_KEY, int(proj.get('proj_id'))))
                record = {
                    'appt_date': str(date.today()),
                    'appt_date_period': proj.get('period'),
                    'appt_type': appt_config.APPT_TYPE['auto_appt'],
                    'appt_name': appt_name,
                    'appt_proj_id': appt_proj_info.get('id'),
                    'appt_proj_category': appt_proj_info.get('proj_category'),
                    'appt_proj_name': appt_proj_info.get('proj_name'),
                    'appt_proj_type': appt_proj_info.get('proj_type'),
                    'patient_id': patient_id,
                    "price": proj.get('price'),
                    "room": appt_proj_info.get('proj_room'),
                    "state": 1,
                    "urgency_level": 1,
                }
                create_appt(record)
                continue


"""
查询预约记录
过滤条件有： 是否完成，openid，id_card_no, name, proj_id, doctor, patient_id
"""


def query_appt(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 查询预约记录时，如果患者是在远途自助机或者诊室找医生帮忙取号的，自动创建预约
    # 根据 patient_id 查询自助挂号信息
    patient_id = json_data.get('patient_id')
    if patient_id:
        auto_create_appt_by_self_reg(int(patient_id))

    state_sql = 'state > 0 '
    if 'is_completed' in json_data:
        state_sql = ' state >= {}'.format(appt_config.APPT_STATE['completed']) if int(json_data.get('is_completed')) \
            else 'state < {}'.format(appt_config.APPT_STATE['completed'])

    openid = json_data.get('openid')
    openid_sql = f' and openid = \'{openid}\' ' if openid else ''
    id_card_no = json_data.get('id_card_no')
    id_card_no_sql = f' and id_card_no LIKE \'%{id_card_no}%\' ' if id_card_no else ''
    name = json_data.get('name')
    name_sql = f" and appt_name LIKE \'%{name}%\' " if name else ''
    proj_id = json_data.get('proj_id')
    proj_id_sql = f' and appt_proj_id = {proj_id}' if proj_id else ''
    doctor = json_data.get('doctor')
    doctor_sql = f' and doctor LIKE \'%{doctor}%\' ' if doctor else ''
    start_time, end_time = json_data.get("start_time"), json_data.get("end_time")
    time_sql = f' and (appt_date BETWEEN \'{start_time}\' AND \'{end_time}\') ' if start_time and end_time else ''
    patient_id_sql = f' and patient_id = \'{patient_id}\' ' if patient_id else ''

    query_sql = f"select * from nsyy_gyl.appt_record " \
                f"where {state_sql}{doctor_sql}{openid_sql}{id_card_no_sql}{time_sql}{name_sql}{proj_id_sql}{patient_id_sql}"
    appts = db.query_all(query_sql)

    # 组装医嘱信息
    for record in appts:
        appt_id = record.get('id')
        query_sql = f"select * from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}"
        advicel = db.query_all(query_sql)
        record['doctor_advice'] = advicel
        record['time_slot'] = appt_config.APPT_PERIOD_INFO.get(int(record['time_slot']))

    del db

    total = len(appts)
    page_number, page_size = json_data.get("page_number"), json_data.get("page_size")
    if page_number and page_size:
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        appts = appts[start_index:end_index]

    return appts, total


"""
完成/取消/过号 预约
"""


def operate_appt(appt_id: int, type: int):
    cur_time = str(datetime.now())[:19]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select * from nsyy_gyl.appt_record where id = {int(appt_id)}'
    record = db.query_one(query_sql)
    if not record:
        raise Exception(f'预约id {appt_id} 预约记录不存在，请检查入参.')

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
    del db

    # 预约完成，查询医嘱打印 引导单
    if type == 1:
        create_appt_by_doctor_advice(record.get('patient_id'), record.get('doctor'), appt_id, int(record.get('urgency_level')))

    # 取消预约，可预约数量 + 1
    if type == 2:
        proj_id, period, appt_date = str(record.get('appt_proj_id')), str(
            record.get('appt_date_period')), record.get('appt_date')
        redis_client = redis.Redis(connection_pool=pool)
        quantity_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, proj_id)
        if not quantity_data:
            print(f'取消预约更新可预约数量：不存在项目 id 为 {proj_id} 的预约项目')
            return
        quantity_data = json.loads(quantity_data)
        quantity_data[appt_date][period]['quantity'] = int(quantity_data[appt_date][period].get('quantity') + 1)
        quantity_data[appt_date][period]['hourly_quantity'][str(record.get('time_slot'))] = \
            int(quantity_data[appt_date][period]['hourly_quantity'][str(record.get('time_slot'))] + 1)
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, proj_id, json.dumps(quantity_data, default=str))

    # 过号，重新取号，排在最后
    if type == 3:
        sign_in({'appt_proj_id': str(record.get('appt_proj_id')), 'appt_id': str(record.get('id')),
                 'appt_type': int(record.get('appt_type')), 'patient_id': str(record.get('patient_id'))})


"""
根据医嘱创建预约
"""


def create_appt_by_doctor_advice(patient_id: str, doc_name: str, appt_id, urgency_level):
    param = {"type": "his_yizhu_info", 'patient_id': patient_id, 'doc_name': doc_name}
    doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    advice_dict = {}
    for item in doctor_advice:
        key = item.get('执行部门ID')
        if key not in advice_dict:
            advice_dict[key] = []
        advice_dict[key].append(item)

    # 计算总价格
    for dept_id, value in advice_dict.items():
        if not value:
            continue
        # 计算总价格
        price = 0
        for d in value:
            price += d.get('实收金额')

        # 根据医嘱中的执行科室id 查询出院内项目
        query_sql = f'select * from nsyy_gyl.appt_project where proj_type = 2 and dept_id = {dept_id}'
        projl = db.query_all(query_sql)
        if not projl:
            print('当前医嘱没有可预约项目，使用默认项目创建预约', dept_id)
            appt_proj_category = 500
            appt_proj_id = 500
            appt_proj_name = "医嘱项目"
            appt_proj_type = 2
            room = "医嘱项目"
        else:
            appt_proj_category = projl[0].get('proj_category')
            appt_proj_id = projl[0].get('id')
            appt_proj_name = projl[0].get('proj_name')
            appt_proj_type = projl[0].get('proj_type')
            room = projl[0].get('proj_room')

        dept_info = redis_client.hget(appt_config.APPT_DEPT_INFO_KEY, str(dept_id))
        location_id = ''
        if dept_info:
            dept_info = json.loads(dept_info)
            location_id = dept_info.get('location_id')

        record = {
            'father_id': int(appt_id),
            "appt_date": str(date.today()),
            "appt_date_period": 1 if datetime.now().hour < 12 else 2,
            "appt_type": 4,
            "appt_name": value[0].get('姓名'),
            "appt_proj_category": appt_proj_category,
            "appt_proj_id": appt_proj_id,
            "appt_proj_name": appt_proj_name,
            "appt_proj_type": appt_proj_type,
            "patient_id": patient_id,
            "price": price,
            "room": room,
            "state": 1,
            "urgency_level": int(urgency_level),
            "location_id": location_id
        }

        new_appt_id = create_appt(record)
        advicel = []
        for v in value:
            json_data = {
                'appt_id': new_appt_id,
                'pay_id': v.get('NO'),
                'advice_info': v.get('医嘱内容'),
                'advice_desc': v.get('检查明细项'),
                'dept_id': v.get('执行部门ID'),
                'dept_name': v.get('执行科室'),
                'price': v.get('实收金额')
            }

            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_advice ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                raise Exception("医嘱记录入库失败! sql = " + insert_sql)
            json_data['id'] = last_rowid
            advicel.append(json_data)

    del db


"""
预约签到
"""


def sign_in(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    appt_id = int(json_data['appt_id'])
    appt_type = int(json_data.get('appt_type'))
    patient_id = int(json_data.get('patient_id'))
    # 如果是医嘱预约，检查付款状态
    if appt_type == 4:
        # 根据预约id 查询医嘱记录
        query_sql = f'select pay_id from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}'
        advicel = db.query_all(query_sql)
        if advicel:
            pay_ids = [item['pay_id'] for item in advicel]
            param = {"type": "his_pay_info", "patient_id": patient_id, "no_list": pay_ids}
            his_pay_info = call_third_systems_obtain_data('his_info', 'his_pay_info', param)
            is_ok = False
            for p in his_pay_info:
                if int(p.get('记录状态')) != 0:
                    is_ok = True
                    break
            if not is_ok:
                raise Exception('所有医嘱项目均为付款，请及时付款', param)

    # 签到前到 his 中取号, 小程序预约，现场预约需要取号。 自助挂号机挂号的预约不需要挂号. todo 取号价格待更换为真实的数据
    if appt_type in (1, 2):
        param = {"type": "his_visit_reg", "patient_id": json_data.get('patient_id'), "AsRowid": 2116, "PayAmt": 0.01}
        his_socket_ret_code = call_third_systems_obtain_data('his_socket', 'his_visit_reg', param)
        if his_socket_ret_code != '0':
            raise Exception('在 his 中取号失败， 签到失败, ResultCode: ', his_socket_ret_code)

    # 判断是否需要更换项目
    change_proj_sql = ''
    quantity_data = ''
    time_slot = 0
    if 'appt_proj_name' in json_data and json_data.get('appt_proj_name'):
        # 检查项目是否可以预约
        quantity_data, time_slot = check_appointment_quantity(json_data['appt_proj_id'], json_data['appt_date'],
                                                   json_data['appt_date_period'])

        change_proj_sql = ', appt_proj_id = {}, appt_proj_type = {}, appt_proj_category = {},' \
                          ' appt_proj_name = \'{}\', room = \'{}\' ' \
            .format(json_data['appt_proj_id'], json_data['appt_proj_type'],
                    json_data['appt_proj_category'], json_data['appt_proj_name'], json_data['room'])

    sign_in_num = __get_signin_num(int(json_data['appt_proj_id']))
    sign_in_time = str(datetime.now())[:19]
    op_sql = ' sign_in_time = \'{}\', sign_in_num = {}, state = {} '.format(sign_in_time, sign_in_num,
                                                                            appt_config.APPT_STATE['in_queue'])
    update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql}{change_proj_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db

    # 如果更换项目，更新可预约数量
    if quantity_data:
        redis_client = redis.Redis(connection_pool=pool)
        appt_date = json_data['appt_date']
        quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity'] = \
            int(quantity_data[appt_date][str(json_data['appt_date_period'])]['quantity']) - 1
        quantity_data[appt_date][str(json_data['appt_date_period'])]['hourly_quantity'][str(time_slot)] = \
            int(quantity_data[appt_date][str(json_data['appt_date_period'])]['hourly_quantity'][str(time_slot)]) - 1
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(json_data['appt_proj_id']),
                          json.dumps(quantity_data, default=str))


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
    socket_data = {"msg": '请患者 {} 到 {} {} 号诊室就诊'.format(json_data.get('name'), json_data.get('proj_name'),
                                                                 str(json_data.get('proj_room'))),
                   "type": 200}
    if global_config.run_in_local:
        # 测试环境
        data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(socket_push_url, data=json.dumps(data), headers=headers)
        print("Socket Push Status: ", response.status_code, "Response: ", response.text)
    else:
        # 正式环境： todo 待测试正式环境 socket 发送用法是否有问题
        from tools import socket_send
        socket_send(socket_data, 'm_user', socket_id)


"""
叫号下一个 
"""


def next_num(id, is_group):
    data_list, photo = query_wait_list({'type': 1, 'wait_id': id})

    # 更新列表中第一个为处理中
    if data_list:
        wait_list = data_list[0].get('wait_list')
        if wait_list and wait_list[0].get('state') == appt_config.APPT_STATE['processing']:
            raise Exception('当前存在处理中的病患，无法执行下一个操作，请先处理当前患者')

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        update_sql = 'UPDATE nsyy_gyl.appt_record SET state = {} WHERE id = {} ' \
            .format(appt_config.APPT_STATE['processing'], data_list[0].get('wait_list')[0].get('id'))
        db.execute(sql=update_sql, need_commit=True)
        del db

        # 呼叫患者
        json_data = {
            'socket_id': 'd' + str(id) if is_group else 'z' + str(id),
            'name': data_list[0].get('wait_list')[0].get('appt_name'),
            'proj_name': data_list[0].get('wait_list')[0].get('appt_proj_name'),
            'proj_room': data_list[0].get('wait_list')[0].get('room')
        }
        call(json_data)
        data_list[0].get('wait_list')[0]['state'] = appt_config.APPT_STATE['processing']

    return data_list


"""
查询所有预约项目
"""


def query_all_appt_project(type: int):
    # 1 先查询所有项目列表，类型相同的仅查一个
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select proj_category, max(proj_name) as proj_name from nsyy_gyl.appt_project where proj_type = {type} group by proj_category'
    projectl = db.query_all(query_sql)
    del db

    # 2 查询项目剩余可预约数量
    today_date = str(datetime.today())[:10]
    redis_client = redis.Redis(connection_pool=pool)
    for proj in projectl:
        rooml = redis_client.hget(APPT_PROJECTS_CATEGORY_KEY, str(proj['proj_category']))
        if not rooml:
            print('缓存中不存在 proj_category 为 ', str(proj['proj_category']), ' 的项目信息')
            continue
        rooml = json.loads(rooml)
        bookable_list = []
        for room in rooml:
            quantityd = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(room['id']))
            if quantityd:
                quantityd = json.loads(quantityd)
                for date, slots in quantityd.items():
                    for slot, info in slots.items():
                        if today_date == date and not if_the_current_time_period_is_available(slot):
                            continue
                        info['date'], info['period'] = date, slot
                        bookable_list.append(info)
        # 对数据按照日期进行分组
        sorted_data = sorted(bookable_list, key=lambda x: (x['date'], x['period']))

        data_list = []
        for key, group in groupby(sorted_data, key=lambda x: (x['date'], x['period'])):
            # todo 暂时先将价格改为 0.01，共测试使用
            # data_list.append({
            #     "date": key[0],
            #     "period": key[1],
            #     "list": list(group)
            # })
            list_group = list(group)
            for item in list_group:
                item['price'] = float(0.01)
            data_list.append({
                "date": key[0],
                "period": key[1],
                "list": list_group
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
    redis_client = redis.Redis(connection_pool=pool)

    wait_id = int(json_data.get('wait_id'))
    type = int(json_data.get('type'))
    wait_state = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'])
    todaystr = date.today()
    if int(type) == 1:
        condition_sql = f'appt_proj_id = {wait_id} and state in {wait_state} and appt_date = \'{todaystr}\' '
    elif int(type) == 2:
        condition_sql = f'appt_proj_category = {wait_id} and state in {wait_state} and appt_date = \'{todaystr}\' '

    query_sql = f'select * from nsyy_gyl.appt_record where {condition_sql} '
    appts = db.query_all(query_sql)
    del db

    # 如果是诊室，查询医生图片
    photo = ''
    if type == 1:
        period = 1 if datetime.now().hour < 12 else 2
        today_date = str(date.today())
        proj_info = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, wait_id)
        if proj_info:
            proj_info = json.loads(proj_info)
            appt_info = proj_info.get(today_date)
            if appt_info and str(period) in appt_info:
                photo = appt_info.get(str(period)).get("doctor_photo")

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
        for index, item in enumerate(wait_list):
            item["sort_index"] = index + 1  # 排序字段从 1 开始
        ret = {
            'appt_proj_name': appt_proj_name,
            'doctor': doctor,
            'room': room,
            'wait_list': wait_list
        }
        result.append(ret)

    return result, photo


"""
更新医嘱付款状态
"""


def update_doctor_advice_pay_state(idl):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    ids = ", ".join(map(str, idl))
    update_sql = f'update nsyy_gyl.appt_doctor_advice set state = 1 where id in ({ids})'
    db.execute(update_sql, need_commit=True)
    del db


"""
查询医嘱
"""


def query_advice_by_father_appt_id(father_appt_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = f"select * from nsyy_gyl.appt_record where father_id = {int(father_appt_id)} "
    appts = db.query_all(query_sql)

    for record in appts:
        appt_id = int(record.get('id'))
        record['time_slot'] = appt_config.APPT_PERIOD_INFO.get(int(record['time_slot']))
        query_sql = f'select * from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}'
        advicel = db.query_all(query_sql)
        if advicel:
            # 按 pay_id 排序
            advicel.sort(key=lambda x: x['pay_id'])
            # 根据 pay_id 分组并计算每个分组的 price 总和
            grouped_data = {}
            for key, group in groupby(advicel, key=lambda x: x['pay_id']):
                group_list = list(group)
                total_price = sum(item['price'] for item in group_list)
                grouped_data[key] = {
                    'items': group_list,
                    'total_price': total_price
                }

            record['doctor_advice'] = grouped_data
    del db
    return appts


"""
加载预约数据到内存
1. 当天预约人的紧急程度
2. 当天的签到计数
3. 近7天的可预约项目，包含剩余可预约数量
"""


def load_appt_data_into_cache():
    current_time = datetime.now()
    print(" 执行综合预约定时任务 ", current_time)

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 清空旧的预约数据
    keys = redis_client.keys('APPT_*')
    for key in keys:
        redis_client.delete(key)

    # 缓存执行科室信息
    query_sql = 'select * from nsyy_gyl.appt_dept_info'
    dept_infol = db.query_all(query_sql)
    for item in dept_infol:
        redis_client.hset(appt_config.APPT_DEPT_INFO_KEY, str(item.get('dept_id')), json.dumps(item, default=str))

    # 缓存医嘱信息 todo 是否近缓存当天的医嘱?
    query_sql = 'select * from nsyy_gyl.appt_doctor_advice'
    advice_list = db.query_all(query_sql)
    adviced = {}
    for item in advice_list:
        if str(item.get('appt_id')) not in adviced:
            adviced[str(item.get('appt_id'))] = []
        adviced[str(item.get('appt_id'))].append(item)

    for key, value in adviced.items():
        redis_client.hset(appt_config.APPT_DOCTOR_ADVICE_KEY, str(key), json.dumps(value, default=str))

    # 取消所有过期预约记录
    today_str = str(datetime.now().date())
    update_sql = 'UPDATE nsyy_gyl.appt_record SET state = {}, cancel_time = \'{}\'' \
                 ' where appt_date < \'{}\' and state < {} ' \
        .format(appt_config.APPT_STATE['canceled'], str(current_time)[:19], today_str,
                appt_config.APPT_STATE['completed'])
    db.execute(sql=update_sql, need_commit=True)

    # 查询当天所有未取消的预约, 缓存预约人的紧急情况 & 签到计数
    query_sql = f'select * from nsyy_gyl.appt_record where appt_date = \'{today_str}\' and state < 6'
    appt_recordl = db.query_all(query_sql)
    for record in appt_recordl:
        # 缓存紧急程度
        key = str(record['patient_id']) + '_' + str(record['appt_proj_id'])
        redis_client.hset(APPT_URGENCY_LEVEL_KEY, key, record['urgency_level'])

        # 更新当天的签到计数
        appt_proj_id = int(record['appt_proj_id'])
        if record['sign_in_num']:
            sign_in_num = int(record['sign_in_num']) or -1
            old_num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, appt_proj_id) or 0
            if sign_in_num and int(old_num) < sign_in_num:
                redis_client.hset(APPT_SIGN_IN_NUM_KEY, appt_proj_id, sign_in_num)

    # 缓存医生照片信息
    query_sql = 'select * from nsyy_gyl.appt_doctor_info'
    appt_doctor_infol = db.query_all(query_sql)
    for item in appt_doctor_infol:
        key = item.get('room') + item.get('name')
        redis_client.hset(APPT_DOCTOR_INFO_KEY, key, item.get('photo'))

    weekday_number = (datetime.today().weekday() + 1) % 8
    # 缓存坐诊医生信息 & 当天的坐诊医生到项目的映射
    query_sql = 'select appt_doctor_sched.doctor_his_name, ' \
                'appt_doctor_sched.doctor_name, appt_doctor_sched.consultation_room, ' \
                'appt_doctor_sched.proj_id, appt_doctor_sched.day_of_week, ' \
                'appt_doctor_sched.period, appt_doctor.dept_id, appt_doctor.dept_name, ' \
                'appt_doctor.doctor_id, appt_doctor.doctor_type, appt_doctor.price, appt_doctor.appointment_id ' \
                'from nsyy_gyl.appt_doctor_sched ' \
                'INNER JOIN nsyy_gyl.appt_doctor ON appt_doctor_sched.doctor_his_name = appt_doctor.doctor_name'
    doctor_schedl = db.query_all(query_sql)
    doctord = {}
    doctor_to_proj = {}
    for item in doctor_schedl:
        key = f"{item['proj_id']}_{item['day_of_week']}_{item['period']}"
        if key not in doctord:
            doctord[key] = []
        doctord[key].append(item)

        # 如果是当天的 缓存 医生和项目的映射
        if int(item['day_of_week']) == int(weekday_number):
            if item['doctor_his_name'] not in doctor_to_proj:
                doctor_to_proj[item.get('doctor_his_name')] = []
            doctor_to_proj[item.get('doctor_his_name')].append(item)

    for key, item in doctord.items():
        redis_client.hset(APPT_ATTENDING_DOCTOR_KEY, key, json.dumps(item, default=str))

    for key, item in doctor_to_proj.items():
        redis_client.hset(appt_config.APPT_DOCTOR_TO_PROJ_KEY, key, json.dumps(item, default=str))

    # 缓存所有项目, 缓存近 7 天的项目可预约情况
    query_sql = f'select * from nsyy_gyl.appt_project'
    appt_projectl = db.query_all(query_sql)
    group_by_categoryd = {}
    # 按 category 分组
    for item in appt_projectl:
        category = item['proj_category']
        if category not in group_by_categoryd:
            group_by_categoryd[category] = []
        group_by_categoryd[category].append(item)
    for category, list in group_by_categoryd.items():
        redis_client.hset(APPT_PROJECTS_CATEGORY_KEY, str(category), json.dumps(list, default=str))

    for appt_project in appt_projectl:
        redis_client.hset(APPT_PROJECTS_KEY, int(appt_project['id']), json.dumps(appt_project, default=str))
        # 缓存预约项目近 7 天的剩余可预约数量
        quantity = appt_project.get('proj_capacity')
        quantity_data = {}
        # 缓存近 7 天的可预约数量
        today = datetime.now().date()
        for i in range(7):
            nextday = today + timedelta(days=i)
            weekday_number = (nextday.weekday() + 1) % 8
            value = {}
            # 上午
            doct = redis_client.hget(APPT_ATTENDING_DOCTOR_KEY, f"{appt_project['id']}_{weekday_number}_1")
            if doct:
                doct = json.loads(doct)
                # 多个医生，提取 doctor_name 字段并拼接成字符串
                doctorl = ', '.join([d['doctor_his_name'] for d in doct])
                price = max(doct, key=lambda x: float(x['price']))['price']
                dept_id = doct[0].get('dept_id')
                # 根据房间号和医生名字找医生图片
                key = doct[0].get('consultation_room') + doct[0].get('doctor_name')
                photo = redis_client.hget(appt_config.APPT_DOCTOR_INFO_KEY, key)
                # 计算半小时的容量
                hq = int(quantity / 8)
                value['1'] = {
                    'date': 'am',
                    'quantity': quantity,
                    'max_quantity': quantity,
                    'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq, '6': hq, '7': hq, '8': hq},
                    'doctor': doctorl,
                    'doctor_dept_id': dept_id,
                    'price': float(price),
                    'room': appt_project.get('proj_room'),
                    'proj_name': appt_project.get('proj_name'),
                    'proj_id': appt_project.get('id'),
                    'proj_type': appt_project.get('proj_type'),
                    'proj_category': appt_project.get('proj_category'),
                    'doctor_photo': photo if photo else ''
                }
            doct = redis_client.hget(APPT_ATTENDING_DOCTOR_KEY, f"{appt_project['id']}_{weekday_number}_2")
            if doct:
                doct = json.loads(doct)
                doctorl = ', '.join([d['doctor_his_name'] for d in doct])
                price = max(doct, key=lambda x: float(x['price']))['price']
                dept_id = doct[0].get('dept_id')
                # 根据房间号和医生名字找医生图片
                key = doct[0].get('consultation_room') + doct[0].get('doctor_name')
                photo = redis_client.hget(appt_config.APPT_DOCTOR_INFO_KEY, key)
                hq = int(quantity / 8)
                value['2'] = {'date': 'pm',
                              'quantity': quantity,
                              'max_quantity': quantity,
                              'hourly_quantity': {'9': hq, '10': hq, '11': hq, '12': hq, '13': hq, '14': hq, '15': hq, '16': hq},
                              'doctor': doctorl,
                              'doctor_dept_id': dept_id,
                              'price': float(price),
                              'room': appt_project.get('proj_room'),
                              'proj_name': appt_project.get('proj_name'),
                              'proj_id': appt_project.get('id'),
                              'proj_type': appt_project.get('proj_type'),
                              'proj_category': appt_project.get('proj_category'),
                              'doctor_photo': photo if photo else ''
                              }
            if not doct and int(appt_project['proj_type']) == 2:
                # 院内项目不指定医生
                hq = int(quantity / 8)
                # 'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq, '6': hq, '7': hq, '8': hq},
                # 'hourly_quantity': {'9': hq, '10': hq, '11': hq, '12': hq, '13': hq, '14': hq, '15': hq, '16': hq},
                # 'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq},
                # 'hourly_quantity': {'5': hq, '6': hq, '7': hq, '8': hq},
                value['1'] = {'date': 'am',
                              'quantity': quantity,
                              'max_quantity': quantity,
                              'hourly_quantity': {'1': hq, '2': hq, '3': hq, '4': hq, '5': hq, '6': hq, '7': hq, '8': hq},
                              'room': appt_project.get('proj_room'),
                              'proj_name': appt_project.get('proj_name'),
                              'proj_id': appt_project.get('id'),
                              'proj_type': appt_project.get('proj_type'),
                              'proj_category': appt_project.get('proj_category')
                              }
                value['2'] = {'date': 'pm',
                              'quantity': quantity,
                              'max_quantity': quantity,
                              'hourly_quantity': {'9': hq, '10': hq, '11': hq, '12': hq, '13': hq, '14': hq, '15': hq, '16': hq},
                              'room': appt_project.get('proj_room'),
                              'proj_name': appt_project.get('proj_name'),
                              'proj_id': appt_project.get('id'),
                              'proj_type': appt_project.get('proj_type'),
                              'proj_category': appt_project.get('proj_category')
                              }

            if value:
                quantity_data[str(nextday)] = value
        if quantity_data:
            redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(appt_project['id']),
                              json.dumps(quantity_data, default=str))

    # 根据已产生的预约更新剩余可预约数量
    today = datetime.now().date()
    query_sql = 'select * from nsyy_gyl.appt_record where appt_date >= {} and state < {}'.format(str(today),
                                                                                                 appt_config.APPT_STATE[
                                                                                                     'canceled'])
    appt_record_list = db.query_all(query_sql)
    appt_proj_id_to_appt = {}
    for item in appt_record_list:
        appt_proj_id = item['appt_proj_id']
        if appt_proj_id not in appt_proj_id_to_appt:
            appt_proj_id_to_appt[appt_proj_id] = []
        appt_proj_id_to_appt[appt_proj_id].append(item)
    del db

    for proj_id, recordl in appt_proj_id_to_appt.items():
        data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(proj_id))
        if not data:
            continue
        data = json.loads(data)
        for record in recordl:
            period = int(record['appt_date_period'])
            datestr = record['appt_date']
            time_slot = str(record['time_slot'])
            if data.get(datestr):
                data[datestr][str(period)]['quantity'] = int(data[datestr][str(period)]['quantity']) - 1
                data[datestr][str(period)]['hourly_quantity'][time_slot] = int(data[datestr][str(period)]['hourly_quantity'][time_slot]) - 1

        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, int(proj_id),
                          json.dumps(data, default=str))

    print(" 综合预约定时任务执行完成 ", datetime.now())
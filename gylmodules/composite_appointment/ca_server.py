import json
import time
from collections import defaultdict

import redis
import requests

from datetime import datetime, date, timedelta
from itertools import groupby

from gylmodules import global_config, global_tools
from gylmodules.composite_appointment import appt_config, sched_manage
from gylmodules.utils.db_utils import DbUtil
from gylmodules.composite_appointment.appt_config import \
    APPT_SIGN_IN_NUM_KEY, APPT_PROJECTS_KEY, APPT_REMAINING_RESERVATION_QUANTITY_KEY, \
    APPT_DOCTORS_KEY, APPT_EXECUTION_DEPT_INFO_KEY, APPT_ROOMS_KEY, \
    APPT_DAILY_AUTO_REG_RECORD_KEY, APPT_DOCTORS_BY_NAME_KEY, \
    APPT_ROOMS_BY_PROJ_KEY

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)

lock_redis_client = redis.Redis(connection_pool=pool)

# 可以预约的时间段
room_dict = {}
periodd = {'1': [1, 2, 3, 4], '2': [5, 6, 7, 8]}  # 1 上午 2 下午 3 全天
periodd['3'] = periodd['1'] + periodd['2']


def cache_capacity():
    """
    系统启动后 需要先缓存排班信息，以及每个诊室的剩余可预约数量
    :return:
    """
    start_time = time.time()
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    today = datetime.now().date()
    start_date = today.strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=6)).strftime('%Y-%m-%d')

    # 缓存门诊项目近七天的可预约情况
    projects = db.query_all(f'select * from nsyy_gyl.appt_project')
    # 不需要判断 d.his_status = 1，每天同步医生信息时，会更新当天的排班医生的状态
    all_schedule = db.query_all(f"""select t.did, t.rid, t.pid, t.shift_date, t.shift_type, 
                                    case when t.status is null THEN 3 else t.status end as status from (
                                        select s.did, s.rid, s.pid, s.shift_date, s.shift_type, ds.status 
                                        from nsyy_gyl.appt_schedules s left join nsyy_gyl.appt_schedules_doctor ds 
                                        on s.did = ds.did and s.shift_date = ds.shift_date 
                                        and s.shift_type = ds.shift_type WHERE s.shift_date 
                                        between '{start_date}' and '{end_date}' and (ds.status = 1 or s.did = 0)) t""")
    for proj in projects:
        # 近 7 天的可预约数量
        pid = int(proj.get('id'))
        quantity = proj.get('nsnum')
        hq = int(quantity / 8)  # 计算每个时段的数量

        for i in range(7):
            shift_date = today + timedelta(days=i)
            # 门诊项目
            shift_date_schedule = [s for s in all_schedule if s['pid'] == pid and s['shift_date'] == shift_date]
            for item in shift_date_schedule:
                rid = str(item.get('rid'))
                shift_type = str(item.get('shift_type'))  # 上午(1) 或 下午(2)

                if rid not in room_dict:
                    room_dict[str(item.get('rid'))] = {}
                if str(shift_date) not in room_dict[rid]:
                    room_dict[rid][str(shift_date)] = {}

                time_slots = {
                    '1': hq, '2': hq, '3': hq, '4': hq
                } if shift_type == '1' else {
                    '5': hq, '6': hq, '7': hq, '8': hq
                }
                # 更新房间容量字典
                room_dict[rid][str(shift_date)][shift_type] = time_slots

    # 根据已产生的预约更新剩余可预约数量
    query_sql = f'''select * from nsyy_gyl.appt_record where book_date >= CURDATE() and type in (1, 2) 
                    and state < {appt_config.APPT_STATE['canceled']} and is_doc_change = 0'''
    records = db.query_all(query_sql)
    del db
    for record in records:
        period = str(record['book_period'])
        rid = str(record.get('rid'))
        datestr = record['book_date']
        time_slot = str(record['time_slot'])

        # 确保房间和日期存在
        if rid in room_dict and datestr in room_dict[rid]:
            if period in room_dict[rid][datestr] and time_slot in room_dict[rid][datestr][period]:
                room_dict[rid][datestr][period][time_slot] -= 1
            else:
                print(datetime.now(),
                      f'rid={rid}, date={datestr}, period={period}, slot={time_slot} 该时段不存在，可能已停诊')
        else:
            print(datetime.now(), f'rid={rid}, date={datestr} 没有找到匹配的房间或日期，可能已停诊')

    print(datetime.now(), '房间容量缓存完成, 耗时: ', time.time() - start_time, ' s')


cache_capacity()


"""
调用第三方系统
"""


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", timeout=3, json=param)
            data = response.text
            data = json.loads(data)
            if type == 'his_visit_reg':
                print(datetime.now(), 'his 取号返回: ', data, ' 取号参数：', param)
                data = data[2]
            elif type == 'reg_refund_apply':
                data = data
            else:
                data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'his_visit_reg':
            # 门诊挂号 当天
            from tools import nhis_api
            data = nhis_api(param, tcode='4005')
            print(datetime.now(), 'his 取号返回: ', data, ' 取号参数：', param)
            data = data[2]
            # data = data.get('ResultCode')
        elif type == 'his_visit_check':
            # 查询当天患者挂号信息
            from tools import his_visit_check
            data = his_visit_check(param)
        elif type == 'his_yizhu_info':
            # 查询当天患者医嘱信息
            # from tools import his_yizhu_info
            # data = his_yizhu_info(param)
            data = []
        elif type == 'his_pay_info':
            # 查询付款状态
            from tools import his_pay_info
            data = his_pay_info(param)
        elif type == 'orcl_db_read':
            # 根据 sql 查询数据
            from tools import orcl_db_read
            data = orcl_db_read(param)
        elif type == 'reg_refund_apply':
            from tools import reg_refund_apply
            data = reg_refund_apply(param)

    return data


def his_yizhu_info(patient_id, doc_name):
    """
    查询患者当天的检查检验医嘱
    :param patient_id:
    :param doc_name:
    :return:
    """
    cdate = str(datetime.today().date())
    sql = f"""select my.jiuzhenid 挂号单号, my.yizhuid 医嘱ID, my.yuanyizhuid 原医嘱ID, my.zhixingks "执行部门ID", my.bingrenxm 姓名,
            my.zhixingksmc 执行科室, my.yizhuxmid 医嘱项目ID, my.yizhumc 医嘱内容, coalesce(( select sum(mf.jiesuanje) 付款金额 
            from df_jj_menzhen.mz_jiesuan1 mj join df_jj_menzhen.mz_feiyong1 mf2 on mj.jiesuanid = mf2.jiesuanid
            join df_jj_menzhen.mz_feiyong2 mf on mf.feiyongid = mf2.feiyongid 
            where mf2.jiuzhenid = my.jiuzhenid and mf.yuanyizhuid = my.yizhuid),0) 付款金额
            from df_lc_menzhen.mz_yizhu my where my.bingrenxm not like '%测试%' 
            and my.yizhuxmid not in (select shoufeixmid from df_zhushuju.gy_shoufeixm where hesuanxm='30008')
            and my.bingrenid='{patient_id}' and my.kaidanysxm='{doc_name}' and my.kaidanrq::DATE = '{cdate}'
    """
    data = global_tools.call_new_his_pg(sql)
    return data


def online_appt(json_data):
    """
    线上预约（微信小程序）  前端调用 李工后端支付接口，李工后端监听支付状态，支付成功 调用该接口创建记录
    :param json_data:
    :return:
    """
    json_data['type'] = appt_config.APPT_TYPE['online']
    json_data['level'] = appt_config.APPT_URGENCY_LEVEL['green']
    json_data['state'] = appt_config.APPT_STATE['booked']
    json_data['pay_state'] = appt_config.appt_pay_state['oa_pay']
    create_appt(json_data)


# def offline_appt(json_data):
#     """
#     线下预约（现场）
#     :param json_data:
#     :return:
#     """
#     json_data['type'] = appt_config.APPT_TYPE['offline']
#     json_data['level'] = json_data.get('level') or appt_config.APPT_URGENCY_LEVEL['green']
#     json_data['state'] = appt_config.APPT_STATE['booked']
#     json_data['pay_state'] = appt_config.appt_pay_state['oa_pay']
#     create_appt(json_data)


def check_appointment_quantity(book_info):
    """
    校验是否可以继续预约
    小程序预约和线下预约选择的时间段（上午/下午）不能更改
    自助预约/医嘱预约可以根据容量调整时间段
    """
    def find_next_available(date, next_slot, period_list, find_in, pre_room_dict):
        capdict_am = pre_room_dict.get(str(book_info['room']), {}).get(date, {}).get('1', {})
        capdict_pm = pre_room_dict.get(str(book_info['room']), {}).get(date, {}).get('2', {})
        for s in period_list:
            if s <= 4 and int(find_in) in (1, 3):  # 上午时段
                if s >= next_slot and capdict_am.get(str(s), 0) > 0:
                    return date, s
            elif s > 4 and int(find_in) in (2, 3):  # 下午时段
                if s >= next_slot and capdict_pm.get(str(s), 0) > 0:
                    return date, s
        return None, None

    room = str(book_info['room'])
    book_date = book_info.get('date', None)
    period = str(book_info.get('period')) if book_info.get('period') else '3'

    if not book_info.get('time_slot', ''):
        current_slot = appt_config.appt_slot_dict[datetime.now().hour]
        if book_date and book_date != str(datetime.today().strftime("%Y-%m-%d")):
            current_slot = 5 if int(period) == 2 else 1
    else:
        current_slot = int(book_info.get('time_slot'))

    # 如果指定了日期，直接在指定日期查找可用时段
    if book_date:
        next_date, next_slot = find_next_available(book_date, current_slot, periodd[period], int(period), room_dict)
        if not next_slot:
            raise Exception("当前时间段无号源,请重新选择时间段")
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
            next_date, next_slot = find_next_available(date, slot_to_check, periodd[period], period, room_dict)
        else:
            next_date, next_slot = find_next_available(date, 1, periodd[period], period, room_dict)

        if next_slot:
            return next_date, next_slot

    raise Exception("未找到可用时间段")


def create_appt(json_data, last_date=None, last_slot=None):
    """
    创建预约
    1. 线上小程序预约 (前端发起付款，李工监听付款状态，付款成功，调用 wx_appt 接口)
    2. 现场 oa 预约
    3. 自助挂号机取号，查询预约记录时，根据挂号信息自动创建
    4. 根据医嘱创建预约
    :param json_data:
    :param last_date:
    :param last_slot:
    :return:
    """
    json_data['create_time'] = str(datetime.now())[:19]
    redis_client = redis.Redis(connection_pool=pool)
    if json_data.get('rid'):
        room_data = redis_client.hget(APPT_ROOMS_KEY, str(json_data.get('rid')))
        if not room_data:
            raise Exception("未找到预约诊室信息")
        room_data = json.loads(room_data)
        json_data['room'] = room_data.get('no')
        if 'location_id' not in json_data:
            json_data['location_id'] = room_data.get('no')
    if json_data.get('pid'):
        proj_data = redis_client.hget(APPT_PROJECTS_KEY, str(json_data.get('pid')))
        if not proj_data:
            raise Exception("未找到预约项目信息")
        proj_data = json.loads(proj_data)
        json_data['ptype'] = proj_data.get('proj_type')
        json_data['pname'] = proj_data.get('proj_name')
    if json_data.get('doc_id'):
        doc_data = redis_client.hget(APPT_DOCTORS_KEY, str(json_data.get('doc_id')))
        if not doc_data:
            raise Exception("未找到预约医生信息")
        doc_data = json.loads(doc_data)
        json_data['doc_his_name'] = doc_data.get('his_name')
        json_data['doc_dept_id'] = doc_data.get('dept_id')
        json_data['price'] = doc_data.get('fee')

    # 检查项目是否可以预约，以及获取预估时间段
    book_info = {'room': json_data['rid']}
    if last_date and last_slot:
        book_info['last_date'] = last_date
        book_info['last_slot'] = last_slot
    else:
        book_info['date'] = json_data['book_date'] if json_data.get('book_date') else str(
            datetime.today().strftime("%Y-%m-%d"))
        book_info['period'] = json_data['book_period'] if json_data.get('book_period') else '3'
        book_info['time_slot'] = json_data['time_slot'] if json_data.get('time_slot') else None
    bdate, bslot = check_appointment_quantity(book_info)

    json_data['book_date'] = bdate
    json_data['time_slot'] = bslot
    if bslot < 5:
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
    query_sql = f'select count(*) AS record_count from nsyy_gyl.appt_record ' \
                f'where state in {wait_state} and book_date = \'{bdate}\' {condition_sql} '
    result = db.query_one(query_sql)
    json_data['wait_num'] = int(result.get('record_count'))

    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.appt_record ({fileds}) VALUES {args}"
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


def auto_create_appt_by_auto_reg(patient_key, did, rid, pid):
    """
    自助机/诊间 挂号的补一条记录，用于排号，不消耗小程序号源
    :param patient_key:  患者姓名/身份证号
    :param did:
    :param rid:
    :param pid:
    :return:
    """
    # 根据身份证号或者就诊卡号查询患者当天的挂号记录
    condition_sql = f"( mzgh.bingrenxm like '{patient_key}' " \
                    f"or brxx.shenfenzh like '{patient_key}' " \
                    f"or brxx.jiuzhenkh like '{patient_key}' )"

    # 查询病人当天的挂号记录 不存在自助挂号记录 直接返回
    sql = f"""select mzgh.guahaoid "NO", mzgh.shoufeiid id, brxx.jiuzhenkh 就诊卡号, brxx.shenfenzh 身份证号,
	          brxx.bingrenid "病人ID", mzgh.bingrenxm 姓名, mzgh.guahaoks 执行部门id, mzgh.guahaoysxm 执行人,
	        case when mzgh.zuofeibz=1 or mzgh.jiaoyilx=-1 then -1 
	        when mzgh.zuofeibz=0 and mzgh.jiaoyilx=1 then 1 else null end as 记录状态
            from df_jj_menzhen.mz_guahao mzgh join df_bingrenzsy.gy_bingrenxx brxx on mzgh.bingrenid = brxx.bingrenid
            where {condition_sql} and date(mzgh.guahaorq) = current_date order by mzgh.guahaorq desc"""

    reg_recordl = global_tools.call_new_his_pg(sql)
    if not reg_recordl:
        raise Exception(f"未找到 {patient_key} 今天的自助挂号记录")

    # 查询当天所有自助挂号的记录（pay no）集合
    redis_client = redis.Redis(connection_pool=pool)
    created_pay_list = redis_client.smembers(APPT_DAILY_AUTO_REG_RECORD_KEY)

    # 上午挂号的可以预约上午和下午，下午挂号的只能预约下午， 1=上午 2=下午
    period = 1 if datetime.now().hour < 12 else 2
    # 同一个人 退费和正常挂号是不同的记录
    for item in reg_recordl:
        # 记录状态 1-正常的挂号或预约记录
        if int(item.get('记录状态')) != 1:
            continue

        # 判断是否已经创建过预约  TODO 新 his NO 长啥样
        pay_no = reg_recordl[0].get('NO')
        if pay_no in created_pay_list:
            print(f"{patient_key} 今天的自助挂号记录已经创建过预约记录，请勿重复创建")
            continue

        doctor_in_cache = redis_client.hget(APPT_DOCTORS_KEY, str(did))
        if not doctor_in_cache:
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, pay_no)
            print(datetime.now(), 'TODO: ', f'综合预约系统中不存在 {did} 医生，请及时维护门诊医生信息', item)
            continue

        target_doctor = json.loads(doctor_in_cache)
        target_proj = json.loads(redis_client.hget(APPT_PROJECTS_KEY, str(pid)))
        target_room = json.loads(redis_client.hget(APPT_ROOMS_KEY, str(rid)))
        try:
            # 根据上面的信息，创建预约
            record = {'type': appt_config.APPT_TYPE['after_reg'], 'patient_id': int(item.get('病人ID')),
                      'id_card_no': item.get('身份证号'), 'patient_name': item.get('姓名'),
                      'state': appt_config.APPT_STATE['booked'], 'pid': target_proj.get('id'),
                      'pname': target_proj.get('proj_name'), 'ptype': target_proj.get('proj_type'),
                      'rid': target_room.get('id'), 'room': target_room.get('no'), 'book_date': str(date.today()),
                      'book_period': period, 'level': 1, 'price': target_doctor.get('fee'),
                      'doc_id': target_doctor.get('id'), 'doc_his_name': target_doctor.get('his_name'),
                      'doc_dept_id': target_doctor.get('dept_id'), 'pay_no': pay_no,
                      'pay_state': appt_config.appt_pay_state['his_pay'],
                      'location_id': target_proj.get('location_id') if target_proj.get(
                          'location_id') else target_room.get(
                          'no')}
            new_appt_id, _, _ = create_appt(record)
            # 维护 pay no
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, pay_no)
            sign_in({
                'appt_id': new_appt_id,
                'type': record.get('type'),
                'patient_id': record.get('patient_id'),
                'patient_name': record.get('patient_name'),
                'pid': record.get('pid'),
                'rid': record.get('rid')
            })
        except Exception as e:
            print(datetime.now(), '根据自助挂号记录创建预约异常: ', e)


def query_appt_record(json_data):
    """
    查询预约记录
    过滤条件有： 是否完成，openid，id_card_no, name, proj_id, doctor, patient_id
    query_from = 1 oa 所有预约记录查询
    query_from = 2 oa 医生页面预约记录查询
    query_from = 3 oa 分诊页面预约记录查询
    query_from = 4 小程序查询
    :param json_data:
    :return:
    """
    # 根据 patient_id 查询自助挂号信息
    query_from = json_data.get('query_from')
    id_card_list = json_data.get('id_card_list')
    medical_card_list = json_data.get('medical_card_list')
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
    appts = db.query_all(f"select * from nsyy_gyl.appt_record where {condition_sql}")
    del db

    total = len(appts)
    page_number, page_size = json_data.get("page_number"), json_data.get("page_size")
    if page_number and page_size:
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        appts = appts[start_index:end_index]

    return appts, total


def push_patient(patient_name: str, socket_id: str):
    """
    预约有修改，通过 socket 通知前端
    :param patient_name:
    :param socket_id:
    :return:
    """
    try:
        socket_data = {"patient_name": patient_name, "type": 300}
        data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    except Exception as e:
        print(datetime.now(), "Socket Push Error: ", e.__str__())


def operate_appt(appt_id: int, type: int):
    """
    完成/取消/过号/报道 预约
    :param appt_id:
    :param type:
    :return:
    """
    cur_time = str(datetime.now())[:19]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select * from nsyy_gyl.appt_record where id = {int(appt_id)}'
    record = db.query_one(query_sql)
    if not record:
        raise Exception(datetime.now(), f' {appt_id} 预约记录不存在')

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

    update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql} WHERE id = {appt_id} '
    db.execute(sql=update_sql, need_commit=True)
    del db

    # 预约完成，查询医嘱打印 引导单
    if type == 1 and int(record.get('type')) < 4:
        # TODO 更新医嘱查询接口
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
        sign_in({'appt_id': record.get('id'), 'type': record.get('type'), 'patient_id': record.get('patient_id'),
                 'patient_name': record.get('patient_name'), 'pid': record.get('pid'), 'rid': record.get('rid')
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


def batch_insert_appt_doctor_advice(batch_insert_data):
    if not batch_insert_data:
        return
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    try:
        fields = ','.join(batch_insert_data[0].keys())
        values = [tuple(item.values()) for item in batch_insert_data]
        placeholders = ','.join(['%s'] * len(batch_insert_data[0]))

        insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_advice ({fields}) " \
                     f"VALUES {','.join([f'({placeholders})' for _ in values])}"
        flattened_values = [item for sublist in values for item in sublist]

        last_rowid = db.execute(sql=insert_sql, args=flattened_values, need_commit=True)
        if last_rowid == -1:
            raise Exception(datetime.now(), "医嘱记录批量入库失败!")
    except Exception as e:
        print(datetime.now(), f"数据库插入异常: {str(e)}")
    finally:
        del db


def create_appt_by_doctor_advice(patient_id: str, doc_name: str, id_card_no, appt_id, level):
    """
    根据医嘱创建预约
    :param patient_id:
    :param doc_name:
    :param id_card_no:
    :param appt_id:
    :param level:
    :return:
    """
    # TODO 更新查询医嘱接口
    doctor_advice = his_yizhu_info(patient_id, doc_name)
    if not doctor_advice:
        # 没有医嘱直接返回
        return

    # 使用defaultdict优化分组
    from collections import defaultdict
    advice_dict = defaultdict(list)
    dept_ids = set()
    for item in doctor_advice:
        dept_id = item.get('执行部门ID')
        advice_dict[dept_id].append(item)
        dept_ids.add(str(dept_id))  # 转换为字符串用于Redis查询

    redis_client = redis.Redis(connection_pool=pool)
    # 批量获取部门信息优化
    proj_info = {}
    if dept_ids:
        # 批量获取所有部门信息
        dept_projs = redis_client.hmget(APPT_EXECUTION_DEPT_INFO_KEY, list(dept_ids))
        proj_info = dict(zip(dept_ids, [json.loads(p) if p else None for p in dept_projs]))

    last_date, last_slot = None, None
    other_advice = []
    batch_insert_data = []  # 批量插入数据缓存
    current_time_period = 1 if datetime.now().hour < 12 else 2  # 预计算时间参数
    for dept_id, advicel in advice_dict.items():
        # 根据医嘱中的执行科室id 查询出院内项目
        proj = proj_info.get(str(dept_id))
        if not proj:
            print('当前医嘱没有可预约项目，暂时使用默认项目创建预约，待后续维护',
                  ' patient id ', patient_id, 'doc_name', doc_name, advicel)
            other_advice.extend(advicel)
            continue

        room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, proj.get('id')))
        record = {'father_id': int(appt_id), 'id_card_no': id_card_no, "book_date": str(date.today()),
                  "book_period": current_time_period, "type": appt_config.APPT_TYPE['advice_appt'],
                  "patient_id": patient_id, "patient_name": advicel[0].get('姓名'),
                  "pid": proj.get('id'), "pname": proj.get('proj_name'), "ptype": proj.get('proj_type'),
                  'rid': room.get('id'), 'room': room.get('no'),
                  "state": 0, "level": int(level),
                  "location_id": proj.get('location_id') if proj.get('location_id') else room.get('no'),
                  }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdate, bslot = create_appt(record, last_date, last_slot)
        last_slot = bslot
        last_date = bdate

        # 按 pay_id 排序，后按 pay_id 分组
        advicel.sort(key=lambda x: x['医嘱id'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(advicel, key=lambda x: x['医嘱id']):
            group_list = list(group)
            # 使用第一个元素的字典结构来创建合并后的记录
            batch_insert_data.append({
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('医嘱id'),
                'advice_desc': '; '.join(item['医嘱内容'] for item in group_list),
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': sum(float(item['付款金额']) for item in group_list)
            })

    if other_advice:
        advice_record = {'father_id': int(appt_id), 'id_card_no': id_card_no, "book_date": str(date.today()),
                         "book_period": 1 if datetime.now().hour < 12 else 2,
                         "type": appt_config.APPT_TYPE['advice_appt'],
                         "patient_id": patient_id, "patient_name": other_advice[0].get('姓名'),
                         "pid": 79, "pname": "其他项目", 'rid': 153, 'room': '当前诊室',
                         "ptype": 2, "state": 0, "level": int(level),
                         }
        # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
        new_appt_id, bdata, bslot = create_appt(advice_record, last_date, last_slot)
        sorted_other = sorted(other_advice, key=lambda x: x['医嘱id'])
        for key, group in groupby(sorted_other, key=lambda x: x['医嘱id']):
            group_list = list(group)
            combined_advice = {'appt_id': new_appt_id, 'pay_id': group_list[0]['医嘱id'],
                               'advice_desc': '; '.join(i['医嘱内容'] for i in group_list),
                               'dept_id': group_list[0]['执行部门ID'],
                               'dept_name': group_list[0]['执行科室'],
                               'price': sum(float(i['付款金额']) for i in group_list)
                               }
            batch_insert_data.append(combined_advice)

    batch_insert_appt_doctor_advice(batch_insert_data)


def update_advice(json_data):
    """
    更新医嘱
    :param json_data:
    :return:
    """
    # TODO 更新医嘱查询接口
    father_appt_id = int(json_data.get('appt_id'))
    patient_id = int(json_data.get('patient_id'))
    doc_name = json_data.get('doc_name')
    new_doctor_advice = his_yizhu_info(patient_id, doc_name)
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
    batch_insert_data = []  # 批量插入数据缓存
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
        query_sql = f'select * from nsyy_gyl.appt_record ' \
                    f'where book_date = \'{str(date.today())}\' and patient_id = {patient_id} and pid = {pid} '
        created = db.query_one(query_sql)
        del db

        if created:
            # 更新医嘱
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            appt_id = int(created.get('id'))
            data = db.query_all(f'select pay_id from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}')
            del db
            pay_ids = [item['pay_id'] for item in data]
            advicel.sort(key=lambda x: x['医嘱id'])
            for key, group in groupby(advicel, key=lambda x: x['医嘱id']):
                if key in pay_ids:
                    continue
                group_list = list(group)
                # 使用第一个元素的字典结构来创建合并后的记录
                new_json_data = {
                    'appt_id': appt_id,
                    'pay_id': group_list[0].get('医嘱id'),
                    'advice_desc': '; '.join(item['医嘱内容'] for item in group_list),
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': sum(float(item['付款金额']) for item in group_list)
                }
                batch_insert_data.append(new_json_data)
        else:
            # 新增医嘱
            if not proj:
                other_advice += advicel
                continue

            room = json.loads(redis_client.hget(APPT_ROOMS_BY_PROJ_KEY, pid))
            record = {'father_id': father_appt_id, "book_date": str(date.today()),
                      "book_period": 1 if datetime.now().hour < 12 else 2,
                      "type": appt_config.APPT_TYPE['advice_appt'], "patient_id": patient_id,
                      "patient_name": advicel[0].get('姓名'), "pid": pid, "pname": proj.get('proj_name'),
                      "ptype": proj.get('proj_type'), 'rid': room.get('id'), 'room': room.get('no'),
                      "state": 0, "level": int(level),
                      "location_id": proj.get('location_id') if proj.get('location_id') else room.get('no'),
                      }
            # 根据医嘱创建的预约，将执行科室的 id 存入 doctor_dept_id 中
            new_appt_id, bdate, bslot = create_appt(record, last_date, last_slot)
            last_slot = bslot
            last_date = bdate
            # 按 pay_id 排序，后按 pay_id 分组
            advicel.sort(key=lambda x: x['医嘱id'])
            # 根据 pay_id 分组并计算每个分组的 price 总和
            for key, group in groupby(advicel, key=lambda x: x['医嘱id']):
                group_list = list(group)
                # 使用第一个元素的字典结构来创建合并后的记录
                new_data = {
                    'appt_id': new_appt_id,
                    'pay_id': group_list[0].get('NO'),
                    'advice_desc': '; '.join(item['医嘱内容'] for item in group_list),
                    'dept_id': group_list[0].get('执行部门ID'),
                    'dept_name': group_list[0].get('执行科室'),
                    'price': sum(float(item['付款金额']) for item in group_list)
                }
                batch_insert_data.append(new_data)

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
        other_advice.sort(key=lambda x: x['医嘱id'])
        # 根据 pay_id 分组并计算每个分组的 price 总和
        for key, group in groupby(other_advice, key=lambda x: x['医嘱id']):
            group_list = list(group)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_data1 = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('医嘱id'),
                'advice_desc': '; '.join(item['医嘱内容'] for item in group_list),
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': sum(float(item['付款金额']) for item in group_list)
            }

    # 批量插入数据库
    batch_insert_appt_doctor_advice(batch_insert_data)


def inpatient_advice(json_data):
    """
    住院患者医嘱查询
    :param json_data:
    :return:
    """
    # TODO 更新医嘱查询接口
    advice_dict = {}
    doctor_advice = his_yizhu_info(json_data.get('patient_id'), json_data.get('doc_name'))
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
    """
    根据住院患者医嘱创建预约
    :param json_data:
    :return:
    """
    advicel = json_data.get('advicel')
    if not advicel:
        return
    sql = f"""
           SELECT brxx.SHENFENZH 身份证号, brxx.BINGRENID 病人ID FROM df_bingrenzsy.gy_bingrenxx brxx 
           WHERE brxx.BINGRENID = '{advicel[0].get('patient_id')}'  ORDER BY brxx.JIANDANGRQ DESC
        """
    patient_info = global_tools.call_new_his(sql)
    batch_insert_data = []
    if patient_info:
        patient_info = patient_info[0]
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
        for key, group in groupby(advicel, key=lambda x: x['NO']):
            group_list = list(group)
            # 使用第一个元素的字典结构来创建合并后的记录
            new_data2 = {
                'appt_id': new_appt_id,
                'pay_id': group_list[0].get('NO'),
                'advice_desc': '; '.join(item['检查明细项'] for item in group_list),
                'dept_id': group_list[0].get('执行部门ID'),
                'dept_name': group_list[0].get('执行科室'),
                'price': sum(item['实收金额'] for item in group_list)
            }
            batch_insert_data.append(new_data2)
    else:
        raise Exception('根据患者信息查询不到病人信息', ' 病人id = ', advicel[0].get('patient_id'))
    batch_insert_appt_doctor_advice(batch_insert_data)


def sign_in(json_data, over_num: bool = False):
    """
    预约签到
    1. 第一次签到 （his 取号/ 医嘱项目检查付款状态）
    2. 过号 重新取号
    :param json_data:
    :param over_num:
    :return:
    """
    # 七点之前 数据还没有同步
    current_time = datetime.now()
    if current_time.hour < 7:
        raise Exception("现在是早上7点之前，不允许签到。当前时间: {}".format(current_time))

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
        update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql} WHERE id = {appt_id} '
        db.execute(sql=update_sql, need_commit=True)
        del db
        return

    query_sql = f'select * from nsyy_gyl.appt_record where id = {appt_id}'
    record = db.query_one(query_sql)
    if int(record.get('state')) > appt_config.APPT_STATE['booked']:
        # 第一次签到 如果发现已经签到过，直接返回
        del db
        return

    if datetime.strptime(record.get('book_date'), '%Y-%m-%d').date() != datetime.now().date():
        del db
        raise Exception(f"预约日期是 {record.get('book_date')} 非当天的预约记录，无法签到")

    # # 如果是医嘱预约，检查付款状态 (type = 5 住院医嘱不需要检查付款状态)
    # if appt_type == appt_config.APPT_TYPE['advice_appt']:
    #     # 根据预约id 查询医嘱记录
    #     query_sql = f'select pay_id from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}'
    #     advicel = db.query_all(query_sql)
    #     if advicel:
    #         # TODO 待更新付款状态查询接口
    #         pay_ids = [item['pay_id'] for item in advicel]
    #         param = {"type": "his_pay_info", "patient_id": patient_id, "no_list": pay_ids}
    #         his_pay_info = call_third_systems_obtain_data('his_info', 'his_pay_info', param)
    #         is_ok = False
    #         # 如果有多个付款项目，只要有一个付款的就允许签到
    #         for p in his_pay_info:
    #             if int(p.get('记录状态')) != 0:
    #                 is_ok = True
    #                 break
    #         if not is_ok:
    #             raise Exception('所有医嘱项目均未付款，请及时付款后再签到', param)

    # 签到前到 his 中取号, 小程序预约，现场预约需要取号。 自助挂号机挂号的预约不需要挂号
    pay_sql, pay_no = '', ''
    if appt_type in (1, 2):
        doctorinfo = redis_client.hget(APPT_DOCTORS_KEY, str(json_data.get('doc_id')))
        if doctorinfo:
            doctorinfo = json.loads(doctorinfo)

            if doctorinfo.get('his_status') == 0:
                raise Exception('当前医生今天在 his 中没有挂号权限, 无法签到')

            sign_in_ret = ''
            try:
                # paymethod: 1 微信 2 支付宝
                param = {"type": "his_visit_reg", "paymethod": 1, "day": record.get('book_date'),
                         "patient_id": patient_id, "AsRowid": str(doctorinfo.get('appointment_id')),
                         "PayAmt": float(doctorinfo.get('fee')), "orderid": record.get('orderid')}
                sign_in_ret = call_third_systems_obtain_data('his_socket', 'his_visit_reg', param)
                if not sign_in_ret or int(sign_in_ret.get('ResultCode')) != 0:
                    raise Exception('在 his 中取号失败， 签到接口返回数据, ', sign_in_ret)
            except Exception:
                raise Exception('在 his 中取号失败， 签到接口返回数据, ', sign_in_ret)
            # 挂号成功更新 pay_no
            pay_no = sign_in_ret.get('RegisterNo')
            redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, pay_no)
            pay_sql = ", pay_no = \'{}\' ".format(pay_no)
        else:
            raise Exception('获取医生信息失败， 签到失败, doc_id = ', str(json_data.get('doc_id')))

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
    update_sql = f'UPDATE nsyy_gyl.appt_record SET {op_sql}{change_proj_sql}{pay_sql} WHERE id = {appt_id} '
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


def if_the_current_time_period_is_available(period):
    """
    获取当前时间段 （上午/下午）
    :param period:
    :return:
    """
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


def call(json_data):
    """
    呼叫 （通过 socket 实现）
    :param json_data:
    :return:
    """
    try:
        socket_id = json_data.get('socket_id')
        room = ' '.join(list(json_data.get('proj_room')))
        socket_data = {"msg": '请患者 {} 到 {} 诊室就诊'.format(json_data.get('name'), room), "type": 200}
        data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    except Exception as e:
        print(datetime.now(), 'Call Exception: ', e.__str__())


def next_num(id, is_group):
    """
    叫号下一个
    :param id:
    :param is_group:
    :return:
    """
    data_list, doctor, project = query_wait_list({'type': 1, 'wait_id': id})

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
            'socket_id': 'd' + str(is_group) if is_group != -1 else 'z' + str(id),
            'name': data_list[0].get('wait_list')[0].get('patient_name'),
            'proj_room': data_list[0].get('wait_list')[0].get('room')
        }
        call(json_data)
        data_list[0].get('wait_list')[0]['state'] = appt_config.APPT_STATE['processing']

    return data_list


def query_all_appt_project(type: int, target_pid: int, only_today: bool = False):
    """
    微信小程序查询项目信息分为两个接口（数据量大，分为两个）
    1. 仅返回项目列表
    2. 选择某一个项目，查询该项目的可预约时间段
    查询所有预约项目（优化版）
    """
    # 预计算公共参数
    redis_client = redis.Redis(connection_pool=pool)
    current_date = datetime.now().date()
    today_str = str(current_date)
    current_hour = datetime.now().hour
    current_slot = appt_config.appt_slot_dict[current_hour]

    # 1. 批量获取并预处理项目数据
    proj_raw = redis_client.hvals(APPT_PROJECTS_KEY)
    proj_list = [json.loads(p) for p in proj_raw if int(json.loads(p).get('proj_type', 0)) == int(type)]

    if not target_pid:
        result = []
        for proj in proj_list:
            result.append({**proj})
        return result

    # 2. 批量获取剩余数量数据
    project_ids = [str(p['id']) for p in proj_list]
    remaining_data = redis_client.hmget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, project_ids)
    remaining_map = {pid: json.loads(data) for pid, data in zip(project_ids, remaining_data) if data}

    # 3. 预加载医生数据
    all_doctor_ids = set()
    for data in remaining_map.values():
        for date_slots in data.values():
            for slot_info in date_slots.values():
                for rid_info in slot_info.values():
                    if 'doc_id' in rid_info and rid_info['doc_id']:
                        all_doctor_ids.add(str(rid_info['doc_id']))
    if all_doctor_ids:
        doctors = redis_client.hmget(APPT_DOCTORS_KEY, list(all_doctor_ids))
        doctor_map = {did: json.loads(d) for did, d in zip(all_doctor_ids, doctors) if d}

    # 4. 并行处理每个项目
    result = []
    for proj in proj_list:
        pid = str(proj['id'])
        if str(target_pid) != pid:
            continue
        bookable_data = remaining_map.get(pid, {})

        # 5. 使用生成器处理时间段
        def process_slots():
            for date_key, slots in bookable_data.items():
                # 只返回当天的数据
                if date_key != today_str and only_today:
                    continue
                for period, rooms in slots.items():
                    # 时间有效性检查
                    if date_key == today_str and not if_the_current_time_period_is_available(period):
                        continue

                    # 处理房间数据
                    valid_rooms = []
                    for rid, rinfo in rooms.items():
                        # 房间有效性检查
                        room_quantity = room_dict.get(str(rid), {}).get(date_key, {}).get(str(period), {})
                        if not room_quantity:
                            continue
                        if int(rinfo.get('proj_type')) == 1 and int(rinfo.get('doc_id')) == 0:
                            continue

                        # 计算剩余数量
                        total = sum(int(v) for k, v in room_quantity.items() if int(k) >= current_slot)
                        if 'doc_id' in rinfo:
                            rinfo['doctor'] = doctor_map.get(str(rinfo['doc_id']))

                        # 转换字典
                        # {'5': 3, '6': 3}
                        # 改为
                        # {'5': {"name": "8:00-9:00", "count": 3}, '6': {"name": "9:00-10:00", "count": 3}}
                        transformed_dict = {
                            k: {
                                "name": appt_config.APPT_PERIOD_INFO[int(k)],
                                "count": v
                            }
                            for k, v in room_quantity.items()
                        }
                        yield {
                            'date': date_key,
                            'period': period,
                            'rid': rid,
                            'quantity': total,
                            'detail': {**rinfo, 'hourly_quantity': transformed_dict}
                        }

        # 6. 分组处理优化
        sorted_slots = sorted(process_slots(), key=lambda x: (x['date'], x['period']))
        grouped_data = []
        for key, group in groupby(sorted_slots, key=lambda x: (x['date'], x['period'])):
            date_period, period = key
            group_list = list(group)
            group_list[0].pop('date')
            group_list[0].pop('period')
            grouped_data.append({
                "date": date_period,
                "period": int(period),
                "list": [{
                    "date": date_period,
                    "period": int(period),
                    'rid': item['rid'],
                    'quantity': item['quantity'],
                    **item['detail']
                } for item in group_list]
            })

        # 7. 构建最终结果
        result.append({
            **proj,
            'bookable_list': grouped_data,
        })

    # 创建新列表，只保留非空的 bookable_list
    filtered_data = []
    for item in result:
        all_empty = all(len(bookable["list"]) == 0 for bookable in item["bookable_list"])
        if not all_empty:
            filtered_data.append(item)

    return filtered_data


# def query_all_appt_project(type: int, only_today: bool = False):
#     """
#     查询所有预约项目（优化版）
#     """
#     # 预计算公共参数
#     redis_client = redis.Redis(connection_pool=pool)
#     current_date = datetime.now().date()
#     today_str = str(current_date)
#     current_hour = datetime.now().hour
#     current_slot = appt_config.appt_slot_dict[current_hour]
#
#     # 1. 批量获取并预处理项目数据
#     proj_raw = redis_client.hvals(APPT_PROJECTS_KEY)
#     proj_list = [json.loads(p) for p in proj_raw if int(json.loads(p).get('proj_type', 0)) == int(type)]
#
#     # 2. 批量获取剩余数量数据
#     project_ids = [str(p['id']) for p in proj_list]
#     remaining_data = redis_client.hmget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, project_ids)
#     remaining_map = {pid: json.loads(data) for pid, data in zip(project_ids, remaining_data) if data}
#
#     # 3. 预加载医生数据
#     all_doctor_ids = set()
#     for data in remaining_map.values():
#         for date_slots in data.values():
#             for slot_info in date_slots.values():
#                 for rid_info in slot_info.values():
#                     if 'doc_id' in rid_info and rid_info['doc_id']:
#                         all_doctor_ids.add(str(rid_info['doc_id']))
#     if all_doctor_ids:
#         doctors = redis_client.hmget(APPT_DOCTORS_KEY, list(all_doctor_ids))
#         doctor_map = {did: json.loads(d) for did, d in zip(all_doctor_ids, doctors) if d}
#
#     # 4. 并行处理每个项目
#     result = []
#     for proj in proj_list:
#         pid = str(proj['id'])
#         bookable_data = remaining_map.get(pid, {})
#
#         # 5. 使用生成器处理时间段
#         def process_slots():
#             for date_key, slots in bookable_data.items():
#                 # 只返回当天的数据
#                 if date_key != today_str and only_today:
#                     continue
#                 for period, rooms in slots.items():
#                     # 时间有效性检查
#                     if date_key == today_str and not if_the_current_time_period_is_available(period):
#                         continue
#
#                     # 处理房间数据
#                     valid_rooms = []
#                     for rid, rinfo in rooms.items():
#                         # 房间有效性检查
#                         room_quantity = room_dict.get(str(rid), {}).get(date_key, {}).get(str(period), {})
#                         if not room_quantity:
#                             continue
#
#                         # 计算剩余数量
#                         total = sum(int(v) for k, v in room_quantity.items() if int(k) >= current_slot)
#                         if 'doc_id' in rinfo:
#                             rinfo['doctor'] = doctor_map.get(str(rinfo['doc_id']))
#
#                         # 转换字典
#                         # {'5': 3, '6': 3}
#                         # 改为
#                         # {'5': {"name": "8:00-9:00", "count": 3}, '6': {"name": "9:00-10:00", "count": 3}}
#                         transformed_dict = {
#                             k: {
#                                 "name": appt_config.APPT_PERIOD_INFO[int(k)],
#                                 "count": v
#                             }
#                             for k, v in room_quantity.items()
#                         }
#                         yield {
#                             'date': date_key,
#                             'period': period,
#                             'rid': rid,
#                             'quantity': total,
#                             'detail': {**rinfo, 'hourly_quantity': transformed_dict}
#                         }
#
#         # 6. 分组处理优化
#         sorted_slots = sorted(process_slots(), key=lambda x: (x['date'], x['period']))
#         grouped_data = []
#         for key, group in groupby(sorted_slots, key=lambda x: (x['date'], x['period'])):
#             date_period, period = key
#             group_list = list(group)
#             group_list[0].pop('date')
#             group_list[0].pop('period')
#             grouped_data.append({
#                 "date": date_period,
#                 "period": int(period),
#                 "list": [{
#                     "date": date_period,
#                     "period": int(period),
#                     'rid': item['rid'],
#                     'quantity': item['quantity'],
#                     **item['detail']
#                 } for item in group_list]
#             })
#
#         # 7. 构建最终结果
#         result.append({
#             **proj,
#             'bookable_list': grouped_data,
#         })
#
#     # 创建新列表，只保留非空的 bookable_list
#     filtered_data = []
#     for item in result:
#         all_empty = all(len(bookable["list"]) == 0 for bookable in item["bookable_list"])
#         if not all_empty:
#             filtered_data.append(item)
#
#     return filtered_data


def query_proj_info(type: int):
    """
    查询科室信息 & 科室医生列表
    :param type:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    projl = redis_client.hvals(APPT_PROJECTS_KEY)
    projl = [json.loads(proj) for proj in projl]

    today_str = str(datetime.now().date())
    data = []
    for proj in projl:
        if int(proj.get('proj_type')) != int(type):
            continue
        proj['proj_doctors'] = query_docs_in_the_same_project(proj.get('id'))
        data.append(proj)

    return data


def query_docs_in_the_same_project(pid):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""
        select * from nsyy_gyl.appt_doctor where id in 
        (select did from nsyy_gyl.appt_schedules where pid = {int(pid)} group by did order by did)
        and his_status = 1
    """
    docs = db.query_all(query_sql)
    del db
    return docs


def query_room_list(type: int):
    """
    查询大厅列表/ 诊室列表
    type=1 诊室
    type=2 大厅
    :param type:
    :return:
    """
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


def query_wait_list(json_data):
    """
    查询大厅/诊室等待列表
    type=1 诊室 wait_id 是 rid 房间号
    type=2 大厅 wiat_id 是 pid 项目id
    :param json_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    redis_client = redis.Redis(connection_pool=pool)

    wait_id = int(json_data.get('wait_id'))
    type = int(json_data.get('type'))

    doctor = ''
    proj = ''
    if type == 1:
        period = 1 if datetime.now().hour < 12 else 2
        query_sql = f"""select s.* from nsyy_gyl.appt_schedules s left join nsyy_gyl.appt_schedules_doctor ds 
                        on ds.did = s.did and ds.shift_date = s.shift_date and ds.shift_type = s.shift_type 
                        where s.rid = {int(wait_id)} and s.shift_date = '{datetime.now().date()}' 
                        and s.shift_type = {period} and (ds.status = 1 or s.did = 0)"""
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
    query_sql = f'select * from nsyy_gyl.appt_record ' \
                f'where state in {wait_state} and book_date = \'{str(date.today())}\' {condition_sql} '
    recordl = db.query_all(query_sql)
    recordl = sorted(recordl,
                     key=lambda x: (-x['state'], x['sort_num'], -x['level'], x['book_period'], x['sign_in_num']))

    # 查询医嘱
    if recordl:
        appt_id_list = [record.get('id') for record in recordl]
        ids = ', '.join(map(str, appt_id_list))
        query_sql = f'select * from nsyy_gyl.appt_doctor_advice where appt_id in ({ids}) '
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


def update_doctor_advice_pay_state(idl):
    """
    更新医嘱付款状态
    :param idl:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f'update nsyy_gyl.appt_doctor_advice set state = 1 where id in ({", ".join(map(str, idl))})'
    db.execute(update_sql, need_commit=True)
    del db


def query_advice_by_father_appt_id(json_data):
    """
    查询医嘱
    :param json_data:
    :return:
    """
    father_appt_id = json_data.get('father_appt_id')
    patient_id = json_data.get('patient_id')

    conditions = []
    if father_appt_id:
        conditions.append(f"father_id = {int(father_appt_id)}")

    if patient_id:
        # 如果需要只查询当天数据，可以在这里加上过滤
        conditions.append(f"type >= 4 and patient_id = {int(patient_id)}")

    if not conditions:
        return []  # 如果没有条件，返回空列表

    condition_sql = " AND ".join(conditions)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = f"select * from nsyy_gyl.appt_record where {condition_sql}"
    appts = db.query_all(query_sql)

    for record in appts:
        appt_id = int(record.get('id'))
        record['time_slot'] = appt_config.APPT_PERIOD_INFO.get(int(record['time_slot']))
        query_sql = f'select * from nsyy_gyl.appt_doctor_advice where appt_id = {appt_id}'
        record['doctor_advice'] = db.query_all(query_sql)
    del db
    return appts


def update_doc(json_data):
    """
    更新医生信息
    :param json_data:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = ' name = \'{}\' '.format(json_data.get('name')) if json_data.get('name') else ''
    condition_sql += ', no = {} '.format(json_data.get('no')) if json_data.get('no') else ''
    condition_sql += ', dept_id = {} '.format(json_data.get('dept_id')) if json_data.get('dept_id') else ''
    condition_sql += ', dept_name = \'{}\' '.format(json_data.get('dept_name')) if json_data.get('dept_name') else ''
    condition_sql += ', career = \'{}\' '.format(json_data.get('career')) if json_data.get('career') else ''
    condition_sql += ', fee = {} '.format(json_data.get('fee')) if json_data.get('fee') else ''
    condition_sql += ", appointment_id = '{}' ".format(json_data.get('appointment_id')) if json_data.get(
        'appointment_id') else ''
    condition_sql += ', photo = \'{}\' '.format(json_data.get('photo')) if json_data.get('photo') else ''
    condition_sql += ', `desc` = \'{}\' '.format(json_data.get('desc')) if json_data.get('desc') else ''
    condition_sql += ', phone = \'{}\' '.format(json_data.get('phone')) if json_data.get('phone') else ''
    condition_sql += ', good_at = \'{}\' '.format(json_data.get('good_at')) if json_data.get('good_at') else ''

    id = int(json_data.get('id'))
    update_sql = f'UPDATE nsyy_gyl.appt_doctor SET {condition_sql} WHERE id = {id}'
    db.execute(update_sql, need_commit=True)

    doc_info = db.query_one(f'select * from nsyy_gyl.appt_doctor WHERE id = {id}')
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


def change_room(json_data):
    """
    检查项目切换房间
    :param json_data:
    :return:
    """
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
        update_sql = f"""UPDATE nsyy_gyl.appt_record SET {state_sql} rid = {change_to_rid}, room = '{change_to_room}', 
                         book_period = {current_period}, time_slot = {current_slot}, 
                         sort_num = {appt_config.default_sort_num} WHERE id IN ({','.join(change_id_list)})"""
        db.execute(update_sql, need_commit=True)
    except Exception as e:
        raise Exception(f"数据库操作失败: {e}") from e
    finally:
        del db  # 使用close()确保连接关闭

    room_dict[change_to_rid][today_str][str(current_period)][str(current_slot)] -= len(change_id_list)


def update_wait_list_sort(json_data):
    """
    更新等待列表顺序
    :param json_data:
    :return:
    """
    recordl = json_data.get('recordl')
    # 生成批量更新SQL语句
    update_sql = f"UPDATE nsyy_gyl.appt_record SET sort_num = CASE id "
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


def update_sort_info(appt_id, sort_info):
    """
    更新调整顺序的原因
    :param appt_id:
    :param sort_info:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(f"UPDATE nsyy_gyl.appt_record SET sort_info = '{sort_info}' WHERE id = {int(appt_id)} ",
               need_commit=True)
    del db


def update_wait_num(rid, pid):
    """
    更新等待人数 （以下几种时机触发）
    1. 新建预约时 自主查询前方等待人数更新
    2. 取消预约 / 完成预约
    3. 过号时
    4. 调整等待列表顺序时
    5. 签到后
    :param rid:
    :param pid:
    :return:
    """

    # 1. 未签到的等待人数为 （等待中 处理中 过号） 的所有数量
    # 2. 已签到的等待任务数为 所在当前房间等待列表中的位置
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 查询当前项目 当天所有未完成 未取消的记录
    query_sql = 'select * from nsyy_gyl.appt_record where pid = {} and book_date = \'{}\' and state < {} '. \
        format(int(pid), str(date.today()), appt_config.APPT_STATE['completed'])
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
        db.execute(f"""UPDATE nsyy_gyl.appt_record SET wait_num = {pid_wait_num} 
                         WHERE id IN ({','.join(map(str, unsign_idl))}) """, need_commit=True)

    # 更新等待列表中的记录的 前方等待人数
    if rid_wait_record:
        rid_wait_record = sorted(rid_wait_record, key=lambda x: (-x['state'], x['sort_num'], -x['level'],
                                                                 x['book_period'], x['sign_in_num']))
        # 生成批量更新SQL语句
        update_sql = f"UPDATE nsyy_gyl.appt_record SET wait_num = CASE id "
        ids = []
        index = 0
        for record in rid_wait_record:
            update_sql += f"WHEN {record['id']} THEN {index} "
            ids.append(record['id'])
            index = index + 1
        update_sql += "END WHERE id IN (%s)" % ','.join(map(str, ids))
        db.execute(update_sql, need_commit=True)
    del db


def update_or_insert_project(json_data):
    """
    新增或更新预约项目
    :param json_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    proj = None
    rid_list = []
    try:
        pid = json_data.get('pid')
        if pid:  # 如果存在pid，则更新
            proj_name = json_data.get('proj_name')
            if not proj_name:
                raise Exception("项目名称不能为空")
            update_sql = f"UPDATE nsyy_gyl.appt_project SET proj_name = '{proj_name}' where id = {pid} "
            db.execute(update_sql, need_commit=True)
        else:
            proj_type = json_data.get('proj_type')
            proj_name = json_data.get('proj_name')
            nsnum = json_data.get('nsnum')
            if not proj_name or not nsnum or not proj_type:
                raise Exception("新增项目，项目名称或项目容量不能为空")

            pid = db.execute(f"""INSERT INTO nsyy_gyl.appt_project (proj_type, proj_name, nsnum) 
                             VALUES ({proj_type}, '{proj_name}', {nsnum})""", need_commit=True)
            if pid == -1:
                raise Exception("新增项目失败! ", json_data)

        rids = db.query_all(f"""select rid from nsyy_gyl.appt_schedules where pid = {pid} 
                                  and shift_date = '{datetime.now().date()}'""")
        rid_list = [rid.get('rid') for rid in rids]
        proj = db.query_one(f"select * from nsyy_gyl.appt_project where id = {int(pid)} ")
    except Exception as e:
        raise Exception("项目更新/新增失败: ", e)
    finally:
        del db

    # 更新缓存
    redis_client = redis.Redis(connection_pool=pool)
    redis_client.hset(APPT_PROJECTS_KEY, str(proj['id']), json.dumps(proj, default=str))
    # socket 通知诊室更新
    socket_id = 'd' + str(pid)
    push_patient('', socket_id)
    for rid in rid_list:
        socket_id = 'z' + str(rid)
        push_patient('', socket_id)


def load_data_into_cache():
    """
    加载诊室/项目/医生信息到内存
    :return:
    """
    start_time = time.time()
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 使用 Pipeline 批量操作
    with redis_client.pipeline() as pipe:
        # 缓存项目信息
        pipe.delete(APPT_PROJECTS_KEY, APPT_EXECUTION_DEPT_INFO_KEY)
        projs = db.query_all(f'SELECT * FROM nsyy_gyl.appt_project')
        for proj in projs:
            pipe.hset(APPT_PROJECTS_KEY, str(proj['id']), json.dumps(proj, default=str))
            if proj.get('dept_id'):
                pipe.hset(APPT_EXECUTION_DEPT_INFO_KEY, str(proj['dept_id']), json.dumps(proj, default=str))

        # 缓存医生信息（使用内存字典合并同名医生）
        pipe.delete(APPT_DOCTORS_KEY, APPT_DOCTORS_BY_NAME_KEY)
        doctors = db.query_all(f'SELECT * FROM nsyy_gyl.appt_doctor')
        name_dict = defaultdict(list)
        for doc in doctors:
            pipe.hset(APPT_DOCTORS_KEY, str(doc['id']), json.dumps(doc, default=str))
            name_dict[doc['his_name']].append(doc)
        for name, docs in name_dict.items():
            pipe.hset(APPT_DOCTORS_BY_NAME_KEY, name, json.dumps(docs, default=str))

        # 缓存房间信息
        pipe.delete(APPT_ROOMS_KEY)
        rooms = db.query_all(f'SELECT * FROM nsyy_gyl.appt_room')
        room_groups = defaultdict(list)
        for room in rooms:
            pipe.hset(APPT_ROOMS_KEY, str(room['id']), json.dumps(room, default=str))
            room_groups[room['group_id']].append(room)
        for group_id, group_rooms in room_groups.items():
            pipe.hset(APPT_ROOMS_BY_PROJ_KEY, str(group_id), json.dumps(group_rooms[0], default=str))

        # 执行所有管道命令
        pipe.execute()

    # 加载当天自助挂号记录（使用 SSCAN/SADD 优化大数据量场景）
    redis_client.delete(APPT_DAILY_AUTO_REG_RECORD_KEY)
    pay_nos = db.query_all(f'SELECT DISTINCT pay_no FROM nsyy_gyl.appt_record '
                           f'WHERE book_date = CURDATE() AND pay_no IS NOT NULL AND type = 3')
    if pay_nos:
        redis_client.sadd(APPT_DAILY_AUTO_REG_RECORD_KEY, *[n['pay_no'] for n in pay_nos])

    del db
    print(datetime.now(), "综合预约静态数据加载完成, 耗时：", time.time() - start_time, 's')


def cache_proj_7day_schedule(proj, all_schedule=None):
    """
    每日执行
    1. 作废过期的预约
    2. 缓存当日的签到号码
    3. 缓存近七天的可预约项目数据
    :param all_schedule:
    :param proj:
    :return:
    """
    pid = int(proj.get('id'))
    redis_client = redis.Redis(connection_pool=pool)
    if not all_schedule:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        today = datetime.now().date()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=6)).strftime('%Y-%m-%d')
        # all_schedule = db.query_all(f'''SELECT s.* FROM nsyy_gyl.appt_schedules s JOIN nsyy_gyl.appt_doctor d
        #                                 ON s.did = d.id WHERE s.shift_date between '{start_date}' and '{end_date}'
        #                                 AND s.status = 1 AND s.pid = {pid} AND d.his_status = 1''')
        all_schedule = db.query_all(f"""select t.did, t.rid, t.pid, t.shift_date, t.shift_type, 
                                        case when t.status is null THEN 3 else t.status end as status from (
                                        select s.did, s.rid, s.pid, s.shift_date, s.shift_type, ds.status 
                                        from nsyy_gyl.appt_schedules s left join nsyy_gyl.appt_schedules_doctor ds 
                                        on s.did = ds.did and s.shift_date = ds.shift_date and s.shift_type = ds.shift_type 
                                        WHERE s.shift_date between '{start_date}' and '{end_date}' 
                                        and s.pid = {pid} and (ds.status = 1 or s.did = 0)) t""")
        del db

    # 近 7 天的可预约数量
    today = datetime.now().date()
    seven_day_data = {}
    for day_offset in range(7):
        target_date = today + timedelta(days=day_offset)
        am_schedule, pm_schedule = {}, {}
        for item in filter(lambda x: x['shift_date'] == target_date and x['pid'] == pid, all_schedule):
            data = redis_client.hget(APPT_ROOMS_KEY, str(item.get('rid'))) or "{}"
            room = json.loads(data)
            if not room:
                continue
            time_slot = am_schedule if item['shift_type'] == 1 else pm_schedule
            if int(proj.get('proj_type')) == 1:  # 门诊项目
                doc_info = redis_client.hget(APPT_DOCTORS_KEY, str(item.get('did')))
                doctor = json.loads(doc_info) if doc_info else {'fee': 0}
                time_slot[item['rid']] = {
                    'doc_id': item['did'],
                    'doctor': doctor,
                    'price': float(doctor.get('fee', 0)),
                    'room': room,
                    'rid': item.get('rid'),
                    'proj_name': proj.get('proj_name'),
                    'proj_type': proj.get('proj_type'),
                    'proj_id': proj.get('id')
                }
            else:  # 院内项目
                time_slot[item['rid']] = {
                    'room': room,
                    'rid': item.get('rid'),
                    'proj_name': proj.get('proj_name'),
                    'proj_type': proj.get('proj_type'),
                    'proj_id': proj.get('id')
                }
        seven_day_data[str(target_date)] = {'1': am_schedule, '2': pm_schedule}

    if seven_day_data:
        redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid),
                          json.dumps(seven_day_data, default=str))


def run_everyday():
    try:
        start_time = time.time()
        # 自动复制排班
        auto_copy_schedule()
        # 第一阶段：加载静态数据
        load_data_into_cache()
        # 第二阶段：处理动态数据
        redis_client = redis.Redis(connection_pool=pool)
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)

        # 取消今天之前未完成的预约，小程序取消预约涉及到退款，由用户自己取消
        all_cancel_type = (appt_config.APPT_TYPE['offline'], appt_config.APPT_TYPE['auto_appt'],
                           appt_config.APPT_TYPE['advice_appt'])
        update_sql = f"""UPDATE nsyy_gyl.appt_record SET state = {appt_config.APPT_STATE['canceled']}, 
                        cancel_time = NOW() WHERE book_date < CURDATE() 
                        AND state < {appt_config.APPT_STATE['completed']} AND type IN {tuple(all_cancel_type)}"""
        db.execute(update_sql, need_commit=True)

        # 使用覆盖索引优化签到计数查询
        state_cond = (appt_config.APPT_STATE['in_queue'], appt_config.APPT_STATE['processing'],
                      appt_config.APPT_STATE['over_num'])
        signin_sql = f'''SELECT pid, MAX(sign_in_num) as num 
                        FROM nsyy_gyl.appt_record WHERE book_date = CURDATE() 
                          AND state IN {tuple(state_cond)} GROUP BY pid'''
        records = db.query_all(signin_sql)
        redis_client.delete(APPT_SIGN_IN_NUM_KEY)
        for record in records:
            if record.get('num'):
                sign_in_num = int(record.get('num'))
                old_num = redis_client.hget(APPT_SIGN_IN_NUM_KEY, str(record['pid'])) or 0
                if int(old_num) < sign_in_num:
                    redis_client.hset(APPT_SIGN_IN_NUM_KEY, str(record['pid']), sign_in_num)

        today = datetime.now().date()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=6)).strftime('%Y-%m-%d')
        # all_schedule = db.query_all(f'''SELECT s.* FROM nsyy_gyl.appt_schedules s JOIN nsyy_gyl.appt_doctor d
        #                                 ON s.did = d.id WHERE s.shift_date between '{start_date}' and '{end_date}'
        #                                 AND s.status = 1 AND d.his_status = 1''')
        all_schedule = db.query_all(f"""select t.did, t.rid, t.pid, t.shift_date, t.shift_type, 
                                        case when t.status is null THEN 3 else t.status end as status from (
                                        select s.did, s.rid, s.pid, s.shift_date, s.shift_type, ds.status 
                                        from nsyy_gyl.appt_schedules s left join nsyy_gyl.appt_schedules_doctor ds 
                                        on s.did = ds.did and s.shift_date = ds.shift_date and s.shift_type = ds.shift_type 
                                        WHERE s.shift_date between '{start_date}' and '{end_date}' and (ds.status = 1 or s.did = 0)) t""")
        del db

        # 并行处理项目缓存（需考虑Redis线程安全）
        redis_client.delete(APPT_REMAINING_RESERVATION_QUANTITY_KEY)
        proj_map = redis_client.hgetall(APPT_PROJECTS_KEY)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for pid, proj_str in proj_map.items():
                proj = json.loads(proj_str)
                futures.append(executor.submit(
                    cache_proj_7day_schedule,
                    proj,
                    [s for s in all_schedule if s['pid'] == int(pid)]
                ))
            for f in futures:
                f.result()

        print(datetime.now(), "综合预约所有数据缓存完成, 耗时：", time.time() - start_time, 's')
    except Exception as e:
        print(f"定时任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


def auto_copy_schedule():
    # 下一周的周一
    today = datetime.today()
    next_week_start = today + timedelta(days=(7 - today.weekday()))

    # 本周的周一
    days_since_monday = today.weekday()
    cur_week_start = today - timedelta(days=days_since_monday)
    cur_week_start = cur_week_start.date()

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)

    query_sql = f"select count(*) from nsyy_gyl.appt_schedules_doctor " \
                f"where shift_date >= '{next_week_start.strftime('%Y-%m-%d')}'"
    if db.query_one(query_sql).get('count(*)') == 0:
        try:
            sched_manage.copy_schedule(cur_week_start.strftime('%Y-%m-%d'), next_week_start.strftime('%Y-%m-%d'), None, None, None, 'doctor')
        except Exception as e:
            print(f"自动复制排班记录失败: {str(e)}")

    query_sql = f"select count(*) from nsyy_gyl.appt_schedules where shift_date >= '{next_week_start.strftime('%Y-%m-%d')}'"
    if db.query_one(query_sql).get('count(*)') == 0:
        try:
            sched_manage.copy_schedule(cur_week_start.strftime('%Y-%m-%d'), next_week_start.strftime('%Y-%m-%d'), None, None, None, 'room')
        except Exception as e:
            print(f"自动复制排班记录失败: {str(e)}")

    del db


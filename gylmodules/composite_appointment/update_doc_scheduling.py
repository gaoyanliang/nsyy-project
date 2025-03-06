import json
import re
from datetime import datetime, timedelta
from itertools import groupby

import redis
import requests

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.composite_appointment.appt_config import APPT_DOCTORS_BY_NAME_KEY, APPT_ROOMS_KEY, APPT_PROJECTS_KEY, \
    APPT_DOCTORS_KEY, APPT_REMAINING_RESERVATION_QUANTITY_KEY
from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)


def call_third_systems_obtain_data(param: dict):
    data = []
    url = f"http://127.0.0.1:6080/his_socket"
    if global_config.run_in_local:
        # url = f"http://192.168.3.12:6080/his_socket"
        url = f"http://192.168.124.53:6080/his_socket"

    try:
        # 发送 POST 请求，将字符串数据传递给 data 参数
        response = requests.post(url, timeout=30, json=param)
        data = response.text
        data = json.loads(data)
        data = data.get('List').get('Item')
    except Exception as e:
        print(datetime.now(), '调用第三方系统方法失败： param = ' + str(param) + "   " + e.__str__())

    return data


"""
每日凌晨更新当天的坐班医生信息
"""


def update_today_doc_info():
    doc_list = call_third_systems_obtain_data(
        {
            "type": "his_mz_source_check",
            "day": datetime.now().strftime("%Y-%m-%d"),
            "start": 0
        }
    )

    if not doc_list:
        print(datetime.now(), '当天坐班医生查询失败')
        return

    # 数据预处理（过滤 + 字段映射）
    processed_data = [
        {
            '医生ID': d['MarkId'], '医生姓名': d['MarkDesc'], '号码': d['AsRowid'], '挂号级别': d['SessionType'],
            '现价': d['Price'], '真实姓名': re.sub(r'[a-zA-Z0-9]', '', d['MarkDesc']),
            '科室ID': d['DepID'], '部门名称': d['DepName'], 'visit_id': d['VisitID'], "FartherDepID": d['FartherDepID'],
            "FartherDepName": d['FartherDepName'], "Sex": d['Sex'], "UCount": d['UCount'],
            "shouFeiXmMc": d['shouFeiXmMc']
        }
        for d in doc_list
        if d.get('MarkDesc') and d.get('MarkId')
    ]
    # 核心处理逻辑
    latest_records = {}
    for record in processed_data:
        # 使用复合键（医生ID + 科室ID）作为唯一标识
        composite_key = (int(record['医生ID']), int(record['科室ID']))

        # 获取已存在的记录（如果有）
        existing = latest_records.get(composite_key)
        if not existing or (existing['挂号级别'] != record['挂号级别']
                            and record['现价'] > existing['现价']):
            latest_records[composite_key] = record

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc_in_db_list = db.query_all("select * from nsyy_gyl.appt_doctor")
    doc_in_db_dict = {}
    doc_in_db_sorted = sorted(doc_in_db_list, key=lambda x: (x["no"], x["dept_id"]))
    for key, group in groupby(doc_in_db_sorted, key=lambda x: (x["no"], x["dept_id"])):
        doc_in_db_dict[key] = list(group)

    his_status_set = set()
    for key, new_doc in latest_records.items():
        doc_in_db = doc_in_db_dict.get(key)
        if not doc_in_db:
            # print(datetime.now(), f"医生 {key} 在数据库中不存在，新增医生信息", new_doc)
            insert_sql = f"""
                    insert into nsyy_gyl.appt_doctor(name, his_name, no, career, fee, appointment_id, 
                    dept_id, dept_name, update_time, visit_id, his_status, farther_dept_id, farther_dept_name, 
                    sex, u_count, shoufei_xm) values ('{new_doc.get('真实姓名')}', 
                    '{new_doc.get('医生姓名')}', {new_doc.get('医生ID')}, '{new_doc.get('挂号级别')}', 
                    '{new_doc.get('现价')}', '{new_doc.get('号码')}', {new_doc.get('科室ID')}, 
                    '{new_doc.get('部门名称')}', '{update_time}', '{new_doc.get('visit_id')}', 1, 
                    {new_doc.get('FartherDepID')}, '{new_doc.get('FartherDepName')}', '{new_doc.get('Sex')}',
                     {new_doc.get('UCount')}, '{new_doc.get('shouFeiXmMc')}')
                    """
            row_no = db.execute(insert_sql, need_commit=True)
            if row_no == -1:
                print("医生入库失败! sql = " + insert_sql)
                continue
            his_status_set.add(row_no)

            doc = {'id': row_no, 'dept_id': int(new_doc.get('科室ID')), 'dept_name': new_doc.get('部门名称'),
                   'no': new_doc.get('医生ID'), 'name': new_doc.get('真实姓名'), 'his_name': new_doc.get('医生姓名'),
                   'career': new_doc.get('挂号级别'), 'fee': new_doc.get('现价'), 'appointment_id': new_doc.get('号码'),
                   'visit_id': new_doc.get('visit_id'), 'farther_dept_id': new_doc.get('FartherDepID'),
                   'farther_dept_name': new_doc.get('FartherDepName'), 'sex': new_doc.get('Sex'),
                   'u_count': new_doc.get('UCount'), 'shoufei_xm': new_doc.get('shouFeiXmMc')}
            redis_client.hset(APPT_DOCTORS_KEY, str(doc.get('id')), json.dumps(doc, default=str))
            query_sql = f""" select * from nsyy_gyl.appt_doctor where his_name = '{doc.get('his_name')}' """
            docs = db.query_all(query_sql)
            # 新增的数据中，新增的医生编号，如果没有编号，则从人员表获取
            db.execute("UPDATE nsyy_gyl.appt_doctor ad JOIN nsyy_gyl.人员表 e ON ad.no = e.ID "
                       "SET ad.emp_nub = e.编号 where ad.emp_nub is null")
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, doc.get('his_name'), json.dumps(docs, default=str))
            continue

        his_status_set.add(doc_in_db[0].get('id'))
        if new_doc.get('号码') != doc_in_db[0].get('appointment_id') or \
                int(new_doc.get('科室ID')) != int(doc_in_db[0].get('dept_id')) or \
                new_doc.get('部门名称') != doc_in_db[0].get('dept_name') or \
                new_doc.get('真实姓名') != doc_in_db[0].get('name') or \
                new_doc.get('医生姓名') != doc_in_db[0].get('his_name') or \
                new_doc.get('visit_id') != doc_in_db[0].get('visit_id') or \
                new_doc.get('FartherDepID') != doc_in_db[0].get('farther_dept_id') or \
                new_doc.get('UCount') != doc_in_db[0].get('u_count') or \
                new_doc.get('shouFeiXmMc') != doc_in_db[0].get('shoufei_xm') or \
                int(new_doc.get('医生ID')) != int(doc_in_db[0].get('no')) or \
                float(new_doc.get('现价')) != float(doc_in_db[0].get('fee')):
            update_sql = f"""
                        update nsyy_gyl.appt_doctor set
                          dept_id = {new_doc.get('科室ID')}, dept_name = '{new_doc.get('部门名称')}',
                          no = {new_doc.get('医生ID')}, name = '{new_doc.get('真实姓名')}', 
                          his_name = '{new_doc.get('医生姓名')}', career = '{new_doc.get('挂号级别')}', 
                          fee = '{new_doc.get('现价')}', update_time = '{update_time}',
                          appointment_id = '{new_doc.get('号码')}', visit_id = '{new_doc.get('visit_id')}', 
                          farther_dept_id = {new_doc.get('FartherDepID')}, sex = '{new_doc.get('Sex')}',
                          farther_dept_name = '{new_doc.get('FartherDepName')}', u_count = {new_doc.get('UCount')},
                          shoufei_xm = '{new_doc.get('shouFeiXmMc')}' where id = {doc_in_db[0].get('id')}
                        """
            db.execute(update_sql, need_commit=True)

            doc = doc_in_db[0]
            doc['dept_id'] = int(new_doc.get('科室ID'))
            doc['dept_name'] = new_doc.get('部门名称')
            doc['no'] = new_doc.get('医生ID')
            doc['name'] = new_doc.get('真实姓名')
            doc['his_name'] = new_doc.get('医生姓名')
            doc['career'] = new_doc.get('挂号级别')
            doc['fee'] = new_doc.get('现价')
            doc['appointment_id'] = new_doc.get('号码')
            doc['visit_id'] = new_doc.get('visit_id')
            doc['farther_dept_id'] = new_doc.get('FartherDepID')
            doc['farther_dept_name'] = new_doc.get('FartherDepName')
            doc['sex'] = new_doc.get('Sex')
            doc['u_count'] = new_doc.get('UCount')
            doc['shoufei_xm'] = new_doc.get('shouFeiXmMc')
            redis_client.hset(APPT_DOCTORS_KEY, str(doc.get('id')), json.dumps(doc, default=str))
            query_sql = f""" select * from nsyy_gyl.appt_doctor where his_name = '{doc.get('his_name')}' """
            docs = db.query_all(query_sql)
            redis_client.hset(APPT_DOCTORS_BY_NAME_KEY, doc.get('his_name'), json.dumps(docs, default=str))
            # print(datetime.now(), "医生信息有变化，更新", key, new_doc)

    # 更新当日医生坐诊状态
    id_list = ','.join(map(str, his_status_set))
    db.execute(f"""UPDATE nsyy_gyl.appt_doctor SET his_status = CASE WHEN id IN ({id_list}) THEN 1 ELSE 0 END""",
               need_commit=True)
    # 当日医生非坐诊状态的排班记录设置为停诊
    db.execute(f"""UPDATE nsyy_gyl.appt_schedules SET status = 3 
                    WHERE did NOT IN ({id_list}) and shift_date = '{datetime.now().date()}'""")

    doctor_list = db.query_all(f"""select sid, did from nsyy_gyl.appt_schedules 
                     where shift_date = '{datetime.now().date()}' and did not in ({id_list}) """)
    update_list = []
    for doc in doctor_list:
        doc_in_cache = json.loads(redis_client.hget(APPT_DOCTORS_KEY, str(doc.get('did'))))
        doc_in_cache = json.loads(redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, str(doc_in_cache.get('his_name'))))
        if not doc_in_cache:
            continue
        did = -1
        sorted_doctors = sort_doctors(doc_in_cache)
        for d in sorted_doctors:
            if int(d.get('his_status')) == 1:
                did = int(d.get('id'))
                break
        if did != -1:
            update_list.append((did, int(doc.get('sid'))))

    if update_list:
        db.execute_many("UPDATE nsyy_gyl.appt_schedules SET did = %s WHERE sid = %s", update_list, need_commit=True)

    del db


def sort_doctors(doctor_list):
    def sort_key(doctor):
        return 0 if "门诊" in doctor.get('dept_name', '') else 1
    return sorted(doctor_list, key=sort_key)


# update_today_doc_info()


def push_patient(patient_name: str, socket_id: str):
    try:
        socket_data = {"patient_name": patient_name, "type": 300}
        data = {'msg_list': [{'socket_data': socket_data, 'pers_id': socket_id, 'socketd': 'w_site'}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    except Exception as e:
        print(datetime.now(), "Socket Push Error: ", e.__str__())


def update_today_sched(sched):
    """
    排班更新，更新缓存
    :param proj:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    pid = int(sched.get('pid'))
    proj = redis_client.hget(APPT_PROJECTS_KEY, str(pid))
    proj = json.loads(proj)

    today = datetime.now().date()
    room = redis_client.hget(APPT_ROOMS_KEY, str(sched.get('rid')))
    room = json.loads(room)

    aml, pml = {}, {}
    if int(proj.get('proj_type')) == 1:
        doc_info = redis_client.hget(APPT_DOCTORS_KEY, str(sched.get('did')))
        if not doc_info:
            doc_info = {'fee': 0}
        else:
            doc_info = json.loads(doc_info)
        if int(sched.get('ampm')) == 1:
            # 上午
            aml[sched.get('rid')] = {
                'doc_id': sched.get('did'),
                'doctor': doc_info,
                'price': float(doc_info.get('fee')),
                'room': room,
                'rid': sched.get('rid'),
                'proj_name': proj.get('proj_name'),
                'proj_type': proj.get('proj_type'),
                'proj_id': proj.get('id')
            }
        else:
            # 下午
            pml[sched.get('rid')] = {
                'doc_id': sched.get('did'),
                'doctor': doc_info,
                'price': float(doc_info.get('fee')),
                'room': room,
                'rid': sched.get('rid'),
                'proj_name': proj.get('proj_name'),
                'proj_type': proj.get('proj_type'),
                'proj_id': proj.get('id')
            }
    else:
        # 院内项目不指定医生
        if int(sched.get('ampm')) == 1:
            aml[sched.get('rid')] = {
                'room': room,
                'rid': sched.get('rid'),
                'proj_name': proj.get('proj_name'),
                'proj_type': proj.get('proj_type'),
                'proj_id': proj.get('id')
            }
        else:
            pml[sched.get('rid')] = {
                'room': room,
                'rid': sched.get('rid'),
                'proj_name': proj.get('proj_name'),
                'proj_type': proj.get('proj_type'),
                'proj_id': proj.get('id')
            }

    sched_data = redis_client.hget(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid))
    sched_data = json.loads(sched_data) if sched_data else {}
    sched_data[str(today)] = {'1': aml, '2': pml}
    redis_client.hset(APPT_REMAINING_RESERVATION_QUANTITY_KEY, str(pid),
                      json.dumps(sched_data, default=str))


"""
定时更新 诊室医生坐班信息
根据 rid worktime ampm 来定位一条排班记录， 然后更新 did
"""


def do_update():
    now = datetime.now()
    if now.hour < 7 or now.hour > 18:
        return
    # 查询最近新登录过 ip 列表
    login_check_url = "http://192.168.3.240:6093/mz_logincheck"
    if global_config.run_in_local:
        login_check_url = "http://192.168.124.53:6080/mz_logincheck"

    # 获取5分钟前的时间
    time_filter = datetime.now() - timedelta(minutes=5)
    login_data = []
    try:
        response = requests.post(
            login_check_url,
            json={"start_t": time_filter.strftime("%Y-%m-%d %H:%M:%S")},
            timeout=10
        )
        data = response.text
        data = json.loads(data)
        login_data = data.get('data')
    except Exception as e:
        print(datetime.now(), '门诊登录查询方法失败：' + time_filter.strftime("%Y-%m-%d %H:%M:%S") + " " + e.__str__())
    if not login_data:
        return
    # 构建 IP -> 医生姓名 映射
    ip_to_dname = {login.get('ip'): login.get('zhigongxm') for login in login_data}

    # 根据 ip 列表查询房间号
    ips_str = ', '.join(f"'{ip}'" for ip in ip_to_dname.keys())
    query_sql = f"select * from nsyy_gyl.appt_room where ip in ({ips_str})"
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    room_list = db.query_all(query_sql)
    if not room_list:
        del db
        return

    # 构建房间号映射
    rid_to_ip = {room['id']: room['ip'] for room in room_list}
    rids = list(rid_to_ip.keys())

    # 根据房间号查询此刻的排班信息
    # 获取当前时段和工作时间
    period = 1 if datetime.now().hour < 12 else 2
    worktime = (datetime.now().weekday() + 1) % 8

    # 查询排班信息
    rids_str = ', '.join(map(str, rids))
    sql = f"""
        SELECT a.* FROM nsyy_gyl.appt_schedules a
        INNER JOIN (SELECT rid, MIN(sid) AS min_id  FROM nsyy_gyl.appt_schedules WHERE rid IN ({rids_str}) 
        AND shift_date = {datetime.now().date()} AND shift_type = {period} GROUP BY rid
        ) b ON a.rid = b.rid AND a.sid = b.min_id
    """
    schedule_list = db.query_all(sql)
    if not schedule_list:
        del db
        return

    redis_client = redis.Redis(connection_pool=pool)
    for sched in schedule_list:
        rid = sched['rid']
        rip = rid_to_ip.get(rid)
        if not rip:
            continue

        dname = ip_to_dname.get(rip)
        if not dname:
            continue

        # 获取医生 ID
        doctor_data = redis_client.hget(APPT_DOCTORS_BY_NAME_KEY, dname)
        if not doctor_data:
            continue
        doctor_info = json.loads(doctor_data)

        today = datetime.today().date()
        dids = [doctor_info['id']] if isinstance(doctor_info, dict) else [
            doc['id'] for doc in doctor_info if doc.get('update_time') and
                                                datetime.strptime(doc['update_time'],
                                                                  "%Y-%m-%d %H:%M:%S").date() == today
        ]

        if not dids or sched['did'] in dids or sched['status'] != 3:
            continue

        # 更新医生 ID
        update_sql = f"""UPDATE nsyy_gyl.appt_schedules SET did = {dids[0]}, status = 1 WHERE sid = {sched['sid']}"""
        db.execute(update_sql, need_commit=True)
        print(datetime.now(), 'DEBUG: 更新排班', sched, dids[0])

        sched['did'] = dids[0]
        sched['status'] = 1
        update_today_sched(sched)

        push_patient('', f'z{rid}')
        push_patient('', f'y{rid}')

    del db

# do_update()

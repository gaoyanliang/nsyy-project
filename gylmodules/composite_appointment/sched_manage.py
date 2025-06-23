import json
from datetime import datetime, timedelta

import redis
from dateutil.relativedelta import relativedelta

from gylmodules import global_config, global_tools
from gylmodules.composite_appointment import appt_config
from gylmodules.composite_appointment.appt_config import APPT_ROOMS_KEY, APPT_PROJECTS_KEY
from gylmodules.composite_appointment import ca_server
from gylmodules.utils.db_utils import DbUtil

from collections import defaultdict
from itertools import groupby

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)


def data_list(query_by, online: int = 0):
    """
    查询数据列表
    :param query_by:
    :param online:
    :return:
    """
    if query_by == 'doctor':
        sql = 'select * from nsyy_gyl.appt_doctor' if online == 0 \
            else 'select * from nsyy_gyl.appt_doctor where his_status = 1'
    elif query_by == 'room':
        sql = 'select * from nsyy_gyl.appt_room'
    elif query_by == 'project':
        sql = 'select * from nsyy_gyl.appt_project where proj_type = 1'
    else:
        raise Exception('查询数据类型未知')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    data = db.query_all(sql)
    del db

    return data


def query_doc_bynum_or_name(key):
    """
    住院挂号时，需要根据员工号或者医生姓名查询医生信息，这种方式查询出来的医生可直接挂号
    :param key:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""select d.* from nsyy_gyl.appt_doctor d join nsyy_gyl.appt_schedules_doctor sd on d.id = sd.did 
                    where (d.name like '%{key}%' or d.emp_nub = '{key}') and d.his_status = 1 
                    and sd.shift_date = '{str(datetime.now().date())}' and sd.status = 1 """
    docl = db.query_all(query_sql)
    del db

    return docl


def get_schedule(start_date, end_date, query_by, pid, rid: int = 45):
    """
    查询排班列表（医生维度）
    :param start_date:
    :param end_date:
    :param query_by:
    :param pid:
    :param rid:
    :return:
    """
    if not rid:
        rid = 0
    if query_by == 'doctor':
        if pid:
            query_sql = f"""SELECT s.dsid, s.did, s.shift_date, s.shift_type, s.status,
                         d.his_name FROM nsyy_gyl.appt_schedules_doctor s
                        JOIN nsyy_gyl.appt_schedules ss ON s.did = ss.did 
                        JOIN nsyy_gyl.appt_doctor d ON s.did = d.id WHERE s.shift_date 
                        BETWEEN '{start_date}' AND '{end_date}' and ss.pid = {int(pid)} 
                        ORDER BY d.his_name, s.shift_date"""
        else:
            query_sql = f"""SELECT s.dsid, s.did, s.shift_date, s.shift_type, s.status,
                             d.his_name FROM nsyy_gyl.appt_schedules_doctor s
                            JOIN nsyy_gyl.appt_doctor d ON s.did = d.id WHERE s.shift_date 
                            BETWEEN '{start_date}' AND '{end_date}' ORDER BY d.his_name, s.shift_date """
    else:
        pid_condition = f"AND s.pid = {int(pid)}" if pid else ""
        rid_condition = '' if rid == 0 else f" AND s.rid = {rid}"
        query_sql = f"""SELECT s.sid, s.shift_date, s.shift_type, s.rid, r.no, s.pid, p.proj_name, 
                    s.did, d.dept_name, d.name, d.his_name, d.career, s.status FROM nsyy_gyl.appt_schedules s
                    JOIN nsyy_gyl.appt_room r ON s.rid = r.id JOIN nsyy_gyl.appt_project p ON s.pid = p.id
                    JOIN nsyy_gyl.appt_doctor d ON s.did = d.id WHERE s.shift_date BETWEEN '{start_date}' 
                    AND '{end_date}' {pid_condition} {rid_condition} ORDER BY r.no, s.shift_date"""

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    result = db.query_all(query_sql)
    del db
    group_by = 'his_name' if query_by == 'doctor' else 'no'
    ret_data = []
    # 按照医生进行分组
    for key, group in groupby(result, key=lambda x: x[group_by]):
        ret_data.append({"name": key, "list": list(group)})
    return ret_data


def copy_schedule(source_date, target_date, pid, did, rid, copy_by: str = 'doctor'):
    """
    复制排班 支持按周复制，按月复制
    copy_schedule('2024-03-04', '2024-03-11')
    copy_schedule('2024-03', '2024-04')
    :param source_date:
    :param target_date:
    :param pid:
    :param did:
    :param rid:
    :param copy_by:
    :return:
    """
    if len(source_date) != len(target_date):
        raise Exception("日期格式不正确", source_date, target_date)
    try:
        if len(source_date) == 7:
            # 按月复制
            source_start = datetime.strptime(source_date, "%Y-%m").date()
            source_end = source_start + relativedelta(months=1) - timedelta(days=1)

            diff = (datetime.strptime(target_date, "%Y-%m").year - source_start.year) * 12 + (
                    datetime.strptime(target_date, "%Y-%m").month - source_start.month)
            date_sql = f"DATE_FORMAT(shift_date, '%Y-%m') >= '{target_date}' and shift_date " \
                       f" < '{datetime.strptime(target_date, '%Y-%m').date() + relativedelta(months=1)}'"
        elif len(source_date) == 10:
            # 按周复制
            source_start = datetime.strptime(source_date, "%Y-%m-%d").date()
            source_end = source_start + timedelta(days=6)

            diff = (datetime.strptime(target_date, "%Y-%m-%d").date() - source_start).days
            date_sql = f"shift_date >= '{target_date}' and shift_date < " \
                       f"'{datetime.strptime(target_date, '%Y-%m-%d').date() + timedelta(days=7)}'"
        else:
            raise Exception("日期格式不正确", source_date, target_date)

        condition_sql = ""
        condition_sql = condition_sql + f" AND s.did = {int(did)}" if did else ""
        condition_sql = condition_sql + f" AND s.rid = {int(rid)}" if rid else ""
        condition_sql = condition_sql + f" AND s.pid = {int(pid)}" if pid else ""

        table_name = "nsyy_gyl.appt_schedules" if copy_by != 'doctor' else "nsyy_gyl.appt_schedules_doctor"
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        # 要复制的排班日期后面 不能有排班记录
        query_sql = f"""select 1 from {table_name} WHERE {date_sql} {condition_sql} """
        if db.query_all(query_sql):
            del db
            raise Exception("目标日期后有排班记录，请先删除")

        # 获取源排班
        query_sql = f"""select did, rid, pid, shift_date, shift_type, status FROM nsyy_gyl.appt_schedules s
                                   WHERE shift_date BETWEEN '{source_start}' AND '{source_end}' {condition_sql}"""
        if copy_by == 'doctor':
            query_sql = f"""select ds.did, ds.shift_date, ds.shift_type, ds.status 
            FROM nsyy_gyl.appt_schedules_doctor ds left join nsyy_gyl.appt_schedules s on ds.did = s.did
            WHERE ds.shift_date BETWEEN '{source_start}' AND '{source_end}' {condition_sql}"""
        source_schedules = db.query_all(query_sql)

        new_schedules = []
        # 批量插入（忽略冲突）
        if copy_by != 'doctor':
            for s in source_schedules:
                new_date = s.get('shift_date') + (timedelta(days=diff)
                                                  if len(source_date) == 10 else relativedelta(months=diff))
                new_schedules.append((s.get('did'), s.get('rid'), s.get('pid'), new_date,
                                      s.get('shift_type'), s.get('status')))
            insert_sql = """INSERT IGNORE INTO nsyy_gyl.appt_schedules (did, rid, pid, shift_date, shift_type, status)
                            VALUES (%s, %s, %s, %s, %s, %s)"""
        else:
            for s in source_schedules:
                new_date = s.get('shift_date') + (timedelta(days=diff)
                                                  if len(source_date) == 10 else relativedelta(months=diff))
                new_schedules.append((s.get('did'), new_date, s.get('shift_type'), s.get('status')))
            insert_sql = """INSERT IGNORE INTO nsyy_gyl.appt_schedules_doctor (did, shift_date, shift_type, status)
                                        VALUES (%s, %s, %s, %s)"""
        db.execute_many(insert_sql, new_schedules, need_commit=True)
        del db
    except Exception as e:
        raise e


def create_schedule(did, rid, pid, shift_date, shift_type):
    """
    新增排班记录
    :param did:
    :param rid:
    :param pid:
    :param shift_date:
    :param shift_type:
    :return:
    """
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        # 检查诊室占用
        query_sql = f"""SELECT 1 FROM nsyy_gyl.appt_schedules WHERE rid = {int(rid)} 
                        AND shift_date = '{shift_date}' AND shift_type = {int(shift_type)}"""
        if db.query_all(query_sql):
            raise Exception("该诊室此时段已被占用, 请在排班记录中进行更新")

        # 插入记录
        insert_sql = f"""INSERT INTO nsyy_gyl.appt_schedules (did, rid, pid, shift_date, shift_type)
                         VALUES ({int(did)}, {int(rid)}, {int(pid)}, '{shift_date}', {int(shift_type)})"""
        db.execute(insert_sql, need_commit=True)
        del db
    except Exception as e:
        raise Exception('新增排班记录异常', e)


def create_doctor_schedule(did, start_date, end_date):
    """
    新增医生排班记录
    :param did:
    :param start_date:
    :param end_date:
    :return:
    """
    try:
        # 将字符串转换为datetime对象
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        doc_s_data = []
        current_date = start
        while current_date <= end:
            doc_s_data.append((int(did), current_date.strftime('%Y-%m-%d'), 1, 1))
            doc_s_data.append((int(did), current_date.strftime('%Y-%m-%d'), 2, 1))
            # 增加一天
            current_date += timedelta(days=1)

        # 批量插入
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        insert_sql = """
            INSERT INTO nsyy_gyl.appt_schedules_doctor (did, shift_date, shift_type, status)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE did = VALUES(did), shift_date = VALUES(shift_date),
            shift_type = VALUES(shift_type), status = VALUES(status)
        """
        db.execute_many(insert_sql, doc_s_data, need_commit=True)
        del db
    except Exception as e:
        raise Exception('新增医生排班记录异常', e)


def update_schedule(sid, new_rid, new_did, new_pid):
    """
    更新排班记录
    :param sid:
    :param new_rid:
    :param new_did:
    :param new_pid:
    :return:
    """
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        # 获取原记录信息
        query_sql = f"""SELECT * FROM nsyy_gyl.appt_schedules WHERE sid = {int(sid)}"""
        original = db.query_one(query_sql)
        if not original:
            raise Exception("排班记录不存在")

        # 如果修改的是当天的排班，医生修改时校验医生是否有排班权限
        if original.get('shift_date').strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d") \
                and int(new_did) != int(original.get('did')):
            q_sql = f"""select d.id from nsyy_gyl.appt_doctor d join nsyy_gyl.appt_schedules_doctor ds on ds.did = d.id 
                         where d.id = {new_did} and d.his_status = 1 and ds.status = 1 
                         and ds.shift_date = '{datetime.now().strftime("%Y-%m-%d")}' """
            allow_scheduling = db.query_all(q_sql)
            if not allow_scheduling:
                raise Exception("该医生今天没有排班权限")

        # 检查新时间冲突, 仅当修改房间的时候需要检查冲突
        if new_rid:
            shift_date = original.get('shift_date').strftime("%Y-%m-%d")
            query_sql = f"""SELECT 1 FROM nsyy_gyl.appt_schedules WHERE rid = {int(new_rid)} 
            AND shift_date = '{shift_date}' AND shift_type = {original.get('shift_type')} AND sid != {sid}"""
            if db.query_all(query_sql):
                raise Exception("新时段已被占用, 如需修改请更新排班记录")

        # 更新记录
        update_sql = f"""UPDATE nsyy_gyl.appt_schedules SET rid = {int(new_rid)}, did = {int(new_did)}, 
                         pid = {int(new_pid)} WHERE sid = {int(sid)}"""

        db.execute(update_sql, need_commit=True)
        del db

        ca_server.push_patient('', 'z' + str(new_rid))
        ca_server.push_patient('', 'y' + str(new_rid))

        pid_list = []
        if new_pid:
            pid_list.append(new_pid)
        if new_pid and new_pid != int(original.get('pid')):
            pid_list.append(original.get('pid'))
        global_tools.start_thread(update_cache_schedule, (pid_list,))
    except Exception as e:
        raise Exception('更新排班记录异常', e)


def update_doctor_schedule(dsid, new_status):
    """
    更新排班记录
    :param sid:
    :param new_status:
    :return:
    """
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        # 更新记录
        update_sql = f"""UPDATE nsyy_gyl.appt_schedules_doctor SET status = {int(new_status)} 
        WHERE dsid = {int(dsid)}"""
        db.execute(update_sql, need_commit=True)

        query_sql = f"select pid from nsyy_gyl.appt_schedules where did in " \
                    f"(select did from nsyy_gyl.appt_schedules_doctor where dsid = {int(dsid)}) group by pid"
        pid_list = db.query_all(query_sql)
        del db

        if not pid_list:
            return

        pid_list = [p.get('pid') for p in pid_list]
        global_tools.start_thread(update_cache_schedule, (pid_list,))
    except Exception as e:
        raise Exception('更新医生排班记录异常', e)


def query_today_dept_for_appointment():
    """
    查询当天可预约的科室列表
    :return:
    """
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""SELECT distinct d.dept_id DeptID, d.dept_name DeptName, d.farther_dept_id FartherDeptID, 
    d.farther_dept_name FartherDeptName  FROM nsyy_gyl.appt_schedules s join nsyy_gyl.appt_schedules_doctor ds 
    on ds.did = s.did and ds.shift_date = s.shift_date and ds.shift_type = s.shift_type 
    join nsyy_gyl.appt_doctor d on s.did = d.id 
    WHERE s.shift_date = '{datetime.now().date()}' and d.his_status = 1 and ds.status = 1 """
    dept_list = db.query_all(query_sql)
    del db

    return {
        "Count": len(dept_list),
        "ErrorMsg": "",
        "Intime": start_time,
        "Outtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ResultCode": 0,
        "ReturnQty": len(dept_list),
        "TransCode": "4003",
        "List": {
            "Item": dept_list
        },
        "code": 20000,
        "res": "成功"
    }


def query_today_doctor_for_appointment(dept_id):
    """
    查询当天可预约的科室医生列表
    :param dept_id:
    :return:
    """
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""SELECT d.*, s.shift_type FROM nsyy_gyl.appt_schedules s 
    join nsyy_gyl.appt_doctor d on s.did = d.id join nsyy_gyl.appt_schedules_doctor ds 
    on ds.did = s.did and ds.shift_date = s.shift_date and ds.shift_type = s.shift_type 
    WHERE s.shift_date = '{datetime.now().date()}' and d.his_status = 1 and d.dept_id = {dept_id} and ds.status = 1"""
    doctor_list = db.query_all(query_sql)
    del db

    today_doc = []
    for doc in doctor_list:
        shift_type = doc.get('shift_type')
        today_doc.append({
            "RigsterType": "1",  # 含义待定 目前发现仅急诊 急诊内科 急诊诊查费 是2 其他都是 1
            "AsRowid": doc.get('appointment_id'),
            "EnSerNumList": "1",  # 含义待定
            "IsTime": "2",  # 含义待定
            "ShangXiaWBz": "0" if shift_type == 1 else "1",
            "BegTime": "08:00:00" if shift_type == 1 else "14:00:00",
            "EndTime": "12:00:00" if shift_type == 1 else "17:30:00",
            "HBTime": "上午" if shift_type == 1 else "下午",
            "DepID": doc.get('dept_id'),
            "DepName": doc.get('dept_name'),
            "FartherDepID": doc.get('farther_dept_id'),
            "FartherDepName": doc.get('farther_dept_name'),
            "MarkDesc": doc.get('his_name'),
            "MarkId": doc.get('no'),
            "Price": str(doc.get('fee')),
            "RegCount": 100,
            "SessionType": doc.get('career'),
            "Sex": doc.get('sex'),
            "UCount": doc.get('u_count'),
            "VisitID": doc.get('visit_id'),
            "shouFeiXmMc": doc.get('shoufei_xm')
        })

    return {
        "Count": len(today_doc),
        "ErrorMsg": "",
        "Intime": start_time,
        "Outtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ResultCode": 0,
        "ReturnQty": len(today_doc),
        "TransCode": "4003",
        "List": {
            "Item": today_doc
        },
        "code": 20000,
        "res": "成功"
    }


def update_cache_schedule(pid_list):
    if not pid_list:
        return
    redis_client = redis.Redis(connection_pool=pool)
    for pid in pid_list:
        proj = json.loads(redis_client.hget(APPT_PROJECTS_KEY, str(pid)))
        ca_server.cache_proj_7day_schedule(proj)
    ca_server.cache_capacity()


def query_proj_info(proj_type: int):
    """
    查询科室信息 & 科室医生列表（合并查询，优化 Redis & 数据库性能）
    :param proj_type: 项目类型
    :return: 过滤后的项目信息（含医生）
    """
    data = []
    proj_list = []
    redis_client = redis.Redis(connection_pool=pool)
    proj_list = [json.loads(proj[1]) for proj in redis_client.hscan_iter(APPT_PROJECTS_KEY)]
    if not proj_list:
        return []

    # 获取所有项目 ID，批量查询医生数据
    project_ids = list(proj["id"] for proj in proj_list if int(proj["proj_type"]) == proj_type)
    ids_str = ",".join(map(str, project_ids))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    docs = db.query_all(f"""
        SELECT d.*, s.pid FROM nsyy_gyl.appt_doctor d JOIN nsyy_gyl.appt_schedules s ON d.id = s.did
        WHERE s.pid IN ({ids_str}) AND d.his_status = 1
    """)
    del db

    doctor_map = defaultdict(list)
    for row in docs:
        project_id = row["pid"]
        doctor_map[project_id].append(row)

    # 组织数据结构
    for proj in proj_list:
        if int(proj["proj_type"]) != proj_type:
            continue
        proj_id = proj["id"]
        proj["proj_doctors"] = doctor_map.get(proj_id, [])
        data.append(proj)

    return data

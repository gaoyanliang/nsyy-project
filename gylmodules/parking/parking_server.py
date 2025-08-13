import json
from itertools import groupby

from gylmodules import global_config, global_tools
from gylmodules.parking import parking_tools, parking_config
from gylmodules.shift_change import shift_change_config
from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime, timedelta

"""查询会员车辆列表"""


def query_vip_list(key, page_no, page_size):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    condition_sql = ""
    if key:
        condition_sql = f"where plate_no like '%{key}%' or person_name like '%{key}%' or dept_name like '%{key}%'"
    # 查询总数
    total = db.query_one(f"SELECT COUNT(*) FROM nsyy_gyl.parking_vip_cars {condition_sql}")
    total = total.get('COUNT(*)')

    # 分页查询数据
    vip_list = db.query_all(f"SELECT * FROM nsyy_gyl.parking_vip_cars {condition_sql} "
                            f"LIMIT {page_size} OFFSET {(page_no - 1) * page_size}")
    del db

    return {"list": vip_list, "total": total}


"""允许车辆长时间停放 SVIP"""


def add_svip(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    car_id = json_data.get('car_id')
    svip = json_data.get('svip')
    update_sql = f"update nsyy_gyl.parking_vip_cars set is_svip = {svip}  where id = {car_id}"
    db.execute(update_sql, need_commit=True)

    operater = json_data.get('operater')
    operater_id = json_data.get('operater_id')
    # 新增操作记录
    operate_log = {"operater": operater, "operater_id": operater_id,
                   "log": f"{'新增' if svip else '取消'} SVIP 记录",
                   "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                   "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_vip_cars ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    db.execute(sql=insert_sql, need_commit=True)

    del db


"""查询出入库记录"""


def query_inout_records(page_no, page_size, start_date, end_date):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    condition_sql = ""
    if start_date and end_date:
        condition_sql = f"where cross_date between '{start_date}' and '{end_date}'"
    # 查询总数
    total = db.query_one(f"SELECT COUNT(*) FROM nsyy_gyl.parking_inout_records {condition_sql}")
    total = total.get('COUNT(*)')

    # 分页查询数据
    inout_list = db.query_all(f"SELECT * FROM nsyy_gyl.parking_inout_records {condition_sql} "
                              f"LIMIT {page_size} OFFSET {(page_no - 1) * page_size}")
    del db

    return {"list": inout_list, "total": total}


"""新增会员车辆"""


def add_vip_car(json_data):
    # 添加车辆信息 & 会员包期
    park_id = parking_config.park_id_dict.get(json_data.get('park_name'))
    vehicle_id = parking_tools.add_new_car_and_recharge(json_data.get('plate_no'), park_id,
                                                        json_data.get('start_date'), json_data.get('end_date'))
    if not vehicle_id:
        raise Exception("会员车辆添加失败!")

    operater = json_data.pop('operater')
    operater_id = json_data.pop('operater_id')
    json_data['vip_status'] = 1
    json_data['vehicle_id'] = vehicle_id
    json_data['create_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 新增会员记录
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.parking_vip_cars ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)

    log = "新增会员车辆记录"
    if last_rowid == -1:
        log = f"会员车辆添加失败!, {insert_sql}"

    # 新增操作记录
    operate_log = {"operater": operater, "operater_id": operater_id,
                   "log": log, "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                   "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    db.execute(sql=insert_sql, need_commit=True)
    del db


"""更新会员车辆信息"""


def update_vip_car(json_data):
    car_id = json_data.get('car_id')
    update_condition = []
    if json_data.get('plate_no'):
        update_condition.append(f"plate_no = '{json_data.get('plate_no')}'")
    if json_data.get('person_name'):
        update_condition.append(f"person_name = '{json_data.get('person_name')}'")
    if json_data.get('dept_name'):
        update_condition.append(f"dept_name = '{json_data.get('dept_name')}'")
    if json_data.get('dept_id'):
        update_condition.append(f"dept_id = '{json_data.get('dept_id')}'")
    if json_data.get('vehicle_group'):
        update_condition.append(f"vehicle_group = '{json_data.get('vehicle_group')}'")
    if json_data.get('park_name'):
        update_condition.append(f"park_name = '{json_data.get('park_name')}'")

    if update_condition:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        update_sql = f"UPDATE nsyy_gyl.parking_vip_cars SET {','.join(update_condition)} WHERE id = {car_id}"
        db.execute(update_sql, need_commit=True)

        # 新增操作记录
        operate_log = {"operater": json_data.get('operater'), "operater_id": json_data.get('operater_id'),
                       "log": f"更新会员车辆信息", "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                     f"VALUES {str(tuple(operate_log.values()))}"
        db.execute(sql=insert_sql, need_commit=True)
        del db


"""移除会员车辆"""


def remove_vip_car(json_data):
    car_id = json_data.get('car_id')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    vip_car = db.query_one(f"select * from nsyy_gyl.parking_vip_cars where id = {car_id}")
    if not vip_car or not vip_car.get('vehicle_id', ''):
        del db
        raise Exception("会员车辆不存在!")

    success, result = parking_tools.delete_vip_car(vip_car.get('vehicle_id'))
    if not success:
        raise Exception("会员车辆移除失败!")

    delete_sql = f"DELETE FROM nsyy_gyl.parking_vip_cars WHERE id = {car_id}"
    db.execute(sql=delete_sql, need_commit=True)

    # 新增操作记录
    operate_log = {"operater": json_data.get('operater'), "operater_id": json_data.get('operater_id'),
                   "log": "移除会员车辆", "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                   "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    db.execute(sql=insert_sql, need_commit=True)
    del db


"""操作（renew 续费/ freeze 冻结/ restore 恢复 / reset 重置包期）会员车辆"""


def operate_vip_car(json_data):
    car_id = json_data.get('car_id')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    vip_car = db.query_one(f"select * from nsyy_gyl.parking_vip_cars where id = {car_id}")
    if not vip_car or not vip_car.get('vehicle_id', ''):
        del db
        raise Exception("会员车辆不存在!")

    operate_type = json_data.get('operate_type')
    vip_status = 1
    start_date = json_data.get('start_date', '')
    end_date = json_data.get('end_date', '')
    if operate_type in ['renew', 'restore']:
        # 续费/恢复 都需要充值
        success, result = parking_tools.add_vip_card(vip_car['vehicle_id'],
                                                     parking_config.park_id_dict.get(vip_car['park_name']),
                                                     start_date, end_date)
    elif operate_type == 'freeze':
        # 冻结会员车辆
        success, result = parking_tools.remove_vip_card(vip_car['plate_no'], vip_car['vehicle_id'],
                                                        parking_config.park_id_dict.get(vip_car['park_name']))
        vip_status = 3
    elif operate_type == 'reset':
        # 重置会员车辆包期， 需要先删除包期，再新增包期
        success, result = parking_tools.reset_vip_card(vip_car['plate_no'], vip_car['vehicle_id'],
                                                       parking_config.park_id_dict.get(vip_car['park_name']),
                                                       start_date, end_date)
    else:
        del db
        raise Exception("操作类型错误! renew 续费/ freeze 冻结/ restore 恢复")

    if success:
        operate_log = {"operater": json_data.get('operater'), "operater_id": json_data.get('operater_id'),
                       "log": f"{operate_type} 会员车辆 {vip_car} 会员包期, {result} ",
                       "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        update_sql = f"update nsyy_gyl.parking_vip_cars set vip_status = {vip_status}, " \
                     f"start_date = '{start_date}', end_date = '{end_date}'  where id = {car_id}"
        db.execute(update_sql, need_commit=True)
    else:
        operate_log = {"operater": json_data.get('operater'), "operater_id": json_data.get('operater_id'),
                       "log": f"{operate_type} 会员车辆 {vip_car} 异常, {result} ",
                       "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    db.execute(sql=insert_sql, need_commit=True)
    del db


"""自动抓取数据"""


def auto_fetch_data(start_date, end_date):
    timeout_cars, vip_cars, past_records = parking_tools.fetch_data(start_date, end_date, is_fetch_vip=False)

    vip_car_no_list = [vip_car.get('plate_no') for vip_car in vip_cars]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute("update nsyy_gyl.parking_vip_cars set park_time = '0'", need_commit=True)

    if vip_cars:
        args = []
        for vip_car in vip_cars:
            args.append((vip_car.get('vehicle_id'), vip_car.get('plate_no'), vip_car.get('person_name'),
                         vip_car.get('vehicle_group'), vip_car.get('park_name'), vip_car.get('start_time'),
                         vip_car.get('end_time'), vip_car.get('vip_status')))
        insert_sql = """INSERT INTO nsyy_gyl.parking_vip_cars (vehicle_id, plate_no, person_name, vehicle_group, 
            park_name, start_date, end_date, vip_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE vehicle_id = VALUES(vehicle_id), plate_no = VALUES(plate_no)"""
        db.execute_many(insert_sql, args, need_commit=True)

    if past_records:
        args = []
        for record in past_records:
            args.append(
                (record.get('plate_no'), record.get('car_in_out'), record.get('cross_date'), record.get('vehicle_pic'),
                 record.get('entrance_name'), record.get('park_name'), record.get('uuid')))
        insert_sql = """INSERT INTO nsyy_gyl.parking_inout_records (plate_no, car_in_out, cross_date, vehicle_pic, 
        entrance_name, park_name, uuid) VALUES (%s, %s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE plate_no = VALUES(plate_no)"""
        db.execute_many(insert_sql, args, need_commit=True)

    if timeout_cars:
        # 构建 CASE WHEN 语句
        park_time_list = []
        plate_no_list = []
        case_sql = " CASE plate_no "
        for car in timeout_cars:
            if car.get('plate_no') not in vip_car_no_list:
                continue
            case_sql += f" WHEN '{car.get('plate_no')}' THEN %s "
            park_time_list.append(car.get('park_time'))
            plate_no_list.append(car.get('plate_no'))
        case_sql += " END "

        if plate_no_list:
            # 执行更新
            sql = f"UPDATE nsyy_gyl.parking_vip_cars SET park_time = {case_sql} " \
                  f"WHERE plate_no IN ({', '.join(['%s'] * len(plate_no_list))})"

            # 合并参数：先park_time_list，后plate_no_list
            params = park_time_list + plate_no_list
            db.execute(sql, params, need_commit=True)
    del db


"""报表"""


def calculate_parking_duration(start_date, end_date):
    """
    计算每辆车每次的停车时长
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 分页查询数据
    inout_list = db.query_all(f"SELECT b.person_name, b.dept_id, b.dept_name, b.vehicle_group, a.* "
                              f"FROM nsyy_gyl.parking_inout_records a join nsyy_gyl.parking_vip_cars b "
                              f"on a.plate_no = b.plate_no where a.cross_date "
                              f"between '{start_date} 00:00:00' and '{end_date} 23:59:59' "
                              f"and b.vehicle_group = 'VIP'")
    del db

    if not inout_list:
        return []

    results = []
    inout_list = sorted(inout_list, key=lambda x: (x['plate_no'], x['cross_date']))
    for plate_no, group in groupby(inout_list, key=lambda x: x['plate_no']):
        group_list = list(group)

        # 初始化变量
        in_records = []
        out_records = []
        for row in group_list:
            if row['car_in_out'] == '入场':
                in_records.append({
                    'time': row['cross_date'],
                    'data': row
                })
            elif row['car_in_out'] == '出场':
                out_records.append({
                    'time': row['cross_date'],
                    'data': row
                })

        # 处理第一条出场记录（没有对应的入场记录）
        if out_records and (not in_records or out_records[0]['time'] < in_records[0]['time']):
            out_record = out_records.pop(0)
            results.append({
                'plate_no': out_record['data'].get('plate_no'),
                'person_name': out_record['data'].get('person_name'),
                'dept_id': out_record['data'].get('dept_id'),
                'dept_name': out_record['data'].get('dept_name'),
                'in_time': None,
                'out_time': out_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_hours': None,
                'park_name': out_record['data'].get('park_name')
            })

        # 匹配入场和出场记录
        i = j = 0
        while i < len(in_records) and j < len(out_records):
            in_record = in_records[i]
            out_record = out_records[j]

            # 确保出场时间在入场时间之后
            if out_record['time'] > in_record['time']:
                # 计算停车时长（分钟）
                duration = (out_record['time'] - in_record['time']).total_seconds() / 60

                # 添加到结果
                results.append({
                    'plate_no': out_record['data'].get('plate_no'),
                    'person_name': out_record['data'].get('person_name'),
                    'dept_id': out_record['data'].get('dept_id'),
                    'dept_name': out_record['data'].get('dept_name'),
                    'in_time': in_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    'out_time': out_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_hours': round(duration, 2),
                    'park_name': in_record['data'].get('park_name')
                })
                i += 1
                j += 1
            else:
                # 出场时间早于入场时间，跳过这个出场记录
                results.append({
                    'plate_no': out_record['data'].get('plate_no'),
                    'person_name': out_record['data'].get('person_name'),
                    'dept_id': out_record['data'].get('dept_id'),
                    'dept_name': out_record['data'].get('dept_name'),
                    'in_time': None,
                    'out_time': out_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_hours': None,
                    'status': '只有出场记录',
                    'in_entrance': None,
                    'out_entrance': out_record['data'].get('entrance_name'),
                    'park_name': out_record['data'].get('park_name')
                })
                j += 1

        # 处理剩余的未匹配入场记录
        while i < len(in_records):
            in_record = in_records[i]
            results.append({
                'plate_no': in_record['data'].get('plate_no'),
                'person_name': in_record['data'].get('person_name'),
                'dept_id': in_record['data'].get('dept_id'),
                'dept_name': in_record['data'].get('dept_name'),
                'in_time': in_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'out_time': None,
                'duration_hours': None,
                'park_name': in_record['data'].get('park_name')
            })
            i += 1

        # 处理剩余的未匹配出场记录
        while j < len(out_records):
            out_record = out_records[j]
            results.append({
                'plate_no': out_record['data'].get('plate_no'),
                'person_name': out_record['data'].get('person_name'),
                'dept_id': out_record['data'].get('dept_id'),
                'dept_name': out_record['data'].get('dept_name'),
                'in_time': None,
                'out_time': out_record['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_hours': None,
                'park_name': out_record['data'].get('park_name')
            })
            j += 1

    return results

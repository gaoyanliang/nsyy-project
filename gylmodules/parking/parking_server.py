import json
import logging
import re
import time
from itertools import groupby

import redis

from gylmodules import global_config, global_tools
from gylmodules.critical_value import cv_config
from gylmodules.parking import parking_tools, parking_config
from gylmodules.shift_change import shift_change_config
from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)


"""查询预警/停用清单/申请清单"""


def query_timeout_list(type, page_no, page_size):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    condition_sql = f" and park_time >= {parking_config.warning_day} "
    if str(type) == 'shutdown_list':
        # 停放清单
        condition_sql = f" and vip_status = 3 "
    elif str(type) == 'warning_list':
        # 预警清单
        condition_sql = f" and park_time > {parking_config.warning_day} and vip_status = 1 "
    elif str(type) == 'apply_list':
        # 已提交的员工列表 供审批
        condition_sql = f" and vip_status = -1 "
    # 查询总数
    total = db.query_one(f"SELECT COUNT(*) FROM nsyy_gyl.parking_vip_cars where vehicle_group = '员工车辆' and deleted = 0 and is_svip = 0 {condition_sql} "
                         f"order by create_at desc")
    total = total.get('COUNT(*)')

    # 分页查询数据
    vip_list = db.query_all(f"SELECT * FROM nsyy_gyl.parking_vip_cars where vehicle_group = '员工车辆' and deleted = 0 and is_svip = 0 {condition_sql} "
                            f"order by create_at desc "
                            f"LIMIT {page_size} OFFSET {(page_no - 1) * page_size}")
    del db

    return {"list": vip_list, "total": total}


"""审批（高文强） / 启用（财务）车辆"""


def approval_and_enable(json_data, type):
    if 'plate_no' in json_data:
        json_data['plate_no'] = json_data.get('plate_no').replace(' ', '')
    car_id = json_data.get('plate_no')
    operator = json_data.pop('operater')
    operator_id = json_data.pop('operater_id')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    car = db.query_one(f"SELECT * FROM nsyy_gyl.parking_vip_cars where plate_no = '{car_id}'")
    if not car:
        del db
        raise Exception("会员车辆不存在")

    if type == 'approval':
        if car.get('vip_status') != -1:
            del db
            raise Exception("会员车辆状态异常，请联系信息科处理")
        update_sql = f"update nsyy_gyl.parking_vip_cars SET vip_status = 0 " \
                     f"WHERE plate_no = '{car_id}' and vip_status = -1"
    elif type == 'enable':
        if car.get('vip_status') != 0:
            del db
            raise Exception("会员车辆未审批, 请先联系总务科审批")
        update_sql = f"update nsyy_gyl.parking_vip_cars SET vip_status = 1, " \
                     f"start_date = '{json_data.get('start_date')}', end_date = '{json_data.get('end_date')}', " \
                     f"pay_amount = {json_data.get('pay_amount')}, pay_time = '{json_data.get('pay_time')}' " \
                     f"WHERE plate_no = '{car_id}'"
    else:
        raise Exception('操作类型错误')
    db.execute(sql=update_sql, need_commit=True)

    operate_log = {"operater": operator, "operater_id": operator_id, "plate_no": car_id,
                   "log": "审批车辆", "param": json.dumps(json_data, ensure_ascii=False, default=str),
                   "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "op_result": "成功", "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   'pay_amount': json_data.get('pay_amount', 0)}
    if type == 'enable':
        redis_client = redis.Redis(connection_pool=pool)
        redis_client.delete(parking_config.redis_key)
        json_data['park_name'] = car.get('park_name')
        json_data['vehicle_group'] = car.get('vehicle_group')
        json_data['vehicle_id'] = car.get('vehicle_id')
        operate_log = {"operater": operator, "operater_id": operator_id, "plate_no": car_id,
                       "log": "enable_vip_car", "param": json.dumps(json_data, ensure_ascii=False, default=str),
                       "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       'pay_amount': json_data.get('pay_amount', 0)}

        redis_client = redis.Redis(connection_pool=pool)
        redis_client.delete(parking_config.redis_key)

    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        global_tools.send_to_wx(f"会员车辆操作记录添加失败! {operate_log}")
        logger.warning(f"会员车辆操作记录添加失败! {operate_log}")
    del db


"""更新车牌号"""


def update_car_plate_no(json_data):
    if 'old_plate_no' in json_data:
        json_data['old_plate_no'] = json_data.get('old_plate_no').replace(' ', '')
    if 'new_plate_no' in json_data:
        json_data['new_plate_no'] = json_data.get('new_plate_no').replace(' ', '')
    old_plate_no = json_data.get('old_plate_no')
    new_plate_no = json_data.get('new_plate_no')
    operator = json_data.pop('operater')
    operator_id = json_data.pop('operater_id')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    car = db.query_one(f"SELECT * FROM nsyy_gyl.parking_vip_cars where plate_no = '{old_plate_no}'")
    if not car or not car.get('vehicle_id'):
        del db
        raise Exception("会员车辆不存在 或 会员车辆未正式启用")

    db.execute(sql=f"update nsyy_gyl.parking_vip_cars set plate_no = '{new_plate_no}' "
                   f"where plate_no = '{old_plate_no}' ", need_commit=True)
    json_data['park_name'] = car.get('park_name')
    json_data['vehicle_group'] = car.get('vehicle_group')
    json_data['vehicle_id'] = car.get('vehicle_id')
    json_data['start_date'] = car.get('start_date')
    json_data['end_date'] = car.get('end_date')
    operate_log = {"operater": operator, "operater_id": operator_id, "plate_no": old_plate_no,
                   "log": "update_plate_no", "param": json.dumps(json_data, ensure_ascii=False, default=str),
                   "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'pay_amount': 0}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        logger.warning(f"会员车辆操作记录添加失败! {operate_log}")
    del db

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.delete(parking_config.redis_key)


"""提醒车主超时"""


def reminder_person(car_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    sql = f"update nsyy_gyl.parking_vip_cars SET reminder_time = " \
          f"'{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' WHERE id = {car_id}"
    db.execute(sql=sql, need_commit=True)
    del db


"""查询会员车辆列表"""


def query_vip_list(key, dept_id, start_date, end_date, page_no, page_size, type, violated):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    condition_sql = " and vehicle_group = 'VIP' " if str(type) == "VIP" else " and vehicle_group != 'VIP' "
    if key:
        condition_sql = condition_sql + f" and (plate_no like '%{key}%' or person_name like '%{key}%') "
    if dept_id:
        condition_sql = condition_sql + f" and dept_id = '{dept_id}' "
    if start_date and end_date:
        condition_sql = condition_sql + f" and start_date between '{start_date}' and '{end_date}' "
    # 查询总数
    total = db.query_one(f"SELECT COUNT(*) FROM nsyy_gyl.parking_vip_cars where deleted = 0 "
                         f"and violated = {violated} {condition_sql} order by create_at desc")
    total = total.get('COUNT(*)')

    # 分页查询数据
    vip_list = db.query_all(f"SELECT * FROM nsyy_gyl.parking_vip_cars where deleted = 0 "
                            f"and violated = {violated} {condition_sql} order by create_at desc "
                            f"LIMIT {page_size} OFFSET {(page_no - 1) * page_size}")
    del db

    return {"list": vip_list, "total": total}


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


"""员工申请会员车辆"""


def apply_vip_car(json_data):
    if 'plate_no' in json_data:
        json_data['plate_no'] = json_data.get('plate_no').replace(' ', '')
    if 'operater_id' in json_data:
        json_data['applicant_id'] = json_data.pop('operater_id')
    if 'operater' in json_data:
        json_data['applicant_name'] = json_data.pop('operater')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    car = db.query_one(f"select * from nsyy_gyl.parking_vip_cars where plate_no = '{json_data.get('plate_no')}'")
    if not car:
        json_data['vip_status'] = -1
        json_data['create_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fileds = ','.join(json_data.keys())
        args = str(tuple(json_data.values()))
        insert_sql = f"INSERT INTO nsyy_gyl.parking_vip_cars ({fileds}) VALUES {args}"
        last_rowid = db.execute(sql=insert_sql, need_commit=True)
        if last_rowid == -1:
            del db
            raise Exception('会员车辆添加失败!, 请检查车牌号是否重复 避免重复申请')
    else:
        end_date = json_data.get('end_date')
        date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        new_end_date = date_obj + timedelta(days=int(car.get('left_days')))
        end_date = new_end_date.strftime('%Y-%m-%d')
        update_sql = f"update nsyy_gyl.parking_vip_cars SET vip_status = -1, " \
                     f"person_name = '{json_data.get('person_name')}', " \
                     f"person_phone = '{json_data.get('person_phone')}', " \
                     f"dept_id = {json_data.get('dept_id')}, " \
                     f"dept_name = '{json_data.get('dept_name')}', " \
                     f"vehicle_group = '员工车辆', " \
                     f"park_name = '南石医院', " \
                     f"end_date = '{end_date}', " \
                     f"start_date = '{json_data.get('start_date')}', " \
                     f"applicant_id = '{json_data.get('applicant_id')}', " \
                     f"applicant_name = '{json_data.get('applicant_name', '')}', " \
                     f"driver_license = '{json_data.get('driver_license', '')}', " \
                     f"relationship = '{json_data.get('relationship', '')}' " \
                     f"WHERE plate_no = '{json_data.get('plate_no')}'"
        db.execute(update_sql, need_commit=True)

    del db


"""新增/移除/冻结/恢复/重置 会员车辆"""


def operate_vip_car(type, json_data):
    if 'plate_no' in json_data:
        json_data['plate_no'] = json_data.get('plate_no').replace(' ', '')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if type == 'add':
        # 新增临时会员记录
        operator = json_data.pop('operater')
        operator_id = json_data.pop('operater_id')
        if json_data.get('vehicle_group', '') != "VIP":
            del db
            return
        enable_add = db.query_all(f"select * from nsyy_gyl.parking_authorize where user_id = '{operator_id}' ")
        if not enable_add:
            del db
            raise Exception('您没有权限添加临时VIP车辆，请联系总务科添加权限后重试')

        json_data['vip_status'] = 0
        json_data['create_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fileds = ','.join(json_data.keys())
        args = str(tuple(json_data.values()))
        insert_sql = f"INSERT INTO nsyy_gyl.parking_vip_cars ({fileds}) VALUES {args}"
        last_rowid = db.execute(sql=insert_sql, need_commit=True)
        if last_rowid == -1:
            del db
            raise Exception('会员车辆添加失败!')

        operate_log = {"operater": operator, "operater_id": operator_id, "plate_no": json_data.get('plate_no'),
                       "log": "add_vip_car", "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    elif type == 'remove':
        vip_car = db.query_one(f"select * from nsyy_gyl.parking_vip_cars where id = {json_data.get('car_id')}")
        if not vip_car:
            del db
            raise Exception("会员车辆不存在! 无法移除")

        delete_sql = f"update nsyy_gyl.parking_vip_cars SET deleted = 1, " \
                     f"plate_no = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}-{vip_car.get('plate_no')}' " \
                     f"WHERE id = {json_data.get('car_id')}"
        db.execute(sql=delete_sql, need_commit=True)

        json_data['vehicle_id'] = vip_car.get('vehicle_id')
        if vip_car.get('vehicle_id', ''):
            operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                           "log": "remove_vip_car", "plate_no": vip_car.get('plate_no'),
                           "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                           "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           'pay_amount': json_data.get('pay_amount', 0)}
        else:
            operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                           "log": "remove_vip_car", "plate_no": vip_car.get('plate_no'),
                           "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                           "op_result": "成功", "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           'pay_amount': json_data.get('pay_amount', 0)}
    elif type == 'operate':
        # 操作（renew 续费/ freeze 冻结/ restore 恢复 / reset 重置包期）会员车辆
        operate_type = json_data.get('operate_type')
        vip_car = db.query_one(f"select * from nsyy_gyl.parking_vip_cars where id = {json_data.get('car_id')}")
        if not vip_car or not vip_car.get('vehicle_id', ''):
            del db
            raise Exception("会员车辆不存在 或 暂未添加成功，请稍后重试!")

        vip_status = 1
        if operate_type == 'freeze':
            # 日常停用
            vip_status = 4
        if operate_type == 'freeze' and json_data.get('operater', '') == 'auto':
            # 超时停用
            vip_status = 3

        extended_days = vip_car.get('extended_days', 0)
        # 恢复车辆会员时，需要将延时天数清零
        if operate_type == 'restore':
            extended_days = 0
        update_cond = ''
        if json_data.get('start_date'):
            update_cond = update_cond + f", start_date = '{json_data.get('start_date')}' "
        if json_data.get('end_date'):
            update_cond = update_cond + f", end_date = '{json_data.get('end_date')}' "
        update_sql = f"update nsyy_gyl.parking_vip_cars set vip_status = {vip_status}, " \
                     f"extended_days = {extended_days} {update_cond} " \
                     f" where id = {json_data.get('car_id')}"
        db.execute(update_sql, need_commit=True)

        json_data['vehicle_id'] = vip_car.get('vehicle_id', '')
        json_data['park_name'] = vip_car.get('park_name', '')
        json_data['plate_no'] = vip_car.get('plate_no', '')
        if vip_car.get('vehicle_id', ''):
            operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                           "log": f"{operate_type}_vip_car", "plate_no": vip_car.get('plate_no'),
                           "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                           "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           'pay_amount': json_data.get('pay_amount', 0)}
        else:
            operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                           "log": f"{operate_type}_vip_car", "plate_no": vip_car.get('plate_no'),
                           "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                           "op_result": "成功", "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           'pay_amount': json_data.get('pay_amount', 0)}

    elif type == 'ignore':
        update_sql = f"update nsyy_gyl.parking_vip_cars set extended_days = {json_data.get('extended_days', 0)} " \
                     f" where id = {json_data.get('car_id')}"
        db.execute(update_sql, need_commit=True)

        operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                       "log": f"超时忽略 {json_data.get('extended_days', 0)} 天", "plate_no": json_data.get('plate_no'),
                       "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "op_result": "成功", "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       'pay_amount': json_data.get('pay_amount', 0)}
    else:
        raise Exception('操作类型错误!')

    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        logger.warning(f"会员车辆操作记录添加失败! {json_data}")
    del db

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.delete(parking_config.redis_key)


"""更新会员车辆信息"""


def update_vip_car(json_data):
    if 'plate_no' in json_data:
        json_data['plate_no'] = json_data.get('plate_no').replace(' ', '')
    car_id = json_data.get('id')
    update_condition = []
    if json_data.get('person_name'):
        update_condition.append(f"person_name = '{json_data.get('person_name')}'")
    if json_data.get('person_phone'):
        update_condition.append(f"person_phone = '{json_data.get('person_phone')}'")
    if json_data.get('dept_name'):
        update_condition.append(f"dept_name = '{json_data.get('dept_name')}'")
    if json_data.get('dept_id'):
        update_condition.append(f"dept_id = '{json_data.get('dept_id')}'")
    if json_data.get('vehicle_group'):
        update_condition.append(f"vehicle_group = '{json_data.get('vehicle_group')}'")
    if json_data.get('park_name'):
        update_condition.append(f"park_name = '{json_data.get('park_name')}'")
    if json_data.get('extended_days'):
        update_condition.append(f"extended_days = {json_data.get('extended_days')}")
    if json_data.get('svip'):
        update_condition.append(f"svip = {json_data.get('svip')}")
    if json_data.get('pay_amount'):
        update_condition.append(f"pay_amount = {json_data.get('pay_amount')}")
    if json_data.get('pay_time'):
        update_condition.append(f"pay_time = '{json_data.get('pay_time')}'")
    if json_data.get('driver_license'):
        update_condition.append(f"driver_license = '{json_data.get('driver_license')}'")
    if json_data.get('relationship'):
        update_condition.append(f"relationship = '{json_data.get('relationship')}'")

    if json_data.get('new_plate_no'):
        data = {"new_plate_no": json_data.get('new_plate_no'), "old_plate_no": json_data.get('plate_no'),
                "operater": json_data.get('operater'), "operater_id": json_data.get('operater_id')}
        update_car_plate_no(data)

    if update_condition:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        update_sql = f"UPDATE nsyy_gyl.parking_vip_cars SET {','.join(update_condition)} WHERE id = {car_id}"
        db.execute(update_sql, need_commit=True)

        # 新增操作记录
        operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                       "plate_no": json_data.get('plate_no'),
                       "log": f"update_car_info", "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                       "op_result": "成功", "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                     f"VALUES {str(tuple(operate_log.values()))}"
        db.execute(sql=insert_sql, need_commit=True)
        del db


# =============================================== 定时任务 ===============================================


def calculate_entry_time(parking_minutes):
    """
    根据当前时间和停放时长计算入场时间
    :param parking_minutes: 停放时长（分钟）
    :return: 入场时间字符串（格式：YYYY-MM-DD HH:MM:SS）
    """
    # 获取当前时间
    current_time = datetime.now()

    # 计算入场时间（当前时间减去停放时长）
    entry_time = current_time - timedelta(minutes=parking_minutes)

    # 格式化输出
    return entry_time.strftime('%Y-%m-%d %H:%M:%S')


"""自动抓取数据"""


def time_str_to_minutes(time_str):
    """
    将包含天、小时、分钟的时间字符串转换为总分钟数
    """
    days, hours, minutes = 0, 0, 0
    # 使用正则表达式提取数字和单位
    pattern = r'(\d+)\s*(天|小时|分钟)'
    matches = re.findall(pattern, time_str)

    for value, unit in matches:
        num = int(value)
        if unit == '天':
            days = num
        elif unit == '小时':
            hours = num
        elif unit == '分钟':
            minutes = num

    # 计算总分钟数
    total_minutes = days * 24 * 60 + hours * 60 + minutes
    return total_minutes


def auto_fetch_data():
    start_date = f"{(datetime.today() - timedelta(days=1)).date()}"
    end_date = start_date

    def run():
        max_retries = 3
        retry_count = 0
        is_success = False
        while retry_count < max_retries:
            try:
                # 记录请求开始时间（用于计算耗时）
                start_time = datetime.now()
                timeout_cars, vip_cars, past_records = parking_tools.fetch_data(start_date, end_date, is_fetch_vip=True)
                logger.info(f"成功获取到今停车场数据 | 耗时: {(datetime.now() - start_time).total_seconds():.2f}s")
                is_success = True
                if is_success:
                    return is_success, timeout_cars, vip_cars, past_records
            except Exception as e:
                last_exception = e
                retry_count += 1
                wait_time = 2 ** retry_count  # 指数退避（1, 2, 4秒...）
                logger.exception("获取到今停车场数据异常 稍后重试")
                if retry_count < max_retries:
                    time.sleep(wait_time)
                else:
                    global_tools.send_to_wx("自动同步停车场数据失败")

        return is_success, [], [], []

    is_success, timeout_cars, vip_cars, past_records = run()
    if not is_success:
        return

    vip_car_no_list = [vip_car.get('plate_no') for vip_car in vip_cars]
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    all_cars = db.query_all("select plate_no, vip_status from nsyy_gyl.parking_vip_cars where deleted = 0")
    hist_car_status = {car.get('plate_no'): car.get('vip_status') for car in all_cars}
    all_cars = [car.get('plate_no') for car in all_cars]

    for car in vip_cars:
        car['violated'] = 0 if car['plate_no'] in all_cars else 1
        if car.get('vip_status') != hist_car_status.get(car.get('plate_no'), -2):
            global_tools.send_to_wx(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                                    f"会员车辆 [{car.get('plate_no')}] 状态不一致, 真实状态为: {car.get('vip_status')} "
                                    f"OA 状态为: {hist_car_status.get(car.get('plate_no'), -2)}")

    if vip_cars:
        args = []
        for vip_car in vip_cars:
            args.append((
                vip_car['vehicle_id'], vip_car['plate_no'], vip_car['person_name'], vip_car['vehicle_group'],
                vip_car['park_name'], vip_car['start_date'], vip_car['end_date'], vip_car['vip_status'],
                vip_car['violated'], vip_car['left_days'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        insert_sql = """INSERT INTO nsyy_gyl.parking_vip_cars (vehicle_id, plate_no, person_name, vehicle_group, 
            park_name, start_date, end_date, vip_status, violated, left_days, create_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE vehicle_id = VALUES(vehicle_id), 
            plate_no = VALUES(plate_no), violated = VALUES(violated), left_days = VALUES(left_days)"""
        db.execute_many(insert_sql, args, need_commit=True)
        # 更新到期的会员
        db.execute("update nsyy_gyl.parking_vip_cars set vip_status = 2 where vip_status = 1 and left_days = 0", need_commit=True)

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
        db.execute("update nsyy_gyl.parking_vip_cars set entry_time = NULL, park_time_str = NULL, park_time = 0", need_commit=True)
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
            sql = f"UPDATE nsyy_gyl.parking_vip_cars SET park_time_str = {case_sql} " \
                  f"WHERE plate_no IN ({', '.join(['%s'] * len(plate_no_list))})"
            # 合并参数：先park_time_list，后plate_no_list
            params = park_time_list + plate_no_list
            db.execute(sql, params, need_commit=True)

    all_cars = db.query_all("select plate_no, park_time_str from nsyy_gyl.parking_vip_cars "
                            "where deleted = 0 and park_time_str is not null")

    if all_cars:
        park_time_list = []
        plate_no_list = []
        case_sql = " CASE plate_no "
        for car in all_cars:
            case_sql += f" WHEN '{car.get('plate_no')}' THEN %s "
            park_time_list.append(time_str_to_minutes(car.get('park_time_str')))
            plate_no_list.append(car.get('plate_no'))
        case_sql += " END "

        if plate_no_list:
            # 执行更新
            sql = f"UPDATE nsyy_gyl.parking_vip_cars SET park_time = {case_sql} " \
                  f"WHERE plate_no IN ({', '.join(['%s'] * len(plate_no_list))})"
            # 合并参数：先park_time_list，后plate_no_list
            params = park_time_list + plate_no_list
            db.execute(sql, params, need_commit=True)

        entry_time_list = []
        plate_no_list = []
        case_sql = " CASE plate_no "
        for car in all_cars:
            case_sql += f" WHEN '{car.get('plate_no')}' THEN %s "
            entry_time_list.append(calculate_entry_time(time_str_to_minutes(car.get('park_time_str'))))
            plate_no_list.append(car.get('plate_no'))
        case_sql += " END "

        if plate_no_list:
            # 执行更新
            sql = f"UPDATE nsyy_gyl.parking_vip_cars SET entry_time = {case_sql} " \
                  f"WHERE plate_no IN ({', '.join(['%s'] * len(plate_no_list))})"
            # 合并参数：先park_time_list，后plate_no_list
            params = entry_time_list + plate_no_list
            db.execute(sql, params, need_commit=True)
    del db


def auto_freeze_car():
    if parking_config.enable_auto_freeze and not global_config.run_in_local:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        records = db.query_all(f"select * from nsyy_gyl.parking_vip_cars "
                               f"where vehicle_group = '员工车辆' and park_time >= 10 * 24 * 60 and vip_status = 1")
        del db
        if not records:
            return

        for record in records:
            operate_vip_car("operate", {
                "car_id": record.get('id'),
                "operate_type": "freeze",
                "operater_id": "auto",
                "operater": "auto"
            })


def auto_asynchronous_execution():
    """异步执行所有车辆操作"""
    def asynchronous_run():
        redis_client = redis.Redis(connection_pool=pool)
        if redis_client.exists(parking_config.redis_key):
            return

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        operate_record = db.query_one(f"select * from nsyy_gyl.parking_operation_logs "
                                      f"where op_result is null order by create_at limit 1")

        if not operate_record:
            del db
            redis_client.set(parking_config.redis_key, 1)
            return

        try:
            log_type = operate_record.get('log')
            param = json.loads(operate_record.get('param'))
            if log_type == 'add_vip_car':
                park_id = parking_config.park_id_dict.get(param.get('park_name'))
                vehicle_id = parking_tools.add_new_car_and_recharge(param.get('plate_no'), park_id,
                                                                    param.get('start_date'), param.get('end_date'),
                                                                    param.get('vehicle_group', ''))
                if not vehicle_id:
                    logger.error(f"自动任务 - 新增临时VIP车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                    del db
                    return
                db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}', vip_status = 1 "
                           f"where plate_no = '{param.get('plate_no')}'", need_commit=True)
            elif log_type == 'enable_vip_car':
                park_id = parking_config.park_id_dict.get(param.get('park_name'))
                vehicle_id = param.get('vehicle_id')
                if not param.get('vehicle_id'):
                    vehicle_id = parking_tools.add_new_car_and_recharge(param.get('plate_no'), park_id,
                                                                        param.get('start_date'), param.get('end_date'),
                                                                        param.get('vehicle_group', ''))
                    if not vehicle_id:
                        logger.error(f"自动任务 - 新增会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        del db
                        return
                else:
                    # 启用车辆时，如果存在 vehicle id 则重置会员车辆包期
                    success, result = parking_tools.reset_vip_card(param.get('plate_no'), param.get('vehicle_id'),
                                                                   park_id,
                                                                   param.get('start_date'), param.get('end_date'))
                    if not success:
                        logger.error(f"自动任务 - 启用重置会员车辆包期失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        del db
                        return
                db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}', vip_status = 1 "
                           f"where plate_no = '{param.get('plate_no')}'", need_commit=True)
            elif log_type == 'remove_vip_car':
                success, result = parking_tools.delete_vip_car(param.get('vehicle_id'))
                if not success:
                    logger.error(f"自动任务 - 移除会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                    del db
                    return
            elif log_type == 'reset_vip_car':
                # 重置会员车辆包期， 需要先删除包期，再新增包期
                success, result = parking_tools.reset_vip_card(param.get('plate_no'), param.get('vehicle_id'),
                                                               parking_config.park_id_dict.get(param.get('park_name')),
                                                               param.get('start_date'), param.get('end_date'))
                if not success:
                    logger.error(f"自动任务 - 重置会员车辆包期失败, op_log_id = {operate_record.get('id')} 稍后重试")
                    del db
                    return
            elif log_type == 'freeze_vip_car':
                success, result = parking_tools.remove_vip_card(param.get('plate_no'), param.get('vehicle_id'),
                                                                parking_config.park_id_dict.get(param.get('park_name')))
                if not success:
                    logger.error(f"自动任务 - 冻结会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                    del db
                    return
            elif log_type == 'renew_vip_car' or log_type == 'restore_vip_car':
                # 续费/恢复 都需要充值
                success, result = parking_tools.add_vip_card(param.get('vehicle_id'),
                                                             parking_config.park_id_dict.get(param.get('park_name')),
                                                             param.get('start_date'), param.get('end_date'))
                if not success:
                    logger.error(f"自动任务 - 续费/恢复会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                    del db
                    return
                if success and log_type == 'restore_vip_car':
                    # 恢复会员车辆时 将停放时长移除
                    db.execute(f"update nsyy_gyl.parking_vip_cars set park_time = 0, "
                               f"park_time_str = NULL where plate_no = '{param.get('plate_no')}' ", need_commit=True)
            elif log_type == 'update_plate_no':
                # 修改车牌号 调用修改车牌接口 修改后停车场系统不识别车辆， 改为先移除旧车辆信息 再新增新车牌
                if param.get('vehicle_id'):
                    success, result = parking_tools.delete_vip_car(param.get('vehicle_id'))
                    if not success:
                        logger.error(f"自动任务 - 更新车牌 1移除旧车牌车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        global_tools.send_to_wx(f"op_log_id = {operate_record.get('id')} 更新车牌(移除旧车牌)失败, {param}")
                        del db
                        return

                    vehicle_id = parking_tools.add_new_car_and_recharge(param.get('new_plate_no'),
                                                                        parking_config.park_id_dict.get(param.get('park_name')),
                                                                        param.get('start_date'), param.get('end_date'),
                                                                        param.get('vehicle_group', ''))
                    if not vehicle_id:
                        logger.error(f"自动任务 - 更新车牌2 新增新车牌车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        global_tools.send_to_wx(f"op_log_id = {operate_record.get('id')} 更新车牌（新增新车牌车辆）失败, {param}")
                        del db
                        return

                    db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}' "
                               f"where plate_no = '{param.get('new_plate_no')}'", need_commit=True)
            else:
                logger.warning(f"自动任务 - 无效操作类型: {operate_record}")
                del db
                return

            db.execute(f"update nsyy_gyl.parking_operation_logs set op_result = '成功', "
                       f"op_time = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' "
                       f"where id = {operate_record.get('id')}", need_commit=True)
            del db
            return
        except Exception as e:
            logger.error(f"自动任务 - 异常: {e.__str__()[:100]}")

    global_tools.start_thread(asynchronous_run)


#  =============================================== 报表 & 授权管理 ===============================================


"""报表"""


def calculate_parking_fee(parking_minutes):
    """
    计算停车费用
    :param parking_minutes: 停车时长（分钟）
    :return: 应收费用（元）
    """
    # 免费时段
    if parking_minutes <= 30:
        return 0

    # 首段收费（30-120分钟）
    if parking_minutes <= 120:
        return 3

    # 超出120分钟后的循环收费
    extra_minutes = parking_minutes - 120
    # 每60分钟1元，不足60分钟按60分钟计算
    extra_charge = (extra_minutes + 59) // 60  # 等价于 math.ceil(extra_minutes / 60)

    return 3 + extra_charge


def calculate_parking_duration(type, start_date, end_date):
    """
    计算每辆车每次的停车时长
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
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
                'amount': 0,
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
                    'duration_hours': duration,
                    'amount': calculate_parking_fee(duration),
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
                    'amount': 0,
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
                'amount': 0,
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
                'amount': 0,
                'park_name': out_record['data'].get('park_name')
            })
            j += 1

    if str(type) == 'summary':
        from collections import defaultdict
        record_dict = defaultdict(list)
        dept_ids = set()
        for item in results:
            dept_id = item.get('dept_id')
            record_dict[dept_id].append(item)

        ret = []
        for dept_id, record_list in record_dict.items():
            record_list = list(record_list)
            sum = 0.0
            for item in record_list:
                sum += item.get('amount')
            ret.append({
                "dept_id": dept_id if dept_id else '0',
                "dept_name": record_list[0].get('dept_name', '') if record_list[0].get('dept_name') else '',
                "amount": sum,
            })
        return ret

    return results


"""选择时间内年卡车辆的变化情况，可计算出该阶段收费/退费总额"""


def vehicle_changes(start_date, end_date):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    records = db.query_all(f"select a.*, pvc.person_name, pvc.park_name from nsyy_gyl.parking_operation_logs a "
                           f"join parking_vip_cars pvc on a.plate_no = pvc.plate_no where pvc.vehicle_group = '员工车辆'"
                           f" and pvc.deleted = 0 and a.create_at between '{start_date} 00:00:00' "
                           f"and '{end_date} 23:59:59' and a.log in ('enable_vip_car', 'freeze_vip_car', "
                           f"'restore_vip_car', 'remove_vip_car', 'renew_vip_car', 'reset_vip_car') "
                           f"order by a.plate_no")
    del db
    return records


"""授权管理"""


def person_authorize(json_data):
    is_delete = json_data.get('is_delete')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if int(is_delete) == 1:
        delete_sql = f"delete from nsyy_gyl.parking_authorize where id = {json_data.get('id')}"
        db.execute(sql=delete_sql, need_commit=True)
    else:
        if json_data.get('id'):
            update_sql = f"""
            UPDATE nsyy_gyl.parking_authorize SET dept_id = '{json_data.get('dept_id')}', 
            dept_name = '{json_data.get('dept_name')}',  user_id = '{json_data.get('user_id')}', 
            user_name = '{json_data.get('user_name')}', 
            create_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' WHERE id = {json_data.get('id')};
            """
            db.execute(sql=update_sql, need_commit=True)
        else:
            insert_sql = """INSERT INTO nsyy_gyl.parking_authorize (dept_id, dept_name, user_id, user_name, create_at)
                    VALUES (%s, %s, %s, %s, %s) """
            db.execute(insert_sql, args=(json_data.get('dept_id'), json_data.get('dept_name'),
                                         json_data.get('user_id'), json_data.get('user_name'),
                                         datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)

    operate_log = {"operater": json_data.get('operater', ''), "operater_id": json_data.get('operater_id', ''),
                   "log": f"维护授权列表", "param": f"{json.dumps(json_data, ensure_ascii=False, default=str)}",
                   "op_result": '成功', "op_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    insert_sql = f"INSERT INTO nsyy_gyl.parking_operation_logs ({','.join(operate_log.keys())}) " \
                 f"VALUES {str(tuple(operate_log.values()))}"
    db.execute(sql=insert_sql, need_commit=True)
    del db


"""查询授权列表"""


def query_person_authorize():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    records = db.query_all("select * from nsyy_gyl.parking_authorize")
    del db
    return records

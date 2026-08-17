#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/gyl/gyl_server')  # 就这一行！

import json
import logging
import time
import sys
import redis
from datetime import datetime, timedelta

# 添加日志配置
# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # 输出到控制台
        logging.StreamHandler(sys.stdout),
        # 输出到同级目录的日志文件
        logging.FileHandler(f'parking_auto_run.log')
    ]
)
logger = logging.getLogger(__name__)

from gylmodules import global_config, global_tools
from gylmodules.parking import parking_tools, parking_config
from gylmodules.utils.db_utils_new import DbUtil

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)


def auto_execution_task():
    """异步执行所有车辆操作"""
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists(parking_config.NEED_EXECUTE_PARKING):
        logger.debug("无需要执行的车辆操作")
        return
    if redis_client.exists(parking_config.EXECUTING_PARKING):
        logger.info("有正在执行的车辆操作")
        return

    while True:
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            operate_records = db.query_all(f"select * from nsyy_gyl.parking_operation_logs "
                                          f"where op_result is null order by create_at limit 5")

        if not operate_records:
            logger.info("暂时无需要执行的车辆操作")
            redis_client.delete(parking_config.EXECUTING_PARKING)
            redis_client.delete(parking_config.NEED_EXECUTE_PARKING)
            return

        for operate_record in operate_records:
            logger.info(f"开始执行车辆操作:车牌号 {operate_record.get('plate_no', '')}, 操作类型 {operate_record.get('log', '')}")
            # 添加运行标识
            redis_client.set(parking_config.EXECUTING_PARKING, operate_record.get('id'))

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
                        global_tools.send_to_wx(f"自动任务 - 新增临时VIP车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        continue
                    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                        db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}', vip_status = 1 "
                                   f"where plate_no = '{param.get('plate_no')}'", need_commit=True)

                elif log_type == 'enable_vip_car' or log_type == 'reset_vip_car' \
                        or log_type == 'renew_vip_car' or log_type == 'restore_vip_car':
                    # 在旧数据上修改包期后 有时候停车系统会出现 识别不出来车辆的问题（数据正常），所以先删除旧车辆数据 再新增车辆数据
                    park_id = parking_config.park_id_dict.get(param.get('park_name'))

                    vehicle_id = param.get('vehicle_id')
                    car_record = db.query_one(f"select vehicle_id from nsyy_gyl.parking_vip_cars "
                                              f"where plate_no = '{param.get('plate_no')}' ")
                    if car_record and car_record.get('vehicle_id'):
                        vehicle_id = car_record.get('vehicle_id')

                    if vehicle_id:
                        success, result = parking_tools.delete_vip_car(param.get('vehicle_id'))
                        if not success:
                            logger.error(
                                f"自动任务 - {log_type} 1删除旧车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                            global_tools.send_to_wx(
                                f"op_log_id = {operate_record.get('id')} {log_type}(删除旧车辆)失败, {param}")
                            continue

                    vehicle_id = parking_tools.add_new_car_and_recharge(param.get('plate_no'), park_id,
                                                                        param.get('start_date'), param.get('end_date'),
                                                                        param.get('vehicle_group', ''))
                    if not vehicle_id:
                        logger.error(f"自动任务 - {log_type} 新增会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        global_tools.send_to_wx(f"自动任务 - {log_type} 新增会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        continue

                    condition_sql = ""
                    if log_type == 'restore_vip_car':
                        # 恢复会员车辆时 将停放时长移除
                        condition_sql = ", park_time = 0, entry_time = NULL, park_time_str = NULL"

                    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                        db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}', vip_status = 1 "
                                   f"{condition_sql} where plate_no = '{param.get('plate_no')}'", need_commit=True)

                elif log_type == 'remove_vip_car':
                    success, result = parking_tools.delete_vip_car(param.get('vehicle_id'))
                    if not success:
                        logger.error(f"自动任务 - 移除会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        global_tools.send_to_wx(f"自动任务 - 移除会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        continue
                elif log_type == 'freeze_vip_car':
                    success, result = parking_tools.remove_vip_card(param.get('plate_no'), param.get('vehicle_id'),
                                                                    parking_config.park_id_dict.get(param.get('park_name')))
                    if not success:
                        logger.error(f"自动任务 - 冻结会员车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                        continue
                elif log_type == 'update_plate_no':
                    # 修改车牌号 调用修改车牌接口 修改后停车场系统不识别车辆， 改为先移除旧车辆信息 再新增新车牌
                    if param.get('vehicle_id'):
                        success, result = parking_tools.delete_vip_car(param.get('vehicle_id'))
                        if not success:
                            logger.error(f"自动任务 - 更新车牌 1移除旧车牌车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                            global_tools.send_to_wx(f"op_log_id = {operate_record.get('id')} 更新车牌(移除旧车牌)失败, {param}")
                            continue

                        vehicle_id = parking_tools.add_new_car_and_recharge(param.get('new_plate_no'),
                                                                            parking_config.park_id_dict.get(
                                                                                param.get('park_name')),
                                                                            param.get('start_date'), param.get('end_date'),
                                                                            param.get('vehicle_group', ''))
                        if not vehicle_id:
                            logger.error(f"自动任务 - 更新车牌2 新增新车牌车辆失败, op_log_id = {operate_record.get('id')} 稍后重试")
                            global_tools.send_to_wx(f"op_log_id = {operate_record.get('id')} 更新车牌（新增新车牌车辆）失败, {param}")
                            continue

                        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                            db.execute(f"update nsyy_gyl.parking_vip_cars set vehicle_id = '{vehicle_id}' "
                                       f"where plate_no = '{param.get('new_plate_no')}'", need_commit=True)
                else:
                    logger.warning(f"自动任务 - 无效操作类型: {operate_record}")
                    continue

                with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                            global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                    db.execute(f"update nsyy_gyl.parking_operation_logs set op_result = '成功', "
                               f"op_time = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' "
                               f"where id = {operate_record.get('id')}", need_commit=True)

                time.sleep(5)
            except Exception as e:
                logger.error(f"自动任务 - 异常: {e.__str__()[:100]}")

        redis_client.delete(parking_config.EXECUTING_PARKING)

if __name__ == '__main__':
    auto_execution_task()


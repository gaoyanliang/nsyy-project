import time

import redis
import requests
from fastapi import WebSocket, HTTPException, WebSocketDisconnect, APIRouter
from fastapi import Query
from datetime import datetime, date
import json

import logging
import websockets

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils_new import DbUtil
from outpatient_queue import ai_tool
from outpatient_queue.database import DatabaseManager
from outpatient_queue.models import *
from outpatient_queue.websocket_manager import manager
from outpatient_queue.config import BUSINESS_TYPES

logger = logging.getLogger(__name__)

# ====================== 统一添加 /mz 前缀（使用 APIRouter） ======================
mz_router = APIRouter(prefix="/mz")

db_manager = DatabaseManager()

# 自定义JSON编码器处理datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        return super().default(obj)


def json_serialize(obj):
    """将对象转换为JSON可序列化的格式"""
    return json.loads(json.dumps(obj, cls=DateTimeEncoder))

"""获取所有业务类型"""
@mz_router.get("/business-types")
async def get_business_types():
    return BUSINESS_TYPES


"""获取窗口列表"""
@mz_router.get("/windows")
async def get_windows():
    data = db_manager.get_windows_list()
    data = {item.get('id'): item for item in data}
    return data


"""获取窗口信息"""
@mz_router.get("/windows/{window_id}")
async def get_window_info(window_id: int):
    windows = db_manager.get_windows_list()
    for window in windows:
        if window['id'] == window_id:
            return window
    raise HTTPException(status_code=404, detail="窗口不存在")


"""取号"""
@mz_router.post("/api/take-number")
async def take_number(request: TakeNumberRequest):
    try:
        # 添加患者信息
        db_manager.add_patient(request.patient_id, request.patient_name,
                               request.id_card, request.phone)

        # 生成排队号
        queue_number = db_manager.generate_queue_number(request.business_id)
        business_name = BUSINESS_TYPES[request.business_id]['name']
        business_type = BUSINESS_TYPES[request.business_id]['type']

        # 添加到排队记录
        success = db_manager.add_queue_record(
            queue_number, f"{datetime.today().strftime('%Y%m%d')}",
            request.patient_id, request.patient_name, request.business_id, business_type, business_name
        )

        if success:
            # 广播更新
            await manager.broadcast_all({
                'type': 'queue_update',
                'action': 'new_queue',
                'data': {
                    'queue_number': queue_number,
                    'patient_name': request.patient_name,
                    'business_id': request.business_id,
                    'business_type': business_type,
                    'business_name': business_name,
                    'waiting_count': db_manager.get_waiting_count(request.business_id)
                }
            })

            return {
                'success': True,
                'queue_number': queue_number,
                'business_id': request.business_id,
                'business_type': business_type,
                'business_name': business_name,
                'waiting_count': db_manager.get_waiting_count(request.business_id),
            }
        else:
            raise HTTPException(status_code=500, detail="取号失败")

    except Exception as e:
        logger.error(f"取号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""获取患者药品信息"""
@mz_router.get("/api/patient/{patient_id}/medicines")
async def get_patient_medicines(patient_id: str):
    sql = f"""
          select zj.bingrenid,zj.xingming name,zj.jiuzhenid,my.yizhumc,my.kaidanrq, my.kaidanksmc, my.kaidanysxm, 
round( coalesce(mf.jiesuanje*coalesce(mf.chufangts,1),gy.danjia*coalesce(mc.chufangts,1)*my.shuliang), 4) as price,
        my.chufangid ,
        case when mf.feiyongid is null then 0 else 1 end as zt, my.fayaobz 
        from df_lc_menzhen.zj_jiuzhenxx zj
        join df_lc_menzhen.mz_yizhu my on zj.jiuzhenid = my.jiuzhenid and my.yizhulx in ('11','12','13')
        join df_lc_menzhen.mz_chufang mc on my.chufangid = mc.chufangid
        left join df_bingrenzsy.gy_bingrenxx gb on zj.bingrenid = gb.bingrenid
        left join df_jj_menzhen.mz_feiyong2 mf on my.yizhuid=mf.yizhubh 
        left join df_yaokufang.gy_yaopinjg gy on my.jiageid = gy.jiageid and gy.chandijglx ='DANJIA1' and gy.zuofeibz=0
        where zj.jiuzhenrq::date=current_date and gb.shenfenzh = '{patient_id}'
            """

    medicines = db_manager.pg_query(sql)
    return {'medicines': medicines}


"""根据身份证号查询患者信息"""
@mz_router.get("/api/patient/by-id-card/{patient_id}")
async def get_patient_info(patient_id: str):
    sql = f""" select gb.xingming name, gb.xingbiemc, gb.chushengrq, gb.shenfenzh, 
            case 
                when a.years >= 1 then a.years || '岁'
                when a.months >= 1 then a.months || '月' || a.days || '天'
                else a.days || '天'
            end as nianling
        from df_bingrenzsy.gy_bingrenxx gb
        cross join lateral (
            select 
                extract(year from age(current_date, gb.chushengrq))::int as years,
                extract(month from age(current_date, gb.chushengrq))::int as months,
                extract(day from age(current_date, gb.chushengrq))::int as days
        ) a where gb.shenfenzh = '{patient_id}' or gb.jiuzhenkh = '{patient_id}'"""
    patients_info = db_manager.pg_query(sql)
    return patients_info[0] if patients_info else {}


"""药品缴费"""
@mz_router.post("/api/pay-medicine/{medicine_id}")
async def pay_medicine(medicine_id: int):
    success = db_manager.update_medicine_payment(medicine_id)
    if success:
        return {'success': True, 'message': '缴费成功'}
    else:
        raise HTTPException(status_code=400, detail="缴费失败或已缴费")


"""获取所有业务排队状态"""
@mz_router.get("/api/queue/status")
async def get_queue_status():
    status = db_manager.get_all_business_status()
    current_calls = db_manager.get_current_calls()

    # 转换datetime为字符串
    for call in current_calls:
        if 'call_time' in call and call['call_time']:
            call['call_time'] = call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['call_time'],
                                                                                              datetime) else call[
                'call_time']
        if 'create_time' in call and call['create_time']:
            call['create_time'] = call['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['create_time'],
                                                                                                  datetime) else call[
                'create_time']
        if 'complete_time' in call and call['complete_time']:
            call['complete_time'] = call['complete_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['complete_time'],
                                                                                                  datetime) else call[
                'complete_time']
        if 'skip_time' in call and call['skip_time']:
            call['skip_time'] = call['skip_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                call['skip_time'],
                datetime) else call[
                'skip_time']

    return {
        'business_status': status,
        'current_calls': current_calls,
        'total_waiting': db_manager.get_waiting_count(),
        'avg_wait_time': db_manager.get_avg_wait_time(),
        'today_total': db_manager.get_today_total()
    }


""" 根据患者id 和业务id 判断患者当天是否重复取号"""
@mz_router.get("/api/is-repeat/{patient_id}/{business_id}")
async def is_repeat_queue(patient_id: str, business_id: str):
    record = db_manager.is_repeat_queue(patient_id, business_id)
    if record:
        return {'is_repeat': True, 'message': '当日已取号', 'queue_number': record.get('queue_number'),
                'queue_time': record.get('create_time'), 'business_name': record.get('business_name')}
    else:
        return {'is_repeat': False, 'message': '当日未取号'}


"""获取过号状态"""
@mz_router.get("/api/queue/overdue")
async def get_queue_overdue(business_type: Optional[str] = None, window_id: Optional[str] = None):
    overdue_queues = db_manager.get_overdue_list(business_type, window_id)

    # 转换datetime为字符串
    for call in overdue_queues:
        if 'call_time' in call and call['call_time']:
            call['call_time'] = call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['call_time'],
                                                                                              datetime) else call[
                'call_time']
        if 'create_time' in call and call['create_time']:
            call['create_time'] = call['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['create_time'],
                                                                                                  datetime) else call[
                'create_time']
        if 'complete_time' in call and call['complete_time']:
            call['complete_time'] = call['complete_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['complete_time'],
                                                                                                  datetime) else call[
                'complete_time']
        if 'skip_time' in call and call['skip_time']:
            call['skip_time'] = call['skip_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                call['skip_time'],
                datetime) else call[
                'skip_time']

    return {
        'success': True,
        'list': overdue_queues
    }


"""获取排队列表"""
@mz_router.get("/api/queue/list")
async def get_queue_list(business_id: Optional[str] = None, window_id: Optional[str] = None, status: str = 'waiting'):
    business_ids = []
    if business_id:
        business_ids = [str(business_id)]
    if window_id:
        window_info = db_manager.get_window_info(int(window_id))
        business_ids = window_info['business_sort'].split(',')

    queues = db_manager.get_queue_list(business_ids, status)

    # 转换datetime为字符串
    for queue in queues:
        if 'create_time' in queue and queue['create_time']:
            queue['create_time'] = queue['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                queue['create_time'], datetime) else queue['create_time']
        if 'call_time' in queue and queue['call_time']:
            queue['call_time'] = queue['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(queue['call_time'],
                                                                                                datetime) else queue[
                'call_time']
        if 'complete_time' in queue and queue['complete_time']:
            queue['complete_time'] = queue['complete_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                queue['complete_time'], datetime) else queue['complete_time']

    return {'queues': queues}


"""获取排队列表"""
@mz_router.get("/api/queue/history/{window_id}")
async def get_history_list(window_id: int):
    window = db_manager.get_window_info(window_id)
    if not window:
        raise HTTPException(status_code=404, detail="窗口不存在")
    queues = db_manager.get_history_list(window_id)

    # 转换datetime为字符串
    for queue in queues:
        if 'create_time' in queue and queue['create_time']:
            queue['create_time'] = queue['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                queue['create_time'], datetime) else queue['create_time']
        if 'skip_time' in queue and queue['skip_time']:
            queue['skip_time'] = queue['skip_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(queue['skip_time'],
                                                                                                datetime) else queue[
                'skip_time']
        if 'complete_time' in queue and queue['complete_time']:
            queue['complete_time'] = queue['complete_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                queue['complete_time'], datetime) else queue['complete_time']

    ret_data = [{
      "queue_number": item.get('queue_number'),
      "patient_name": item.get('patient_name'),
      "business_name": item.get('business_name'),
      "service_time": item.get('complete_time') if item.get('status') == 'completed' else item.get('skip_time'),
      "status": item.get('status'),
    } for item in queues]

    return {'history': ret_data}


@mz_router.post("/api/tts_call")
async def call_patient(request: CallRequest):
    # 可以校验窗口是否存在，或直接推送
    window = db_manager.get_window_info(request.window_id)
    if not window:
        raise HTTPException(status_code=404, detail="窗口不存在")
    message = {
        'queue_number': request.queue_number,
        'patient_name': request.patient_name,
        'window_id': request.window_id,
        'window_name': window['window_name'],
    }

    await manager.send_to_window(request.window_id, {'type': 'tts_call', 'data': message})

    return {
        'success': True,
        'window': window
    }


"""叫号"""
@mz_router.post("/api/call")
async def call_queue(request: CallRequest):
    # 获取窗口信息
    window = db_manager.get_window_info(request.window_id)
    if not window:
        raise HTTPException(status_code=404, detail="窗口不存在")

    if request.call_type == 'specific':
        # 广播叫号信息
        call_data = {
            'queue_number': request.queue_number,
            'patient_name': request.patient_name,
            'business_type': request.business_type,
            'window_id': request.window_id,
            'window_name': window['window_name'],
        }

        await manager.send_to_window(request.window_id, {
            'type': 'call_success',
            'data': call_data
        })

        return {
            'success': True,
            'window': window
        }

    # ========== 1. 在这里添加 Redis 分布式锁 ==========
    redis_client = redis.Redis(connection_pool=pool)  # 使用已有的连接池
    lock_key = f"call_lock:{request.window_id}"

    # 尝试获取锁，过期时间设为 3 秒（防止死锁），nx=True 表示键不存在时才设置
    if not redis_client.set(lock_key, "1", ex=3, nx=True):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")

    try:
        next_queue = db_manager.call_next_queue(request.business_type, window['business_sort'],
                                                request.window_id, window['window_name'])
        if not next_queue:
            return {'success': False, 'message': '叫号失败'}

        # 广播叫号信息
        call_data = {
            'queue_number': next_queue['queue_number'],
            'patient_name': next_queue['patient_name'],
            'business_type': next_queue['business_type'],
            'business_name': next_queue['business_name'],
            'window_id': request.window_id,
            'window_name': window['window_name'],
            'call_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        await manager.broadcast_all({'type': 'call', 'data': call_data})
        await manager.send_to_window(request.window_id, {'type': 'call_success', 'data': call_data})

        return {'success': True, 'queue': next_queue, 'window': window}
    finally:
        # ========== 3. 无论成功或失败，都要释放锁 ==========
        redis_client.delete(lock_key)



    # # 获取下一个排队
    # next_queue = db_manager.get_next_queue(request.business_type, window['business_sort'])
    # if not next_queue:
    #     return {'success': False, 'message': '没有等待的患者'}
    #
    # # 叫号
    # success = db_manager.call_queue(next_queue['queue_number'], request.window_id, window['window_name'])
    #
    # if success:
    #     # 转换datetime
    #     call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #
    #     # 广播叫号信息
    #     call_data = {
    #         'queue_number': next_queue['queue_number'],
    #         'patient_name': next_queue['patient_name'],
    #         'business_type': next_queue['business_type'],
    #         'business_name': next_queue['business_name'],
    #         'window_id': request.window_id,
    #         'window_name': window['window_name'],
    #         'call_time': call_time
    #     }
    #
    #     await manager.broadcast_all({
    #         'type': 'call',
    #         'data': call_data
    #     })
    #
    #     await manager.send_to_window(request.window_id, {
    #         'type': 'call_success',
    #         'data': call_data
    #     })
    #
    #     return {
    #         'success': True,
    #         'queue': next_queue,
    #         'window': window
    #     }
    # else:
    #     raise HTTPException(status_code=500, detail="叫号失败")


"""完成服务"""
@mz_router.post("/api/complete")
async def complete_service(request: CompleteRequest):
    success = db_manager.complete_queue(request.queue_number)

    if success:
        await manager.broadcast_all({
            'type': 'complete',
            'data': {
                'queue_number': request.queue_number,
                'window_id': request.window_id
            }
        })
        return {'success': True}
    else:
        raise HTTPException(status_code=500, detail="完成服务失败")


"""取药完成"""
@mz_router.post("/api/medicine/complete")
async def medicine_complete(request: CompleteRequest):
    success = db_manager.medicine_complete(request.queue_number, request.status)

    if success:
        await manager.broadcast_all({
            'type': 'complete',
            'data': {
                'queue_number': request.queue_number,
                'window_id': request.window_id,
                'status': request.status
            }
        })
        return {'success': True}
    else:
        raise HTTPException(status_code=500, detail="完成服务失败")


"""跳过/过号"""
@mz_router.post("/api/skip")
async def skip_queue(request: SkipRequest):
    success = db_manager.skip_queue(request.queue_number, request.reason)

    if success:
        await manager.broadcast_all({
            'type': 'skip',
            'data': {
                'queue_number': request.queue_number,
                'reason': request.reason
            }
        })
        return {'success': True}
    else:
        raise HTTPException(status_code=500, detail="跳过失败")


"""唤醒"""
@mz_router.post("/api/wakeup")
async def wake_up(request: WakeUpRequest):
    success = db_manager.wake_up(request.patient_id, request.queue_number, request.business_type)

    if success:
        await manager.send_to_window(request.window_id, {
            'type': 'queue_update'
        })
        return {'success': True}
    else:
        raise HTTPException(status_code=500, detail="唤醒失败")


"""患者重新激活过号的排队（通过重新刷卡/扫码）"""
@mz_router.post("/api/patient/reactivate/{patient_id}/{business_id}")
async def reactivate_patient_queue(patient_id: str, business_id: str):
    try:
        # 查找该患者是否有过号的排队记录（状态为skipped）
        skipped_queue = db_manager.get_patient_skipped_record(patient_id, business_id)
        if not skipped_queue:
            return {
                'success': False,
                'message': '没有找到过号的排队记录',
                'has_skipped': False
            }

        # 重新激活，顺延到当前队列末尾
        # success = db.reactivate_queue(skipped_queue['queue_number'])

        new_queue_number = db_manager.reactivate_queue_defer(
            old_queue_number=skipped_queue['queue_number'],
            patient_id=patient_id,
            patient_name=skipped_queue['patient_name'],
            business_id=skipped_queue['business_id']
        )

        if new_queue_number:
            # 获取更新后的等待人数
            waiting_count = db_manager.get_waiting_count(skipped_queue['business_id'])
            avg_wait_time = db_manager.get_avg_wait_time(skipped_queue['business_id'])
            today_total = db_manager.get_today_total(skipped_queue['business_id'])

            # 广播队列更新
            await manager.broadcast_all({
                'type': 'queue_update',
                'action': 'reactivate',
                'data': {
                    'queue_number': skipped_queue['queue_number'],
                    'patient_name': skipped_queue['patient_name'],
                    'business_type': skipped_queue['business_type'],
                    'business_name': skipped_queue['business_name'],
                    'waiting_count': waiting_count,
                    'avg_wait_time': avg_wait_time,
                    'today_total': today_total
                }
            })

            return {
                'success': True,
                'message': f'已顺延，新排队号：{new_queue_number}',
                'old_queue_number': skipped_queue['queue_number'],
                'queue_number': new_queue_number,
                'business_name': skipped_queue['business_name'],
                'waiting_count': waiting_count,
                'has_skipped': True
            }
        else:
            return {
                'success': False,
                'message': '顺延失败',
                'has_skipped': True
            }

    except Exception as e:
        logger.error(f"重新激活失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""检查患者是否有过号的排队记录"""
@mz_router.get("/api/patient/{patient_id}/{business_id}/check-skipped")
async def check_patient_skipped(patient_id: str, business_id: str):
    try:
        skipped_queue = db_manager.get_patient_skipped_record(patient_id, business_id)
        if skipped_queue:
            # 转换datetime
            if 'create_time' in skipped_queue and skipped_queue['create_time']:
                skipped_queue['create_time'] = skipped_queue['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                    skipped_queue['create_time'], datetime) else skipped_queue['create_time']

            return {
                'has_skipped': True,
                'queue': skipped_queue
            }
        else:
            return {
                'has_skipped': False
            }
    except Exception as e:
        logger.error(f"检查过号记录失败: {e}")
        return {'has_skipped': False}


@mz_router.get("/api/status")
async def get_status():
    return {'status': 'ok'}


"""大屏展示WebSocket连接"""
@mz_router.websocket("/ws/display")
async def websocket_display(websocket: WebSocket):
    await manager.connect_display(websocket)
    try:
        # 发送初始数据
        status = db_manager.get_all_business_status()
        current_calls = db_manager.get_current_calls()

        # 转换datetime为字符串
        for call in current_calls:
            if 'call_time' in call and call['call_time']:
                call['call_time'] = call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(call['call_time'],
                                                                                                  datetime) else call[
                    'call_time']
            if 'create_time' in call and call['create_time']:
                call['create_time'] = call['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                    call['create_time'], datetime) else call['create_time']

        # 获取所有等待队列
        waiting_queues = db_manager.get_queue_list(status='waiting')
        for queue in waiting_queues:
            if 'create_time' in queue and queue['create_time']:
                queue['create_time'] = queue['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                    queue['create_time'], datetime) else queue['create_time']

        init_data = {
            'type': 'init',
            'data': {
                'business_status': status,
                'current_calls': current_calls,
                'waiting_queues': waiting_queues,
                'total_waiting': db_manager.get_waiting_count(),
                'avg_wait_time': db_manager.get_avg_wait_time(),
                'today_total': db_manager.get_today_total()
            }
        }

        await websocket.send_text(json.dumps(init_data, cls=DateTimeEncoder))

        while True:
            # 保持连接，接收心跳
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
            elif data == 'get_status':
                # 客户端请求最新状态
                status = db_manager.get_all_business_status()
                current_calls = db_manager.get_current_calls()
                for call in current_calls:
                    if 'call_time' in call and call['call_time']:
                        call['call_time'] = call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                            call['call_time'], datetime) else call['call_time']

                await websocket.send_text(json.dumps({
                    'type': 'status_update',
                    'data': {
                        'business_status': status,
                        'current_calls': current_calls,
                        'total_waiting': db_manager.get_waiting_count(),
                        'avg_wait_time': db_manager.get_avg_wait_time(),
                        'today_total': db_manager.get_today_total()
                    }
                }, cls=DateTimeEncoder))

    except WebSocketDisconnect:
        manager.disconnect_display(websocket)
        logger.debug("大屏WebSocket连接断开")
    except Exception as e:
        logger.warning(f"大屏WebSocket错误: {e}")
        manager.disconnect_display(websocket)


"""窗口WebSocket连接"""
@mz_router.websocket("/ws/window/{window_id}")
async def websocket_window(websocket: WebSocket, window_id: int):
    await manager.connect_window(websocket, window_id)
    try:
        logger.debug(f"窗口 {window_id} WebSocket连接成功")

        # 连接成功后发送当前窗口的叫号状态
        # 获取该窗口正在叫号的患者
        current_call = db_manager.get_current_window_calls(window_id)

        # 获取窗口信息
        window_info = db_manager.get_window_info(window_id)

        # 转换datetime
        if current_call:
            if current_call.get('call_time'):
                current_call['call_time'] = current_call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                    current_call['call_time'], datetime) else current_call['call_time']
            if current_call.get('create_time'):
                current_call['create_time'] = current_call['create_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                    current_call['create_time'], datetime) else current_call['create_time']

        # 发送初始化数据
        init_data = {
            'type': 'init',
            'data': {
                'window_id': window_id,
                'window_name': window_info['window_name'] if window_info else f'窗口{window_id}',
                'window_type': window_info['window_type'] if window_info else 'general',
                'current_call': current_call
            }
        }

        await websocket.send_json(init_data)

        if current_call:
            logger.debug(f"窗口 {window_id} 恢复当前叫号: {current_call['queue_number']}")

        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            if data == 'ping':
                logger.debug(f"ping 窗口 {window_id} WebSocket连接保持")
                await websocket.send_text('pong')
            elif data == 'get_status':
                # 客户端请求当前窗口状态
                current_call = db_manager.get_current_window_calls(window_id)
                if current_call:
                    if current_call.get('call_time'):
                        current_call['call_time'] = current_call['call_time'].strftime(
                            "%Y-%m-%d %H:%M:%S") if isinstance(current_call['call_time'], datetime) else current_call[
                            'call_time']
                        current_call['create_time'] = current_call['create_time'].strftime(
                            "%Y-%m-%d %H:%M:%S") if isinstance(current_call['create_time'], datetime) else current_call[
                            'call_time']

                await websocket.send_json({
                    'type': 'status',
                    'data': {
                        'current_call': current_call
                    }
                })
            else:
                # 尝试解析JSON消息
                try:
                    msg = json.loads(data)
                    if msg.get('type') == 'get_queue_list':
                        business_id = msg.get('business_id')
                        if business_id:
                            queues = db_manager.get_queue_list([str(business_id)], 'waiting')
                            for queue in queues:
                                if 'create_time' in queue and queue['create_time']:
                                    queue['create_time'] = queue['create_time'].strftime(
                                        "%Y-%m-%d %H:%M:%S") if isinstance(queue['create_time'], datetime) else queue[
                                        'create_time']
                            await websocket.send_json({
                                'type': 'queue_list',
                                'data': {
                                    'business_id': business_id,
                                    'business_type': BUSINESS_TYPES[business_id]['type'],
                                    'queues': queues
                                }
                            })
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        manager.disconnect_window(websocket, window_id)
        logger.warning(f"窗口 {window_id} WebSocket连接断开")
    except Exception as e:
        logger.warning(f"窗口 {window_id} WebSocket错误: {e}")
        manager.disconnect_window(websocket, window_id)


"""取药页面WebSocket连接"""
@mz_router.websocket("/ws/pharmacy")
async def websocket_pharmacy(websocket: WebSocket):
    await manager.connect_pharmacy(websocket)
    try:

        init_data = {'type': 'init'}
        await websocket.send_text(json.dumps(init_data, cls=DateTimeEncoder))

        while True:
            # 保持连接，接收心跳
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
            elif data == 'get_status':
                await websocket.send_text(json.dumps({'type': 'pharmacy_update'}, cls=DateTimeEncoder))

    except WebSocketDisconnect:
        manager.disconnect_pharmacy(websocket)
        logger.warning("取药WebSocket连接断开")
    except Exception as e:
        logger.warning(f"取药WebSocket错误: {e}")
        manager.disconnect_pharmacy(websocket)


# =================================================================================================================
# ============================================== 阿里云大模型 实时转写 ==============================================
# =================================================================================================================

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)
INDICATOR_TASK_KEY = 'pacs_indicator_task'
INDICATOR_TASK_RUNNING_KEY = 'pacs_indicator_task_running'

REPORT_TASK_KEY = 'pacs_report_task'
REPORT_TASK_RUNNING_KEY = 'pacs_report_task_running'

API_KEY = "sk-1d02e5ab8bc5420aa4c6c7d2ac9464dd"
WORKSPACE_ID = "ws-nzup4ofn31zrv9f9"
ASR_WS_URL = (
    f"wss://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime"
    "?model=qwen-audio-3.0-realtime-flash"
)

# 模版和词条 key
PACS_TEMPLATE_KEY = "pacs_template"
PACS_ENTRY_KEY = "pacs_entry"


@mz_router.websocket("/asr/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    logger.info("✅ 前端 WebSocket 连接已建立")

    asr_ws = None
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        asr_ws = await websockets.connect(
            ASR_WS_URL,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=60,
        )
        logger.info("✅ 已连接到阿里云 ASR 服务")

        # 发送会话配置
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 800,
                },
                "input_audio_format": "pcm",
                "output_audio_format": "pcm",
                "instructions": (
                    "你是一个专业的医疗语音转写助手。请准确识别医生口述的内容，输出时，请尽量保持句子连贯，并使用句号、逗号等标点分隔，使文本自然流畅。"
                ),
            },
        }
        await asr_ws.send(json.dumps(session_config))
        logger.debug("📋 已发送会话配置")

        async def safe_send(message: dict):
            """安全发送消息，忽略连接已关闭的错误"""
            try:
                # 检查 WebSocket 状态（如果 starlette 提供 client_state）
                if hasattr(websocket, 'client_state') and websocket.client_state.value != 1:
                    return
                await websocket.send_text(json.dumps(message))
            except (WebSocketDisconnect, RuntimeError, Exception) as e:
                logger.debug(f"发送消息失败（连接可能已关闭）: {e}")

        # ---------- 消息转发函数 ----------
        async def forward_to_frontend():
            """ASR → 前端（全量使用 json.dumps）"""
            try:
                async for message in asr_ws:
                    try:
                        event = json.loads(message)
                        if not isinstance(event, dict):
                            continue

                        event_type = event.get("type", "")
                        logger.debug(f"📨 ASR 事件 {event_type}: {event}")

                        # ---- 实时增量（逐字） ----
                        if event_type == "response.text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                await safe_send({"type": "stash", "text": delta})
                                logger.debug(f"↗️ delta: {delta}")

                        # ---- 最终完整文本（途径1） ----
                        elif event_type == "response.text.done":
                            text = event.get("text", "")
                            if text:
                                await safe_send({"type": "final", "text": text})
                                logger.debug(f"📝 final (text.done): {text[:50]}...")

                        # ---- 另一种中间结果（可能包含 stash） ----
                        elif event_type == "conversation.item.input_audio_transcription.delta":
                            stash = event.get("stash", "")
                            if stash:
                                await safe_send({"type": "stash", "text": stash})

                        # ---- 语音开始 / 停止 ----
                        elif event_type == "input_audio_buffer.speech_started":
                            await safe_send({"type": "speech_start"})
                            logger.debug("🎤 语音开始")

                        elif event_type == "input_audio_buffer.speech_stopped":
                            await safe_send({"type": "speech_stop"})
                            logger.debug("🔇 语音结束")

                            # ---- 识别完成辅助信号（不携带文本） ----
                        elif event_type == "conversation.item.input_audio_transcription.completed":
                            # 仅发送状态，不发送文本
                            await safe_send({"type": "transcription_completed"})
                            logger.debug("✅ 识别任务完成")

                        # ---- 错误事件 ----
                        elif event_type == "error":
                            error_obj = event.get("error")
                            if isinstance(error_obj, dict):
                                err_text = error_obj.get("message", "未知错误")
                            else:
                                err_text = str(error_obj) if error_obj else "未知错误"
                            logger.error(f"❌ ASR 错误: {err_text}")
                            await safe_send({"type": "error", "text": f"ASR 错误: {err_text}"})
                    except Exception as e:
                        logger.error(f"处理单条消息异常: {e}")

            except websockets.exceptions.ConnectionClosed as e:
                logger.debug(f"ASR 连接关闭: {e}")
                try:
                    await websocket.close(code=1000, reason="ASR 断开")
                except:
                    pass
            except Exception as e:
                logger.error(f"转发主循环异常: {e}")
                try:
                    await websocket.close(code=1011, reason="内部错误")
                except:
                    pass

        async def forward_to_asr():
            """前端 → ASR（音频流）"""
            try:
                while True:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    msg_type = data.get("type")

                    if msg_type == "audio":
                        audio_b64 = data.get("data", "")
                        if audio_b64:
                            await asr_ws.send(
                                json.dumps({"type": "input_audio_buffer.append", "audio": audio_b64})
                            )
                    elif msg_type == "commit":
                        await asr_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    elif msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                logger.debug("前端 WebSocket 断开")
                # 可选：主动关闭 ASR 连接
                try:
                    await asr_ws.close()
                except:
                    pass
            except Exception as e:
                logger.error(f"音频转发异常: {e}")

        import asyncio
        # 并发执行双向转发
        await asyncio.gather(
            forward_to_frontend(),
            forward_to_asr(),
            return_exceptions=True
        )

    except Exception as e:
        logger.error(f"WebSocket 处理异常: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "text": f"服务异常: {e}"}))
        except:
            pass
    finally:
        if asr_ws:
            await asr_ws.close()
        try:
            await websocket.close()
        except:
            pass
        logger.info("🔌 连接已关闭")


"""根据住院号 / 患者类型（住院/门诊）查询患者信息"""
@mz_router.get("/asr/patient_pacs_info/{zhuyuanhao}/{patient_type}/{check_type}")
async def patient_pacs_info(zhuyuanhao: str, patient_type: str, check_type: str):
    patient_type_str = "住院患者"
    if patient_type == "inpatient":
        sql = f"""select zb.bingrenzyid, zb.zhuyuanhao, zb.xingming patient_name, zb.nianling patient_age, 
        zb.xingbiemc patient_sex, yb.yizhuid, yb.kaizhuksmc dept_name, yb.kaizhuksid dept_id, yb.kaizhuysxm,
        to_char(yb.kaizhusj,'yyyy-mm-dd hh24:mi:ss') kaizhusj, to_char(yb.kaishisj,'yyyy-mm-dd hh24:mi:ss') kaishisj,
        yb.yizhumc check_item ,yb.shenqingdanzt ,lj.jianchabzfl, case when yb.shenqingdanzt>=580 then 1 else 0 end as status from df_jj_zhuyuan.zy_bingrenxx zb
        join df_lc_zhuyuan.yz_bingrenyz yb on yb.bingrenzyid = zb.bingrenzyid and yb.yizhufl = '23' and yb.yizhuzt in (2,3,4) 
        and yb.yizhumc not like '%加收%' and yb.shenqingdanzt  not in (501,502)
        -- and yb.shenqingdanzt <560   --查询未出报告
        and yb.kaishisj>=current_date - interval '10 day'  --查询最近10天所有的
        join df_shenqingdan.yj_jianchasqdxm yj   on yb.yizhuid=yj.yizhubh 
        join df_zhushuju.lcgy_jianchaxm lj on lj.jianchaxmid= yj.jianchaxmid 
        where zb.zaiyuanzt=0 and zb.xingming not like '%测试%' and zb.zhuyuanhao = '{zhuyuanhao}' order by yb.kaishisj desc """
        patient_type_str = "住院患者"
    elif patient_type == "outpatient":
        sql = f""" select zb.jiuzhenid, zb.jiuzhenkh zhuyuanhao, zb.xingming patient_name, zb.nianling patient_age, 
            zb.xingbiemc patient_sex, yb.yizhuid, yb.kaidanksmc dept_name, yb.kaidanks dept_id, yb.kaidanysxm,
            to_char(yb.kaidanrq,'yyyy-mm-dd hh24:mi:ss') kaizhusj, to_char(yb.kaishisj,'yyyy-mm-dd hh24:mi:ss') kaishisj,
            yb.yizhumc check_item ,yb.shenqingdanzt ,lj.jianchabzfl, case when yb.shenqingdanzt>=580 then 1 else 0 end as status 
            from df_lc_menzhen.zj_jiuzhenxx zb
            join df_lc_menzhen.mz_yizhu yb on yb.jiuzhenid = zb.jiuzhenid and yb.yizhulx = '23'
            and yb.yizhumc not like '%加收%' and yb.shenqingdanzt  not in (501,502)
            -- and yb.shenqingdanzt <560   --查询未出报告
            and yb.kaishisj>=current_date - interval '10 day'  --查询最近10天所有的
            join df_shenqingdan.yj_jianchasqdxm yj   on yb.yizhuid=yj.yizhubh 
            join df_zhushuju.lcgy_jianchaxm lj on lj.jianchaxmid= yj.jianchaxmid 
            where  zb.xingming not like '%测试%' and zb.jiuzhenrq>=current_date-1
            and zb.jiuzhenkh = '{zhuyuanhao}' order by yb.kaishisj desc """
        patient_type_str = "门诊患者"
    elif patient_type == "tijian":
        sql = f"""
            select t7.DJLSH zhuyuanhao, t7.XM patient_name, case when t7.xb = 1 then '男' else '女' end  patient_sex,
           t7.nl  patient_age, '体检科' dept_name, '207' dept_id,  ZHXM.MC check_item,
           convert( varchar(19),t7.tjrq,120 ) kaizhusj,
           convert( varchar(19),t7.tjrq,120 ) kaishisj,
           'tj_' + cast( JLB.xh as varchar(10) )  yizhuid,
           rtrim( ZHXM.GNLX )  jianchabzfl,
           rtrim( JLB.TJXMBH )  TJXMBH,
           case when JLB.xj is not null or JLB.JCSJ is not null then 1 else 0 end status
            from futian_user.TJ_TJJLB   JLB
            join futian_user.TJ_TJDJB   t7 on JLB.TJBH = t7.TJBH and JLB.TJCS = t7.TJCS
         JOIN futian_user.TJ_ZHXM_HD AS ZHXM ON JLB.TJXMBH = ZHXM.BH
         left join futian_user.TJ_TJJLMXB AS MXB ON JLB.XH = MXB.XH
        where (t7.DJLSH = '{zhuyuanhao}' or t7.TJBH = '{zhuyuanhao}')  and JLB.LXBH in (select tmp.LXBH from futian_user.TJ_TJLXB tmp where tmp.JCJYLX = 2)
        """
        patient_type_str = "体检患者"

    if patient_type == "tijian":
        patients_info = global_tools.call_tijian_query(sql)
    else:
        patients_info = db_manager.pg_query(sql)
    if not patients_info:
        return {}
    info = {
            "zhuyuanhao": patients_info[0].get("zhuyuanhao", ''),
            "patient_name": patients_info[0]["patient_name"],
            "patient_age": patients_info[0]["patient_age"],
            "patient_sex": patients_info[0]["patient_sex"],
            "dept_id": patients_info[0]["dept_id"],
            "dept_name": patients_info[0]["dept_name"],
            "patient_type": patient_type_str,
        }

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        sql = f"""select id, check_items, patient_info from nsyy_gyl.pacs_ai_report where zhuyuanhao = '{zhuyuanhao}'"""
        records = db.query_all(sql)

    record_dict = {}
    if records:
        record_dict = {record["check_items"]: record for record in records}

    check_items_list = []
    for item in patients_info:
        if item.get('jianchabzfl') and item["jianchabzfl"] != check_type:
            continue
        check_items_list.append({
            "yizhuid": item["yizhuid"],
            'check_item': item["check_item"],
            'kaizhusj': item["kaizhusj"],
            'kaishisj': item["kaishisj"],
            "jianchabzfl": item["jianchabzfl"],
            'status': item["status"],  # 0: 未做, 1: 已做
            "report_id": record_dict.get(item["check_item"], {}).get('id', 0),
            "patient_info": record_dict.get(item["check_item"], {}).get('patient_info', '')
        })
    info['check_items_list'] = check_items_list

    return info



""" 提交 ai报告申请 """
@mz_router.post("/asr/pacs-submit")
async def pacs_submit(request: AsrSubmitRequest):
    check_items = request.check_items
    if not check_items:
        return {"success": False, "message": "请选择检查项目"}
    check_items = check_items.split(",")
    check_items = [item for item in check_items if item and not item.__contains__('加收')]
    if not check_items:
        return {"success": False, "message": "没有需要ai处理的检查项目"}

    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        args = []
        patient_type = "住院患者" if request.patient_type == 'inpatient' else '门诊患者'
        patient_info = request.patient_info
        if not (patient_info.__contains__('患者性别') and patient_info.__contains__('患者年龄')):
            patient_info = f"{request.patient_info}, 患者性别: {request.patient_sex}, 患者年龄: {request.patient_age}"
        for item in check_items:
            args.append((request.zhuyuanhao, request.patient_name, request.patient_age, request.patient_sex, request.dept_id,
                    request.dept_name, request.yizhuid, item, submit_time, patient_info, patient_type))
        insert_sql = """INSERT INTO nsyy_gyl.pacs_ai_report (zhuyuanhao, patient_name, patient_age, patient_sex, 
                        dept_id, dept_name, yizhuid, check_items, submit_time, patient_info, patient_type) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        db.execute_many(insert_sql, args, need_commit=True)

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.set(INDICATOR_TASK_KEY, 1)
    redis_client.set(REPORT_TASK_KEY, 1)
    return {'success': True}


""" 查询提交的ai报告列表 """
@mz_router.get("/asr/pacs_ai_reports")
async def pacs_ai_reports(page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)):

    offset = (page - 1) * page_size
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 1️⃣ 查总数
        total_row = db.query_one("""SELECT COUNT(*) AS total FROM nsyy_gyl.pacs_ai_report""")
        total = total_row['total'] if total_row else 0

        # 2️⃣ 查分页数据（列表页不查 LONGTEXT）
        list_sql = f"""
            SELECT id, zhuyuanhao, patient_name, patient_type, patient_age, patient_sex, dept_name, check_items, patient_info, indicator_data, indicator_status, 
            submit_time, IF(ai_report IS NULL, 0, 1) AS report_status FROM nsyy_gyl.pacs_ai_report ORDER BY id DESC LIMIT {page_size} OFFSET {offset}
        """
        rows = db.query_all(list_sql)
        for row in rows:
            if row['submit_time']:
                row['submit_time'] = row['submit_time'].strftime("%Y-%m-%d %H:%M:%S")

    return {
        "success": True,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "data": rows
    }


""" 查询某一个ai报告 """
@mz_router.get("/asr/pacs_ai_report/{report_id}")
async def pacs_ai_report(report_id: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        record = db.query_one(f"""SELECT * FROM nsyy_gyl.pacs_ai_report where id = {report_id}""")

    if not record:
        raise HTTPException(status_code=404, detail="报告记录不存在")

    indicator_data = record.get('indicator_data')
    if indicator_data:
        try:
            indicator_data = json.loads(indicator_data)
            # 如果是心脏类的检查，将指标以表格的样式放到报告最上方
            for item in ['室壁运动分析', '左心功能测定', '心包', '心脏彩色多普勒超声', '心脏彩色多普勒超声（经胸）', '经颅多普勒超声发泡试验']:
                if item in record.get('check_items', ''):
                    indicator_data = xinzang_zhibiao(indicator_data)
                    break
        except Exception:
            pass
    ai_report = record.get('ai_report')
    if ai_report:
        try:
            ai_report = json.loads(ai_report)
        except Exception:
            ai_report = {}
    else:
        ai_report = {}

    return {
        "success": True,
        "report": {
            "seen": ai_report.get('seen', ''),
            "prompt": ai_report.get('prompt', ''),
            "indicator_data": indicator_data
        }
    }


"""
更新患者信息或指标数据
- 支持单独更新 patient_info 或 indicator_data
- 若两个字段都提供则同时更新
"""
@mz_router.put("/asr/pacs_ai_report/{report_id}")
async def update_pacs_report(report_id: int, request: UpdateReportRequest):
    # 1. 查询记录是否存在
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        report = db.query_one(f"""SELECT id FROM nsyy_gyl.pacs_ai_report where id = {report_id}""")
    if not report:
        raise HTTPException(status_code=404, detail="报告记录不存在")

    # 2. 构建更新字段
    if request.patient_info is None and request.indicator_data is None:
        raise HTTPException(status_code=400, detail="至少提供一个字段进行更新")

    # 3. 执行更新
    try:
        if request.patient_info is not None:
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                        global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                db.execute(f"""update nsyy_gyl.pacs_ai_report set patient_info = %s where id = %s""",
                                    (request.patient_info, report_id), need_commit=True)

        if request.indicator_data is not None:
            indicator_data = request.indicator_data
            if isinstance(indicator_data, dict):
                indicator_data = json.dumps(indicator_data)
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                        global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                db.execute(f"""update nsyy_gyl.pacs_ai_report set indicator_data = %s, indicator_status = 1 
                                where id = %s""",(indicator_data, report_id), need_commit=True)
        # 如果是重新编辑，清空指标和报告重新生成
        if request.re_edit:
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                        global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                db.execute(f"""update nsyy_gyl.pacs_ai_report set ai_report = NULL, indicator_data = NULL, 
                                indicator_status = 0 where id = %s""", (report_id, ), need_commit=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

    # 4. 返回成功响应（可选返回更新后的记录）
    return {
        "code": 200,
        "success": True,
        "message": "更新成功"
    }


"""根据检查项目 获取ai提示词"""
def get_pacs_ai_prompt(check_items):
    param = {
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "type": "get_rpt_templ",
        "rpt_name": check_items
    }

    # 动态 URL
    query_url = "http://192.168.124.53:6080/chaosheng_bingli" if global_config.run_in_local else "http://127.0.0.1:6080/chaosheng_bingli"
    data = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            response = requests.post(query_url, json=param, timeout=30)
            # 检查 HTTP 状态码
            response.raise_for_status()
            result = response.json()
            data = result.get('data', {})
            return data
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                time.sleep(sleep_time)
            else:
                logger.error(f"get_pacs_ai_prompt 已达最大重试次数 {max_retries}。最后错误: {str(e)}")
                return []


"""异步执行所有 指标任务"""
def pacs_indicator_data_task():
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists(INDICATOR_TASK_KEY):
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            records = db.query_one(f"select count(*) from nsyy_gyl.pacs_ai_report "
                                  f"where indicator_data is null OR CHAR_LENGTH(indicator_data) < 10")
            if not records or records['count(*)'] == 0:
                logger.debug("没有需要执行的指标任务")
                return
    if redis_client.exists(INDICATOR_TASK_RUNNING_KEY):
        logger.info("有正在执行的指标任务")
        return

    while True:
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            records = db.query_all(f"select id, check_items, patient_info from nsyy_gyl.pacs_ai_report "
                                  f"where indicator_data is null OR CHAR_LENGTH(indicator_data) < 10 order by submit_time limit 5")

        if not records:
            logger.info("所有指标任务均已执行完成")
            redis_client.delete(INDICATOR_TASK_KEY)
            redis_client.delete(INDICATOR_TASK_RUNNING_KEY)
            return
        for record in records:
            logger.info(f"开始执行指标任务:report id {record.get('id', '')}")
            # 添加运行标识
            redis_client.set(INDICATOR_TASK_RUNNING_KEY, record.get('id'))
            try:
                # 获取ai提示词
                check_item = record.get("check_items")
                text = get_pacs_ai_prompt([check_item])
                if not text:
                    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                        db.execute(f"""update nsyy_gyl.pacs_ai_report set indicator_data = '该检查项目没有ai提示词', 
                        indicator_status = 1 where id = {record.get('id')} """, need_commit=True)
                    continue

                patient_info = record.get("patient_info")
                text = text.get(check_item, "") + patient_info

                start_time = time.time()
                is_json_bool = False

                # 模版二 心脏
                for item in ['室壁运动分析', '左心功能测定', '心包', '心脏彩色多普勒超声', '心脏彩色多普勒超声（经胸）']:
                    if item in record.get('check_items', ''):
                        is_json_bool = True
                # 模版一 脑-颈部血管
                for item in ['双侧锁骨下静脉', '双侧颈内静脉', '双侧颈动脉、椎动脉、锁骨下动脉', '多普勒检查', '心脏彩色多普勒超声（经胸）', '经颅多普勒超声发泡试验']:
                    if item in record.get('check_items', ''):
                        is_json_bool = True
                # 模版三 甲状腺及颈部淋巴结
                for item in ['颈部淋巴结', '甲状腺及颈部淋巴结']:
                    if item in record.get('check_items', ''):
                        is_json_bool = True
                # 模版四 常规腹部脏器
                for item in ['腹部脏器（肝、胆、胰、脾）', '腹膜后（腹膜后淋巴结、肾上腺）', '腹腔淋巴结', '腹水', '胸水', '疝']:
                    if item in record.get('check_items', ''):
                        is_json_bool = True

                ai_indicator = ai_tool.call_ai_for_patient(text, is_json=is_json_bool)
                indicator_status = ", indicator_status = 1"
                try:
                    if isinstance(ai_indicator, dict):
                        for item in ai_indicator:
                            if not item.get('value', ''):
                                indicator_status = ""
                                break
                    ai_indicator = json.dumps(ai_indicator, ensure_ascii=False, default=str)
                except Exception:
                    pass
                logging.info(f"pacs 指标任务 {record.get('id')} - 耗时: {time.time() - start_time}")
                with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                            global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                    db.execute(f""" update nsyy_gyl.pacs_ai_report set indicator_data = %s {indicator_status} where id = %s """,
                                        (ai_indicator, record.get('id')), need_commit=True)

            except Exception as e:
                logger.error(f"pacs 指标任务 - 异常: {e.__str__()}")


def xinzang_zhibiao(ai_indicator):
    def pad_by_visual(text, target_width):
        # 使用 GBK 编码计算视觉宽度（终端通常如此）
        visual_len = len(text.encode('gbk', errors='ignore'))
        if visual_len >= target_width:
            return text
        return text + ' ' * (target_width - visual_len)

    try:
        str_d = {}
        for item in ai_indicator:
            if item.get('value'):
                str_d[item.get('name')] = f"{item.get('value')} {item.get('unit')} {item.get('abnormal')}" if item.get('abnormal') and item.get('abnormal', '') not in ['null', "None"] else f"{item.get('value')} {item.get('unit')}"

        str_f = ''
        # 设定第一列视觉宽度为 22，第二列视觉宽度为 12，第三列视觉宽度为 22（可根据数据调整）、
        str_f += pad_by_visual("左房前后径[25-40]", 23) + pad_by_visual(f"{str_d.get('左房前后径')}", 15) + pad_by_visual(
            "左房容积", 23) + f"{str_d.get('左房容积')} \n"
        str_f += pad_by_visual("右室前后径[16-30]", 23) + pad_by_visual(f"{str_d.get('右室前后径')}", 15) + pad_by_visual(
            "主动脉瓣环", 23) + f"{str_d.get('主动脉瓣环')} \n"
        str_f += pad_by_visual("主肺动脉径[16-30]", 23) + pad_by_visual(f"{str_d.get('主肺动脉径')}", 15) + pad_by_visual(
            "左室后壁厚度", 23) + f"{str_d.get('左室后壁厚度')} \n"
        str_f += pad_by_visual("室间隔厚度[8-12]", 23) + pad_by_visual(f"{str_d.get('室间隔厚度')}", 15) + pad_by_visual(
            "升主动脉内径", 23) + f"{str_d.get('升主动脉内径')} \n"
        str_f += pad_by_visual("运动幅度-左室后壁", 23) + pad_by_visual(f"{str_d.get('运动幅度-左室后壁')}", 15) + pad_by_visual(
            "左室舒张期内径", 23) + f"{str_d.get('左室舒张期内径')} \n"
        str_f += pad_by_visual("运动幅度-室间隔", 23) + pad_by_visual(f"{str_d.get('运动幅度-室间隔')}", 15) + pad_by_visual(
            "左室收缩期内径", 23) + f"{str_d.get('左室收缩期内径')} \n"

        str_f += pad_by_visual("左室舒张期容积", 23) + pad_by_visual(f"{str_d.get('左室舒张期容积')}", 15) + pad_by_visual(
            "即时心率", 23) + f"{str_d.get('即时心率')} \n"
        str_f += pad_by_visual("左室收缩期容积", 23) + pad_by_visual(f"{str_d.get('左室收缩期容积')}", 15) + pad_by_visual(
            "每搏输出量", 23) + f"{str_d.get('每搏输出量')} \n"
        str_f += pad_by_visual("左室射血分数[50-80]", 23) + pad_by_visual(f"{str_d.get('左室射血分数')}", 15) + pad_by_visual(
            "每分钟输出量", 23) + f"{str_d.get('每分钟输出量')} \n"
        str_f += pad_by_visual("左室短轴缩短率", 23) + pad_by_visual(f"{str_d.get('左室短轴缩短率')}", 15) + '\n'

        # 血液流动与瓣膜
        str_f += pad_by_visual("二尖瓣环间隔测", 23) + pad_by_visual(f"{str_d.get('二尖瓣环间隔测')}", 15) + pad_by_visual(
            "二尖瓣A峰", 23) + f"{str_d.get('二尖瓣A峰')} \n"
        str_f += pad_by_visual("二尖瓣环侧隔测", 23) + pad_by_visual(f"{str_d.get('二尖瓣环侧隔测')}", 15) + pad_by_visual(
            "二尖瓣E峰", 23) + f"{str_d.get('二尖瓣E峰')} \n"
        str_f += pad_by_visual("三尖瓣反流流速", 23) + pad_by_visual(f"{str_d.get('三尖瓣反流流速')}", 15) + pad_by_visual(
            "E/e", 23) + f"{str_d.get('E/e')} \n"
        str_f += pad_by_visual("肺动脉流速", 23) + pad_by_visual(f"{str_d.get('肺动脉流速')}", 15) + pad_by_visual(
            "主动脉流速", 23) + f"{str_d.get('主动脉流速')} \n"
        str_f += pad_by_visual("估测肺动脉压约", 23) + pad_by_visual(f"{str_d.get('估测肺动脉压约')}", 15) + pad_by_visual(
            "压力阶差", 23) + f"{str_d.get('压力阶差')} \n\n"

    except Exception:
        logger.error("指标数据解析异常")
        pass
    return str_f.replace('None', ' ')


def pacs_auto_report_task():
    """异步执行所有 自动生成报告任务"""
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists(REPORT_TASK_KEY):
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            records = db.query_one(f"select count(*) from nsyy_gyl.pacs_ai_report "
                                   f"where ai_report is null OR CHAR_LENGTH(ai_report) < 10")
            if not records or records['count(*)'] == 0:
                logger.debug("没有需要执行的报告生成任务")
                return
    if redis_client.exists(REPORT_TASK_RUNNING_KEY):
        logger.info("有正在执行的 pacs auto report 任务")
        return

    while True:
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            records = db.query_all(f"select id, patient_age, patient_sex, check_items, patient_info from nsyy_gyl.pacs_ai_report "
                                  f"where (ai_report is null OR CHAR_LENGTH(ai_report) < 10) order by submit_time limit 5")

        if not records:
            logger.info("所有 pacs auto report 任务均已执行完成")
            redis_client.delete(REPORT_TASK_KEY)
            redis_client.delete(REPORT_TASK_RUNNING_KEY)
            return
        for record in records:
            logger.info(f"开始执行 pacs auto report 任务:report id {record.get('id', '')}")
            # 添加运行标识
            redis_client.set(REPORT_TASK_RUNNING_KEY, record.get('id'))
            try:
                prompt_template = """
                你是一名专业超声科报告生成助手。请严格根据以下信息生成一份规范的超声检查报告。

                【检查项目】
                {check_items}
                
                【患者信息】
                性别：{sex}
                年龄：{age}
                
                【报告模板】
                {template}
                
                【词条映射表】
                {terms_json}
                
                【医生口述】
                {oral_text}
                
                生成规则：
                1. 只输出一个 JSON 对象，格式为：{{"seen":"超声所见内容","prompt":"超声提示内容"}}。
                   不要输出 Markdown、代码块、解释文字，不要用数组包裹。
                2. “超声所见”以【报告模板】中的“检查所见模板”为骨架。 模板中正常描述默认保留；仅口述中的异常发现替换或追加到对应部位。正常测值不追加。
                   若口述中匹配到【词条映射表】中的异常词条，则将该词条的 "seen" 追加到超声所见中，将该词条的 "prompt" 追加到超声提示中，。
                3. 数据填充：
                   - 口述中有单位则保留原单位；无单位时按词条默认单位（如 mm）。
                   - 口述中的“乘以”“x”“X”“*”统一转为“×”。
                   - 若未提取到数据，不要编造，可省略该数值。
                4. 口述中未提及的器官，一律按模板正常描述输出。 口述与模板正常描述冲突时，以口述和词条为准。
                5. “超声所见”只写客观描述，不写诊断结论。诊断性描述只能出现在“超声提示”中。 禁止按口述顺序罗列数据。正常功能只写“xxx功能正常”，不列具体数值。
                6. “超声提示”总结所有异常诊断，按临床重要性排序，与“所见”呼应，不重复具体数值，除非词条模板要求。
                7. 口述中可能含有口语，请转换为专业术语，但必须保留所有异常数据。
                8. 不要添加口述和词条中不存在的异常发现。
                9. 若同一器官有多个异常，合并描述，避免重复。
                10. 若模板中有未填充的占位符（如“大小约mmxmm”），且口述未提供数据，则替换为“大小未见明显异常”或删除该数值描述，保持语句通顺。
                11. 超声所见不要堆砌检查数据，有模版的话以模版为骨架进行完善，没有模版的话 尽量是总结性的描述
                """

                report_template, template_id = get_pacs_templates(record['check_items'])
                terms = get_pacs_entrys(template_id)

                prompt = prompt_template.format(
                    check_items=record['check_items'],
                    sex=record['patient_sex'],
                    age=record['patient_age'],
                    template=report_template,
                    terms_json=json.dumps(terms, ensure_ascii=False) if terms else '',
                    oral_text=record['patient_info']
                )

                start_time = time.time()
                ai_report = ai_tool.call_ai_for_patient(prompt, is_json=True)
                try:
                    if isinstance(ai_report, dict):
                        ai_report = json.dumps(ai_report, ensure_ascii=False, default=str)
                except Exception:
                    pass
                logging.info(f"pacs auto report 任务 {record.get('id')} - 耗时: {time.time() - start_time}")

                with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                            global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                    db.execute(""" update nsyy_gyl.pacs_ai_report set ai_report = %s where id = %s """,
                                        (ai_report, record.get('id')), need_commit=True)

            except Exception as e:
                logger.error(f"pacs auto report 任务 - 异常: {e.__str__()}")



# =========================================================================================================
# =================================== 模板与词条管理模块（独立，不影响主功能） ===================================
# =========================================================================================================


""" 查询pacs 检查项目报告模版 """
@mz_router.get("/asr/pacs_report_template")
async def pacs_report_template(page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), keyword: str = ''):

    offset = (page - 1) * page_size
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        where_str = '' if not keyword else f"where check_item like '%{keyword}%'"
        # 1️⃣ 查总数
        total_row = db.query_one(f"""SELECT COUNT(*) AS total FROM nsyy_gyl.pacs_report_template {where_str}""")
        total = total_row['total'] if total_row else 0

        # 2️⃣ 查分页数据（列表页不查 LONGTEXT）
        list_sql = f""" SELECT * FROM nsyy_gyl.pacs_report_template {where_str} 
        ORDER BY id DESC LIMIT {page_size} OFFSET {offset} """
        rows = db.query_all(list_sql)
    return {
        "success": True,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "data": rows
    }


# ---------- 2. 查询单条（前端"编辑"回显备用） ----------
@mz_router.get("/asr/pacs_report_template/{tid}")
async def get_pacs_report_template(tid: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT * FROM nsyy_gyl.pacs_report_template WHERE id = {tid}")
    if not row:
        return {"success": False, "message": f"模板 #{tid} 不存在"}
    return {"success": True, "data": row}


# ---------- 3. 新增模板 ----------
@mz_router.post("/asr/pacs_report_template")
async def create_pacs_report_template(body: TemplateBody):
    if not body.check_item or not body.check_item.strip():
        return {"success": False, "message": "check_item 不能为空"}

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 检查重名（同一检查项目不允许重复）
        exists = db.query_one(
            "SELECT id FROM nsyy_gyl.pacs_report_template WHERE check_item = %s LIMIT 1",
            (body.check_item.strip(),)
        )
        if exists:
            return {"success": False, "message": f"检查项目【{body.check_item}】已存在"}

        insert_sql = """
            INSERT INTO nsyy_gyl.pacs_report_template (check_item, report_template, group_id)
            VALUES (%s, %s, %s)
        """
        new_id = db.execute(insert_sql, (
            body.check_item.strip(),
            body.report_template or '',
            body.group_id if body.group_id is not None else -1
        ), need_commit=True)

    cache_pacs_template(cache_template=True, cache_entry=False)
    return {"success": True, "message": "创建成功", "id": new_id}


# ---------- 4. 更新模板 ----------
@mz_router.put("/asr/pacs_report_template/{tid}")
async def update_pacs_report_template(tid: int, body: TemplateBody):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT id FROM nsyy_gyl.pacs_report_template WHERE id = {tid}")
        if not row:
            return {"success": False, "message": f"模板 #{tid} 不存在"}

        update_sql = """
            UPDATE nsyy_gyl.pacs_report_template
            SET check_item = %s, report_template = %s, group_id = %s
            WHERE id = %s
        """
        db.execute(update_sql, (
            body.check_item.strip(),
            body.report_template or '',
            body.group_id if body.group_id is not None else -1,
            tid
        ), need_commit=True)

    cache_pacs_template(cache_template=True, cache_entry=False)
    return {"success": True, "message": "更新成功", "id": tid}

# ---------- 5. 删除模板 ----------
@mz_router.delete("/asr/pacs_report_template/{tid}")
async def delete_pacs_report_template(tid: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT id FROM nsyy_gyl.pacs_report_template WHERE id = {tid}")
        if not row:
            return {"success": False, "message": f"模板 #{tid} 不存在"}

        db.execute(f"DELETE FROM nsyy_gyl.pacs_report_template WHERE id = {tid}", need_commit=True)

    cache_pacs_template(cache_template=True, cache_entry=False)
    return {"success": True, "message": "删除成功", "id": tid}




# =========================================================
# 二、报告词条表 pacs_report_entry
# =========================================================

# ---------- 1. 查询列表 ----------
@mz_router.get("/asr/pacs_report_entry")
async def pacs_report_entry_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = '',
    check_item: str = '',
    check_item_id: Optional[int] = None
):
    # 强制 int，保险一层
    page = int(page)
    page_size = int(page_size)
    offset = (page - 1) * page_size

    # 组装 WHERE（多条件）
    conditions = []
    params_list = []

    if keyword:
        like = f"%{keyword}%"
        conditions.append("(keyword LIKE %s OR seen LIKE %s OR prompt LIKE %s)")
        params_list.extend([like, like, like])

    if check_item:
        conditions.append("check_item = %s")
        params_list.append(check_item)

    if check_item_id is not None:
        conditions.append("check_item_id = %s")
        params_list.append(check_item_id)

    where_str = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        # 1️⃣ 总数
        count_sql = f"SELECT COUNT(*) AS total FROM nsyy_gyl.pacs_report_entry {where_str}"
        if params_list:
            count_row = db.query_one(count_sql, tuple(params_list))
        else:
            count_row = db.query_one(count_sql)
        total = count_row['total'] if count_row else 0

        # 2️⃣ 分页：LIMIT/OFFSET 直接内联整数（已类型校验，安全）
        list_sql = f"""
                    SELECT * FROM nsyy_gyl.pacs_report_entry
                    {where_str}
                    ORDER BY id DESC
                    LIMIT {page_size} OFFSET {offset}
                """
        if params_list:
            rows = db.query_all(list_sql, tuple(params_list))
        else:
            rows = db.query_all(list_sql)

    return {
        "success": True,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "data": rows
    }


# ---------- 2. 查询单条 ----------
@mz_router.get("/asr/pacs_report_entry/{eid}")
async def get_pacs_report_entry(eid: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT * FROM nsyy_gyl.pacs_report_entry WHERE id = {eid}")
    if not row:
        return {"success": False, "message": f"词条 #{eid} 不存在"}
    return {"success": True, "data": row}


# ---------- 3. 新增词条 ----------
@mz_router.post("/asr/pacs_report_entry")
async def create_pacs_report_entry(body: EntryBody):
    if not body.keyword or not body.keyword.strip():
        return {"success": False, "message": "keyword 不能为空"}

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 同一检查项目下关键字唯一
        if body.check_item_id is not None:
            exists = db.query_one(
                """SELECT id FROM nsyy_gyl.pacs_report_entry
                   WHERE keyword = %s AND check_item_id = %s LIMIT 1""",
                (body.keyword.strip(), body.check_item_id)
            )
        else:
            exists = db.query_one(
                """SELECT id FROM nsyy_gyl.pacs_report_entry
                   WHERE keyword = %s AND (check_item_id IS NULL OR check_item_id = 0) LIMIT 1""",
                (body.keyword.strip(),)
            )
        if exists:
            return {"success": False,
                    "message": f"该检查项目下关键字【{body.keyword}】已存在"}

        insert_sql = """
            INSERT INTO nsyy_gyl.pacs_report_entry
                (keyword, seen, prompt, check_item_id, check_item)
            VALUES (%s, %s, %s, %s, %s)
        """
        new_id = db.execute(insert_sql, (
            body.keyword.strip(),
            body.seen or '',
            body.prompt or '',
            body.check_item_id,
            body.check_item or ''
        ), need_commit=True)

    cache_pacs_template(cache_template=False, cache_entry=True)
    return {"success": True, "message": "创建成功", "id": new_id}


# ---------- 4. 更新词条 ----------
@mz_router.put("/asr/pacs_report_entry/{eid}")
async def update_pacs_report_entry(eid: int, body: EntryBody):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT id FROM nsyy_gyl.pacs_report_entry WHERE id = {eid}")
        if not row:
            return {"success": False, "message": f"词条 #{eid} 不存在"}

        update_sql = """
            UPDATE nsyy_gyl.pacs_report_entry
            SET keyword = %s, seen = %s, prompt = %s,
                check_item_id = %s, check_item = %s
            WHERE id = %s
        """
        db.execute(update_sql, (
            body.keyword.strip(),
            body.seen or '',
            body.prompt or '',
            body.check_item_id,
            body.check_item or '',
            eid
        ), need_commit=True)

    cache_pacs_template(cache_template=False, cache_entry=True)
    return {"success": True, "message": "更新成功", "id": eid}


# ---------- 5. 删除词条 ----------
@mz_router.delete("/asr/pacs_report_entry/{eid}")
async def delete_pacs_report_entry(eid: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        row = db.query_one(f"SELECT id FROM nsyy_gyl.pacs_report_entry WHERE id = {eid}")
        if not row:
            return {"success": False, "message": f"词条 #{eid} 不存在"}

        db.execute(f"DELETE FROM nsyy_gyl.pacs_report_entry WHERE id = {eid}", need_commit=True)

    cache_pacs_template(cache_template=False, cache_entry=True)
    return {"success": True, "message": "删除成功", "id": eid}


# ---------- 6. 模版列表 ----------
@mz_router.get("/asr/check_item_options")
async def check_item_options(keyword: str = ''):
    """
    返回所有检查项目（来自 pacs_report_template），用于词条表单的下拉选择。
    不分页，一次性返回（检查项目通常不超过几百条）。
    """
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if keyword:
            sql = """
                SELECT id, check_item
                FROM nsyy_gyl.pacs_report_template
                WHERE check_item LIKE %s
                ORDER BY check_item ASC
            """
            rows = db.query_all(sql, (f"%{keyword}%",))
        else:
            sql = """
                SELECT id, check_item
                FROM nsyy_gyl.pacs_report_template
                ORDER BY check_item ASC
            """
            rows = db.query_all(sql)

    return {"success": True, "total": len(rows), "data": rows}

NO_TEMPLATE = ('该检查项目没有固定报告模版，请根据患者情况进行生成', -1)

def get_pacs_templates(check_item: str):
    if not check_item:
        return NO_TEMPLATE

    redis_client = redis.Redis(connection_pool=pool)
    try:
        raw = redis_client.hgetall(PACS_TEMPLATE_KEY)
    finally:
        redis_client.close()          # 归还连接到池，不是关闭池

    import re
    def _norm(s: str) -> str:
        return re.sub(r'[\s()（）、]', '', s or '')
    for field, value in raw.items():
        try:
            tmp = json.loads(value)
            if _norm(tmp.get('check_item')) == _norm(check_item):
                if tmp.get('report_template'):
                    return tmp['report_template'], tmp.get('id')
                return NO_TEMPLATE

        except (json.JSONDecodeError, TypeError):
            logger.warning("模板 %s 反序列化失败，跳过", field)
    return NO_TEMPLATE


def get_pacs_entrys(check_item_id: int):
    if check_item_id <= 0:
        return []
    redis_client = redis.Redis(connection_pool=pool)
    try:
        raw = redis_client.hgetall(PACS_ENTRY_KEY)
    finally:
        redis_client.close()          # 归还连接到池，不是关闭池

    entrys = []
    for field, value in raw.items():
        try:
            entry = json.loads(value)
            if entry['check_item_id'] == check_item_id:
                entrys.append({
                    "triggers": entry['keyword'].split('1'),
                    "prompt": entry.get('prompt', ''),
                    "seen": entry.get('seen', '')
                })
        except (json.JSONDecodeError, TypeError):
            logger.warning("词条 %s 反序列化失败，跳过", field)
    return entrys



def cache_pacs_template(cache_template: bool = False, cache_entry: bool = False):
    redis_client = redis.Redis(connection_pool=pool)
    # 服务启动时 删除运行标识，防止服务异常退出导致运行标识未删除
    redis_client.delete(INDICATOR_TASK_RUNNING_KEY)
    redis_client.delete(REPORT_TASK_RUNNING_KEY)

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if cache_template:
            templates = db.query_all("SELECT * FROM nsyy_gyl.pacs_report_template")
            if templates:
                for item in templates:
                    redis_client.hset(PACS_TEMPLATE_KEY, str(item['id']), json.dumps(item))
        if cache_entry:
            entrys = db.query_all("SELECT * FROM nsyy_gyl.pacs_report_entry")
            if entrys:
                for item in entrys:
                    redis_client.hset(PACS_ENTRY_KEY, str(item['id']), json.dumps(item))

cache_pacs_template(cache_template=True, cache_entry=True)





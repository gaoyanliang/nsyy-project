from fastapi import WebSocket, HTTPException, WebSocketDisconnect, APIRouter
from datetime import datetime, date
import json

import logging

from outpatient_queue.database import DatabaseManager
from outpatient_queue.models import *
from outpatient_queue.websocket_manager import manager
from outpatient_queue.config import BUSINESS_TYPES

logger = logging.getLogger(__name__)
# ====================== 统一添加 /gyl 前缀（使用 APIRouter） ======================
mz_router = APIRouter(prefix="/mz")

db = DatabaseManager()

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
    data = db.get_windows_list()
    data = {item.get('id'): item for item in data}
    return data


"""获取窗口信息"""
@mz_router.get("/windows/{window_id}")
async def get_window_info(window_id: int):
    windows = db.get_windows_list()
    for window in windows:
        if window['id'] == window_id:
            return window
    raise HTTPException(status_code=404, detail="窗口不存在")


"""取号"""
@mz_router.post("/api/take-number")
async def take_number(request: TakeNumberRequest):
    try:
        # 添加患者信息
        db.add_patient( request.patient_id, request.patient_name,
            request.id_card, request.phone)

        # 生成排队号
        queue_number = db.generate_queue_number(request.business_id)
        business_name = BUSINESS_TYPES[request.business_id]['name']
        business_type = BUSINESS_TYPES[request.business_id]['type']

        # 添加到排队记录
        success = db.add_queue_record(
            queue_number, f"{datetime.today().strftime('%Y%m%d')}",
            request.patient_id, request.patient_name, request.business_id, business_type, business_name
        )

        if success:
            # 广播更新
            await manager.broadcast({
                'type': 'queue_update',
                'action': 'new_queue',
                'data': {
                    'queue_number': queue_number,
                    'patient_name': request.patient_name,
                    'business_id': request.business_id,
                    'business_type': business_type,
                    'business_name': business_name,
                    'waiting_count': db.get_waiting_count(request.business_id)
                }
            })

            return {
                'success': True,
                'queue_number': queue_number,
                'business_id': request.business_id,
                'business_type': business_type,
                'business_name': business_name,
                'waiting_count': db.get_waiting_count(request.business_id),
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

    medicines = db.pg_query(sql)
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
    patients_info = db.pg_query(sql)
    return patients_info[0] if patients_info else {}


"""药品缴费"""
@mz_router.post("/api/pay-medicine/{medicine_id}")
async def pay_medicine(medicine_id: int):
    success = db.update_medicine_payment(medicine_id)
    if success:
        return {'success': True, 'message': '缴费成功'}
    else:
        raise HTTPException(status_code=400, detail="缴费失败或已缴费")


"""获取所有业务排队状态"""
@mz_router.get("/api/queue/status")
async def get_queue_status():
    status = db.get_all_business_status()
    current_calls = db.get_current_calls()

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
        'total_waiting': db.get_waiting_count(),
        'avg_wait_time': db.get_avg_wait_time(),
        'today_total': db.get_today_total()
    }


"""获取过号状态"""
@mz_router.get("/api/queue/overdue")
async def get_queue_overdue():
    overdue_queues = db.get_overdue_list()

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
        window_info = db.get_window_info(int(window_id))
        business_ids = window_info['business_sort'].split(',')

    queues = db.get_queue_list(business_ids, status)

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


@mz_router.post("/api/tts_call")
async def call_patient(request: CallRequest):
    # 可以校验窗口是否存在，或直接推送
    window = db.get_window_info(request.window_id)
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
    window = db.get_window_info(request.window_id)
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

    # 获取下一个排队
    next_queue = db.get_next_queue(request.business_type, window['business_sort'])
    if not next_queue:
        return {'success': False, 'message': '没有等待的患者'}

    # 叫号
    success = db.call_queue(next_queue['queue_number'], request.window_id, window['window_name'])

    if success:
        # 转换datetime
        call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 广播叫号信息
        call_data = {
            'queue_number': next_queue['queue_number'],
            'patient_name': next_queue['patient_name'],
            'business_type': next_queue['business_type'],
            'business_name': next_queue['business_name'],
            'window_id': request.window_id,
            'window_name': window['window_name'],
            'call_time': call_time
        }

        await manager.broadcast({
            'type': 'call',
            'data': call_data
        })

        await manager.send_to_window(request.window_id, {
            'type': 'call_success',
            'data': call_data
        })

        return {
            'success': True,
            'queue': next_queue,
            'window': window
        }
    else:
        raise HTTPException(status_code=500, detail="叫号失败")


"""完成服务"""
@mz_router.post("/api/complete")
async def complete_service(request: CompleteRequest):
    success = db.complete_queue(request.queue_number)

    if success:
        await manager.broadcast({
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
    success = db.medicine_complete(request.queue_number, request.status)

    if success:
        await manager.broadcast({
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
    success = db.skip_queue(request.queue_number, request.reason)

    if success:
        await manager.broadcast({
            'type': 'skip',
            'data': {
                'queue_number': request.queue_number,
                'reason': request.reason
            }
        })
        return {'success': True}
    else:
        raise HTTPException(status_code=500, detail="跳过失败")


"""患者重新激活过号的排队（通过重新刷卡/扫码）"""
@mz_router.post("/api/patient/reactivate/{patient_id}/{business_id}")
async def reactivate_patient_queue(patient_id: str, business_id: str):
    try:
        # 查找该患者是否有过号的排队记录（状态为skipped）
        skipped_queue = db.get_patient_skipped_record(patient_id, business_id)
        if not skipped_queue:
            return {
                'success': False,
                'message': '没有找到过号的排队记录',
                'has_skipped': False
            }

        # 重新激活，顺延到当前队列末尾
        # success = db.reactivate_queue(skipped_queue['queue_number'])

        new_queue_number = db.reactivate_queue_defer(
            old_queue_number=skipped_queue['queue_number'],
            patient_id=patient_id,
            patient_name=skipped_queue['patient_name'],
            business_id=skipped_queue['business_id']
        )

        if new_queue_number:
            # 获取更新后的等待人数
            waiting_count = db.get_waiting_count(skipped_queue['business_id'])
            avg_wait_time = db.get_avg_wait_time(skipped_queue['business_id'])
            today_total = db.get_today_total(skipped_queue['business_id'])

            # 广播队列更新
            await manager.broadcast({
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
        skipped_queue = db.get_patient_skipped_record(patient_id, business_id)
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
    await manager.connect(websocket, "display")
    try:
        # 发送初始数据
        status = db.get_all_business_status()
        current_calls = db.get_current_calls()

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
        waiting_queues = db.get_queue_list(status='waiting')
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
                'total_waiting': db.get_waiting_count(),
                'avg_wait_time': db.get_avg_wait_time(),
                'today_total': db.get_today_total()
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
                status = db.get_all_business_status()
                current_calls = db.get_current_calls()
                for call in current_calls:
                    if 'call_time' in call and call['call_time']:
                        call['call_time'] = call['call_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(
                            call['call_time'], datetime) else call['call_time']

                await websocket.send_text(json.dumps({
                    'type': 'status_update',
                    'data': {
                        'business_status': status,
                        'current_calls': current_calls,
                        'total_waiting': db.get_waiting_count(),
                        'avg_wait_time': db.get_avg_wait_time(),
                        'today_total': db.get_today_total()
                    }
                }, cls=DateTimeEncoder))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.warning("大屏WebSocket连接断开")
    except Exception as e:
        logger.warning(f"大屏WebSocket错误: {e}")
        manager.disconnect(websocket)


"""窗口WebSocket连接"""
@mz_router.websocket("/ws/window/{window_id}")
async def websocket_window(websocket: WebSocket, window_id: int):
    await manager.connect(websocket, "window", window_id)
    try:
        logger.debug(f"窗口 {window_id} WebSocket连接成功")

        # 连接成功后发送当前窗口的叫号状态
        # 获取该窗口正在叫号的患者
        current_call = db.get_current_window_calls(window_id)

        # 获取窗口信息
        window_info = db.get_window_info(window_id)

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
                await websocket.send_text('pong')
            elif data == 'get_status':
                # 客户端请求当前窗口状态
                current_call = db.get_current_window_calls(window_id)
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
                            queues = db.get_queue_list([str(business_id)], 'waiting')
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
        manager.disconnect(websocket, window_id)
        logger.warning(f"窗口 {window_id} WebSocket连接断开")
    except Exception as e:
        logger.warning(f"窗口 {window_id} WebSocket错误: {e}")
        manager.disconnect(websocket, window_id)


"""取药页面WebSocket连接"""
@mz_router.websocket("/ws/pharmacy")
async def websocket_pharmacy(websocket: WebSocket):
    await manager.connect(websocket, "pharmacy")
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
        manager.disconnect(websocket)
        logger.warning("取药WebSocket连接断开")
    except Exception as e:
        logger.warning(f"取药WebSocket错误: {e}")
        manager.disconnect(websocket)

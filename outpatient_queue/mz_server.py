from fastapi import WebSocket, HTTPException, WebSocketDisconnect, APIRouter
from datetime import datetime, date
import json

import logging
import websockets

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
            await manager.broadcast_all({
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

        await manager.broadcast_all({
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
    success = db.medicine_complete(request.queue_number, request.status)

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
    success = db.skip_queue(request.queue_number, request.reason)

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
    await manager.connect_display(websocket)
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


API_KEY = "sk-1d02e5ab8bc5420aa4c6c7d2ac9464dd"
WORKSPACE_ID = "ws-nzup4ofn31zrv9f9"
ASR_WS_URL = (
    f"wss://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime"
    "?model=qwen-audio-3.0-realtime-flash"
)


@mz_router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    print('------------')
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
        logger.info("📋 已发送会话配置")

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
                        logger.info(f"📨 ASR 事件 {event_type}: {event}")

                        # ---- 实时增量（逐字） ----
                        if event_type == "response.text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                await websocket.send_text(
                                    json.dumps({"type": "stash", "text": delta})
                                )
                                logger.debug(f"↗️ delta: {delta}")

                        # ---- 最终完整文本（途径1） ----
                        elif event_type == "response.text.done":
                            text = event.get("text", "")
                            if text:
                                await websocket.send_text(
                                    json.dumps({"type": "final", "text": text})
                                )
                                logger.info(f"📝 final (text.done): {text[:50]}...")

                        # # ---- 最终完整文本（途径2） ----
                        # elif event_type == "conversation.item.input_audio_transcription.completed":
                        #     transcript = event.get("transcript", "")
                        #     if transcript:
                        #         await websocket.send_text(
                        #             json.dumps({"type": "final", "text": transcript})
                        #         )
                        #         logger.info(f"📝 final (transcription): {transcript[:50]}...")
                        #
                        # ---- 另一种中间结果（可能包含 stash） ----
                        elif event_type == "conversation.item.input_audio_transcription.delta":
                            stash = event.get("stash", "")
                            if stash:
                                await websocket.send_text(
                                    json.dumps({"type": "stash", "text": stash})
                                )

                        # ---- 语音开始 / 停止 ----
                        elif event_type == "input_audio_buffer.speech_started":
                            await websocket.send_text(json.dumps({"type": "speech_start"}))
                            logger.info("🎤 语音开始")

                        elif event_type == "input_audio_buffer.speech_stopped":
                            await websocket.send_text(json.dumps({"type": "speech_stop"}))
                            logger.info("🔇 语音结束")

                            # ---- 识别完成辅助信号（不携带文本） ----
                        elif event_type == "conversation.item.input_audio_transcription.completed":
                            # 仅发送状态，不发送文本
                            await websocket.send_text(json.dumps({"type": "transcription_completed"}))
                            logger.info("✅ 识别任务完成")

                        # ---- 错误事件 ----
                        elif event_type == "error":
                            error_obj = event.get("error")
                            if isinstance(error_obj, dict):
                                err_text = error_obj.get("message", "未知错误")
                            else:
                                err_text = str(error_obj) if error_obj else "未知错误"
                            logger.error(f"❌ ASR 错误: {err_text}")
                            await websocket.send_text(
                                json.dumps({"type": "error", "text": f"ASR 错误: {err_text}"})
                            )

                    except Exception as e:
                        import traceback
                        logger.error(f"处理单条消息异常: {e}\n{traceback.format_exc()}")

            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"ASR 连接关闭: {e}")
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
                logger.info("前端 WebSocket 断开")
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


@mz_router.post("/api/generate-report")
async def generate_report(request: AsrRequest):
    # 可以校验窗口是否存在，或直接推送
    # data = ai_tool.call_ai_for_patient(request.text)
    data = f"""
        ---
        ## 核心角色与任务设定
        
        你是一名心脏超声质控专家。
        
        你的核心任务为以下工作：
        1. 识别文本中的患者超声测量数值，然后填充到标准表格模版中 （最终返回Markdown表格内容 ）
        2. 基于测量的患者数值，予以患者情况分析，输出超声报告
        
        标准表格模版 - Markdown表格模板（可直接复制到支持Markdown的编辑器）：
        
        ```markdown
        | 项目 | 参考范围 | 检查值 | 状态 |
        |------|----------|--------|------|
        | **一、腔室内径（mm）** | | | |
        | 左房前后径 | 25-40 | ___ | ___ |
        | 左房容积 | — | ___ ml | ___ |
        | 主动脉瓣环 | — | ___ mm | ___ |
        | 升主动脉内径 | — | ___ mm | ___ |
        | 右室前后径 | 16-30 | ___ mm | ___ |
        | 主肺动脉径 | 16-30 | ___ mm | ___ |
        | 左室舒张期内径 | 女≤50 / 男≤55 | ___ mm | ___ |
        | 左室收缩期内径 | — | ___ mm | ___ |
        | **二、室壁厚度及运动（mm）** | | | |
        | 室间隔厚度 | 8-12 | ___ | ___ |
        | 室间隔运动幅度 | — | ___ | ___ |
        | 左室后壁厚度 | — | ___ | ___ |
        | 左室后壁运动幅度 | — | ___ | ___ |
        | **三、血流动力学参数** | | | |
        | 主动脉流速 | — | ___ m/s | ___ |
        | 肺动脉流速 | — | ___ m/s | ___ |
        | 二尖瓣E峰 | — | ___ m/s | ___ |
        | 二尖瓣A峰 | — | ___ m/s | ___ |
        | 二尖瓣环间隔侧e | — | ___ cm/s | ___ |
        | 二尖瓣环侧壁侧e | — | ___ cm/s | ___ |
        | E/e" | — | ___ | ___ |
        | 三尖瓣反流流速 | — | ___ m/s | ___ |
        | 三尖瓣反流压差 | — | ___ mmHg | ___ |
        | 估测肺动脉收缩压 | — | ___ mmHg | ___ |
        | **四、心功能参数** | | | |
        | 左室舒张期容积 | — | ___ ml | ___ |
        | 左室收缩期容积 | — | ___ ml | ___ |
        | 左室射血分数（LVEF） | 50-80% | ___ % | ___ |
        | 左室短轴缩短率 | — | ___ % | ___ |
        | 每搏输出量 | — | ___ ml | ___ |
        | 每分钟输出量 | — | ___ L/min | ___ |
        | 即时心率 | — | ___ bpm | ___ |
        | **五、结构描述** | | | |
        | 双房及左室 | — | ___ | ___ |
        | 左室壁运动 | — | ___ | ___ |
        | 房室间隔 | — | ___ | ___ |
        | 心内瓣膜 | — | ___ | ___ |
        | 大动脉 | — | ___ | ___ |
        ```
        ---
        **以下是患者情况，以及患者超声测量结果**
        {request.text}
        """

    if not data:
        return {
            'success': False,
            'report': None
        }
    return {
        'success': True,
        'report': data
    }


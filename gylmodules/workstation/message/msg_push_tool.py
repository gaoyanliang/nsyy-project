import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError

from threading import Lock

import aiohttp
import requests
from datetime import datetime
from apns2.client import APNsClient
from apns2.payload import Payload, PayloadAlert

from gylmodules import global_config
from gylmodules.global_tools import timed_lru_cache
from gylmodules.utils.db_utils import DbUtil
from gylmodules.utils.event_loop import GlobalEventLoop

# Android
android_client_id = "109560375"
android_client_secret = "7c156cd2d19c23fb6100fa947850fabeb5c655ee5d099cf8b8875f097df05d83"
# android_push_url = "https://push-api.cloud.huawei.com/v2/388421841221765522/messages:send"
android_push_url = "https://push-api.cloud.huawei.com/v1/109560375/messages:send"

logger = logging.getLogger(__name__)
# 全局锁保证线程安全
_token_lock = Lock()


# 缓存华为token（5分钟）
@timed_lru_cache(seconds=300, maxsize=2)
def get_cached_token(client_id, client_secret):
    """带锁的Token获取"""
    with _token_lock:
        return get_huawei_push_token(client_id, client_secret)


def get_huawei_push_token(client_id, client_secret):
    """
    获取华为推送 token
    :param client_id: 客户端ID
    :param client_secret: 客户端密钥
    :return: 成功返回access_token，失败返回None
    """
    url = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=5)
        # 检查HTTP状态码
        response.raise_for_status()
        response_json = response.json()
        access_token = response_json.get("access_token")
        if not access_token:
            logger.error("get Huawei Push Token Error")
            return None

        logger.debug(f"get Huawei Push Token Success: {access_token}")
        return access_token
    except Exception as re:
        logger.error(f"Huawei Token Request Error: {str(re)}")
        return None


def build_android_payload(title, body, tokens):
    return {
        "validate_only": False,
        "message": {
            "notification": {"title": title, "body": body},
            "android": {
                "category": "IM",  # 必须传
                "notification": {
                    "priority": "HIGH",  # 必须为HIGH
                    "channel_id": "high_channel_id",  # 与客户端一致
                    "click_action": {"type": 3}
                }
            },
            "token": tokens
        }
    }


async def _async_push(url, token, payload):
    """真正的异步推送实现"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as session:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with session.post(url, json=payload, headers=headers) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"android push error: {str(e)}")
        return {"code": "80800001", "msg": str(e)}


def android_push(url, token, payload):
    """线程安全的异步调用入口"""
    start_time = time.time()
    loop = GlobalEventLoop().get_loop()
    coro = _async_push(url, token, payload)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        ret = future.result(timeout=10)
        logger.info(f"android 推送耗时：{time.time() - start_time}")
        return ret
    except TimeoutError:
        future.cancel()
        return {"code": "80000002", "msg": "Request timeout"}


def send_single_apns(client: APNsClient, device_token: str, title: str, body: str) -> bool:
    """发送单个通知（同步阻塞）"""
    try:
        payload = Payload(alert=PayloadAlert(title=title, body=body), sound="default", category="MY_CATEGORY")
        client.send_notification(device_token, payload, "com.nsyy.Nsyy")
        return True
    except Exception as e:
        print(f"ios 推送失败 {device_token[:8]}...: {e.__class__}")
        return False


def ios_push(title, body, device_tokens):
    start_time = time.time()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pem_path = os.path.join(script_dir, "ck.pem")  # 拼接完整路径
    client = APNsClient(pem_path, password="gyl.2015", use_sandbox=global_config.run_in_local)
    payload = Payload(alert=PayloadAlert(title=title, body=body), category="MY_CATEGORY", sound="default", )

    send_error_tokens = []
    for token in device_tokens:
        try:
            # 方法没有返回值，发送失败会抛出异常
            client.send_notification(token, payload, topic="com.nsyy.Nsyy")
        except Exception as e:
            logger.error(f"iOS push to {token}: {e.__class__}")
            send_error_tokens.append(token)
    logger.info(f"ios 推送耗时：{time.time() - start_time}")
    return send_error_tokens


def android_push_task(title, body, device_tokens):
    """Android 推送任务，供线程池调用"""
    android_error_tokens = []
    if not device_tokens:
        return android_error_tokens

    token = get_cached_token(android_client_id, android_client_secret)
    if token:
        android_batch_size = 500
        for i in range(0, len(device_tokens), android_batch_size):
            batch_tokens = device_tokens[i:i + android_batch_size]
            payload = build_android_payload(title, body, batch_tokens)
            ret = android_push(android_push_url, token, payload)
            if ret.get("code") == "80000000":
                logger.debug(f"Android push batch success: {len(batch_tokens)} tokens")
            elif ret.get("code") == "80100000":
                logger.warning(f"Android push batch error: {ret.get('msg')[:100]}")
                illegal_tokens = json.loads(ret.get("msg")).get("illegal_tokens", [])
                android_error_tokens.extend(illegal_tokens)
            else:
                logger.warning(f"Android push batch error: {ret.get('msg')[:100]}")
                android_error_tokens.extend(batch_tokens)
    else:
        android_error_tokens = device_tokens
    return android_error_tokens


def ios_push_task(title, body, device_tokens):
    """iOS 推送任务，供线程池调用"""
    return ios_push(title, body, device_tokens)


def push_msg_to_devices(pers_ids, title, body):
    start_time = datetime.now()

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    device_tokens = db.query_all(f"select * from nsyy_gyl.app_token_info where pers_id "
                                 f"in ({','.join(map(str, pers_ids))}) and device_token IS NOT NULL and online = 1 ")
    del db
    if not device_tokens:
        logger.debug(f"No devices found for pers_id: {pers_ids}")
        return []

    # 预处理消息内容
    msg_title = title or "新消息通知📢"
    msg_body = body or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 分组设备
    ios_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                         and item.get("brand") == "IOS" and item.get("device_token")]
    android_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                             and item.get("brand") != "IOS" and item.get("device_token")]

    if len(ios_device_tokens) > 0:
        # 推送初始化的时候会报错 module 'h2.settings' has no attribute 'ENABLE_PUSH'，仅影响第一个，所以在首位插入一个无效token
        ios_device_tokens.insert(0, "010101001010101010")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    pem_path = os.path.join(script_dir, "ck.pem")  # 拼接完整路径
    # client = APNsClient(pem_path, password="gyl.2015", use_sandbox=global_config.run_in_local)
    client = APNsClient(pem_path, password="gyl.2015", use_sandbox=False)
    payload = Payload(alert=PayloadAlert(title=title, body=body), category="MY_CATEGORY", sound="default", )

    # 并行执行 Android 和 iOS 推送
    android_error_tokens, ios_error_tokens = [], []
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交 Android 和 iOS 推送任务
        android_future = executor.submit(android_push_task, msg_title, msg_body, android_device_tokens)
        # ios_future = executor.submit(ios_push_task, msg_title, msg_body, ios_device_tokens)
        ios_futures = [executor.submit(send_single_apns, client, token, title, body)
                       for token in ios_device_tokens]
        # 等待结果
        android_error_tokens = android_future.result()
        for future, token in zip(ios_futures, ios_device_tokens):
            if not future.result():  # 阻塞获取结果
                ios_error_tokens.append(token)

    logger.info(f"push msg to devices Total time: {(datetime.now() - start_time).total_seconds():.2f}s")
    send_fail_pers_ids = []
    error_tokens = android_error_tokens + ios_error_tokens
    if error_tokens:
        failed_set = set(error_tokens)  # 转为集合提升查找效率
        pers_status = {}

        for device in device_tokens:
            pers_id = device['pers_id']
            token = device['device_token']
            # 如果该pers_id尚未记录，或之前有成功记录
            if pers_id not in pers_status or pers_status[pers_id]:
                pers_status[pers_id] = (token in failed_set)
        send_fail_pers_ids = [pers_id for pers_id, is_failed in pers_status.items() if is_failed]
    return send_fail_pers_ids

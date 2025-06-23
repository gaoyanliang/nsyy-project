import asyncio
import json
import logging
import os
from collections import defaultdict
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
        response = requests.post(url, headers=headers, data=data, timeout=10)
        # 检查HTTP状态码
        response.raise_for_status()

        # 尝试解析JSON响应
        try:
            response_json = response.json()
            access_token = response_json.get("access_token")

            if not access_token:
                error_msg = response_json.get("error_description", "No access_token in response")
                logger.error(f"get Huawei Push Token Error: {error_msg}")
                return None
            logger.debug(f"get Huawei Push Token Success: {access_token}")
            return access_token
        except JSONDecodeError as je:
            logger.error(f"Huawei Token JSON Error: {str(je)}, Response: {response.text[:200]}")
            return None
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
        logger.error(f"Push error: {str(e)}")
        return {"code": "80800001", "msg": str(e)}


def android_push(url, token, payload):
    """线程安全的异步调用入口"""
    loop = GlobalEventLoop().get_loop()
    coro = _async_push(url, token, payload)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return future.result(timeout=10)
    except TimeoutError:
        future.cancel()
        return {"code": "80000002", "msg": "Request timeout"}


def ios_push(title, body, device_tokens):
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
            logger.error(f"Error sending notification to {token}: {e.__str__()}")
            send_error_tokens.append(token)
    return send_error_tokens


def push_msg_to_devices(pers_ids, title, body):
    start_time = datetime.now()

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    device_tokens = db.query_all(f"select * from nsyy_gyl.app_token_info where pers_id "
                                 f"in ({','.join(map(str, pers_ids))}) and device_token IS NOT NULL and online = 1 ")
    del db
    if not device_tokens:
        logger.debug(f"No devices found for pers_id: {pers_ids}")
        return

    # 预处理消息内容
    msg_title = title or "新消息通知📢"
    msg_body = body or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 分组设备
    ios_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                         and item.get("brand") == "IOS" and item.get("device_token")]
    android_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                             and item.get("brand") != "IOS" and item.get("device_token")]

    android_error_tokens, ios_error_tokens = [], []
    if android_device_tokens:
        ret = android_push(android_push_url, get_cached_token(android_client_id, android_client_secret),
                           build_android_payload(msg_title, msg_body, android_device_tokens))
        if ret.get("code") == "80000000":
            logger.debug(f"android push result: {ret}")
            android_error_tokens = []
        elif ret.get("code") == "80100000":
            logger.warning(f"android push error: {ret}")
            illegal_tokens = json.loads(ret.get("msg"))
            illegal_tokens = illegal_tokens.get("illegal_tokens")
            android_error_tokens = illegal_tokens
        else:
            logger.error(f"android push error: {ret}")
            android_error_tokens = android_device_tokens
    if ios_device_tokens:
        ios_error_tokens = ios_push(msg_title, msg_body, ios_device_tokens)

    logger.debug(f"push msg to devices Total time: {(datetime.now() - start_time).total_seconds():.2f}s")
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


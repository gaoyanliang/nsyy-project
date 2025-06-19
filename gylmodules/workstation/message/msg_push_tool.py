import asyncio
import concurrent
import logging
from json import JSONDecodeError

from threading import Lock

from concurrent.futures import ThreadPoolExecutor

import aiohttp
import requests
from datetime import datetime

from gylmodules import global_config
from gylmodules.global_tools import timed_lru_cache
from gylmodules.utils.db_utils import DbUtil
from gylmodules.utils.event_loop import GlobalEventLoop

# Android
android_client_id = "109560375"
android_client_secret = "7c156cd2d19c23fb6100fa947850fabeb5c655ee5d099cf8b8875f097df05d83"
# android_push_url = "https://push-api.cloud.huawei.com/v2/388421841221765522/messages:send"
android_push_url = "https://push-api.cloud.huawei.com/v1/109560375/messages:send"

# iOS
ios_client_id = "114409375"
ios_client_secret = "0419f0ad14ce4ea0eda6bf1698d2804e97c949673d5b87d6de1076c56d77d365"
ios_push_url = "https://push-api.cloud.huawei.com/v1/114409375/messages:send"

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
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
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


def build_ios_payload(title, body, tokens):
    return {
        "validate_only": False,
        "message": {
            "apns": {
                # 10/5
                "headers": {"apns-topic": "com.nsyy.Nsyy", "apns-priority": "5"},
                # 1：测试用户 2：正式用户 3：VOIP用户
                "hms_options": {"target_user_type": 2},
                "payload": {
                    "aps": {"alert": {"title": title, "body": body}, "sound": "default"}
                }
            },
            "token": tokens
        }
    }


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


def sync_push(url, token, payload):
    """线程安全的异步调用入口"""
    loop = GlobalEventLoop().get_loop()
    coro = _async_push(url, token, payload)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return future.result(timeout=10)
    except TimeoutError:
        future.cancel()
        return {"code": "80000002", "msg": "Request timeout"}


def push_msg_to_devices(pers_ids, title, body):
    start_time = datetime.now()

    query_sql = f"select * from nsyy_gyl.app_token_info where pers_id in ({','.join(map(str, pers_ids))}) " \
                f"and device_token IS NOT NULL and online = 1 "
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    device_tokens = db.query_all(query_sql)
    del db
    if not device_tokens:
        logger.warning(f"No devices found for pers_id: {pers_ids}")
        return

    # 预处理消息内容
    msg_title = title or "新消息通知📢"
    msg_body = body or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 分组设备
    ios_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                         and item.get("brand") == "IOS" and item.get("device_token")]
    android_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                             and item.get("brand") != "IOS" and item.get("device_token")]

    # 并行推送（使用线程池+全局事件循环）
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        if ios_device_tokens:
            futures.append(executor.submit(sync_push, ios_push_url,
                                           get_cached_token(ios_client_id, ios_client_secret),
                                           build_android_payload(msg_title, msg_body, ios_device_tokens)))
        if android_device_tokens:
            futures.append(executor.submit(sync_push, android_push_url,
                                           get_cached_token(android_client_id, android_client_secret),
                                           build_android_payload(msg_title, msg_body, android_device_tokens)))

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                logger.info(f"Push result: {title} {body} {pers_ids} {result}")
            except Exception as e:
                logger.error(f"Push failed: {str(e)}")

    logger.debug(f"push msg to devices Total time: {(datetime.now() - start_time).total_seconds():.2f}s")

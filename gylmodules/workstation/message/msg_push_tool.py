import hashlib
import json
import logging
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from threading import Lock
from urllib.parse import quote

import httpx
import requests
from datetime import datetime

from gylmodules import global_config
from gylmodules.global_tools import timed_lru_cache
from gylmodules.utils.db_utils_new import DbUtil
from gylmodules.workstation.message.ios_push import send_apns_batch

# Android manufacturer
VIVO = 'VIVO'
HUAWEI = 'HUAWEI'
XIAOMI = 'XIAOMI'
OPPO = 'OPPO'
HONOR = 'HONOR'

logger = logging.getLogger(__name__)
# 全局锁保证线程安全
_token_lock = Lock()


# 缓存华为token（半小时）
@timed_lru_cache(seconds=30*60, maxsize=2)
def get_cached_token(manufacturer):
    """带锁的Token获取"""
    with _token_lock:
        return get_android_push_token(manufacturer)


"""获取安卓厂商的推送 token 24小时过期，做缓存，1-2小时更新一次。"""


def get_android_push_token(manufacturer):
    data, auth_url = {}, ''
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if manufacturer == "HUAWEI":
        data = {"grant_type": "client_credentials", "client_id": '117640783',
                "client_secret": '9a715cd100fcbb690784987665edc4b8b3373ed622c1508e8fb4f6322e49ad0b'}
        auth_url = 'https://oauth-login.cloud.huawei.com/oauth2/v3/token'
    elif manufacturer == "XIAOMI":
        # 小米不需要推送token
        return "non-xiaomi-push-token"
    elif manufacturer == "OPPO":
        # 加密签名。
        # 是用AppKey、当前时间戳毫秒数、MasterSecret拼接而成的字符串并用SHA256加密而成的字符串。
        # MasterSecret是注册应用时OPPO PUSH发放的服务端密钥，与AppKey对应
        # 获取当前时间戳毫秒数（整数）
        timestamp_long = int(time.time() * 1000)
        sign_string = f"44d06ef650aa47f0ba3d9369288b0780{timestamp_long}afb2df43e28444a881137202f4b46d99"
        # MD5成小写字母
        sha256_hash = hashlib.sha256(sign_string.encode('utf-8')).hexdigest()
        data = {"app_key": "44d06ef650aa47f0ba3d9369288b0780", "sign": sha256_hash, "timestamp": timestamp_long}
        auth_url = 'https://api.push.oppomobile.com/server/v1/auth'
    elif manufacturer == "VIVO":
        timestamp_long = int(time.time() * 1000)
        # appId appKey timestamp appSecret
        sign_string = f"106010793f1452de50721734e395fbc0a1624fc{timestamp_long}efdf2033-4d88-4c79-8e6d-4ad1cd950fe9"
        # MD5成小写字母
        md5_hash = hashlib.md5()
        md5_hash.update(sign_string.encode('utf-8'))
        sign = hashlib.sha256(sign_string.encode('utf-8')).hexdigest()
        data = {"appId": "106010793", "appKey": "11f1452de50721734e395fbc0a1624fc", "timestamp": timestamp_long,
                "sign": md5_hash.hexdigest().lower()}
        headers = {"Content-Type": "application/json"}
        auth_url = 'https://api-push.vivo.com.cn/message/auth'
    elif manufacturer == "HONOR":
        data = {"grant_type": "client_credentials", "client_id": 'a35c616c0e7d4efbbfa083e7c51a3936',
                "client_secret": '7F8eVjHhqVWAYGAstUMDodoxdt2afd3E'}
        auth_url = 'https://iam.developer.honor.com/auth/token'
    else:
        logger.error(f"不支持的推送厂商 {manufacturer}")
        return None

    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            response = requests.post(auth_url, headers=headers, data=data, timeout=10)
            # 检查HTTP状态码
            response.raise_for_status()
            response_json = response.json()

            access_token = None
            if manufacturer == "HUAWEI":
                access_token = response_json.get("access_token")
            elif manufacturer == "OPPO":
                if response_json.get("code") == 200:
                    access_token = response_json.get("data").get("auth_token")
                else:
                    raise Exception(f"{response_json}")
            elif manufacturer == "VIVO":
                if response_json.get("result") == 0:
                    access_token = response_json.get("authToken")
                else:
                    raise Exception(f"{response_json}")
            elif manufacturer == "HONOR":
                access_token = response_json.get("access_token")
            else:
                access_token = None

            if access_token:
                logger.debug(f"get {manufacturer} Push Token Success: {access_token}")
                return access_token
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                time.sleep(sleep_time)
            else:
                logger.error(f" 获取 {manufacturer} 推送 token失败:  {str(e)} ")
                return None
    return None


"""构建推送消息"""


def build_payload(manufacturer, title, body, push_token):
    if manufacturer == HUAWEI:
        # 普通消息
        return {
            "validate_only": False,
            "message": {
                "notification": {"title": title, "body": body},
                "android": {
                    "category": "IM",  # 必须传
                    "notification": {
                        "priority": "HIGH",  # 必须为HIGH
                        "importance": "NORMAL",
                        "click_action": {"type": 3},
                        "channel_id": "default_channel",
                    }
                },
                "token": []
            }
        }

        # # 自定义通知铃声 需指定 channel_id  importance sound default_sound 。不能使用
        # return  {
        #         "validate_only": False,
        #         "message": {
        #             "notification": {"title": title, "body": body},
        #             "android": {
        #                 "category": "IM",
        #                 "notification": {
        #                     # "channel_id": "custom_channel",
        #                     "importance": "NORMAL",
        #                     "priority": "HIGH",
        #                     "click_action": {"type": 3},
        #                     "sound": "/raw/alert",
        #                     "default_sound": False
        #                 }
        #             },
        #             "token": []
        #         }
        #     }
    elif manufacturer == HONOR:
        return {
            "notification": {
                "title": title,
                "body": body,
            },
            "android": {
                "targetUserType": 1 if global_config.run_in_local else 0
            }
        }
    elif manufacturer == XIAOMI:
        # template_param = json.dumps({
        #     "keywords1": title,
        #     "keywords2": body
        # })
        # return {
        #     "title": title,
        #     "payload": quote(body),
        #     "restricted_package_name": "com.nsyy.Nsyy",
        #     "description": body, # 小米手机 description 展示详情
        #     "notify_id": random.Random().randint(0, 2147483647),
        #     # "extra.channel_id": "153397",
        #     "extra.channel_id": "157037", # 自定义音频
        #     "extra.template_id": "P13328",
        #     "extra.template_param": template_param
        # }
        return {
            "title": title,
            "payload": quote(body),
            "restricted_package_name": "com.nsyy.Nsyy",
            "description": body,  # 小米手机 description 展示详情
            "notify_id": random.Random().randint(0, 2147483647),
            "extra.channel_id": "153397",
        }
    elif manufacturer == OPPO:
        return {
            "auth_token": push_token,
            "app_message_id": uuid.uuid4().__str__(),
            "title": title,
            "content": body
        }
    elif manufacturer == VIVO:
        return {
            "appId":106010793,
            "title": title,
            "content": body,
            "notifyType": 4,
            "skipType": 1,
            "classification": 1,
            "requestId": uuid.uuid4().__str__(),
            "pushMode": 1 if global_config.run_in_local else 0,
            "sendOnline": False
        }
    return {}



# =============================== android 推送（同步实现） ===============================

_ANDROID_HTTP_CLIENT = None
_ANDROID_HTTP_LOCK = threading.Lock()


def get_android_http_client() -> httpx.Client:
    """全局同步 HTTP 客户端，复用连接池"""
    global _ANDROID_HTTP_CLIENT
    with _ANDROID_HTTP_LOCK:
        if _ANDROID_HTTP_CLIENT is None:
            _ANDROID_HTTP_CLIENT = httpx.Client(
                timeout=httpx.Timeout(6.0, connect=2.0, read=3.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            )
        return _ANDROID_HTTP_CLIENT


def android_push(url, headers, payload):
    """同步推送入口（替代 asyncio.run_coroutine_threadsafe 版本）"""
    client = get_android_http_client()
    try:
        content_type = headers.get('Content-Type', '').lower()
        use_json = (isinstance(payload, dict)
                    and ('application/json' in content_type or not content_type))
        if use_json:
            resp = client.post(url, json=payload, headers=headers)
        else:
            resp = client.post(url, data=payload, headers=headers)
        return resp.json()
    except Exception as e:
        logger.error(f"android push error: {str(e)}")
        return {"code": "80800001", "msg": str(e)}


def build_and_push(manufacturer, device_tokens, title, body):
    # 获取对应厂商的 推送 token
    push_token = get_cached_token(manufacturer)
    if not push_token:
        # 所有设备均推送失败
        return device_tokens

    push_error_device_tokens = []
    batch_size = 200
    payload = build_payload(manufacturer, title, body, push_token)
    if manufacturer == HUAWEI:
        # 推送文档 https://developer.huawei.com/consumer/cn/doc/HMSCore-Guides/android-server-dev-0000001050040110
        # url = "https://push-api.cloud.huawei.com/v2/388421841221765522/messages:send"
        # send_url = "https://push-api.cloud.huawei.com/v1/109560375/messages:send"
        send_url = "https://push-api.cloud.huawei.com/v1/117640783/messages:send"
        headers = {"Authorization": f"Bearer {push_token}", "Content-Type": "application/json"}
        for i in range(0, len(device_tokens), batch_size):
            batch_tokens = device_tokens[i:i + batch_size]
            payload["message"]["token"] = batch_tokens
            ret = android_push(send_url, headers, payload)
            if ret.get("code") == "80000000":
                logger.debug(f"{manufacturer} batch push success: {len(batch_tokens)} tokens")
            elif ret.get("code") == "80100000":
                logger.warning(f"{manufacturer} batch push error: {ret.get('msg')[:100]}")
                illegal_tokens = json.loads(ret.get("msg")).get("illegal_tokens", [])
                push_error_device_tokens.extend(illegal_tokens)
            else:
                logger.warning(f"Android push batch error: {ret.get('msg')[:100]}")
                push_error_device_tokens.extend(batch_tokens)
    elif manufacturer == HONOR:
        # 推送文档 https://developer.honor.com/cn/docs/11002/reference/downlink-message
        send_url = "https://push-api.cloud.honor.com/api/v1/104537220/sendMessage"
        headers = {"Authorization": f"Bearer {push_token}", "Content-Type": "application/json", "timestamp": str(time.time() * 1000)}
        for i in range(0, len(device_tokens), batch_size):
            batch_tokens = device_tokens[i:i + batch_size]
            payload["token"] = batch_tokens
            ret = android_push(send_url, headers, payload)
            if ret.get("code") != 200:
                push_error_device_tokens.extend(batch_tokens)
    elif manufacturer == OPPO:
        # OPPO 广播推送 分两步
        # 1. 保存通知栏消息内容体 获取 message_id
        save_msg_url = "https://api.push.oppomobile.com/server/v1/message/notification/save_message_content"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        ret = android_push(save_msg_url, headers, payload)
        if ret.get("code") != 0:
            logger.debug(f"{manufacturer} 推送（保存通知栏消息内容体 ）异常 {ret}")
            push_error_device_tokens.extend(device_tokens)
        else:
            message_id = ret.get("data", {}).get("message_id")
            # 2. 广播推送
            send_url = "https://api.push.oppomobile.com/server/v1/message/notification/broadcast"
            if message_id:
                for i in range(0, len(device_tokens), batch_size):
                    batch_tokens = device_tokens[i:i + batch_size]
                    payload = {
                        "auth_token": push_token,
                        "message_id": message_id,
                        "target_type": 2,  # 2:表示推送目标为注册ID类型
                        "target_value": ';'.join(batch_tokens)
                    }
                    ret = android_push(send_url, headers, payload)
                    if ret.get("code") != 0:
                        logger.debug(f"{manufacturer} batch push failed: {len(batch_tokens)} tokens")
                        push_error_device_tokens.extend(batch_tokens)
                    else:
                        push_ret = ret.get("data", {})
                        push_ret = push_ret.pop('message_id')
                        push_ret = push_ret.pop('task_id')
                        if push_ret:
                            for err_code, err_tokens in push_ret.items():
                                logger.warning(f"{manufacturer} push error code: {err_code}, {len(err_tokens)} tokens")
                                push_error_device_tokens.extend(err_tokens)
    elif manufacturer == VIVO:
        # VIVO广播推送 分两步
        # 1. 保存群推消息公共体 获取 taskId
        save_msg_url = "https://api-push.vivo.com.cn/message/saveListPayload"
        headers = {"Content-Type": "application/json"}
        ret = android_push(save_msg_url, headers, payload)
        if ret.get("result") != 0:
            logger.debug(f"{manufacturer} 推送（保存通知栏消息内容体 ）异常 {ret}")
            push_error_device_tokens.extend(device_tokens)
        else:
            taskId = ret.get("taskId", '')
            # 2. 广播推送
            send_url = "https://api-push.vivo.com.cn/message/pushToList"
            if taskId:
                for i in range(0, len(device_tokens), batch_size):
                    batch_tokens = device_tokens[i:i + batch_size]
                    payload = {
                        "appId": 106010793,
                        "regIds": batch_tokens,
                        "taskId": taskId,
                        "requestId": uuid.uuid4().__str__()
                    }
                    ret = android_push(send_url, headers, payload)
                    if ret.get("result") != 0:
                        logger.debug(f"{manufacturer} batch push failed: {len(batch_tokens)} tokens")
                        push_error_device_tokens.extend(batch_tokens)
                    else:
                        push_ret = ret.get("invalidUsers", [])
                        if push_ret:
                            for item in push_ret:
                                push_error_device_tokens.extend(item.get('userid'))
                            logger.warning(f"{manufacturer} push error code: {push_ret}")
    elif manufacturer == XIAOMI:
        # 推送文档 https://dev.mi.com/xiaomihyperos/documentation/detail?pId=1559
        send_url = "https://api.xmpush.xiaomi.com/v2/message/regid"
        headers = {"Authorization": f"key=SSP2jvXAkRLBGue3/QIsjA==", "Content-Type": "application/x-www-form-urlencoded"}
        for i in range(0, len(device_tokens), batch_size):
            batch_tokens = device_tokens[i:i + batch_size]
            payload["registration_id"] = ','.join(batch_tokens)
            ret = android_push(send_url, headers, payload)
            if ret.get("code") != 0 or ret.get("result") != "ok":
                logger.warning(f"xiaomi batch push error: {ret}")
                push_error_device_tokens.extend(batch_tokens)
    else:
        logger.warning(f"{manufacturer} 推送异常")
    return push_error_device_tokens


# android 推送入口 供线程池调用
def android_push_task(title, body, device_tokens):
    start_time = time.time()
    android_error_tokens = []
    if not device_tokens:
        return android_error_tokens

    # 根据厂商进行分组 然后推送
    huawei_list = [item.get('device_token') for item in device_tokens if item.get('brand')
                             and item.get("brand") == 'HUAWEI' and item.get("device_token")]
    if huawei_list:
        android_error_tokens.extend(build_and_push(HUAWEI, huawei_list, title, body))

    honor_list = [item.get('device_token') for item in device_tokens if item.get('brand')
                             and item.get("brand") == 'HONOR' and item.get("device_token")]
    if honor_list:
        android_error_tokens.extend(build_and_push(HONOR, honor_list, title, body))

    xiaomi_list = [item.get('device_token') for item in device_tokens if item.get('brand')
                             and item.get("brand") in ['XIAOMI', 'REDMI', 'POCO', 'BLACKSHARK']
                             and item.get("device_token")]
    if xiaomi_list:
        android_error_tokens.extend(build_and_push(XIAOMI, xiaomi_list, title, body))

    oppo_list = [item.get('device_token') for item in device_tokens if item.get('brand')
                             and item.get("brand") in ['OPPO', 'REALME', 'ONEPLUS'] and item.get("device_token")]
    if oppo_list:
        android_error_tokens.extend(build_and_push(OPPO, oppo_list, title, body))

    vivo_list = [item.get('device_token') for item in device_tokens if item.get('brand')
                             and item.get("brand") in ['VIVO', 'IQOO'] and item.get("device_token")]
    if vivo_list:
        android_error_tokens.extend(build_and_push(VIVO, vivo_list, title, body))

    logger.debug(f"android 推送：目标设备: {len(device_tokens)} | "
                f"失败: {len(android_error_tokens)} ｜ 耗时 {time.time() - start_time}")
    return android_error_tokens


# =============================== iOS 推送 ===============================

# ios_push.py

# =============================== 向设备推送入口 ===============================


def push_msg_to_devices(pers_ids, title, body, is_ringtone: bool=False):
    # ✅ 处理 pers_ids
    if isinstance(pers_ids, (int, str)):
        pers_ids = [str(pers_ids)]
    elif isinstance(pers_ids, list):
        pers_ids = [str(item) for item in pers_ids]
    else:
        raise TypeError("pers_ids 必须是 int / list /str")

    start_time = time.time()

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        device_tokens = db.query_all(f"select * from nsyy_gyl.app_token_info where pers_id "
                                     f"in ({','.join([f'{item}' for item in pers_ids])}) and device_token IS NOT NULL and online = 1 ")
    if not device_tokens:
        logger.debug(f"No devices found for pers_id: {pers_ids}")
        return []

    # 预处理消息内容
    msg_title = title or "新消息通知📢"
    msg_body = body or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 分组设备
    ios_device_tokens = [item.get("device_token") for item in device_tokens if item.get('brand')
                         and item.get("brand") == "IOS" and item.get("device_token")]
    android_device_tokens = [item for item in device_tokens if item.get('brand')
                             and item.get("brand") != "IOS" and item.get("device_token")]

    # 并行执行 Android 和 iOS 推送
    android_error_tokens, ios_error_tokens = [], []
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交 Android 和 iOS 推送任务
        android_future = executor.submit(android_push_task, msg_title, msg_body, android_device_tokens)
        # ios 支持铃声通知
        sound = "alert.wav" if is_ringtone else "default"
        ios_futures = executor.submit(send_apns_batch, ios_device_tokens, msg_title, msg_body, sound)
        # 等待结果
        android_error_tokens = android_future.result()
        ios_error_tokens = ios_futures.result()

    error_tokens = android_error_tokens + ios_error_tokens
    # 统一日志
    total_devices = len(device_tokens)
    success_count = total_devices - len(error_tokens)
    logger.debug(f"推送完成 | 目标设备: {total_devices} | 成功: {success_count} | "
                f"失败: {len(error_tokens)} | 耗时: {time.time() - start_time}s")

    send_fail_pers_ids = []
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




# send_apns_batch(['fb701c01d93fa074c4ff12bbddd3d3a5534b11c0a43382c151cd22d981cf7abb'], '危急值提醒', '发现新危急值，请及时处理[王世方-张彪-3078854-0]')

# android_push_task('危急值提醒', '发现新危急值，请及时处理[22王世方---张彪-3078854-0]', [{'device_token': '5aUCGHsxBk0r0Wk+jWdbXyrhThZH9z9XlmLbLL3tcxbqOUlbaF7UaU7x6dW9cxvv', 'brand': 'REDMI'}])

# android_push_task('危急值提醒', '发现新危急值，请及时处理[33王世方---张彪-3078854-0]', [{'device_token': '0869381038197228300038136000CN01', 'brand': 'HUAWEI'}])

# android_push_task('危急值提醒', ' TEST 发现新危急值，请及时处理', [{'device_token': 'IQAAAACy1i-wAAAcGVhaFdUIdV7KG_yxqsxOrjsXli5GCdVQo5IIRZEeYfWPef5uIoS7CsVLh-y8wxtJWAVIeVg-diaIU8ku4JRUY7Mo8bSI206GcA', 'brand': 'HUAWEI'}])
# android_push_task('危急值提醒', ' TEST 发现新危急值，请及时处理', [{'device_token': 'IQAAAACy1i-wAADupXqm-ovXvGBTne29Qchegy7AWyjAi-gFGVz_6fLKceW33Kkr-0RsMdMfqiSDENkPu7YZiTSnEZ581UmCaspxY0H3rssVRlBiqQ', 'brand': 'HUAWEI'}])



#

import base64
from datetime import datetime, date
import json
import threading
import traceback
import logging
import time
from _decimal import Decimal
from logging.handlers import RotatingFileHandler

from functools import wraps, lru_cache
from typing import Callable, Any, List, Dict

import cx_Oracle
import requests
import psycopg2

from psycopg2.extras import RealDictCursor
from flask import Blueprint, jsonify, request

from gylmodules import global_config

DB_CONFIG = {"dbname": "df_his", "user": "ogg", "password": "nyogg@2024", "host": "192.168.8.57", "port": "6000"}


def setup_logging(log_file='app.log', level=logging.INFO, backup_count=5, max_bytes=10 * 1024 * 1024,  # 10MB
                  formats='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """
    全局日志配置函数
    :param log_file: 日志文件路径
    :param level: 日志级别（默认INFO）
    :param formats: 日志格式
    :param max_bytes: 单个日志文件最大大小
    :param backup_count: 备份文件数量
    """
    # 创建根日志器
    logger = logging.getLogger()
    logger.setLevel(level)

    # 避免重复添加Handler（防止多次调用时重复日志）
    if logger.handlers:
        logger.handlers.clear()

    # 控制台Handler
    if global_config.run_in_local:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(formats))
        logger.addHandler(console_handler)

    if not global_config.run_in_local:
        # 文件Handler（自动轮转）
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            delay=False,  # 禁用延迟打开文件（Python 3.6+）
        )
        file_handler.setFormatter(logging.Formatter(formats))
        file_handler.flush()  # 立即刷新缓冲区（可选，但建议添加）

        # 添加Handler
        logger.addHandler(file_handler)

    # 关闭第三方库的冗余日志（可选）， INFO 日志（只显示 WARNING 及以上）
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("hyper").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)

    return logger


logger = logging.getLogger(__name__)

oracle_env = {
    # newzt 系统
    "ORACLE_NEWZT_USER": "system",
    "ORACLE_NEWZT_PASSWORD": "NSpingtai!8166",
    "ORACLE_NEWZT_DSN": "192.168.8.84:1521/nsyypt",

    # ydhl 系统
    "ORACLE_YDHL_USER": "kyeecis",
    "ORACLE_YDHL_PASSWORD": "kyeepass",
    "ORACLE_YDHL_DSN": "192.168.3.98:1521/orcl",

    # sannuo_xuetang 系统
    "ORACLE_SANNUO_XUETANG_USER": "XUETANG",
    "ORACLE_SANNUO_XUETANG_PASSWORD": "XUETANG",
    "ORACLE_SANNUO_XUETANG_DSN": "192.168.3.68:1521/orcl",

    # ythis 系统
    "ORACLE_YTHIS_USER": "ZLHIS",
    "ORACLE_YTHIS_PASSWORD": "7EF8625",
    "ORACLE_YTHIS_DSN": "192.168.200.254:1521/ytfy",

    # kfhis 系统
    "ORACLE_KFHIS_USER": "zlhis",
    "ORACLE_KFHIS_PASSWORD": "his",
    "ORACLE_KFHIS_DSN": "192.168.3.18:1521/orcl",

    # nshis 系统
    "ORACLE_NSHIS_USER": "zlhis",
    "ORACLE_NSHIS_PASSWORD": ".1451534F81B",
    "ORACLE_NSHIS_DSN": "192.168.3.8:1521/ORCL"
}

# 连接池（全局单例）
_oracle_pools = {}

"""获取或创建Oracle连接池"""


def get_oracle_pool(sys: str) -> cx_Oracle.SessionPool:
    if sys not in _oracle_pools:
        _oracle_pools[sys] = cx_Oracle.SessionPool(
            user=oracle_env.get(f"ORACLE_{sys.upper()}_USER"),
            password=oracle_env.get(f"ORACLE_{sys.upper()}_PASSWORD"),
            dsn=oracle_env.get(f"ORACLE_{sys.upper()}_DSN"),
            min=2, max=5, increment=1
        )
    return _oracle_pools[sys]


"""安全执行Oracle查询（参数化查询 + 连接池）"""


def connect_oracle(sql: str, sys: str = 'newzt') -> List[Dict]:
    try:
        pool = get_oracle_pool(sys)
        conn = pool.acquire()
        cursor = conn.cursor()

        # 执行SQL查询
        cursor.execute(sql)
        rows = cursor.fetchall()
        return normalize_oracle_result(cursor, rows)
    except Exception as e:
        logger.error(f"Oracle错误: sys={sys}, sql {sql}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            pool.release(conn)


"""标准化 Oracle 查询结果，使其与 MySQL 格式一致"""


def normalize_oracle_result(cursor, rows: List[tuple]) -> List[Dict[str, Any]]:
    # 获取列名
    columns = [col[0] for col in cursor.description]
    col_types = [col[1] for col in cursor.description]  # 获取字段类型
    normalized_rows = []

    for row in rows:
        normalized_row = {}
        for i, value in enumerate(row):
            col_name = columns[i]
            if isinstance(value, cx_Oracle.LOB):
                # 处理 CLOB/BLOB 类型
                if hasattr(value, 'read'):
                    normalized_row[col_name] = value.read()
                else:
                    normalized_row[col_name] = str(value)
            elif value is None:
                col_type = col_types[i]
                # 根据字段类型设置默认值
                if col_type == cx_Oracle.STRING:
                    normalized_row[col_name] = ""
                elif col_type == cx_Oracle.CLOB:
                    normalized_row[col_name] = ""
                elif col_type == cx_Oracle.BLOB:
                    normalized_row[col_name] = b''
                else:
                    normalized_row[col_name] = 0
            elif isinstance(value, (datetime, date)):
                if isinstance(value, datetime):
                    normalized_row[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    normalized_row[col_name] = value.strftime('%Y-%m-%d')
            elif isinstance(value, cx_Oracle.Timestamp):
                normalized_row[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                normalized_row[col_name] = value

        normalized_rows.append(normalized_row)

    return normalized_rows


def call_new_his(sql: str, sys: str = 'newzt', clobl: list = None):
    if global_config.run_in_local:
        # 本地测试调用领导接口，线上直连数据库
        return call_new_his_local(sql, sys, clobl)

    data = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            return connect_oracle(sql, sys=sys)
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                logging.warning(f"call_new_his 第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logging.error(f"call_new_his 已达最大重试次数 {max_retries}。最后错误: {str(e)}")
                return []

    return data


"""本地 调用领导 oracle_sql 接口实现 oracle 数据库查询"""


def call_new_his_local(sql: str, sys: str = 'newzt', clobl: list = None):
    """调用新 HIS 查询数据（支持异常重试）"""
    sql = base64.b64encode(sql.encode()).decode()
    param = {"key": "o4YSo4nmde9HbeUPWY_FTp38mB1c", "sys": sys, "sql": sql}
    if clobl:
        param['clobl'] = clobl

    # 动态 URL
    query_oracle_url = "http://192.168.124.5:5000/oracle_sql"
    # query_oracle_url = "http://192.168.3.12:6080/gyl/cv/query_oracle_data"

    data = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            response = requests.post(query_oracle_url, json=param, timeout=30)
            # 检查 HTTP 状态码
            response.raise_for_status()
            result = response.json()
            data = result.get('data', [])
            return data
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                logger.warning(f"call_new_his_api 第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logger.error(f"call_new_his_api 已达最大重试次数 {max_retries}。最后错误: {str(e)}\nSQL: {sql}")
                return []


def call_new_his_pg(sql):
    results = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            # 使用 `with` 语句确保自动关闭连接
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    datas = cur.fetchall()
                    for row in datas:
                        results.append(dict(row))

            return results
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                logging.warning(f"数据库连接失败，第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logging.error(f"数据库操作失败，已达最大重试次数 {max_retries}。最后错误: {str(e)}\nSQL: {sql}")
                return []

    return results


def start_thread(funct, args=None, tl=None):
    """
    start a thread
    :param funct:
    :param args:
    :param tl:
    :return:
    """

    if not tl:
        tl = []
    if not args:
        args = ()
    t = threading.Thread(target=funct, args=args)
    t.setDaemon(True)  # 服务器一直运行，所以子线程不会被关
    tl.append(t)
    t.start()
    return t


# ==========================================
# ============== router 装饰器 ==============
# ==========================================


# 用装饰器处理重复逻辑
def api_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        json_data = {}
        try:
            if request.get_data():
                json_data = json.loads(request.get_data().decode('utf-8'))

            # 本地调试时 打印
            logger.debug(f"请求 {request.url} 参数：{json_data}")

            if not json_data:
                result = func(*args, **kwargs)
            else:
                result = func(json_data, *args, **kwargs)
            return jsonify({'code': 20000, 'data': result if result is not None else {}})
        except json.JSONDecodeError:
            error_msg = f"Invalid JSON format"
            return jsonify({'code': 50000, 'res': error_msg})
        except KeyError as e:
            return jsonify({'code': 50000, 'res': f'Missing parameter: {e}'})
        except Exception as e:
            if global_config.run_in_local:
                logger.debug(f"{request.url} 系统异常： {str(e)} , param = {json_data} {traceback.print_exc()}")
            return jsonify({'code': 50000, 'res': str(e)})

    return wrapper


# 参数校验
def validate_params(*required_params):
    def decorator(func):
        @wraps(func)
        def wrapper(json_data, *args, **kwargs):
            missing = [param for param in required_params if param not in json_data]
            if missing:
                raise KeyError(f"Missing params: {', '.join(missing)}")
            return func(json_data, *args, **kwargs)

        return wrapper

    return decorator


def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_cache(func: Callable) -> Callable:
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expire_time = time.time() + func.lifetime

        @wraps(func)
        def wrapped_func(*args: Any, **kwargs: Any) -> Any:
            if time.time() > func.expire_time:
                func.cache_clear()
                func.expire_time = time.time() + func.lifetime
            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


# ==========================================
# ============== 签名          ==============
# ==========================================

def upload_sign_file(base64_str, is_pdf: bool = False):
    """
    将签名后的 pdf 以及图片上传至服务器
    :param base64_str:
    :param is_pdf:
    :return:
    """
    param = {"type": "save", "b64file": base64_str}
    if is_pdf:
        param['fext'] = 'pdf'
    url = "http://192.168.124.53:6080/b64pic_process" if global_config.run_in_local \
        else "http://192.168.3.12:6080/b64pic_process"
    response = requests.post(url, timeout=10, json=param)
    data = json.loads(response.text)
    if int(data.get('code')) != 20000:
        raise Exception(data)
    return data.get('download_path')


def encrypt_data(data: str, url_encode=False) -> str:
    """
    使用私钥加密数据并用Base64编码
    鉴权需要：使用应用私钥对“appId=xxx&id=xxx”进行参数签名，得到Base64编码格式签名值后进行URLEncode(UTF-8)传输。
    :param data:
    :param url_encode:
    :return:
    """
    import base64
    from urllib.parse import quote
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import serialization

    CONSTANT = {
        'sign_ca': 'MIIBsjCCAVagAwIBAgINX4AzdCiIohv0Mn2yGDAMBggqgRzPVQGDdQUAMEAxCzAJBgNVBAYTAkNOMRQwEgYDVQQDDAtTTTIgUk9PVCBDQTELMAkGA1UECAwCU0gxDjAMBgNVBAoMBVNIRUNBMB4XDTE4MDYwNDA5MDczOVoXDTIwMDYwNDA5MDczOVowWTELMAkGA1UEBhMCQ04xCzAJBgNVBAgMAlNIMQswCQYDVQQHDAJTSDENMAsGA1UECgwEc2lnbjENMAsGA1UECwwEc2lnbjESMBAGA1UEAwwJc2lnbl90ZXN0MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAE/XSK6MQlAeaGb8ZdiK6tzqALW1r6mubTb8POeFRpoCcX7rk34AbXFXRB5G17Er0TXY/VKtpXdlxY6GiMh2gtQqMaMBgwCQYDVR0TBAIwADALBgNVHQ8EBAMCBsAwDAYIKoEcz1UBg3UFAANIADBFAiA/HuCgtS03qEzL5tKy0Qmb8/UbQIc7akq5WctWvhzGWQIhAJe/76Z752H7Ug+Dpe7mgSiQ7VZ3n9Z/LOaEG7nS0VE5',
        'yun_private_key': "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDbM4E/CLLZEt5Dw4W0F7HCGk8WdmZqhtA2jgCgvNVEt7nbOmY2HPjUf2PgjMbxO2cWbDQIh22Hy+v3MKxm2QJPC0OWKbpSg3HklbaVWvMOCDsGJ8VLDWMp3Q7reRR1E6AuXhE9yu6+6ZhqfAxpE6EFfYChvn24r8wVjPDtRmXd9lRHwn+um5GVhDUeNDXx2see+0fBlxRxaTdXbxrLmfdjFx9g+M/vdm7l5jj9QV0kJvqv5DTXHl+E4xKUdxZkGIMBdkLR+ynORA0vef+eBgYMg8GiR6oP/4Hi/sZuF2qQ9wScPIl6wjcah+S0asEED3IMNoc9thAqYIw1AgtduG8nAgMBAAECggEAfdWFXqApu3+fZJs7h/UKMHlV6XkytfiKUqcWKS/95iLqaLWPs4TSO3qd5WwrUJRfS3n2LOdBs3EXFqI0dh4huyqmM+/kbDXVDfn8BKVfXjDPYWs3USxwProONJMfcU5A6B1MHIMAp0wGGSr5HOEN0M8JJtDp7znMGJr+O9fr5ozQG17jLax0ApJOXBpvuZpb9PB6k+GgvtV1En+YO583lkXbKegtzE1pd/Zzo/HFpr2AVKjlYjzX2S1QEj+L7OxvibpOavq1H7eEkUSzZJOnbfDLT2tFrQvOjUIr1H4JSoQJwDUFtj2twWkUew1yQ2A53htYVgwJXVA4edOs287IcQKBgQD0kLDlTW8o8uijO7xkGb/hBC+T38tGEmN3HL0elF/GJbF91ZdyLA4TSxbDNmlU/ShawKtuu8NhYw25H2e3mWddoj6MLrgGQQJB3FISDA9ON9InswN/ADISKAufm+YgubVyHAaSAPbNrDU/AyUyibtiB7d4LtnK35ph9di6DxVHGwKBgQDlcziI6lP8bC7Tv+w/Efhgq0l0In3/tuiL5xqX07i8GLX0naJyYLTemJ6wGjsG4hkE3ysYsUju0mOxE0uP3OKEOdkkoYo0ZZwFNmC2z+6pVwa0L1/lYZU04KDdJpVNieuhFot5FHA+qfO5jBQiE3s8DeDZunDfOoOaxB7xXei85QKBgFFv6OfCPDS3hk3ss1Pl2yYTncAw8mBX+TUNpdAL+kRiAtNzD2YeU2WLSH4inTqGvixSIgPSlEHWmRg+4+uYMnpUb12ApRi4BwdlVRLbXzFdlyZPDuf4abPwD8bLQ/s7u7bOrEVr+sMMCAL+iiFlCbef+DEV8MIEaUUbd1qlcSFnAoGBAMmEu7eMTr0Y6ruxCTWPe9yzM20bShxHsdAF5lZIbixNa6lutRjNlK0Xz++M6iCufRjJRFmIgyy1fTctYiT088D76ZmBgxdn0nLFgoWs88iolUu1e/zDCr+JNd9lnqWeJ2OwoEh0SezPaS6iN6CCCa8B5WR0meOEyccozqBgQSN9AoGBAI7CPKUxJsPAt3SXHOyOlVIPjVpuyZvYBvqLL2aKWIC5eP1gN4VkjyoIgi++zTS3GquYWQQxl4lvz+MPG7OZo2U+eRU3YwrBddsx9H4sX6QqgZ9XQdz35Le9yDa18I4A0q5GhWlvlXr+iCR3sP6/yeeCrHL4idn7/ttJBK8j9aDy"
    }
    private_key_bytes = base64.b64decode(CONSTANT['yun_private_key'])
    private_key = serialization.load_der_private_key(private_key_bytes, password=None)

    signature = private_key.sign(data.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
    sign = base64.b64encode(signature).decode()
    return sign if not url_encode else quote(sign)


def fetch_yun_sign_img(user_id: str):
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from urllib.parse import unquote
    """获取医生/护士 云医签 签名图片"""

    try:
        # 创建支持重试的 Session
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1,  # 最大重试次数 指数退避因子（1s, 2s, 4s）
            status_forcelist=[500, 502, 503, 504],  # 遇到这些状态码时重试
            allowed_methods=["POST"]  # 仅对 POST 请求重试
        ))
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 构造请求URL和参数  发送请求（自动重试逻辑已内置）
        params = {'appId': 11, 'id': user_id, 'sign': encrypt_data(f'appId=11&id={user_id}', url_encode=True)}
        response = session.post('http://192.168.3.181:8080/openapi/v1/user/seal', data=params, timeout=10)
        response.raise_for_status()  # 检查HTTP错误

        resp_data = response.json()

        if resp_data.get('ret', '') != 'success':
            logger.error(f"请求云医签医生/护理签名 API 业务错误: {resp_data}")
            return None

        # logger.info("获取签名图片成功")
        scale_seal = unquote(resp_data.get('data', {}).get('scaleSeal'))
        return scale_seal

    except requests.exceptions.RequestException as e:
        logger.error(f"请求失败: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"响应解析失败: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"未知错误: {str(e)}", exc_info=True)
        return None


def call_yangcheng_sign_serve(param: dict, ts_sign: bool = False):
    """
    调用 杨程 部署的签名服务器，进行签名
    :param param:
    :param ts_sign:
    :return:
    """
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            sign_serve_url = "http://192.168.3.45:8087/yun_signer/opera_sign" \
                if not ts_sign else "http://192.168.3.45:8087/signer/opera_sign"
            response = requests.post(sign_serve_url, timeout=10, json=param)
            data = json.loads(response.text)
            if int(data.get('code')) != 20000:
                raise Exception(data)
            return data.get('data')
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                logging.warning(
                    f"签名服务器连接失败，第 {retry_count}/{max_retries} 次重试..."
                    f"错误: {str(e)}，{sleep_time}秒后重试"
                )
                time.sleep(sleep_time)
            else:
                logging.error(f"签名服务器连接失败，已达最大重试次数 {max_retries}。最后错误: {str(e)}\n")
                return {}


def send_to_wx(log_str):
    try:
        webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=59432c15-d5fc-42c4-9315-d21d4b53b181"
        data = {"msgtype": "text", "text": {"content": log_str}}
        resp = requests.post(webhook, json=data)
    except Exception as e:
        logger.error(f"发送微信通知失败: {e}")


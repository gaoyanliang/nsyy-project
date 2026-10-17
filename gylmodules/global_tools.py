from gylmodules import global_config
import oracledb
# # 启用 Thick 模式，连接 Oracle 11g
if not global_config.run_in_local:
    oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/21/client64/lib")

import pandas as pd
import json
from datetime import datetime, date
import threading
import traceback
import logging
import time
from logging.handlers import RotatingFileHandler

from functools import wraps, lru_cache
from typing import Callable, Any, List, Dict

import redis
import requests
import psycopg2

from psycopg2.extras import RealDictCursor
from flask import jsonify, request

from gylmodules import global_config
from gylmodules.utils.db_utils_new import DbUtil

DB_CONFIG = {"dbname": "df_his", "user": "ogg", "password": "nyogg@2024", "host": "192.168.8.57", "port": "6000"}
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True, protocol=2)


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
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("apns2.client").setLevel(logging.WARNING)
    logging.getLogger("mysql").setLevel(logging.WARNING)
    logging.getLogger("tzlocal").setLevel(logging.WARNING)  # 新增
    logging.getLogger("httpcore").setLevel(logging.WARNING)  # 新增
    logging.getLogger("websockets.client").setLevel(logging.WARNING)  # 新增
    logging.getLogger('redis.connection').setLevel(logging.WARNING)
    logging.getLogger('geventwebsocket.handler').setLevel(logging.WARNING)

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
    "ORACLE_YTHIS_PASSWORD": ".7EF8625",
    "ORACLE_YTHIS_DSN": "192.168.200.254:1521/ytfy",

    # kfhis 系统
    "ORACLE_KFHIS_USER": "zlhis",
    "ORACLE_KFHIS_PASSWORD": "his",
    "ORACLE_KFHIS_DSN": "192.168.3.18:1521/orcl",

    # nshis 系统
    "ORACLE_NSHIS_USER": "zlhis",
    "ORACLE_NSHIS_PASSWORD": ".1451534F81B",
    "ORACLE_NSHIS_DSN": "192.168.3.8:1521/ORCL",

    # nsshouma 系统
    "ORACLE_NSSHOUMA_USER": "sam1_db_bzbb",
    "ORACLE_NSSHOUMA_PASSWORD": "123456",
    "ORACLE_NSSHOUMA_DSN": "192.168.3.66:1521/orcl"
}

# 连接池（全局单例）
_oracle_pools = {}

"""获取或创建Oracle连接池"""


def get_oracle_pool(sys: str) -> oracledb.ConnectionPool:
    if sys not in _oracle_pools:
        # 从环境变量字典中获取凭据
        user = oracle_env.get(f"ORACLE_{sys.upper()}_USER")
        password = oracle_env.get(f"ORACLE_{sys.upper()}_PASSWORD")
        dsn = oracle_env.get(f"ORACLE_{sys.upper()}_DSN")

        # 关键：确保 user 和 password 不为 None 或空字符串
        # 如果它们为空，需要检查你的 oracle_env 字典或环境变量配置
        if not user or not password:
            raise ValueError(f"Missing Oracle credentials for system: {sys}")

        _oracle_pools[sys] = oracledb.create_pool(
            user=user,
            password=password,
            dsn=dsn,
            min=5,
            max=25,
            increment=2
        )
    return _oracle_pools[sys]


"""安全执行Oracle查询（参数化查询 + 连接池）"""
def connect_oracle(sql: str, sys: str = 'newzt') -> List[Dict]:
    pool = None
    conn = None
    cursor = None
    try:
        pool = get_oracle_pool(sys)
        conn = pool.acquire()
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()
        return normalize_oracle_result(cursor, rows)
    except Exception as e:
        logger.error(f"Oracle错误: sys={sys}, sql {sql}, exception {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and pool is not None:
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
            if isinstance(value, oracledb.LOB):
                # 处理 CLOB/BLOB 类型
                if hasattr(value, 'read'):
                    normalized_row[col_name] = value.read()
                else:
                    normalized_row[col_name] = str(value)
            elif value is None:
                col_type = col_types[i]
                # 根据字段类型设置默认值
                if col_type == oracledb.STRING:
                    normalized_row[col_name] = ""
                elif col_type == oracledb.CLOB:
                    normalized_row[col_name] = ""
                elif col_type == oracledb.BLOB:
                    normalized_row[col_name] = b''
                else:
                    normalized_row[col_name] = 0
            elif isinstance(value, (datetime, date)):
                if isinstance(value, datetime):
                    normalized_row[col_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    normalized_row[col_name] = value.strftime('%Y-%m-%d')
            else:
                normalized_row[col_name] = value

        normalized_rows.append(normalized_row)

    return normalized_rows


def call_new_his(sql: str, sys: str = 'newzt', clobl: list = None):
    data = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            return connect_oracle(sql, sys=sys)
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                logger.warning(f"call_new_his 第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logger.error(f"call_new_his 已达最大重试次数 {max_retries}。最后错误: {str(e)}")
                return []

    return data


"""查询PG数据库"""


def call_new_his_pg(sql, retry_count: int = 0):
    results = []
    max_retries, retry_count, retry_delay = 3, 0, 1
    if retry_count != 0:
        max_retries = retry_count
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
                logger.warning(f"数据库连接失败，第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logger.error(f"数据库操作失败，已达最大重试次数 {max_retries}。最后错误: {str(e)}\nSQL: {sql}")
                return []

    return results



""" 查询 SQL Server 数据库 """
def call_query_sqlserver(sql: str) -> List[Dict]:
    # 连接信息
    SERVER = '192.168.3.222'
    USERNAME = 'reader'
    PASSWORD = 'reader'

    # 创建连接字符串
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )

    import pyodbc
    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cursor = conn.cursor()

            cursor.execute("""SET NOCOUNT ON; SET ARITHABORT ON;""")
            cursor.execute(sql)

            # 跳过没有结果集的 batch
            while cursor.description is None:
                if not cursor.nextset():
                    break

            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return result
    except pyodbc.Error as e:
        logger.error(f"SQL Server 查询错误: {e}")
    return []


def call_tijian_query(sql: str):
    if global_config.run_in_local:
        import pymssql
        try:
            # 使用 freetds.conf 中定义的 server38
            conn = pymssql.connect(server='server38', user='sa', password='nstj@2014',
                                   database='tj_xlms', autocommit=True, charset='UTF-8')
            cursor = conn.cursor()
            cursor.execute(sql)

            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            conn.close()
            return result
        except pymssql.Error as e:
            logger.error(f"SQL Server 查询错误: {e}")
            return []
        finally:
            if conn:
                conn.close()
            if cursor:
                cursor.close()
    else:
        # 连接信息
        SERVER = '192.168.3.38,1433'
        USERNAME = 'sa'
        PASSWORD = 'nstj@2014'
        DATABASE = 'tj_xlms'

        # 创建连接字符串
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={SERVER};"
            f"UID={USERNAME};"
            f"PWD={PASSWORD};"
            f'DATABASE={DATABASE};'
            "TrustServerCertificate=yes;"
            "Connection Timeout=30;"
        )

        import pyodbc
        try:
            with pyodbc.connect(conn_str, autocommit=True) as conn:
                cursor = conn.cursor()

                cursor.execute("""SET NOCOUNT ON; SET ARITHABORT ON;""")
                cursor.execute(sql)

                # 跳过没有结果集的 batch
                while cursor.description is None:
                    if not cursor.nextset():
                        break

                columns = [c[0] for c in cursor.description]
                rows = cursor.fetchall()

                result = [dict(zip(columns, row)) for row in rows]
                return result
        except pyodbc.Error as e:
            logger.error(f"SQL Server 查询错误: {e}")
        return []



def start_thread(funct, args=None, tl=None):
    if not tl:
        tl = []
    if not args:
        args = ()
    t = threading.Thread(target=funct, args=args, daemon=True)
    tl.append(t)
    t.start()
    return t


"""socket 推送"""

def socket_push(info, data):
    # 老结构
    # data = {'msg_list': [{"socketd": "m_app", 'socket_data':   { "type": 400, "data": { "message": {msg 的内容} } },
    # 'pers_id': user_id}]}

    # 通过 pers——ID 区分院内人员和患者 患者的pers id 是 微信的openid 是字符串
    people_list = data.get('pers_id', [])

    # 如果是单个值，转成列表
    if isinstance(people_list, (int, str)):
        people_list = [people_list]

    pers_id_list = []
    patient_id_list = []

    for i in people_list:
        if isinstance(i, int):
            pers_id_list.append(i)
        elif isinstance(i, str) and i.isdigit():
            pers_id_list.append(int(i))
        else:
            patient_id_list.append(str(i))

    data['pers_id'] = pers_id_list
    data['patient_id'] = patient_id_list

    max_retries, retry_count, retry_delay = 3, 0, 1
    while retry_count < max_retries:
        try:
            # 发送POST请求
            response = requests.post(global_config.socket_push_url, data=json.dumps(data),
                                     headers={'Content-Type': 'application/json'}, timeout=5)
            logger.debug(f" {info} Socket 推送结果:  {response.text}   发送数据:  {data}")
            # 打印响应内容
            if response.status_code != 200:
                raise Exception(f" {info} Socket 推送结果:  {response.status_code}  {response.text}  {data}")

            return
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                # logger.warning(f"socket_push 第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                time.sleep(sleep_time)
            else:
                logger.error(f" {info} Socket 推送失败:  {str(e)}  {data}")
                return


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
    url = "http://192.168.124.8:6080/b64pic_process" if global_config.run_in_local \
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
                logger.warning(
                    f"签名服务器连接失败，第 {retry_count}/{max_retries} 次重试..."
                    f" user_id = {param.get('user_id', '')} 错误: {str(e)}，{sleep_time}秒后重试"
                )
                time.sleep(sleep_time)
            else:
                logger.error(f"签名服务器连接失败，已达最大重试次数 {max_retries}。最后错误: {str(e)}\n")
                return {}


def send_to_wx(log_str):
    try:
        # 基于 webhook 推送给企业微信群聊
        webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=59432c15-d5fc-42c4-9315-d21d4b53b181"
        data = {"msgtype": "text", "text": {"content": log_str}}
        resp = requests.post(webhook, json=data, timeout=5)
    except Exception as e:
        logger.error(f"发送微信通知失败: {e}")


# ==========================================
# ============== 其他工具      ==============
# ==========================================


"""
交接班系统： 同步医生职称
医师电子化排班： 同步医生基本信息
"""
def fetch_doctor():
    sql = """select gz.zhigongid 职工id, gz.zhigonggh 职工工号, gz.zhigongxm 姓名, gz1.zhichengmc 职称, gz1.keshimc,
		gz1.dianhua1 电话, gz2.zuzhimc 人事科室, gz3.zuzhimc 考勤科室, gz4.zuzhimc 核算科室,
		coalesce(gz.renshiks,gz.kaoqinks,gz.hesuanks,gz1.keshiid) as 科室id,
		coalesce(gz2.zuzhimc,gz3.zuzhimc,gz4.zuzhimc,gz1.keshimc) 科室
	from df_zhushuju.gy_zhigongda gz join df_zhushuju.gy_zhigongxx gz1 on gz.zhigongid = gz1.zhigongid
		and gz1.zuofeibz = 0 and gz1.dangqianzt ='1' and gz1.zaizhizt =1 
	left join df_zhushuju.gy_zuzhidy gz2 on gz.renshiks=gz2.zuzhiid
	left join df_zhushuju.gy_zuzhidy gz3 on gz.kaoqinks=gz3.zuzhiid
	left join df_zhushuju.gy_zuzhidy gz4 on gz.hesuanks=gz4.zuzhiid
	where gz.zhigonglb = '1'"""
    data = call_new_his_pg(sql)
    if not data:
        return

    with DbUtil('192.168.3.12', 'root', '123123', "oa_test") as db:
        doctors = db.query_all("select his_no, pers_id from oa_test.hr_pers_main where is_active = 1")

    doctor_pers_id_map = {str(item.get('his_no')): item.get('pers_id') for item in doctors}

    redis_client = redis.Redis(connection_pool=pool)
    for item in data:
        if item.get('职工工号'):
            # 交接班系统需要
            zhicheng = '住院医师' if item.get('职称', '') == '医师' else item.get('职称')
            if zhicheng:
                redis_client.set(f"doctor_title:{item.get('职工工号')}", zhicheng)

            item['pers_id'] = doctor_pers_id_map.get(str(item.get('职工工号')), '')
            # 医生排班需要
            redis_client.hset(f"doctor_schedule", str(item.get('职工工号')), json.dumps(item, ensure_ascii=False, default=str))

# fetch_doctor()


def excel_to_jsons(file_path, sheet_num: int = 0, header_line: int = 1, keys: list = None):
    """
    :param file_path: Excel 文件路径
    :param sheet_num: 工作表索引，从0开始
    :param header_line: 表头所在行号（从1开始）
    :param keys: 需要提取的列名列表，若为 None 则提取所有列
    :return: JSON 字符串列表
    """
    import openpyxl
    wbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wbook[wbook.sheetnames[sheet_num]]

    # 读取所有表头
    headers = [cell.value for cell in sheet[header_line]]

    # 如果指定了 keys，则只保留这些列；否则保留所有列
    if keys is not None:
        # 仅保留在 keys 中出现的列名（按 keys 的顺序保留，便于排序）
        # 如果某个 key 不在 headers 中，此处会被忽略（也可主动抛出异常）
        valid_keys = [k for k in keys if k in headers]
        # 构建列索引映射：列名 -> 列索引（0-based）
        col_indices = {name: idx for idx, name in enumerate(headers) if name in valid_keys}
        # 为了后续 zip 顺序一致，按 valid_keys 顺序取出列值
        # 由于 iter_rows 按列顺序返回，我们需要按索引提取，但更简单的是直接用行字典过滤
    else:
        valid_keys = headers

    results = []
    for row in sheet.iter_rows(min_row=header_line + 1, values_only=True):  # 从表头下一行开始
        # 将整行与所有表头组合成字典
        full_dict = dict(zip(headers, row))
        # 如果指定了 keys，则过滤字典
        if keys is not None:
            row_dict = {k: full_dict[k] for k in valid_keys if k in full_dict}
        else:
            row_dict = full_dict

        # 如果需要写入文件，需要将row_dict转为JSON字符串
        # row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
        results.append(row_dict)

    return results


def jsons_to_excel_pandas(json_list, file_path, sheet_name="Sheet1"):
    """
    将JSON列表写入Excel
    :param json_list: 可以是 字典列表 或 JSON字符串列表
    :param file_path: 输出路径，如 "output.xlsx"
    :param sheet_name: 工作表名称
    """
    # 如果传入的是 JSON 字符串列表（比如你之前的函数返回的），先转为字典列表
    if json_list and isinstance(json_list[0], str):
        dict_list = [json.loads(item) for item in json_list]
    else:
        dict_list = json_list

    # 核心操作：字典列表 -> DataFrame -> Excel
    df = pd.DataFrame(dict_list)
    df.to_excel(file_path, sheet_name=sheet_name, index=False)

    print(f"成功写入 {len(df)} 行数据到 {file_path}")

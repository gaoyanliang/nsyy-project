import json
import threading
import traceback
from functools import wraps

import requests
import psycopg2
from datetime import datetime

from psycopg2.extras import RealDictCursor
from flask import Blueprint, jsonify, request

from gylmodules import global_config


DB_CONFIG = {
    "dbname": "df_his",
    "user": "ogg",
    "password": "nyogg@2024",
    "host": "192.168.8.57",
    "port": "6000"
}


def call_new_his(sql: str, clobl: list = None):
    """
    调用新 his 查询数据
    :param sql:
    :param clobl:
    :return:
    """
    param = {"key": "o4YSo4nmde9HbeUPWY_FTp38mB1c", "sys": "newzt", "sql": sql}
    if clobl:
        param['clobl'] = clobl

    query_oracle_url = "http://127.0.0.1:6080/oracle_sql"
    if global_config.run_in_local:
        query_oracle_url = "http://192.168.124.53:6080/oracle_sql"

    data = []
    err_data = ''
    try:
        response = requests.post(query_oracle_url, json=param, timeout=15)
        err_data = response.text
        if response.status_code != 200 or not response.text.strip():
            print(datetime.now(), 'oracle_sql 请求失败，服务器未返回数据：', response.status_code, err_data, param)
            return []
        data = json.loads(response.text)
        data = data.get('data', [])
    except Exception as e:
        print(datetime.now(), '调用新 HIS 查询数据失败：', param.get('sql'), err_data, e)

    return data


def call_new_his_pg(sql):
    results = []
    try:
        # 使用 `with` 语句确保自动关闭连接
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                datas = cur.fetchall()
                for row in datas:
                    results.append(dict(row))

    except Exception as e:
        print(datetime.now(), 'PG 数据库查询失败', e, sql)

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
        try:
            json_data = {}
            if request.get_data():
                json_data = json.loads(request.get_data().decode('utf-8'))

            # 本地调试时 打印
            if global_config.run_in_local:
                print(datetime.now(), request.url, '请求参数：', json_data)

            result = func(json_data, *args, **kwargs)
            return jsonify({'code': 20000, 'data': result if result is not None else {}})
        except json.JSONDecodeError:
            error_msg = f"Invalid JSON format"
            return jsonify({'code': 50000, 'res': error_msg})
        except KeyError as e:
            return jsonify({'code': 50000, 'res': f'Missing parameter: {e}'})
        except Exception as e:
            print(datetime.now(), request.url, f"系统异常: {e}", traceback.print_exc())
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


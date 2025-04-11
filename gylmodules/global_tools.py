import json
import threading

import requests
import psycopg2
from datetime import datetime

from psycopg2.extras import RealDictCursor

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
            print(datetime.now(), '请求失败，服务器未返回数据：', response.status_code, err_data)
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

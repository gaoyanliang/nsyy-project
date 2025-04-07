import json
import requests
from datetime import datetime

from gylmodules import global_config


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


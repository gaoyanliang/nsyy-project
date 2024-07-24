import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from gylmodules import global_config
from gylmodules.critical_value import cv_config
import asyncio
from datetime import datetime
import xml.etree.ElementTree as ET
import re
import redis

from gylmodules.utils.db_utils import DbUtil

# from gylmodules.critical_value.critical_value import medical_record_writing_back
#
# json_data = {
#     "pat_no": '400657',
#     "pat_type": 3,
#     "record": {'time': datetime.now()},
#     "handler_name": "handler_name",
#     "timer": '2024-07-19 15:19:19',
#     "method": "method",
#     "analysis": "analysis"
# }
#
# medical_record_writing_back(json_data)
#
# print(datetime.now())




# import re
#
# # address = "河南省镇平县彭营乡彭庄村彭庄11组168号"
# address = "卧龙区石桥镇一村"
#
# # 使用正则表达式解析地址
# pattern = re.compile(r'^(?P<province>.+?省)(?P<county>.+?县)(?P<township>.+?乡)(?P<village>.+?村)(?P<group>.+组)(?P<house_number>\d+号)$')
# match = pattern.match(address)
#
# if match:
#     address_components = match.groupdict()
#     province = address_components['province']
#     county = address_components['county']
#     township = address_components['township']
#     village = address_components['village']
#     group = address_components['group']
#     house_number = address_components['house_number']
#
#     print(f"省: {province}")
#     print(f"市: 不明确（可能需要进一步解析）")
#     print(f"县: {county}")
#     print(f"乡/街道: {township + village}")
#     print(f"组: {group}")
#     print(f"号: {house_number}")
# else:
#     print("地址格式不匹配")



pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=2, decode_responses=True)
redis_client = redis.Redis(connection_pool=pool)

redis_client.hset("APPT_PROJECTS", '10', json.dumps({"id": 10, "proj_type": 1, "proj_name": "肾内科/老年医学科门诊", "location_id": None, "dept_id": None, "dept_name": None, "is_group": 0, "nsnum": 24}))



# # value = ['1', '2', '2', '3']
# value = []
# value = list(set(value))
#
# print(value)
#
# dt = datetime.strptime('2024-07-22 12:12:12', "%Y-%m-%d %H:%M:%S")
# review_time = dt.strftime("%Y.%m.%d %H:%M:%S")
#
# print()
#
#
# key = '头部'
#
# if key.__contains__('头'):
#     print('tousssssssssssssss')


# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
# # 构建 SQL 语句，更新字段中的 \r 字符
# update_sql = f"""
# UPDATE nsyy_gyl.cv_template
# SET cv_result_pinyin_abb = REPLACE(cv_result_pinyin_abb, '\r', '')
# WHERE cv_result_pinyin_abb LIKE '%\r%'
# """
#
# db.execute(update_sql, need_commit=True)
# del db

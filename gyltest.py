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
from openpyxl import Workbook

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



# pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
#                             db=2, decode_responses=True)
# redis_client = redis.Redis(connection_pool=pool)
#
# redis_client.hset("APPT_PROJECTS", '10', json.dumps({"id": 10, "proj_type": 1, "proj_name": "肾内科/老年医学科门诊", "location_id": None, "dept_id": None, "dept_name": None, "is_group": 0, "nsnum": 24}))



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


db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
            global_config.DB_DATABASE_GYL)



query_sql = """
select patient_name 患者姓名, 
 patient_treat_id  住院号, 
 cv_id 项目编码, 
 cv_name  危机值名称,
 cv_result 危机值内容,
 doctor_recv_time  医师接收时间,
 handle_doctor_name  处理医师,
 method  处理记录
 from nsyy_gyl.cv_info where time > '2024-04-01 00:00:00' and time < '2024-06-30 23:59:59' and cv_source
"""
record = db.query_all(query_sql, need_commit=True)
del db



#
# def call_third_systems_obtain_data(type: str, param: dict):
#     data = []
#     if global_config.run_in_local:
#         try:
#             # 发送 POST 请求，将字符串数据传递给 data 参数
#             response = requests.post("http://192.168.124.53:6080/int_api", json=param)
#             data = response.text
#             data = json.loads(data)
#             data = data.get('data')
#         except Exception as e:
#             print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#     else:
#         if type == 'orcl_db_read':
#             # 根据住院号/门诊号查询 病人id 主页id
#             from tools import orcl_db_read
#             data = orcl_db_read(param)
#
#     return data
#
#
# param = {
#     "type": "orcl_db_read",
#     "db_source": "nsbingli",
#     "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#     "clob": ['CONTENT', 'CONTENTTEXT'],
#     # "sql": "select 1 t from dual"
#     # "sql": "select title from Bz_Doc_Log where ROWNUM < 10"
#     "sql": """
# select *
#   from (select *
#           from (Select b.病人id,
#                        b.主页id,
#                        t.title       as 文档名称,
#                        -- a.title       文档类型,
#                        t.creat_time  记录时间
#                        -- t.creator     文档作者,
#                        -- t.contenttext.getclobval() contenttext,
#                        -- t.content.getclobval() content
#                   From Bz_Doc_Log t
#                   left join Bz_Act_Log a
#                     on a.Id = t.Actlog_Id
#                   left join 病人变动记录@HISINTERFACE b
#                     on a.extend_tag = 'BD_' || to_char(b.id))
#          order by 记录时间)
#  where 文档名称 like '%入院记录%' and ROWNUM < 50
#     """
# }
#
# # where
# # 病人ID = 564646
# # and 主页ID = 12
# # and 文档名称
# # like
# # '%记录%'
# records = call_third_systems_obtain_data('orcl_db_read', param)
#
# for rec in records:
#     print(rec)
#
# # print(records)
#






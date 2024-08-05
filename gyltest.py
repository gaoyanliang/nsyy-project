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
SELECT * FROM nsyy_gyl.cv_info where id = 3375
"""

record = db.query_one(query_sql)

print()

# insert_sql = """
# INSERT INTO nsyy_gyl.cv_info (patient_treat_id,req_docno,alertman,cv_flag,patient_type,cv_type,cv_name,cv_result,cv_unit,cv_ref,
# patient_gender,patient_name,patient_age,dept_id,dept_name,alert_dept_id,alert_dept_name,alertman_name,alertman_pers_id,cv_id,cv_source,alertdt,time,state,nurse_recv_timeout,nurse_send_timeout,doctor_recv_timeout,doctor_handle_timeout,total_timeout)
# VALUES (120, '谭宗章', '0248', '', 5, 2, '*血小板', '18 10^9/L', '', '125-350',
#  '1', '孙绍连', '59岁', 140, '呼吸科门诊', 140, '呼吸科门诊', '谭宗章', '9910', '1721984666261', 10, '2024-07-26 17:04:26', '2024-07-26 17:04:26', 1, '420', '60', '300', '120', '600')
#
# """
# try:
#     ret = db.execute(insert_sql, need_commit=True)
#     print(ret)
# except Exception as e:
#     print(' ------------- ')
#     print(e)
# del db



#
# def call_third_systems_obtain_data(type: str, param: dict):
#     data = []
#     if global_config.run_in_local:
#         try:
#             # 发送 POST 请求，将字符串数据传递给 data 参数
#             response = requests.post("http://192.168.3.12:6080/int_api", json=param)
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
#     "clob": ['CONTENT'],
#     # "sql": "select 1 t from dual"
#     # "sql": "select title from Bz_Doc_Log where ROWNUM < 10"
#     "sql": """
# select *
#   from (select *
#           from (Select b.病人id,
#                        b.主页id,
#                        t.title       文档名称,
#                        a.title       文档类型,
#                        t.creat_time  创建时间,
#                        t.creator     文档作者,
#                        RAWTOHEX(t.id) 文档ID
#                        -- t.contenttext.getclobval() contenttext,
#                        -- t.content.getclobval() content
#                   From Bz_Doc_Log t
#                   left join Bz_Act_Log a
#                     on a.Id = t.Actlog_Id
#                   left join 病人变动记录@HISINTERFACE b
#                     on a.extend_tag = 'BD_' || to_char(b.id))
#          order by 创建时间)
#  where 病人ID = 564646 and 主页ID = 15
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
# # for rec in records:
# #     print(rec)
#
# print(records)


# Example text
text = "入院，已住院4。"

# Regular expression pattern to match departments
# pattern = r"于[\u4e00-\u9fa5\d\s年月日]+由([\u4e00-\u9fa5]+)转入([\u4e00-\u9fa5]+)"
pattern = r"由([\u4e00-\u9fa5]+)转入([\u4e00-\u9fa5]+)"

# Find all matches
matches = re.findall(pattern, text)

if len(matches) == 2:
    print(matches[0])
    print(matches[1])

print(matches)



import json
import time
from datetime import datetime, timedelta, date
import os, requests
import base64
from itertools import groupby

import redis
import netifaces as ni
import xlrd

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.critical_value import cv_config
from gylmodules.utils.db_utils import DbUtil
from suds.client import Client

from zeep import Client
from zeep.exceptions import Fault
from zeep.transports import Transport
import logging
import requests


data = {'test': 112}
print(data.get('tessst') or appt_config.APPT_URGENCY_LEVEL['green'])

num_people = 4
ans = [0] * num_people

print(ans)
#
#
# call_webservices('08ef7020-5a22-405a-a2ff-9f0259478e3d', '001', '123', '123')
#
#
# sched_data = [
#
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 1, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 1, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 2, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 2, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 3, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 3, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 4, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 4, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 5, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 5, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 6, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 6, 'ampm': 2, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 7, 'ampm': 1, 'state': 1},
#     {'did': 417, 'rid': 152, 'pid': 80, 'worktime': 7, 'ampm': 2, 'state': 1},
#
# ]
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
#
# for json_data in sched_data:
#     fileds = ','.join(json_data.keys())
#     args = str(tuple(json_data.values()))
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     insert_sql = f"INSERT INTO appt.appt_scheduling ({fileds}) VALUES {args}"
#     last_rowid = db.execute(sql=insert_sql, need_commit=True)
#     if last_rowid == -1:
#         del db
#         raise Exception("入库失败! sql = " + insert_sql)
# del db

# socket_push_url = 'http://120.194.96.67:6066/inter_socket_msg'
# socket_data = {"patient_name": '', "type": 400}
# data = {'msg_list': [{'socket_data': socket_data, 'pers_id': 'w1', 'socketd': 'w_site'}]}
# headers = {'Content-Type': 'application/json'}
# response = requests.post(socket_push_url, data=json.dumps(data), headers=headers)
# print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", socket_data,
#       "socket_id: ", 'w1')


#
# old_list = [
#     {"dept_id": 1, "advicel": [{'pay_id: ': 1, 'body': 'test1'}, {'pay_id: ': 2, 'body': 'test2'}]},
#     {"dept_id": 2, "advicel": [{'pay_id: ': 3, 'body': 'test1'}, {'pay_id: ': 4, 'body': 'test2'}]},
#     {"dept_id": 3, "advicel": [{'pay_id: ': 5, 'body': 'test1'}, {'pay_id: ': 6, 'body': 'test2'}]}
# ]
#
# # 按照 dept_id 分组
# grouped_dict = {}
# for item in old_list:
#     dept_id = item["dept_id"]
#     advicel = item["advicel"]
#
#     if dept_id not in grouped_dict:
#         grouped_dict[dept_id] = []
#
#     grouped_dict[dept_id].extend(advicel)
#
#
#
#
#
# old_list = [
#     {"dept_id": 1, "advicel": [{'pay_id: ': 1, 'body': 'test1'}, {'pay_id: ': 2, 'body': 'test2'}]},
#     {"dept_id": 2, "advicel": [{'pay_id: ': 3, 'body': 'test1'}, {'pay_id: ': 4, 'body': 'test2'}]},
#     {"dept_id": 3, "advicel": [{'pay_id: ': 5, 'body': 'test1'}, {'pay_id: ': 6, 'body': 'test2'}]}
# ]
#
#
# new_list = [
#     {"dept_id": 1, "advicel": [{'pay_id: ': 1, 'body': 'test1'}, {'pay_id: ': 2, 'body': 'test2'}, {'pay_id: ': 7, 'body': 'test2'}]},
#     {"dept_id": 2, "advicel": [{'pay_id: ': 3, 'body': 'test1'}, {'pay_id: ': 4, 'body': 'test2'}]},
#     {"dept_id": 3, "advicel": [{'pay_id: ': 5, 'body': 'test1'}, {'pay_id: ': 6, 'body': 'test2'}]},
#     {"dept_id": 4, "advicel": [{'pay_id: ': 8, 'body': 'test1'}, {'pay_id: ': 9, 'body': 'test2'}]},
# ]
# # 创建字典，以 dept_id 为键
# old_dict = {item['dept_id']: item['advicel'] for item in old_list}
# new_dict = {item['dept_id']: item['advicel'] for item in new_list}
#
# new_advices_grouped = {}
#
# # 比较每个部门的 advicel
# for dept_id, new_advicel in new_dict.items():
#     old_advicel = old_dict.get(dept_id, [])
#     old_advicel_set = {frozenset(advice.items()) for advice in old_advicel}
#     new_advicel_set = {frozenset(advice.items()) for advice in new_advicel}
#
#     added_advices = new_advicel_set - old_advicel_set
#     if added_advices:
#         new_advices_grouped[dept_id] = [dict(advice) for advice in added_advices]
#
# print(new_advices_grouped)
#
#
# param = {"type": "his_yizhu_info", 'patient_id': 3563057, 'doc_name': '夏明栓'}
# # new_doctor_advice = call_third_systems_obtain_data('his_info', 'his_yizhu_info', param)
# try:
#     # 发送 POST 请求，将字符串数据传递给 data 参数
#     response = requests.post(f"http://192.168.124.53:6080/his_info", json=param)
#     data = response.text
#     data = json.loads(data)
#     if type == 'his_visit_reg':
#         data = data.get('ResultCode')
#     else:
#         data = data.get('data')
# except Exception as e:
#     print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#
# new_doctor_advice = data
#
# # 按执行科室分组
# advice_dict = {}
# for item in new_doctor_advice:
#     key = item.get('执行部门ID')
#     if key not in advice_dict:
#         advice_dict[key] = []
#     advice_dict[key].append(item)
#
# dept_to_advice = {}
# for dept_id, advicel in advice_dict.items():
#     # 按 pay_id 排序，后按 pay_id 分组
#     advicel.sort(key=lambda x: x['NO'])
#     dept_to_advice[dept_id] = []
#     for key, group in groupby(advicel, key=lambda x: x['NO']):
#         group_list = list(group)
#         combined_advice_desc = '; '.join(item['检查明细项'] for item in group_list)
#         total_price = sum(item['实收金额'] for item in group_list)
#         json_data = {
#             'pay_id': group_list[0].get('NO'),
#             'advice_desc': combined_advice_desc,
#             'dept_id': group_list[0].get('执行部门ID'),
#             'dept_name': group_list[0].get('执行科室'),
#             'price': total_price
#         }
#         dept_to_advice[dept_id].append(json_data)
#
# print(dept_to_advice)

# pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
#                             db=appt_config.APPT_REDIS_DB, decode_responses=True)
#
# redis_client = redis.Redis(connection_pool=pool)
#
# ret = redis_client.hget(APPT_DOCTOR_ADVICE_KEY, "dfasdfa")
#
#
# print(ret)
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# query_sql = f'select pay_id from nsyy_gyl.appt_doctor_advice where appt_id = 22'
# advicel = db.query_all(query_sql)
#
# print(advicel)
#
#
#
# # 2. Load the Excel file file_path为文件绝对路径, num为sheet序号（从0算起）
# excel_path = '/Users/gaoyanliang/Downloads/检验检查3.xls'
# num = 0
#
# wbook = xlrd.open_workbook(excel_path)
# sheet = wbook.sheet_by_index(num)
#
# # 获取表格内容
# rows = sheet.nrows  # 获取表格的行数
# data_list = []  # 获取每行数据, 组成一个list
# for n in range(1, rows):
#     values = sheet.row_values(n)
#     data = {
#     "收费唯一标识": int(values[1]),
#     "NO": values[2],
#     "病人ID": int(values[3]),
#     "医嘱序号": int(values[5]),
#     "姓名": values[4],
#     "医嘱内容": values[6],
#     "检查明细项": values[7],
#     "执行科室": values[8],
#     "执行部门ID": values[9],
#     "实收金额": values[10]
#     }
#     data_list.append(data)
#     if n > 26:
#         break
#
# print('total: ', len(data_list))
# # for d in retl:
# #     print(d)


#
# sdfadfa = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
# print(max(1,2))
#
# num = 9
#
# while num > 2:
#     print('-2')
#     num -= 2
#
# print(num)
#
# merged_list_1 = []
# list1 = [1, 2, 3]
# list2 = [4, 5, 6]
# list3 = [7, 8, 9]
#
# string_list = [f"'{item}'" for item in list2]
#
# print(','.join(string_list))
#
# # 方法1: 使用 + 操作符
# merged_list_1 = merged_list_1 + list1
# merged_list_1 = merged_list_1 + list2
# merged_list_1 = merged_list_1 + list3
# print(f"使用 + 操作符合并: {merged_list_1}")
#
#
#
# # data = [{"cv_source": 4}, {"cv_source": 4}]
# data = [{'CV_SOURCE': 4}, {'CV_SOURCE': 4}]
#
# # 使用列表推导式和字典推导式将键转换为大写
# converted_data = [{k.upper(): v for k, v in item.items()} for item in data]
#
# # 打印结果
# print(converted_data)
#
#
# data = [{"cv_source": 4, "other_field": "value1"}, {"cv_source": 4, "other_field": "value2"}]
#
# # 使用列表推导式和条件语句进行选择性转换
# converted_data = [
#     {("CV_SOURCE" if k == "cv_source" else k): v for k, v in item.items()}
#     for item in data
# ]
#
# # 打印结果
# print(converted_data)
#
#
#
# print(time.time()*1000)
#
# print( datetime.now().strftime("%Y%m%d%H%M%S%f"))
#
# data = [{'price': '0.9'}, {'price': '0.8'}, {'price': '0.7'}]
#
# price = max(data, key=lambda x: float(x['price']))['price']
#
# print(price)




#
#
# def async_alert(type, id, msg):
#     def alert(type, id, msg):
#         key = cv_config.CV_SITES_REDIS_KEY[type] + str(id)
#         payload = {'type': 'popup', 'wiki_info': msg}
#         redis_client = redis.Redis(connection_pool=pool)
#         sites = redis_client.smembers(key)
#
#         records = []
#         if sites:
#             for ip in sites:
#                 auto_start_state = True
#                 url = f'http://{ip}:8085/opera_wiki'
#                 try:
#                     ret = requests.post(url, json=payload)
#                     if ret and 'code' in ret and '20000' in str(ret.get('code')):
#                         continue
#                 except Exception as e:
#                     print(f'向 {ip} 发送危机值弹框通知失败，准备远程启动危机值程序, ip 信息： ', '病区 ' if int(type) == 1 else '科室 ', id)
#
#                 url = f'http://{ip}:8091/push?r=D:/Softwares/WeiJiZhi/start.bat'
#                 try:
#                     ret = requests.post(url)
#                     if ret and 'code' in ret and '20000' not in str(ret.get('code')):
#                         auto_start_state = False
#                         print(f'{ip} 危机值程序远程启动失败 ret = {ret}')
#                 except Exception as e:
#                     auto_start_state = False
#                     print(f'{ip} 危机值程序远程启动失败')
#
#                 if not auto_start_state:
#                     records.append({'ip': ip, 'type': type, 'type_id': id, 'time': str(datetime.now())[:19]})
#
#     thread_b = threading.Thread(target=alert, args=(type, id, msg))
#     thread_b.start()





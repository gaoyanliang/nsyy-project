import json
import time
from datetime import datetime, date
import os
import requests
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

data = [
    {'id': 34, 'appt_id': 273, 'pay_id': 'Y0589907', 'advice_desc': '静脉注射(或静脉采血); 真空采血管(特殊采血管）',
     'dept_id': 144, 'dept_name': '医学检验科', 'price': 6.8000, 'state': 0},
    {'id': 35, 'appt_id': 273, 'pay_id': 'Y0589911',
     'advice_desc': '梅毒螺旋体特异抗体测定; 丙型肝炎抗体测定(Anti--HCV); 人免疫缺陷病毒抗体测定(Anti-HIV)指金标法、硒标法; 乙型肝炎表面抗原测定(HBsAg)',
     'dept_id': 144, 'dept_name': '医学检验科', 'price': 65.3000, 'state': 0},
    {'id': 36, 'appt_id': 274, 'pay_id': 'Y0589909', 'advice_desc': '还少胶囊', 'dept_id': 245, 'dept_name': '门诊药房',
     'price': 40.3000, 'state': 0},
    {'id': 37, 'appt_id': 275, 'pay_id': 'Y0589912', 'advice_desc': 'X线计算机体层(CT)扫描(16-40层)', 'dept_id': 68643,
     'dept_name': '16排CT', 'price': 203.0000, 'state': 0},
    {'id': 38, 'appt_id': 276, 'pay_id': 'Y0589906', 'advice_desc': '精液质量与功能分析', 'dept_id': 94683,
     'dept_name': '生殖男科门诊', 'price': 85.5000, 'state': 0},
    {'id': 39, 'appt_id': 276, 'pay_id': 'Y0589908', 'advice_desc': '阴茎超声血流图检查', 'dept_id': 94683,
     'dept_name': '生殖男科门诊', 'price': 118.3200, 'state': 0}
]

# 用于存储拼接后的结果
result = {}

# 遍历数据
for record in data:
    appt_id = record['appt_id']
    advice_desc = record['advice_desc']

    if appt_id in result:
        result[appt_id]['advice_desc'] += '; ' + advice_desc
    else:
        result[appt_id] = record.copy()
        result[appt_id]['advice_desc'] = advice_desc

# 转换结果为列表格式
result_list = list(result.values())

# 输出结果
for r in result_list:
    print(r)

#
# # 示例 room_dict 数据结构
# room_dict = {
#     'room1': {
#         '2024-06-11': {'1': {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2},
#                        '2': {9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2}},
#         '2024-06-12': {'1': {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2},
#                        '2': {9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2}},
#         '2024-06-13': {'1': {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2},
#                        '2': {9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2}},
#     }
# }
#
# periodd = {1: [1, 2, 3, 4, 5, 6, 7, 8], 2: [9, 10, 11, 12, 13, 14, 15, 16]}  # 1 上午 2 下午 3 全天
# periodd[3] = periodd[1] + periodd[2]
#
# def check_appointment_quantity(book_info):
#     def find_next_available(date, next_slot, period_list, find_in):
#         capdict_am = room_dict[book_info['room']][date]['1'] if room_dict[book_info['room']][date].get('1') else {}
#         capdict_pm = room_dict[book_info['room']][date]['2'] if room_dict[book_info['room']][date].get('2') else {}
#         for s in period_list:
#             if s <= 8 and find_in in (1, 3):  # 上午时段
#                 if s >= next_slot and capdict_am.get(s, 0) > 0:
#                     return date, s
#             elif s > 8 and find_in in (2, 3):  # 下午时段
#                 if s >= next_slot and capdict_pm.get(s, 0) > 0:
#                     return date, s
#         return None, None
#
#     room = book_info['room']
#     book_date = book_info.get('date', None)
#     period = int(book_info.get('period')) if book_info.get('period') else 3
#
#     current_slot = appt_config.appt_slot_dict[datetime.now().hour]
#     # 如果指定了日期，直接在指定日期查找可用时段
#     if book_date:
#         next_date, next_slot = find_next_available(book_date, current_slot, periodd[period], period)
#         if not next_slot:
#             raise Exception("No available period found for the specified date and period")
#         return next_date, next_slot
#
#     today = datetime.today().strftime("%Y-%m-%d")
#     last_date = book_info.get('last_date', today)
#     last_slot = book_info.get('last_slot', None)
#     # 查找从last_date和last_slot之后可用的时间和时间段
#     for date in sorted(room_dict[room].keys()):
#         if last_date and date < last_date:
#             continue
#         if date == last_date:
#             slot_to_check = last_slot + 1 if last_slot is not None else current_slot
#             next_date, next_slot = find_next_available(date, slot_to_check, periodd[period], period)
#         else:
#             next_date, next_slot = find_next_available(date, 1, periodd[period], period)
#
#         if next_slot:
#             return next_date, next_slot
#
#     # return None, "No available period found"
#     raise Exception("No available period found")
#
#
# date, period = check_appointment_quantity({
#     'date': '2024-06-11',
#     'room': 'room1',
#     # 'last_date': '2024-06-12',  # 上一次预约的日期
#     # 'last_slot': 10,             # 上一次预约的时间段
#     'period': 2                # 本次预约的时段，1 表示上午
# })
# print(f"Date: {date}, Period: {period}")
#
# date, period = check_appointment_quantity({
#     # 'date': '2024-06-11',
#     'room': 'room1',
#     'last_date': '2024-06-12',  # 上一次预约的日期
#     'last_slot': 10,             # 上一次预约的时间段
#     # 'period': 2                # 本次预约的时段，1 表示上午
# })
# print(f"Date: {date}, Period: {period}")
#




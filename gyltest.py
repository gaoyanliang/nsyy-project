import json
import time
from datetime import datetime, date
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

appt_recordl = [
    {'id': 'id1', 'name': 'name1', 'age': 'age1'},
    {'id': 'id2', 'name': 'name2', 'age': 'age2'},
    {'id': 'id3', 'name': 'name3', 'age': None},
    {'id': 'id4', 'name': 'name4', 'age': 'age4'}
]

record_dict = {(d['id'], d['name']): d for d in appt_recordl if d.get('age')}

if ('id1', 'name1') in record_dict:
    print('afdaf')


data = {'危机值': '测试'}

if '测试' in data.get('危机值'):
    print('--------------------')



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




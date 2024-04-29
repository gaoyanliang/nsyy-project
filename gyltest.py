import json
import time
from datetime import datetime, timedelta

import redis
import netifaces as ni


schedule = {
    '2024-04-24': {
        '1': {'date': 'am', 'quantity': 16, 'doctor': {'id': 5, 'doctor_id': None, 'doctor_name': '刘正廷', 'dept_id': None, 'dept_name': None, 'consultation_room': '2001', 'proj_id': 1, 'day_of_week': 3, 'period': 1}},
        '2': {'date': 'pm', 'quantity': 16, 'doctor': {'id': 6, 'doctor_id': None, 'doctor_name': '刘正廷', 'dept_id': None, 'dept_name': None, 'consultation_room': '2001', 'proj_id': 1, 'day_of_week': 3, 'period': 2}}
    },
    '2024-04-25': {
        '1': {'date': 'am', 'quantity': 15, 'doctor': {'id': 7, 'doctor_id': None, 'doctor_name': '刘正廷', 'dept_id': None, 'dept_name': None, 'consultation_room': '2001', 'proj_id': 1, 'day_of_week': 4, 'period': 1}},
        '2': {'date': 'pm', 'quantity': 16, 'doctor': {'id': 8, 'doctor_id': None, 'doctor_name': '刘正廷', 'dept_id': None, 'dept_name': None, 'consultation_room': '2001', 'proj_id': 1, 'day_of_week': 4, 'period': 2}}
    },
    # 其他日期...
}

bookable_list = []
for date, slots in schedule.items():
    for slot, info in slots.items():
        info['date'] = date
        info['slot'] = slot
        bookable_list.append(info)

print(bookable_list)

for b in bookable_list:
    print(b)


# p1 预约时间 p2 签到时间 p3 紧急程度
data = [
    {'appt_date_period': 1, 'sign_in_num': 4, 'urgency_level': 1},
    {'appt_date_period': 1, 'sign_in_num': 5, 'urgency_level': 2},
    {'appt_date_period': 1, 'sign_in_num': 8, 'urgency_level': 3},
    {'appt_date_period': 2, 'sign_in_num': 1, 'urgency_level': 1},
    {'appt_date_period': 2, 'sign_in_num': 7, 'urgency_level': 2}
]

data_sorted = sorted(data, key=lambda x: (-x['urgency_level'], x['appt_date_period'], x['sign_in_num']))

test = [{'test': 1}, {'ssss': 2}]

for d in data_sorted:
    d['test'] = test

for d in data_sorted:
    print(d)


# p1 预约时间 p2 签到时间 p3 紧急程度
data = [
    {'appt_date_period': 1, 'sign_in_num': 4, 'urgency_level': 1},
    {'appt_date_period': 1, 'sign_in_num': 5, 'urgency_level': 2},
    {'appt_date_period': 1, 'sign_in_num': 8, 'urgency_level': 3},
    {'appt_date_period': 2, 'sign_in_num': 1, 'urgency_level': 1},
    {'appt_date_period': 2, 'sign_in_num': 7, 'urgency_level': 2}
]

print(set([1,4,5]) - set([1,2,3]))
print(set([1,2,3]) - set([1,4,5]))





# 获取本地默认网关的接口名称
default_gateway = ni.gateways()['default'][ni.AF_INET][1]
# 获取该接口的 IP 地址
local_ip = ni.ifaddresses(default_gateway)[ni.AF_INET][0]['addr']
print(local_ip)


print('-----------------------------------')

from itertools import groupby

data = [
    {"date": "2024-04-25", "doctor": "刘正廷", "period": "1", "proj_id": 1, "proj_name": "全科医学科门诊", "quantity": 15, "room": "2001"},
    {"date": "2024-04-25", "doctor": "刘正廷", "period": "2", "proj_id": 1, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2001"},
    {"date": "2024-04-26", "doctor": "刘正廷", "period": "1", "proj_id": 1, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2001"},
    {"date": "2024-04-26", "doctor": "刘正廷", "period": "2", "proj_id": 1, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2001"},
    {"date": "2024-04-25", "doctor": "来大双", "period": "1", "proj_id": 2, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2702"},
    {"date": "2024-04-25", "doctor": "李新旗", "period": "2", "proj_id": 2, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2702"},
    {"date": "2024-04-26", "doctor": "来大双", "period": "1", "proj_id": 2, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2702"},
    {"date": "2024-04-26", "doctor": "来大双", "period": "2", "proj_id": 2, "proj_name": "全科医学科门诊", "quantity": 16, "room": "2702"},
]

# 对数据按照日期进行分组
sorted_data = sorted(data, key=lambda x: (x['date'], x['period']))
for item in sorted_data:
    print(item)

grouped_data = [list(group) for key, group in groupby(sorted_data, key=lambda x: x['date'])]
for item in grouped_data:
    print(item)




# 连接到 Redis
# r = redis.Redis(host='localhost', port=6379, db=0)
# r.flushdb()



from itertools import groupby

data = [
    {'date': '2024-04-25', 'doctor': '刘正廷', 'period': '1', 'proj_id': 1, 'proj_name': '全科医学科门诊', 'quantity': 15, 'room': '2001'},
    {'date': '2024-04-25', 'doctor': '来大双', 'period': '1', 'proj_id': 2, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2702'},
    {'date': '2024-04-25', 'doctor': '刘正廷', 'period': '2', 'proj_id': 1, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2001'},
    {'date': '2024-04-25', 'doctor': '李新旗', 'period': '2', 'proj_id': 2, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2702'},
    {'date': '2024-04-26', 'doctor': '刘正廷', 'period': '1', 'proj_id': 1, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2001'},
    {'date': '2024-04-26', 'doctor': '来大双', 'period': '1', 'proj_id': 2, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2702'},
    {'date': '2024-04-26', 'doctor': '刘正廷', 'period': '2', 'proj_id': 1, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2001'},
    {'date': '2024-04-26', 'doctor': '来大双', 'period': '2', 'proj_id': 2, 'proj_name': '全科医学科门诊', 'quantity': 16, 'room': '2702'}
]


# 先对数据进行排序
sorted_data = sorted(data, key=lambda x: x['date'])

# 按 date 分组
grouped_data = {}
for key, group in groupby(sorted_data, key=lambda x: (x['date'], x['period'])):
    grouped_data[key] = list(group)

# 输出结果

print('----------------------------------')
print('----------------------------------')
for date, entries in grouped_data.items():
    print(date)
    print(entries)




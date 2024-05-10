import json
import time
from datetime import datetime, timedelta, date
import re

import redis
import netifaces as ni

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil


s = '   df  ads    '
result = re.sub(r'^\s+|\s+$', '', s)
print(result)
result = ' '.join(s.strip().split())
print(result)

print(date.today())

wait_list = []

if wait_list and wait_list[0].get('state'):
    print("sfad")

wait_list.append({"state": 1})

if wait_list and wait_list[0].get('state'):
    print("fasdfasdfadsfadf")

# 定义一个包含字段的字典
my_dict = {
    'name': 'John',
    'age': 30,
    'city': 'New York',
    'test': 1
}

name, age = my_dict.get('name'), my_dict.get('age')

# 输出移除的字段值
print("name: ", name, 'age: ', age)

wait_list = []
if wait_list:
    print('11111111111')
wait_list.append(1)
if wait_list:
    print('22222222222')




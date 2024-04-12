import time
from datetime import datetime
import redis

from gylmodules.critical_value import cv_config

# pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
#                             db=cv_config.CV_REDIS_DB, decode_responses=True)
#
# redis_client = redis.Redis(connection_pool=pool)
#
# redis_client.delete('adfa')


testd = [1,1,1,1]
print(list(set(testd)))


query_sql = """
select a.*, 2 cv_source from {inspection_system_table} a 
            where ({idrsa} alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss')) and VALIDFLAG=1 and HISCHECKDT1=0
            union 
            select b.*, 3 cv_source from {imaging_system_table} b 
            where ({idrsb} alertdt > to_date('{start_t}', 'yyyy-mm-dd hh24:mi:ss')) and VALIDFLAG=1 and HISCHECKDT1=0
"""

print(query_sql)


print(query_sql.replace('{idrsa}', '1,2,3,4,5'))

print(set([1,4,5]) - set([1,2,3]))
print(set([1,2,3]) - set([1,4,5]))

print(str(datetime.now())[:19])
cvd = {'a': 1, 'b': 2, 'c': 3, 'd': '4'}

fileds = [key for key in cvd.keys()]
print(fileds)

print("--------")


# print(','.join(cvd.keys()))
# print(str(tuple(cvd.values())))


keys = ','.join(cvd.keys())  # a,b,c,d
values = tuple(cvd.values())  # (1, 2, 3, '4')
# 将键和值按指定格式拼接成字符串
key_string = ', '.join([f"{key} = {value}" for key, value in cvd.items()])  # a = 1, b = 2, c = 3, d = 4

print(keys)
print(values)
print(key_string)




# 获取当前时间戳
timestamp = time.time()
print(timestamp)

# 将时间戳转换为本地时间的结构化表示
local_time = time.localtime(timestamp)
print(local_time)
# 格式化时间
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
print(formatted_time)

print(time.localtime(1712885368))
print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(1712885368)))

# 获取当前时间戳，并将其转换为整数
timestamp = int(time.time())
print(timestamp)




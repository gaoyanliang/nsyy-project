import json

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from gylmodules.critical_value import cv_config
import asyncio
from datetime import datetime
import redis
import aiohttp
import threading

from apscheduler.schedulers.background import BackgroundScheduler


pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)
test_scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

redis_client = redis.Redis(connection_pool=pool)

sites = redis_client.smembers('CV_SITES_DEPT_300')

sites1 = redis_client.smembers('CV_SITES_WARD_1000962')

# sites.add('192.168.124.24')

merged_set = sites.union(sites1)


print()






times = 0

# ids = (0, 1)
#
# if ids[0]:
#     print('---------')
# if ids[1]:
#     print('=========')

ids = (1, 1)

if ids[0] is None or int(ids[0]):
    print('---------')
if ids[1]:
    print('=========')





#
# def async_alert():
#     def alertttt():
#         payload = {'type': 'popup', 'wiki_info': "msg"}
#         redis_client = redis.Redis(connection_pool=pool)
#         sites = redis_client.smembers("CV_SITES_DEPT_94143")
#         if sites:
#             print(threading.current_thread(),  ' 查询到 ', len(sites), ' 个 ip 地址', sites, '   ', datetime.now())
#             # 设置 requests 的连接池
#             retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504, 20003])
#             adapter = HTTPAdapter(max_retries=retries, pool_connections=15, pool_maxsize=15)
#
#             for ip in sites:
#                 url = f'http://{ip}:8085/opera_wiki'
#                 session = None
#                 try:
#                     session = requests.Session()
#                     session.mount('http://', adapter)
#                     response = session.post(url, json={'type': 'stop'})  # 连接超时5秒，读取超时10秒
#                     response.raise_for_status()  # 如果响应状态码不是 200-400 之间，产生异常
#
#                     response = session.post(url, json=payload, timeout=(3, 3))  # 连接超时5秒，读取超时10秒
#                     response.raise_for_status()  # 如果响应状态码不是 200-400 之间，产生异常
#
#                     print(threading.current_thread(), " 请求成功 url = ", url)
#                 except requests.exceptions.Timeout:
#                     print(threading.current_thread(), " 请求超时 url = ", url)
#                     pass
#                 except requests.exceptions.RequestException as e:
#                     print(threading.current_thread(), " 请求失败 url = ", url, payload, '    ', datetime.now())
#                     pass
#                 finally:
#                     if session:
#                         session.close()  # 确保连接关闭
#
#     thread_b = threading.Thread(target=alertttt)
#     thread_b.start()
#
#
# def test_task():
#     global times
#     times = times + 1
#     print(threading.current_thread(), f"test_task {times}")
#     for i in range(10):
#         async_alert()
#
#
# def schedule_task():
#     test_scheduler.add_job(test_task, trigger='interval', seconds=10, max_instances=20,
#                                 id='cv_timeout')
#     test_scheduler.start()
#
#     while True:
#         pass
#
#
# schedule_task()











#
# async def send_request(session, url, payload):
#     try:
#         async with session.post(url, json=payload, timeout=2) as response:
#             response.raise_for_status()
#             print(threading.current_thread(), f"通知请求成功: {url} {payload} ", datetime.now())
#     except asyncio.TimeoutError:
#         print(threading.current_thread(), f"请求超时: {url} {payload} ", datetime.now())
#     except aiohttp.ClientError as e:
#         print(threading.current_thread(), f"请求失败: {url} {payload} ", datetime.now())
#
#
# async def alertttt():
#     payload = {'type': 'popup', 'wiki_info': "msg"}
#     redis_client = redis.Redis(connection_pool=pool)
#     sites = redis_client.smembers("CV_SITES_DEPT_94143")
#     if sites:
#         print(threading.current_thread(), ' 查询到 ', len(sites), ' 个 ip 地址', sites, ' ', datetime.now())
#         async with aiohttp.ClientSession() as session:
#             stop_tasks = []
#             popup_tasks = []
#             for ip in sites:
#                 url = f'http://{ip}:8085/opera_wiki'
#                 stop_tasks.append(send_request(session, url, {'type': 'stop'}))
#                 popup_tasks.append(send_request(session, url, payload))
#             await asyncio.gather(*stop_tasks)
#             await asyncio.sleep(0.3)  # 间隔 100 毫秒
#             await asyncio.gather(*popup_tasks)
#
#
#
# def async_alert():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(alertttt())
#     loop.close()
#
# def test_task():
#     global times
#     times += 1
#     print(f"test_task {times} ", datetime.now())
#     async_alert()
#
#

#
#
#





















import json
import time
from datetime import datetime, timedelta, date
import os, requests
import base64

import redis
import netifaces as ni

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil





print(time.time()*1000)

print( datetime.now().strftime("%Y%m%d%H%M%S%f"))

main_dir = '/Users/gaoyanliang/nsyy/综合预约/坐诊医生'

db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
            global_config.DB_DATABASE_GYL)

json_datal = []
for root, dirs, files in os.walk(main_dir):
    # root 是当前目录路径
    # dirs 是当前目录下的子目录列表
    # files 是当前目录下的文件列表

    # 我们只关心第一层子目录，因此直接跳过 root 本身
    if root == main_dir:
        continue

    # 从当前目录路径中提取子目录名
    subdir_name = os.path.basename(root)

    for file in files:
        # 获取文件名，不包含扩展名
        file_name = os.path.splitext(file)[0]

        server_path = '/home/cc/att/public/坐诊医生/' + subdir_name + '/' + file

        # 将字符串转换为字节
        byte_data = server_path.encode('utf-8')
        # 对字节进行Base64编码
        base64_encoded = base64.b64encode(byte_data)
        # 将Base64编码的字节转换回字符串
        encoded_string = base64_encoded.decode('utf-8')

        json_datal.append({
            'room': str(subdir_name),
            'name': file_name,
            'photo': encoded_string
        })
        print(subdir_name, file_name, server_path, encoded_string)

for json_data in json_datal:
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_info ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("入库失败! sql = " + insert_sql)





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





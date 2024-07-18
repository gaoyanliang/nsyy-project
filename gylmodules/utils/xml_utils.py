import xml.etree.ElementTree as ET
import os
import base64
import requests
import json
import pandas as pd

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil


# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)

# # 查询数据库中存储的医生信息
# db = DbUtil('192.168.3.12', "gyl", "123456", 'nsyy_gyl')
# doctorl = db.query_all(f'select * from nsyy_gyl.appt_doctor')
#
# doctord = {}
# for item in doctorl:
#     doctord[item.get('his_name')] = item



my_set = set()
my_set1 = set()
items = {}
start_id = [0, 100, 200, 300, 400, 500]
index = 1

# 查询 his 中所有门诊医生的信息，并按照名字排序
ret = []
for id in start_id:
    data = None
    try:
        # 发送 POST 请求，将字符串数据传递给 data 参数
        response = requests.post(f"http://192.168.124.53:6080/his_socket", json={
            "type": "his_mz_source_check",
            "start": id
        })
        data = response.text
        data = json.loads(data)
        data = data.get('data')
    except Exception as e:
        print('调用第三方系统方法失败 ' + e.__str__())

    # with open(file_path, 'r', encoding='gb2312', errors='ignore') as file:
    #     xml_data = file.read()
    if not data:
        continue
    root = ET.fromstring(data)

    for item in root.findall('.//Item'):
        price = "%.4f" % float(item.find('Price').text)
        json_data = {
            'appointment_id': int(item.find('AsRowid').text),
            'dept_id': int(item.find('DepID').text),
            'dept_name': item.find('DepName').text.strip(),
            'doctor_id': int(item.find('MarkId').text),
            'doctor_name': item.find('MarkDesc').text.strip(),
            'doctor_type': item.find('SessionType').text.strip(),
            'price': price,
        }
        ret.append(json_data)

sorted_data = sorted(ret, key=lambda x: x["doctor_name"])


# last_data = []
# for index, value in enumerate(sorted_data):
#     if index > 0 and value.get('doctor_name') == sorted_data[index-1].get('doctor_name'):
#         last_data.append(sorted_data[index-1])
#         last_data.append(value)
#
# print()

# 将数据转换为 DataFrame
# df = pd.DataFrame(last_data)
# # 将 DataFrame 写入 Excel 文件
# output_file = 'appointments.xlsx'
# df.to_excel(output_file, index=False)

# print(f"数据已写入 {output_file}")

# 多身份医生
# index = 1
# for json_data in last_data:
#     print(index, '  ', json_data)
#     index = index + 1

print('======================================')
print('======================================')
print('======================================')
print('======================================')
index = 1
for json_data in sorted_data:
    print(index, '  ', json_data)

    # 对比医生挂号信息是否有变化
    # doc = doctord.get(json_data.get('doctor_name'))
    # if doc:
    #     if int(doc.get('dept_id')) != int(json_data.get('dept_id')) or int(doc.get('appointment_id')) != int(json_data.get('appointment_id')):
    #         print('医生信息有误 old ： ', doc)
    #         print('医生信息有误 new： ', json_data)
    #         print()
    #         print()
    # else:
    #     print('不存在医生： ', json_data)
    #     print()
    #     print()



    index = index + 1
    # fileds = ','.join(json_data.keys())
    # args = str(tuple(json_data.values()))
    # insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_info ({fileds}) VALUES {args}"
    # last_rowid = db.execute(sql=insert_sql, need_commit=True)
    # if last_rowid == -1:
    #     del db
    #     raise Exception("入库失败! sql = " + insert_sql)

# 缓存医生图片
# main_dir = '/Users/gaoyanliang/nsyy/综合预约/医生图片'
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
# #
# query_sql = 'select doc_his_name, doc_name, consultation_room as room FROM nsyy_gyl.appt_doctor_sched GROUP BY doc_his_name, doc_name, consultation_room '
# docl = db.query_all(query_sql)
#
# docd = {}
# for item in docl:
#     docd[item.get('doc_name') + item.get('room')] = item.get('doc_his_name')
#
# json_datal = []
# for root, dirs, files in os.walk(main_dir):
#     # root 是当前目录路径
#     # dirs 是当前目录下的子目录列表
#     # files 是当前目录下的文件列表
#
#     # 我们只关心第一层子目录，因此直接跳过 root 本身
#     # if root == main_dir:
#     #     continue
#
#     # 从当前目录路径中提取子目录名
#     subdir_name = os.path.basename(root)
#
#     for file in files:
#         # 获取文件名，不包含扩展名
#         file_name = os.path.splitext(file)[0]
#
#         server_path = '/home/cc/att/public/doc/' + file
#
#         encoded_string = base64.b64encode(server_path.encode("utf-8")).decode().replace("+", "%2B")
#
#         update_sql = f'UPDATE appt.appt_doctor SET photo = \'{encoded_string}\' WHERE his_name = \'{file_name}\' '
#         db.execute(sql=update_sql, need_commit=True)


# data = {
#     'doc_name': file_name,
#     'photo': encoded_string
# }
# json_datal.append(data)
#
# print(data)

# for json_data in json_datal:
#     fileds = ','.join(json_data.keys())
#     args = str(tuple(json_data.values()))
#     insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_photo ({fileds}) VALUES {args}"
#     last_rowid = db.execute(sql=insert_sql, need_commit=True)
#     if last_rowid == -1:
#         del db
#         raise Exception("入库失败! sql = " + insert_sql)


#
# import base64
#
# # 原始数据
# original_data = "/home/cc/att/public/doc_photo/default.jpg"
#
# # 编码过程
# encoded_data = base64.b64encode(original_data.encode('utf-8')).decode('utf-8')
# print(f"Encoded Data: {encoded_data}")
#
# # 解码过程
# decoded_data = base64.b64decode(encoded_data.encode('utf-8')).decode('utf-8')
# print(f"Decoded Data: {decoded_data}")
#
# encoded_data = 'L2hvbWUvY2MvYXR0L3B1YmxpYy9kb2NfcGhvdG8vZGVmYXVsdC5qcGcK'
#
# decoded_data = base64.b64decode(encoded_data.encode('utf-8')).decode('utf-8')
# print(f"Decoded Data: {decoded_data}")
#
#
#
#
# # 假设 path 是你要编码的字符串
# path = "/home/cc/att/public/doc_photo/default.jpg"
#
# # 进行 Base64 编码
# encoded_path = base64.b64encode(path.encode("utf-8")).decode("utf-8")
#
# print(encoded_path)
#
# # 将 Base64 编码结果中的 + 替换为 %2B
# encoded_path_safe = encoded_path.replace("+", "%2B")
#
# print(f"原始路径: {path}")
# print(f"Base64 编码（替换 + 为 %2B 后）: {encoded_path_safe}")
#
#
# path = "/home/cc/att/public/doc_photo/default.jpg"
#
#
# # 将字符串转换为字节
# byte_data = path.encode('utf-8')
# # 对字节进行Base64编码
# base64_encoded = base64.b64encode(byte_data)
# # 将Base64编码的字节转换回字符串
# encoded_string = base64_encoded.decode('utf-8')
#
# print(encoded_string)
#
# # print(base64.b64encode(path.encode("utf-8")).decode().replace("+", "%2B"))
# #
# #
# # print(base64.b64encode(path.encode("utf-8")).decode().replace("+", "%2B"))


# server_path1 = '/home/cc/att/public/doc/贾玲.png'
# server_path2 = '/home/cc/att/public/doc/席三营.png'
#
#
# print(base64.b64encode(server_path1.encode("utf-8")).decode().replace("+", "%2B"))
# print(base64.b64encode(server_path2.encode("utf-8")).decode().replace("+", "%2B"))

# update_sql = f'UPDATE appt.appt_doctor SET photo = \'{encoded_string}\' WHERE his_name = \'{file_name}\' '
# db.execute(sql=update_sql, need_commit=True)

import xml.etree.ElementTree as ET
import os
import base64

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

# # Open the XML file with the appropriate encoding
# # with open('/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/101.xml', 'r', encoding='gb2312') as file:
#
# file_list = ['/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/1.xml',
#              '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/101.xml',
#              '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/201.xml',
#              '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/301.xml',
#              '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/401.xml']
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# my_set = set()
# my_set1 = set()
# items = {}
# for file_path in file_list:
#
#     with open(file_path, 'r', encoding='gb2312', errors='ignore') as file:
#         xml_data = file.read()
#     root = ET.fromstring(xml_data)
#
#     for item in root.findall('.//Item'):
#         price = "%.4f" % float(item.find('Price').text)
#         json_data = {
#             'appointment_id': int(item.find('AsRowid').text),
#             'dept_id': int(item.find('DepID').text),
#             'dept_name': item.find('DepName').text.strip(),
#             'doctor_id': int(item.find('MarkId').text),
#             'doctor_name': item.find('MarkDesc').text.strip(),
#             'doctor_type': item.find('SessionType').text.strip(),
#             'price': price,
#         }
#         # print(json_data)
#         set_data = tuple(json_data.items())
#         if set_data in my_set:
#             continue
#         my_set.add(set_data)
#
#         copy_data = json_data.copy()
#         copy_data.pop('price')
#         copy_data.pop('doctor_type')
#         copy_data.pop('appointment_id')
#         copy_data = tuple(copy_data.items())
#
#         if copy_data in my_set1:
#             val = items[copy_data]
#             if price > val.get('price'):
#                 items[copy_data] = json_data
#         else:
#             items[copy_data] = json_data
#             my_set1.add(copy_data)
#
#
# for _, json_data in items.items():
#     fileds = ','.join(json_data.keys())
#     args = str(tuple(json_data.values()))
#     insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_info ({fileds}) VALUES {args}"
#     last_rowid = db.execute(sql=insert_sql, need_commit=True)
#     if last_rowid == -1:
#         del db
#         raise Exception("入库失败! sql = " + insert_sql)
#





# 缓存医生图片
main_dir = '/Users/gaoyanliang/nsyy/综合预约/doc_photo'

db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
            global_config.DB_DATABASE_GYL)

query_sql = 'select doc_his_name, doc_name, consultation_room as room FROM nsyy_gyl.appt_doctor_sched GROUP BY doc_his_name, doc_name, consultation_room '
docl = db.query_all(query_sql)

docd = {}
for item in docl:
    docd[item.get('doc_name') + item.get('room')] = item.get('doc_his_name')

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

        server_path = '/home/cc/att/public/doc_photo/' + subdir_name + '/' + file


        # # 将字符串转换为字节
        # byte_data = server_path.encode('utf-8')
        # # 对字节进行Base64编码
        # base64_encoded = base64.b64encode(byte_data)
        # # 将Base64编码的字节转换回字符串
        # encoded_string = base64_encoded.decode('utf-8')

        encoded_string = base64.b64encode(server_path.encode("utf-8")).decode().replace("+", "%2B")

        json_datal.append({
            'room': str(subdir_name),
            'doc_name': file_name,
            'doc_his_name': docd.get(file_name+str(subdir_name)) if docd.get(file_name+str(subdir_name)) else '',
            'photo': encoded_string
        })
        print(encoded_string)

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

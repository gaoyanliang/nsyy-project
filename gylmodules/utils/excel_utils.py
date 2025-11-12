import xlrd
import re

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

"""
将医生排班数据写入数据库
"""

# 1. 加载项目
db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

query_sql = 'select id, proj_room from nsyy_gyl.appt_project'
projl = db.query_all(query_sql)
projd = {}
for proj in projl:
    projd[proj.get('proj_room')] = proj.get('id')
del db


# 2. Load the Excel file file_path为文件绝对路径, num为sheet序号（从0算起）
excel_path = '/Users/gaoyanliang/Downloads/副本2024门诊4月份排班  .xls'
num = 1

wbook = xlrd.open_workbook(excel_path)
sheet = wbook.sheet_by_index(num)

# 获取表格内容
rows = sheet.nrows  # 获取表格的行数
data_list = []  # 获取每行数据, 组成一个list
for n in range(2, rows):
    values = sheet.row_values(n)
    data_list.append(values)

db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
            global_config.DB_DATABASE_GYL)
name, room, period, retl = '', '', '', []
for d in data_list:
    if d[0]:
        name = d[0]
    if d[1]:
        room = d[1]
    if d[2]:
        period = d[2]

    if '科室' in name \
            or '外科系统' in name \
            or '烧伤门诊' in name \
            or '眼科门诊（8号楼1楼）' in name \
            or '神经内科门诊（2号楼2楼西区23通道）' in name \
            or '胸痛门诊' in name:
        continue

    proj_id = projd[room]
    for i in range(3, 10):
        if d[i]:
            # print(f"Name: {name:^10} Room: {room:^10} ProjId: {proj_id:^10} Period: {period:^10} Day1: {d[i]:^10} ")
            json_data = {
                'doctor_name': re.sub(r'^\s+|\s+$', '', d[i]),
                'consultation_room': room,
                'proj_id': int(proj_id),
                'day_of_week': i - 2,
                'period': 1 if period in '上午' else 2
            }
            retl.append(json_data)
            fileds = ','.join(json_data.keys())
            args = str(tuple(json_data.values()))
            insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_sched_copy1 ({fileds}) VALUES {args}"
            last_rowid = db.execute(sql=insert_sql, need_commit=True)
            if last_rowid == -1:
                del db
                raise Exception("入库失败! sql = " + insert_sql)

del db
print('total: ', len(retl))
# for d in retl:
#     print(d)







# 新增一列再写回表格
# import pandas as pd
#
# # 定义文件路径和工作表索引
# excel_path = '/Users/gaoyanliang/Downloads/副本2025.1-9月扣款项目明细（所有医保）.xls'
# num = 0
#
# # 读取Excel文件
# df = pd.read_excel(excel_path, sheet_name=num)
#
# # 假设第一列的名称为 'Column1'，如果没有列名，可以使用默认的列名
# # 如果没有列名，可以通过 df.columns 查看列名
# first_column_name = df.columns[13]
#
# # value_mapping = {
# #     'A': 'ValueA',
# #     'B': 'ValueB',
# #     'C': 'ValueC',
# #     # 添加更多的映射关系
# # }
#
# # 创建新列 'NewColumn' 并根据第一列的内容赋值
# df['NewColumn'] = df[first_column_name].map(value_mapping).fillna('DefaultValue')
#
# # 打印DataFrame以查看结果
# print(df)
#
# # 将修改后的数据写回到新的Excel文件中
# output_path = '/Users/gaoyanliang/Downloads/副本2025.1-9月扣款项目明细（所有医保）_updated.xlsx'
#
# # 使用openpyxl引擎写入Excel文件
# df.to_excel(output_path, index=False, engine='openpyxl')
#
# print(f"数据已成功写入 {output_path}")



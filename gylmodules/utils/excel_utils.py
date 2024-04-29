import pandas as pd

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

# 从 Excel 文件中读取数据并转换为 DataFrame
# df = pd.read_excel('/Users/gaoyanliang/nsyy/综合预约项目表.xlsx')
df = pd.read_excel('/Users/gaoyanliang/nsyy/综合预约医生值班表.xlsx')

# 连接到 MySQL 数据库
db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

# # 构建 INSERT 语句
# sql = "INSERT INTO nsyy_gyl.appt_project (proj_type, proj_category, proj_name, proj_room, proj_capacity, proj_period, is_group) VALUES (%s, %s, %s, %s, %s, %s, %s)"
# # 执行 INSERT 语句
# for index, row in df.iterrows():
#     db.execute(sql, tuple(row), need_commit=True)


# 构建 INSERT 语句
sql = "INSERT INTO nsyy_gyl.appt_doctor_sched (doctor_name, consultation_room, proj_id, day_of_week, period) VALUES (%s, %s, %s, %s, %s)"
# 执行 INSERT 语句
for index, row in df.iterrows():
    db.execute(sql, tuple(row), need_commit=True)

del db










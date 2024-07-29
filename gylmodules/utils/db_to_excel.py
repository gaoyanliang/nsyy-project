
import pandas as pd
import pymysql
from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

# ========= 将数据库记录写入Excel ==========


# 查询数据库中的记录
query = "SELECT * FROM nsyy_gyl.alert_fail_log"
df = pd.read_sql(query, pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='gyl.2015',
    database='nsyy_gyl'))

# 将数据写入 Excel 文件
output_file = 'output.xlsx'
df.to_excel(output_file, index=False, engine='openpyxl')

print(f"Data has been written to {output_file}")



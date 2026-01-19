from gylmodules.utils.db_utils import DbUtil
from gylmodules import global_config
import pandas as pd



# import pandas as pd
# import math
#
# 将大表拆分成小表 。每一个表格5000条数据
# input_file = "/Users/gaoyanliang/Downloads/dat_202601141441.xlsx"      # 原始表格
# rows_per_file = 5000           # 每个文件 5000 行
# output_prefix = "output_part"  # 输出文件名前缀
#
# df = pd.read_excel(input_file)
#
# total_rows = len(df)
# file_count = math.ceil(total_rows / rows_per_file)
#
# for i in range(file_count):
#     start = i * rows_per_file
#     end = start + rows_per_file
#     sub_df = df.iloc[start:end]
#
#     output_file = f"{output_prefix}_{i+1}.xlsx"
#     sub_df.to_excel(output_file, index=False)
#
#     print(f"生成文件：{output_file}，行数 {len(sub_df)}")


if __name__ == "__main__":
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)

    # 将 excel 中的数据写入数据库
    df = pd.read_excel("/Users/gaoyanliang/nsyy/常见食物能量表.xlsx")
    # 获取文档的长度
    length = len(df)
    for i in range(0, length):
        # 数据转字符类型
        record = df.loc[i].values
        if record[3] == 'x':
            record[3] = True
        else:
            record[3] = False
        if record[4] == 'x':
            record[4] = True
        else:
            record[4] = False
        record = tuple(record)

        # 插入表数据
        sqlSentence = "INSERT INTO menu (name,kcal,unit,is_breakfast,is_dunch) VALUES (%s,%s,%s,%s,%s)"
        last_rowid = db.execute(sqlSentence, record, need_commit=True)

    del db


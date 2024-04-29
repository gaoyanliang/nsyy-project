from gylmodules.utils.db_utils import DbUtil
from gylmodules import global_config
import pandas as pd


if __name__ == "__main__":
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
    db.get_version()

    dbs = db.list_databases()
    print(f"database list: {dbs}")

    dbs = db.list_tables()
    print(f"table list: {dbs}")

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


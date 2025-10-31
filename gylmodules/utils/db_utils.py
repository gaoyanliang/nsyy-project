import logging
import time

import pymysql
from pymysql.cursors import DictCursor

from gylmodules import global_config

logger = logging.getLogger(__name__)

"""
数据库工具类
"""


class DbUtil:
    """构造函数"""

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.__conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
        # Create a cursor with DictCursor
        self.__cursor = self.__conn.cursor(cursor=DictCursor)
        # log.debug(f'connect db: {host}=, {port}=, {user}=, {password}=, {database}=')

    def __del__(self):
        """析构函数"""
        if self.__cursor is not None:
            self.__cursor.close()
        if self.__conn is not None:
            self.__conn.close()
        # log.debug("close db!")

    def get_conn(self):
        """获取连接"""
        return self.__conn

    def get_cursor(self, cursor=None):
        """获取游标"""
        return self.__conn.cursor(cursor)

    def __commit(self):
        """提交改动"""
        self.__conn.commit()

    def execute(self, sql, args=None, need_commit: bool = False, print_log: bool = True):
        """获取SQL执行结果"""
        try:
            start_time = time.time()
            self.__cursor.execute(sql, args)
            last_rowid = self.__cursor.lastrowid
            if need_commit:
                self.__commit()

            # logger.debug(f"execute耗时 {time.time() - start_time} 秒, 执行SQL {sql}")
            return last_rowid
        except Exception as e:
            if print_log:
                logger.warning(f"执行SQL {sql}, 遇到异常 {e}")
            else:
                logger.error(f"执行SQL {sql}, 遇到异常 {e}")
            self.__conn.rollback()
        return -1

    def execute_many(self, sql, args=None, need_commit: bool = False, print_log: bool = True):
        """获取SQL执行结果"""
        try:
            start_time = time.time()
            self.__cursor.executemany(sql, args)
            if need_commit:
                self.__commit()

            # logger.debug(f"execute_many 耗时 {time.time() - start_time} 秒, 执行SQL {sql}")
            # 获取最后一个插入记录的ID
            return self.__cursor.lastrowid
        except Exception as e:
            if print_log:
                logger.warning(f"执行SQL {sql}, 遇到异常 {e}")
            else:
                logger.error(f"执行SQL {sql}, 遇到异常 {e}")
            self.__conn.rollback()
        return -1

    def query_one(self, sql, print_log: bool = True):
        """查询单条数据"""
        result = None
        start_time = time.time()
        try:
            self.__cursor.execute(sql)
            result = self.__cursor.fetchone()
        except Exception as e:
            if print_log:
                logger.warning(f"执行SQL {sql}, 遇到异常 {e}")
            else:
                logger.debug(f"执行SQL {sql}, 遇到异常 {e}")
        # logger.debug(f"query_one 耗时 {time.time() - start_time} 秒, 执行SQL {sql}")
        return result

    def query_all(self, sql, print_log: bool = True):
        """查询多条数据"""
        list_result = ()
        start_time = time.time()
        try:
            self.__cursor.execute(sql)
            list_result = self.__cursor.fetchall()
        except Exception as e:
            if print_log:
                logger.warning(f"执行SQL {sql}, 遇到异常 {e}")
            else:
                logger.error(f"执行SQL {sql}, 遇到异常 {e}")
        # logger.debug(f"query_one 耗时 {time.time() - start_time} 秒, 执行SQL {sql}")
        return list_result


if __name__ == "__main__":
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
    data = db.query_all("select count(*) from nsyy_gyl.cv_info")
    print(data)

    del db




import logging
import time
from contextlib import contextmanager
from typing import Optional, Union, List, Dict, Any, Tuple

import pymysql
from pymysql.cursors import DictCursor

from gylmodules import global_config

logger = logging.getLogger(__name__)

"""
数据库工具类 - 优化版
优化点：
- 支持上下文管理器（with语句），确保资源自动释放（连接和游标）。
- 在__del__中添加属性存在性检查，避免AttributeError。
- 修复日志消息错误（query_all日志从"query_one"改为"query_all"）。
- query_one和query_all支持参数化查询（args参数）。
- execute_many返回受影响的行数（rowcount），而非lastrowid（executemany不返回lastrowid）。
- get_cursor方法修复：使用传入的cursor类型（如果提供）。
- 统一异常处理和日志级别（使用error而非warning在print_log=False时）。
- 线程安全建议：每个线程/请求使用独立的DbUtil实例。
- 返回类型优化：query_all返回List[Dict]，以匹配DictCursor。
- 移除未使用的__commit方法，改为直接在方法中调用commit。
"""


class DbUtil:
    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.__conn: Optional[pymysql.connections.Connection] = None
        self.__cursor: Optional[pymysql.cursors.Cursor] = None
        self._connect()

    def _connect(self) -> None:
        """内部连接方法，便于重连"""
        try:
            self.__conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',  # 推荐添加字符集
                autocommit=False  # 显式控制事务
            )
            self.__cursor = self.__conn.cursor(cursor=DictCursor)
            logger.debug(f"成功连接数据库: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def __enter__(self) -> 'DbUtil':
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """上下文管理器出口：自动关闭资源"""
        self.close()
        return exc_type is None  # 如果有异常，不抑制它

    def __del__(self) -> None:
        """析构函数：备用清理（但优先使用with语句）"""
        if hasattr(self, '_DbUtil__cursor') and self.__cursor is not None:
            try:
                self.__cursor.close()
            except Exception as e:
                logger.warning(f"关闭游标时异常: {e}")
        if hasattr(self, '_DbUtil__conn') and self.__conn is not None:
            try:
                self.__conn.close()
            except Exception as e:
                logger.warning(f"关闭连接时异常: {e}")
        logger.debug("数据库资源已清理")

    def close(self) -> None:
        """显式关闭资源"""
        if self.__cursor is not None:
            try:
                self.__cursor.close()
                self.__cursor = None
            except Exception as e:
                logger.warning(f"关闭游标时异常: {e}")
        if self.__conn is not None:
            try:
                self.__conn.close()
                self.__conn = None
            except Exception as e:
                logger.warning(f"关闭连接时异常: {e}")
        logger.debug("数据库资源已显式关闭")

    def get_conn(self) -> Optional[pymysql.connections.Connection]:
        """获取连接（如果已关闭则None）"""
        return self.__conn

    def get_cursor(self, cursor_type: Optional[Union[type, str]] = None) -> Optional[pymysql.cursors.Cursor]:
        """获取游标，支持自定义cursor类型（默认DictCursor）"""
        if self.__conn is None:
            logger.warning("连接已关闭，无法获取游标")
            return None
        cursor_class = cursor_type if cursor_type else DictCursor
        return self.__conn.cursor(cursor=cursor_class)

    def execute(self, sql: str, args: Optional[Union[tuple, dict]] = None,
                need_commit: bool = False, print_log: bool = True) -> int:
        """执行SQL（INSERT/UPDATE/DELETE），返回受影响行数或lastrowid"""
        if self.__cursor is None:
            raise RuntimeError("游标已关闭，请重新连接")
        try:
            start_time = time.time()
            self.__cursor.execute(sql, args or ())
            rowcount = self.__cursor.rowcount
            last_rowid = self.__cursor.lastrowid if hasattr(self.__cursor, 'lastrowid') else -1
            if need_commit:
                self.__conn.commit()
            logger.info(f"execute 耗时 {time.time() - start_time:.4f} 秒, SQL: {sql}" +
                        (f" 参数: {args}" if args else ""))
            return last_rowid if last_rowid != 0 else rowcount
        except Exception as e:
            self.__conn.rollback()
            log_level = logger.error if not print_log else logger.warning
            log_level(f"执行SQL失败: {sql} {args or ''}, 异常: {e}")
            return -1

    def execute_many(self, sql: str, args: List[Union[tuple, dict]],
                     need_commit: bool = False, print_log: bool = True) -> int:
        """批量执行SQL，返回受影响行数"""
        if self.__cursor is None:
            raise RuntimeError("游标已关闭，请重新连接")
        try:
            start_time = time.time()
            self.__cursor.executemany(sql, args)
            rowcount = self.__cursor.rowcount
            if need_commit:
                self.__conn.commit()
            logger.info(f"execute_many 耗时 {time.time() - start_time:.4f} 秒, SQL: {sql}, 影响行数: {rowcount}")
            return rowcount
        except Exception as e:
            self.__conn.rollback()
            log_level = logger.error if not print_log else logger.warning
            log_level(f"执行SQL失败: {sql} {args}, 异常: {e}")
            return -1

    def query_one(self, sql: str, args: Optional[Union[tuple, dict]] = None,
                  print_log: bool = True) -> Optional[Dict[str, Any]]:
        """查询单条数据，返回Dict或None"""
        if self.__cursor is None:
            raise RuntimeError("游标已关闭，请重新连接")
        start_time = time.time()
        result: Optional[Dict[str, Any]] = None
        try:
            self.__cursor.execute(sql, args or ())
            result = self.__cursor.fetchone()
        except Exception as e:
            log_level = logger.error if not print_log else logger.warning
            log_level(f"查询SQL失败: {sql} {args or ''}, 异常: {e}")
        logger.info(f"query_one 耗时 {time.time() - start_time:.4f} 秒, SQL: {sql}" +
                    (f" 参数: {args}" if args else ""))
        return result

    def query_all(self, sql: str, args: Optional[Union[tuple, dict]] = None,
                  print_log: bool = True) -> List[Dict[str, Any]]:
        """查询多条数据，返回List[Dict]"""
        if self.__cursor is None:
            raise RuntimeError("游标已关闭，请重新连接")
        start_time = time.time()
        results: List[Dict[str, Any]] = []
        try:
            self.__cursor.execute(sql, args or ())
            results = self.__cursor.fetchall()
        except Exception as e:
            log_level = logger.error if not print_log else logger.warning
            log_level(f"查询SQL失败: {sql} {args or ''}, 异常: {e}")
        logger.info(f"query_all 耗时 {time.time() - start_time:.4f} 秒, SQL: {sql}, 返回行数: {len(results)}" +
                    (f" 参数: {args}" if args else ""))
        return results


# 使用方式示例
if __name__ == "__main__":
    # 推荐使用with语句，确保资源自动释放
    with DbUtil(
        host=global_config.DB_HOST,
        user=global_config.DB_USERNAME,
        password=global_config.DB_PASSWORD,
        database=global_config.DB_DATABASE_GYL
    ) as db:
        # 参数化查询示例（防SQL注入）
        data = db.query_all("SELECT * FROM nsyy_gyl.cv_info WHERE id > %s", args=(0,))
        print(f"查询结果: {data[:2]}...")  # 只打印前两条

        # 执行插入示例
        # insert_id = db.execute(
        #     "INSERT INTO example_table (name) VALUES (%s)",
        #     args=("test",),
        #     need_commit=True
        # )
        # print(f"插入ID: {insert_id}")

    # 显式关闭（with已自动处理）
    # db.close()  # 如果不使用with

    # 批量执行示例
    # with DbUtil(...) as db:
    #     affected = db.execute_many(
    #         "INSERT INTO example_table (name) VALUES (%s)",
    #         args=[("batch1",), ("batch2",)]
    #     )
    #     print(f"批量影响行数: {affected}")
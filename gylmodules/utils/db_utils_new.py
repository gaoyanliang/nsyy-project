import logging
import time
from contextlib import contextmanager

import pymysql
from pymysql.constants import CLIENT
from pymysql.cursors import DictCursor

from gylmodules import global_config

logger = logging.getLogger(__name__)


class DbUtil:
    """数据库工具类（每个实例独立连接，支持上下文管理器，保证资源安全释放）"""

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306,
                 connect_timeout: int = 5, read_timeout: int = 30, write_timeout: int = 30,
                 max_retries: int = 2, retry_delay: float = 0.5, max_idle_time: int = 300,     # 最大空闲时间（秒）
             max_lifetime: int = 1800):
        """
        :param connect_timeout: 连接超时（秒）
        :param read_timeout: 读超时（秒）
        :param write_timeout: 写超时（秒）
        :param max_retries: 执行失败最大重试次数
        :param retry_delay: 重试间隔（秒）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_idle_time = max_idle_time
        self.max_lifetime = max_lifetime

        self._conn = None
        self._cursor = None
        # self._connect()  # 构造时立即连接

    def _connect(self):
        """建立数据库连接（内部使用）"""
        try:
            self._conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout,
                write_timeout=self.write_timeout,
                cursorclass=DictCursor,
                autocommit=False,
                client_flag=CLIENT.MULTI_STATEMENTS
            )
            self._cursor = self._conn.cursor()
            logger.debug(f"数据库连接成功: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"数据库连接失败: {self.host}:{self.port}/{self.database}, 错误: {e}")
            raise

    def _ensure_connection(self):
        """确保连接有效，无效则重连"""
        try:
            """真正需要时才连接"""
            if self._conn is None or not self._conn.open:
                self._connect()
                return
            # ping 检查连接是否存活，reconnect=True 会在断开时自动重连
            # self._conn.ping(reconnect=True)
        except Exception as e:
            logger.warning(f"数据库连接已断开，尝试重连: {e}")
            self._close_resources()
            self._connect()

    def _close_resources(self):
        """关闭游标和连接（不抛出异常）"""
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def close(self):
        """手动关闭连接（推荐使用上下文管理器，无需手动调用）"""
        self._close_resources()

    def __enter__(self):
        """上下文管理器入口"""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时自动关闭连接"""
        self.close()

    def __del__(self):
        """析构函数，确保资源释放（作为后备，不保证立即执行）"""
        self.close()

    def _execute_with_retry(self, sql, args, need_commit, is_many, print_log):
        """
        执行SQL（带重试机制）
        :return: lastrowid 或 -1
        """
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_connection()
                start_time = time.time()
                if is_many:
                    self._cursor.executemany(sql, args)
                else:
                    self._cursor.execute(sql, args)
                last_rowid = self._cursor.lastrowid
                if need_commit:
                    self._conn.commit()
                # 慢查询记录（超过2秒）
                elapsed = time.time() - start_time
                if elapsed > 2.0:
                    logger.warning(f"慢查询 ({elapsed:.2f}s): {sql[:200]}")
                return last_rowid
            except Exception as e:
                last_error = e
                if print_log:
                    logger.warning(f"SQL执行失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                else:
                    logger.debug(f"SQL执行失败: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    self._close_resources()  # 关闭旧连接，下次重连
                else:
                    # 最后一次失败，回滚
                    if need_commit and self._conn:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                    logger.error(f"SQL执行最终失败: {sql[:200]}, 错误: {e}")
        return -1

    def execute(self, sql, args=None, need_commit=False, print_log=True):
        """
        执行单条SQL（INSERT/UPDATE/DELETE）
        :return: lastrowid 或 -1
        """
        return self._execute_with_retry(sql, args, need_commit, is_many=False, print_log=print_log)

    def execute_many(self, sql, args=None, need_commit=False, print_log=True):
        """
        批量执行SQL
        :return: lastrowid 或 -1
        """
        return self._execute_with_retry(sql, args, need_commit, is_many=True, print_log=print_log)

    def query_one(self, sql, print_log=True):
        """
        查询单条数据，返回字典或 None
        """
        try:
            self._ensure_connection()
            start_time = time.time()
            self._cursor.execute(sql)
            result = self._cursor.fetchone()
            elapsed = time.time() - start_time
            if elapsed > 2.0:
                logger.warning(f"慢查询 ({elapsed:.2f}s): {sql[:200]}")
            return result
        except Exception as e:
            if print_log:
                logger.warning(f"查询单条失败: {e}, SQL: {sql[:200]}")
            else:
                logger.debug(f"查询单条失败: {e}")
            return None

    def query_all(self, sql, print_log=True):
        """
        查询多条数据，返回列表
        """
        try:
            self._ensure_connection()
            start_time = time.time()
            self._cursor.execute(sql)
            result = self._cursor.fetchall()
            elapsed = time.time() - start_time
            if elapsed > 2.0:
                logger.warning(f"慢查询 ({elapsed:.2f}s): {sql[:200]}")
            return result
        except Exception as e:
            if print_log:
                logger.warning(f"查询多条失败: {e}, SQL: {sql[:200]}")
            else:
                logger.debug(f"查询多条失败: {e}")
            return ()

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器，自动提交或回滚
        用法：
            with db.transaction():
                db.execute(...)
                db.execute(...)
        """
        self._ensure_connection()
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise


# 可选：线程本地连接池（每个线程一个独立连接，减少重复创建开销）
import threading


class ThreadLocalDbPool:
    """
    线程本地数据库连接池
    每个线程拥有自己独立的 DbUtil 实例，线程之间不共享，无需加锁。
    用法：
        pool = ThreadLocalDbPool(global_config.DB_HOST, ...)
        db = pool.get_connection()  # 每个线程第一次调用时创建新实例，之后复用
        # 使用完毕后不需要 close，线程结束时会自动清理（需手动调用 close_all 或依赖线程局部变量回收）
    """

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306, **kwargs):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port,
            **kwargs
        }
        self._local = threading.local()

    def get_connection(self) -> DbUtil:
        """获取当前线程的 DbUtil 实例（自动创建并缓存）"""
        if not hasattr(self._local, 'db'):
            self._local.db = DbUtil(**self.config)
        return self._local.db

    def close_all(self):
        """关闭当前线程的连接（线程结束时调用，或者定期调用）"""
        if hasattr(self._local, 'db'):
            self._local.db.close()
            delattr(self._local, 'db')


if __name__ == "__main__":
    # 使用示例1：上下文管理器（推荐，自动释放）
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        data = db.query_all("SELECT count(*) AS cnt FROM nsyy_gyl.cv_info")
        print(data)
    #
    # # 使用示例2：手动创建并显式关闭（兼容旧代码）
    # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
    #             global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
    # try:
    #     data = db.query_all("SELECT * FROM nsyy_gyl.cv_info LIMIT 10")
    #     print(data)
    # finally:
    #     db.close()  # 显式关闭
    #
    # # 使用示例3：线程本地连接池（适合多线程环境，每个线程复用连接）
    # pool = ThreadLocalDbPool(global_config.DB_HOST, global_config.DB_USERNAME,
    #                          global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
    #
    # def worker():
    #     db = pool.get_connection()
    #     data = db.query_all("SELECT 1")
    #     # 不需要 close，线程退出时会自动清理（但建议在任务结束时显式调用 pool.close_all()）
    #
    # import threading
    # t = threading.Thread(target=worker)
    # t.start()
    # t.join()
    # pool.close_all()  # 清理当前线程的连接
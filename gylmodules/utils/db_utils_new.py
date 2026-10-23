# gylmodules/utils/db_utils_new.py
import logging
import random
import threading
import time
from contextlib import contextmanager

import pymysql
from pymysql.constants import CLIENT
from pymysql.cursors import DictCursor
from pymysql.err import InterfaceError, OperationalError

from gylmodules import global_config

logger = logging.getLogger(__name__)

# 只对这些错误码重试：连接类 + 死锁 + 锁等待
_RETRYABLE_ERRNOS = frozenset({
    2003,  # Can't connect to MySQL server
    2006,  # MySQL server has gone away
    2013,  # Lost connection to MySQL server during query
    2055,  # Lost connection to MySQL server
    1040,  # Too many connections
    1205,  # Lock wait timeout exceeded
    1213,  # Deadlock found
})


class DbError(Exception):
    """数据库异常基类"""
    pass


class DbConnectionError(DbError):
    """连接类错误（可重试）"""
    pass


class DbUtil:
    """
    生产级 MySQL 工具类。

    设计约定：
    - 每个实例对应一个独立连接，实例内部**不是线程安全**的；
      多线程场景请每个线程一个实例（用 ThreadLocalDbPool）或
      用连接池版本。
    - 上下文管理器 `with DbUtil(...) as db:` 自动关闭。
    - `execute` / `query_*` 均支持 `args` 参数化，务必使用参数化防注入。
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306,
        connect_timeout: int = 5,
        read_timeout: int = 30,
        write_timeout: int = 30,
        max_retries: int = 2,
        retry_delay: float = 0.5,
        connect_retries: int = 3,
        max_idle_time: int = 300,     # 空闲超过则主动重连（秒），0 表示不检查
        max_lifetime: int = 1800,     # 连接寿命上限（秒），0 表示不检查
        slow_query_threshold: float = 2.0,
    ):
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
        self.connect_retries = connect_retries
        self.max_idle_time = max_idle_time
        self.max_lifetime = max_lifetime
        self.slow_query_threshold = slow_query_threshold

        self._conn = None
        self._cursor = None
        self._created_at = 0.0     # 连接创建时间（monotonic）
        self._last_used = 0.0      # 最后一次使用时间
        self._in_tx = False        # 事务标志

    # ============================================================
    #  连接管理
    # ============================================================

    def _connect(self):
        """建立连接，带独立重试与指数退避"""
        last_err = None
        for attempt in range(self.connect_retries):
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
                    client_flag=CLIENT.MULTI_STATEMENTS,
                )
                self._cursor = self._conn.cursor()
                now = time.monotonic()
                self._created_at = now
                self._last_used = now
                logger.debug(
                    "数据库连接成功: %s:%s/%s", self.host, self.port, self.database
                )
                return
            except Exception as e:
                last_err = e
                # 只有连接类错误才值得重试
                if not self._is_retryable(e):
                    break
                if attempt < self.connect_retries - 1:
                    sleep = self.retry_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    logger.warning(
                        "数据库连接失败 (尝试 %d/%d)，%.2fs 后重试: %s",
                        attempt + 1, self.connect_retries, sleep, e,
                    )
                    time.sleep(sleep)

        logger.error(
            "数据库连接最终失败: %s:%s/%s, 错误: %s",
            self.host, self.port, self.database, last_err,
        )
        raise DbConnectionError(str(last_err)) from last_err

    def _close_resources(self):
        """幂等关闭连接与游标，不抛异常"""
        if self._cursor is not None:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None

        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

        self._in_tx = False
        self._created_at = 0.0
        self._last_used = 0.0

    def _ensure_connection(self):
        """
        确保连接可用。检测顺序：
        1. 从未连接 / 已关闭 → 新建
        2. 空闲超时 → 主动丢弃重建
        3. 寿命超时 → 主动丢弃重建
        4. ping 服务端 → 失败则重建
        """
        now = time.monotonic()

        # 从未连接 或 已被关闭
        if self._conn is None or not getattr(self._conn, "open", False):
            self._close_resources()
            self._connect()
            return

        # 空闲超时
        if (
            self.max_idle_time > 0
            and self._last_used > 0
            and now - self._last_used > self.max_idle_time
        ):
            logger.debug(
                "连接空闲超过 %ss，主动重连", self.max_idle_time
            )
            self._close_resources()
            self._connect()
            return

        # 寿命超时
        if (
            self.max_lifetime > 0
            and self._created_at > 0
            and now - self._created_at > self.max_lifetime
        ):
            logger.debug(
                "连接超过最大生命周期 %ss，主动重连", self.max_lifetime
            )
            self._close_resources()
            self._connect()
            return

        # 服务端活性检测（不自动重连，我们自己管理重连逻辑）
        try:
            self._conn.ping(reconnect=False)
        except Exception:
            logger.debug("连接 ping 失败，主动重连")
            self._close_resources()
            self._connect()

    def _is_retryable(self, e: BaseException) -> bool:
        """只有连接类错误 / 死锁 才重试"""
        if isinstance(e, InterfaceError):
            return True
        if isinstance(e, OperationalError):
            return bool(e.args) and e.args[0] in _RETRYABLE_ERRNOS
        return False

    # ============================================================
    #  上下文管理器
    # ============================================================

    def __enter__(self):
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 事务上下文中发生异常 → 回滚
        if exc_type is not None and self._conn is not None and self._in_tx:
            try:
                self._conn.rollback()
            except Exception:
                pass
        self._close_resources()

    def close(self):
        self._close_resources()

    def __del__(self):
        # 解释器关闭时属性可能已清理，必须 try/except
        try:
            self._close_resources()
        except Exception:
            pass

    # ============================================================
    #  写操作
    # ============================================================

    def execute(self, sql, args=None, need_commit=False, print_log=True):
        """单条 SQL（INSERT/UPDATE/DELETE）。返回 lastrowid，失败返回 -1。"""
        return self._execute_with_retry(
            sql, args, need_commit, is_many=False, print_log=print_log
        )

    def execute_many(self, sql, args=None, need_commit=False, print_log=True):
        """批量执行。args 必须是 list[tuple]。"""
        return self._execute_with_retry(
            sql, args, need_commit, is_many=True, print_log=print_log
        )

    def _execute_with_retry(self, sql, args, need_commit, is_many, print_log):
        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_connection()
                start = time.monotonic()

                if is_many:
                    self._cursor.executemany(sql, args)
                elif args is None:
                    self._cursor.execute(sql)
                else:
                    self._cursor.execute(sql, args)

                last_rowid = self._cursor.lastrowid

                # 只有在非事务上下文中才自动提交
                if need_commit and not self._in_tx:
                    self._conn.commit()

                self._last_used = time.monotonic()
                elapsed = self._last_used - start
                if elapsed > self.slow_query_threshold:
                    logger.warning("慢查询 (%.2fs): %s", elapsed, sql[:200])
                return last_rowid

            except Exception as e:
                retryable = self._is_retryable(e)

                # 非连接类错误：立刻放弃，回滚
                if not retryable:
                    if need_commit and self._conn and not self._in_tx:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                    if print_log:
                        logger.error("SQL执行失败（不可重试）: %s, SQL: %s", e, sql[:200])
                    else:
                        logger.debug("SQL执行失败: %s", e)
                    return -1

                # 连接类错误：可重试
                if attempt < self.max_retries:
                    sleep = self.retry_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    if print_log:
                        logger.warning(
                            "SQL执行失败 (可重试 %d/%d)，%.2fs 后重试: %s",
                            attempt + 1, self.max_retries + 1, sleep, e,
                        )
                    self._close_resources()
                    time.sleep(sleep)
                    continue

                # 重试耗尽
                if need_commit and self._conn and not self._in_tx:
                    try:
                        self._conn.rollback()
                    except Exception:
                        pass
                logger.error(
                    "SQL执行最终失败 (重试 %d 次后放弃): %s, SQL: %s",
                    self.max_retries, e, sql[:200],
                )
                return -1

        return -1

    # ============================================================
    #  读操作
    # ============================================================

    def query_one(self, sql, args=None, print_log=True):
        """查询单条，返回 dict 或 None。"""
        return self._query_with_retry(sql, args, fetch_one=True, print_log=print_log)

    def query_all(self, sql, args=None, print_log=True):
        """查询多条，返回 tuple[dict]。"""
        return self._query_with_retry(sql, args, fetch_one=False, print_log=print_log)

    def _query_with_retry(self, sql, args, fetch_one, print_log):
        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_connection()
                start = time.monotonic()

                if args is None:
                    self._cursor.execute(sql)
                else:
                    self._cursor.execute(sql, args)

                result = self._cursor.fetchone() if fetch_one else self._cursor.fetchall()

                self._last_used = time.monotonic()
                elapsed = self._last_used - start
                if elapsed > self.slow_query_threshold:
                    logger.warning("慢查询 (%.2fs): %s", elapsed, sql[:200])
                return result

            except Exception as e:
                retryable = self._is_retryable(e)

                if not retryable:
                    if print_log:
                        logger.warning("查询失败（不可重试）: %s, SQL: %s", e, sql[:200])
                    else:
                        logger.debug("查询失败: %s", e)
                    return None if fetch_one else ()

                if attempt < self.max_retries:
                    sleep = self.retry_delay * (2 ** attempt)
                    if print_log:
                        logger.warning(
                            "查询失败 (可重试 %d/%d)，%.2fs 后重试: %s",
                            attempt + 1, self.max_retries + 1, sleep, e,
                        )
                    self._close_resources()
                    time.sleep(sleep)
                    continue

                logger.error("查询最终失败: %s, SQL: %s", e, sql[:200])
                return None if fetch_one else ()

        return None if fetch_one else ()

    # ============================================================
    #  事务
    # ============================================================

    @contextmanager
    def transaction(self):
        """
        事务上下文。内部的 execute/query 不会自动 commit，
        由 with 块结束时统一 commit / 异常时 rollback。

        用法：
            with db.transaction():
                db.execute(sql1, args1, need_commit=True)
                db.execute(sql2, args2, need_commit=True)
        """
        self._ensure_connection()
        self._in_tx = True
        try:
            yield self
            self._conn.commit()
        except Exception:
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._in_tx = False


# ============================================================
#  线程本地连接池（单线程内复用）
# ============================================================

class ThreadLocalDbPool:
    """
    每个线程一个 DbUtil，避免跨线程共享连接。
    适合：Flask 多线程 + 每个请求自己 close 的旧代码改造。
    """

    def __init__(self, host, user, password, database, port=3306, **kwargs):
        self._config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            **kwargs,
        }
        self._local = threading.local()

    def get_connection(self) -> DbUtil:
        db = getattr(self._local, "db", None)
        if db is None:
            db = DbUtil(**self._config)
            self._local.db = db
        return db

    def close(self):
        db = getattr(self._local, "db", None)
        if db is not None:
            db.close()
            self._local.db = None

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
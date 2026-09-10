import asyncio
import logging
import time
import psycopg2

from psycopg2.extras import RealDictCursor
from mysql.connector import pooling
import redis
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading

from gylmodules import global_config
from gylmodules.global_config import db_config
from outpatient_queue.websocket_manager import manager
from outpatient_queue.config import REDIS_CONFIG, BUSINESS_TYPES

logger = logging.getLogger(__name__)
WINDOW_KEY = "windows:list"

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        logger.info("=== DatabaseManager init ===")
        if self._initialized:
            return
        self._initialized = True
        self.pool = None
        self.redis_client = None
        self._scheduler_running = False  # 调度线程标志
        self._medicine_monitor_running = False  # 定时查询取药状态
        self.init_data()

    """初始化数据库连接池和 Redis"""
    def init_data(self):
        logger.info("======================== init_data ========================")
        # Redis 初始化（可选）
        if global_config.run_in_local:
            try:
                self.redis_client = redis.Redis(**REDIS_CONFIG)
                self.redis_client.ping()
                logger.info("Redis 连接成功")
            except Exception as e:
                logger.warning(f"Redis 连接失败，将禁用 Redis 功能: {e}")
                self.redis_client = None
        else:
            try:
                # 复制配置，避免污染原字典
                redis_config = REDIS_CONFIG.copy()
                # 强制使用 RESP2 协议
                pool = redis.ConnectionPool(**redis_config, protocol=2)
                self.redis_client = redis.Redis(connection_pool=pool)
                self.redis_client.ping()
                logger.info("Redis 连接成功（RESP2 协议）")
            except Exception as e:
                logger.warning(f"Redis 连接失败，将禁用 Redis 功能: {e}")
                self.redis_client = None

        try:
            # 创建 MySQL 连接池
            self.pool = pooling.MySQLConnectionPool(
                pool_name="hospital_queue_pool",
                pool_size=10,          # 根据实际并发调整（推荐 5-20）
                pool_reset_session=True,
                **db_config
            )
            logger.info("MySQL 连接池创建成功")
            self.create_tables()

            # 初始化 Redis 计数器
            self._init_redis_counters()

            # 在 Redis 连接成功后，启动每日重置调度
            if self.redis_client:
                self._start_daily_reset_scheduler()
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
        self._init_unmedicine_queue_cache()
        self._start_medicine_monitor()  # 启动药品监控
        self.cache_data()


    """获取连接池中的连接"""
    def get_connection(self):
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        return self.pool.get_connection()

    def create_tables(self):
        """创建数据库表"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # 患者表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hqs_patients (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100),
                    id_card VARCHAR(18),
                    phone VARCHAR(11),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_id_card (id_card)
                )
            """)

            # 排队记录表（增加复合索引）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hqs_queue_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    queue_number VARCHAR(20),
                    queue_date VARCHAR(20),
                    patient_id VARCHAR(50),
                    patient_name VARCHAR(100),
                    business_id VARCHAR(20),
                    business_type VARCHAR(20),
                    business_name VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'waiting',
                    window_id INT,
                    window_name VARCHAR(50),
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    call_time TIMESTAMP NULL,
                    complete_time TIMESTAMP NULL,
                    skip_time TIMESTAMP NULL,
                    skip_reason VARCHAR(200),
                    medication_state INT,
                    medication_time TIMESTAMP NULL,
                    INDEX idx_status (status),
                    INDEX idx_business_id (business_id),
                    INDEX idx_business_type (business_type),
                    INDEX idx_queue_number (queue_number),
                    INDEX idx_create_time (create_time),
                    INDEX idx_business_status_time (business_id, business_type, status, create_time),
                    UNIQUE INDEX idx_unique_queue (queue_number, queue_date)
                )
            """)

            # 药品缴费记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hqs_medicine_payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    patient_id VARCHAR(50),
                    medicine_name VARCHAR(200),
                    price DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'unpaid',
                    prescription_id VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_time TIMESTAMP NULL,
                    INDEX idx_patient_id (patient_id),
                    INDEX idx_status (status)
                )
            """)

            # 窗口表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hqs_windows (
                    id INT PRIMARY KEY,
                    window_name VARCHAR(50),
                    window_type VARCHAR(50),
                    prefix VARCHAR(10),
                    business_sort VARCHAR(50),
                    is_active BOOLEAN DEFAULT TRUE,
                    current_queue_number VARCHAR(20),
                    last_call_time TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("数据库表创建/检查完成")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    """从 MySQL 初始化 Redis 计数器（当天数据）"""
    def _init_redis_counters(self):
        """从 MySQL 初始化 Redis 计数器（当天数据），优化版：使用分组查询减少数据库往返"""
        if not self.redis_client:
            return

        date_str = datetime.now().strftime("%Y%m%d")
        conn = self.get_connection()

        try:
            cursor = conn.cursor(dictionary=True)
            # 全量同步 – 使用分组查询一次性获取所有业务类型的统计数据
            # 1) 等待人数分组统计
            cursor.execute("""
                SELECT business_id, COUNT(*) as cnt
                 from hqs_queue_records
                WHERE queue_date = %s AND status = 'waiting'
                GROUP BY business_id
            """, (date_str,))
            waiting_map = {row['business_id']: row['cnt'] for row in cursor.fetchall()}

            # 2) 今日总数分组统计
            cursor.execute("""
                SELECT business_id, COUNT(*) as cnt
                from hqs_queue_records
                WHERE queue_date = %s
                GROUP BY business_id
            """, (date_str,))
            total_map = {row['business_id']: row['cnt'] for row in cursor.fetchall()}

            # 3) 完成服务统计（包含计数和总等待秒数）
            cursor.execute("""
                SELECT business_id,
                       COUNT(*) as cnt,
                       SUM(TIMESTAMPDIFF(SECOND, create_time, complete_time)) as total_sec
                from hqs_queue_records
                WHERE queue_date = %s AND status = 'completed'
                GROUP BY business_id
            """, (date_str,))
            completed_rows = cursor.fetchall()
            completed_map = {}
            total_sec_map = {}
            for row in completed_rows:
                bt = row['business_id']
                # 确保 count 为 int（虽然大概率已是 int，但安全起见）
                completed_map[bt] = int(row['cnt']) if row['cnt'] is not None else 0
                # 显式将 total_sec 转为 int，处理 None 情况
                total_sec_map[bt] = int(row['total_sec']) if row['total_sec'] is not None else 0

            # 获取所有可能出现的业务类型（从 BUSINESS_TYPES 中提取唯一的 type）
            all_business_ids = set()
            for bt_id in BUSINESS_TYPES.keys():
                all_business_ids.add(bt_id)

            # 遍历所有业务类型，写入 Redis（没有统计数据的类型默认为 0）
            pipe = self.redis_client.pipeline()
            for bt in all_business_ids:
                waiting = waiting_map.get(bt, 0)
                total = total_map.get(bt, 0)
                completed = completed_map.get(bt, 0)
                total_sec = total_sec_map.get(bt, 0)

                pipe.set(f"waiting_count:{bt}:{date_str}", waiting)
                pipe.set(f"today_total:{bt}:{date_str}", total)
                pipe.set(f"completed_count:{bt}:{date_str}", completed)
                pipe.set(f"total_wait_time:{bt}:{date_str}", total_sec)

            total_waiting = sum(waiting_map.values())
            total_today = sum(total_map.values())
            pipe.set(f"waiting_count:all:{date_str}", total_waiting)
            pipe.set(f"today_total:all:{date_str}", total_today)

            pipe.execute()
            logger.info(f"Redis 计数器初始化完成（全量，共 {len(all_business_ids)} 个业务类型）")

        except Exception as e:
            logger.error(f"初始化 Redis 计数器失败: {e}")
        finally:
            cursor.close()
            conn.close()

    """缓存窗口数据"""
    def cache_data(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""SELECT id, window_name, window_type, prefix, business_sort FROM hqs_windows 
                                where is_active = 1 order by window_type, window_name""")
            windows = cursor.fetchall()
            if windows:
                self.redis_client.set(WINDOW_KEY, json.dumps(windows))
            else:
                windows = []
            return windows
        finally:
            cursor.close()
            conn.close()

    """启动后台线程，每天凌晨执行计数器重置"""
    def _start_daily_reset_scheduler(self):
        if self._scheduler_running:
            logger.info("每日重置调度器已在运行")
            return

        def scheduler_loop():
            self._scheduler_running = True
            while True:
                now = datetime.now()
                # 计算下一个凌晨 00:00:00
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
                sleep_seconds = (next_midnight - now).total_seconds()
                logger.info(f"下次 Redis 计数器重置时间: {next_midnight.strftime('%Y-%m-%d %H:%M:%S')} (等待 {sleep_seconds:.0f} 秒)")
                time.sleep(sleep_seconds)

                # 执行重置
                try:
                    logger.info("开始执行每日 Redis 计数器重置...")
                    self.reset_daily_counters()
                    logger.info("每日 Redis 计数器重置完成")
                except Exception as e:
                    logger.error(f"每日重置失败: {e}")

        thread = threading.Thread(target=scheduler_loop, daemon=True, name="DailyRedisReset")
        thread.start()
        logger.info("每日重置调度线程已启动")

    """手动或自动重置 Redis 计数器（从 MySQL 重新同步当天数据）"""
    def reset_daily_counters(self):
        if not self.redis_client:
            logger.warning("Redis 未连接，无法重置计数器")
            return
        self._init_redis_counters()

    # ==== 使用 Redis 存储当天排队记录 ====

    """服务启动时加载当天待配药记录到 Redis"""
    def _init_unmedicine_queue_cache(self):
        if not self.redis_client:
            return
        # 检查是否已存在缓存，若存在则跳过（或强制重新加载）
        if self.redis_client.exists("unmedicine_queue"):
            logger.info("待配药缓存已存在，跳过初始化")
            return
        self._load_unmedicine_queue_records_to_cache()

    def _load_unmedicine_queue_records_to_cache(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            date_str = datetime.now().strftime("%Y%m%d")
            cursor.execute("""SELECT patient_id FROM hqs_queue_records WHERE queue_date = %s and business_id = 1 
            and medication_state = 0 """, (date_str,))
            records = cursor.fetchall()
            if not records:
                logger.info("当天无待配药记录")
                return
            pipe = self.redis_client.pipeline()
            for rec in records:
                pipe.lpush('unmedicine_queue', rec.get('patient_id'))
            pipe.execute()
            logger.info(f"待配药缓存初始化完成，共加载 {len(records)} 条记录")
        except Exception as e:
            logger.error(f"加载待配药缓存失败: {e}")
        finally:
            cursor.close()
            conn.close()


    # ====================== 患者相关 ======================
    """查询患者跳过记录"""
    def get_patient_skipped_record(self, patient_id: str, business_id: str) -> Dict:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""SELECT * FROM hqs_queue_records
                           WHERE patient_id = %s AND business_id = %s AND status = 'skipped' and queue_date = %s 
                           ORDER BY create_time DESC LIMIT 1
                           """, (patient_id, business_id, datetime.now().strftime("%Y%m%d")))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    """新增患者"""
    def add_patient(self, patient_id: str, name: str, id_card: str = None, phone: str = None) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(""" INSERT INTO hqs_patients (id, name, id_card, phone) VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), id_card = IFNULL(VALUES(id_card), id_card),
                phone = IFNULL(VALUES(phone), phone) """, (patient_id, name, id_card, phone))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加患者失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()


    # ====================== 队列相关 ======================
    # 生成排队号 - 格式：A001, B001, C001 等
    def generate_queue_number(self, business_id: str) -> str:
        """生成排队号（原子化查询）"""
        if business_id not in BUSINESS_TYPES:
            raise ValueError(f"未知业务类型: {business_id}")
        prefix = BUSINESS_TYPES[business_id]['prefix']

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT MAX(CAST(SUBSTRING(queue_number, 2) AS UNSIGNED))
                FROM hqs_queue_records WHERE queue_number LIKE %s AND queue_date = %s
            """, (f"{prefix}%", datetime.now().strftime("%Y%m%d")))
            result = cursor.fetchone()
            max_num = result[0] if result and result[0] else 0
            next_num = max_num + 1
            return f"{prefix}{next_num:03d}"
        finally:
            cursor.close()
            conn.close()

    def is_repeat_queue(self, patient_id: str, business_id: str) -> dict:
        """ 判断当天是否已取号 """
        if business_id not in BUSINESS_TYPES:
            raise ValueError(f"未知业务类型: {business_id}")
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True) # ✅ 解决 Unread result
            cursor.execute("""SELECT id, queue_number, business_name, create_time
            FROM hqs_queue_records WHERE patient_id = %s AND business_id = %s AND status = 'waiting' 
            AND queue_date = %s""", (patient_id, business_id, datetime.now().strftime("%Y%m%d")))
            row = cursor.fetchone()
            if not row:
                return None
            if row.get('create_time', ''):
                row['create_time'] = row['create_time'].strftime("%Y-%m-%d %H:%M:%S")
            return row
        except Exception as e:
            logger.error(f"判断当天是否已取号 遇到异常: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    """添加排队记录 + 事务"""
    def add_queue_record(self, queue_number: str, queue_date: str, patient_id: str,
                         patient_name: str, business_id: str, business_type: str, business_name: str) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            conn.start_transaction()

            cursor.execute("""INSERT INTO hqs_queue_records (queue_number, queue_date, patient_id, patient_name, 
            business_id, business_type, business_name, status) VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting')
            """, (queue_number, queue_date, patient_id, patient_name, business_id, business_type, business_name))
            conn.commit()

            # 更新 Redis 计数器
            if self.redis_client:
                try:
                    date_str = datetime.now().strftime("%Y%m%d")
                    self.redis_client.incr(f"waiting_count:{business_id}:{date_str}")
                    self.redis_client.incr(f"today_total:{business_id}:{date_str}")
                    # 可选：全局计数器
                    self.redis_client.incr(f"waiting_count:all:{date_str}")
                    self.redis_client.incr(f"today_total:all:{date_str}")

                    if business_id == 1:
                        # 如果是取药业务 添加到缓存
                        self.redis_client.lpush("unmedicine_queue", patient_id)
                except Exception as e:
                    logger.warning(f"更新 Redis 计数器失败: {e}")

            # Redis 仅通知，不维护队列列表
            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({
                        'action': 'add',
                        'data': {
                            'queue_number': queue_number, 'patient_name': patient_name,
                            'business_id': business_id, 'business_type': business_type, 'business_name': business_name
                        }
                    }))
                except Exception as redis_e:
                    logger.warning(f"Redis 发布失败: {redis_e}")

            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"添加排队记录失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """获取下一个等待号 """
    def get_next_queue(self, business_type: str, business_sort) -> Optional[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            conn.start_transaction()

            sort_list = [s.strip() for s in business_sort.split(",") if s.strip()]
            if not sort_list:
                raise ValueError(f"无效的排序参数 {business_sort}")
            # 构造 FIELD 排序参数
            placeholders = ",".join(["%s"] * len(sort_list))
            sql = f"""
                SELECT * FROM hqs_queue_records
                WHERE business_type = %s
                  AND status = 'waiting'
                  AND queue_date = %s
                  AND business_id IN ({placeholders})          -- 过滤：只取列表中的业务
                ORDER BY FIELD(business_id, {placeholders}),   -- 排序：按给定顺序
                         priority DESC, create_time ASC
                LIMIT 1
            """
            params = [business_type, datetime.now().strftime("%Y%m%d")] + sort_list + sort_list
            cursor.execute(sql, params)
            queue = cursor.fetchone()

            conn.commit()
            return queue
        except Exception as e:
            conn.rollback()
            logger.error(f"获取下一个队列失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    """获取下一个等待号 """
    def call_next_queue(self, business_type: str, business_sort: str, window_id: int, window_name: str) -> Optional[
        Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()

            sort_list = [s.strip() for s in business_sort.split(",") if s.strip()]
            if not sort_list:
                raise ValueError(f"无效的排序参数 {business_sort}")
            placeholders = ",".join(["%s"] * len(sort_list))
            sql = f""" SELECT * FROM hqs_queue_records WHERE business_type = %s AND status = 'waiting'  
                AND queue_date = %s AND business_id IN ({placeholders}) 
                ORDER BY FIELD(business_id, {placeholders}), priority DESC, create_time ASC 
                LIMIT 1 FOR UPDATE """
            params = [business_type, datetime.now().strftime("%Y%m%d")] + sort_list + sort_list
            cursor.execute(sql, params)
            queue = cursor.fetchone()
            if not queue:
                conn.commit()
                return None

            # 更新为 calling
            cursor.execute("""UPDATE hqs_queue_records
                SET status = 'calling', window_id = %s, window_name = %s, call_time = NOW()
                WHERE queue_number = %s AND status = 'waiting' AND queue_date = %s
            """, (window_id, window_name, queue['queue_number'], datetime.now().strftime("%Y%m%d")))

            # 更新窗口当前叫号
            cursor.execute("""UPDATE hqs_windows
                SET current_queue_number = %s, last_call_time = NOW() WHERE id = %s
            """, (queue['queue_number'], window_id))

            conn.commit()

            # Redis 通知
            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({ 'action': 'call',
                        'queue_number': queue['queue_number'], 'window_id': window_id, 'window_name': window_name}))
                except Exception as redis_e:
                    logger.warning(f"Redis 发布失败: {redis_e}")

            # 更新 Redis 计数器（安全递减）
            self._update_waiting_counts(queue['business_id'], -1)

            return queue
        except Exception as e:
            conn.rollback()
            logger.error(f"call_next_queue 失败: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    """叫号（事务保护两个表更新）"""
    def call_queue(self, queue_number: str, window_id: int, window_name: str) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            conn.start_transaction()

            # 先查出该记录的业务类型（用于更新 Redis）
            cursor.execute("SELECT business_id FROM hqs_queue_records WHERE queue_number = %s AND status = 'waiting' "
                           "and queue_date = %s", (queue_number, datetime.now().strftime("%Y%m%d")))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return False
            business_id = row[0]

            # 更新队列状态
            cursor.execute(""" UPDATE hqs_queue_records SET status = 'calling', window_id = %s, window_name = %s, 
            call_time = NOW() WHERE queue_number = %s AND status = 'waiting' and queue_date = %s """,
                           (window_id, window_name, queue_number, datetime.now().strftime("%Y%m%d")))
            if cursor.rowcount == 0:
                conn.rollback()
                return False

            # 更新窗口当前叫号
            cursor.execute("""UPDATE hqs_windows SET current_queue_number = %s, last_call_time = NOW() WHERE id = %s
            """, (queue_number, window_id))
            conn.commit()

            # Redis 通知
            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({ 'action': 'call',
                        'queue_number': queue_number, 'window_id': window_id, 'window_name': window_name}))
                except Exception as redis_e:
                    logger.warning(f"Redis 发布失败: {redis_e}")

                try:
                    # 使用安全递减，不再直接 decr
                    self._update_waiting_counts(business_id, -1)
                except Exception as e:
                    logger.warning(f"Redis 更新失败: {e}")

            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"叫号失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """完成服务"""
    def complete_queue(self, queue_number: str) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()
            # 获取记录的创建时间和业务类型
            cursor.execute("SELECT create_time, business_id FROM hqs_queue_records WHERE queue_number = %s "
                           "AND status = 'calling' AND queue_date = %s",
                           (queue_number, datetime.now().strftime("%Y%m%d")))
            record = cursor.fetchone()
            if not record:
                conn.rollback()
                return False
            create_time = record['create_time']
            business_id = record['business_id']

            cursor.execute("""UPDATE hqs_queue_records SET status = 'completed', complete_time = NOW()
                WHERE queue_number = %s AND queue_date = %s""", (queue_number, datetime.now().strftime("%Y%m%d")))
            conn.commit()

            # 计算等待时长（秒）
            complete_time = datetime.now()
            wait_seconds = int((complete_time - create_time).total_seconds())

            # 更新 Redis
            if self.redis_client:
                try:
                    date_str = datetime.now().strftime("%Y%m%d")
                    self.redis_client.incr(f"completed_count:{business_id}:{date_str}")
                    self.redis_client.incrby(f"total_wait_time:{business_id}:{date_str}", wait_seconds)
                    # 全局
                    self.redis_client.incr(f"completed_count:all:{date_str}")
                    self.redis_client.incrby(f"total_wait_time:all:{date_str}", wait_seconds)
                except Exception as e:
                    logger.warning(f"Redis 更新失败: {e}")

            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({
                        'action': 'complete', 'queue_number': queue_number}))
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"完成服务失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """药品收集完成"""
    def medicine_complete(self, queue_number: str, status: int) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""UPDATE hqs_queue_records SET medication_state = %s, medication_time = NOW()
                WHERE queue_number = %s AND queue_date = %s""", (status, queue_number, datetime.now().strftime("%Y%m%d")))
            conn.commit()
            logger.info(f"{queue_number} 药品收集完成" if status == 2 else f"{queue_number} 完成取药")
            return True
        except Exception as e:
            logger.error(f"药品收集失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """跳过处理"""
    def skip_queue(self, queue_number: str, reason: str = "过号") -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""UPDATE hqs_queue_records SET status = 'skipped', skip_time = NOW(), skip_reason = %s
                WHERE queue_number = %s AND status = 'calling' AND queue_date = %s""",
                           (reason, queue_number, datetime.now().strftime("%Y%m%d")))
            conn.commit()

            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({
                        'action': 'skip', 'queue_number': queue_number, 'reason': reason }))
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"跳过失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """
    重新唤醒
    保留原号码，默认排在队列第一
    """
    def wake_up(self, patient_id: str, queue_number: str, business_type: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()
            # 获取记录的创建时间和业务类型
            cursor.execute("SELECT * FROM hqs_queue_records WHERE patient_id = %s AND queue_number = %s "
                           "AND business_type = %s AND status = 'skipped' AND queue_date = %s",
                           (patient_id, queue_number, business_type, datetime.now().strftime("%Y%m%d")))
            record = cursor.fetchone()
            if not record:
                conn.rollback()
                return False

            cursor.execute("UPDATE hqs_queue_records SET status='reactivated', queue_number=%s WHERE id = %s",
                           (f"{record['queue_number']}_{datetime.now().strftime('%Y%m%d%H%M%S')}", record['id']))
            # 插入新记录，priority 设为 1
            cursor.execute("""INSERT INTO hqs_queue_records (queue_number, queue_date, patient_id, patient_name, 
                business_id, business_type, business_name, status, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting', 1)""",
                (record['queue_number'], datetime.now().strftime("%Y%m%d"), patient_id, record['patient_name'],
                 record['business_id'], business_type, record['business_name']))

            conn.commit()

            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({
                        'action': 'add',
                        'data': {
                            'queue_number': queue_number, 'patient_name': record['patient_name'],
                            'business_id': record['business_id'], 'business_type': record['business_type'],
                            'business_name': record['business_name']
                        }
                    }))
                except Exception:
                    pass
                try:
                    # 新插入了一条 waiting 记录，增加计数
                    self._update_waiting_counts(record['business_id'], 1)
                except Exception as e:
                    logger.warning(f"Redis 更新 waiting_count 失败: {e}")
            return True
        except Exception as e:
            logger.error(f"唤醒失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    """
    重新激活排号 
    顺延过号：
        - 原记录保留 skipped
        - 新生成一条排队记录，排在队尾
    """
    def reactivate_queue_defer(self, old_queue_number: str, patient_id: str,
                               patient_name: str, business_id: str) -> Optional[str]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            conn.start_transaction()

            cursor.execute("""UPDATE hqs_queue_records SET status = 'reordered' WHERE queue_number = %s 
            AND queue_date = %s""", (old_queue_number, datetime.now().strftime("%Y%m%d")))

            # 生成新排队号
            new_queue_number = self.generate_queue_number(business_id)
            business_name = BUSINESS_TYPES[business_id]['name']
            queue_date = datetime.now().strftime("%Y%m%d")

            cursor.execute("""INSERT INTO hqs_queue_records (queue_number, queue_date, patient_id, patient_name,
                 business_id, business_type, business_name, status) VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting')
            """, (new_queue_number, queue_date, patient_id, patient_name, business_id,
                BUSINESS_TYPES[business_id]['type'], business_name))

            conn.commit()

            # Redis 通知
            if self.redis_client:
                try:
                    self.redis_client.publish('queue_update', json.dumps({
                        'action': 'reactivate_defer',
                        'data': {
                            'old_queue_number': old_queue_number, 'new_queue_number': new_queue_number,
                            'patient_name': patient_name, 'business_id': business_id,
                            'business_type': BUSINESS_TYPES[business_id]['type'], 'business_name': business_name
                        }
                    }))
                except Exception:
                    pass
                try:
                    # 新插入了一条 waiting 记录，增加计数
                    self._update_waiting_counts(business_id, 1)
                except Exception as e:
                    logger.warning(f"Redis 更新 waiting_count 失败: {e}")

            return new_queue_number
        except Exception as e:
            conn.rollback()
            logger.error(f"顺延过号失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


    # ====================== 查询方法 ======================
    """获取窗口列表"""
    def get_windows_list(self) -> List[Dict]:
        if self.redis_client:
            try:
                windows = self.redis_client.get(WINDOW_KEY)
                if windows:
                    windows = json.loads(windows)
                else:
                    windows = self.cache_data()
                return windows
            except Exception as redis_e:
                logger.warning(f"Redis 获取窗口列表失败: {redis_e}")
        return []

    def get_window_info(self, window_id: int) -> Dict:
        windows = self.get_windows_list()
        for window in windows:
            if window['id'] == window_id:
                return window
        return {}

    def get_waiting_count(self, business_id: str = None) -> int:
        date_str = datetime.now().strftime("%Y%m%d")
        if self.redis_client:
            try:
                if business_id:
                    key = f"waiting_count:{business_id}:{date_str}"
                    val = self.redis_client.get(key)
                    if val is not None:
                        # return int(val)
                        int_val = int(val)
                        if int_val < 0:
                            # 从数据库获取真实值并修正
                            actual = self._get_waiting_count_from_db(business_id)  # 实现下面的辅助方法
                            self.redis_client.set(key, actual)
                            return actual
                        return int_val
                else:
                    # 全局：累加所有业务类型
                    total = 0
                    for bt in set(bt_id for bt_id in BUSINESS_TYPES.keys()):
                        val = self.redis_client.get(f"waiting_count:{bt}:{date_str}")
                        total += int(val) if val else 0
                    return total
            except Exception as e:
                logger.warning(f"Redis 读取 waiting_count 失败: {e}")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if business_id:
                cursor.execute(""" SELECT COUNT(*) FROM hqs_queue_records WHERE business_id = %s AND status = 'waiting' 
                AND queue_date = %s """, (business_id, datetime.now().strftime("%Y%m%d")))
            else:
                cursor.execute("SELECT COUNT(*) FROM hqs_queue_records WHERE status = 'waiting' "
                               "AND queue_date = %s ", (datetime.now().strftime("%Y%m%d"), ))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def _get_waiting_count_from_db(self, business_id: str = None) -> int:
        """直接从数据库查询等待人数（不依赖 Redis）"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            date_str = datetime.now().strftime("%Y%m%d")
            if business_id:
                cursor.execute("""SELECT COUNT(*) FROM hqs_queue_records 
                                  WHERE business_id = %s AND status = 'waiting' AND queue_date = %s""",
                               (business_id, date_str))
            else:
                cursor.execute("""SELECT COUNT(*) FROM hqs_queue_records 
                                  WHERE status = 'waiting' AND queue_date = %s""", (date_str,))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def get_avg_wait_time(self, business_id: str = None):
        date_str = datetime.now().strftime("%Y%m%d")
        if self.redis_client:
            try:
                if business_id:
                    completed = self.redis_client.get(f"completed_count:{business_id}:{date_str}")
                    total_sec = self.redis_client.get(f"total_wait_time:{business_id}:{date_str}")
                    if completed is not None and total_sec is not None:
                        completed = int(completed)
                        total_sec = int(total_sec)
                        if completed == 0:
                            return 0
                        return int(total_sec / completed / 60)  # 转换为分钟
                else:
                    # 全局：累加所有业务
                    total_sec_all = 0
                    completed_all = 0
                    for bt in set(bt_id for bt_id in BUSINESS_TYPES.keys()):
                        comp = self.redis_client.get(f"completed_count:{bt}:{date_str}")
                        tsec = self.redis_client.get(f"total_wait_time:{bt}:{date_str}")
                        completed_all += int(comp) if comp else 0
                        total_sec_all += int(tsec) if tsec else 0
                    if completed_all == 0:
                        return 0
                    return int(total_sec_all / completed_all / 60)
            except Exception as e:
                logger.warning(f"Redis 读取 avg_wait_time 失败: {e}")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if business_id:
                cursor.execute("""
                    select AVG(timestampdiff(second,create_time, complete_time)) / 60  from hqs_queue_records 
                    WHERE business_id = %s AND queue_date = %s 
                """, (business_id, datetime.now().strftime("%Y%m%d")))
            else:
                cursor.execute("SELECT AVG(timestampdiff(second,create_time, complete_time)) / 60 "
                               "FROM hqs_queue_records WHERE queue_date = %s ",
                               (datetime.now().strftime("%Y%m%d"), ))

            da = cursor.fetchone()
            return  int(da[0]) if da[0] else 0
        finally:
            cursor.close()
            conn.close()

    def get_today_total(self, business_id: str = None):
        date_str = datetime.now().strftime("%Y%m%d")
        if self.redis_client:
            try:
                if business_id:
                    key = f"today_total:{business_id}:{date_str}"
                    val = self.redis_client.get(key)
                    if val is not None:
                        return int(val)
                else:
                    total = 0
                    for bt in set(bt_id for bt_id in BUSINESS_TYPES.keys()):
                        val = self.redis_client.get(f"today_total:{bt}:{date_str}")
                        total += int(val) if val else 0
                    return total
            except Exception as e:
                logger.warning(f"Redis 读取 today_total 失败: {e}")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if business_id:
                cursor.execute("""select COUNT(*) from hqs_queue_records  WHERE business_id = %s AND queue_date = %s
                   """, (business_id, datetime.now().strftime("%Y%m%d")))
            else:
                cursor.execute("SELECT COUNT(*) FROM hqs_queue_records WHERE queue_date = %s ",
                               (datetime.now().strftime("%Y%m%d"),))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def get_queue_list(self, business_ids=None, status: str = 'waiting') -> List[Dict]:
        if business_ids is None:
            business_ids = []
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            if business_ids:
                placeholders = ','.join(f"'{item}'" for item in business_ids)
                sql = f"""SELECT * FROM hqs_queue_records WHERE business_id IN ({placeholders}) AND status = '{status}' 
                AND queue_date = '{datetime.now().strftime('%Y%m%d')}' ORDER BY FIELD(business_id, {placeholders}), priority DESC, create_time ASC """
                cursor.execute(sql)
            else:
                cursor.execute("""SELECT * FROM hqs_queue_records WHERE status = %s AND queue_date = %s
                    ORDER BY create_time ASC """, (status, datetime.now().strftime('%Y%m%d')))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_history_list(self, window_id: int) -> List[Dict]:
        if not window_id:
            return []
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(f"""SELECT queue_number, status, patient_name, business_name, create_time, complete_time, skip_time 
                                FROM hqs_queue_records WHERE window_id = {window_id} and status = 'completed'
                                AND queue_date = '{datetime.now().strftime('%Y%m%d')}' ORDER BY create_time DESC """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_all_business_status(self) -> Dict:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""
                SELECT business_id, business_type, business_name, status 
                FROM hqs_queue_records WHERE (status = 'waiting' or status = 'skipped') and queue_date = %s
            """, (datetime.now().strftime('%Y%m%d'), ))
            status_list = cursor.fetchall()
            result = {}
            for item in status_list:
                if item['business_id'] not in result:
                    result[item['business_id']] = {
                        'name': item['business_name'],
                        'waiting_count': 0,
                        'skipped_count': 0
                    }
                if item['status'] == 'skipped':
                    result[item['business_id']]['skipped_count'] += 1
                if item['status'] == 'waiting':
                    result[item['business_id']]['waiting_count'] += 1
            return result
        finally:
            cursor.close()
            conn.close()

    def get_current_calls(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""SELECT * FROM hqs_queue_records WHERE status = 'calling' and queue_date = %s 
            ORDER BY call_time DESC """, (datetime.now().strftime('%Y%m%d'), ))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_current_window_calls(self, window_id: int) -> Dict:
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("""SELECT * FROM hqs_queue_records WHERE status = 'calling' AND window_id = %s 
            and queue_date = %s""", (window_id, datetime.now().strftime('%Y%m%d')))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def update_medicine_payment(self, medicine_id: int) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(""" UPDATE hqs_medicine_payments SET status = 'paid', paid_time = NOW()
                WHERE id = %s AND status = 'unpaid' """, (medicine_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新缴费状态失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_overdue_list(self, business_type, window_id):
        """查询过号列表"""
        condition_sql = ""
        if business_type:
            condition_sql = condition_sql + f" AND business_type = '{business_type}' "
        if window_id:
            condition_sql = condition_sql + f" AND window_id = {window_id} "
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            sql = f"""SELECT * FROM hqs_queue_records WHERE status = 'skipped' AND queue_date = %s {condition_sql} ORDER BY create_time ASC """
            cursor.execute(sql, (datetime.now().strftime('%Y%m%d'), ))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    """启动药品取药状态监控线程（每10秒）"""
    def get_medicines_state(self, ids) -> List[Dict]:
        """查询患者取药状态"""
        try:
            sql = f"""select shenfenzh shenfenzh,max(fayaobz) fayaobz
                from(select gb.shenfenzh,my.fayaobz,mj.jiesuanid,
                dense_rank() over (partition by gb.shenfenzh order by  mj.shoufeirq desc) as rk
                        from df_lc_menzhen.zj_jiuzhenxx zj
                        join df_lc_menzhen.mz_yizhu my on zj.jiuzhenid = my.jiuzhenid and my.yizhulx in ('11','12','13')
                        left join df_bingrenzsy.gy_bingrenxx gb on zj.bingrenid = gb.bingrenid
                        left join df_jj_menzhen.mz_feiyong2 mf on my.yizhuid=mf.yizhubh 
                        left join df_jj_menzhen.mz_feiyong1 mf2 on mf.feiyongid = mf2.feiyongid
                        left join df_jj_menzhen.mz_jiesuan1 mj on mf2.jiesuanid  = mj.jiesuanid and mj.jiaoyilx=1 and mj.chongxiaobz =0
                        where zj.jiuzhenrq::date=current_date and gb.shenfenzh in ({ids})) v  where rk=1 group by shenfenzh"""
            return self.pg_query(sql)
        except Exception as e:
            logger.error(f"查询患者取药状态失败: {e}")
            return []

    def _start_medicine_monitor(self):
        if self._medicine_monitor_running:
            return
        self._medicine_monitor_running = True

        def monitor_loop():
            # 记录上一次的药品 ID 列表，用于检测变化
            logger.debug("药品状态监控线程已启动，每10秒执行一次")
            while True:
                try:
                    if self.redis_client:
                        all_items = self.redis_client.lrange('unmedicine_queue', 0, -1)
                        if all_items:
                            ids = ','.join([f"'{item}'" for item in all_items])
                            try:
                                unmedicines = self.get_medicines_state(ids)
                                updated_ids = [item['shenfenzh'] for item in unmedicines if item['fayaobz'] == 1]
                                if updated_ids:
                                    pipe = self.redis_client.pipeline()
                                    for item_id in updated_ids:
                                        pipe.lrem('unmedicine_queue', 0, item_id)
                                    pipe.execute()
                                    try:
                                        updated_ids = ','.join([f"'{item}'" for item in updated_ids])
                                        conn = self.get_connection()
                                        cursor = conn.cursor(dictionary=True, buffered=True)
                                        cursor.execute("""UPDATE hqs_queue_records SET medication_state = 1 WHERE patient_id in (%s) 
                                        AND queue_date = %s AND medication_state = 0 and business_id = '1' """, (updated_ids, datetime.now().strftime("%Y%m%d")))
                                    finally:
                                        cursor.close()
                                        conn.close()
                            except Exception as e:
                                logger.error(f"查询患者取药状态失败: {e}")

                            # manager.send_to_pharmacy({'type': 'pharmacy_update'})
                            # 关键修改：使用 asyncio.run 执行异步协程
                            asyncio.run(manager.broadcast_to_pharmacy({'type': 'pharmacy_update'}))

                    # 每10秒执行一次
                    time.sleep(20)
                except Exception as e:
                    logger.error(f"药品状态监控循环异常: {e}")
                    time.sleep(20)  # 出错后仍然等待

        thread = threading.Thread(target=monitor_loop, daemon=True, name="MedicineStatusMonitor")
        thread.start()
        logger.info("药品状态监控线程已启动")

    # ====================== 辅助方法 ======================
    def sync_redis_from_mysql(self):
        """可选：从 MySQL 同步 waiting 记录到 Redis（对账用）"""
        if not self.redis_client:
            logger.warning("Redis 未连接，跳过同步")
            return
        try:
            # 清空旧队列（如果之前有维护 list）
            for bt in BUSINESS_TYPES:
                self.redis_client.delete(f'queue:{bt}')
            logger.info("Redis 队列已清空并准备重新同步")
        except Exception as e:
            logger.warning(f"Redis 同步失败: {e}")

    def close(self):
        """应用关闭时清理资源"""
        if self.pool:
            self.pool.close()
            logger.info("MySQL 连接池已关闭")
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis 连接已关闭")

    def pg_query(self, sql):
        results = []
        DB_CONFIG = {"dbname": "df_his", "user": "ogg", "password": "nyogg@2024",
                     "host": "192.168.8.57", "port": "6000"}
        max_retries, retry_count, retry_delay = 2, 0, 1
        if retry_count != 0:
            max_retries = retry_count
        while retry_count < max_retries:
            try:
                # 使用 `with` 语句确保自动关闭连接
                with psycopg2.connect(**DB_CONFIG) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(sql)
                        datas = cur.fetchall()
                        for row in datas:
                            results.append(dict(row))
                return results
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                    logger.warning(f"数据库连接失败，第 {retry_count}/{max_retries} 次重试... {sleep_time} 秒后重试")
                else:
                    logger.error(f"数据库操作失败，已达最大重试次数 {max_retries}。最后错误: {str(e)}\nSQL: {sql}")
                    return []
        return results



    def _safe_decr(self, key: str) -> int:
        """
        原子递减，保证结果不为负数。
        返回递减后的值；若当前值≤0，则返回0且不递减。
        使用 Lua 脚本保证原子性。
        """
        if not self.redis_client:
            return 0
        lua = """
            local key = KEYS[1]
            local val = redis.call('GET', key)
            if val and tonumber(val) > 0 then
                return redis.call('DECR', key)
            else
                return 0
            end
        """
        try:
            return int(self.redis_client.eval(lua, 1, key))
        except Exception as e:
            logger.warning(f"安全递减 Redis 键 {key} 失败: {e}")
            return 0

    def _safe_incr(self, key: str, delta: int = 1) -> int:
        """
        原子递增，返回递增后的值。
        若键不存在，则先设置为0再递增。
        """
        if not self.redis_client:
            return 0
        try:
            return int(self.redis_client.incrby(key, delta))
        except Exception as e:
            logger.warning(f"递增 Redis 键 {key} 失败: {e}")
            return 0

    def _update_waiting_counts(self, business_id: str, delta: int):
        """
        统一更新 waiting_count 计数（包括业务维度和全局维度）。
        delta 可为正（增）或负（减）。
        """
        date_str = datetime.now().strftime("%Y%m%d")
        key_biz = f"waiting_count:{business_id}:{date_str}"
        key_all = f"waiting_count:all:{date_str}"
        if delta > 0:
            self._safe_incr(key_biz, delta)
            self._safe_incr(key_all, delta)
        elif delta < 0:
            # 递减时使用安全方法，避免负数
            self._safe_decr(key_biz)
            self._safe_decr(key_all)
        else:
            return

        # 可选：同步更新 today_total 等，但此处只处理 waiting_count

# # 单例实例（在 FastAPI 中直接导入使用）
# db = DatabaseManager()



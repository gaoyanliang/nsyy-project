import logging
import time

import pymysql
import redis
from contextlib import contextmanager
from datetime import datetime

from pymysql.cursors import DictCursor

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

lock_redis_client = redis.Redis(connection_pool=pool)
logger = logging.getLogger(__name__)


@contextmanager
def redis_lock(key, timeout=5):
    lock_key = f"lock:{key}"
    acquired = False
    try:
        start = time.time()
        while time.time() - start < timeout:
            if lock_redis_client.set(lock_key, "1", nx=True, ex=timeout):
                acquired = True
                break
            time.sleep(0.05)
        if not acquired:
            raise Exception(f"Failed to acquire lock for {key}")
        yield
    finally:
        if acquired:
            lock_redis_client.delete(lock_key)


def acquire_lock(room):
    """获取Redis分布式锁"""
    lock_key = f"lock:{room}"
    return lock_redis_client.set(lock_key, "1", nx=True, ex=5)  # 5秒锁


def release_lock(room):
    """释放锁"""
    lock_redis_client.delete(f"lock:{room}")


"""推送给前端"""


def broadcast_update():
    """广播所有队列状态"""
    logger.info('推送给前端')
    # with pymysql.connect(**global_config.db_config) as conn:
    #     with conn.cursor(cursor=DictCursor) as cur:
    #         cur.execute("SELECT * FROM person_queue WHERE status!='done' ORDER BY room, order_index")
    #         rows = cur.fetchall()
    # 
    # for item in rows:
    #     item['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # socketio.emit('queue_update', rows, broadcast=True)


"""查询房间排队列表"""


def query_queue(room_list):
    if not room_list:
        return []
    rooms = ','.join(f'{item}' for item in room_list)
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute("SELECT * FROM person_queue WHERE status!='done' ORDER BY room, order_index")
            rows = cur.fetchall()

    for item in rows:
        item['created_at'] = item['created_at'].strftime("%Y-%m-%d %H:%M:%S") if item['created_at'] else ''
        item['updated_at'] = item['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if item['updated_at'] else ''
    return rows


"""排号入队"""


def enqueue(room, name):
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute("SELECT MAX(order_index) AS max_idx FROM person_queue WHERE room=%s", (room,))
            max_idx = cur.fetchone()
            max_idx = max_idx[0] or 0
            cur.execute("INSERT INTO person_queue (name, room, order_index) VALUES (%s,%s,%s)",
                        (name, room, max_idx + 1))
        conn.commit()
    logging.info(f"{room} 新增排队人员: {name}")
    broadcast_update()


"""出对列"""


def dequeue(room):
    try:
        with pymysql.connect(**global_config.db_config) as conn:
            with conn.cursor(cursor=DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM person_queue WHERE room=%s AND status='waiting' ORDER BY order_index LIMIT 1", (room,))
                person = cur.fetchone()
                if not person:
                    return None

                # 标记为服务中
                cur.execute("UPDATE person_queue SET status='serving' WHERE id=%s", (person['id'],))
                conn.commit()

        logging.info(f"{room} 开始叫号: {person['name']}")
        broadcast_update()
        return person

    except Exception as e:
        logging.error(f"Dequeue error, {e}")
        return None
    finally:
        release_lock(room)


"""从队列中移除某个人"""


def remove_person(pid):
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute("UPDATE person_queue SET status='removed' WHERE id=%s", (pid,))
        conn.commit()
    broadcast_update()
    logging.info(f"人员ID={pid} 已标记为 removed")


"""
标记某人过号
    mode = 'delay'   顺延（保持在队列中，插入到第N位之后）
    mode = 'requeue' 重新排号（新建记录）
"""


def missed(pid, mode: str = 'delay'):
    if not pid:
        raise ValueError('missing person id')

    # Redis 分布式锁，避免并发叫号冲突
    with redis_lock(f"missed_lock:{pid}"):
        with pymysql.connect(**global_config.db_config) as conn:
            with conn.cursor(cursor=DictCursor) as cur:
                cur.execute("SELECT * FROM person_queue WHERE id=%s", (pid,))
                person = cur.fetchone()
                if not person:
                    raise ValueError('invalid person id')

                room = person['room']
                name = person['name']

                if mode == 'delay':
                    # 获取当前队列
                    cur.execute("""
                        SELECT id, order_index FROM person_queue
                        WHERE room=%s AND status='waiting'
                        ORDER BY order_index
                    """, (room,))
                    waiting = cur.fetchall()

                    # 顺延到第3个等待者后（可调）
                    if len(waiting) >= 3:
                        ref_order = float(waiting[2]['order_index'])
                        new_order = ref_order + 0.1
                    elif waiting:
                        new_order = float(waiting[-1]['order_index']) + 0.1
                    else:
                        new_order = 1

                    cur.execute("""
                        UPDATE person_queue
                        SET status='waiting', order_index=%s
                        WHERE id=%s
                    """, (new_order, pid))
                    msg = f"{room} 房间 {name} 过号顺延，排在后面"

                elif mode == 'requeue':
                    # 标记原记录为 missed
                    cur.execute("""
                        UPDATE person_queue
                        SET status='missed'
                        WHERE id=%s
                    """, (pid,))
                    # 重新插入队尾
                    cur.execute("""
                        SELECT MAX(order_index) AS max_idx FROM person_queue WHERE room=%s
                    """, (room,))
                    max_idx = cur.fetchone()['max_idx'] or 0
                    cur.execute("""
                        INSERT INTO person_queue (name, room, order_index, status)
                        VALUES (%s, %s, %s, 'waiting')
                    """, (name, room, max_idx + 1))
                    msg = f"{room} 房间 {name} 过号重新排号"

                else:
                    raise ValueError('invalid mode')

            conn.commit()

    logging.info(msg)
    broadcast_update()  # 通过 WebSocket 通知前端更新
    return msg


"""重新排序"""


def reorder(room, order_list):
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            for idx, pid in enumerate(order_list, start=1):
                cur.execute("UPDATE person_queue SET order_index=%s WHERE id=%s", (idx, pid))
        conn.commit()
    broadcast_update()
    logging.info(f"{room} 队列重新排序: {order_list}")


"""完成叫号"""


def done(pid):
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute("UPDATE person_queue SET status='done' WHERE id=%s", (pid,))
        conn.commit()
    broadcast_update()
    logging.info(f"人员ID={pid} 已完成叫号 (done)")


"""清理过期排队数据"""


def cleanup_old_records(days: int = 30):
    with pymysql.connect(**global_config.db_config) as conn:
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute(
                "DELETE FROM person_queue WHERE status IN ('done', 'removed') AND created_at < NOW() - INTERVAL %s DAY",
                (days,))
        conn.commit()
    logging.info(f"已清理 {days} 天前的历史记录")



from datetime import datetime
import redis
import json
import threading
from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.workstation import ws_config

'''
workstation 有以下定时任务需求：

-- 消息模块 --
1. 每两分钟将缓存中的新消息入库
2. 每两分钟将缓存中的历史聊天人入库

'''

pool = redis.ConnectionPool(host=ws_config.REDIS_HOST, port=ws_config.REDIS_PORT,
                            db=ws_config.REDIS_DB, decode_responses=True)
# Create a scheduler
write_message_lock = threading.Lock()
write_historical_contacts_lock = threading.Lock()


#  ==========================================================================================
#  ==========================     消息模块      ==============================================
#  ==========================================================================================

def write_data_to_db():
    write_message()
    write_historical_contacts()


def write_message():
    with write_message_lock:
        redis_client = redis.Redis(connection_pool=pool)
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        all_elements = redis_client.lrange(ws_config.NEW_MESSAGE, 0, -1)
        element_len = len(all_elements)
        if element_len <= 0:
            return

        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '开始写入 ' + str(element_len) + ' 条新消息')
        redis_client.ltrim(ws_config.NEW_MESSAGE, element_len, -1)

        for element in all_elements:
            msg = json.loads(element)
            if int(msg.get('chat_type') == 0):
                args = (
                    int(msg.get('id')), int(msg.get('chat_type')), int(msg.get('context_type')), int(msg.get('sender')),
                    msg.get('sender_name'), msg.get('receiver'), msg.get('context'), msg.get('timer'))
                insert_sql = "INSERT INTO nsyy_gyl.ws_message (id, chat_type, context_type, " \
                             "sender, sender_name, receiver, context, timer) " \
                             "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
                last_rowid = db.execute(insert_sql, args, need_commit=True)
                if last_rowid == -1:
                    print(datetime.now(), "新消息入库失败, ", args)
            elif int(msg.get('chat_type') == 1):
                args = (
                    int(msg.get('id')), int(msg.get('chat_type')), int(msg.get('context_type')), int(msg.get('sender')),
                    msg.get('sender_name'), msg.get('receiver'), msg.get('receiver_name'),
                    msg.get('context'), msg.get('timer'))
                insert_sql = "INSERT INTO nsyy_gyl.ws_message (id, chat_type, context_type, " \
                             "sender, sender_name, receiver, receiver_name, context, timer) " \
                             "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                last_rowid = db.execute(insert_sql, args, need_commit=True)
                if last_rowid == -1:
                    print(datetime.now(), "新消息入库失败, ", args)
            elif int(msg.get('chat_type') == 2):
                args = (
                    int(msg.get('id')), int(msg.get('chat_type')), int(msg.get('context_type')), int(msg.get('sender')),
                    msg.get('sender_name'), msg.get('group_id'), msg.get('receiver'), msg.get('receiver_name'),
                    msg.get('context'), msg.get('timer'))
                insert_sql = "INSERT INTO nsyy_gyl.ws_message (id, chat_type, context_type, " \
                             "sender, sender_name, group_id, receiver, receiver_name, context, timer) " \
                             "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                last_rowid = db.execute(insert_sql, args, need_commit=True)
                if last_rowid == -1:
                    print(datetime.now(), "新消息入库失败, ", args)

        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '写入完成 ')


def write_historical_contacts():
    with write_historical_contacts_lock:
        redis_client = redis.Redis(connection_pool=pool)
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        all_elements = redis_client.lrange(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, 0, -1)
        element_len = len(all_elements)
        if element_len <= 0:
            return
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '开始写入 ' + str(element_len) + ' 条历史联系人记录')
        redis_client.ltrim(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, element_len, -1)

        for element in all_elements:
            record = json.loads(element)
            if record.get('chat_type') == ws_config.PRIVATE_CHAT:
                # 私聊
                query_sql = "select * from nsyy_gyl.ws_historical_contacts " \
                            "where user_id = {} and chat_type = {} and chat_id = {} " \
                    .format(int(record.get('user_id')), int(record.get('chat_type')), int(record.get('chat_id')))
                hc = db.query_one(query_sql)
                if hc is None:
                    args = (int(record.get('user_id')), record.get('user_name'), int(record.get('chat_type')),
                            int(record.get('chat_id')), record.get('chat_name'), int(record.get('last_msg_id'))
                            , record.get('last_msg'), record.get('last_msg_time'))
                    insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts (user_id, user_name, chat_type, " \
                                 "chat_id, chat_name, last_msg_id, last_msg, last_msg_time) " \
                                 "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        print(datetime.now(), "历史联系人入库失败!", args)
                else:
                    update_sql = 'UPDATE nsyy_gyl.ws_historical_contacts ' \
                                 'SET last_msg_id = %s, last_msg = %s, last_msg_time = %s' \
                                 ' WHERE user_id = %s and chat_type = %s and chat_id = %s '
                    args = (record.get('last_msg_id'), record.get('last_msg'), record.get('last_msg_time'),
                            int(record.get('user_id')), int(record.get('chat_type')), int(record.get('chat_id')))
                    db.execute(update_sql, args, need_commit=True)
            elif record.get('chat_type') == ws_config.GROUP_CHAT:
                # 群聊
                query_sql = "select * from nsyy_gyl.ws_historical_contacts " \
                            "where user_id = {} and chat_type = {} and group_id = {} " \
                    .format(int(record.get('user_id')), int(record.get('chat_type')), int(record.get('group_id')))
                hc = db.query_one(query_sql)
                if hc is None:
                    args = (int(record.get('user_id')), record.get('user_name'), int(record.get('chat_type')),
                            int(record.get('group_id')), int(record.get('last_msg_id')),
                            int(record.get('chat_id')), record.get('chat_name')
                            , record.get('last_msg'), record.get('last_msg_time'))
                    insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts (user_id, user_name, chat_type, " \
                                 "group_id, last_msg_id, chat_id, chat_name, last_msg, last_msg_time) " \
                                 "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        print(datetime.now(), "历史联系人入库失败!", args)
                else:
                    update_sql = 'UPDATE nsyy_gyl.ws_historical_contacts ' \
                                 'SET last_msg_id = %s, last_msg = %s, last_msg_time = %s' \
                                 ' WHERE user_id = %s and chat_type = %s and group_id = %s '
                    args = (record.get('last_msg_id'), record.get('last_msg'), record.get('last_msg_time'),
                            int(record.get('user_id')), int(record.get('chat_type')), int(record.get('group_id')))
                    db.execute(update_sql, args, need_commit=True)
            elif record.get('chat_type') == ws_config.NOTIFICATION_MESSAGE:
                # 通知
                query_sql = "select * from nsyy_gyl.ws_historical_contacts " \
                            "where user_id = {} and chat_type = {} " \
                    .format(int(record.get('user_id')), int(record.get('chat_type')))
                hc = db.query_one(query_sql)
                if hc is None:
                    args = (int(record.get('user_id')), record.get('user_name'),
                            int(record.get('chat_type')), int(record.get('last_msg_id')),
                            record.get('last_msg'), record.get('last_msg_time'))
                    insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts (user_id, user_name, chat_type, " \
                                 "last_msg_id, last_msg, last_msg_time) " \
                                 "VALUES (%s,%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        print(datetime.now(), "历史联系人入库失败!", args)
                else:
                    update_sql = 'UPDATE nsyy_gyl.ws_historical_contacts ' \
                                 'SET last_msg_id = %s, last_msg = %s, last_msg_time = %s' \
                                 ' WHERE user_id = %s and chat_type = %s and chat_id = %s '
                    args = (int(record.get('last_msg_id')), record.get('last_msg'), record.get('last_msg_time'),
                            int(record.get('user_id')), int(record.get('chat_type')), record.get('chat_id'))
                    db.execute(update_sql, args, need_commit=True)


# def schedule_task():
#     scheduler.add_job(write_message, trigger='interval', minutes=6)
#     scheduler.add_job(write_historical_contacts, trigger='interval', minutes=10)
#
#     # Start the scheduler
#     scheduler.start()

# schedule_task()

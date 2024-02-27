import json
import random
import redis
import string
import threading
from datetime import datetime

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.workstation import ws_config
from gylmodules.workstation.socket_push import push

pool = redis.ConnectionPool(host=ws_config.REDIS_HOST, port=ws_config.REDIS_PORT,
                            db=ws_config.REDIS_DB, decode_responses=True)



# 消息id 初始为 0
# 为 0 时，从数据库查询最新消息的id 进行更新
# 不为 0 时，自增
message_id = -1
message_id_lock = threading.Lock()

group_id = -1
group_id_lock = threading.Lock()


def get_message_id():
    global message_id

    with message_id_lock:
        if message_id == -1:
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            query_sql = 'select count(*) from nsyy_gyl.ws_message'
            count = db.query_one(query_sql)
            message_id = int(count.get('count(*)'))

        # Increment the ID and return the new value
        message_id += 1
        next_id = message_id

    return next_id


def get_group_id():
    global group_id

    with group_id_lock:
        if group_id == -1:
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            query_sql = 'select count(*) from nsyy_gyl.ws_group'
            count = db.query_one(query_sql)
            group_id = int(count.get('count(*)'))

        # Increment the ID and return the new value
        group_id += 1
        next_id = group_id

    return next_id


#  ==========================================================================================
#  ==========================     消息管理      ==============================================
#  ==========================================================================================


def send_chat_message(context_type: int, sender: int, group_id: int, receiver: int, context: str):
    """
    发送聊天消息 💬
    :param context_type:
    :param sender:
    :param group_id:
    :param receiver:
    :param context:
    :return:
    """
    send_message(ws_config.CHAT_MESSAGE, context_type, sender, group_id, receiver, context)


def send_notification_message(context_type: int, receiver: str, context: str):
    """
    发送通知消息 📢
    :param context_type:
    :param receiver:
    :param context:
    :return:
    """
    send_message(ws_config.NOTIFICATION_MESSAGE, context_type, None, None, receiver, context)


def send_message(msg_type: int, context_type: int, sender: int, group_id: int, receiver: str, context: str):
    """
    发送消息，并通过 socket 通知
    :param msg_type:
    :param context_type:
    :param sender:
    :param group_id:
    :param receiver:
    :param context:
    :return:
    """
    # 1. 获取消息 id, 并将消息组装为 json str
    new_message_id = get_message_id()
    timer = datetime.now()
    new_message = {
        'id': new_message_id,
        'msg_type': msg_type,
        'context_type': context,
        'sender': sender,
        'group_id': group_id,
        'receiver': receiver,
        'context': context,
        'timer': timer

    }

    # 2. 将最新消息缓存到 redis
    redis_client = redis.Redis(connection_pool=pool)
    if msg_type == ws_config.NOTIFICATION_MESSAGE:
        # 📢 通知消息
        receivers = receiver.split(',')
        for recv in receivers:
            msg_redis_key = 'NotificationMessage[' + str(recv) + ']'
            redis_client.rpush(msg_redis_key, json.dumps(new_message, default=str))


            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and FIND_IN_SET( {}, receiver) > 0 ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.NOTIFICATION_MESSAGE, recv)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 100 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} ' \
                            'and FIND_IN_SET( {}, receiver) > 0 ' \
                            'order by id desc limit 200 '.format(ws_config.NOTIFICATION_MESSAGE, recv)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))
    else:
        # 💬聊天消息
        if group_id is None:
            # 私聊, 保证双方发送的消息用同一个 key
            if sender <= int(receiver):
                msg_redis_key = 'PrivateChat[' + str(sender) + '-to-' + str(receiver) + ']'
            else:
                msg_redis_key = 'PrivateChat[' + str(receiver) + '-to-' + str(sender) + ']'

            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and ((sender = {} and receiver = {}) or (sender = {} and receiver = {})) ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.CHAT_MESSAGE, sender, receiver,
                                                                 receiver, sender)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 200 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} and ' \
                            ' ((sender = {} and receiver = {}) or (sender = {} and receiver = {})) ' \
                            'order by id desc limit 200 '.format(ws_config.CHAT_MESSAGE, sender, receiver, receiver,
                                                                 sender)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))
        else:
            # 群聊
            msg_redis_key = 'GroupChat[' + str(group_id) + ']'

            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and group_id = {} ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.CHAT_MESSAGE, group_id)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 200 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} ' \
                            'and group_id = {} ' \
                            'order by id desc limit 200 '.format(ws_config.CHAT_MESSAGE, group_id)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

    del db







    # 1. 将消息入库
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    timer = datetime.now()
    args = (msg_type, context_type, sender, group_id, receiver, context, timer)
    insert_sql = "INSERT INTO nsyy_gyl.ws_message (msg_type, context_type, sender, group_id, receiver, context, timer)" \
                 " VALUES (%s,%s,%s,%s,%s,%s,%s)"
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        raise Exception("消息入库失败!")
    del db

    # 记录历史联系人
    if msg_type == ws_config.CHAT_MESSAGE:
        if group_id is None:
            record_historical_contacts(sender, ws_config.PRIVATE_CHAT, int(receiver), context, timer)
        else:
            record_historical_contacts(sender, ws_config.GROUP_CHAT, group_id, context, timer)

    move_message_to_redis_cache(msg_type, group_id, sender, str(receiver))

    # 2. 通过 socket 向接收者推送通知
    socket_push(last_rowid)


def move_message_to_redis_cache(type: int, group_id: int, sender: int, receiver: str):
    """
    将消息放入 redis 缓存（根据缓存哪的数据进行更新）
    从缓存中取出最后一条数据，从数据库中查询，该条消息之后是否又其他消息，取最新的 200 条存入缓存
    缓存中不存在，直接取数据库中最新的200条
    :param type:
    :param group_id:
    :param sender:
    :param receiver:
    :return:
    """

    # 将最新消息缓存到 redis
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if type == ws_config.NOTIFICATION_MESSAGE:
        # 📢 通知消息
        receivers = receiver.split(',')
        for recv in receivers:
            msg_redis_key = 'NotificationMessage[' + str(recv) + ']'
            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and FIND_IN_SET( {}, receiver) > 0 ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.NOTIFICATION_MESSAGE, recv)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 100 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} ' \
                            'and FIND_IN_SET( {}, receiver) > 0 ' \
                            'order by id desc limit 200 '.format(ws_config.NOTIFICATION_MESSAGE, recv)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))
    else:
        # 💬聊天消息
        if group_id is None:
            # 私聊, 保证双方发送的消息用同一个 key
            if sender <= int(receiver):
                msg_redis_key = 'PrivateChat[' + str(sender) + '-to-' + str(receiver) + ']'
            else:
                msg_redis_key = 'PrivateChat[' + str(receiver) + '-to-' + str(sender) + ']'

            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and ((sender = {} and receiver = {}) or (sender = {} and receiver = {})) ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.CHAT_MESSAGE, sender, receiver,
                                                                 receiver, sender)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 200 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 100 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} and ' \
                            ' ((sender = {} and receiver = {}) or (sender = {} and receiver = {})) ' \
                            'order by id desc limit 200 '.format(ws_config.CHAT_MESSAGE, sender, receiver, receiver,
                                                                 sender)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))
        else:
            # 群聊
            msg_redis_key = 'GroupChat[' + str(group_id) + ']'

            # 从 redis 缓存中取出最后一条消息，然后查询该条消息之后所有的新消息
            if redis_client.exists(msg_redis_key) == 1:
                list_len = redis_client.llen(msg_redis_key)
                msg_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)
                # 将 JSON 对象转换为 Python 字典
                data = json.loads(msg_data_in_redis[0])
                msg_id = data['id']

                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where id > {} and msg_type = {} ' \
                            'and group_id = {} ' \
                            'order by id desc limit 200 '.format(int(msg_id), ws_config.CHAT_MESSAGE, group_id)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

                    # redis 缓存中只保存最新的 200 条消息
                    if list_len + len(msg_list) > 200:
                        redis_client.ltrim(msg_redis_key, 0, list_len + len(msg_list) - 201)
            else:
                # 如果不存在，直接存入
                # 查询最新的 200 条消息（如果消息量大）
                query_sql = 'select * from nsyy_gyl.ws_message where msg_type = {} ' \
                            'and group_id = {} ' \
                            'order by id desc limit 200 '.format(ws_config.CHAT_MESSAGE, group_id)
                msg_list = db.query_all(query_sql)

                if msg_list is not None:
                    for m in reversed(msg_list):
                        redis_client.rpush(msg_redis_key, json.dumps(m, default=str))

    del db


def socket_push(msg_id: int):
    """
    通过 socket 向用户推送通知, 同时更新未读消息未读数量（缓存数量加一）
    :param msg_id:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = 'select * from nsyy_gyl.ws_message where id = {} '.format(msg_id)
    msg = db.query_one(query_sql)

    msg_type = msg.get('msg_type')
    # 聊天消息推送
    if msg_type == ws_config.CHAT_MESSAGE:
        # 向所有用户推送未读消息数量，以及最后一条消息内容
        msg_group_id = msg.get('group_id')
        msg_receiver = msg.get('receiver')
        msg_sender = msg.get('sender')
        # 私聊
        if msg_group_id is None:
            # 查询未读数量（先读缓存，缓存不存在读库）
            unread_redis_key = 'Unread[' + str(msg_sender) + '-to-' + str(msg_receiver) + ']'
            if redis_client.exists(unread_redis_key) == 1:
                # 未读数量 +1
                redis_client.set(unread_redis_key, int(redis_client.get(unread_redis_key)) + 1)
                unread = int(redis_client.get(unread_redis_key))
            else:
                query_sql = 'select * from nsyy_gyl.ws_message_read where type = {} and sender = {} and receiver = {} ' \
                    .format(ws_config.PRIVATE_CHAT, int(msg_sender), int(msg_receiver))
                message_read = db.query_one(query_sql)
                last_read = -1
                if message_read is not None:
                    last_read = message_read.get('last_read')
                else:
                    # 向 message_read 中插入一条记录
                    timer = datetime.now()
                    args = (ws_config.PRIVATE_CHAT, int(msg_sender), int(msg_receiver), -1, timer)
                    insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                                 "VALUES (%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        raise Exception("已读状态入库失败!")

                query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                            'where msg_type = {} and sender = {} and receiver = {} and id > {} ' \
                    .format(ws_config.CHAT_MESSAGE, int(msg_sender), int(msg_receiver), int(last_read))
                unread = db.query_one(query_sql)

                # 更新缓存
                redis_client.set(unread_redis_key, unread.get('count(*)'))

            # TODO socket.push(msg, unread)
            socket_data = {
                "type": 0,
                "data": {
                    "msg": msg,
                    "unread": unread
                }
            }
            push(json.dumps(socket_data, default=str), int(msg_receiver))
            print(f'socket push {msg_receiver}= , {msg}= , {unread}=')

        # 群聊(从缓存中获取)
        else:
            # 先获取群成员信息
            group_member_redis_key = 'GroupMember[' + str(msg_group_id) + ']'
            if redis_client.exists(group_member_redis_key) == 1:
                group_member = redis_client.smembers(group_member_redis_key)
            else:
                query_sql = 'select user_id from nsyy_gyl.ws_group_member ' \
                            'where group_id = {} and state = 1 ' \
                    .format(msg_group_id)
                group_member = db.query_all(query_sql)
                # 更新缓存
                for mem in group_member:
                    redis_client.sadd(group_member_redis_key, mem.get('user_id'))

            # 遍历群成员推送消息
            for member in group_member:
                if type(member) == dict:
                    member_id = member['user_id']
                else:
                    member_id = member

                # 如果群成员就是发送者本身，跳过
                if int(member_id) == int(msg_sender):
                    continue

                # 查询未读数量（先读缓存，缓存不存在读库）
                group_unread_redis_key = 'GroupUnread[' + str(member_id) + '-to-' + str(msg_group_id) + ']'
                if redis_client.exists(group_unread_redis_key) == 1:
                    redis_client.set(group_unread_redis_key, int(redis_client.get(group_unread_redis_key)) + 1)
                    unread = int(redis_client.get(group_unread_redis_key))
                else:
                    # 群成员 member 在群中的未读消息记录
                    query_sql = 'select * from nsyy_gyl.ws_message_read ' \
                                'where type = {} and sender = {} and receiver = {} ' \
                        .format(ws_config.GROUP_CHAT, int(member_id), int(msg_group_id))
                    message_read = db.query_one(query_sql)
                    last_read = -1
                    if message_read is not None:
                        last_read = message_read.get('last_read')
                    else:
                        # 向 message_read 中插入一条记录
                        timer = datetime.now()
                        args = (ws_config.GROUP_CHAT, int(member_id), int(msg_group_id), -1, timer)
                        insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                                     "VALUES (%s,%s,%s,%s,%s)"
                        last_rowid = db.execute(insert_sql, args, need_commit=True)
                        if last_rowid == -1:
                            raise Exception("已读状态入库失败!")

                    query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                                'where msg_type = {} and group_id = {} and id > {} ' \
                        .format(ws_config.CHAT_MESSAGE, int(msg_group_id), int(last_read))
                    unread = db.query_one(query_sql)

                    # 更新缓存
                    redis_client.set(group_unread_redis_key, unread.get('count(*)'))

                # TODO socket.push(msg, unread)
                socket_data = {
                    "type": 0,
                    "data": {
                        "msg": msg,
                        "unread": unread
                    }
                }
                push(json.dumps(socket_data, default=str), int(member_id))
                print(f'socket push {member}= , {msg}= , {unread}=')
    elif msg_type == ws_config.NOTIFICATION_MESSAGE:
        # 向所有用户推送未读消息数量，以及最后一条消息内容
        receivers = str(msg.get('receiver')).split(',')
        for recv in receivers:
            notification_unread_redis_key = 'NotificationUnread[' + str(recv) + ']'
            if redis_client.exists(notification_unread_redis_key) == 1:
                redis_client.set(notification_unread_redis_key,
                                 int(redis_client.get(notification_unread_redis_key)) + 1)
                unread = int(redis_client.get(notification_unread_redis_key))
            else:
                query_sql = 'select * from nsyy_gyl.ws_message_read where type = {} and receiver = {} ' \
                    .format(ws_config.NOTIFICATION_MESSAGE, int(recv))
                message_read = db.query_one(query_sql)
                last_read = -1
                if message_read is not None:
                    last_read = message_read.get('last_read')
                else:
                    # 向 message_read 中插入一条记录
                    timer = datetime.now()
                    args = (ws_config.NOTIFICATION_MESSAGE, int(recv), -1, timer)
                    insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, receiver, last_read, timer) " \
                                 "VALUES (%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        raise Exception("已读状态入库失败!")

                query_sql = 'select count(*) from nsyy_gyl.ws_message where msg_type = {} ' \
                            'and FIND_IN_SET({}, receiver) > 0 and id > {} ' \
                    .format(ws_config.NOTIFICATION_MESSAGE, int(recv), int(last_read))
                unread = db.query_one(query_sql)

                # 更新缓存
                redis_client.set(notification_unread_redis_key, int(unread.get('count(*)')))

            # TODO socket.push(msg, unread)  type 待定
            socket_data = {
                "type": 0,
                "data": {
                    "msg": msg,
                    "unread": unread
                }
            }
            push(json.dumps(socket_data, default=str), int(recv))
            print(f'socket push {recv}= , {msg}= , {unread}=')

    del db


def update_read(type: int, is_group: bool, sender: int, receiver: int, last_read: int):
    """
    处理已读回执，更新已读状态
    :param type:
    :param is_group: 是否是群聊
    :param sender:
    :param receiver:
    :param last_read:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 如果是通知类消息不需要关心发送者，只需要关心接收者
    if type == ws_config.NOTIFICATION_MESSAGE:
        query_sql = 'SELECT * FROM nsyy_gyl.ws_message_read WHERE type = {} AND receiver = {} ' \
            .format(type, receiver)
        existing_record = db.query_one(query_sql)
        if existing_record is not None and existing_record.get('last_read') < last_read:
            # 如果存在记录，则更新
            update_sql = 'UPDATE nsyy_gyl.ws_message_read SET last_read = %s WHERE type = %s AND receiver = %s'
            args = (last_read, type, receiver)
            db.execute(update_sql, args, need_commit=True)
        elif existing_record is None:
            # 如果不存在记录，则插入新纪录
            timer = datetime.now()
            args = (type, sender, receiver, last_read, timer)
            insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                         "VALUES (%s,%s,%s,%s,%s)"
            last_rowid = db.execute(insert_sql, args, need_commit=True)
            if last_rowid == -1:
                raise Exception("已读状态入库失败!")

        # 更新缓存
        query_sql = 'select count(*) from nsyy_gyl.ws_message where msg_type = {} ' \
                    'and FIND_IN_SET({}, receiver) > 0  and id > {} ' \
            .format(ws_config.NOTIFICATION_MESSAGE, int(receiver), int(last_read))
        unread = db.query_one(query_sql)

        notification_unread_redis_key = 'NotificationUnread[' + str(receiver) + ']'
        redis_client.set(notification_unread_redis_key, int(unread.get('count(*)')))

    elif type == ws_config.CHAT_MESSAGE:
        if is_group:
            query_sql = 'SELECT * FROM nsyy_gyl.ws_message_read WHERE type = {} AND sender = {} AND receiver = {} ' \
                .format(ws_config.GROUP_CHAT, sender, receiver)
        else:
            query_sql = 'SELECT * FROM nsyy_gyl.ws_message_read WHERE type = {} AND sender = {} AND receiver = {} ' \
                .format(ws_config.PRIVATE_CHAT, sender, receiver)
        existing_record = db.query_one(query_sql)
        if existing_record is not None and existing_record.get('last_read') < last_read:
            # 如果存在记录，则更新
            update_sql = 'UPDATE nsyy_gyl.ws_message_read SET last_read = %s ' \
                         'WHERE type = %s AND sender = %s AND receiver = %s'
            args = (last_read, type, sender, receiver)
            db.execute(update_sql, args, need_commit=True)
        elif existing_record is None:
            # 如果不存在记录，则插入新纪录
            timer = datetime.now()
            if is_group:
                args = (ws_config.GROUP_CHAT, sender, receiver, last_read, timer)
            else:
                args = (ws_config.PRIVATE_CHAT, sender, receiver, last_read, timer)
            insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                         "VALUES (%s,%s,%s,%s,%s)"
            last_rowid = db.execute(insert_sql, args, need_commit=True)
            if last_rowid == -1:
                raise Exception("已读状态入库失败!")

        # 更新缓存
        if is_group:
            query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                        'where msg_type = {} and group_id = {} and id > {} ' \
                .format(ws_config.CHAT_MESSAGE, int(receiver), int(last_read))
            unread = db.query_one(query_sql)

            # 更新缓存(这里 sender 是接收群消息的人， receiver 是群)
            group_unread_redis_key = 'GroupUnread[' + str(sender) + '-to-' + str(receiver) + ']'
            redis_client.set(group_unread_redis_key, int(unread.get('count(*)')))
        else:
            query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                        'where msg_type = {} and sender = {} and receiver = {} and id > {} ' \
                .format(ws_config.CHAT_MESSAGE, int(sender), int(receiver), int(last_read))
            unread = db.query_one(query_sql)

            # 更新缓存
            unread_redis_key = 'Unread[' + str(sender) + '-to-' + str(receiver) + ']'
            redis_client.set(unread_redis_key, int(unread.get('count(*)')))

    del db


def get_notification_message_list(receiver: int, start: int, count: int):
    """
    读取通知类消息
    :param receiver:
    :param start:  开始 消息id
    :param count:  待读取的消息数量
    :return:
    """

    # 先更新缓存
    move_message_to_redis_cache(ws_config.NOTIFICATION_MESSAGE, None, None, str(receiver))

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 如果 start 在缓存中，从缓存中读取
    msg_redis_key = 'NotificationMessage[' + str(receiver) + ']'
    in_cache = True
    notification_messages = []
    if redis_client.exists(msg_redis_key) == 1:

        if start == -1:
            notification_messages = redis_client.lrange(msg_redis_key, -count, -1)
            for index in range(len(notification_messages)):
                notification_messages[index] = json.loads(notification_messages[index])
        else:
            list_len = redis_client.llen(msg_redis_key)
            first_data_in_redis = redis_client.lrange(msg_redis_key, 0, 0)
            last_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)

            # 将 JSON 对象转换为 Python 字典
            first_data = json.loads(first_data_in_redis[0])
            last_data = json.loads(last_data_in_redis[0])
            first_msg_id = first_data['id']
            last_msg_id = last_data['id']

            if int(first_msg_id) <= start <= int(last_msg_id):
                # Get all elements in the list
                list_elements = redis_client.lrange(msg_redis_key, 0, -1)

                # Iterate over the elements
                for element in list_elements:
                    data = json.loads(element)
                    if int(data['id']) >= start:
                        notification_messages.append(data)
                    if len(notification_messages) >= count:
                        break
            else:
                in_cache = False

    # 缓存中不存在，查库
    if not in_cache:
        query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
                    'WHERE id >= {} AND msg_type = {} AND FIND_IN_SET( {}, receiver) > 0 limit {} ' \
            .format(start, ws_config.NOTIFICATION_MESSAGE, receiver, count)
        notification_messages = db.query_all(query_sql)

    del db

    return notification_messages


def get_chat_list(user_id: int):
    """
    读取群聊列表
    :param user_id:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = 'SELECT * FROM nsyy_gyl.ws_historical_contacts ' \
                'WHERE user_id = {} ' \
                'or group_id in ' \
                '(select group_id from nsyy_gyl.ws_group_member where user_id = {} and state = 1 ) ' \
                'order by last_msg_time desc'\
        .format(user_id, user_id)
    historical_contacts = db.query_all(query_sql)

    chats = []
    # 组装信息，私聊提供发送人姓名，群聊提供群名称
    for contact in historical_contacts:
        if contact.get('chat_type') == ws_config.GROUP_CHAT:
            group_id = int(contact.get('group_id'))
            query_sql = 'SELECT * FROM nsyy_gyl.ws_group ' \
                        'WHERE id = {} '.format(group_id)
            group = db.query_one(query_sql)

            # 查询未读数量
            group_unread_redis_key = 'GroupUnread[' + str(user_id) + '-to-' + str(group_id) + ']'
            if redis_client.exists(group_unread_redis_key) == 1:
                unread = redis_client.get(group_unread_redis_key)
            else:
                query_sql = 'select * from nsyy_gyl.ws_message_read ' \
                            'where type = {} and sender = {} and receiver = {} ' \
                    .format(ws_config.CHAT_MESSAGE, int(user_id), int(group_id))
                message_read = db.query_one(query_sql)
                last_read = -1
                if message_read is not None:
                    last_read = message_read.get('last_read')
                else:
                    # 向 message_read 中插入一条记录
                    timer = datetime.now()
                    args = (ws_config.PRIVATE_CHAT, int(user_id), int(group_id), -1, timer)
                    insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                                 "VALUES (%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        raise Exception("已读状态入库失败!")

                query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                            'where msg_type = {} and group_id = {} and id > {} ' \
                    .format(ws_config.CHAT_MESSAGE, int(group_id), int(last_read))
                unread = db.query_one(query_sql)
                unread = unread.get('count(*)')

                # 更新缓存(这里 sender 是接收群消息的人， receiver 是群)
                group_unread_redis_key = 'GroupUnread[' + str(user_id) + '-to-' + str(group_id) + ']'
                redis_client.set(group_unread_redis_key, int(unread))

            chats.append({
                'id': group_id,
                'name': group.get('group_name'),
                'is_group': True,
                'last_msg': contact.get('last_msg'),
                'last_msg_time': contact.get('last_msg_time'),
                'unread': unread
            })

        else:
            # 查询未读数量
            chat_user_id = contact.get('chat_id')
            unread_redis_key = 'Unread[' + str(chat_user_id) + '-to-' + str(user_id) + ']'
            if redis_client.exists(unread_redis_key) == 1:
                unread = redis_client.get(unread_redis_key)
            else:
                query_sql = 'select * from nsyy_gyl.ws_message_read ' \
                            'where type = {} and sender = {} and receiver = {} ' \
                    .format(ws_config.CHAT_MESSAGE, int(chat_user_id), int(user_id))
                message_read = db.query_one(query_sql)
                last_read = -1
                if message_read is not None:
                    last_read = message_read.get('last_read')
                else:
                    # 向 message_read 中插入一条记录
                    timer = datetime.now()
                    args = (ws_config.PRIVATE_CHAT, int(chat_user_id), int(user_id), -1, timer)
                    insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
                                 "VALUES (%s,%s,%s,%s,%s)"
                    last_rowid = db.execute(insert_sql, args, need_commit=True)
                    if last_rowid == -1:
                        raise Exception("已读状态入库失败!")

                query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
                            'where msg_type = {} and sender = {} and receiver = {} and id > {} ' \
                    .format(ws_config.CHAT_MESSAGE, int(chat_user_id), int(user_id), int(last_read))
                unread = db.query_one(query_sql)
                redis_client.set(unread_redis_key, int(unread.get("count(*)")))

            # TODO 根据 sender 查询用户名， 暂时用随机字符串代替用户名
            chats.append({
                'id': user_id,
                'name': generate_random_string(8),
                'is_group': False,
                'last_msg': contact.get('last_msg'),
                'last_msg_time': contact.get('last_msg_time'),
                'unread': unread
            })

    del db

    return chats


def generate_random_string(length):
    """
    生成长度为 length 的随机字符串
    :param length:
    :return:
    """
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def get_chat_message(cur_user_id: int, chat_user_id: int, group_id: int, start: int, count: int):
    """
    读取群聊消息
    :param cur_user_id:  当前用户是 sender
    :param chat_user_id:  聊天对象是 receiver，如果是群聊 chat_user_id is None
    :param group_id:
    :param start
    :param count
    :return:
    """
    # 先更新缓存
    move_message_to_redis_cache(ws_config.CHAT_MESSAGE, group_id, chat_user_id, str(cur_user_id))

    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    chat_messages = []
    last_read = -1
    if group_id is not None:
        # 群聊
        in_cache = True
        msg_redis_key = 'GroupChat[' + str(group_id) + ']'
        if redis_client.exists(msg_redis_key) == 1:
            if start == -1:
                chat_messages = redis_client.lrange(msg_redis_key, -count, -1)
                for index in range(len(chat_messages)):
                    chat_messages[index] = json.loads(chat_messages[index])
            else:
                list_len = redis_client.llen(msg_redis_key)
                first_data_in_redis = redis_client.lrange(msg_redis_key, 0, 0)
                last_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)

                first_data = json.loads(first_data_in_redis[0])
                last_data = json.loads(last_data_in_redis[0])
                first_msg_id = first_data['id']
                last_msg_id = last_data['id']

                if int(first_msg_id) <= start <= int(last_msg_id):
                    # Get all elements in the list
                    list_elements = redis_client.lrange(msg_redis_key, 0, -1)

                    # Iterate over the elements
                    for element in list_elements:
                        data = json.loads(element)
                        if int(data['id']) >= start:
                            chat_messages.append(data)
                        if len(chat_messages) >= count:
                            break
                else:
                    in_cache = False

        # 缓存不存在，入库查找
        if not in_cache:
            query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
                        'WHERE id >= {} and msg_type = {} AND receiver = {} limit {} ' \
                .format(start, ws_config.CHAT_MESSAGE, group_id, count)
            chat_messages = db.query_all(query_sql)
            del db

        if len(chat_messages) != 0:
            last_read = int(chat_messages[len(chat_messages) - 1].get('id'))
            # 更新群聊已读状态
            update_read(ws_config.CHAT_MESSAGE, True, cur_user_id, group_id, last_read)

    else:
        # 私聊(注意⚠️： 既要查询 A->B 的消息，也要查询 B->A 的消息)
        # 私聊, 保证双方发送的消息用同一个 key
        if chat_user_id <= int(cur_user_id):
            msg_redis_key = 'PrivateChat[' + str(chat_user_id) + '-to-' + str(cur_user_id) + ']'
        else:
            msg_redis_key = 'PrivateChat[' + str(cur_user_id) + '-to-' + str(chat_user_id) + ']'

        in_cache = True
        if redis_client.exists(msg_redis_key) == 1:
            if start == -1:
                chat_messages = redis_client.lrange(msg_redis_key, -count, -1)
                for index in range(len(chat_messages)):
                    chat_messages[index] = json.loads(chat_messages[index])
            else:
                list_len = redis_client.llen(msg_redis_key)
                first_data_in_redis = redis_client.lrange(msg_redis_key, 0, 0)
                last_data_in_redis = redis_client.lrange(msg_redis_key, list_len - 1, list_len - 1)

                first_data = json.loads(first_data_in_redis[0])
                last_data = json.loads(last_data_in_redis[0])
                first_msg_id = first_data['id']
                last_msg_id = last_data['id']

                if int(first_msg_id) <= start <= int(last_msg_id):
                    # Get all elements in the list
                    list_elements = redis_client.lrange(msg_redis_key, 0, -1)

                    # Iterate over the elements
                    for element in list_elements:
                        data = json.loads(element)
                        if int(data['id']) >= start:
                            chat_messages.append(data)
                        if len(chat_messages) >= count:
                            break
                else:
                    in_cache = False

        # 缓存不存在，入库查找
        if not in_cache:
            query_sql = 'select * from nsyy_gyl.ws_message where id >= {} and msg_type = {} ' \
                        'and ((sender = {} and receiver = {} ) or (sender = {} and receiver = {} )) ' \
                .format(start, ws_config.CHAT_MESSAGE, chat_user_id, cur_user_id,
                        cur_user_id, chat_user_id, count)
            chat_messages = db.query_all(query_sql)

        if len(chat_messages) != 0:
            last_read = int(chat_messages[len(chat_messages) - 1].get('id'))
            # 更新私聊已读状态
            update_read(ws_config.CHAT_MESSAGE, False, chat_user_id, cur_user_id, last_read)

    del db
    return chat_messages


def record_historical_contacts(user_id: int, chat_type: int, chat_id: int, last_msg: str, last_msg_time: datetime):
    """
    记录历史联系人
    :param user_id:
    :param chat_type:
    :param chat_id: 群聊时为 group_id
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    if chat_type == ws_config.PRIVATE_CHAT:
        # 私聊
        query_sql = 'select * from nsyy_gyl.ws_historical_contacts ' \
                    'where user_id = {} and chat_type = {} and chat_id = {} '\
            .format(user_id, ws_config.PRIVATE_CHAT, chat_id)
        record = db.query_one(query_sql)
        if record is None:
            # 不存在，插入记录
            args = (user_id, ws_config.PRIVATE_CHAT, chat_id, last_msg, last_msg_time)
            insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts " \
                         "(user_id, chat_type, chat_id, last_msg, last_msg_time)" \
                         " VALUES (%s,%s,%s,%s,%s)"
            last_id = db.execute(insert_sql, args, need_commit=True)
            if last_id == -1:
                raise Exception("历史联系人入库失败!")

            args = (chat_id, ws_config.PRIVATE_CHAT, user_id, last_msg, last_msg_time)
            insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts " \
                         "(user_id, chat_type, chat_id, last_msg, last_msg_time)" \
                         " VALUES (%s,%s,%s,%s,%s)"
            last_id = db.execute(insert_sql, args, need_commit=True)
            if last_id == -1:
                raise Exception("历史联系人入库失败!")
        else:
            # 记录存在，更新
            update_sql = 'UPDATE nsyy_gyl.ws_historical_contacts SET last_msg = %s , last_msg_time = %s' \
                         ' where user_id = %s and chat_type = %s and chat_id = %s'
            args = (last_msg, last_msg_time, user_id, ws_config.PRIVATE_CHAT, chat_id)
            db.execute(update_sql, args, need_commit=True)

            args = (last_msg, last_msg_time, chat_id, ws_config.PRIVATE_CHAT, user_id)
            db.execute(update_sql, args, need_commit=True)

    elif chat_type == ws_config.GROUP_CHAT:
        # 群聊
        query_sql = 'select * from nsyy_gyl.ws_historical_contacts ' \
                    'where chat_type = {} and group_id = {} '\
            .format(ws_config.GROUP_CHAT, chat_id)
        record = db.query_one(query_sql)
        if record is None:
            # 不存在，插入记录
            args = (user_id, ws_config.GROUP_CHAT, chat_id, last_msg, last_msg_time)
            insert_sql = "INSERT INTO nsyy_gyl.ws_historical_contacts " \
                         "(user_id, chat_type, group_id, last_msg, last_msg_time)" \
                         " VALUES (%s,%s,%s,%s,%s)"
            last_id = db.execute(insert_sql, args, need_commit=True)
            if last_id == -1:
                raise Exception("历史联系人入库失败!")

        else:
            # 记录存在，更新
            update_sql = 'UPDATE nsyy_gyl.ws_historical_contacts SET last_msg = %s , last_msg_time = %s' \
                         ' where chat_type = %s and group_id = %s'
            args = (last_msg, last_msg_time, ws_config.GROUP_CHAT, chat_id)
            db.execute(update_sql, args, need_commit=True)

    del db


#  ==========================================================================================
#  ==========================     群组管理      ==============================================
#  ==========================================================================================


def create_group(group_name: str, creator: int, members: str):
    """
    创建群聊
    :param group_name:
    :param creator:
    :param members:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    timer = datetime.now()
    args = (group_name, creator, timer)
    insert_sql = "INSERT INTO nsyy_gyl.ws_group (group_name, creator, timer)" \
                 " VALUES (%s,%s,%s)"
    group_id = db.execute(insert_sql, args, need_commit=True)
    if group_id == -1:
        raise Exception("群组入库失败!")

    members = members.replace(" ", "")
    for member in members.split(','):
        args = (group_id, member, 0, 0, timer)
        insert_sql = "INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, join_type, state, timer)" \
                     " VALUES (%s,%s,%s,%s,%s)"
        db.execute(insert_sql, args, need_commit=True)

    # TODO 向所有成员发生邀请入群通知 用户名需要查询
    group_notification = {
        "context": '[入群邀请] 用户: ' + str(creator) + ' 邀请您加入群聊 ' + group_name,
        "group_info": {
            "group_id": group_id,
            "group_name": group_name,
            "creator": creator
        }
    }

    # 生成通知记录 & socket 推送
    send_notification_message(0, members, json.dumps(group_notification))

    del db


def update_group_name(group_id: int, group_name: str):
    """
    修改群名称
    :param group_id:
    :param group_name:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = "select * from nsyy_gyl.ws_group where id = {} ".format(group_id)
    group = db.query_one(query_sql)
    if group is None:
        raise Exception("不存在群组，请仔细检查")

    update_sql = 'UPDATE nsyy_gyl.ws_group SET group_name = %s WHERE id = %s'
    args = (group_name, group_id)
    db.execute(update_sql, args, need_commit=True)

    del db


def join_group(group_id: id, members: str, join_type: int):
    """
    加入群聊
    :param group_id:
    :param members:
    :param join_type: 0-邀请 1-申请
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = "select * from nsyy_gyl.ws_group where id = {} ".format(group_id)
    group = db.query_one(query_sql)
    if group is None:
        raise Exception("不存在群组，请仔细检查")

    timer = datetime.now()
    members = members.replace(" ", "")
    for member in members.split(','):
        query_sql = "select * from nsyy_gyl.ws_group_member where group_id = {} AND user_id = {} " \
            .format(group_id, member)
        group_member = db.query_one(query_sql)
        if group_member:
            continue

        args = (group_id, member, join_type, 0, timer)
        insert_sql = "INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, join_type, state, timer)" \
                     " VALUES (%s,%s,%s,%s,%s)"
        db.execute(insert_sql, args, need_commit=True)

        # TODO 根据入群方式生成通知然后 socket 推送
        if join_type == ws_config.INVITE_JOIN_GROUP:
            # 邀请人群
            notification_msg = {
                "type": 0,
                "context": '[入群邀请] 用户: ' + str(group.get('creator')) + ' 邀请您加入群聊 ' + group.get('group_name'),
                "group_info": json.dumps(group, default=str)
            }

            # 生成通知记录 & socket 推送
            send_notification_message(0, members, json.dumps(notification_msg, default=str))
        elif join_type == ws_config.APPLY_JOIN_GROUP:
            # 申请入群
            notification_msg = {
                "type": 0,
                "context": '[申请入群] 用户: ' + str(member) + ' 申请加入您的群聊 ' + group.get(
                    'group_name'),
                "group_info": json.dumps(group, default=str)
            }
            # 生成通知记录 & socket 推送
            send_notification_message(0, str(member), json.dumps(notification_msg, default=str))

    del db


def remove_group(group_id: int, members: str):
    """
    移出群聊
    :param group_id:
    :param members:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = "select * from nsyy_gyl.ws_group where id = {} ".format(group_id)
    group = db.query_one(query_sql)
    if group is None:
        raise Exception("不存在群组，请仔细检查")

    group_member_redis_key = 'GroupMember[' + str(group_id) + ']'
    members = members.replace(" ", "")
    for member in members.split(','):
        update_sql = "UPDATE nsyy_gyl.ws_group_member SET state = 2 WHERE group_id = {} AND user_id = {} " \
            .format(group_id, member)
        db.execute(update_sql, need_commit=True)
        # 移出缓存
        if redis_client.exists(group_member_redis_key) == 1:
            redis_client.srem(group_member_redis_key, int(member))

    del db


def confirm_join_group(group_id: int, user_id: int):
    """
    确认加入群聊
    :param group_id:
    :param user_id:
    :return:
    """
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    group_member_redis_key = 'GroupMember[' + str(group_id) + ']'

    query_sql = "select * from nsyy_gyl.ws_group_member where group_id = {} and user_id = {} ".format(group_id, user_id)
    group_member = db.query_one(query_sql)
    if group_member is None:
        raise Exception(f"不存在邀请记录，请仔细检查. {group_member}=")

    update_sql = "UPDATE nsyy_gyl.ws_group_member SET state = 1 WHERE group_id = {} AND user_id = {} " \
        .format(group_id, user_id)
    db.execute(update_sql, need_commit=True)

    # 放入缓存
    redis_client.sadd(group_member_redis_key, user_id)

    del db


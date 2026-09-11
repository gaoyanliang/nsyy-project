import json
import logging
import redis
from datetime import datetime

from gylmodules import global_config, global_tools
from gylmodules.group import group_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.workstation import ws_config
from gylmodules.workstation.message import msg_push_tool

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)
logger = logging.getLogger(__name__)


def flush_msg_cache():
    redis_client = redis.Redis(connection_pool=pool)
    keys = redis_client.keys('MESSAGE*')

    # cache group info
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = 'select group_id from nsyy_gyl.group where group_state = 1'
    all_group = db.query_all(query_sql)
    del db
    for group in all_group:
        redis_client.set(group_config.group_key.format(str(group.get('group_id'))),
                         json.dumps(group, default=str))


def cache_group_member(group_id):
    redis_client = redis.Redis(connection_pool=pool)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f'select user_id from nsyy_gyl.group_member where group_id = {group_id} and state = 1 '
    group_member = db.query_all(query_sql)
    del db

    redis_key = group_config.group_member_ids_key.format(str(group_id))
    for member in group_member:
        redis_client.sadd(redis_key, member.get('user_id'))


#  ==========================================================================================
#  ==========================     消息管理      ==============================================
#  ==========================================================================================


def send_notification_message(context_type: int, sender, sender_name,
                              receiver, receiver_name, context: str):
    # 发送通知消息 📢
    send_message(ws_config.NOTIFICATION_MESSAGE, context_type, sender, sender_name,
                 None, receiver, receiver_name, context)


def batch_send_notification_message(context_type, sender, sender_name, receivers, context: str):
    # 发送通知消息 📢
    receiver = ','.join([item.get('user_id') for item in receivers])
    receiver_name = ','.join([item.get('user_name') for item in receivers])
    if len(receiver_name) > 20:
        # 计算需要保留的完整名字数量
        truncated = receiver_name[:20]
        # 确保不在名字中间截断，找到最后一个逗号位置
        last_comma = truncated.rfind(',')
        if last_comma > 20 * 0.5:  # 至少保留一半
            truncated = truncated[:last_comma] + '...'
        else:
            truncated = truncated + '...'
        receiver_name = truncated

    send_message(ws_config.NOTIFICATION_MESSAGE, context_type, sender, sender_name,
                 None, receiver, receiver_name, context)


"""
发送消息，并通过 socket 通知
消息发送 仅通过 socket 将消息发出去，前端接收到 socket 消息之后，调用手机本地接口，将消息保存到本地
"""


def send_message(chat_type: int, context_type: int, sender, sender_name,
                 group_id: int, receiver, receiver_name, context: str, audio_notification: bool = False):
    # 获取消息 id, 并将消息组装为 json str
    timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if chat_type == ws_config.GROUP_CHAT:
        # 群聊，先验证是否属于群成员
        in_group = is_in_group(group_id, sender)
        if not in_group:
            raise Exception('用户不在群组中, 无法发送消息')

    new_message = {'chat_type': chat_type, 'context_type': context_type, 'sender': sender,
                   'sender_name': sender_name, 'group_id': int(group_id) if group_id else 0,
                   'receiver': receiver if receiver else 0, 'receiver_name': receiver_name,
                   'context': context, 'timer': timer}

    redis_client = redis.Redis(connection_pool=pool)
    # 进 Redis List 缓冲区（用于批量持久化）
    redis_client.rpush(ws_config.msg_cache_key['messages'], json.dumps(new_message, default=str, ensure_ascii=False))

    # 插入数据库时需要压缩，socket推送时需要解压
    if chat_type == ws_config.NOTIFICATION_MESSAGE:
        new_message['context'] = json.loads(new_message.get('context'))

    # 通过 socket 向接收者推送通知
    global_tools.start_thread(socket_push, (new_message, audio_notification))
    # socket_push(new_message)


"""
通过 socket 向用户推送通知, 同时更新未读消息未读数量（缓存数量加一）
"""


def socket_push(msg: dict, audio_notification: bool = False):
    redis_client = redis.Redis(connection_pool=pool)
    chat_type = msg.get('chat_type')
    if chat_type == ws_config.PRIVATE_CHAT:
        # 私聊
        msg_receiver, msg_sender = msg.get('receiver'), msg.get('sender')
        global_tools.socket_push("私聊消息推送", {"socketd": ["m_app", "m_user"], "type": 100,
                                                  'pers_id': [msg_receiver],
                                                  'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                  "socket_data": msg})
        global_tools.start_thread(msg_push_tool.push_msg_to_devices, ([msg_receiver], "新消息来咯", f"{msg.get('sender_name')} 发来一条消息", audio_notification))
        # 推送给发送者 逻辑统一 将消息保存至本地
        global_tools.socket_push("私聊消息推送", {"socketd": ["m_app"], "type": 100,
                                                  'pers_id': [msg_sender],
                                                  'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                  "socket_data": msg})

    elif chat_type == ws_config.GROUP_CHAT:
        # 向所有用户推送未读消息数量，以及最后一条消息内容
        msg_group_id, msg_sender = msg.get('group_id'), msg.get('sender')
        group_member_redis_key = group_config.group_member_ids_key.format(str(msg_group_id))
        if not redis_client.exists(group_member_redis_key):
            cache_group_member(msg_group_id)

        group_member = redis_client.smembers(group_member_redis_key)
        group_member = list(group_member)
        group_member = [int(item) for item in group_member]
        # 遍历群成员推送消息
        global_tools.socket_push("群聊消息推送", {"socketd": ["m_app", "m_user"], "type": 100,
                                                  'pers_id': group_member,
                                                  'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                  "socket_data": msg})
        for member in group_member:
            global_tools.start_thread(msg_push_tool.push_msg_to_devices, ([member], "新消息来咯",
                                                                          f" {msg.get('receiver_name')} 收到群聊消息", audio_notification))

    elif chat_type == ws_config.NOTIFICATION_MESSAGE:
        # 向所有用户推送未读消息数量，以及最后一条消息内容
        receivers = str(msg.get('receiver')).split(',')
        names = str(msg.get('receiver_name')).split(',')
        index = 0
        for recv in receivers:
            msg['receiver'] = int(recv)
            msg['receiver_name'] = names[index]
            index = index + 1
            global_tools.socket_push("通知消息推送", {"socketd": ["m_app", "m_user"], "type": 400,
                                                      'pers_id': [recv],
                                                      'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                      "socket_data": msg})

        global_tools.start_thread(msg_push_tool.push_msg_to_devices, (receivers, "新消息来咯",
                                                                      f"接收到来自 {msg.get('sender_name')} 的通知消息", audio_notification))


"""后台线程：定时从 Redis 拉消息批量写 MySQL"""

def batch_flush_worker(batch_size=100):
    try:
        redis_client = redis.Redis(connection_pool=pool)
        key = ws_config.msg_cache_key['messages']

        # —— 1. 批量 pop（兼容所有 Redis 版本） ——
        pipe = redis_client.pipeline()
        for _ in range(batch_size):
            pipe.lpop(key)
        raw_messages = [item for item in pipe.execute() if item]
        if not raw_messages:
            return

        # —— 2. 解析 JSON ——
        messages = []
        for item in raw_messages:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            messages.append(json.loads(item))

        # —— 3. 批量插入 MySQL ——
        values_list = []
        for msg in messages:
            row = (
                msg.get('chat_type'),
                msg.get('context_type', 0),
                msg.get('sender', ""),
                msg.get('sender_name', ''),
                msg.get('group_id', 0),
                msg.get('receiver'),
                msg.get('receiver_name', ''),
                msg.get('context', ''),
                msg.get('timer') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            values_list.append(row)

        insert_sql = """INSERT INTO nsyy_gyl.ws_message (chat_type, context_type, sender, sender_name, group_id,
                receiver, receiver_name, context, timer) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        try:
            db.execute_many(insert_sql, values_list, need_commit=True)
            logger.debug(f"批量插入成功：{len(messages)} 条消息")

        except Exception as e:
            logger.error(f"批量插入失败，消息已重新入队: {e}")

            # —— 回滚到 Redis（顺序保证一致） ——
            pipe = redis_client.pipeline()
            for msg in reversed(messages):
                pipe.lpush(key, json.dumps(msg, default=str, ensure_ascii=False))
            pipe.execute()

        finally:
            del db

    except Exception as e:
        logger.error(f"刷库任务异常: {e}")


#  ==========================================================================================
#  ==========================     群组管理      ==============================================
#  ==========================================================================================


# def create_group(group_name: str, creator: int, creator_name: str, members):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     redis_client = redis.Redis(connection_pool=pool)
#
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     args = (group_name, creator, creator_name, timer)
#     insert_sql = "INSERT INTO nsyy_gyl.ws_group (group_name, creator, creator_name, timer)" \
#                  " VALUES (%s,%s,%s,%s)"
#     group_id = db.execute(insert_sql, args, need_commit=True)
#     if group_id == -1:
#         del db
#         raise Exception(f"群组 {group_name} 创建失败!")
#
#     redis_client.set(group_config.group_key.format(str(group_id)), json.dumps({
#         "id": group_id, "group_name": group_name, "creator": creator, "creator_name": creator_name, "timer": timer
#     }, default=str))
#
#     # 将创建者本身放入缓存
#     group_member_redis_key = group_config.group_member_ids_key.format(str(group_id))
#     redis_client.sadd(group_member_redis_key, int(creator))
#
#     values = []
#     values.append((group_id, int(creator), creator_name, 0, 1, timer))
#     for member in members:
#         if int(member.get('user_id')) != int(creator):
#             values.append((group_id, int(member.get('user_id')), member.get('user_name'), 0, 0, timer))
#
#     insert_sql = """INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, user_name, join_type, state, timer)
#                 VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE state = VALUES(state),
#                 is_reply = VALUES(is_reply)"""
#     db.execute_many(insert_sql, args=values, need_commit=True)
#     del db
#
#     group_notification = {"type": 110, "title": "入群邀请",
#                           "description": "用户: " + creator_name + " 邀请您加入群聊 " + group_name,
#                           "time": timer, "group_info": {
#                                           "group_id": group_id,
#                                           "group_name": group_name,
#                                           "creator": creator
#                                       }
#                           }
#
#     # 生成通知记录 & socket 推送， 使用列表推导式提取 "user_id" 值
#     user_ids = [int(m["user_id"]) for m in members]
#     for user_id in user_ids:
#         if int(user_id) == int(creator):
#             continue
#         send_notification_message(ws_config.NOTIFICATION_MESSAGE, creator, creator_name,
#                                   user_id, "", json.dumps(group_notification, default=str))
#
#     # 创建者发送一条消息，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
#     send_message(ws_config.GROUP_CHAT, 0, int(creator), creator_name, int(group_id), int(group_id), group_name,
#                  f"{creator_name} 创建了群聊 {group_name}")
#
#     return {"group_id": group_id, "group_name": group_name}
#
#
# def update_group(group_id: int, group_name: str, members):
#     """
#     更新群聊
#     前端做校验，仅群主可以编辑
#     :param group_id:
#     :param group_name:
#     :param members:
#     :return:
#     """
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     redis_client = redis.Redis(connection_pool=pool)
#     group = db.query_one(f"select * from nsyy_gyl.ws_group where id = {group_id} ")
#     if group is None:
#         del db
#         raise Exception("不存在群组，请仔细检查")
#
#     if group_name is not None:
#         update_sql = f"UPDATE nsyy_gyl.ws_group SET group_name = '{group_name}' WHERE id = {group_id}"
#         db.execute(update_sql, need_commit=True)
#         group['group_name'] = group_name
#         redis_client.set(group_config.group_key.format(str(group_id)), json.dumps(group, default=str))
#
#     values = []
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     for member in members:
#         if member.get('status') == 0:
#             # 新增群成员
#             values.append((group_id, member.get('user_id'), member.get('user_name'), 0, 0, timer))
#
#             # 邀请人群
#             send_notification_message(ws_config.NOTIFICATION_MESSAGE,
#                                       int(group.get('creator')),
#                                       group.get('creator_name'),
#                                       member.get('user_id'),
#                                       member.get('user_name'),
#                                       json.dumps({
#                                           "type": 110, "title": "入群邀请", "time": timer,
#                                           "description": "用户: " + group.get(
#                                               'creator_name') + " 邀请您加入群聊 " + group.get('group_name'),
#                                           "group_info": {
#                                               "group_id": group_id,
#                                               "group_name": group.get('creator_name'),
#                                               "creator": int(group.get('creator'))
#                                           }
#                                       }, default=str))
#
#         elif member.get('status') == 2:
#             # 移除群成员
#             values.append((group_id, member.get('user_id'), member.get('user_name'), 0, 2, timer))
#
#             # 移出缓存
#             group_member_redis_key = group_config.group_member_ids_key.format(str(group_id))
#             if redis_client.exists(group_member_redis_key) == 1:
#                 redis_client.srem(group_member_redis_key, int(member.get('user_id')))
#
#     insert_sql = """INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, user_name, join_type, state, timer)
#                 VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE state = VALUES(state),
#                 is_reply = VALUES(is_reply)"""
#     db.execute_many(insert_sql, args=values, need_commit=True)
#     del db
#
#
# def query_group(group_id: int):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     group = db.query_one(f"select * from nsyy_gyl.ws_group where id = {group_id} ")
#     if group is None:
#         del db
#         raise Exception('群聊不存在')
#
#     query_sql = f"select user_id, user_name from nsyy_gyl.ws_group_member where group_id = {group_id} and state = 1"
#     members = db.query_all(query_sql)
#     del db
#
#     group["member"] = members
#     return group
#
#
# def query_groups(user_id: int):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     groups = db.query_all(f"select * from nsyy_gyl.ws_group where id "
#                          f"in (select group_id from nsyy_gyl.ws_group_member where user_id = {user_id} and state = 1)")
#     del db
#     return groups
#
#
# def confirm_join_group(group_id: int, group_name: str, user_id: int, user_name: str, confirm: int):
#     """
#     确认加入群聊
#     :param confirm: 1 同意 3 拒绝
#     :return:
#     """
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     query_sql = f"select * from nsyy_gyl.ws_group_member where group_id = {group_id} and user_id = {user_id} "
#     group_member = db.query_one(query_sql)
#     if group_member is None:
#         del db
#         raise Exception("不存在邀请记录，请仔细检查. ")
#     if int(group_member.get('is_reply')) == 1:
#         del db
#         raise Exception("邀请记录已响应，请勿重复操作")
#
#     update_sql = f"UPDATE nsyy_gyl.ws_group_member SET state = {confirm}, is_reply = 1, " \
#                  f"update_time = '{timer}'  WHERE group_id = {group_id} AND user_id = {user_id} "
#     db.execute(update_sql, need_commit=True)
#     del db
#
#     # 放入缓存
#     if confirm == 1:
#         group_member_redis_key = group_config.group_member_ids_key.format(str(group_id))
#         redis_client = redis.Redis(connection_pool=pool)
#         redis_client.sadd(group_member_redis_key, int(user_id))
#
#         # 给创建者也发送一个通知，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
#         send_message(ws_config.GROUP_CHAT, 0, int(user_id), user_name, int(group_id), int(group_id), group_name,
#                      f"{user_name} 加入了群聊 {group_name}")


def is_in_group(group_id: int, user_id):
    redis_client = redis.Redis(connection_pool=pool)
    return redis_client.sismember(group_config.group_member_ids_key.format(group_id), str(user_id))


def save_phone_info(phone_info):
    """
    保存用户手机信息
    :param phone_info:
    :return:
    """
    logger.debug(f"保存设备token {phone_info}")
    pers_id = phone_info.get("pers_id")
    device_token = phone_info.get("device_token")
    brand = phone_info.get("brand")
    online = phone_info.get("online", 1)
    if brand:
        brand = brand.upper()
    if not pers_id or not device_token or not brand:
        return

    insert_sql = """INSERT INTO nsyy_gyl.app_token_info (pers_id, device_token, brand, online) 
                VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE pers_id = VALUES(pers_id), 
                device_token = VALUES(device_token), brand = VALUES(brand), online = VALUES(online), 
                update_time = CURRENT_TIMESTAMP"""
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute(insert_sql, args=(pers_id, device_token, brand, online), need_commit=True)
    del db


#  ==========================================================================================
#  ==========================     患者管理      ==============================================
#  ==========================================================================================


# 关注医生
# 关注医生时，需要和医生/医护建小群， 同时将患者加入大群（所有关注该医生的患者）


def follow_doctor(patient_pers_id, patient_name: str, doctor_pers_id, doctor_name: str):
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=60 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(group_config.create_key.format(patient_pers_id), 1, ex=10, nx=True):
        raise Exception('系统繁忙：请勿频繁关注，请于1分钟后再次尝试')

    # 首先判断之前是否关注过
    unique_id = generate_unique_id(patient_pers_id, doctor_pers_id)
    cur_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    sql = f"""SELECT * from nsyy_gyl.group where group_type = 2 and group_type_id = '{unique_id}'"""
    target_group = db.query_one(sql)

    if target_group:
        # 已经关注过该医生 说明群存在 修改状态即可
        # 重置医患关系群
        update_sql = f"""UPDATE nsyy_gyl.group SET group_state = 1, updated_at = '{cur_date}' 
        where group_id = {target_group.get('group_id')}"""
        db.execute(update_sql, need_commit=True)
        update_sql = f"""UPDATE nsyy_gyl.group_member SET state = 1, updated_at = '{cur_date}' 
        where group_id = {target_group.get('group_id')}"""
        db.execute(update_sql, need_commit=True)
        # 重置医生大群
        update_sql = f"""UPDATE nsyy_gyl.group_member SET state = 1, updated_at = '{cur_date}' 
                where user_id = '{patient_pers_id}' and group_id = (select group_id from nsyy_gyl.group 
                where group_type = 2 and group_type_id = '{doctor_pers_id}')"""
        db.execute(update_sql, need_commit=True)
    else:
        # 之前没有关注过该医生
        # 创建医患关系群
        group_name = f"{doctor_name}医生-{patient_name}专属沟通群"
        insert_sql = """INSERT INTO nsyy_gyl.group (group_name, owner_id, owner_name, created_at, updated_at, 
                    description, is_public, mail_account_state, group_state, group_type, group_type_id, follower_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """
        group_id = db.execute(insert_sql, args=(group_name,
                                                patient_pers_id, patient_name, cur_date, cur_date,
                                                f"本群为 {doctor_name} 医生 与 {patient_name} 的专属一对一沟通群，仅限双方及必要医护成员。",
                                                0, 1, 1, 2, unique_id, doctor_pers_id), need_commit=True)
        # 将医生/助手/患者加入群聊
        insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, join_type, state, is_reply, 
                        allow_edit, created_at, updated_at, mail_state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ON DUPLICATE KEY UPDATE state = VALUES(state), updated_at = VALUES(updated_at), 
                        is_reply = VALUES(is_reply), allow_edit = VALUES(allow_edit)"""
        # TODO 将医生助手加入群
        args = [(group_id, patient_pers_id, patient_name, 0, 1, 1, 2, cur_date, cur_date, 1),
                (group_id, doctor_pers_id, doctor_name, 0, 1, 1, 1, cur_date, cur_date, 1)]
        db.execute_many(insert_sql, args=args, need_commit=True)

        # 加入聊天群
        group_member_redis_key = group_config.group_member_ids_key.format(group_id)
        redis_client = redis.Redis(connection_pool=pool)
        redis_client.sadd(group_member_redis_key, str(patient_pers_id))
        redis_client.sadd(group_member_redis_key, str(doctor_pers_id))

        # 创建者发送一条消息，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
        send_message(ws_config.GROUP_CHAT, 0, doctor_pers_id, doctor_name, int(group_id), int(group_id), group_name,
                     f"{patient_name} 关注了 {doctor_name} 医生")

        # 将患者加入医生粉丝群
        query_sql = f"select group_id from nsyy_gyl.group where group_type = 2 and group_type_id = '{doctor_pers_id}'"
        doctor_group = db.query_one(query_sql)
        if not doctor_group:
            group_name = f"{doctor_name}医生 患者交流群"
            insert_sql = """INSERT INTO nsyy_gyl.group (group_name, owner_id, owner_name, created_at, updated_at, 
                    description, is_public, mail_account_state, group_state, group_type, group_type_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """
            group_id = db.execute(insert_sql, args=(group_name, doctor_pers_id, doctor_name,
                                                    cur_date, cur_date, f"本群为 {doctor_name} 医生 患者沟通群",
                                                    0, 1, 1, 2, doctor_pers_id), need_commit=True)

            insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, join_type, state, is_reply, 
                            allow_edit, created_at, updated_at, mail_state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                            ON DUPLICATE KEY UPDATE state = VALUES(state), updated_at = VALUES(updated_at), 
                            is_reply = VALUES(is_reply), allow_edit = VALUES(allow_edit)"""
            # TODO 将医生助手加入群
            args = (group_id, doctor_pers_id, doctor_name, 0, 1, 1, 2, cur_date, cur_date, 1)
            db.execute(insert_sql, args=args, need_commit=True)

            # 加入聊天群
            group_member_redis_key = group_config.group_member_ids_key.format(group_id)
            redis_client = redis.Redis(connection_pool=pool)
            redis_client.sadd(group_member_redis_key, str(patient_pers_id))
            redis_client.sadd(group_member_redis_key, str(doctor_pers_id))

            # 创建者发送一条消息，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
            send_message(ws_config.GROUP_CHAT, 0, doctor_pers_id, doctor_name, int(group_id), int(group_id), group_name,
                         f"{patient_name} 关注了 {doctor_name} 医生")
        else:
            group_id = doctor_group.get("group_id")

        insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, join_type, state, is_reply, 
                        allow_edit, created_at, updated_at, mail_state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ON DUPLICATE KEY UPDATE state = VALUES(state), updated_at = VALUES(updated_at), 
                        is_reply = VALUES(is_reply), allow_edit = VALUES(allow_edit)"""
        args = (group_id, patient_pers_id, patient_name, 0, 1, 1, 0, cur_date, cur_date, 1)
        db.execute(insert_sql, args=args, need_commit=True)

    del db

# 生成医患关系的唯一标识

def generate_unique_id(patient_pers_id, doctor_pers_id, length: int = 12) -> str:
    import hashlib
    import base64
    combined = f"{patient_pers_id}_{doctor_pers_id}"
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).digest()
    short_hash = base64.urlsafe_b64encode(hash_bytes).decode('utf-8').rstrip('=')
    return f"dp_{short_hash[:length]}"


"""
取消关注医生
取消关注后 关闭医患一对一群聊，同时患者退出医生粉丝群
"""
def unfollow_doctor(patient_pers_id, doctor_pers_id):
    # 首先判断之前是否关注过
    unique_id = generate_unique_id(patient_pers_id, doctor_pers_id)
    cur_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    sql = f"""SELECT * from nsyy_gyl.group where group_type = 2 and group_type_id = '{unique_id}'"""
    target_group = db.query_one(sql)
    if target_group:
        update_sql = """update nsyy_gyl.group_member set state = 2, updated_at = %s where group_id = %s"""
        db.execute(update_sql, args=(cur_date, target_group.get("group_id")), need_commit=True)
        update_sql = """update nsyy_gyl.group set group_state = 0, updated_at = %s where group_id = %s"""
        db.execute(update_sql, args=(cur_date, target_group.get("group_id")), need_commit=True)

    query_sql = f"select group_id from nsyy_gyl.group where group_type = 2 and group_type_id = '{doctor_pers_id}'"
    doctor_group = db.query_one(query_sql)
    if doctor_group:
        update_sql = """update nsyy_gyl.group_member set state = 2, updated_at = %s where group_id = %s"""
        db.execute(update_sql, args=(cur_date, doctor_group.get("group_id")), need_commit=True)

    del db


"""查询患者的关注群列表 （包含一对一群聊 和 医生大群）"""

def query_follow_list(patient_pers_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    sql = f"""select * from (select g.*,c.context,row_number() 
            over (partition by gm.group_id order by c.timer desc) as rk
            from nsyy_gyl.group g join nsyy_gyl.group_member gm on
            g.group_id = gm.group_id left join nsyy_gyl.ws_message c on g.group_id = c.group_id
            where gm.user_id = '{patient_pers_id}' and g.group_state = 1 and gm.state = 1) vv where vv.rk=1"""
    follow_list = db.query_all(sql)
    del db
    return follow_list


def patient_msg_query(group_id, start: int = -1, count: int = 10, keyword: str = None, start_time_str: str = None, end_time_str: str = None):
    # 患者消息查询 因为只有群聊，仅传 group id 就可以了
    query_condition = ""
    if keyword:
        query_condition += f" and context like '%{keyword}%' "
    if start_time_str and end_time_str:
        query_condition += f" and timer >= '{start_time_str}' and timer <= '{end_time_str}' "
    if start != -1:
        query_condition += f" and id < {start} "

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""select * from nsyy_gyl.ws_message where group_id = {group_id} {query_condition} order by id desc limit {count}"""
    msgs = db.query_all(query_sql)
    del db
    return msgs










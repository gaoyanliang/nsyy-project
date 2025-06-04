# import json
# import redis
# import threading
# import requests
# from datetime import datetime
#
# from gylmodules import global_config
# from gylmodules.utils.db_utils import DbUtil
# from gylmodules.workstation import ws_config
# from gylmodules.workstation.schedule_task import write_data_to_db
#
# pool = redis.ConnectionPool(host=ws_config.REDIS_HOST, port=ws_config.REDIS_PORT,
#                             db=ws_config.REDIS_DB, decode_responses=True)
#
# # 消息id 初始为 0, 为 0 时，从数据库查询最新消息的id 进行更新, 不为 0 时，自增
# message_id = 0
# message_id_lock = threading.Lock()
#
#
# def get_message_id():
#     global message_id
#
#     with message_id_lock:
#         if message_id == 0:
#             print(datetime.now(), '当前 id 为： ' + str(message_id))
#             db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                         global_config.DB_DATABASE_GYL)
#             query_sql = 'select id from nsyy_gyl.ws_message order by id desc limit 1'
#             id = db.query_one(query_sql)
#             del db
#
#             if id is not None:
#                 message_id = int(id.get('id'))
#             print(datetime.now(), "初始化 message id 为： " + str(message_id))
#
#         # Increment the ID and return the new value
#         message_id += 1
#         next_id = message_id
#         return next_id
#
#
# def flush_msg_cache():
#     redis_client = redis.Redis(connection_pool=pool)
#     keys = redis_client.keys('MSG_*')
#     for key in keys:
#         if key == "MSG_NEW-MESSAGE" or key == "MSG_NEW-HISTORICAL-CONTACTS-RECORD":
#             continue
#         redis_client.delete(key)
#
#     # cache group info
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = 'select * from nsyy_gyl.ws_group'
#     all_group = db.query_all(query_sql)
#     del db
#     for group in all_group:
#         redis_client.set(ws_config.msg_cache_key['group_info'].format(str(group.get('id'))), json.dumps(group, default=str))
#
#     write_data_to_db()
#
#
# # 项目启动刷新消息缓存
# # flush_msg_cache()
#
#
# # 测试环境：
# # 192.168.124.53:6080/inter_socket_msg
# # json格式
# # msg_list: [{socket_data: {}, pers_id: 123,}]
#
# # 正式环境：
# # from tools import socket_send
# # socket_send(socket_data, 'm_user', pers_id)
#
# # 消息推送 type = 100
# def push(socket_data: dict, user_id: int):
#     # print('向用户 ' + str(user_id) + ' 推送消息: ' + json.dumps(socket_data, default=str))
#
#     data = {'msg_list': [{'socket_data': socket_data, 'pers_id': user_id}]}
#     # data = {'msg_list': [{'socket_data': socket_data, 'pers_id': user_id, 'socketd': 'w_site'}]}
#     # 设置请求头
#     headers = {'Content-Type': 'application/json'}
#     # 发送POST请求
#     response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
#     # 打印响应内容
#     # print("Socket Push Status: ", response.status_code)
#     # print("Socket Push Response: ", response.text)
#
#
# #  ==========================================================================================
# #  ==========================     消息管理      ==============================================
# #  ==========================================================================================
#
#
# def send_notification_message(context_type: int, sender: int, sender_name: str,
#                               receiver: str, context: str):
#     # 发送通知消息 📢
#     send_message(ws_config.NOTIFICATION_MESSAGE, context_type, sender, sender_name,
#                  None, receiver, None, context)
#
#
# """
# redis 缓存中只保存最新的 100 条消息
# """
#
#
# def ltrim_100(redis_key):
#     redis_client = redis.Redis(connection_pool=pool)
#     list_len = redis_client.llen(redis_key)
#     if list_len > ws_config.msg_cache_count:
#         redis_client.ltrim(redis_key, 0, list_len - ws_config.msg_cache_count + 1)
#
#
# def cache_msg(chat_type: int, redis_key, cur_user_id: int, chat_user_id: int):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     if chat_type == ws_config.NOTIFICATION_MESSAGE:
#         query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
#                     'and FIND_IN_SET( {}, receiver) > 0 ' \
#                     'order by id desc limit {} ' \
#             .format(ws_config.NOTIFICATION_MESSAGE, str(cur_user_id), ws_config.msg_cache_count)
#         msg_list = db.query_all(query_sql)
#     elif chat_type == ws_config.PRIVATE_CHAT:
#         query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
#                     'and (sender in {} and receiver in {} )' \
#                     'order by id desc limit {} ' \
#             .format(ws_config.PRIVATE_CHAT, (int(cur_user_id), int(chat_user_id)),
#                     (int(chat_user_id), int(cur_user_id)), ws_config.msg_cache_count)
#         msg_list = db.query_all(query_sql)
#     elif chat_type == ws_config.GROUP_CHAT:
#         query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
#                     'and group_id = {} ' \
#                     'order by id desc limit {} ' \
#             .format(ws_config.GROUP_CHAT, int(chat_user_id), ws_config.msg_cache_count)
#         msg_list = db.query_all(query_sql)
#     else:
#         msg_list = []
#
#     del db
#
#     if msg_list is not None:
#         for m in reversed(msg_list):
#             redis_client.rpush(redis_key, json.dumps(m, default=str))
#
#
# def cache_hist_contacts(user_id):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = 'select * from nsyy_gyl.ws_historical_contacts where user_id = {}'.format(int(user_id))
#     contacts = db.query_all(query_sql)
#     del db
#
#     for c in contacts:
#         if int(c.get('chat_type')) == ws_config.PRIVATE_CHAT:
#             redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(c.get('user_id')))
#             redis_hash_key = 'Private[' + str(c.get('user_id')) + '-' + str(c.get('chat_id')) + ']'
#             redis_client.hset(redis_key, redis_hash_key, json.dumps(c, default=str))
#         elif int(c.get('chat_type')) == ws_config.GROUP_CHAT:
#             redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(c.get('user_id')))
#             redis_hash_key = 'Group[' + str(c.get('group_id')) + ']'
#             redis_client.hset(redis_key, redis_hash_key, json.dumps(c, default=str))
#         elif int(c.get('chat_type')) == ws_config.NOTIFICATION_MESSAGE:
#             redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(c.get('user_id')))
#             redis_hash_key = 'Notification'
#             redis_client.hset(redis_key, redis_hash_key, json.dumps(c, default=str))
#
#
# def cache_group_member(group_id):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = 'select user_id, user_name from nsyy_gyl.ws_group_member ' \
#                 'where group_id = {} and state = 1 ' \
#         .format(int(group_id))
#     group_member = db.query_all(query_sql)
#     del db
#
#     redis_key = ws_config.msg_cache_key['group_member'].format(str(group_id))
#     for member in group_member:
#         redis_client.sadd(redis_key, int(member.get('user_id')))
#
#
# """
# 发送消息，并通过 socket 通知
# """
#
#
# def send_message(chat_type: int, context_type: int, sender: int, sender_name: str,
#                  group_id: int, receiver: str, receiver_name: str, context: str):
#     # 1. 获取消息 id, 并将消息组装为 json str
#     new_message_id = get_message_id()
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
#     if chat_type == ws_config.GROUP_CHAT:
#         # 群聊，先验证是否属于群成员
#         in_group = is_in_group(group_id, sender)
#         if not in_group:
#             raise Exception('用户不在群组中, 无法发送消息')
#
#     new_message = {
#         'id': new_message_id,
#         'chat_type': chat_type,
#         'context_type': context_type,
#         'sender': sender,
#         'sender_name': sender_name,
#         'group_id': group_id,
#         'receiver': receiver,
#         'receiver_name': receiver_name,
#         'context': context,
#         'timer': timer
#     }
#
#     # 2. 将最新消息缓存到 redis
#     redis_client = redis.Redis(connection_pool=pool)
#     redis_client.rpush(ws_config.NEW_MESSAGE, json.dumps(new_message, default=str))
#
#     if chat_type == ws_config.NOTIFICATION_MESSAGE:
#         # 📢 通知消息
#         receivers = receiver.split(',')
#         for recv in receivers:
#             if int(recv) != int(sender):
#                 msg_redis_key = ws_config.msg_cache_key['notification_msg'].format(str(recv))
#                 redis_client.rpush(msg_redis_key, json.dumps(new_message, default=str))
#                 ltrim_100(msg_redis_key)
#     elif chat_type == ws_config.PRIVATE_CHAT:
#         # 私聊, 保证双方发送的消息用同一个 key
#         msg_redis_key = ws_config.msg_cache_key['private_msg'].format(str(receiver) + '-to-' + str(sender))
#         if sender <= int(receiver):
#             msg_redis_key = ws_config.msg_cache_key['private_msg'].format(str(sender) + '-to-' + str(receiver))
#         redis_client.rpush(msg_redis_key, json.dumps(new_message, default=str))
#         ltrim_100(msg_redis_key)
#     elif chat_type == ws_config.GROUP_CHAT:
#         msg_redis_key = ws_config.msg_cache_key['group_msg'].format(str(group_id))
#         redis_client.rpush(msg_redis_key, json.dumps(new_message, default=str))
#         ltrim_100(msg_redis_key)
#
#     # 3. 记录历史联系人 私聊群聊 context 是一句话， 通知 context 是json结构
#     if chat_type == ws_config.PRIVATE_CHAT:
#         cache_historical_contacts(sender, sender_name, ws_config.PRIVATE_CHAT, receiver, receiver_name,
#                                   new_message_id, context, timer)
#     elif chat_type == ws_config.GROUP_CHAT:
#         cache_historical_contacts(sender, sender_name, ws_config.GROUP_CHAT, group_id, receiver_name,
#                                       new_message_id, context, timer)
#     elif chat_type == ws_config.NOTIFICATION_MESSAGE:
#         cache_historical_contacts(sender, sender_name, ws_config.NOTIFICATION_MESSAGE, receiver, None,
#                                   new_message_id, context, timer)
#
#     # 4. 通过 socket 向接收者推送通知
#     if chat_type == ws_config.NOTIFICATION_MESSAGE:
#         new_message['context'] = json.loads(new_message.get('context'))
#     socket_push(new_message)
#
#     return new_message_id
#
#
# """
# 记录历史联系人
# """
#
#
# def cache_historical_contacts(sender: int, sender_name: str, chat_type: int, receiver: str,
#                               receiver_name: str, last_msg_id: int, last_msg: str, last_msg_time):
#     redis_client = redis.Redis(connection_pool=pool)
#
#     if not redis_client.exists(ws_config.msg_cache_key['hist_contacts'].format(str(sender))):
#         cache_hist_contacts(int(sender))
#
#     if chat_type == ws_config.PRIVATE_CHAT:
#         if not redis_client.exists(ws_config.msg_cache_key['hist_contacts'].format(str(receiver))):
#             cache_hist_contacts(int(receiver))
#
#         # 私聊
#         historical_contacts = {
#             'user_id': sender,
#             'user_name': sender_name,
#             'chat_type': chat_type,
#             'chat_id': int(receiver),
#             'chat_name': receiver_name,
#             'last_msg_id': last_msg_id,
#             'last_msg': last_msg,
#             'last_msg_time': last_msg_time
#         }
#         redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(sender))
#         redis_hash_key = 'Private[' + str(sender) + '-' + str(receiver) + ']'
#         redis_client.hset(redis_key, redis_hash_key, json.dumps(historical_contacts, default=str))
#         redis_client.rpush(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, json.dumps(historical_contacts, default=str))
#
#         # receiver 和 sender 互换
#         historical_contacts['user_id'], historical_contacts['user_name'], historical_contacts['chat_id'], \
#             historical_contacts['chat_name'] = int(receiver), receiver_name, sender, sender_name
#         redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(receiver))
#         redis_hash_key = 'Private[' + str(receiver) + '-' + str(sender) + ']'
#         redis_client.hset(redis_key, redis_hash_key, json.dumps(historical_contacts, default=str))
#         redis_client.rpush(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, json.dumps(historical_contacts, default=str))
#
#     elif chat_type == ws_config.GROUP_CHAT:
#         # 群聊
#         historical_contacts = {
#             'user_id': sender,
#             'user_name': sender_name,
#             'chat_type': chat_type,
#             'group_id': int(receiver),
#             'chat_id': int(receiver),
#             'chat_name': receiver_name,
#             'last_msg_id': last_msg_id,
#             'last_msg': last_msg,
#             'last_msg_time': last_msg_time
#         }
#         redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(sender))
#         redis_hash_key = 'Group[' + str(receiver) + ']'
#         redis_client.hset(redis_key, redis_hash_key, json.dumps(historical_contacts, default=str))
#         redis_client.rpush(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, json.dumps(historical_contacts, default=str))
#
#         # 遍历群成员，更新群成员的历史联系人(最后一条消息)
#         group_member_redis_key = ws_config.msg_cache_key['group_member'].format(str(receiver))
#         if redis_client.exists(group_member_redis_key) == 1:
#             all_elements = redis_client.smembers(group_member_redis_key)
#             for element in all_elements:
#                 redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(element))
#
#                 if not redis_client.exists(redis_key):
#                     cache_hist_contacts(int(element))
#
#                 redis_hash_key = 'Group[' + str(receiver) + ']'
#                 redis_client.hset(redis_key, redis_hash_key, json.dumps(historical_contacts, default=str))
#
#     elif chat_type == ws_config.NOTIFICATION_MESSAGE:
#         # 通知
#         historical_contacts = {
#             'user_id': sender,
#             'user_name': sender_name,
#             'chat_type': chat_type,
#             'receiver_list': receiver,
#             'last_msg_id': last_msg_id,
#             'last_msg': last_msg,
#             'last_msg_time': last_msg_time
#         }
#         receivers = receiver.split(',')
#         for recv in receivers:
#             if not redis_client.exists(ws_config.msg_cache_key['hist_contacts'].format(str(recv))):
#                 cache_hist_contacts(int(recv))
#
#             redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(recv))
#             redis_hash_key = 'Notification'
#             redis_client.hset(redis_key, redis_hash_key, json.dumps(historical_contacts, default=str))
#
#         redis_client.rpush(ws_config.NEW_HISTORICAL_CONTACTS_RECORD, json.dumps(historical_contacts, default=str))
#
#
# def read_unread_count(redis_key):
#     redis_client = redis.Redis(connection_pool=pool)
#     unread = 1
#     if redis_client.exists(redis_key) == 1:
#         # 未读数量 +1
#         unread = int(redis_client.get(redis_key)) + 1
#     redis_client.set(redis_key, unread)
#     return unread
#
#
# """
# 通过 socket 向用户推送通知, 同时更新未读消息未读数量（缓存数量加一）
# """
#
#
# def socket_push(msg: dict):
#     redis_client = redis.Redis(connection_pool=pool)
#     chat_type = msg.get('chat_type')
#     if chat_type == ws_config.PRIVATE_CHAT:
#         # 私聊
#         msg_receiver, msg_sender = msg.get('receiver'), msg.get('sender')
#         # 查询未读数量（先读缓存，缓存不存在读库）
#         unread_redis_key = ws_config.msg_cache_key['unread'].format(str(msg_sender), str(msg_receiver))
#         # 缓存中不存在唯独数量，读数据库，初始化
#         if redis_client.exists(unread_redis_key) == 0:
#             update_read(ws_config.PRIVATE_CHAT, msg_sender, msg_receiver, -1, True)
#         unread = read_unread_count(unread_redis_key)
#         push({"type": 100, "data": {"msg": msg, "unread": unread}}, int(msg_receiver))
#
#     elif chat_type == ws_config.GROUP_CHAT:
#         # 向所有用户推送未读消息数量，以及最后一条消息内容
#         msg_group_id, msg_sender = msg.get('group_id'), msg.get('sender')
#         group_member_redis_key = ws_config.msg_cache_key['group_member'].format(str(msg_group_id))
#         if not redis_client.exists(group_member_redis_key):
#             cache_group_member(msg_group_id)
#
#         group_member = redis_client.smembers(group_member_redis_key)
#         # 遍历群成员推送消息
#         for member in group_member:
#             # 如果群成员就是发送者本身，跳过
#             if int(member) == int(msg_sender):
#                 continue
#
#             # 查询未读数量（先读缓存，缓存不存在读库）
#             group_unread_redis_key = ws_config.msg_cache_key['group_unread'].format(str(msg_group_id), str(member))
#             if redis_client.exists(group_unread_redis_key) == 0:
#                 update_read(ws_config.GROUP_CHAT, int(member), int(msg_group_id), -1, True)
#
#             unread = read_unread_count(group_unread_redis_key)
#             push({"type": 100, "data": {"msg": msg, "unread": unread}}, int(member))
#
#     elif chat_type == ws_config.NOTIFICATION_MESSAGE:
#         # 向所有用户推送未读消息数量，以及最后一条消息内容
#         receivers = str(msg.get('receiver')).split(',')
#         for recv in receivers:
#             # 发送者本人不推送
#             if int(recv) == int(msg.get('sender')):
#                 continue
#             notification_unread_redis_key = ws_config.msg_cache_key['notification_unread'].format(str(recv))
#             if redis_client.exists(notification_unread_redis_key) == 0:
#                 update_read(ws_config.NOTIFICATION_MESSAGE, None, int(recv), -1, True)
#             unread = read_unread_count(notification_unread_redis_key)
#             push({"type": 100, "data": {"msg": msg, "unread": unread}}, int(recv))
#
#
# """
# 读取消息
# read_type = 0 通知消息
# read_type = 1 私聊消息
# read_type = 2 群聊消息
# """
#
#
# def read_messages(read_type: int, cur_user_id: int, chat_user_id: int, start: int, count: int):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     messages = []
#     if read_type == ws_config.NOTIFICATION_MESSAGE:
#         # 读取通知消息
#         notification_msg_redis_key = ws_config.msg_cache_key['notification_msg'].format(str(cur_user_id))
#         # 判断是否存在缓存，不存在查库并缓存
#         if redis_client.exists(notification_msg_redis_key) == 0:
#             cache_msg(ws_config.NOTIFICATION_MESSAGE, notification_msg_redis_key, cur_user_id, None)
#
#         in_cache = True
#         if start == -1:
#             messages = redis_client.lrange(notification_msg_redis_key, -count, -1)
#             for index in range(len(messages)):
#                 messages[index] = json.loads(messages[index])
#                 messages[index]["context"] = json.loads(messages[index].get('context'))
#         else:
#             list_len = redis_client.llen(notification_msg_redis_key)
#             first_data_in_redis = redis_client.lrange(notification_msg_redis_key, 0, 0)
#             last_data_in_redis = redis_client.lrange(notification_msg_redis_key, list_len - 1, list_len - 1)
#
#             # 将 JSON 对象转换为 Python 字典
#             first_data = json.loads(first_data_in_redis[0])
#             last_data = json.loads(last_data_in_redis[0])
#             first_msg_id, last_msg_id = first_data['id'], last_data['id']
#
#             if int(first_msg_id) < start <= int(last_msg_id):
#                 list_elements = redis_client.lrange(notification_msg_redis_key, 0, -1)
#                 for element in reversed(list_elements):
#                     data = json.loads(element)
#                     # 下拉刷新，每次查询的都是老数据，所以这里是 小于
#                     if int(data['id']) < start:
#                         data["context"] = json.loads(data.get('context'))
#                         messages.append(data)
#                     if len(messages) >= count:
#                         break
#             else:
#                 in_cache = False
#
#         # 缓存中不存在，查库 （缓存中并没有保存所有数据，有可能不会命中缓存）
#         if not in_cache:
#             query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
#                         'WHERE id < {} AND chat_type = {} AND FIND_IN_SET( {}, receiver) > 0 ' \
#                         'order by id desc limit {} ' \
#                 .format(start, ws_config.NOTIFICATION_MESSAGE, cur_user_id, count)
#             messages = db.query_all(query_sql)
#             if messages:
#                 for m in messages:
#                     m['context'] = json.loads(m.get('context'))
#                     if isinstance(m.get('timer'), datetime):
#                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
#
#         # 更新已读状态
#         if len(messages) > 0:
#             last_msg = messages[len(messages) - 1]
#             update_read(ws_config.NOTIFICATION_MESSAGE, None, int(cur_user_id), int(last_msg.get('id')))
#
#     elif read_type == ws_config.PRIVATE_CHAT:
#         # 读取私聊消息 (注意⚠️： 既要查询 A->B 的消息，也要查询 B->A 的消息) 保证双方发送的消息用同一个 key
#         private_msg_redis_key = ws_config.msg_cache_key['private_msg'].format(str(cur_user_id) + '-to-' + str(chat_user_id))
#         if int(chat_user_id) <= int(cur_user_id):
#             private_msg_redis_key = ws_config.msg_cache_key['private_msg'].format(
#                 str(chat_user_id) + '-to-' + str(cur_user_id))
#
#         # 判断是否存在缓存，不存在查库并缓存
#         if redis_client.exists(private_msg_redis_key) == 0:
#             cache_msg(ws_config.PRIVATE_CHAT, private_msg_redis_key, cur_user_id, chat_user_id)
#
#         in_cache = False
#         if redis_client.exists(private_msg_redis_key) == 1:
#             if start == -1:
#                 in_cache = True
#                 messages = redis_client.lrange(private_msg_redis_key, -count, -1)
#                 for index in range(len(messages)):
#                     messages[index] = json.loads(messages[index])
#             else:
#                 list_len = redis_client.llen(private_msg_redis_key)
#                 first_data_in_redis = redis_client.lrange(private_msg_redis_key, 0, 0)
#                 last_data_in_redis = redis_client.lrange(private_msg_redis_key, list_len - 1, list_len - 1)
#
#                 first_data = json.loads(first_data_in_redis[0])
#                 last_data = json.loads(last_data_in_redis[0])
#                 first_msg_id = first_data['id']
#                 last_msg_id = last_data['id']
#
#                 if int(first_msg_id) < start <= int(last_msg_id):
#                     in_cache = True
#                     list_elements = redis_client.lrange(private_msg_redis_key, 0, -1)
#                     for element in reversed(list_elements):
#                         data = json.loads(element)
#                         if int(data['id']) < start:
#                             messages.append(data)
#                         if len(messages) >= count:
#                             break
#
#         # 缓存不存在，入库查找
#         if not in_cache:
#             query_sql = 'select * from nsyy_gyl.ws_message where id < {} and chat_type = {} ' \
#                         'and (sender in {} or receiver in {})' \
#                         ' order by id desc limit {}  ' \
#                 .format(start, ws_config.PRIVATE_CHAT, (int(chat_user_id), int(cur_user_id)),
#                         (int(chat_user_id), int(cur_user_id)), count)
#             messages = db.query_all(query_sql)
#             if messages:
#                 for m in messages:
#                     if isinstance(m.get('timer'), datetime):
#                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
#
#         if len(messages) != 0:
#             # 更新私聊已读状态
#             last_msg = messages[len(messages) - 1]
#             update_read(ws_config.PRIVATE_CHAT, int(chat_user_id), cur_user_id, int(last_msg.get('id')))
#
#     elif read_type == ws_config.GROUP_CHAT:
#         in_group = is_in_group(chat_user_id, cur_user_id)
#         if not in_group:
#             raise Exception('您已被移除群组, 无法查看消息')
#
#         # 读取群聊消息
#         group_msg_redis_key = ws_config.msg_cache_key['group_msg'].format(str(chat_user_id))
#         # 判断是否存在缓存，不存在查库并缓存
#         if redis_client.exists(group_msg_redis_key) == 0:
#             cache_msg(ws_config.GROUP_CHAT, group_msg_redis_key, None, chat_user_id)
#
#         in_cache = False
#         if redis_client.exists(group_msg_redis_key) == 1:
#             if start == -1:
#                 in_cache = True
#                 messages = redis_client.lrange(group_msg_redis_key, -count, -1)
#                 for index in range(len(messages)):
#                     messages[index] = json.loads(messages[index])
#             else:
#                 list_len = redis_client.llen(group_msg_redis_key)
#                 first_data_in_redis = redis_client.lrange(group_msg_redis_key, 0, 0)
#                 last_data_in_redis = redis_client.lrange(group_msg_redis_key, list_len - 1, list_len - 1)
#
#                 first_data = json.loads(first_data_in_redis[0])
#                 last_data = json.loads(last_data_in_redis[0])
#                 first_msg_id = first_data['id']
#                 last_msg_id = last_data['id']
#
#                 if int(first_msg_id) < start <= int(last_msg_id):
#                     in_cache = True
#                     # Get all elements in the list
#                     list_elements = redis_client.lrange(group_msg_redis_key, 0, -1)
#                     for element in reversed(list_elements):
#                         data = json.loads(element)
#                         if int(data['id']) < start:
#                             messages.append(data)
#                         if len(messages) >= count:
#                             break
#
#         # 缓存不存在，入库查找
#         if not in_cache:
#             query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
#                         'WHERE id < {} and chat_type = {} AND group_id = {} order by id desc limit {} ' \
#                 .format(start, ws_config.GROUP_CHAT, int(chat_user_id), count)
#             messages = db.query_all(query_sql)
#             if messages:
#                 for m in messages:
#                     if isinstance(m.get('timer'), datetime):
#                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
#
#         if len(messages) != 0:
#             # 更新群聊已读状态
#             last_msg = messages[len(messages) - 1]
#             update_read(ws_config.GROUP_CHAT, int(chat_user_id), cur_user_id, int(last_msg.get('id')))
#
#     del db
#
#     if start != -1:
#         # 返回反序
#         return messages[::-1]
#     else:
#         return messages
#
#
# """
# 供 app 端查询最新消息并存储到本地, 返回消息的顺序需要和 read_messages 的相反
# read_message 查询 start 之前的消息
# read_message_for_update 查询 start 之后的消息
# read_type = 0 通知消息
# read_type = 1 私聊消息
# read_type = 2 群聊消息
# """
#
#
# # def read_messages_for_update(read_type: int, cur_user_id: int, chat_user_id: int, start: int, count: int):
# #     redis_client = redis.Redis(connection_pool=pool)
# #     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #                 global_config.DB_DATABASE_GYL)
# #
# #     messages = []
# #     if read_type == ws_config.NOTIFICATION_MESSAGE:
# #         # 读取通知消息
# #         notification_msg_redis_key = ws_config.msg_cache_key['notification_msg'].format(str(cur_user_id))
# #         # 判断是否存在缓存，不存在查库并缓存
# #         if redis_client.exists(notification_msg_redis_key) == 0:
# #             # 查询最新的 300 条消息（如果消息量大）
# #             query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
# #                         'and FIND_IN_SET( {}, receiver) > 0 ' \
# #                         'order by id desc limit 300 '.format(ws_config.NOTIFICATION_MESSAGE, str(cur_user_id))
# #             msg_list = db.query_all(query_sql)
# #
# #             if msg_list is not None:
# #                 for m in reversed(msg_list):
# #                     redis_client.rpush(notification_msg_redis_key, json.dumps(m, default=str))
# #
# #         in_cache = True
# #         if redis_client.exists(notification_msg_redis_key) == 1:
# #             list_len = redis_client.llen(notification_msg_redis_key)
# #             first_data_in_redis = redis_client.lrange(notification_msg_redis_key, 0, 0)
# #             last_data_in_redis = redis_client.lrange(notification_msg_redis_key, list_len - 1, list_len - 1)
# #
# #             # 将 JSON 对象转换为 Python 字典
# #             first_data = json.loads(first_data_in_redis[0])
# #             last_data = json.loads(last_data_in_redis[0])
# #             first_msg_id = first_data['id']
# #             last_msg_id = last_data['id']
# #
# #             if start == int(last_msg_id):
# #                 return messages
# #
# #             if int(first_msg_id) <= start <= int(last_msg_id) or start == -1:
# #                 # Get all elements in the list
# #                 list_elements = redis_client.lrange(notification_msg_redis_key, 0, -1)
# #                 for element in list_elements:
# #                     data = json.loads(element)
# #                     if int(data['id']) > start:
# #                         messages.append(data)
# #                     if len(messages) >= count:
# #                         break
# #             else:
# #                 in_cache = False
# #
# #         # 缓存中不存在，查库
# #         if not in_cache:
# #             query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
# #                         'WHERE id > {} AND chat_type = {} AND FIND_IN_SET( {}, receiver) > 0 limit {} ' \
# #                 .format(start, ws_config.NOTIFICATION_MESSAGE, cur_user_id, count)
# #             messages = db.query_all(query_sql)
# #             if messages:
# #                 for m in messages:
# #                     if isinstance(m.get('timer'), datetime):
# #                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
# #
# #     elif read_type == ws_config.PRIVATE_CHAT:
# #         # 读取私聊消息
# #         # 私聊(注意⚠️： 既要查询 A->B 的消息，也要查询 B->A 的消息)
# #         # 私聊, 保证双方发送的消息用同一个 key
# #         private_msg_redis_key = ws_config.msg_cache_key['private_msg'].format(str(cur_user_id) + '-to-' + str(chat_user_id))
# #         if int(chat_user_id) <= int(cur_user_id):
# #             private_msg_redis_key = ws_config.msg_cache_key['private_msg'].format(
# #                 str(chat_user_id) + '-to-' + str(cur_user_id))
# #
# #         # 判断是否存在缓存，不存在查库并缓存
# #         if redis_client.exists(private_msg_redis_key) == 0:
# #             # 查询最新的 300 条消息（如果消息量大）
# #             query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
# #                         'and ((sender = {} and receiver = {} ) or (sender = {} and receiver = {} ))' \
# #                         'order by id desc limit 300 '\
# #                 .format(ws_config.PRIVATE_CHAT, int(cur_user_id), int(chat_user_id),
# #                         int(chat_user_id), int(cur_user_id))
# #             msg_list = db.query_all(query_sql)
# #
# #             if msg_list is not None:
# #                 for m in reversed(msg_list):
# #                     redis_client.rpush(private_msg_redis_key, json.dumps(m, default=str))
# #
# #         in_cache = False
# #         if redis_client.exists(private_msg_redis_key) == 1:
# #             list_len = redis_client.llen(private_msg_redis_key)
# #             first_data_in_redis = redis_client.lrange(private_msg_redis_key, 0, 0)
# #             last_data_in_redis = redis_client.lrange(private_msg_redis_key, list_len - 1, list_len - 1)
# #
# #             first_data = json.loads(first_data_in_redis[0])
# #             last_data = json.loads(last_data_in_redis[0])
# #             first_msg_id = first_data['id']
# #             last_msg_id = last_data['id']
# #
# #             if start == int(last_msg_id):
# #                 return messages
# #
# #             if int(first_msg_id) <= start <= int(last_msg_id) or start == -1:
# #                 in_cache = True
# #                 # Get all elements in the list
# #                 list_elements = redis_client.lrange(private_msg_redis_key, 0, -1)
# #                 for element in list_elements:
# #                     data = json.loads(element)
# #                     if int(data['id']) > start:
# #                         messages.append(data)
# #                     if len(messages) >= count:
# #                         break
# #
# #         # 缓存不存在，入库查找
# #         if not in_cache:
# #             query_sql = 'select * from nsyy_gyl.ws_message where id > {} and chat_type = {} ' \
# #                         'and ((sender = {} and receiver = {} ) or (sender = {} and receiver = {} )) limit {} ' \
# #                 .format(start, ws_config.PRIVATE_CHAT, int(chat_user_id), cur_user_id,
# #                         cur_user_id, int(chat_user_id), count)
# #             messages = db.query_all(query_sql)
# #             if messages:
# #                 for m in messages:
# #                     if isinstance(m.get('timer'), datetime):
# #                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
# #
# #     elif read_type == ws_config.GROUP_CHAT:
# #         # 读取群聊消息
# #         group_msg_redis_key = ws_config.msg_cache_key['group_msg'].format(str(chat_user_id))
# #         # 判断是否存在缓存，不存在查库并缓存
# #         if redis_client.exists(group_msg_redis_key) == 0:
# #             # 查询最新的 300 条消息（如果消息量大）
# #             query_sql = 'select * from nsyy_gyl.ws_message where chat_type = {} ' \
# #                         'and group_id = {} ' \
# #                         'order by id desc limit 300 '\
# #                 .format(ws_config.GROUP_CHAT, int(chat_user_id))
# #             msg_list = db.query_all(query_sql)
# #             if msg_list is not None:
# #                 for m in reversed(msg_list):
# #                     redis_client.rpush(group_msg_redis_key, json.dumps(m, default=str))
# #
# #         in_cache = False
# #         if redis_client.exists(group_msg_redis_key) == 1:
# #             list_len = redis_client.llen(group_msg_redis_key)
# #             first_data_in_redis = redis_client.lrange(group_msg_redis_key, 0, 0)
# #             last_data_in_redis = redis_client.lrange(group_msg_redis_key, list_len - 1, list_len - 1)
# #
# #             first_data = json.loads(first_data_in_redis[0])
# #             last_data = json.loads(last_data_in_redis[0])
# #             first_msg_id = first_data['id']
# #             last_msg_id = last_data['id']
# #
# #             if start == int(last_msg_id):
# #                 return messages
# #
# #             if int(first_msg_id) <= start <= int(last_msg_id) or start == -1:
# #                 in_cache = True
# #                 # Get all elements in the list
# #                 list_elements = redis_client.lrange(group_msg_redis_key, 0, -1)
# #                 for element in list_elements:
# #                     data = json.loads(element)
# #                     if int(data['id']) > start:
# #                         messages.append(data)
# #                     if len(messages) >= count:
# #                         break
# #
# #         # 缓存不存在，入库查找
# #         if not in_cache:
# #             query_sql = 'SELECT * FROM nsyy_gyl.ws_message ' \
# #                         'WHERE id > {} and chat_type = {} AND group_id = {} limit {} ' \
# #                 .format(start, ws_config.GROUP_CHAT, int(chat_user_id), count)
# #             messages = db.query_all(query_sql)
# #             if messages:
# #                 for m in messages:
# #                     if isinstance(m.get('timer'), datetime):
# #                         m['timer'] = m.get('timer').strftime("%Y-%m-%d %H:%M:%S")
# #
# #     del db
# #     return messages
#
#
# def update_read(chat_type: int, sender: int, receiver: int, last_read: int, update_cache: bool = False):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     # 如果是通知类消息不需要关心发送者，只需要关心接收者
#     need_update_cache = update_cache
#     if chat_type == ws_config.NOTIFICATION_MESSAGE:
#         query_sql = 'SELECT * FROM nsyy_gyl.ws_message_read WHERE type = {} AND receiver = {} ' \
#             .format(chat_type, receiver)
#         existing_record = db.query_one(query_sql)
#         if existing_record is not None and existing_record.get('last_read') < last_read:
#             # 如果存在记录，则更新
#             update_sql = 'UPDATE nsyy_gyl.ws_message_read SET last_read = %s WHERE type = %s AND receiver = %s'
#             args = (last_read, chat_type, receiver)
#             db.execute(update_sql, args, need_commit=True)
#             need_update_cache = True
#         elif existing_record is None:
#             # 如果不存在记录，则插入新纪录
#             timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             args = (chat_type, receiver, last_read, timer)
#             insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, receiver, last_read, timer) VALUES (%s,%s,%s,%s)"
#             last_rowid = db.execute(insert_sql, args, need_commit=True)
#             if last_rowid == -1:
#                 raise Exception("已读状态入库失败!")
#             need_update_cache = True
#
#         if need_update_cache:
#             # 更新缓存
#             query_sql = 'select count(*) from nsyy_gyl.ws_message where chat_type = {} ' \
#                         'and FIND_IN_SET({}, receiver) > 0  and id > {} ' \
#                 .format(ws_config.NOTIFICATION_MESSAGE, int(receiver), int(last_read))
#             unread = db.query_one(query_sql)
#
#             notification_unread_redis_key = ws_config.msg_cache_key['notification_unread'].format(str(receiver))
#             redis_client.set(notification_unread_redis_key, int(unread.get('count(*)')))
#
#     else:
#         query_sql = 'SELECT * FROM nsyy_gyl.ws_message_read WHERE type = {} AND sender = {} AND receiver = {} ' \
#                 .format(chat_type, sender, receiver)
#         existing_record = db.query_one(query_sql)
#         if existing_record is not None and existing_record.get('last_read') < last_read:
#             # 如果存在记录，则更新
#             update_sql = 'UPDATE nsyy_gyl.ws_message_read SET last_read = %s ' \
#                          'WHERE type = %s AND sender = %s AND receiver = %s'
#             args = (last_read, chat_type, sender, receiver)
#             db.execute(update_sql, args, need_commit=True)
#             need_update_cache = True
#         elif existing_record is None:
#             # 如果不存在记录，则插入新纪录
#             timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             args = (chat_type, sender, receiver, last_read, timer)
#             insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
#                          "VALUES (%s,%s,%s,%s,%s)"
#             last_rowid = db.execute(insert_sql, args, need_commit=True)
#             if last_rowid == -1:
#                 raise Exception("已读状态入库失败!")
#             need_update_cache = True
#
#         if need_update_cache:
#             # 更新缓存
#             if chat_type == ws_config.GROUP_CHAT:
#                 if not sender:
#                     del db
#                     return
#                 query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
#                             'where chat_type = {} and group_id = {} and id > {} and sender != {}' \
#                     .format(ws_config.GROUP_CHAT, int(receiver), int(last_read), int(sender))
#                 unread = db.query_one(query_sql)
#
#                 # 更新缓存(这里 sender 是接收群消息的人， receiver 是群)
#                 group_unread_redis_key = ws_config.msg_cache_key['group_unread'].format(str(sender), str(receiver))
#                 redis_client.set(group_unread_redis_key, int(unread.get('count(*)')))
#             elif chat_type == ws_config.PRIVATE_CHAT:
#                 query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
#                             'where chat_type = {} and sender = {} and receiver = {} and id > {} ' \
#                     .format(ws_config.PRIVATE_CHAT, int(sender), int(receiver), int(last_read))
#                 unread = db.query_one(query_sql)
#
#                 # 更新缓存
#                 unread_redis_key = ws_config.msg_cache_key['unread'].format(str(sender), str(receiver))
#                 redis_client.set(unread_redis_key, int(unread.get('count(*)')))
#
#     del db
#
#
# """
# 读取群聊列表
# """
#
#
# def get_chat_list(user_id: int):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     all_unread: int = 0
#     chats = []
#     historical_contacts_redis_key = ws_config.msg_cache_key['hist_contacts'].format(str(user_id))
#     if not redis_client.exists(historical_contacts_redis_key):
#         cache_hist_contacts(int(user_id))
#
#     # 通知消息
#     value = redis_client.hget(historical_contacts_redis_key, 'Notification')
#     if value is not None:
#         unread = get_notification_unread(user_id, db)
#         contact = json.loads(value)
#         # 通知消息的context 也是 json 结构的
#         chats.append({
#             'id': user_id,
#             'name': '通知消息',
#             'chat_type': contact.get('chat_type'),
#             'last_msg_id': contact.get('last_msg_id'),
#             'last_msg': json.loads(contact.get('last_msg')),
#             'last_msg_time': contact.get('last_msg_time'),
#             'unread': int(unread)
#         })
#         all_unread += int(unread)
#     else:
#         # 从数据库查询最后一条通知消息
#         query_sql = 'select * from nsyy_gyl.ws_historical_contacts ' \
#                     'where chat_type = {} and FIND_IN_SET( {}, chat_id) > 0 ' \
#                     'order by last_msg_time limit 1 ' \
#             .format(ws_config.NOTIFICATION_MESSAGE, int(user_id))
#         historical_contact = db.query_one(query_sql)
#         if historical_contact is not None:
#             unread = get_notification_unread(user_id, db)
#             chats.append({
#                 'id': user_id,
#                 'name': '通知消息',
#                 'chat_type': historical_contact.get('chat_type'),
#                 'last_msg_id': historical_contact.get('last_msg_id'),
#                 'last_msg': historical_contact.get('last_msg'),
#                 'last_msg_time': historical_contact.get('last_msg_time'),
#                 'unread': int(unread)
#             })
#             all_unread += int(unread)
#
#     # 聊天消息
#     chat_group_set = set()
#     all_fields_and_values = redis_client.hgetall(historical_contacts_redis_key)
#     for key, value in all_fields_and_values.items():
#         # 跳过通知消息
#         if key == 'Notification':
#             continue
#
#         contact = json.loads(value)
#         if contact.get('chat_type') == ws_config.GROUP_CHAT:
#             # 判断当前用户还在不在该群聊中
#             in_group = is_in_group(int(contact.get('group_id')), user_id)
#             if not in_group:
#                 continue
#
#             # 群聊消息
#             group_id = int(contact.get('group_id'))
#             chat_group_set.add(group_id)
#             group_unread_redis_key = ws_config.msg_cache_key['group_unread'].format(str(group_id), str(user_id))
#             # 查询未读数量
#             if redis_client.exists(group_unread_redis_key) == 1:
#                 unread = redis_client.get(group_unread_redis_key)
#             else:
#                 query_sql = 'select * from nsyy_gyl.ws_message_read ' \
#                             'where type = {} and sender = {} and receiver = {} ' \
#                     .format(ws_config.GROUP_CHAT, int(user_id), int(group_id))
#                 message_read = db.query_one(query_sql)
#                 last_read = -1
#                 if message_read is not None:
#                     last_read = message_read.get('last_read')
#                 else:
#                     # 向 message_read 中插入一条记录
#                     timer = datetime.now()
#                     timer = timer.strftime("%Y-%m-%d %H:%M:%S")
#                     args = (ws_config.PRIVATE_CHAT, int(user_id), int(group_id), -1, timer)
#                     insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
#                                  "VALUES (%s,%s,%s,%s,%s)"
#                     last_rowid = db.execute(insert_sql, args, need_commit=True)
#                     if last_rowid == -1:
#                         raise Exception("已读状态入库失败!")
#
#                 query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
#                             'where chat_type = {} and group_id = {} and id > {} and sender != {}' \
#                     .format(ws_config.GROUP_CHAT, int(group_id), int(last_read), int(user_id))
#                 unread = db.query_one(query_sql)
#                 unread = unread.get('count(*)')
#
#             group_info = redis_client.get(ws_config.msg_cache_key['group_info'].format(str(group_id)))
#             group_info = json.loads(group_info)
#             # 更新缓存(这里 sender 是接收群消息的人， receiver 是群)
#             redis_client.set(group_unread_redis_key, int(unread))
#             chats.append({
#                 'id': group_id,
#                 'name': group_info.get('group_name'),
#                 'chat_type': contact.get('chat_type'),
#                 'last_msg_id': contact.get('last_msg_id'),
#                 'last_msg': contact.get('last_msg'),
#                 'last_msg_time': contact.get('last_msg_time'),
#                 'unread': int(unread)
#             })
#             all_unread += int(unread)
#
#         else:
#             # 私聊消息 查询未读数量
#             chat_user_id = contact.get('chat_id')
#             unread_redis_key = ws_config.msg_cache_key['unread'].format(str(chat_user_id), str(user_id))
#             if redis_client.exists(unread_redis_key) == 1:
#                 unread = redis_client.get(unread_redis_key)
#             else:
#                 query_sql = 'select * from nsyy_gyl.ws_message_read ' \
#                             'where type = {} and sender = {} and receiver = {} ' \
#                     .format(ws_config.PRIVATE_CHAT, int(chat_user_id), int(user_id))
#                 message_read = db.query_one(query_sql)
#                 last_read = -1
#                 if message_read is not None:
#                     last_read = message_read.get('last_read')
#                 else:
#                     # 向 message_read 中插入一条记录
#                     timer = datetime.now()
#                     timer = timer.strftime("%Y-%m-%d %H:%M:%S")
#                     args = (ws_config.PRIVATE_CHAT, int(chat_user_id), int(user_id), -1, timer)
#                     insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, sender, receiver, last_read, timer) " \
#                                  "VALUES (%s,%s,%s,%s,%s)"
#                     last_rowid = db.execute(insert_sql, args, need_commit=True)
#                     if last_rowid == -1:
#                         raise Exception("已读状态入库失败!")
#
#                 query_sql = 'select count(*) from nsyy_gyl.ws_message ' \
#                             'where chat_type = {} and sender = {} and receiver = {} and id > {} ' \
#                     .format(ws_config.PRIVATE_CHAT, int(chat_user_id), int(user_id), int(last_read))
#                 unread = db.query_one(query_sql)
#                 unread = int(unread.get("count(*)"))
#                 redis_client.set(unread_redis_key, unread)
#
#             chats.append({
#                 'id': user_id,
#                 'chat_id': int(chat_user_id),
#                 'name': contact.get('chat_name'),
#                 'chat_type': contact.get('chat_type'),
#                 'last_msg_id': contact.get('last_msg_id'),
#                 'last_msg': contact.get('last_msg'),
#                 'last_msg_time': contact.get('last_msg_time'),
#                 'unread': int(unread)
#             })
#             all_unread += int(unread)
#
#     # 加入的所有群聊
#     query_sql = 'select group_id from nsyy_gyl.ws_group_member where user_id = {} and state = 1' \
#         .format(user_id)
#     all = db.query_all(query_sql)
#
#     # 从所有群聊中移除发送过消息的群聊，剩下的就是已创建但未发送过消息的群聊
#     # 将要移除的元素从列表中删除
#     empty_group_list = []
#     for item in all:
#         if int(item.get('group_id')) not in list(chat_group_set):
#             empty_group_list.append(item.get('group_id'))
#
#     for id in empty_group_list:
#         group = db.query_one('select * from nsyy_gyl.ws_group where id = {}'.format(int(id)))
#         if group is not None:
#             chats.append({
#                 'id': group.get('id'),
#                 'name': group.get('group_name'),
#                 'chat_type': ws_config.GROUP_CHAT,
#                 "last_msg_time": group.get('timer').strftime("%Y-%m-%d %H:%M:%S"),
#                 'unread': 0
#             })
#     del db
#
#     # 按照未读数量和最后发送时间排序
#     chats = sorted(
#         chats,
#         key=lambda x: (x['unread'], datetime.strptime(x['last_msg_time'], "%Y-%m-%d %H:%M:%S")),
#         reverse=True
#     )
#     order_num = 1
#     for chat in chats:
#         chat['order_num'] = order_num
#         order_num += 1
#     return chats, all_unread
#
#
# def get_notification_unread(user_id: int, db):
#     redis_client = redis.Redis(connection_pool=pool)
#     notification_unread = ws_config.msg_cache_key['notification_unread'].format(str(user_id))
#     if redis_client.exists(notification_unread) == 1:
#         unread = int(redis_client.get(notification_unread))
#     else:
#         query_sql = 'select * from nsyy_gyl.ws_message_read where type = {} and receiver = {} ' \
#             .format(ws_config.NOTIFICATION_MESSAGE, int(user_id))
#         message_read = db.query_one(query_sql)
#         last_read = -1
#         if message_read is not None:
#             last_read = message_read.get('last_read')
#         else:
#             # 向 message_read 中插入一条记录
#             timer = datetime.now()
#             timer = timer.strftime("%Y-%m-%d %H:%M:%S")
#             args = (ws_config.NOTIFICATION_MESSAGE, int(user_id), -1, timer)
#             insert_sql = "INSERT INTO nsyy_gyl.ws_message_read (type, receiver, last_read, timer) " \
#                          "VALUES (%s,%s,%s,%s)"
#             last_rowid = db.execute(insert_sql, args, need_commit=True)
#             if last_rowid == -1:
#                 raise Exception("已读状态入库失败!")
#
#         query_sql = 'select count(*) from nsyy_gyl.ws_message where chat_type = {} ' \
#                     'and FIND_IN_SET({}, receiver) > 0 and id > {} ' \
#             .format(ws_config.NOTIFICATION_MESSAGE, int(user_id), int(last_read))
#         unread = db.query_one(query_sql)
#         unread = unread.get('count(*)')
#         # 更新缓存
#         redis_client.set(notification_unread, unread)
#
#     return unread
#
#
# #  ==========================================================================================
# #  ==========================     群组管理      ==============================================
# #  ==========================================================================================
#
#
# """
# 创建群聊
# """
#
#
# def create_group(group_name: str, creator: int, creator_name: str, members):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     args = (group_name, creator, creator_name, timer)
#     insert_sql = "INSERT INTO nsyy_gyl.ws_group (group_name, creator, creator_name, timer)" \
#                  " VALUES (%s,%s,%s,%s)"
#     group_id = db.execute(insert_sql, args, need_commit=True)
#     if group_id == -1:
#         raise Exception(f"群组 {group_name} 入库失败!")
#
#     redis_client.set(ws_config.msg_cache_key['group_info'].format(str(group_id)), json.dumps({
#         "id": group_id, "group_name": group_name, "creator": creator, "creator_name": creator_name, "timer": timer
#     }, default=str))
#
#     # 将创建者本身放入缓存
#     group_member_redis_key = ws_config.msg_cache_key['group_member'].format(str(group_id))
#     redis_client.sadd(group_member_redis_key, int(creator))
#
#     args = (group_id, int(creator), creator_name, 0, 1, timer)
#     insert_sql = "INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, user_name, join_type, state, timer)" \
#                  " VALUES (%s,%s,%s,%s,%s,%s)"
#     db.execute(insert_sql, args, need_commit=True)
#
#     for member in members:
#         if int(member.get('user_id')) == int(creator):
#             continue
#         args = (group_id, int(member.get('user_id')), member.get('user_name'), 0, 0, timer)
#         insert_sql = "INSERT INTO nsyy_gyl.ws_group_member (group_id, user_id, user_name, join_type, state, timer)" \
#                      " VALUES (%s,%s,%s,%s,%s,%s)"
#         db.execute(insert_sql, args, need_commit=True)
#
#     del db
#     group_notification = {
#         "type": 110,
#         "title": "入群邀请",
#         "description": "用户: " + creator_name + " 邀请您加入群聊 " + group_name,
#         "time": timer,
#         "group_info": {
#             "group_id": group_id,
#             "group_name": group_name,
#             "creator": creator
#         }
#     }
#
#     # 生成通知记录 & socket 推送， 使用列表推导式提取 "user_id" 值
#     user_ids = [int(m["user_id"]) for m in members]
#     user_ids_str = ','.join(map(str, user_ids))
#     send_notification_message(ws_config.NOTIFICATION_MESSAGE, creator, creator_name,
#                               user_ids_str, json.dumps(group_notification))
#
#     return {"group_id": group_id,
#             "group_name": group_name}
#
#
# """
# 更新群聊
# 前端做校验，仅群主可以编辑
# """
#
#
# def update_group(group_id: int, group_name: str, members):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     redis_client = redis.Redis(connection_pool=pool)
#
#     query_sql = "select * from nsyy_gyl.ws_group where id = {} ".format(group_id)
#     group = db.query_one(query_sql)
#     if group is None:
#         raise Exception("不存在群组，请仔细检查")
#
#     if group_name is not None:
#         update_sql = 'UPDATE nsyy_gyl.ws_group SET group_name = %s WHERE id = %s'
#         args = (group_name, group_id)
#         db.execute(update_sql, args, need_commit=True)
#         redis_client.set(ws_config.msg_cache_key['group_info'].format(str(group_id)), json.dumps({
#             "id": group_id, "group_name": group_name, "creator": group.get('creator'),
#             "creator_name": group.get('creator_name'), "timer": group.get('timer')
#         }, default=str))
#
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     for member in members:
#         if member.get('status') == 0:
#             # 新增群成员
#             query_sql = "select * from nsyy_gyl.ws_group_member where group_id = {} AND user_id = {} " \
#                 .format(group_id, member.get('user_id'))
#             group_member = db.query_one(query_sql)
#             if group_member:
#                 # 更新状态（之前已经入群，但移除后，再次邀请）
#                 update_sql = "UPDATE nsyy_gyl.ws_group_member SET state = 0, is_reply = 0 WHERE group_id = {} AND user_id = {} " \
#                     .format(group_id, member.get('user_id'))
#                 db.execute(update_sql, need_commit=True)
#             else:
#                 # 新邀请入群
#                 args = (group_id, member.get('user_id'), member.get('user_name'), 0, 0, timer)
#                 insert_sql = "INSERT INTO nsyy_gyl.ws_group_member " \
#                              "(group_id, user_id, user_name, join_type, state, timer)" \
#                              " VALUES (%s,%s,%s,%s,%s,%s)"
#                 db.execute(insert_sql, args, need_commit=True)
#
#             # 邀请人群
#             send_notification_message(ws_config.NOTIFICATION_MESSAGE,
#                                       int(group.get('creator')),
#                                       group.get('creator_name'),
#                                       str(member.get('user_id')),
#                                       json.dumps({
#                                                     "type": 110,
#                                                     "title": "入群邀请",
#                                                     "description": "用户: " + group.get('creator_name') + " 邀请您加入群聊 " + group.get('group_name'),
#                                                     "time": timer,
#                                                     "group_info": {
#                                                         "group_id": group_id,
#                                                         "group_name":  group.get('creator_name'),
#                                                         "creator": int(group.get('creator'))
#                                                     }
#                                                 }, default=str))
#
#         elif member.get('status') == 2:
#             # 移除群成员
#             update_sql = "UPDATE nsyy_gyl.ws_group_member SET state = 2 WHERE group_id = {} AND user_id = {} " \
#                 .format(group_id, member.get('user_id'))
#             db.execute(update_sql, need_commit=True)
#
#             # 移出缓存
#             group_member_redis_key = ws_config.msg_cache_key['group_member'].format(str(group_id))
#             if redis_client.exists(group_member_redis_key) == 1:
#                 redis_client.srem(group_member_redis_key, int(member.get('user_id')))
#     del db
#
#
# def query_group(group_id: int):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = "select * from nsyy_gyl.ws_group where id = {} " \
#         .format(group_id)
#     group = db.query_one(query_sql)
#     if group is None:
#         raise Exception('群聊不存在')
#
#     query_sql = "select user_id, user_name from nsyy_gyl.ws_group_member where group_id = {} and state = 1 " \
#         .format(group_id)
#     members = db.query_all(query_sql)
#     del db
#
#     group["member"] = members
#     return group
#
#
# """
# 确认加入群聊
# :param confirm: 1 同意 3 拒绝
# """
#
#
# def confirm_join_group(group_id: int, user_id: int, user_name: str, confirm: int):
#     redis_client = redis.Redis(connection_pool=pool)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     query_sql = "select * from nsyy_gyl.ws_group_member where group_id = {} and user_id = {} "\
#         .format(group_id, user_id)
#     group_member = db.query_one(query_sql)
#     if group_member is None:
#         raise Exception("不存在邀请记录，请仔细检查. ")
#     if int(group_member.get('is_reply')) == 1:
#         raise Exception("邀请记录已响应，请勿重复操作")
#
#     update_sql = "UPDATE nsyy_gyl.ws_group_member SET state = {}, is_reply = 1, update_time = '{}'  WHERE group_id = {} AND user_id = {} " \
#         .format(confirm, timer, group_id, user_id)
#     db.execute(update_sql, need_commit=True)
#
#     del db
#
#     # 放入缓存
#     if confirm == 1:
#         group_member_redis_key = ws_config.msg_cache_key['group_member'].format(str(group_id))
#         redis_client.sadd(group_member_redis_key, int(user_id))
#
#
# def is_in_group(group_id: int, user_id: int):
#     in_group = False
#     redis_client = redis.Redis(connection_pool=pool)
#     gm_redis_key = ws_config.msg_cache_key['group_member'].format(str(group_id))
#     if redis_client.exists(gm_redis_key) == 0:
#         cache_group_member(group_id)
#
#     for member in redis_client.smembers(gm_redis_key):
#         if int(member) == int(user_id):
#             in_group = True
#             break
#
#     return in_group
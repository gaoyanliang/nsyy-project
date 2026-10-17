import json
import logging
import random
import string
from datetime import datetime

import redis

from gylmodules import global_config
from gylmodules.group import group_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.workstation import ws_config
from gylmodules.workstation.mail import mail_server
from gylmodules.workstation.message.message_server import send_notification_message, send_message

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True, protocol=2)
logger = logging.getLogger(__name__)


"""创建群聊"""


def create_group(group_name: str, owner_id: str, owner_name: str, members, desc: str = "", user_mail_account: str = "", is_public: int = 1):
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=60 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(group_config.create_key.format(owner_id), 1, ex=70, nx=True):
        raise Exception('系统繁忙：请勿频繁创建群组，请于1分钟后再次尝试')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:

        # 随机生成邮箱群组账号
        while True:
            mail_account = generate_maillist_code(5)
            query_sql = f"select group_id from nsyy_gyl.group where mail_account = '{mail_account}' "
            if not db.query_one(query_sql):
                break

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        args = (group_name, owner_id, owner_name, created_at, created_at, desc, mail_account, user_mail_account, is_public)
        insert_sql = ("INSERT INTO nsyy_gyl.group (group_name, owner_id, owner_name, created_at, updated_at, description, "
                      "mail_account, user_mail_account, is_public) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)")
        group_id = db.execute(insert_sql, args, need_commit=True)
        if group_id == -1:
            raise Exception(f"群组 {group_name} 创建失败! 请检查群组数据，确保无误后重试！")

    redis_client.set(group_config.group_key.format(group_id), json.dumps({
        "group_id": group_id, "group_name": group_name, "owner_id": owner_id, "owner_name": owner_name,
        "created_at": created_at, "updated_at": created_at, "description": desc, "mail_account": mail_account,
        "user_mail_account": user_mail_account, "is_public": is_public}, default=str))

    # 将创建者本身放入缓存 (聊天系统需要)
    redis_client.sadd(group_config.group_member_ids_key.format(group_id), str(owner_id))

    values = []
    values.append((group_id, owner_id, owner_name, user_mail_account, 0, 1, 1, 2, created_at, created_at))
    for member in members:
        if str(member.get('user_id')) != str(owner_id):
            values.append((group_id, member.get('user_id'), member.get('user_name'), member.get('user_mail_account'),
                           0, 0, 0, 0, created_at, created_at))

    insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, user_mail_account, join_type, 
                state, is_reply, allow_edit, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                ON DUPLICATE KEY UPDATE state = VALUES(state), is_reply = VALUES(is_reply), 
                allow_edit = VALUES(allow_edit), updated_at = VALUES(updated_at)"""

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        db.execute_many(insert_sql, args=values, need_commit=True)

    group_notification = {"type": 110, "title": "入群邀请", "description": f"用户 {owner_name} 邀请您加入群聊 {group_name}",
                          "time": created_at, "group_info": { "group_id": group_id, "group_name": group_name,
                                                              "creator": owner_name}
                        }

    # 生成通知记录 & socket 推送， 使用列表推导式提取 "user_id" 值
    user_ids = [int(m["user_id"]) for m in members]
    for user_id in user_ids:
        if int(user_id) == int(owner_id):
            continue
        send_notification_message(ws_config.NOTIFICATION_MESSAGE, int(owner_id), owner_name,
                                  user_id, "", json.dumps(group_notification, default=str))

    # 创建者发送一条消息，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
    send_message(ws_config.GROUP_CHAT, 0, int(owner_id), owner_name, int(group_id), int(group_id), group_name,
                 f"{owner_name} 创建了群聊 {group_name}")

    # 在邮箱服务器创建对应群组
    if mail_account and user_mail_account:
        mail_server.create_mail_group_at_mail_server(group_id, group_name, mail_account, is_public)
        mail_server.op_group_members_at_mail_server(group_id, group_name, mail_account, user_mail_account)

    return {"group_id": group_id, "group_name": group_name}


"""生成指定长度的字符串 群组邮箱编号 固定以 maillist_ 为前缀  """


def generate_maillist_code(length):
    characters = string.ascii_lowercase + string.digits
    # 使用random.choices从字符集中随机选择字符，形成指定长度的字符串
    random_string = ''.join(random.choices(characters, k=length))
    return 'maillist_' + random_string + "@nsyy.com"


"""
更新群聊
前端做校验，仅群主可以编辑
"""


def update_group(group_id: int, group_name: str, desc: str, is_public, cur_user_id, members):
    redis_client = redis.Redis(connection_pool=pool)
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        group = db.query_one(f"select * from nsyy_gyl.group where group_id = {group_id} ")
        if not group:
            raise Exception("群组不存在，请仔细确认后重试")
        if not db.query_one(f"select * from nsyy_gyl.group_member where group_id = {group_id} and user_id = {cur_user_id} and allow_edit >= 1"):
            raise Exception("您没有权限编辑此群组, 请联系管理员")

    # 构建更新字段
    update_fields = []
    update_values = []

    if group_name:
        update_fields.append("group_name = %s")
        update_values.append(group_name)
        group['group_name'] = group_name

    if desc:
        update_fields.append("description = %s")
        update_values.append(desc)
        group['description'] = desc

    if is_public is not None:
        update_fields.append("is_public = %s")
        update_values.append(is_public)
        group['is_public'] = is_public

    # 执行更新
    if update_fields:
        update_sql = f"""UPDATE nsyy_gyl.group SET {', '.join(update_fields)} WHERE group_id = {group_id}"""
        db.execute(update_sql, tuple(update_values), need_commit=True)
        redis_client.set(group_config.group_key.format(group_id), json.dumps(group, default=str))

    timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if members:
        values = []
        for member in members:
            if not member.get('user_id') or not member.get('user_name') :
                continue
            values.append((group_id, member.get('user_id'), member.get('user_name'), member.get('user_mail_account', ''),
                               member.get('state', 0), member.get('allow_edit', 0), 0, timer, timer))

        insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, user_mail_account, 
                    state, allow_edit, is_reply,  created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    ON DUPLICATE KEY UPDATE allow_edit = VALUES(allow_edit), updated_at = VALUES(updated_at), state = VALUES(state), is_reply = VALUES(is_reply)"""
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL) as db:
            db.execute_many(insert_sql, args=values, need_commit=True)

    for member in members:
        if member.get('state') == 0:
            # 邀请人群
            send_notification_message(ws_config.NOTIFICATION_MESSAGE,
                                      int(group.get('owner_id')),
                                      group.get('owner_name'),
                                      member.get('user_id'),
                                      member.get('user_name'),
                                      json.dumps({
                                          "type": 110, "title": "入群邀请", "time": timer,
                                          "description": "用户: " + group.get(
                                                'owner_name') + " 邀请您加入群聊 " + group.get('group_name'),
                                          "group_info": {
                                              "group_id": group_id,
                                              "group_name": group.get('owner_name'),
                                              "creator": int(group.get('owner_id'))
                                          }
                                      }, default=str))

        elif member.get('state') == 2:
            # 移出缓存
            group_member_redis_key = group_config.group_member_ids_key.format(group_id)
            if redis_client.sismember(group_member_redis_key, str(member.get('user_id'))) == 1:
                redis_client.srem(group_member_redis_key, int(member.get('user_id')))

                # 在邮箱服务器中移除群成员
                if group.get('mail_account') and member.get('user_mail_account'):
                    mail_server.op_group_members_at_mail_server(group_id, group_name, group.get('mail_account'),
                                                                member.get('user_mail_account'), is_add=False)
        else:
            logger.warning(f"未知状态 {member} 忽略")


"""解散群组"""


def disband_group(group_id, user_id):
    redis_client = redis.Redis(connection_pool=pool)
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        group = db.query_one(f"select * from nsyy_gyl.group where group_id = {group_id} ")
        if not group:
            raise Exception("群组不存在，请仔细确认后重试")
        if not db.query_one(f"select * from nsyy_gyl.group_member where group_id = {group_id} and user_id = {user_id} and allow_edit >= 1"):
            raise Exception("您没有权限解散此群组, 请联系管理员")

        db.execute(f"update nsyy_gyl.group set group_state = 0, updated_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' where group_id = {group_id}", need_commit=True)
        redis_client.delete(group_config.group_key.format(group_id))

        db.execute(f"update nsyy_gyl.group_member set state = 2, updated_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' where group_id = {group_id}", need_commit=True)
        redis_client.delete(group_config.group_member_ids_key.format(group_id))

    mail_server.delete_mail_group(group.get('mail_account'), group.get('group_name'))


"""查询群组详情"""


def query_group(group_id):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        group = db.query_one(f"select * from nsyy_gyl.group where group_id = {group_id} ")
        if group is None:
            raise Exception('群聊不存在')
        if group.get('group_state') == 0:
            raise Exception('群聊已解散')

        query_sql = (f"select user_id, user_name, user_mail_account, state, allow_edit, mail_state "
                     f"from nsyy_gyl.group_member where group_id = {group_id} and state = 1")
        members = db.query_all(query_sql)

    group["member"] = members
    return group


"""查询用户加入的群组列表"""


def query_user_group(user_id, group_type: int = 1):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        groups = db.query_all(f"select * from nsyy_gyl.group where group_id in (select group_id from nsyy_gyl.group_member "
                              f"where user_id = {user_id} and state = 1) and group_state = 1 and group_type = {group_type}")
    return groups


"""确认加入群聊 confirm: 1 同意 3 拒绝 """


def confirm_join_group(group_id, user_id, user_name, confirm: int):
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:

        timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query_sql = f"select * from nsyy_gyl.group_member where group_id = {group_id} and user_id = {user_id} "
        group_member = db.query_one(query_sql)
        if group_member is None:
            raise Exception("不存在邀请记录，请仔细检查. ")
        if int(group_member.get('is_reply')) == 1:
            raise Exception("邀请记录已响应，请勿重复操作，入要加入群聊请联系群主重新邀请")

        update_sql = f"UPDATE nsyy_gyl.group_member SET state = {confirm}, is_reply = 1, " \
                     f"updated_at = '{timer}' WHERE group_id = {group_id} AND user_id = {user_id} "
        db.execute(update_sql, need_commit=True)

    # 放入缓存
    if confirm == 1:
        # 加入聊天群
        group_member_redis_key = group_config.group_member_ids_key.format(group_id)
        redis_client = redis.Redis(connection_pool=pool)
        redis_client.sadd(group_member_redis_key, str(user_id))

        group_info = redis_client.get(group_config.group_key.format(group_id))
        group_info = json.loads(group_info)
        group_name = group_info.get('group_name')

        # 给创建者也发送一个通知，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
        send_message(ws_config.GROUP_CHAT, 0, int(user_id), user_name, int(group_id), int(group_id), group_name,
                     f"{user_name} 加入了群聊 {group_name}")

        try:
            # 加入邮件群
            mail_account = group_info.get('mail_account')
            if mail_account and group_member.get('user_mail_account'):
                op_state = mail_server.op_group_members_at_mail_server(group_id, group_name,
                                                                       mail_account, group_member.get('user_mail_account'))

            if op_state:
                update_sql = (f"UPDATE nsyy_gyl.group_member SET mail_state = 1, "
                              f"updated_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' "
                              f"WHERE group_id = {group_id} AND user_id = {user_id} ")
                with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                            global_config.DB_DATABASE_GYL) as db:
                    db.execute(update_sql, need_commit=True)
        except Exception as e:
            logger.error(f"加入邮箱群 {group_id} 失败")


"""创建急诊会诊群聊"""


def create_group(group_name: str, owner_id: str, owner_name: str, members, desc: str = "", user_mail_account: str = "", is_public: int = 1):
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=60 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(group_config.create_key.format(owner_id), 1, ex=70, nx=True):
        raise Exception('系统繁忙：请勿频繁创建群组，请于1分钟后再次尝试')

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:

        # 随机生成邮箱群组账号
        while True:
            mail_account = generate_maillist_code(5)
            query_sql = f"select group_id from nsyy_gyl.group where mail_account = '{mail_account}' "
            if not db.query_one(query_sql):
                break

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        args = (group_name, owner_id, owner_name, created_at, created_at, desc, mail_account, user_mail_account, is_public)
        insert_sql = ("INSERT INTO nsyy_gyl.group (group_name, owner_id, owner_name, created_at, updated_at, description, "
                      "mail_account, user_mail_account, is_public) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)")
        group_id = db.execute(insert_sql, args, need_commit=True)
        if group_id == -1:
            raise Exception(f"群组 {group_name} 创建失败! 请检查群组数据，确保无误后重试！")

    redis_client.set(group_config.group_key.format(group_id), json.dumps({
        "group_id": group_id, "group_name": group_name, "owner_id": owner_id, "owner_name": owner_name,
        "created_at": created_at, "updated_at": created_at, "description": desc, "mail_account": mail_account,
        "user_mail_account": user_mail_account, "is_public": is_public}, default=str))

    # 将创建者本身放入缓存 (聊天系统需要)
    redis_client.sadd(group_config.group_member_ids_key.format(group_id), str(owner_id))

    values = []
    values.append((group_id, owner_id, owner_name, user_mail_account, 0, 1, 1, 2, created_at, created_at))
    for member in members:
        if str(member.get('user_id')) != str(owner_id):
            values.append((group_id, member.get('user_id'), member.get('user_name'), member.get('user_mail_account'),
                           0, 0, 0, 0, created_at, created_at))

    insert_sql = """INSERT INTO nsyy_gyl.group_member (group_id, user_id, user_name, user_mail_account, join_type, 
                state, is_reply, allow_edit, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                ON DUPLICATE KEY UPDATE state = VALUES(state), is_reply = VALUES(is_reply), 
                allow_edit = VALUES(allow_edit), updated_at = VALUES(updated_at)"""

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
        db.execute_many(insert_sql, args=values, need_commit=True)

    group_notification = {"type": 110, "title": "入群邀请", "description": f"用户 {owner_name} 邀请您加入群聊 {group_name}",
                          "time": created_at, "group_info": { "group_id": group_id, "group_name": group_name,
                                                              "creator": owner_name}
                        }

    # 生成通知记录 & socket 推送， 使用列表推导式提取 "user_id" 值
    user_ids = [int(m["user_id"]) for m in members]
    for user_id in user_ids:
        if int(user_id) == int(owner_id):
            continue
        send_notification_message(ws_config.NOTIFICATION_MESSAGE, int(owner_id), owner_name,
                                  user_id, "", json.dumps(group_notification, default=str))

    # 创建者发送一条消息，主要用于在创建者手机上创建一个空的群聊天框，否则创建成功之后，找不到群聊
    send_message(ws_config.GROUP_CHAT, 0, int(owner_id), owner_name, int(group_id), int(group_id), group_name,
                 f"{owner_name} 创建了群聊 {group_name}")

    # 在邮箱服务器创建对应群组
    if mail_account and user_mail_account:
        mail_server.create_mail_group_at_mail_server(group_id, group_name, mail_account, is_public)
        mail_server.op_group_members_at_mail_server(group_id, group_name, mail_account, user_mail_account)

    return {"group_id": group_id, "group_name": group_name}











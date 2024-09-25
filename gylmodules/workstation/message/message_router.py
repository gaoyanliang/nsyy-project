import traceback

from flask import Blueprint, jsonify, request
from gylmodules.workstation import ws_config
from gylmodules.workstation.message import message
import json
from datetime import datetime

message_router = Blueprint('message router', __name__, url_prefix='/msg')


#  发送聊天消息
@message_router.route('/chat', methods=['POST'])
def chat():
    json_data = json.loads(request.get_data().decode('utf-8'))
    context_type = json_data.get("context_type")
    sender = json_data.get("sender")
    sender_name = json_data.get("sender_name")
    group_id = json_data.get("group_id")
    receiver = json_data.get("receiver")
    receiver_name = json_data.get("receiver_name")

    # TODO image/video/audio/link 特殊处理 ，现在只处理 text
    # TODO 如果是多媒体类型，需要先调用上茶接口，获取到存储地址
    context = json_data.get("context")

    try:
        if group_id is None:
            msg_id = message.send_message(ws_config.PRIVATE_CHAT, int(context_type), int(sender), sender_name,
                                 None, receiver, receiver_name, context)
        else:
            msg_id = message.send_message(ws_config.GROUP_CHAT, int(context_type), int(sender), sender_name,
                                 int(group_id), receiver, receiver_name, context)
    except Exception as e:
        print(datetime.now(), f"chat: An unexpected error occurred: {e}, param = ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '消息发送失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '消息发送成功',
        'data': msg_id
    })


#  发送通知消息 TODO 测试
@message_router.route('/notification', methods=['POST'])
def notification():
    json_data = json.loads(request.get_data().decode('utf-8'))
    context_type = json_data.get("context_type")
    cur_user_id = json_data.get('cur_user_id')
    cur_user_name = json_data.get('cur_user_name')
    receiver = json_data.get("receiver")

    # TODO image/video/audio/link 特殊处理 ，现在只处理 text
    # TODO 如果是多媒体类型，需要先调用上茶接口，获取到存储地址
    context = json_data.get("context")

    try:
        if type(context) == dict:
            context = json.dumps(context, default=str)
        message.send_notification_message(int(context_type), int(cur_user_id), cur_user_name, receiver, context)
    except Exception as e:
        print(datetime.now(), f"chat: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '通知发送失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '通知发送成功',
        'data': '通知发送成功'
    })


# 读取消息
# read_type = 0 通知消息
# read_type = 1 私聊消息
# read_type = 2 群聊消息
@message_router.route('/read_messages', methods=['POST'])
def read_messages():
    json_data = json.loads(request.get_data().decode('utf-8'))
    read_type = json_data.get('read_type')
    # 当前用户是发送者
    cur_user_id = json_data.get("cur_user_id")
    # 聊天对象是接收者
    chat_user_id = json_data.get("chat_user_id")
    start = json_data.get("start")
    count = json_data.get("count")

    try:
        if read_type is None:
            return jsonify({
                'code': 50000,
                'res': '读取消息失败，缺少参数 read_type, '
                       'read_type = 0 读取通知消息; read_type = 1 读取私聊消息; read_type = 2 读取群聊消息',
                'data': '读取消息失败，缺少参数 read_type, '
                        'read_type = 0 读取通知消息; read_type = 1 读取私聊消息; read_type = 2 读取群聊消息'
            })
        elif int(read_type) == 0 and cur_user_id is None:
            return jsonify({
                'code': 50000,
                'res': '读取消息失败，缺少参数 cur_user_id, ',
                'data': '读取消息失败，缺少参数 read_type, '
            })
        elif int(read_type) == 1 and chat_user_id is None:
            return jsonify({
                'code': 50000,
                'res': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为私聊对象的id',
                'data': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为私聊对象的id'
            })
        elif int(read_type) == 2 and chat_user_id is None:
            return jsonify({
                'code': 50000,
                'res': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为group_id',
                'data': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为group_id'
            })

        messages = message.read_messages(int(read_type), int(cur_user_id), chat_user_id, int(start), int(count))
    except Exception as e:
        print(datetime.now(), f"message_router.read_messages: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '读取消息失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '读取消息成功',
        'data': messages
    })


# @message_router.route('/read_messages_for_update', methods=['POST'])
# def read_messages_for_update():
#     json_data = json.loads(request.get_data().decode('utf-8'))
#     read_type = json_data.get('read_type')
#     # 当前用户是发送者
#     cur_user_id = json_data.get("cur_user_id")
#     # 聊天对象是接收者
#     chat_user_id = json_data.get("chat_user_id")
#     start = json_data.get("start")
#     count = json_data.get("count")
#
#     try:
#         if read_type is None:
#             return jsonify({
#                 'code': 50000,
#                 'res': '读取消息失败，缺少参数 read_type, '
#                        'read_type = 0 读取通知消息; read_type = 1 读取私聊消息; read_type = 2 读取群聊消息',
#                 'data': '读取消息失败，缺少参数 read_type, '
#                        'read_type = 0 读取通知消息; read_type = 1 读取私聊消息; read_type = 2 读取群聊消息'
#             })
#         elif int(read_type) == 0 and cur_user_id is None:
#             return jsonify({
#                 'code': 50000,
#                 'res': '读取消息失败，缺少参数 cur_user_id, ',
#                 'data': '读取消息失败，缺少参数 read_type, '
#             })
#         elif int(read_type) == 1 and chat_user_id is None:
#             return jsonify({
#                 'code': 50000,
#                 'res': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为私聊对象的id',
#                 'data': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为私聊对象的id'
#             })
#         elif int(read_type) == 2 and chat_user_id is None:
#             return jsonify({
#                 'code': 50000,
#                 'res': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为group_id',
#                 'data': '读取消息失败，缺少参数 chat_user_id, chat_user_id 为group_id'
#             })
#
#         messages = message.read_messages_for_update(int(read_type), int(cur_user_id),
#                                                     chat_user_id, int(start), int(count))
#     except Exception as e:
#         print(f"message_router.read_messages: An unexpected error occurred: {e}")
#         print(traceback.print_exc())
#         return jsonify({
#             'code': 50000,
#             'res': e.__str__(),
#             'data': '读取消息失败，请稍后重试'
#         })
#
#     return jsonify({
#         'code': 20000,
#         'res': '读取消息成功',
#         'data': messages
#     })


# 读取群聊列表
@message_router.route('/read_chats', methods=['POST'])
def read_chats():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_id = json_data.get("user_id")

    try:
        chats, all_unread = message.get_chat_list(int(user_id))

        # 群聊创建之后没人说话时，也需要展示在列表上，但是redis 在将群聊信息写入到数据库之前有一个时间差（写入之前有人发送了消息），
        # 可能导致同一个群聊查询出2个记录一个有lastmsg 一个空群聊
        if chats is not None:
            # 使用集合和列表来保存唯一的 user_id 和记录
            uniques = set()
            filtered = []

            # 遍历每个字典
            for record in chats:
                chat_type = record.get('chat_type')
                if chat_type == ws_config.GROUP_CHAT:
                    id = record.get("id")
                    # 如果 user_id 不在集合中，将其添加到集合，并添加整个记录到列表中
                    if id not in uniques:
                        uniques.add(id)
                        filtered.append(record)
                    # 如果 id 已存在，但 last_msg_time 不为空，则替换掉之前的记录
                    else:
                        if record.get('last_msg_time') is not None:
                            filtered.append(record)
                else:
                    filtered.append(record)
            chats = filtered
    except Exception as e:
        print(datetime.now(), f"read_notification_messages: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '读取群聊列表失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '读取群聊列表成功',
        'data': chats,
        'all_unread': all_unread
    })


@message_router.route('/update_unread', methods=['POST'])
def update_unread():
    json_data = json.loads(request.get_data().decode('utf-8'))
    chat_type = json_data.get("chat_type")
    sender = json_data.get("sender")
    receiver = json_data.get("receiver")
    last_read = json_data.get("last_read")

    try:
        if last_read is None or last_read == '':
            return jsonify({
                'code': 20000
            })
        message.update_read(int(chat_type), sender, receiver, last_read, True)
    except Exception as e:
        print(datetime.now(), f"chat: An unexpected error occurred: {e}, pararm = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000
        })

    return jsonify({
        'code': 20000
    })


#  ==========================================================================================
#  ==========================     群组管理      ==============================================
#  ==========================================================================================


#  创建群聊
@message_router.route('/create_group', methods=['POST'])
def create_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_name = json_data.get("group_name")
    creator = json_data.get("creator")
    creator_name = json_data.get("creator_name")
    members = json_data.get("members")

    try:
        group = message.create_group(group_name, creator, creator_name, members)
    except Exception as e:
        print(datetime.now(), f"create_chat_group: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': {}
        })

    return jsonify({
        'code': 20000,
        'res': '群组创建成功',
        'data': group
    })


@message_router.route('/query_group', methods=['POST'])
def query_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_id = json_data.get("group_id")

    try:
        group = message.query_group(group_id)
    except Exception as e:
        print(datetime.now(), f"query_group: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '查询群组失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '查询群组成功',
        'data': group
    })


#  群名称更新
@message_router.route('/update_group', methods=['POST'])
def update_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_name = json_data.get("group_name")
    group_id = json_data.get("group_id")
    members = json_data.get('members') if json_data.get('members') else []
    try:
        message.update_group(int(group_id), group_name, members)
    except Exception as e:
        print(datetime.now(), f"update_group: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '群组更新失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '群组更新成功',
        'data': '群组更新成功'
    })


#  确认加入群聊
@message_router.route('/confirm_join_group', methods=['POST'])
def confirm_join_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_id = json_data.get("group_id")
    user_id = json_data.get("user_id")
    user_name = json_data.get("user_name")
    confirm = json_data.get("confirm")

    try:
        message.confirm_join_group(int(group_id), int(user_id), user_name, int(confirm))
    except Exception as e:
        print(datetime.now(), f"search_group: An unexpected error occurred: {e}, param = ", json_data)
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '确认入群失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '操作成功',
        'data': '操作成功'
    })

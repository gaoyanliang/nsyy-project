import traceback

from flask import Blueprint, jsonify, request
from gylmodules.utils.unified_logger import UnifiedLogger
from gylmodules.workstation.message import message
import json

message_router = Blueprint('message router', __name__, url_prefix='/msg')
log = UnifiedLogger()


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
        message.send_chat_message(int(context_type), int(sender), sender_name, group_id, receiver, receiver_name, context)
    except Exception as e:
        print(f"chat: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '消息发送失败，请稍后重试',
            'data': '消息发送失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '消息发送成功',
        'data': '消息发送成功'
    })


#  发送通知消息 TODO 测试
@message_router.route('/notification', methods=['POST'])
def notification():
    json_data = json.loads(request.get_data().decode('utf-8'))
    context_type = json_data.get("context_type")
    cur_user_id = json_data.get('cur_user_id')
    receiver = json_data.get("receiver")

    # TODO image/video/audio/link 特殊处理 ，现在只处理 text
    # TODO 如果是多媒体类型，需要先调用上茶接口，获取到存储地址
    context = json_data.get("context")

    try:
        message.send_notification_message(int(context_type), int(cur_user_id), receiver, context)
    except Exception as e:
        print(f"chat: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '消息发送失败，请稍后重试',
            'data': '消息发送失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '消息发送成功',
        'data': '消息发送成功'
    })


# TODO 更新已读状态  测试
@message_router.route('/update_unread', methods=['POST'])
def update_unread():
    json_data = json.loads(request.get_data().decode('utf-8'))
    type = json_data.get("type")
    is_group = json_data.get("is_group")
    sender = json_data.get("sender")
    receiver = json_data.get("receiver")
    last_read = json_data.get("last_read")

    try:
        message.update_read(int(type), is_group, sender, receiver, last_read)
    except Exception as e:
        print(f"chat: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000
        })

    return jsonify({
        'code': 20000
    })


# 读取通知消息
@message_router.route('/read_notification_messages', methods=['POST'])
def read_notification_messages():
    json_data = json.loads(request.get_data().decode('utf-8'))
    receiver = json_data.get("receiver")
    start = json_data.get("start")
    count = json_data.get("count")

    try:
        notification_messages = message.get_notification_message_list(int(receiver), int(start), int(count))
    except Exception as e:
        print(f"read_notification_messages: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '读取通知消息失败，请稍后重试',
            'data': '读取通知消息失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '读取通知消息成功',
        'data': notification_messages
    })


# 读取群聊列表
@message_router.route('/read_chats', methods=['POST'])
def read_chats():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_id = json_data.get("user_id")

    try:
        chats = message.get_chat_list(int(user_id))
    except Exception as e:
        print(f"read_notification_messages: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '读取群聊列表失败，请稍后重试',
            'data': '读取群聊列表失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '读取群聊列表成功',
        'data': chats
    })


# 读取群聊消息
@message_router.route('/read_chat_message', methods=['POST'])
def read_chat_message():
    json_data = json.loads(request.get_data().decode('utf-8'))
    # 当前用户是发送者
    cur_user_id = json_data.get("cur_user_id")
    # 聊天对象是接收者
    chat_user_id = json_data.get("chat_user_id")
    group_id = json_data.get("group_id")
    start = json_data.get("start")
    count = json_data.get("count")

    try:
        chat_messages = message.get_chat_message(int(cur_user_id), chat_user_id, group_id, int(start), int(count))
    except Exception as e:
        print(f"read_chat_message: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '读取群聊消息失败，请稍后重试',
            'data': '读取群聊消息失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '读取群聊消息成功',
        'data': chat_messages
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
    members = json_data.get("members")

    try:
        message.create_group(group_name, creator, members)
    except Exception as e:
        print(f"create_chat_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '群组创建失败，请稍后重试',
            'data': '群组创建失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '群组创建成功',
        'data': '群组创建成功'
    })


#  群名称更新
@message_router.route('/update_group', methods=['POST'])
def update_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_name = json_data.get("group_name")
    group_id = json_data.get("group_id")

    try:
        message.update_group_name(int(group_id), group_name)
    except Exception as e:
        print(f"update_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '群名称更新失败，请稍后重试',
            'data': '群名称更新失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '群名称更新成功',
        'data': '群名称更新成功'
    })


#  加入群聊
@message_router.route('/join_group', methods=['POST'])
def join_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_id = json_data.get("group_id")
    members = json_data.get("members")
    join_type = json_data.get("join_type")

    try:
        message.join_group(int(group_id), members, int(join_type))
    except Exception as e:
        print(f"join_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '加入群聊失败，请稍后重试',
            'data': '加入群聊失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '加入群聊成功',
        'data': '加入群聊成功'
    })


#  移出群聊
@message_router.route('/remove_group', methods=['POST'])
def remove_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_id = json_data.get("group_id")
    members = json_data.get("members")

    try:
        message.remove_group(int(group_id), members)
    except Exception as e:
        print(f"remove_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '移出群聊失败，请稍后重试',
            'data': '移出群聊失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '移出群聊成功',
        'data': '移出群聊成功'
    })


#  确认加入群聊
@message_router.route('/confirm_join_group', methods=['POST'])
def confirm_join_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    group_id = json_data.get("group_id")
    user_id = json_data.get("user_id")

    try:
        message.confirm_join_group(int(group_id), int(user_id))
    except Exception as e:
        print(f"search_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '确认入群失败，请稍后重试',
            'data': '确认入群失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '确认入群成功',
        'data': '确认入群成功'
    })






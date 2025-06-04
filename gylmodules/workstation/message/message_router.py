import traceback

from flask import Blueprint, jsonify, request
from gylmodules.workstation import ws_config
from gylmodules.workstation.message import message_server
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
            message_server.send_message(ws_config.PRIVATE_CHAT, int(context_type), int(sender), sender_name,
                                 None, receiver, receiver_name, context)
        else:
            message_server.send_message(ws_config.GROUP_CHAT, int(context_type), int(sender), sender_name,
                                 int(group_id), receiver, receiver_name, context)
    except Exception as e:
        print(datetime.now(), f"chat: An unexpected error occurred: {e}, param = ", json_data, traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '消息发送失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '消息发送成功'
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
        message_server.send_notification_message(int(context_type), int(cur_user_id), cur_user_name, int(receiver), context)
    except Exception as e:
        print(datetime.now(), f"chat: An unexpected error occurred: {e}, param = ", json_data, traceback.print_exc())
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
        group = message_server.create_group(group_name, creator, creator_name, members)
    except Exception as e:
        print(datetime.now(), f"create_chat_group: {e}, param = ", json_data, traceback.print_exc())
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
        group = message_server.query_group(group_id)
    except Exception as e:
        print(datetime.now(), f"query_group: {e}, param = ", json_data, traceback.print_exc())
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
        message_server.update_group(int(group_id), group_name, members)
    except Exception as e:
        print(datetime.now(), f"update_group: {e}, param = ", json_data, traceback.print_exc())
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
    group_name = json_data.get("group_name")
    user_id = json_data.get("user_id")
    user_name = json_data.get("user_name")
    confirm = json_data.get("confirm")

    try:
        message_server.confirm_join_group(int(group_id), group_name, int(user_id), user_name, int(confirm))
    except Exception as e:
        print(datetime.now(), f"search_group: {e}, param = ", json_data, traceback.print_exc())
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


@message_router.route('/test', methods=['GET', "POST"])
def socket_test():
    cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_server.push({
                    "type": 400,
                    "data": {
                        "message": {
                            "chat_type": 0,
                            "context_type": 10,
                            "sender": 0,
                            "sender_name": "系统",
                            "group_id": None,
                            "receiver": 9640,
                            "receiver_name": "胡海波",
                            "context": {
                                "type": 72,
                                "title": "院感消息",
                                "description": "222222222222",
                                "process_id": 11527,
                                "action": 1,
                                "url": "http: //oa.nsyy.com.cn:6060/?type=15&process_id=11527&action=1",
                                "time": cur_time
                            },
                            "timer": cur_time
                        }
                    }
                }, 9640)
    return "push ok"


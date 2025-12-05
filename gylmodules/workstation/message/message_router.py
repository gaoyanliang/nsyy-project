from flask import Blueprint, jsonify, request

from gylmodules import global_tools
from gylmodules.global_tools import api_response
from gylmodules.workstation import ws_config
from gylmodules.workstation.message import message_server, msg_push_tool
import json
from datetime import datetime

message_router = Blueprint('message router', __name__, url_prefix='/msg')


#  发送聊天消息
@message_router.route('/chat', methods=['POST'])
@api_response
def chat(json_data):
    context_type = json_data.get("context_type")
    sender = json_data.get("sender")
    sender_name = json_data.get("sender_name")
    group_id = json_data.get("group_id")
    receiver = json_data.get("receiver")
    receiver_name = json_data.get("receiver_name")

    # TODO image context_type=2  文件 context——type = 3  /video/audio/link 特殊处理 ，现在只处理 text
    # TODO 如果是多媒体类型，需要先调用上传接口，获取到存储地址
    context = json_data.get("context")

    if group_id is None:
        message_server.send_message(ws_config.PRIVATE_CHAT, int(context_type), int(sender), sender_name,
                             None, receiver, receiver_name, context)
    else:
        message_server.send_message(ws_config.GROUP_CHAT, int(context_type), int(sender), sender_name,
                             int(group_id), receiver, receiver_name, context)


#  发送通知消息
@message_router.route('/notification', methods=['POST'])
@api_response
def notification(json_data):
    context_type = json_data.get("context_type")
    cur_user_id = json_data.get('cur_user_id')
    cur_user_name = json_data.get('cur_user_name')

    receivers = json_data.get("receivers", [])

    # TODO image/video/audio/link 特殊处理 ，现在只处理 text
    # TODO 如果是多媒体类型，需要先调用上传接口，获取到存储地址
    context = json_data.get("context")
    if type(context) == dict:
        context = json.dumps(context, default=str)
    if len(receivers) == 1:
        message_server.send_notification_message(int(context_type), int(cur_user_id), cur_user_name,
                                                 int(receivers[0].get('user_id')), receivers[0].get('user_name'),
                                                 context)
    else:
        message_server.batch_send_notification_message(int(context_type), int(cur_user_id),
                                                       cur_user_name, receivers, context)


#  ==========================================================================================
#  ==========================     群组管理      ==============================================
#  ==========================================================================================


#  创建群聊
@message_router.route('/create_group', methods=['POST'])
@api_response
def create_group(json_data):
    return message_server.create_group(json_data.get("group_name"), json_data.get("creator"),
                                       json_data.get("creator_name"), json_data.get("members"))


@message_router.route('/query_group', methods=['POST'])
@api_response
def query_group(json_data):
    return message_server.query_group(json_data.get("group_id"))


@message_router.route('/query_groups', methods=['POST'])
@api_response
def query_groups(json_data):
    return message_server.query_groups(json_data.get("user_id"))


#  群名称更新
@message_router.route('/update_group', methods=['POST'])
@api_response
def update_group(json_data):
    group_id = json_data.get("group_id")
    members = json_data.get('members') if json_data.get('members') else []
    message_server.update_group(int(group_id), json_data.get("group_name"), members)


#  确认加入群聊
@message_router.route('/confirm_join_group', methods=['POST'])
@api_response
def confirm_join_group(json_data):
    group_id = json_data.get("group_id")
    user_id = json_data.get("user_id")
    confirm = json_data.get("confirm")
    message_server.confirm_join_group(int(group_id), json_data.get("group_name"), int(user_id),
                                      json_data.get("user_name"), int(confirm))


# 存储用户手机信息 token pers——id brand
@message_router.route('/save_phone_info', methods=['POST'])
@api_response
def save_phone_info(json_data):
    message_server.save_phone_info(json_data)


#  推送消息给设备
@message_router.route('/push_msg_to_devices', methods=['POST'])
@api_response
def push_msg_to_devices(json_data):
    return msg_push_tool.push_msg_to_devices(json_data.get('pers_id'), json_data.get('title'), json_data.get('body'))


@message_router.route('/test', methods=['GET', "POST"])
def socket_test():
    cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    global_tools.socket_push("消息推送", {
        "socketd": ["m_app", "m_user"], "type": 400, 'pers_id': [9640],
        'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "socket_data": {"chat_type": 0, "context_type": 10, "sender": 0, "sender_name": "系统",
                            "group_id": None, "receiver": 9640, "receiver_name": "胡海波",
                            "context": {
                                "type": 72, "title": "院感消息", "description": "222222222222",
                                "process_id": 11527, "action": 1,
                                "url": "http: //oa.nsyy.com.cn:6060/?type=15&process_id=11527&action=1",
                                "time": cur_time
                            },
                            "timer": cur_time
                        }})
    return "push ok"


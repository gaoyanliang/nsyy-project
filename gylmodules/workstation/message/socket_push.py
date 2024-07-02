from gylmodules import global_config
import requests
import json

# 测试环境：
# 192.168.124.53:6080/inter_socket_msg
# json格式
# msg_list: [{socket_data: {}, pers_id: 123,}]


# 正式环境：
# from tools import socket_send
# socket_send(socket_data, 'm_user', pers_id)

# 消息推送 type = 100


def push(socket_data: dict, user_id: int):
    print('向用户 ' + str(user_id) + ' 推送消息: ' + json.dumps(socket_data, default=str))

    # 测试环境
    # 要发送的数据
    data = {'msg_list': [{'socket_data': socket_data, 'pers_id': user_id}]}
    # 设置请求头
    headers = {'Content-Type': 'application/json'}
    # 发送POST请求
    response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
    # 打印响应内容
    print("Socket Push Status: ", response.status_code)
    print("Socket Push Response: ", response.text)

# push("test", 100)
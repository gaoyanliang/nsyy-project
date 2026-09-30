from flask import Blueprint

from gylmodules.global_tools import api_response
from gylmodules.group import group_server

group_router = Blueprint('group router', __name__, url_prefix='/group')


#  创建群组
@group_router.route('/create', methods=['POST'])
@api_response
def create_group(json_data):
    return group_server.create_group(json_data.get('group_name', ''), json_data.get('owner_id', ''),
                                     json_data.get('owner_name', ''), json_data.get('members', []),
                                     json_data.get('description', ''), json_data.get('user_mail_account', ''),
                                     json_data.get('is_public', 1))


# 更新群组
@group_router.route('/update', methods=['POST'])
@api_response
def update_group(json_data):
    group_server.update_group(json_data.get('group_id', ''), json_data.get('group_name', ''),
                              json_data.get('description', ''), json_data.get('is_public'),
                              json_data.get('user_id', ''), json_data.get('members', []))


# 解散群组
@group_router.route('/disband', methods=['POST'])
@api_response
def disband_group(json_data):
    group_server.disband_group(json_data.get('group_id', ''), json_data.get('user_id', ''))


# 查询群组信息
@group_router.route('/query_group', methods=['GET', 'POST'])
@api_response
def query_group_info(json_data):
    return group_server.query_group(json_data.get('group_id', ''))


# 查询用户群组
@group_router.route('/query_user_groups', methods=['GET', 'POST'])
@api_response
def query_user_group(json_data):
    return group_server.query_user_group(json_data.get('user_id', ''))


#  确认加入群组
@group_router.route('/confirm', methods=['POST'])
@api_response
def confirm_join_group(json_data):
    group_server.confirm_join_group(json_data.get('group_id', ''), json_data.get('user_id', ''),
                                    json_data.get('user_name', ''), json_data.get('confirm', ''))





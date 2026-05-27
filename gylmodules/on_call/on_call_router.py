from flask import Blueprint, jsonify

from gylmodules import global_tools
from gylmodules.global_tools import api_response
from gylmodules.on_call import on_call_server, on_call_config
from gylmodules.shift_change import shift_change_server

on_call = Blueprint('on call', __name__, url_prefix='/on_call')

@on_call.route('/')
def index():
    """主页"""
    from flask import render_template
    return render_template('index.html')


@on_call.route('/shift_types', methods=['GET'])
@api_response
def get_shift_types():
    return on_call_config.SHIFT_TYPE_MAPPING

@on_call.route('/cache', methods=['GET'])
@api_response
def cache():
    return global_tools.fetch_doctor()


@on_call.route('/doctors', methods=['GET'])
@api_response
def get_all_doctors():
    return on_call_server.get_all_doctors()

@on_call.route('/depts', methods=['GET'])
@api_response
def get_all_depts():
    return shift_change_server.dept_list(1)


# ==================== 今日值班接口 ====================

@on_call.route('/duty/today', methods=['GET'])
def get_today_duty():
    """获取今日值班信息"""
    return on_call_server.get_today_duty()


# ==================== 急诊通知接口 ====================

"""一键通知 - 创建会诊群"""
@on_call.route('/notification/emergency', methods=['POST'])
@api_response
def emergency_notification(json_data):
    on_call_server.emergency_notification(json_data)


"""获取会诊群列表"""
@on_call.route('/notification/records', methods=['POST', "GET"])
@api_response
def get_consultation_groups(json_data):
    return on_call_server.get_consultation_groups(json_data)


"""获取会诊群详情"""
@on_call.route('/notification/record/detail', methods=['POST', 'GET'])
@api_response
def get_consultation_detail(json_data):
    return on_call_server.get_consultation_detail(json_data)


"""发送消息到会诊群"""
@on_call.route('/notification/record/message', methods=['POST'])
@api_response
def send_message(json_data):
    on_call_server.record_message(json_data)

@on_call.route('/record/message', methods=['POST'])
@api_response
def query_message(json_data):
    return on_call_server.query_record_message(json_data)

# ==================== 排班管理接口 ====================

"""获取排班列表"""
@on_call.route('/schedules', methods=['GET', 'POST'])
@api_response
def get_schedules(json_data):
    return on_call_server.get_schedules(json_data)


"""新增值班"""
@on_call.route('/new_schedules', methods=['POST'])
@api_response
def create_schedule(json_data):
    on_call_server.create_schedule(json_data)


"""更新值班"""
@on_call.route('/update_schedules', methods=['POST'])
@api_response
def update_schedules(json_data):
    on_call_server.update_schedule(json_data)


"""删除排班"""
@on_call.route('/schedules/', methods=['DELETE'])
@api_response
def delete_schedule(json_data):
    on_call_server.delete_schedule(json_data.get('id'))


"""复制排班"""
@on_call.route('/schedules/copy', methods=['POST'])
@api_response
def copy_schedules(json_data):
    on_call_server.copy_schedules(json_data)


@on_call.route('/schedules/copy_doctor', methods=['POST'])
@api_response
def copy_doctor_schedules(json_data):
    on_call_server.copy_doctor_schedules(json_data)


"""批量删除排班"""
@on_call.route('/schedules/batch_delete', methods=['POST'])
@api_response
def batch_delete_schedules(json_data):
    on_call_server.batch_delete_schedules(json_data)

"""批量修改班次"""
@on_call.route('/schedules/batch_update', methods=['POST'])
@api_response
def batch_update_schedules(json_data):
    on_call_server.batch_update_schedules(json_data)

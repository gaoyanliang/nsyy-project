import json
import traceback

from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.composite_appointment import composite_appointment as appointment

appt = Blueprint('composite appointment', __name__, url_prefix='/appt')


"""
线上预约
"""


@appt.route('/wx_appt', methods=['POST'])
def wx_appt():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        id_card_no = json_data.get('id_card_no')
        openid = json_data.get('openid')
        appt_name = json_data.get('appt_name')
        if not id_card_no or not openid or not appt_name:
            return jsonify({
                'code': 50000,
                'res': '缺失关键信息, 用户名, 身份证号, openid 不能为空',
            })
        appointment.online_appt(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
    })


"""
线下预约（现场预约）
"""


@appt.route('/offline_appt', methods=['POST'])
def offline_appt():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        id_card_no = json_data.get('id_card_no')
        appt_name = json_data.get('appt_name')
        if not id_card_no or not appt_name:
            return jsonify({
                'code': 50000,
                'res': '缺失关键信息, 用户名, 身份证号 不能为空',
            })
        appointment.offline_appt(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
    })


"""
预约记录查询
"""


@appt.route('/query_appt', methods=['POST'])
def query_appt():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        appts, total = appointment.query_appt(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })
    return jsonify({
        'code': 20000,
        'data': {
            'appts': appts,
            'total': total
        }
    })


"""
操作预约
"""


@appt.route('/op_appt', methods=['POST'])
def cancel_appt():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        appointment.operate_appt(int(json_data.get('appt_id')), int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })
    return jsonify({
        'code': 20000,
    })


"""
预约签到
"""


@appt.route('/sign_in', methods=['POST'])
def sign_in():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        appointment.sign_in(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
    })


"""
查询所有预约项目
"""


@appt.route('/query_projs', methods=['GET', 'POST'])
def get_all_project():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        projectl = appointment.query_all_appt_project(int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': projectl
    })


"""
查询诊室/大厅列表
"""


@appt.route('/query_room_list', methods=['GET', 'POST'])
def query_room_list():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        room_list = appointment.query_room_list(int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': room_list
    })


"""
查询诊室/大厅列表
"""


@appt.route('/query_wait_list', methods=['GET', 'POST'])
def query_wait_list():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        wait_list = appointment.query_wait_list(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': wait_list
    })


"""
下一个
"""


@appt.route('/next', methods=['POST'])
def next_num():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data_list = appointment.next_num(int(json_data.get('id')), int(json_data.get('is_group')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data_list
    })


"""
语音播报
"""


@appt.route('/call', methods=['POST'])
def call_patient():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        appointment.call(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })







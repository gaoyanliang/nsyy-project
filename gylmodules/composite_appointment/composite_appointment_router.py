import json
import traceback

from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.composite_appointment import ca_server as ca_server

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
        patient_name = json_data.get('patient_name')
        patient_id = json_data.get('patient_id')
        if not id_card_no or not openid or not patient_name or not patient_id:
            return jsonify({
                'code': 50000,
                'res': '缺失关键信息： 预约人姓名, 身份证号, openid, patient_id 不能为空',
            })
        ca_server.online_appt(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", 'param: ', json_data)
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
        patient_id = json_data.get('patient_id')
        patient_name = json_data.get('patient_name')
        if not id_card_no or not patient_name or not patient_id:
            return jsonify({
                'code': 50000,
                'res': '缺失关键信息, 患者姓名, 就诊号, 身份证号 不能为空',
            })
        ca_server.offline_appt(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", 'param: ', json_data)
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
        appts, total = ca_server.query_appt_record(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", "param: ", json_data)
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
def op_appt():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.operate_appt(int(json_data.get('appt_id')), int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", " param: ", json_data)
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
        ca_server.sign_in(json_data, over_num=False)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", " param: ", json_data)
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
        projectl = ca_server.query_all_appt_project(int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
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
        room_list = ca_server.query_room_list(int(json_data.get('type')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", " param: ", request.get_data().decode('utf-8'))
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': room_list
    })


"""
查询诊室/大厅 等待列表
"""


@appt.route('/query_wait_list', methods=['GET', 'POST'])
def query_wait_list():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        wait_list, doctor, proj = ca_server.query_wait_list(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': {
            'wait_list': wait_list,
            'doctor': doctor,
            'proj': proj
        }
    })


"""
下一个
"""


@appt.route('/next', methods=['POST'])
def next_num():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data_list = ca_server.next_num(int(json_data.get('id')), int(json_data.get('is_group')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", " param: ", json_data)
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
        ca_server.call(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


"""
查询医嘱
"""


@appt.route('/query_advice', methods=['POST'])
def query_advice_by_father_appt_id():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        advice_info = ca_server.query_advice_by_father_appt_id(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': advice_info
    })


"""
更新医嘱付款状态
"""


@appt.route('/update_advice_pay_state', methods=['POST'])
def update_doctor_advice_pay_state():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_doctor_advice_pay_state(json_data.get('idl'))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


"""
更新医嘱
"""


@appt.route('/update_advice', methods=['POST'])
def update_advice():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_advice(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


"""
查询排班信息
"""


@appt.route('/query_sched', methods=['POST'])
def query_sched():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = ca_server.query_sched(int(json_data.get('rid')))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data
    })


"""
更新排班信息
"""


@appt.route('/update_sched', methods=['POST'])
def update_sched():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_sched(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


@appt.route('/query_doc', methods=['POST'])
def query_doc():
    try:
        data = ca_server.query_doc()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data
    })


@appt.route('/update_doc', methods=['POST'])
def update_doc():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_doc(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
    })


@appt.route('/query_proj_list', methods=['POST'])
def query_proj():
    try:
        data = ca_server.query_proj()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data
    })


"""
供定时任务调用，每天凌晨更新最近七天的可预约数量
"""


@appt.route('/update_capacity', methods=['POST'])
def update_capacity():
    try:
        ca_server.cache_capacity()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


@appt.route('/query_mem_data', methods=['POST'])
def query_mem_data():
    try:
        data = ca_server.query_mem_data()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data
    })


@appt.route('/change_room', methods=['POST'])
def change_room():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.change_room(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


@appt.route('/update_sort', methods=['POST'])
def update_sort():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_wait_list_sort(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


@appt.route('/update_sort_info', methods=['POST'])
def update_sort_info():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_sort_info(int(json_data.get('appt_id')), json_data.get('sort_info'))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


"""
住院患者创建医嘱
"""


@appt.route('/inpatient_advice', methods=['POST'])
def inpatient_advice():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = ca_server.inpatient_advice(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
        'data': data
    })


@appt.route('/inpatient_advice_create', methods=['POST'])
def inpatient_advice_create():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.inpatient_advice_create(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })


@appt.route('/update_or_insert_proj', methods=['POST'])
def update_or_insert_proj():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ca_server.update_or_insert_project(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000
    })

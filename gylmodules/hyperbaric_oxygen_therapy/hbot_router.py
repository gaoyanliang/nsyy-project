import json

from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.hyperbaric_oxygen_therapy import hbot_server

hbot = Blueprint('hyperbaric oxygen therapy', __name__, url_prefix='/hbot')


"""
根据住院号查询病人信息
"""


@hbot.route('/query_patient_info', methods=['POST'])
def query_patient_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = hbot_server.query_patient_info(json_data.get('patient_type'),
                                                      json_data.get('patient_id'), json_data.get('comp_type'))
    except Exception as e:
        print(datetime.now(), "query_patient_info exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "住院患者病人信息查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': patient_info
    })


"""
高压氧治疗登记
"""


@hbot.route('/register', methods=['POST'])
def hbot_register():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.register(json_data)
    except Exception as e:
        print(datetime.now(), "hbot_register exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧治疗登记异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'register successes',
    })


@hbot.route('/query_register_record', methods=['GET', 'POST'])
def query_register_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        register_records = hbot_server.query_register_record(json_data)
    except Exception as e:
        print(datetime.now(), "query_register_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧登记记录查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': register_records
    })


@hbot.route('/update_register_start_time', methods=['POST'])
def update_register_start_time():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.update_register_start_time(json_data)
    except Exception as e:
        print(datetime.now(), "update_register_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "更新开始时间异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'update successes'
    })


@hbot.route('/query_treatment_record', methods=['GET', 'POST'])
def query_treatment_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        treatment_records, total, pending, implemented, canceled = hbot_server.query_treatment_record(json_data)
    except Exception as e:
        print(datetime.now(), "query_treatment_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧治疗记录查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': treatment_records,
        'total': total,
        'pending': pending,
        'implemented': implemented,
        'canceled': canceled
    })


@hbot.route('/update_register_record', methods=['POST', 'PUT'])
def update_register_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.update_register_record(json_data)
    except Exception as e:
        print(datetime.now(), "update_register_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧登记记录更新异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'update successes'
    })


@hbot.route('/update_treatment_record', methods=['POST', 'PUT'])
def update_treatment_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.update_treatment_record(json_data)
    except Exception as e:
        print(datetime.now(), "update_treatment_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧治疗记录更新异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'update successes'
    })


@hbot.route('/refresh_medical_status', methods=['POST'])
def refresh_medical_status():
    try:
        hbot_server.hbot_run_everyday()
    except Exception as e:
        return jsonify({
            'code': 50000,
            'res': "刷新医嘱状态异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'refresh medical status successes'
    })


@hbot.route('/sign', methods=['POST'])
def update_sign_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.update_sign_info(json_data)
    except Exception as e:
        print(datetime.now(), "update_sign_info exception:  param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "更新前面异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'sign successes'
    })


@hbot.route('/hbot_charge', methods=['POST'])
def hbot_charge():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.hbot_charge(json_data)
    except Exception as e:
        print(datetime.now(), "hbot_charge exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'charge successes'
    })


@hbot.route('/data_statistics', methods=['POST', 'GET'])
def data_statistics():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        people_total, price_total = hbot_server.data_statistics(json_data)
    except Exception as e:
        print(datetime.now(), "data_statistics exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "工作量统计数据查询失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'people_total': people_total,
        "price_total": price_total
    })


@hbot.route('/save_sign_info', methods=['POST'])
def save_doc_sign_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = hbot_server.save_sign_info(json_data)
    except Exception as e:
        print(datetime.now(), "save_doc_sign_info exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "医生签名信息保存失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'doc sign info save successes',
        'biz_sn': data
    })


@hbot.route('/save_pdf', methods=['POST'])
def save_pdf():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = hbot_server.save_pdf(json_data)
    except Exception as e:
        print(datetime.now(), "save_pdf exception: ", e)
        return jsonify({
            'code': 50000,
            'res': "签名 pdf 保存失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'sign pdf save successes'
    })


@hbot.route('/query_sign_ret', methods=['POST', 'GET'])
def query_sign_ret():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = hbot_server.query_sign_ret(json_data)
    except Exception as e:
        print(datetime.now(), "query_sign_ret exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "签名结果查询失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'sign ret query successes',
        'data': data
    })


@hbot.route('/query_sign_img', methods=['POST', 'GET'])
def query_sign_img():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = hbot_server.query_sign_ret(json_data, is_query_sign_img=True)
    except Exception as e:
        print(datetime.now(), "query_sign_img exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "签名图片查询失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'sign ret query successes',
        'data': data
    })


@hbot.route('/sign_first_evaluation', methods=['POST', 'GET'])
def sign_first_evaluation():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        data = hbot_server.sign_first_evaluation(json_data)
    except Exception as e:
        print(datetime.now(), "sign_first_evaluation exception: param = ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "首次评估签名失败: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'first evaluation sign successes'
    })



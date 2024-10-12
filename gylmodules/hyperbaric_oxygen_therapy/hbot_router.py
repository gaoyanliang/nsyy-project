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
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = hbot_server.query_patient_info(json_data.get('patient_type'), json_data.get('patient_id'))
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
        register_records = hbot_server.query_register_record(json_data.get('query_type'), json_data.get('key'))
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


@hbot.route('/query_treatment_record', methods=['GET', 'POST'])
def query_treatment_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        treatment_records = hbot_server.query_treatment_record(json_data)
    except Exception as e:
        print(datetime.now(), "query_treatment_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "高压氧治疗记录查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': treatment_records
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
        print(datetime.now(), "hbot_run_everyday exception: ", e)
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
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        hbot_server.update_sign_info(json_data)
    except Exception as e:
        print(datetime.now(), "update_sign_info exception: ", e)
        return jsonify({
            'code': 50000,
            'res': "更新前面异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'sign successes'
    })

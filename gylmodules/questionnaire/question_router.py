import json

from datetime import datetime

from flask import Blueprint, jsonify, request

from gylmodules.questionnaire import question_server, question_config

question = Blueprint('question survey', __name__, url_prefix='/question')


"""
根据就诊卡/身份证号 查询病人信息
"""


@question.route('/query_patient_info', methods=['POST', 'GET'])
def query_patient_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = question_server.query_patient_info(json_data.get('card_no'))
    except Exception as e:
        print(datetime.now(), "query_patient_info exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "病人信息查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': patient_info
    })


@question.route('/create_patient_info', methods=['POST', 'GET'])
def create_patient_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = question_server.create_patient_info(json_data)
    except Exception as e:
        print(datetime.now(), "create_patient_info exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "病人信息创建异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'create & query successes',
        'data': patient_info
    })


"""
查询问题模版类型
"""


@question.route('/query_tpl_list', methods=['POST', 'GET'])
def query_tpl_list():
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': question_config.tpl_list
    })


"""
查询问题列表
"""


@question.route('/query_question_list', methods=['POST', 'GET'])
def query_question_list():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        questions = question_server.query_question_list(json_data)
    except Exception as e:
        print(datetime.now(), "query_question_list exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问题列表查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': questions
    })


"""
问卷调查结果写入
"""


@question.route('/question_survey_ans', methods=['POST'])
def question_survey_ans():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        questions = question_server.question_survey_ans(json_data)
    except Exception as e:
        print(datetime.now(), "question_survey_ans exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果写入异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'question survey successes',
    })


"""
更新问卷调查
"""


@question.route('/update_question_survey_ans', methods=['POST'])
def update_question_survey_ans():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        questions = question_server.update_question_survey_ans(json_data)
    except Exception as e:
        print(datetime.now(), "update_question_survey_ans exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果更新异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'update question survey successes',
    })


"""
查询问卷调查结果
"""


@question.route('/query_question_survey', methods=['POST', 'GET'])
def query_question_survey():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        question_surveys = question_server.query_question_survey(json_data)
    except Exception as e:
        print(datetime.now(), "query_question_survey exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'question survey query successes',
        'data': question_surveys
    })


@question.route('/query_question_survey_by_id', methods=['POST', 'GET'])
def query_question_survey_byid():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        question_surveys = question_server.query_question_survey_by_patient_id(json_data.get('patient_id'))
    except Exception as e:
        print(datetime.now(), "query_question_survey exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果查询(根据病人 id)异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'question survey query successes',
        'data': question_surveys
    })


"""
查询问卷调查结果
"""


@question.route('/view_medical_records', methods=['POST', 'GET'])
def view_medical_records():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        medical_records = question_server.view_medical_records(json_data.get('qid'))
    except Exception as e:
        print(datetime.now(), "view_medical_records exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "门诊病历查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'view medical records successes',
        'data': medical_records
    })


"""
删除问卷
"""


@question.route('/delete_question_survey', methods=['POST', 'DELETE'])
def delete_question_survey():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        question_server.delete_question_survey(json_data.get('qid'))
    except Exception as e:
        print(datetime.now(), "delete_question_survey exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "门诊病历查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'delete successes'
    })




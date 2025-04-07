import json

from datetime import datetime

from flask import Blueprint, jsonify, request

from gylmodules.questionnaire import sq_server

question = Blueprint('question survey', __name__, url_prefix='/question')


"""
根据就诊卡/身份证号 查询病人信息
"""


@question.route('/query_patient_info', methods=['POST', 'GET'])
def query_patient_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = sq_server.query_patient_info(json_data.get('card_no'))
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


"""
登记病人信息
"""


@question.route('/create_patient_info', methods=['POST'])
def create_patient_info():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info = sq_server.create_patient_info(json_data)
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
    try:
        surveys = sq_server.query_tpl_list()
    except Exception as e:
        print(datetime.now(), "create_patient_info exception ", e)
        return jsonify({
            'code': 50000,
            'res': "查询问题模版类型异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': surveys
    })


"""
查询问题列表
"""


@question.route('/query_question_list', methods=['POST', 'GET'])
def query_question_list():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        questions, hist_answer_list = sq_server.query_question_list(json_data.get('su_id'), json_data.get('card_no'))
    except Exception as e:
        print(datetime.now(), "query_question_list exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问题列表查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': questions,
        'hist_answer_list': hist_answer_list
    })


"""
问卷调查结果写入
"""


@question.route('/submit_survey_record', methods=['POST'])
def submit_survey_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        re_id = sq_server.submit_survey_record(json_data)
    except Exception as e:
        print(datetime.now(), "submit_survey_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果写入异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'submit_survey_record successes',
        'data': re_id
    })


"""
更新问卷调查
"""


@question.route('/update_survey_record', methods=['POST'])
def update_survey_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        questions = sq_server.update_survey_record(json_data)
    except Exception as e:
        print(datetime.now(), "update_survey_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果更新异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'update_survey_record successes',
    })


"""
查询问卷调查结果
"""


@question.route('/query_question_survey', methods=['POST', 'GET'])
def query_question_survey():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        if json_data.get('re_id'):
            survey_record, answer_list, test_results, examination_result = \
                sq_server.query_hist_questionnaires_details(json_data)
            data = {
                "survey_record": survey_record,
                "answer_list": answer_list,
                "test_results": test_results,
                "examination_result": examination_result,
            }
        else:
            data = sq_server.query_hist_questionnaires_list(json_data)

    except Exception as e:
        print(datetime.now(), "query_question_survey exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'survey query successes',
        'data': data
    })


"""
查看门诊病历
"""


@question.route('/view_medical_records', methods=['POST', 'GET'])
def view_medical_records():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        patient_info, medical_data, answer_list = sq_server.query_outpatient_medical_record(json_data.get('re_id'))
        # patient_info, medical_data = sq_server.query_outpatient_medical_record(json_data.get('re_id'))
    except Exception as e:
        print(datetime.now(), "view_medical_records exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "门诊病历查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'view medical records successes',
        # 'data': {
        #     "patient_info": patient_info,
        #     "medical_data": medical_data
        # }
        'data': {
            "patient_info": patient_info,
            "medical_data": medical_data,
            "answer_list": answer_list
        }
    })


"""
删除问卷
"""


@question.route('/delete_question_survey', methods=['POST', 'DELETE'])
def delete_question_survey():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        sq_server.delete_question_survey(json_data.get('re_id'))
    except Exception as e:
        print(datetime.now(), "delete_question_survey exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': f"问卷 {json_data.get('re_id')} 删除异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'delete successes'
    })


"""
查询问卷报表
"""


@question.route('/query_operator_report', methods=['POST', 'GET'])
def query_operator_report():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        report = sq_server.query_report(json_data)
    except Exception as e:
        print(datetime.now(), "query_operator_report exception param:", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "统计报表查询异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'query successes',
        'data': report
    })


"""
his 查询问卷列表
"""


@question.route('/query_question_survey_by_id', methods=['POST', 'GET'])
def query_question_survey_byid():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        question_surveys = sq_server.query_question_survey_by_patient_id(json_data.get('patient_id'))
    except Exception as e:
        print(datetime.now(), "query_question_survey_by_patient_id exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "问卷调查结果查询(根据病人 id)异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'question survey query successes',
        'data': question_surveys
    })


@question.route('/submit_medical_record', methods=['POST', 'GET'])
def submit_medical_record():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        question_surveys = sq_server.submit_medical_record(json_data)
    except Exception as e:
        print(datetime.now(), "submit_medical_record exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "病历提交异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        'res': 'submit medical record successes'
    })


@question.route('/patient_quest_details', methods=['POST', 'GET'])
def patient_quest_details():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ques_dtl = sq_server.patient_quest_details(json_data)
    except Exception as e:
        print(datetime.now(), "patient_quest_details exception, param: ", json_data, e)
        return jsonify({
            'code': 50000,
            'res': "患者门诊问卷详情查询异常: " + e.__str__()
        })
    return jsonify(ques_dtl)




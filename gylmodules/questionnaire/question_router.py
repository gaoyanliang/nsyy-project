import json
from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response
from gylmodules.questionnaire import sq_server

question = Blueprint('question survey', __name__, url_prefix='/question')


"""
根据就诊卡/身份证号 查询病人信息
"""


@question.route('/query_patient_info', methods=['POST', 'GET'])
@api_response
def query_patient_info(json_data):
    return sq_server.query_patient_info(json_data.get('card_no'))


"""
登记病人信息
"""


@question.route('/create_patient_info', methods=['POST'])
@api_response
def create_patient_info(json_data):
    return sq_server.create_patient_info(json_data)


"""
查询问题模版类型
"""


@question.route('/query_tpl_list', methods=['POST', 'GET'])
@api_response
def query_tpl_list():
    return sq_server.query_tpl_list()


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
@api_response
def submit_survey_record(json_data):
    return sq_server.submit_survey_record(json_data)


"""
更新问卷调查
"""


@question.route('/update_survey_record', methods=['POST'])
@api_response
def update_survey_record(json_data):
    sq_server.update_survey_record(json_data)


"""
查询问卷调查结果
"""


@question.route('/query_question_survey', methods=['POST', 'GET'])
@api_response
def query_question_survey(json_data):
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
    return data


"""
查看门诊病历
"""


@question.route('/view_medical_records', methods=['POST', 'GET'])
@api_response
def view_medical_records(json_data):
    patient_info, medical_data, answer_list = sq_server.query_outpatient_medical_record(json_data.get('re_id'))
    return {"patient_info": patient_info, "medical_data": medical_data, "answer_list": answer_list}


"""
删除问卷
"""


@question.route('/delete_question_survey', methods=['POST', 'DELETE'])
@api_response
def delete_question_survey(json_data):
    sq_server.delete_question_survey(json_data.get('re_id'))


"""
查询问卷报表
"""


@question.route('/query_operator_report', methods=['POST', 'GET'])
@api_response
def query_operator_report(json_data):
    return sq_server.query_report(json_data)


"""
his 查询问卷列表
"""


@question.route('/query_question_survey_by_id', methods=['POST', 'GET'])
@api_response
def query_question_survey_byid(json_data):
    return sq_server.query_question_survey_by_patient_id(json_data.get('patient_id'))


@question.route('/submit_medical_record', methods=['POST', 'GET'])
@api_response
def submit_medical_record(json_data):
    sq_server.submit_medical_record(json_data)


@question.route('/patient_quest_details', methods=['POST', 'GET'])
def patient_quest_details():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        ques_dtl = sq_server.patient_quest_details(json_data)
    except Exception as e:
        return jsonify({
            'code': 50000,
            'res': "患者门诊问卷详情查询异常: " + e.__str__()
        })
    return jsonify(ques_dtl)




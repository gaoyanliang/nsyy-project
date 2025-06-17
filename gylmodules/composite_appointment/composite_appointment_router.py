import json
import logging

from flask import Blueprint, jsonify, request

from gylmodules.composite_appointment import ca_server, sched_manage, update_doc_scheduling
from gylmodules.global_tools import api_response

appt = Blueprint('composite appointment', __name__, url_prefix='/appt')
logger = logging.getLogger(__name__)


@appt.route('/wx_appt', methods=['POST'])
@api_response
def wx_appt(json_data):
    logger.info(f'微信小程序预约记录创建： {json_data}')

    id_card_no = json_data.get('id_card_no')
    openid = json_data.get('openid')
    patient_name = json_data.get('patient_name')
    patient_id = json_data.get('patient_id')
    if not id_card_no or not openid or not patient_name or not patient_id:
        raise Exception('缺失关键信息： 预约人姓名, 身份证号, openid, patient_id 不能为空')
    ca_server.online_appt(json_data)


"""
预约记录查询
"""


@appt.route('/query_appt', methods=['POST'])
@api_response
def query_appt(json_data):
    appts, total = ca_server.query_appt_record(json_data)
    return {'appts': appts, 'total': total}


"""
操作预约
"""


@appt.route('/op_appt', methods=['POST'])
@api_response
def op_appt(json_data):
    ca_server.operate_appt(int(json_data.get('appt_id')), int(json_data.get('type')))


"""
预约签到
"""


@appt.route('/sign_in', methods=['POST'])
@api_response
def sign_in(json_data):
    ca_server.sign_in(json_data)


"""
查询所有预约项目
"""


@appt.route('/query_projs', methods=['GET', 'POST'])
@api_response
def get_all_project(json_data):
    raise Exception('抱歉！ 系统升级中，请先用自助机挂号或诊间挂号，谢谢')
    return ca_server.query_all_appt_project(int(json_data.get('type')), json_data.get('pid'))


@appt.route('/query_today_projs', methods=['GET', 'POST'])
@api_response
def query_today_projs(json_data):
    return ca_server.query_all_appt_project(int(json_data.get('type')), json_data.get('pid'), only_today=True)


"""
查询诊室房间/大厅列表
"""


@appt.route('/query_room_list', methods=['GET', 'POST'])
@api_response
def query_room_list(json_data):
    return ca_server.query_room_list(int(json_data.get('type')))


"""
查询诊室/大厅 等待列表
"""


@appt.route('/query_wait_list', methods=['GET', 'POST'])
@api_response
def query_wait_list(json_data):
    wait_list, doctor, proj = ca_server.query_wait_list(json_data)
    return {'wait_list': wait_list, 'doctor': doctor, 'proj': proj}


"""
下一个
"""


@appt.route('/next', methods=['POST'])
@api_response
def next_num(json_data):
    return ca_server.next_num(int(json_data.get('id')), int(json_data.get('is_group')))


"""
语音播报
"""


@appt.route('/call', methods=['POST'])
@api_response
def call_patient(json_data):
    ca_server.call(json_data)


"""
查询医嘱
"""


@appt.route('/query_advice', methods=['POST'])
@api_response
def query_advice_by_father_appt_id(json_data):
    return ca_server.query_advice_by_father_appt_id(json_data)


"""
更新医嘱付款状态
"""


@appt.route('/update_advice_pay_state', methods=['POST'])
@api_response
def update_doctor_advice_pay_state(json_data):
    ca_server.update_doctor_advice_pay_state(json_data.get('idl'))


"""
更新医嘱
"""


@appt.route('/update_advice', methods=['POST'])
@api_response
def update_advice(json_data):
    ca_server.update_advice(json_data)


@appt.route('/update_doc', methods=['POST'])
@api_response
def update_doc(json_data):
    ca_server.update_doc(json_data)


"""
供定时任务调用，每天凌晨更新最近七天的可预约数量
"""


@appt.route('/update_capacity', methods=['POST'])
@api_response
def update_capacity():
    ca_server.cache_capacity()


@appt.route('/change_room', methods=['POST'])
@api_response
def change_room(json_data):
    ca_server.change_room(json_data)


@appt.route('/update_sort', methods=['POST'])
@api_response
def update_sort(json_data):
    ca_server.update_wait_list_sort(json_data)


@appt.route('/update_sort_info', methods=['POST'])
@api_response
def update_sort_info(json_data):
    ca_server.update_sort_info(int(json_data.get('appt_id')), json_data.get('sort_info'))


@appt.route('/update_or_insert_proj', methods=['POST'])
@api_response
def update_or_insert_proj(json_data):
    ca_server.update_or_insert_project(json_data)


@appt.route('/refund', methods=['POST'])
def refund():
    return jsonify({
        'code': 50000,
        'res': 'OA 退费功能停用，在HIS中退费'
    })


"""
查询科室（项目）信息 & 科室医生列表
"""


@appt.route('/query_proj_info', methods=['GET', 'POST'])
@api_response
def query_proj_info(json_data):
    return sched_manage.query_proj_info(int(json_data.get('type')))


@appt.route('/query_doc_by_empno', methods=['POST', 'GET'])
@api_response
def query_doc_by_empno(json_data):
    return sched_manage.query_doc_bynum_or_name(json_data.get('key'))


@appt.route('/query_doc', methods=['POST', 'GET'])
@api_response
def query_doc():
    return sched_manage.data_list('doctor')


@appt.route('/doc_list', methods=['POST', 'GET'])
@api_response
def doc_list(json_data):
    return sched_manage.data_list('doctor')


@appt.route('/proj_list', methods=['POST', 'GET'])
@api_response
def query_proj():
    return sched_manage.data_list('project')


@appt.route('/room_list', methods=['POST', 'GET'])
@api_response
def room_list():
    return sched_manage.data_list('room')


@appt.route('/query_sched_list', methods=['POST', 'GET'])
@api_response
def query_sched_list(json_data):
    if not json_data.get('start_date') or not json_data.get('end_date'):
        raise Exception('未选择时间范围')
    return sched_manage.get_schedule(json_data.get('start_date'), json_data.get('end_date'),
                                     json_data.get('query_by', 'doctor'), json_data.get('pid'), json_data.get('rid', 0))


@appt.route('/copy_schedule', methods=['POST'])
@api_response
def copy_schedule(json_data):
    if not json_data.get('source_date') or not json_data.get('target_date'):
        raise Exception('source_date or target_date is empty')
    sched_manage.copy_schedule(json_data.get('source_date'), json_data.get('target_date'),
                               json_data.get('pid'), json_data.get('did'), json_data.get('rid'),
                               json_data.get('copy_by'))


@appt.route('/create_schedule', methods=['POST'])
@api_response
def create_schedule(json_data):
    if not json_data.get('did') or not json_data.get('rid') or not json_data.get('pid') \
            or not json_data.get('shift_date') or not json_data.get('shift_type'):
        raise Exception('参数异常')
    sched_manage.create_schedule(json_data.get('did'), json_data.get('rid'), json_data.get('pid'),
                                 json_data.get('shift_date'), json_data.get('shift_type'))


@appt.route('/update_schedule', methods=['POST'])
@api_response
def update_schedule(json_data):
    sched_manage.update_schedule(json_data.get('sid'), json_data.get('new_rid'), json_data.get('new_did'),
                                 json_data.get('new_pid'))


@appt.route('/update_doctor_schedule', methods=['POST'])
@api_response
def update_doctor_schedule(json_data):
    sched_manage.update_doctor_schedule(json_data.get('dsid'), json_data.get('new_status'))


@appt.route('/create_doctor_schedule', methods=['POST', 'GET'])
@api_response
def create_doctor_schedule(json_data):
    sched_manage.create_doctor_schedule(json_data.get('did'),
                                        json_data.get('start_date'), json_data.get('end_date'))


@appt.route('/update_today_doc_info', methods=['POST', 'GET'])
@api_response
def update_today_doc_info():
    update_doc_scheduling.update_today_doc_info()


@appt.route('/today_dept_for_appointment', methods=['POST', 'GET'])
def today_dept_for_appointment():
    try:
        dept_list = sched_manage.query_today_dept_for_appointment()
    except Exception as e:
        logger.error(f"today_dept_for_appointment Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify(dept_list)


@appt.route('/today_doctor_for_appointment', methods=['POST', 'GET'])
def today_doctor_for_appointment():
    json_data = {}
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        doctor_list = sched_manage.query_today_doctor_for_appointment(json_data.get('dept_id'))
    except Exception as e:
        logger.error(f"today_doctor_for_appointment Exception occurred: {e.__str__()}, param: {json_data}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify(doctor_list)


"""
住院患者创建医嘱
"""


@appt.route('/inpatient_advice', methods=['POST'])
def inpatient_advice():
    return jsonify({
        'code': 50000,
        'res': '该功能暂不支持'
    })

    # json_data = None
    # try:
    #     json_data = json.loads(request.get_data().decode('utf-8'))
    #     data = ca_server.inpatient_advice(json_data)
    # except Exception as e:
    #     print(datetime.now(), f"inpatient_advice Exception occurred: {e.__str__()}, param: ", json_data)
    #     return jsonify({
    #         'code': 50000,
    #         'res': e.__str__()
    #     })
    #
    # return jsonify({
    #     'code': 20000,
    #     'data': data
    # })


@appt.route('/inpatient_advice_create', methods=['POST'])
def inpatient_advice_create():
    return jsonify({
        'code': 50000,
        'res': '该功能暂不支持'
    })

    # json_data = None
    # try:
    #     json_data = json.loads(request.get_data().decode('utf-8'))
    #     ca_server.inpatient_advice_create(json_data)
    # except Exception as e:
    #     print(datetime.now(), f"inpatient_advice_create Exception occurred: {e.__str__()}, param: ", json_data)
    #     return jsonify({
    #         'code': 50000,
    #         'res': e.__str__()
    #     })
    #
    # return jsonify({
    #     'code': 20000
    # })


"""
查询排班信息
"""


@appt.route('/query_sched', methods=['POST'])
def query_sched():
    # TODO 待废弃
    return jsonify({
        'code': 50000,
        'res': "以提供新的排班管理工具, 当前功能废弃"
    })


"""
更新排班信息
"""


@appt.route('/update_sched', methods=['POST'])
def update_schedule_old():
    # TODO 待废弃
    return jsonify({
        'code': 50000,
        'res': "以提供新的排班管理工具, 当前功能废弃"
    })


"""
线下预约（现场预约）
"""


@appt.route('/offline_appt', methods=['POST'])
def offline_appt():
    return jsonify({
        'code': 50000,
        'res': '不支持在OA中预约，请在小程序上进行预约',
    })

    # try:
    #     json_data = json.loads(request.get_data().decode('utf-8'))
    #     id_card_no = json_data.get('id_card_no')
    #     patient_id = json_data.get('patient_id')
    #     patient_name = json_data.get('patient_name')
    #     if not id_card_no or not patient_name or not patient_id:
    #         return jsonify({
    #             'code': 50000,
    #             'res': '缺失关键信息, 患者姓名, 就诊号, 身份证号 不能为空',
    #         })
    #     ca_server.offline_appt(json_data)
    # except Exception as e:
    #     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     print(datetime.now(), f"offline_appt Exception occurred: {e.__str__()}", 'param: ', json_data)
    #     return jsonify({
    #         'code': 50000,
    #         'res': e.__str__()
    #     })
    #
    # return jsonify({
    #     'code': 20000,
    # })


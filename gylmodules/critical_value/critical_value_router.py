import json
import traceback

from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.critical_value import critical_value, cv_manage
from gylmodules.global_tools import api_response

cv = Blueprint('critical value', __name__, url_prefix='/cv')


"""
查询运行中的危机值列表
"""


@cv.route('/inner_call_running_cvs', methods=['POST'])
def running_cvs():
    try:
        running_ids, query_sql, systeml = critical_value.get_running_cvs()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] inner_call_running_cvs Exception occurred: {traceback.print_exc()}")
        running_ids = []

    return jsonify({
        'code': 20000,
        'res': '查询运行中的危急值成功',
        'data': {
            'running_ids': running_ids,
            'query_sql': query_sql,
            'systeml': systeml
        }
    })


"""
系统创建危机值
"""


@cv.route('/inner_call_create_cv', methods=['POST'])
@api_response
def system_create_cv1(json_data):
    critical_value.create_cv(json_data.get('cvd'))


@cv.route('/system_create_cv', methods=['POST'])
@api_response
def system_create_cv(json_data):
    critical_value.create_cv_by_system(json_data, json_data.get('cv_source'))


"""
手工上报危急值
"""


@cv.route('/manual_report_cv', methods=['POST'])
def manual_report_cv():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        is_repted, cv_data = critical_value.manual_report_cv(json_data)
        if is_repted:
            # 重复上报 Repeated reporting
            return jsonify({
                'code': 20000,
                "is_repeated": True,
                "data": cv_data
            })
    except Exception as e:
        print(datetime.now(), f"manual_report_cv Exception occurred: ", e)
        return jsonify({
            'code': 50000,
            'res': "手工上报异常: " + e.__str__()
        })
    return jsonify({
        'code': 20000,
        "is_repeated": False
    })


"""
作废危急值
"""


@cv.route('/invalid_cv', methods=['POST'])
@api_response
def invalid_cv(json_data):
    cv_id = json_data.get('cv_id')
    cv_source = json_data.get('cv_source')
    invalid_info = {"invalid_person": json_data.get('invalid_person', ""),
                    "invalid_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "invalid_reason": json_data.get('invalid_reason', "")}
    critical_value.invalid_crisis_value([str(cv_id)], int(cv_source), invalid_info, True)


"""
windows 客户端启动时， 查询所有待完成的危机值，并弹框提示
"""


@cv.route('/query_and_notice', methods=['POST'])
@api_response
def query_process_cv_and_notice(json_data):
    dept_id = json_data.get("dept_id")
    ward_id = json_data.get("ward_id")
    if not dept_id and not ward_id:
        raise Exception('科室id 和 病区id 不能同时为空')
    critical_value.query_process_cv_and_notice(dept_id, ward_id)


"""
查询超时时间
"""


@cv.route('/query_timeout', methods=['GET', 'POST'])
@api_response
def query_timeout():
    return critical_value.query_timeout()


"""
维护站点信息
"""


@cv.route('/operate_site', methods=['POST'])
@api_response
def operate_site(json_data):
    critical_value.site_maintenance(json_data)


# 查询待审核危机值列表

"""
查询危机值列表
"""


@cv.route('/query', methods=['POST'])
@api_response
def query_cv_list(json_data):
    page_number = json_data.get("page_number")
    page_size = json_data.get("page_size")
    if not page_number or not page_size:
        raise Exception('page_number 和 page_size 不能为空')

    cv_list, total = critical_value.get_cv_list(json_data)
    return {'cv_list': cv_list, 'total': total}


"""
推送危机值
"""


@cv.route('/push', methods=['POST'])
@api_response
def push_critical_value(json_data):
    cv_source = json_data.get('cv_source')
    dept_id = json_data.get('dept_id')
    if not cv_source or not dept_id:
        raise Exception('参数异常：危机值来源和科室id不能为空')
    critical_value.push(json_data)


"""
确认接收危机值
"""


@cv.route('/ask_recv', methods=['POST'])
@api_response
def ack_critical_value(json_data):
    critical_value.confirm_receipt_cv(json_data)


"""
书写护理记录
"""


@cv.route('/nursing_record', methods=['POST'])
@api_response
def write_nursing_records(json_data):
    critical_value.nursing_records(json_data)


"""
医生处理危机值
"""


@cv.route('/doctor_handle', methods=['POST'])
@api_response
def handle_critical_value(json_data):
    critical_value.doctor_handle_cv(json_data)


"""
统计报表
"""


@cv.route('/report_form', methods=['POST'])
@api_response
def query_all(json_data):
    return critical_value.report_form(json_data)


"""
病历模版
"""


@cv.route('/template', methods=['POST'])
@api_response
def template(json_data):
    return critical_value.medical_record_template(json_data)


"""
查询危机值上报科室列表
"""


@cv.route('/alert_dept_list', methods=['POST'])
@api_response
def alert_dept_list(json_data):
    return critical_value.query_alert_dept_list()


@cv.route('/xindian_feedback', methods=['POST'])
@api_response
def xindian_feedback(json_data):
    return critical_value.xindian_data_feedback(json_data)


@cv.route('/update_template', methods=['POST'])
@api_response
def update_template():
    critical_value.update_cv_template()


@cv.route('/query_template', methods=['POST'])
@api_response
def query_template(json_data):
    return critical_value.query_cv_template(json_data.get('key'))


"""
校验危急值数量
"""


@cv.route('/check_cv_count', methods=['POST'])
@api_response
def check_cv_count(json_data):
    return cv_manage.check_crisis_value_count(json_data)


@cv.route('/record', methods=['POST', 'GET'])
@api_response
def test(json_data):
    cv_manage.fetch_cv_record()


@cv.route('/manual_send_to_his', methods=['POST', 'GET'])
@api_response
def manual_send_to_his(json_data):
    critical_value.manual_send_to_his(json_data.get('cv_id'), int(json_data.get('cv_source')))


@cv.route('/manual_send_to_his_invalid', methods=['POST', 'GET'])
@api_response
def manual_send_to_his_invalid(json_data):
    critical_value.manual_send_to_his_invalid(json_data.get('cv_id'), json_data.get('invalid_time'))


@cv.route('/manual_push_cv', methods=['POST', 'GET'])
@api_response
def manual_push_cv(json_data):
    critical_value.manual_push_cv(json_data.get('cv_id'))


@cv.route('/manual_push', methods=['POST', 'GET'])
@api_response
def manual_push_vital_signs(json_data):
    critical_value.manual_push_vital_signs(json_data.get('patient_name'), json_data.get('ip_addr'),
                                           json_data.get('open', True))



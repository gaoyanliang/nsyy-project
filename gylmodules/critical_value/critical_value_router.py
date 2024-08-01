import json
import traceback

from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.critical_value import critical_value

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
def system_create_cv1():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        cvd = json_data.get('cvd')
        critical_value.create_cv(cvd)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] inner_call_create_cv Exception occurred: {traceback.print_exc()}", e)

    return jsonify({
        'code': 20000
    })


@cv.route('/system_create_cv', methods=['POST'])
def system_create_cv():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        cv_source = json_data.get('cv_source')
        critical_value.create_cv_by_system(json_data, cv_source)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] system_create_cv Exception occurred: {traceback.print_exc()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值上报失败，请稍后重试'
        })

    return jsonify({
        'code': 20000
    })


"""
手工上报危急值
"""


@cv.route('/manual_report_cv', methods=['POST'])
def manual_report_cv():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        critical_value.manual_report_cv(json_data)
    except Exception:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] manual_report_cv Exception occurred: {traceback.print_exc()}"
        print(msg)
        return jsonify({
            'code': 50000,
            'res': msg
        })
    return jsonify({
        'code': 20000
    })


@cv.route('/invalid_cv', methods=['POST'])
def invalid_cv():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        cv_id = json_data.get('cv_id')
        cv_source = json_data.get('cv_source')
        critical_value.invalid_crisis_value([str(cv_id)], int(cv_source), True)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] invalid_cv Exception occurred: {e.__str__()}, param: {json_data}"
        print(msg)
        return jsonify({
            'code': 50000,
            'res': msg
        })
    return jsonify({
        'code': 20000
    })


"""
windows 客户端启动时， 查询所有待完成的危机值，并弹框提示
"""


@cv.route('/query_and_notice', methods=['POST'])
def query_process_cv_and_notice():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        dept_id = json_data.get("dept_id")
        ward_id = json_data.get("ward_id")
        if not dept_id and not ward_id:
            return jsonify({
                'code': 50000,
                'res': '科室id 和 病区id 不能同时为空',
                'data': []
            })

        critical_value.query_process_cv_and_notice(dept_id, ward_id)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] query_and_notice Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值查询并通知失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '危机值查询并通知成功',
        'data': '危机值查询并通知成功'
    })


"""
设置危机值超时时间
TODO 禁止用户修改
"""


# @cv.route('/setting_timeout', methods=['POST'])
# def setting_timeout():
#     json_data = json.loads(request.get_data().decode('utf-8'))
#     try:
#         critical_value.setting_timeout(json_data)
#     except Exception as e:
#         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         print(f"[{timestamp}] Exception occurred: {traceback.print_exc()}")
#         return jsonify({
#             'code': 50000,
#             'res': e.__str__(),
#             'data': '危机值超时时间设置失败，请稍后重试'
#         })
#
#     return jsonify({
#         'code': 20000,
#         'res': '危机值超时时间设置成功',
#         'data': '危机值超时时间设置'
#     })


"""
查询超时时间
"""


@cv.route('/query_timeout', methods=['GET', 'POST'])
def query_timeout():
    try:
        timeout_sets = critical_value.query_timeout()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] query_timeout Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值超时时间查询失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '危机值超时时间查询成功',
        'data': timeout_sets
    })


"""
维护站点信息
"""


@cv.route('/operate_site', methods=['POST'])
def operate_site():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        critical_value.site_maintenance(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] operate_site Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '站点信息维护失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '站点信息维护成功',
        'data': '站点信息维护成功'
    })


# 查询待审核危机值列表

"""
查询危机值列表
"""


@cv.route('/query', methods=['POST'])
def query_cv_list():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        page_number = json_data.get("page_number")
        page_size = json_data.get("page_size")
        if not page_number or not page_size:
            return jsonify({
                'code': 50000,
                'res': 'page_number 和 page_size 不能为空',
                'data': {}
            })

        cv_list, total = critical_value.get_cv_list(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] query Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值列表查询失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '危机值列表查询成功',
        'data': {
            'cv_list': cv_list,
            'total': total
        }
    })


"""
推送危机值
"""


@cv.route('/push', methods=['POST'])
def push_critical_value():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        cv_source = json_data.get('cv_source')
        dept_id = json_data.get('dept_id')
        if not cv_source or not dept_id:
            return jsonify({
                'code': 50000,
                'res': '参数异常：' + str(json_data),
                'data': ''
            })
        critical_value.push(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] push Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值推送失败，请稍后重试, ' + json_data
        })

    return jsonify({
        'code': 20000,
        'res': '危机值推送成功',
        'data': '危机值推送成功'
    })


"""
确认接收危机值
"""


@cv.route('/ask_recv', methods=['POST'])
def ack_critical_value():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        critical_value.confirm_receipt_cv(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ask_recv Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值接收失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '危机值接收成功',
        'data': '危机值接收成功'
    })


"""
书写护理记录
"""


@cv.route('/nursing_record', methods=['POST'])
def write_nursing_records():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        critical_value.nursing_records(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] nursing_record Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '危机值护理记录书写失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '危机值护理记录书写成功',
        'data': '危机值护理记录书写成功'
    })


"""
医生处理危机值
"""


@cv.route('/doctor_handle', methods=['POST'])
def handle_critical_value():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        critical_value.doctor_handle_cv(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] doctor_handle Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '医生处理危机值失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '医生处理危机值成功',
        'data': '医生处理危机值成功'
    })


"""
统计报表
"""


@cv.route('/report_form', methods=['POST'])
def query_all():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        report = critical_value.report_form(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] report_form Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '报表查询失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '报表查询成功',
        'data': report
    })


"""
病历模版
"""


@cv.route('/template', methods=['POST'])
def template():
    json_data = json.loads(request.get_data().decode('utf-8'))
    try:
        template = critical_value.medical_record_template(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] template Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': '报表查询失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '报表查询成功',
        'data': template
    })


"""
查询危机值上报科室列表
"""


@cv.route('/alert_dept_list', methods=['POST'])
def alert_dept_list():
    try:
        dept_list = critical_value.query_alert_dept_list()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] alert_dept_list Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': []
        })

    return jsonify({
        'code': 20000,
        'data': dept_list
    })


@cv.route('/xindian_feedback', methods=['POST'])
def xindian_feedback():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        res = critical_value.xindian_data_feedback(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] xindian_feedback Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': []
        })

    return jsonify({
        'code': 20000,
        'data': res
    })


@cv.route('/update_template', methods=['POST'])
def update_template():
    try:
        critical_value.update_cv_template()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] update_template Exception occurred: {e.__str__()}")
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': []
        })

    return jsonify({
        'code': 20000
    })


@cv.route('/query_template', methods=['POST'])
def query_template():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        res = critical_value.query_cv_template(json_data.get('key'))
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] query_template Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__(),
            'data': []
        })

    return jsonify({
        'code': 20000,
        'data': res
    })

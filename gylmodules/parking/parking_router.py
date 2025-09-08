from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response, validate_params
from gylmodules.parking import parking_server, parking_config

parking = Blueprint('parking system', __name__, url_prefix='/parking')


@parking.route('/apply_vip', methods=['POST'])
@api_response
def apply_vip_car(json_data):
    return parking_server.apply_vip_car(json_data)


@parking.route('/approval', methods=['POST'])
@api_response
def approval(json_data):
    return parking_server.approval_and_enable(json_data, 'approval')


@parking.route('/enable', methods=['POST'])
@api_response
def enable(json_data):
    return parking_server.approval_and_enable(json_data, 'enable')


@parking.route('/timeout_list', methods=['POST'])
@api_response
def timeout_list(json_data):
    return parking_server.query_timeout_list(json_data.get('type'),
                                             json_data.get('page_no'), json_data.get('page_size'))


@parking.route('/reminder_person', methods=['POST'])
@api_response
def reminder_person(json_data):
    return parking_server.reminder_person(json_data.get('car_id'))


@parking.route('/vip_list', methods=['POST'])
@api_response
def vip_list(json_data):
    return parking_server.query_vip_list(json_data.get('key', ''), json_data.get('dept_id', ''),
                                         json_data.get('start_date', ''),
                                         json_data.get('end_date', ''), json_data.get('page_no'),
                                         json_data.get('page_size'), json_data.get('type', ""),
                                         json_data.get('violated', 0))


@parking.route('/query_inout_records', methods=['POST'])
@api_response
def query_inout_records(json_data):
    return parking_server.query_inout_records(json_data.get('page_no'), json_data.get('page_size'),
                                              json_data.get('start_date'), json_data.get('end_date'))


# @parking.route('/add_vip_car', methods=['POST'])
# @api_response
# def add_vip_car(json_data):
#     parking_server.operate_vip_car('add', json_data)


@parking.route('/update_vip_car', methods=['POST'])
@api_response
def update_vip_car(json_data):
    parking_server.update_vip_car(json_data)


@parking.route('/remove_vip_car', methods=['POST'])
@api_response
def remove_vip_car(json_data):
    parking_server.operate_vip_car('remove', json_data)


@parking.route('/operate_vip_car', methods=['POST'])
@api_response
def operate_vip_car(json_data):
    parking_server.operate_vip_car('operate', json_data)


@parking.route('/report', methods=['POST'])
@api_response
def query_report(json_data):
    return parking_server.calculate_parking_duration(json_data.get('type'),
                                                     json_data.get('start_date'), json_data.get('end_date'))


@parking.route('/change_report', methods=['POST'])
@api_response
def query_change_report(json_data):
    return parking_server.vehicle_changes(json_data.get('start_date'), json_data.get('end_date'))


@parking.route('/park_info', methods=['POST'])
@api_response
def park_info():
    return parking_config.park_info


@parking.route('/authorize', methods=['POST'])
@api_response
def authorize(json_data):
    parking_server.person_authorize(json_data)


@parking.route('/query_authorize', methods=['POST'])
@api_response
def query_authorize():
    return parking_server.query_person_authorize()


@parking.route('/auto_fetch_data', methods=['POST'])
@api_response
def auto_fetch_data():
    parking_server.auto_fetch_data()


@parking.route('/auto_op_vip', methods=['POST'])
@api_response
def auto_op_vip():
    parking_server.auto_asynchronous_execution()


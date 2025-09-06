from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response
from gylmodules.shift_change import shift_change_server

shift_change = Blueprint('shift change system', __name__, url_prefix='/scs')


@shift_change.route('/shift_change', methods=['POST'])
@api_response
def run_shift_change():
    return shift_change_server.timed_shift_change()


@shift_change.route('/refresh_shift_data', methods=['POST'])
@api_response
def single_run_shift_change(json_data):
    return shift_change_server.single_run_shift_change(json_data)


@shift_change.route('/shift_data', methods=['POST', 'GET'])
@api_response
def query_shift_change_date(json_data):
    return shift_change_server.query_shift_change_date(json_data)


@shift_change.route('/delete_shift_data', methods=['POST', 'GET'])
@api_response
def delete_shift_change_date(json_data):
    shift_change_server.delete_shift_data(json_data.get('record_id'))


@shift_change.route('/new_shift_data', methods=['POST', 'GET'])
@api_response
def new_shift_data(json_data):
    return shift_change_server.update_shift_change_data(json_data)


@shift_change.route('/update_patient_count', methods=['POST', 'GET'])
@api_response
def update_patient_count(json_data):
    return shift_change_server.update_patient_count(json_data)


@shift_change.route('/new_shift_bed_data', methods=['POST', 'GET'])
@api_response
def new_shift_bed_data(json_data):
    return shift_change_server.update_shift_change_bed_data(json_data)


@shift_change.route('/query_shift_config', methods=['POST', 'GET'])
@api_response
def query_shift_config():
    return shift_change_server.query_shift_config()


@shift_change.route('/shift_config', methods=['POST', 'GET'])
@api_response
def shift_config(json_data):
    return shift_change_server.create_or_update_shift_config(json_data)


@shift_change.route('/shift_info', methods=['POST', 'GET'])
@api_response
def get_shift_info(json_data):
    return shift_change_server.query_shift_info(json_data)


@shift_change.route('/sign', methods=['POST'])
@api_response
def save_doc_sign_info(json_data):
    return shift_change_server.save_shift_info(json_data)


@shift_change.route('/query_patient_info', methods=['POST'])
@api_response
def query_patient_info(json_data):
    return shift_change_server.query_patient_info(json_data.get('zhuyuanhao'))


@shift_change.route('/vip_list', methods=['POST'])
@api_response
def vip_list():
    return {"dept_list": [722, 655, 2246, 10000, 2586], "pers_list": [9926, 110100]}








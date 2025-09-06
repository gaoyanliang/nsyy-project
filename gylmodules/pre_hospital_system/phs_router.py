from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response, validate_params
from gylmodules.pre_hospital_system import phs_server, phs_config

phs = Blueprint('Pre hospital emergency system', __name__, url_prefix='/phs')


@phs.route('/register', methods=['POST'])
@api_response
def patient_register(json_data):
    return phs_server.patient_registration(json_data)


@phs.route('/delete_register', methods=['POST'])
@api_response
def delete_register(json_data):
    return phs_server.delete_patient_registration(json_data.get('register_id'))


@phs.route('/update_patient_info', methods=['POST'])
@api_response
@validate_params('register_id')
def update_patient_info(json_data):
    # 提取并处理数据
    register_id = json_data.pop('register_id')
    phs_server.update_patient_info(json_data, register_id)


@phs.route('/query_patient_info', methods=['POST', 'GET'])
@api_response
def query_patient_info(json_data):
    return phs_server.query_patient_info(json_data.get('register_id'), json_data.get('record_id'))


@phs.route('/query_patient_list', methods=['POST', 'GET'])
@api_response
@validate_params('start_date', 'end_date')
def query_patient_list(json_data):
    return phs_server.query_patient_list(json_data.get('key'), json_data.get('bingli', 0), json_data.get('start_date'),
                                         json_data.get('end_date'), json_data.get('page_number'),
                                         json_data.get('page_size'))


@phs.route('/query_record_list', methods=['POST', 'GET'])
@api_response
def query_record_list():
    return phs_server.query_record_list()


@phs.route('/query_patient_record_list', methods=['POST', 'GET'])
@api_response
def query_patient_record_list(json_data):
    return phs_server.query_patient_record_list(json_data.get('register_id'))


@phs.route('/create_patient_record', methods=['POST', 'GET'])
@api_response
@validate_params('register_id', 'record_id')
def create_patient_record(json_data):
    return phs_server.create_patient_record(json_data.get('register_id'),
                                            json_data.get('record_id'), json_data.get('record_data'))


@phs.route('/car_no_list', methods=['POST', 'GET'])
@api_response
def car_no_list():
    return phs_config.car_no_list






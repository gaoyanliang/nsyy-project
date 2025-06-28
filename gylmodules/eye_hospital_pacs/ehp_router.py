import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response, validate_params
from gylmodules.eye_hospital_pacs import ehp_server

ehp_system = Blueprint('Eye Hospital Pacs', __name__, url_prefix='/ehp')


@ehp_system.route('/register', methods=['POST'])
@api_response
def patient_register(json_data):
    ehp_server.patient_registration(json_data)


@ehp_system.route('/treatment', methods=['POST'])
@api_response
def patient_treatment(json_data):
    ehp_server.treatment_records(json_data)


@ehp_system.route('/query_patient', methods=['POST', 'GET'])
@api_response
def query_patient_list(json_data):
    return ehp_server.query_patient_list(json_data)


@ehp_system.route('/medical_record', methods=['POST'])
@api_response
@validate_params('register_id')
def create_medical_record(json_data):
    ehp_server.create_medical_record(json_data)


@ehp_system.route('/update_medical_record', methods=['POST'])
@api_response
def update_medical_record(json_data):
    ehp_server.update_medical_record_detail(json_data)


@ehp_system.route('/query_medical_list', methods=['POST', 'GET'])
@api_response
@validate_params('register_id', 'tid')
def query_medical_list(json_data):
    return ehp_server.query_medical_list(json_data.get('register_id'), json_data.get('tid'))


@ehp_system.route('/query_medical_record', methods=['POST', 'GET'])
@api_response
def query_medical_record(json_data):
    return ehp_server.query_medical_record(json_data.get('record_detail_id'))




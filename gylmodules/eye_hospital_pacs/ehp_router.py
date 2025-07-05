import json
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory

from gylmodules import global_config
from gylmodules.global_tools import api_response, validate_params
from gylmodules.eye_hospital_pacs import ehp_server

ehp_system = Blueprint('Eye Hospital Pacs', __name__, url_prefix='/ehp')


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
@validate_params('register_id')
def query_medical_list(json_data):
    return ehp_server.query_medical_list(json_data.get('register_id'))


@ehp_system.route('/query_medical_record', methods=['POST', 'GET'])
@api_response
def query_medical_record(json_data):
    return ehp_server.query_medical_record(json_data.get('record_detail_id'))


@ehp_system.route('/query_reports', methods=['POST', 'GET'])
@api_response
def query_report_list(json_data):
    return ehp_server.query_report_list(json_data.get('register_id'))


@ehp_system.route('/bind_report', methods=['POST', 'GET'])
@api_response
def bind_report(json_data):
    return ehp_server.bind_report(json_data.get('report_id'), json_data.get('register_id'), json_data.get('patient_id'))


@ehp_system.route('/report', methods=['POST', 'GET'])
def show_report():

    # return send_from_directory("/Users/gaoyanliang/Pictures", "1740967549.2904139.png", as_attachment=True)
    if global_config.run_in_local:
        return send_from_directory("/Users/gaoyanliang/各个系统文档整理/眼科医院/眼科医院仪器检查报告和病历/203光相关断层扫描仪/", "双眼视神经分析.pdf")
    else:
        return send_from_directory("/home/cc/att/public/", "双眼视神经分析.pdf")
    # return send_from_directory("/Users/gaoyanliang/各个系统文档整理/眼科医院/眼科医院仪器检查报告和病历/203光相关断层扫描仪/", "双眼视神经分析.pdf", as_attachment=True)
    # return ehp_server.query_medical_record(json_data.get('record_detail_id'))



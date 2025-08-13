from flask import Blueprint, jsonify, request

from gylmodules.global_tools import api_response, validate_params
from gylmodules.parking import parking_server, parking_config

parking = Blueprint('parking system', __name__, url_prefix='/parking')


@parking.route('/vip_list', methods=['POST'])
@api_response
def vip_list(json_data):
    return parking_server.query_vip_list(json_data.get('key'), json_data.get('page_no'), json_data.get('page_size'))


@parking.route('/add_svip', methods=['POST'])
@api_response
def add_svip(json_data):
    return parking_server.add_svip(json_data.get('car_id'), json_data.get('svip'))


@parking.route('/query_inout_records', methods=['POST'])
@api_response
def query_inout_records(json_data):
    return parking_server.query_inout_records(json_data.get('page_no'), json_data.get('page_size'),
                                              json_data.get('start_date'), json_data.get('end_date'))


@parking.route('/add_vip_car', methods=['POST'])
@api_response
def add_vip_car(json_data):
    parking_server.add_vip_car(json_data)


@parking.route('/update_vip_car', methods=['POST'])
@api_response
def update_vip_car(json_data):
    parking_server.update_vip_car(json_data)


@parking.route('/remove_vip_car', methods=['POST'])
@api_response
def remove_vip_car(json_data):
    parking_server.remove_vip_car(json_data)


@parking.route('/operate_vip_car', methods=['POST'])
@api_response
def operate_vip_car(json_data):
    parking_server.operate_vip_car(json_data)


@parking.route('/auto_fetch_data', methods=['POST'])
@api_response
def auto_fetch_data(json_data):
    parking_server.auto_fetch_data(json_data.get('start_date'), json_data.get('end_date'))


@parking.route('/report', methods=['POST'])
@api_response
def query_report(json_data):
    return parking_server.calculate_parking_duration(json_data.get('start_date'), json_data.get('end_date'))


@parking.route('/park_info', methods=['POST'])
@api_response
def park_info():
    return parking_config.park_info


import datetime
import os
from ftplib import FTP

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from gylmodules import global_tools
from gylmodules.file_system import file_server
from gylmodules.global_tools import api_response

file_system = Blueprint('file system', __name__, url_prefix='/file')


@file_system.route('/new_group', methods=['POST'])
@api_response
def new_group(json_data):
    return file_server.create_or_update_group(json_data)


@file_system.route('/group_member', methods=['POST'])
@api_response
def group_member(json_data):
    return file_server.add_group_member(json_data.get('op_type'), json_data.get('group_id'),
                                        json_data.get('members'), json_data.get('user_id'))


@file_system.route('/query_group_list', methods=['POST', 'GET'])
@api_response
def query_group_list(json_data):
    return file_server.query_group_list(json_data.get('user_id'))


@file_system.route('/query_group_member', methods=['POST', 'GET'])
@api_response
def query_group_member(json_data):
    return file_server.query_group_member(json_data.get('group_id'))


@file_system.route('/add_admin', methods=['POST'])
@api_response
def add_admin(json_data):
    return file_server.add_admin(json_data)


@file_system.route('/dept_admin_list', methods=['POST', 'GET'])
@api_response
def dept_admin_list():
    return file_server.dept_admin_list()


@file_system.route('/query_file_history', methods=['POST', 'GET'])
@api_response
def query_file_history(json_data):
    return file_server.query_file_history(json_data.get('document_id'))


@file_system.route('/new_folder', methods=['POST'])
@api_response
def new_folder(json_data):
    return file_server.new_folder(json_data)


@file_system.route('/update_folder', methods=['POST'])
@api_response
def update_folder(json_data):
    return file_server.update_folder(json_data)


@file_system.route('/move_folder', methods=['POST'])
@api_response
def move_folder(json_data):
    return file_server.move_folder(json_data)


@file_system.route('/upload_file', methods=['POST'])
@api_response
def upload_file(json_data):
    return file_server.upload_file(json_data)


@file_system.route('/update_file', methods=['POST'])
@api_response
def update_file(json_data):
    return file_server.update_file(json_data)


@file_system.route('/move_file', methods=['POST'])
@api_response
def move_file(json_data):
    return file_server.move_file(json_data)


@file_system.route('/query_file_list', methods=['POST', 'GET'])
@api_response
def query_file_list(json_data):
    return file_server.query_file_list(json_data)





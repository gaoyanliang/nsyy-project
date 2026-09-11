import os

from flask import Blueprint, jsonify, request, send_from_directory

from gylmodules.file_system import file_server
from gylmodules.global_tools import api_response

file_system = Blueprint('file system', __name__, url_prefix='/file')

# ==================================================
# ================  科室权限管理路由 ===================
# ==================================================


@file_system.route('/op_dept_admin', methods=['POST'])
@api_response
def add_admin(json_data):
    return file_server.op_admin(json_data)


@file_system.route('/dept_admin_list', methods=['POST', 'GET'])
@api_response
def dept_admin_list(json_data):
    return file_server.dept_admin_list(json_data.get('dept_id'))



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


@file_system.route('/folder_grant', methods=['POST'])
@api_response
def folder_grant(json_data):
    return file_server.grant_folder(json_data.get('resource_type'), json_data.get('resource_ids'),
                                   json_data.get('target_type'), json_data.get('target_ids'),
                                   json_data.get('operation'), json_data.get('perm_fields'))


@file_system.route('/move_folder', methods=['POST'])
@api_response
def move_folder(json_data):
    return file_server.move_folder_or_document(json_data)


@file_system.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        raise Exception('没有选择文件')
    files = request.files.getlist('file')

    upload_files = []
    for file in files:
        # 如果用户没有选择文件
        if file.filename == '':
            continue
        upload_files.append(file)
    file_server.upload_file(request.form, upload_files)
    return jsonify({'code': 20000, 'message': '上传成功'})


@file_system.route('/update_file', methods=['POST'])
@api_response
def update_file(json_data):
    return file_server.update_file(json_data)


@file_system.route('/download', methods=['POST', 'GET'])
def download_file():
    json_data = request.get_json()
    file = file_server.download_file(json_data)
    # 作为附件下载（浏览器会弹出下载对话框）
    return send_from_directory(
        os.path.dirname(file.get('storage_path')),
        os.path.basename(file.get('storage_path')),
        as_attachment=True,
        download_name=file.get('name')  # 指定下载时的文件名
    )



@file_system.route('/query_file_list', methods=['POST', 'GET'])
@api_response
def query_file_list(json_data):
    return file_server.query_file_list(json_data)




# ==================================================
# ================  资源详情路由 ===================
# ==================================================

@file_system.route('/folder_detail', methods=['POST'])
@api_response
def folder_detail(json_data):
    return file_server.folder_detail(json_data)


@file_system.route('/document_detail', methods=['POST'])
@api_response
def document_detail(json_data):
    return file_server.document_detail(json_data)





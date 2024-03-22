import os
import traceback

from flask import Blueprint, jsonify, request, render_template, send_file
from gylmodules.workstation.file import file
import json

file_router = Blueprint('file router', __name__, url_prefix='/file')


@file_router.route('/', methods=['POST'])
def index():
    dirtree = file.query_file_list()
    return render_template('./templates/index.html', file_tree=dirtree)


# http://www.coolpython.net/flask_tutorial/basic/flask-download.html
# 下载本服务器的文件 可以直接使用 send_file 来实现下载。 点击 ip:port/download 直接下载到浏览器
@file_router.route('/download_direct', methods=['POST'])
def download():
    return send_file('./uploads/55cun.png',
                     as_attachment=True, download_name='55cun.png')


@file_router.route("/download", methods=['POST'])
def download_file():
    json_data = json.loads(request.get_data().decode('utf-8'))
    file_path = json_data.get("file_path")
    file_name = file_path.split("/")[-1]
    # 返回当前工作目录
    pwd = os.getcwd()
    local_path = pwd + "/downloads/" + file_name

    file.sftp_download(local_path, "/" + file_path)
    dirtree = file.query_file_list()
    return render_template('./templates/index.html', success='File download successfully',
                           download_file=file_name, file_tree=dirtree, render_tree=file.render_tree)

















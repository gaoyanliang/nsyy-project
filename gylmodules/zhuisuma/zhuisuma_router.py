from flask import Blueprint

from gylmodules.global_tools import api_response
from gylmodules.zhuisuma import zhuisuma_server

zhuisuma_system = Blueprint('zhuisuma system', __name__, url_prefix='/zsm')


@zhuisuma_system.route('/save-codes', methods=['POST'])
@api_response
def save_codes_func(json_data):
    codes = json_data.get('codes', [])

    if not codes:
        raise Exception('没有追溯码')

    return zhuisuma_server.save_codes(codes)


# API: 获取历史数据
@zhuisuma_system.route('/history', methods=['GET'])
@api_response
def get_history_func():
    return zhuisuma_server.get_history()







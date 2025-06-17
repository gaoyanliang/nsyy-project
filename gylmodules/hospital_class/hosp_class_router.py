import json
import logging
from flask import Blueprint, jsonify, request

from gylmodules.hospital_class import hosp_class_server

hosp_class = Blueprint('hospital class', __name__, url_prefix='/hosp_class')
logger = logging.getLogger(__name__)


# 领导设计的接口，仅负责实现
@hosp_class.route('/v1', methods=['POST'])
def hosp_class_func():
    json_data = []
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        return hosp_class_server.hosp_class(json_data)
    except Exception as e:
        logger.error(f"hosp_class_func Exception occurred: {e.__str__()}, param: {json_data}")
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })






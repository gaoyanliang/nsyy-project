import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.hospital_class import hosp_class_server

hosp_class = Blueprint('hospital class', __name__, url_prefix='/hosp_class')


@hosp_class.route('/', methods=['POST', 'OPTIONS'])
def hosp_class_func():
    json_data = []
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        return hosp_class_server.hosp_class(json_data)
    except Exception as e:
        print(datetime.now(), f"hosp_class_func Exception occurred: {e.__str__()}, param: ", json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

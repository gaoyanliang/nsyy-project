import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from gylmodules.medical_record_analysis import parse_server as parse_server

parse = Blueprint('medical record analysis', __name__, url_prefix='/parse')


@parse.route('/query_record_and_parse', methods=['POST'])
def query_record_and_parse():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        parse_server.query_record_and_parse(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", 'param: ', json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    return jsonify({
        'code': 20000,
    })

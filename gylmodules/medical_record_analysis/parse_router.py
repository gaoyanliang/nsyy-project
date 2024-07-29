import json
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from collections import OrderedDict
import dicttoxml

from gylmodules.medical_record_analysis import parse_server as parse_server

parse = Blueprint('medical record analysis', __name__, url_prefix='/parse')


@parse.route('/query_record_and_parse', methods=['POST'])
def query_record_and_parse():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))

        print(json_data)
        cda, structure = parse_server.query_record_and_parse(json_data)
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Exception occurred: {e.__str__()}", 'param: ', json_data)
        return jsonify({
            'code': 50000,
            'res': e.__str__()
        })

    ordered_data = convert_to_ordered_dict(structure)
    ret = {
        'code': 20000,
        'cda': cda,
        'structure': ordered_data
    }
    return Response(response=json.dumps(ret, ensure_ascii=False), mimetype='application/json')
    # return Response(cda, mimetype='application/xml')


def convert_to_ordered_dict(data):
    if isinstance(data, dict):
        return OrderedDict((k, convert_to_ordered_dict(v)) for k, v in data.items())
    elif isinstance(data, list):
        return [convert_to_ordered_dict(item) for item in data]
    else:
        return data

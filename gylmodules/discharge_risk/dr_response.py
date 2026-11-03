# gylmodules/discharge_risk/dr_response.py
import inspect
import json
import logging
import traceback
from functools import wraps

from flask import request, jsonify

logger = logging.getLogger(__name__)


def dr_api_response(func):
    """
    dr_router 专用 API 装饰器。
    与 global_tools.api_response 的区别：
      1. 合并 query string、JSON body、路径参数(kwargs)、上传文件，统一成 json_data
      2. 无条件把 json_data 传给被装饰函数（无参函数自动走 func()）
      3. 返回格式保持 {'code': 20000, 'data': ...}，前端无需改动
    """
    sig = inspect.signature(func)
    positional = [
        p for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)
    ]
    has_json_param = len(positional) >= 1

    @wraps(func)
    def wrapper(*args, **kwargs):
        json_data = {}
        try:
            # 1) query 参数（GET 接口的查询条件都在这）
            if request.args:
                json_data.update(request.args.to_dict(flat=True))

            # 2) JSON body（POST / PUT）
            raw = request.get_data()
            if raw:
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return jsonify({"code": 50000, "res": "Invalid JSON format"})

                if isinstance(body, dict):
                    json_data.update(body)
                elif isinstance(body, list):
                    # 兼容「直接传数组」的批量接口：import_patients
                    json_data["_list"] = body
                else:
                    json_data["_raw"] = body

            # 3) 路径参数（如 <int:patient_id>）
            if kwargs:
                json_data.update(kwargs)

            # 4) multipart 文件（import-file 接口）
            if request.files:
                json_data["_files"] = request.files

            logger.debug(f"[dr] {request.method} {request.url} 参数 keys={list(json_data.keys())}")

            result = func(json_data) if has_json_param else func()
            return jsonify({"code": 20000, "data": result if result is not None else {}})

        except KeyError as e:
            return jsonify({"code": 50000, "res": f"Missing parameter: {e}"})
        except Exception as e:
            logger.error(f"[dr] {request.url} 异常：{e}\n{traceback.format_exc()}")
            return jsonify({"code": 50000, "res": str(e)})

    return wrapper
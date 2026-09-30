import base64

from flask import Flask, request, jsonify
import logging
from datetime import datetime

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('face_recognition_receiver')

error_code = {
    "1": "识别成功",
    "2": "无此人员ID",
    "3": "匹配失败",
    "4": "权限已到期",
    "5": "有效期时段外",
    "6": "群组开门,人员太少",
    "7": "身份证识别失败",
    "11": "未戴安全帽禁止通行",
    "12": "黑名单人员",
}


@app.route('/devicemanagement/php/result.php', methods=['POST'])
def result():
    """
    接收人脸识别设备推送的结果
    """
    try:
        # 记录原始请求信息
        logger.info(f"人脸识别结果 - 时间: {datetime.now()}")

        # 解析请求数据（可能是JSON或表单数据）
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = request.form.to_dict()
            logger.info(f"表单数据: {data}")

        # 处理识别结果
        # process_recognition_result(data)

        code = data.get('body', {}).get('code', '')
        code = code % 100

        # 原始字符串
        original_str = f"{error_code.get(str(code), '')} {data.get('body', {}).get('name', '')} 请通行 "
        # 转换为bytes后编码
        encoded_bytes = base64.b64encode(original_str.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')

        # 返回成功响应（设备可能需要确认）
        return jsonify(
            {
                # int 0：接收成功；400：接收失败
                "code": 0,
                # uint 消息 id  设备推送每条识别结果中会带入sequence，要想控制设备须在回复中带入收到的sequence
                "sequence": data.get('body', {}).get('sequence', ''),
                # string 错误原因
                "msg": "",
                # 需要在线开闸时用，可选,不管设备端的配置
                "body": {
                    # 1:开，0：不开
                    "gate_ctrl": {"open": 1},
                    # 推送消息中的 perid，返回回来。
                    "per_id": data.get('body', {}).get('sequence', ''),
                    # wgin_read、idcard_read，推送消息中的 type 字段，返回回来。
                    "result_type": data.get('type', ''),
                    "tts": {
                        "text": encoded_str,  # utf8+base64 编码
                        "is_female": 1
                    },
                    #
                    "ui": {"text": encoded_str}
                }
            })

    except Exception as e:
        logger.error(f"处理识别结果时出错: {e}")
        return jsonify({
                # int 0：接收成功；400：接收失败
                "code": 400,
                # uint 消息 id  设备推送每条识别结果中会带入sequence，要想控制设备须在回复中带入收到的sequence
                "sequence": data.get('body', {}).get('sequence', ''),
                # string 错误原因
                "msg": "人脸识别失败",
                # 需要在线开闸时用，可选,不管设备端的配置
                "body": {
                    # 1:开，0：不开
                    "gate_ctrl": {"open": 1},
                    # 推送消息中的 perid，返回回来。
                    "per_id": data.get('body', {}).get('sequence', ''),
                    # wgin_read、idcard_read，推送消息中的 type 字段，返回回来。
                    "result_type": data.get('type', ''),
                    "tts": {
                        "text": "5Lq66IS46K+G5Yir5oiQ5YqfIOivt+mAmuihjA==",  # utf8+base64 编码
                        "is_female": 1
                    },
                    #
                    "ui": {"text": "5Lq66IS46K+G5Yir5oiQ5YqfIOivt+mAmuihjA=="}
                }
            })


@app.route('/devicemanagement/php/gio.php', methods=['POST'])
def gio():
    try:
        # 记录原始请求信息
        logger.info(f"刷卡/证结果推送 - 时间: {datetime.now()}")

        # 解析请求数据（可能是JSON或表单数据）
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = request.form.to_dict()
            logger.info(f"表单数据: {data}")

        # 处理识别结果
        # process_recognition_result(data)
        code = data.get('body', {}).get('code', '')
        code = code % 100

        # 原始字符串
        original_str = f"{error_code.get(str(code), '')} {data.get('body', {}).get('name', '')} 请通行 "
        # 转换为bytes后编码
        encoded_bytes = base64.b64encode(original_str.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')

        # 返回成功响应（设备可能需要确认）
        return jsonify(
            {
                # int 0：接收成功；400：接收失败
                "code": 0,
                # uint 消息 id  设备推送每条识别结果中会带入sequence，要想控制设备须在回复中带入收到的sequence
                "sequence": data.get('body', {}).get('sequence', ''),
                # string 错误原因
                "msg": "",
                # 需要在线开闸时用，可选,不管设备端的配置
                "body": {
                    # 1:开，0：不开
                    "gate_ctrl": {"open": 1},
                    # 推送消息中的 perid，返回回来。
                    "per_id": data.get('body', {}).get('sequence', ''),
                    # wgin_read、idcard_read，推送消息中的 type 字段，返回回来。
                    "result_type": data.get('type', ''),
                    "tts": {
                        "text": encoded_str,  # utf8+base64 编码
                        "is_female": 1
                    },
                    #
                    "ui": {"text": encoded_str}
                }
            })

    except Exception as e:
        logger.error(f"处理识别结果时出错: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

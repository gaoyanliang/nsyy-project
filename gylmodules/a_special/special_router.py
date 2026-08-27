import base64
import errno
import hmac
import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
import hashlib

import paramiko
import requests
from flask import Blueprint, request, Response, jsonify, send_file, after_this_request, send_from_directory
import os
import zipfile
from io import BytesIO

import pandas as pd

from gylmodules import global_config, global_tools
from gylmodules.a_special import special_server
from gylmodules.global_tools import api_response
from gylmodules.utils.db_utils_new import DbUtil

logger = logging.getLogger(__name__)
special_system = Blueprint('special system', __name__, url_prefix='/special')

# 手术流转接口 扫描患者腕带 查询患者信息
# 要求： 读取患者腕带或手术申请二维码，获取手术相关信息，包括手术部位，术式，麻醉方式等信息

@special_system.route('/surgical_transfer', methods=['POST', 'GET'])
@api_response
def surgical_transfer_query(json_data):
    data = surgical_transfer_data(json_data)
    return data


"""患者手术流转数据查询"""


def surgical_transfer_data(json_data):
    patient_id = json_data.get('patient_code')
    if not patient_id or not str(patient_id).startswith('BR'):
        raise Exception(f'患者腕带数据异常, 期望: BR|病人ID｜住院次数, 实际: {patient_id}')
    scan_timing = json_data.get('scan_timing')
    split_data = patient_id.split('|')
    patient_id, number = split_data[1], split_data[2]

    sql = f"""select ss.shoushudanid , zb.xingming 姓名, zb.dangqianksmc 科室, zb.zhuyuanhao 住院号,
	        zb.dangqiancwbm 床号, zb.nianling  年龄, ss.bingrenid , ss.shoushubw 手术部位, zb.xingbiemc 性别, 
	        ss.shoushumc || coalesce('+' || ss.shoushumc1, '')|| coalesce('+' || ss.shoushumc2,
	        '')|| coalesce('+' || ss.shoushumc3, '')|| coalesce('+' || ss.shoushumc4, 
            '')|| coalesce('+' || ss.shoushumc5, '') 手术名称, gd.daimamc || case when gd2.daimamc is not null
		and gd.daimamc <> gd2.daimamc then '+' || gd2.daimamc else ''
	    end 麻醉方式,
	to_char(ss.anpaisj, 'YYYY-MM-DD HH24:MI:SS') 手术安排时间, ss.zhenduanmc1 诊断 from df_jj_zhuyuan.zy_bingrenxx zb
    join df_shenqingdan.sm_shoushuxx ss on zb.bingrenzyid = ss.bingrenzyid and ss.zuofeibz = '0'
	and ss.zhuangtaibz in (6, 7) left join df_zhushuju.gy_daima gd on ss.mazuiff = gd.daimaid
	and gd.daimalb = '10078' left join df_zhushuju.gy_daima gd2 on ss.mazuiff1 = gd2.daimaid
	and gd2.daimalb = '10078' 
    where ss.anpaisj >= now()::date and ss.anpaisj < now()::date + interval '1 day' and ss.bingrenid = '{patient_id}'
    -- where ss.anpaisj >= '2025-12-16' and ss.anpaisj < '2025-12-17' and ss.bingrenid = '10190159'
    """
    data = global_tools.call_new_his_pg(sql)
    if not data:
        return {}

    shoushudanids = [str(item.get('shoushudanid')) for item in data]
    shoushudanids = ','.join([f"'{item}'" for item in shoushudanids])
    sql = f"""
        select t.sam_apply_id,
           t.in_oproom_date   入手术室时间,
           t.out_oproom_date  出手术室时间,
           t.oper_beging_date 手术开始时间,
           t.oper_end_date    手术结束时间
      from sam_anar t
     where t.sam_apply_id in ({shoushudanids})
    """
    shijian = global_tools.call_new_his(sql, 'nsshouma')
    shijian_dict = {}
    for item in shijian:
        shijian_dict[item.get('SAM_APPLY_ID')] = item

    for item in data:
        item.update(shijian_dict.get(item.get('shoushudanid'), {}))

    data = data[0]
    patient_name = data.get('姓名', '')
    data['record_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        insert_sql = """INSERT INTO nsyy_gyl.a_surgical_transfer (patient_id, number, patient_name, patient_info,
                                        timing, record_time) VALUES (%s, %s, %s, %s, %s, %s)"""
        args = (patient_id, number, patient_name, json.dumps(data, ensure_ascii=False, default=str),
                scan_timing, data['record_time'])
        db.execute(insert_sql, args, need_commit=True)

    return data


@special_system.route('/invoice_verification', methods=['POST', 'GET'])
@api_response
def invoice_verification_func(json_data):
    return invoice_verification(json_data)



def invoice_verification(param):
    """发票核验，支持两种方式，1.通过发票号码+开票时间+金额查验 2.通过扫描二维码查验"""
    AppKey = "5CC6F31EFCBE4046ACCBA38C671C3005"
    AppSecret = "bf377d065b9fe182c5cf6d40c687691f"

    url = "https://open.cs.zbj.com/v2/invoice/query"
    if 'code' in param:
        url = "https://open.cs.zbj.com/v2/invoice/qrcode"
    headers = {"X-CS-Authorization": "HMAC-SHA256", "X-CS-Key": AppKey, "X-CS-Nonce": str(uuid.uuid4()),
        "X-CS-Timestamp": str(int(time.time())), "X-CS-Version": "v2"}

    signList = ['POST']
    for key, val in headers.items():
        signList.append(key + '=' + val)

    signStr = '|'.join(signList)
    signature = base64.b64encode(hmac.new(bytes(AppSecret, 'utf-8'), bytes(signStr, 'utf-8'), hashlib.sha256).digest())
    headers['X-CS-Signature'] = str(signature, 'utf-8')

    retry_times = 3
    while retry_times > 0:
        try:
            with requests.Session() as session:
                r = session.post(url, headers=headers, json=param, timeout=10)
                r.raise_for_status()
                data = r.json()
            if data.get('success', False):
                return invoice_to_cn(data.get('data', {}))
        except Exception:
            pass
        retry_times -= 1
    return None


FIELD_MAP = {
    "fplx": "发票类型",
    "fpdm": "发票代码",
    "fphm": "发票号码",
    "kprq": "开票日期",

    "xfMc": "销售方名称",
    "xfNsrsbh": "销售方纳税人识别号",
    "xfContact": "销售方联系方式",
    "xfBank": "销售方开户行及账号",

    "gfMc": "购方名称",
    "gfNsrsbh": "购方纳税人识别号",
    "gfContact": "购方联系方式",
    "gfBank": "购方开户行及账号",

    "code": "发票校验码",
    "num": "发票机器码",

    "del": "发票状态",
    "taxamount": "税额合计",
    "goodsamount": "不含税金额合计",
    "sumamount": "价税合计",
    "quantityAmount": "数量合计",

    "isGoodsList": "是否含销货清单",
    "queryCount": "税局查验次数",
    "updateTime": "更新时间",
    "tspzlx": "特殊票种类型",
    "remark": "备注",

    "sfCode": "省份代码",
    "sfMc": "省份名称"
}


GOODS_FIELD_MAP = {
    "name": "商品名称",
    "spec": "规格型号",
    "unit": "单位",
    "amount": "数量",
    "priceUnit": "单价",
    "priceSum": "金额",
    "taxRate": "税率",
    "taxSum": "税额",
    "productCode": "商品分类编码"
}

INVOICE_TYPE_MAP = {
    # —— 传统增值税发票 ——
    "01": "增值税专用发票",
    "02": "货物运输业增值税专用发票",
    "03": "机动车销售统一发票",
    "04": "增值税普通发票",
    "08": "增值税电子专用发票",
    "10": "增值税电子普通发票",
    "11": "增值税普通发票（卷票）",
    "14": "增值税电子普通发票（通行费）",
    "15": "二手车销售统一发票",

    # —— 全电发票（数电发票） ——
    "20": "电子发票（增值税专用发票）",
    "21": "电子发票（普通发票）",
    "72": "电子发票（通行费）",
    "83": "铁路电子客票",
    "61": "航空运输电子客票行程单"
}


"""
将发票接口返回的 JSON 转为中文字段 JSON
"""


def invoice_to_cn(data: dict) -> dict:

    result = {}

    # 一、普通字段映射
    for eng_key, cn_key in FIELD_MAP.items():
        if eng_key in data:
            result[cn_key] = data.get(eng_key)

    # 二、商品明细处理
    goods_list = data.get("goodsData", [])
    cn_goods_list = []

    for item in goods_list:
        cn_item = {}
        for eng_key, cn_key in GOODS_FIELD_MAP.items():
            if eng_key in item:
                cn_item[cn_key] = item.get(eng_key)
        cn_goods_list.append(cn_item)

    if cn_goods_list:
        result["商品明细"] = cn_goods_list

    if '发票类型' in result:
        result['发票类型'] = INVOICE_TYPE_MAP.get(result['发票类型'], result['发票类型'])

    return result



# ===================================================================================================
# ========================================= 住院dip 患者查询 ==========================================
# ===================================================================================================


"""查询入院三天未提交病案首页的患者列表"""


@special_system.route('/unsubmitted', methods=['POST', 'GET'])
@api_response
def unsubmitted():
    return special_server.query_unpage_patients()



"""查询前一天 病案首页有变化的患者列表"""


@special_system.route('/modified-today', methods=['POST', 'GET'])
@api_response
def modified_today():
    return special_server.query_today_update_dip_patients()

@special_system.route('/all-dip', methods=['POST', 'GET'])
@api_response
def all_dip():
    return special_server.query_all_dip_patients()


"""刷新病人pid信息"""

@special_system.route('/patients_update', methods=['POST', 'GET'])
@api_response
def patients_update(json_data):
    return special_server.refresh_patient_dip_info(json_data.get('patientId'))



"""上传税务系统登陆二维码"""

@special_system.route('/tax_login_qrcode_upload', methods=['POST', 'GET'])
def tax_login_qrcode_update():
    if "file" not in request.files:
        return {"code": 50000, "data": '', "res": "没有文件"}

    file = request.files["file"]

    # 构建保存目录
    if global_config.run_in_local:
        save_dir = "/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/a_special/upload"
    else:
        save_dir = "/home/gyl/gyl_server/tax/login"

    # 确保目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)  # exist_ok=True 避免并发问题

    # 构建完整保存路径
    save_path = os.path.join(save_dir, file.filename)
    with open(save_path, "wb") as f:
        content = file.read()
        f.write(content)

    return {
        "code": 0,
        "msg": "success",
        "path": save_path
    }


@special_system.route('/tax_fapiao', methods=['POST', 'GET'])
def tax_fapiao():
    if "file" not in request.files:
        return {"code": 50000, "data": '', "res": "没有文件"}

    file = request.files["file"]
    comp_dir_name = 'no_comp'
    if request.form and 'comp_dir_name' in request.form:
        comp_dir_name = request.form.get('comp_dir_name')

    if global_config.run_in_local:
        save_path = f"/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/a_special/upload/{datetime.now().month}"
        # 确保目录存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        save_path = os.path.join(save_path, file.filename)
        with open(save_path, "wb") as f:
            content = file.read()
            f.write(content)

        return {
            "code": 0,
            "msg": "success",
            "path": save_path
        }

    # ✅ 1. 安全文件名
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    # ✅ 2. 本地临时目录
    local_dir = "/tmp/tax_fapiao_upload"
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    file.save(local_path)

    # 远程目录（按月份）
    remote_dir = f"/home/gyl/tax_fapiao/{datetime.now().year}/{datetime.now().month:02d}/{comp_dir_name}"
    if file.filename.lower().endswith(".zip"):
        remote_dir = f"{remote_dir}/zip"
    remote_path = f"{remote_dir}/{file.filename}"

    # 远程服务器配置
    remote_host = "192.168.9.75"
    remote_user = "gyl"
    remote_pass = "nsyy0601."
    try:
        # 建立 SFTP 连接
        transport = paramiko.Transport((remote_host, 22))
        transport.connect(username=remote_user, password=remote_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # === 修复点开始：使用递归方式创建远程目录 ===
        # 将路径切分，逐级检查并创建
        dir_path = remote_dir
        # 兼容 Windows/Linux 路径分隔符
        folders = dir_path.split(os.sep)
        # 重新拼凑路径进行检查和创建
        current_path = ""
        if dir_path.startswith('/'):
            current_path = "/"

        for folder in folders:
            if not folder:
                continue
            if current_path == "/":
                new_path = current_path + folder
            else:
                new_path = current_path + "/" + folder

            try:
                sftp.stat(new_path)
            except IOError as e:
                # 如果报错是“没有那个文件或目录”，说明需要创建
                if e.errno == errno.ENOENT:
                    print(f"Creating remote directory: {new_path}")
                    sftp.mkdir(new_path)
                else:
                    raise  # 其他错误（如权限问题）抛出

            current_path = new_path
        # === 修复点结束 ===

        # ✅ 5. 用 put 上传
        sftp.put(local_path, remote_path)

        sftp.close()
        transport.close()

        # ✅ 6. 可选：删除本地临时文件
        os.remove(local_path)

        return {
            "code": 0,
            "msg": "success",
            "path": remote_path
        }

    except Exception as e:
        return {
            "code": 50001,
            "msg": "文件上传失败",
            "error": str(e)
        }


@special_system.route('/ocr', methods=['POST', 'GET'])
@api_response
def ocr(json_data):
    return special_server.ocr_try_variants(json_data.get('img_b64'))



# =========================================================================================
# ======================================== 智能手表 ========================================
# =========================================================================================


DATA_FILE = "received_data.log"
HEALTH_FILE = "health_data.log"
POSITION_FILE = "position_data.log"
ALARM_FILE = "alarm_data.log"

def save_record(record: dict, file_path: str = DATA_FILE) -> None:
    """
    将记录追加写入文件，每一行是一个 JSON 字符串
    :param file_path:
    :param record: 要保存的字典
    """
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug(f"Record saved: {record.get('action', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to save record: {e}")

def build_record() -> dict:
    """
    根据当前请求构建一个统一的记录字典
    :return: 包含时间戳、来源、方法、路径、参数、数据等信息的字典
    """
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client_ip": request.remote_addr,
        "method": request.method,
        "url": request.url,
        "path": request.path,
        "args": request.args.to_dict(),          # GET 参数 / POST 表单参数（如果有）
        "headers": dict(request.headers),        # 记录头部便于调试
    }

    # 处理 POST 请求的 body
    if request.method == "POST":
        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            # JSON 数据
            try:
                record["json_body"] = request.get_json(force=True, silent=True)
            except Exception:
                record["json_body"] = None
        elif "application/x-www-form-urlencoded" in content_type:
            # 表单数据
            record["form_data"] = request.form.to_dict()
        else:
            # 其他类型，例如心电图的原始二进制数据
            raw_data = request.get_data()
            # 将二进制数据 base64 编码后存储，避免乱码
            record["binary_body_base64"] = base64.b64encode(raw_data).decode("ascii")
            record["binary_body_length"] = len(raw_data)

    return record

def extract_data() -> dict:
    """
    根据当前请求构建一个统一的记录字典
    :return: 包含时间戳、来源、方法、路径、参数、数据等信息的字典
    """
    # 处理 POST 请求的 body
    received = None
    if request.method == "POST":
        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            # JSON 数据
            try:
                received = request.get_json(force=True, silent=True)
            except Exception as e:
                logger.error(f"解析智能手表推送的数据异常, {e}")
        elif "application/x-www-form-urlencoded" in content_type:
            # 表单数据
            received = request.form.to_dict()
        else:
            logger.error(f"不支持的 Content-Type: {content_type}")

    return received

def handle_time(timestamp_ms):
    timestamp_s = timestamp_ms / 1000
    dt = datetime.fromtimestamp(timestamp_s)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@special_system.route("/devices/receivedata", methods=["GET", "POST"])
def receive_data():
    """
    统一接收设备上报数据的端点
    对应文档中所有的上行数据接口：action=sensor, submitsport, submitbloodglucose,
    calllogs, submitsleep, submitlocation, police, chat, qrcode, submitecg 等
    """
    try:
        # 构建记录
        record = build_record()
        action = record["args"].get("action", "unknown")
        record["action"] = action

        # 保存到文件
        save_record(record)
        received = extract_data()
        if 'alarmList' in received:
            save_record({
                "alarmId": received.get('alarmList')[0].get('alarmId'),
                "imei": received.get('alarmList')[0].get('imei'),
                # 报警类型
                "alarmType": received.get('alarmList')[0].get('alarmType'),
                # 报警名称
                "alarmName": received.get('alarmList')[0].get('alarmName'),
                # 报警开始时间
                "alarmTime": received.get('alarmList')[0].get('alarmTime'),
                "coorTypes": received.get('alarmList')[0].get('coorTypes'),
                "tenantCode": received.get('alarmList')[0].get('tenantCode')
            }, ALARM_FILE)
        elif 'positionList' in received:
            save_record({
                "lat": received.get('positionList')[0].get('lat'),
                "lon": received.get('positionList')[0].get('lon'),
                "imei": received.get('positionList')[0].get('imei'),
                "dateTime": received.get('positionList')[0].get('dateTime'),
                "address": received.get('positionList')[0].get('address'),
            }, POSITION_FILE)
        elif 'heartHealthList' in received:
            save_record({
                # 血氧 单位%
                "bloodOxygen": received.get('heartHealthList')[0].get('bloodOxygen'),
                # 心率 单位min
                "heartRate": received.get('heartHealthList')[0].get('heartRate'),
                # 体温
                "temperature": received.get('heartHealthList')[0].get('temperature'),
                # 血压-收缩压 单位mmHg
                "systolicPressure": received.get('heartHealthList')[0].get('systolicPressure'),
                # 血压-舒张压 单位mmHg
                "diastolicPressure": received.get('heartHealthList')[0].get('diastolicPressure'),
                # 佩戴状态 0未佩戴 1佩戴
                "wearStatus": received.get('heartHealthList')[0].get('wearStatus'),
                # 上传类型 0定时上报 1主动上报
                "uploadType": received.get('heartHealthList')[0].get('uploadType'),
                "imei": received.get('heartHealthList')[0].get('imei'),
                # 创建时间
                "createTime": handle_time(received.get('heartHealthList')[0].get('createTime'))
            }, HEALTH_FILE)

        # 记录日志
        logger.debug(f"Received {request.method} request, action={action}, from {request.remote_addr}")

        # 根据文档，成功返回字符串 "1"
        return Response("1", status=200, mimetype="text/plain")

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        # 异常时返回非 200 状态码
        return Response("Internal Server Error", status=500, mimetype="text/plain")


def read_file_data(file_path, imei=None, start=None, end=None, time_field='createTime'):
    """
    读取文件，按 IMEI 和时间范围过滤，返回记录列表。
    :param file_path: 文件路径
    :param imei: 可选，IMEI 精确匹配
    :param start: 可选，时间范围起始（字符串，格式 "YYYY-MM-DD HH:MM:SS"）
    :param end: 可选，时间范围结束
    :param time_field: 记录中的时间字段名
    :return: 记录列表（字典）
    """
    records = []
    if not os.path.exists(file_path):
        return records
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # IMEI 过滤
            # if imei and rec.get('imei') != imei:
            #     continue
            # 时间过滤
            time_val = rec.get(time_field)
            if time_val:
                if start and time_val < start:
                    continue
                if end and time_val > end:
                    continue
            records.append(rec)
    return records


@special_system.route('/data/heart', methods=['GET'])
def api_heart():
    page = int(request.args.get('page', 0))
    size = int(request.args.get('size', 20))
    imei = request.args.get('imei', '').strip() or None
    start = request.args.get('start', '').strip() or None
    end = request.args.get('end', '').strip() or None

    records = read_file_data(HEALTH_FILE, imei, start, end, 'createTime')
    records = sorted(records, key=lambda x: x.get('createTime'), reverse=True)
    total = len(records)
    start_idx = page * size
    end_idx = start_idx + size
    content = records[start_idx:end_idx]
    return jsonify({
        'content': content,
        'totalElements': total,
        'totalPages': (total + size - 1) // size if total else 0,
        'size': size,
        'number': page
    })

@special_system.route('/data/heart1', methods=['GET'])
def api_heart1():
    page = int(request.args.get('page', 0))
    size = int(request.args.get('size', 20))
    imei = request.args.get('imei', '').strip() or None
    start = request.args.get('start', '').strip() or None
    end = request.args.get('end', '').strip() or None

    sql = """ SELECT  病人id AS 住院id, CONVERT(VARCHAR(20), 时间点, 120) AS createTime,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '心率' THEN 结果 ELSE NULL END) AS heartRate,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '血氧饱和度' THEN 结果 ELSE NULL END) AS bloodOxygen,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '体温' THEN 结果 ELSE NULL END) AS temperature,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '脉搏' THEN 结果 ELSE NULL END) AS 脉搏,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '呼吸' THEN 结果 ELSE NULL END) AS 呼吸,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '收缩压' THEN 结果 ELSE NULL END) AS systolicPressure,
    MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '舒张压' THEN 结果 ELSE NULL END) AS diastolicPressure,
    0 uploadType, 1 wearStatus, '865593070726763' imei  FROM clinicdata.dbo.特护单 
    WHERE 病人id = '6978939'  AND 时间点 >= '2026-06-26' GROUP BY 病人id, CONVERT(VARCHAR(20), 时间点, 120)
    ORDER BY createTime desc """
    if start and end :
        sql = f""" SELECT  病人id AS 住院id, CONVERT(VARCHAR(20), 时间点, 120) AS createTime,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '心率' THEN 结果 ELSE NULL END) AS heartRate,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '血氧饱和度' THEN 结果 ELSE NULL END) AS bloodOxygen,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '体温' THEN 结果 ELSE NULL END) AS temperature,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '脉搏' THEN 结果 ELSE NULL END) AS 脉搏,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '呼吸' THEN 结果 ELSE NULL END) AS 呼吸,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '收缩压' THEN 结果 ELSE NULL END) AS systolicPressure,
        MAX(CASE WHEN 项目分类 = '生命体征' AND 项目名称 = '舒张压' THEN 结果 ELSE NULL END) AS diastolicPressure,
        0 uploadType, 1 wearStatus, '865593070726763' imei  FROM clinicdata.dbo.特护单 
        WHERE 病人id = '6978939'  AND 时间点 >= '{start}' AND 时间点 <= '{end}' GROUP BY 病人id, CONVERT(VARCHAR(20), 时间点, 120)
        ORDER BY createTime desc """



    records = global_tools.call_query_sqlserver(sql)

    total = len(records)
    start_idx = page * size
    end_idx = start_idx + size
    content = records[start_idx:end_idx]
    return jsonify({
        'content': content,
        'totalElements': total,
        'totalPages': (total + size - 1) // size if total else 0,
        'size': size,
        'number': page
    })


@special_system.route('/data/position', methods=['GET'])
def api_position():
    page = int(request.args.get('page', 0))
    size = int(request.args.get('size', 20))
    imei = request.args.get('imei', '').strip() or None
    start = request.args.get('start', '').strip() or None
    end = request.args.get('end', '').strip() or None

    records = read_file_data(POSITION_FILE, imei, start, end, 'dateTime')
    records = sorted(records, key=lambda x: x.get('dateTime'), reverse=True)
    total = len(records)
    start_idx = page * size
    end_idx = start_idx + size
    content = records[start_idx:end_idx]
    return jsonify({
        'content': content,
        'totalElements': total,
        'totalPages': (total + size - 1) // size if total else 0,
        'size': size,
        'number': page
    })

@special_system.route('/data/alarm', methods=['GET'])
def api_alarm():
    page = int(request.args.get('page', 0))
    size = int(request.args.get('size', 20))
    imei = request.args.get('imei', '').strip() or None
    start = request.args.get('start', '').strip() or None
    end = request.args.get('end', '').strip() or None

    records = read_file_data(ALARM_FILE, imei, start, end, 'alarmTime')
    records = sorted(records, key=lambda x: x.get('alarmTime'), reverse=True)
    total = len(records)
    start_idx = page * size
    end_idx = start_idx + size
    content = records[start_idx:end_idx]
    return jsonify({
        'content': content,
        'totalElements': total,
        'totalPages': (total + size - 1) // size if total else 0,
        'size': size,
        'number': page
    })




# =========================================================================================
# ======================================== 自动下载发票 ========================================
# =========================================================================================



@special_system.route("/run_tax/<vm_id>/<path:subpath>", methods=["GET", "POST"])
def forward_request(vm_id, subpath):

    target_url = f"http://192.168.3.121:5000/run_tax/{vm_id}/{subpath}"
    # 把原请求的参数、方法、body 都转过去
    if request.method == "GET":
        resp = requests.get(target_url, params=request.args, timeout=30)
    else:
        resp = requests.request(
            method=request.method,
            url=target_url,
            params=request.args,
            data=request.data,
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            timeout=30,
        )
    # 把目标响应原样返回
    return (resp.content, resp.status_code, dict(resp.headers))



# ======================================== DIP ========================================


# 定义表头字段（按照图片中的顺序）
FIELDS = [
    "医保结算流水号",
    "住院号",
    "住院次数",
    "年龄",
    "性别",
    "患者费别",
    "总费用",
    "住院医师",
    "入院时间",
    "出院时间",
    "诊断",
    "病案诊断",
    "手术",
    "医嘱",
    "出院记录",
    "手术记录",
    "现DIP代码",
    "现DIP名称",
    "现DIP分值",
    "现DIP盈亏",
    "现DIP倍率",
]


def safe_get(record: dict, field: str, default=""):
    """安全地从记录中获取字段值，若缺失或为None则返回默认值"""
    value = record.get(field, default)
    return value if value is not None else default

@special_system.route("/upload_ai_dip", methods=["POST"])
def upload_ai_dip():
    req_json = request.get_json()
    if not req_json:
        return jsonify({"error": "上传的结构必须是 JSON 格式", 'code': 40000})

    if isinstance(req_json, list):
        data = req_json
    elif isinstance(req_json, str):
        data = json.loads(req_json)
    elif isinstance(req_json, dict):
        data = req_json.get("data")
        if not isinstance(data, list):
            data = json.loads(data)
        if not isinstance(data, list):
            return jsonify({"error": "data 字段必须是 JSON 列表", 'code': 40000})
    else:
        return jsonify({"error": "请求体必须是列表或包含 data 字段的对象", 'code': 40000})

    if not data:
        return jsonify({"error": "上传数据不能为空", 'code': 40000})

    special_server.handle_ai_dip(data)

    return jsonify({"data": "success", 'code': 20000})

@special_system.route("/export_grouped_excel1", methods=["POST"])
def export_grouped_excel1():
    req_json = request.get_json()
    if not req_json:
        return jsonify({"error": "请求体必须是 JSON 格式", 'code': 40000})

    # 1. 获取并校验入参
    departments = req_json.get('dept_names')
    start_date_str = req_json.get('start_date')
    end_date_str = req_json.get('end_date')
    comp_name = req_json.get('comp_name')

    if not departments or not start_date_str or not end_date_str:
        return jsonify({
            "error": "缺少必要参数: department, start_date, end_date",
            'code': 40000
        })

    # 2. 解析日期（格式：YYYY-MM-DD）
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "日期格式错误，请使用 YYYY-MM-DD", 'code': 40000})

    if start_date > end_date:
        return jsonify({"error": "开始日期不能晚于结束日期", 'code': 40000})

    # 3. 从数据库查询数据（假设模型字段：departments, discharge_date）
    data = special_server.query_dept_patients(departments, start_date.strftime('%Y-%m-%d'),
                                              end_date.strftime('%Y-%m-%d'), comp_name)
    if not data:
        return jsonify({"error": "未查询到符合条件的数据", 'code': 40000})

    # ---------- 预读固定文件 ----------
    prompt_path = '/Users/gaoyanliang/各个系统文档整理/ai-dip/各科室患者DIP数据/脑病重症病区/提供给AI的提示词.txt' if global_config.run_in_local else '/home/gyl/提供给AI的提示词.txt'
    prompt_content = b""
    if os.path.exists(prompt_path):
        with open(prompt_path, "rb") as f:
            prompt_content = f.read()
    extra_files_base = {
        "提供给AI的提示词.txt": prompt_content,
        "跑AI时不需要再上传综合组排除操作文件.txt": b"No need to upload ..."
    }

    # ---------- 2. 预读 DIP 目录库并缓存每个前缀的过滤结果 ----------
    # 定义合并规则，有些科室病种不能分的太细
    MERGE_GROUPS = {
        'I': ['I0', 'I2', 'I3', 'I4', 'I5'],
        # 未来可增加，例如：
        # 'A': ['A1', 'A2'],
    }
    # 构建前缀→组名映射
    prefix_to_group = {}
    for group_name, prefixes in MERGE_GROUPS.items():
        for p in prefixes:
            prefix_to_group[p] = group_name

    # ---------- 2. 预扫描数据，收集原始前缀、组名及组→前缀列表 ----------
    group_to_prefixes = defaultdict(list)  # 组名 → 该组包含的所有原始前缀（去重）
    group_names = set()  # 所有用到的组名
    temp_data = []  # 暂存每项的原始前缀，避免二次计算（可选）

    for item in data:
        dip_code = item.get("现DIP代码", "").replace(' ', '')
        original_pref = dip_code[:2] if len(dip_code) >= 2 else (dip_code + '0' if dip_code else '未知')
        group_key = prefix_to_group.get(original_pref, original_pref)
        group_names.add(group_key)
        if original_pref not in group_to_prefixes[group_key]:
            group_to_prefixes[group_key].append(original_pref)
        # 可将 (item, original_pref, group_key) 暂存，供后续分组直接用，减少再次遍历
        temp_data.append((item, original_pref, group_key))

    # ---------- 3. 按组生成 DIP 目录库缓存（替代原 filter_excel_cache 逻辑） ----------
    filtered_excel_cache = {}
    dip_path = '/Users/gaoyanliang/各个系统文档整理/ai-dip/各科室患者DIP数据/脑病重症病区/2026年DIP病种目录库.xlsx' \
        if global_config.run_in_local else '/home/gyl/2026年DIP病种目录库.xlsx'

    if os.path.exists(dip_path):
        try:
            df_dip = pd.read_excel(dip_path, dtype=str, engine='openpyxl')
            df_dip['诊断编码'] = df_dip['诊断编码'].astype(str).str.strip().fillna('')
            for gname, prefixes_list in group_to_prefixes.items():
                # 若组内含有 '未知'，则无法按诊断编码过滤，直接使用完整目录
                if '未知' in prefixes_list:
                    df_filtered = df_dip
                else:
                    df_filtered = df_dip[df_dip['诊断编码'].str[:2].isin(prefixes_list)]
                if df_filtered.empty:
                    logging.warning(f"组 {gname} 的前缀 {prefixes_list} 在目录库中无匹配项，将使用完整目录库")
                    df_filtered = df_dip
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                buffer.seek(0)
                filtered_excel_cache[gname] = buffer.getvalue()
        except Exception as e:
            logging.error(f"读取/过滤目录库失败: {e}")
            # 降级：读取原始文件作为统一内容
            with open(dip_path, "rb") as f:
                raw_content = f.read()
            for gname in group_names:
                filtered_excel_cache[gname] = raw_content
    else:
        # 文件不存在，填充提示信息
        for gname in group_names:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                pd.DataFrame([{"备注": "DIP目录库文件未找到"}]).to_excel(writer, index=False)
            buffer.seek(0)
            filtered_excel_cache[gname] = buffer.getvalue()

    # ---------- 3. 按 DIP 前缀分组 ----------
    grouped = defaultdict(list)
    for item, original_pref, group_key in temp_data:
        # 注意：此处需要 pop 掉 "现DIP代码"，但 item 是原始字典的引用，pop 会影响后续，不过不再使用原数据，可以
        item.pop("现DIP代码", None)  # 原代码已经 pop，此处保持一致
        grouped[group_key].append(item)

    # ---------- 4. 生成总 ZIP ----------
    final_zip_buffer = BytesIO()
    with zipfile.ZipFile(final_zip_buffer, "w", zipfile.ZIP_DEFLATED) as final_zf:
        for dip_prefix, patients_in_group in grouped.items():
            # 准备当前分组的额外文件
            extra_files = extra_files_base.copy()
            extra_files["2026年DIP病种目录库.xlsx"] = filtered_excel_cache.get(dip_prefix, b"")

            # 创建子 ZIP
            sub_zip_buffer = BytesIO()
            with zipfile.ZipFile(sub_zip_buffer, "w", zipfile.ZIP_DEFLATED) as sub_zf:
                chunk_size = 20
                for chunk_idx, start_idx in enumerate(range(0, len(patients_in_group), chunk_size)):
                    chunk = patients_in_group[start_idx:start_idx + chunk_size]
                    part_num = chunk_idx + 1

                    rows = [{field: safe_get(record, field) for field in FIELDS} for record in chunk]
                    df_chunk = pd.DataFrame(rows, columns=FIELDS)
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        df_chunk.to_excel(writer, index=False)
                    excel_buffer.seek(0)
                    sub_zf.writestr(f"{dip_prefix}_第{part_num}部分.xlsx", excel_buffer.getvalue())

                # 写入固定文件
                for fname, fcontent in extra_files.items():
                    if fcontent:
                        sub_zf.writestr(fname, fcontent)

            sub_zip_buffer.seek(0)
            final_zf.writestr(f"{dip_prefix}_分组数据.zip", sub_zip_buffer.getvalue())

    final_zip_buffer.seek(0)
    return send_file(
        final_zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{departments[0]}_DIP分组汇总.zip"
    )



@special_system.route("/completed_patients", methods=["POST", "GET"])
def completed_dip_patients():
    req_json = request.get_json()
    if not req_json:
        return jsonify({"error": "请求体必须是 JSON 格式", 'code': 50000})

    # 1. 查询
    data = special_server.completed_dip_patients(req_json)
    if 'page_no' in req_json and 'no_on_page' in req_json:
        return jsonify(data)
    else:
        # 转 DataFrame（字段映射 + datetime 格式化）
        df = pd.DataFrame(data.get('patient_l'))

        def safe_file_name(name: str) -> str:
            import re
            # 将 逗号、空格、斜杠等替换为 _
            return re.sub(r'[\\/*?:"<>|]', '_', name)

        file_name = safe_file_name('_'.join(req_json.get('dept_name', [])))
        start_d = req_json.get('start_d', '')
        end_d = req_json.get('end_d', '')
        download_name = f"{file_name}_{start_d}_{end_d}_已完成患者清单.xlsx"

        # 内存写出 xlsx 并下载
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="已完成患者数据")
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name=download_name)



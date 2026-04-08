import base64
import errno
import hmac
import json
import os
import time
import uuid
from datetime import datetime
import hashlib

import paramiko
import requests
from flask import Blueprint, request

from gylmodules import global_config, global_tools
from gylmodules.a_special import special_server
from gylmodules.global_tools import api_response
from gylmodules.utils.db_utils import DbUtil

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
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = """INSERT INTO nsyy_gyl.a_surgical_transfer (patient_id, number, patient_name, patient_info,
                                    timing, record_time) VALUES (%s, %s, %s, %s, %s, %s)"""
    args = (patient_id, number, patient_name, json.dumps(data, ensure_ascii=False, default=str),
            scan_timing, data['record_time'])
    db.execute(insert_sql, args, need_commit=True)
    del db
    return data


# json_data = {
#     "patient_code": "BR|10151903|1",
#     "scan_timing": 1
# }
#
# surgical_transfer_data(json_data)




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



# parms = {
#     "fphm": "25442000000742066777",
#     "kprq": "20251126",
#     "noTaxAmount": "24.65",
#     "jshj": "24.90"
# }
#
#
# parms = {
#     "code": "01,32,,25442000000742066777,24.90,20251126,,70EC"
# }
#
#
# data = invoice_verification(parms)
# print(data)



"""查询入院三天未提交病案首页的患者列表"""


@special_system.route('/unsubmitted', methods=['POST', 'GET'])
@api_response
def unsubmitted():
    return special_server.query_unpage_patients()



"""查询前一天 病案首页有变化的患者列表"""


@special_system.route('/modified-today', methods=['POST', 'GET'])
@api_response
def modified_today():
    return special_server.query_dip_patients()


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

    # 远程目录（按月份）
    remote_dir = f"/home/gyl/tax_fapiao/{datetime.now().month}"
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

        # 确保远程目录存在
        try:
            sftp.stat(remote_dir)
        except IOError as e:
            if e.errno == errno.ENOENT:
                sftp.mkdir(remote_dir)
            else:
                raise

        # 上传文件
        sftp.putfo(file.stream, remote_path)

        sftp.close()
        transport.close()

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


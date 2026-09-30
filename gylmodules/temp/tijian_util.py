import hmac
import json
import time
import random
import string
import xml.etree.ElementTree as ET
import requests
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


# ==================== 1. 签名工具（对应文档 1.4 节） ====================
def generate_sign(api_key, timestamp, nonce, app_secret):

    # 1. 将 apiKey、timestamp、nonce 按 GB2312 字节顺序排序后拼接 对应 Java 的 generateJoinStr 方法
    items = [api_key, timestamp, nonce]
    items.sort(key=lambda s: s.encode('gb2312'))
    data = ''.join(items)

    # 2. 使用 HmacSHA256 对数据进行签名，返回十六进制小写字符串
    key = app_secret.encode('utf-8')
    message = data.encode('utf-8')
    mac = hmac.new(key, message, hashlib.sha256)
    signature = mac.hexdigest()

    # 根据文档 1.2 节，accessTokens 参数值为 "nonce=xxx&timestamp=xxx&sign=xxx&appKey=xxx"
    sign_str = f"appkey={api_key},timestamp={timestamp},nonceStr={nonce},sign={signature}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()


# ==================== 2. AES 加密工具（对应文档 2.3 节） ====================

def aes_encrypt(content: str, password: str) -> str:
    """
    完全等价 Java SHA1PRNG + AES/ECB/PKCS5Padding
    密钥 = SHA-1(SHA-1(password.getBytes("UTF-8")))[:16]
    """
    # 两次 SHA-1
    h1 = hashlib.sha1(password.encode('utf-8')).digest()
    h2 = hashlib.sha1(h1).digest()[:16]

    cipher = AES.new(h2, AES.MODE_ECB)
    padded = pad(content.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)

    return encrypted.hex().upper()


# ==================== 3. 构建 XML 请求体（对应文档 2.1.1 节） ====================
def build_exam_archive_xml(data):
    """
    构建职业健康档案 XML 数据
    data: 字典，包含体检档案数据
    """
    root = ET.Element("DataExchange")

    # Header
    header = ET.SubElement(root, "Header")
    doc_id = ET.SubElement(header, "DocumentId")
    # 文档标识: 机构编码-业务类别代码-当前时间-5位随机码
    # 这里简化处理，实际使用时请替换为真实机构编码
    doc_id.text = f"{data.get('org_code', '')}-{data.get('exam_type_code', '')}-{time.strftime('%Y%m%d%H%M%S%f')[:-3]}-{''.join(random.choices(string.digits, k=5))}"

    # EventBody
    event_body = ET.SubElement(root, "EventBody")
    record_list = ET.SubElement(event_body, "HEALTH_EXAM_RECORD_LIST")

    # HEALTH_EXAM_RECORD
    record = ET.SubElement(record_list, "HEALTH_EXAM_RECORD")
    record.set("ID", data.get("id", ""))

    # 用人单位信息
    enterprise_info = ET.SubElement(record, "ENTERPRISE_INFO")
    ET.SubElement(enterprise_info, "ENTERPRISE_NAME").text = data.get("enterprise_name", "")
    ET.SubElement(enterprise_info, "CREDIT_CODE").text = data.get("credit_code", "")
    ET.SubElement(enterprise_info, "ECONOMIC_TYPE_CODE").text = data.get("economic_type_code", "")
    ET.SubElement(enterprise_info, "INDUSTRY_CATEGORY_CODE").text = data.get("industry_category_code", "")
    ET.SubElement(enterprise_info, "BUSINESS_SCALE_CODE").text = data.get("business_scale_code", "")
    ET.SubElement(enterprise_info, "ADDRESS_CODE").text = data.get("address_code", "")
    ET.SubElement(enterprise_info, "ADDRESS_DETAIL").text = data.get("address_detail", "")
    ET.SubElement(enterprise_info, "ADDRESS_ZIP_CODE").text = data.get("address_zip_code", "")
    ET.SubElement(enterprise_info, "ENTERPRISE_CONTACT").text = data.get("enterprise_contact", "")
    ET.SubElement(enterprise_info, "CONTACT_TELPHONE").text = data.get("contact_telphone", "")
    ET.SubElement(enterprise_info, "ALL_NAME").text = data.get("all_name", "")
    ET.SubElement(enterprise_info, "ISSUBSIDIARY").text = data.get("issubsidiary", "")
    ET.SubElement(enterprise_info, "TWOLEVELCODE").text = data.get("twolevelcode", "")

    # 用工单位信息
    employer_info = ET.SubElement(record, "ENTERPRISE_INFO_EMPLOYER")
    ET.SubElement(employer_info, "ENTERPRISE_NAME_EMPLOYER").text = data.get("enterprise_name_employer", "")
    ET.SubElement(employer_info, "CREDIT_CODE_EMPLOYER").text = data.get("credit_code_employer", "")
    ET.SubElement(employer_info, "ECONOMIC_TYPE_CODE_EMPLOYER").text = data.get("economic_type_code_employer", "")
    ET.SubElement(employer_info, "INDUSTRY_CATEGORY_CODE_EMPLOYER").text = data.get("industry_category_code_employer", "")
    ET.SubElement(employer_info, "BUSINESS_SCALE_CODE_EMPLOYER").text = data.get("business_scale_code_employer", "")
    ET.SubElement(employer_info, "ADDRESS_CODE_EMPLOYER").text = data.get("address_code_employer", "")
    ET.SubElement(employer_info, "ALL_NAME_EMPLOYER").text = data.get("all_name_employer", "")
    ET.SubElement(employer_info, "ISSUBSIDIARY_EMPLOYER").text = data.get("issubsidiary_employer", "")
    ET.SubElement(employer_info, "TWOLEVELCODE_EMPLOYER").text = data.get("twolevelcode_employer", "")

    # 劳动者信息
    worker_info = ET.SubElement(record, "WORKER_INFO")
    ET.SubElement(worker_info, "WORKER_NAME").text = data.get("worker_name", "")
    ET.SubElement(worker_info, "ID_CARD_TYPE_CODE").text = data.get("id_card_type_code", "")
    ET.SubElement(worker_info, "ID_CARD").text = data.get("id_card", "")
    ET.SubElement(worker_info, "GENDER_CODE").text = data.get("gender_code", "")
    ET.SubElement(worker_info, "BIRTH_DATE").text = data.get("birth_date", "")
    ET.SubElement(worker_info, "WORKER_TELPHONE").text = data.get("worker_telphone", "")

    # 个人生活史
    personal_history = ET.SubElement(record, "PERSONAL_HISTORY")
    ET.SubElement(personal_history, "SMOKING_STATUS").text = data.get("smoking_status", "")
    ET.SubElement(personal_history, "PERSONAL_HISTORY_YEAR").text = data.get("personal_history_year", "")
    ET.SubElement(personal_history, "PERSONAL_HISTORY_MONTH").text = data.get("personal_history_month", "")
    ET.SubElement(personal_history, "DAILY_SMOKING_VOLUME").text = data.get("daily_smoking_volume", "")

    # 体检基本信息
    ET.SubElement(record, "JC_TYPE").text = data.get("jc_type", "")
    ET.SubElement(record, "EXAM_TYPE_CODE").text = data.get("exam_type_code", "")
    ET.SubElement(record, "EXAM_DATE").text = data.get("exam_date", "")
    ET.SubElement(record, "CONTACT_FACTOR_CODE").text = data.get("contact_factor_code", "")
    ET.SubElement(record, "CONTACT_FACTOR_OTHER").text = data.get("contact_factor_other", "")
    ET.SubElement(record, "FACTOR_CODE").text = data.get("factor_code", "")
    ET.SubElement(record, "FACTOR_OTHER").text = data.get("factor_other", "")
    ET.SubElement(record, "WORK_TYPE_CODE").text = data.get("work_type_code", "")
    ET.SubElement(record, "OTHER_WORK_TYPE").text = data.get("other_work_type", "")
    ET.SubElement(record, "IS_REVIEW").text = data.get("is_review", "")
    ET.SubElement(record, "PROTECTIVE_EQUIPMENT_CODE").text = data.get("protective_equipment_code", "")
    ET.SubElement(record, "AREA_CODE").text = data.get("area_code", "")
    ET.SubElement(record, "ORG_CODE").text = data.get("org_code", "")

    # 体检结论列表
    conclusion_list = ET.SubElement(record, "EXAM_CONCLUSION_LIST")
    for conclusion in data.get("exam_conclusion_list", []):
        c = ET.SubElement(conclusion_list, "EXAM_CONCLUSION")
        ET.SubElement(c, "ITAM_CODE").text = conclusion.get("ITAM_CODE", "")
        ET.SubElement(c, "ITAM_NAME").text = conclusion.get("ITAM_NAME", "")
        ET.SubElement(c, "EXAM_CONCLUSION_CODE").text = conclusion.get("EXAM_CONCLUSION_CODE", "")
        ET.SubElement(c, "YSZYB_CODE").text = conclusion.get("YSZYB_CODE", "")
        ET.SubElement(c, "ENTERPRISE_NAME").text = conclusion.get("ENTERPRISE_NAME", "")
        ET.SubElement(c, "ZYJJZ_NAME").text = conclusion.get("ZYJJZ_NAME", "")
        ET.SubElement(c, "QTJB_NAME").text = conclusion.get("QTJB_NAME", "")
        ET.SubElement(c, "HARM_START_DATE").text = conclusion.get("HARM_START_DATE", "")
        ET.SubElement(c, "HARM_AGE_YEAR").text = conclusion.get("HARM_AGE_YEAR", "")
        ET.SubElement(c, "HARM_AGE_MONTH").text = conclusion.get("HARM_AGE_MONTH", "")

    # 检查项目列表
    item_list = ET.SubElement(record, "EXAM_ITEM_RESULT_LIST")
    for item in data.get("exam_item_result_list", []):
        i = ET.SubElement(item_list, "EXAM_ITEM_RESULT")
        ET.SubElement(i, "EXAM_ITEM_PNAME").text = item.get("EXAM_ITEM_PNAME", "")
        ET.SubElement(i, "EXAM_ITEM_NAME").text = item.get("EXAM_ITEM_NAME", "")
        ET.SubElement(i, "EXAM_ITEM_CODE").text = item.get("EXAM_ITEM_CODE", "")
        ET.SubElement(i, "EXAM_RESULT_TYPE").text = item.get("EXAM_RESULT_TYPE", "")
        ET.SubElement(i, "EXAM_RESULT").text = item.get("EXAM_RESULT", "")
        ET.SubElement(i, "DATA_VERSION").text = item.get("DATA_VERSION", "")
        ET.SubElement(i, "EXAM_ITEM_UNIT_CODE").text = item.get("EXAM_ITEM_UNIT_CODE", "")
        ET.SubElement(i, "REFERENCE_RANGE_MIN").text = item.get("REFERENCE_RANGE_MIN", "")
        ET.SubElement(i, "REFERENCE_RANGE_MAX").text = item.get("REFERENCE_RANGE_MAX", "")
        ET.SubElement(i, "ABNORMAL").text = item.get("ABNORMAL", "")

    # 其他信息
    ET.SubElement(record, "WRITE_PERSON").text = data.get("write_person", "")
    ET.SubElement(record, "WRITE_PERSON_TELPHONE").text = data.get("write_person_telphone", "")
    ET.SubElement(record, "WRITE_DATE").text = data.get("write_date", "")
    ET.SubElement(record, "REPORT_ORGAN_CREDIT_CODE").text = data.get("report_organ_credit_code", "")
    ET.SubElement(record, "REMARK").text = data.get("remark", "")
    ET.SubElement(record, "EXAM_PHYSICIAN").text = data.get("exam_physician", "")
    ET.SubElement(record, "EXAM_ORG_TYPE").text = data.get("exam_org_type", "")
    ET.SubElement(record, "SIGN_ID").text = data.get("sign_id", "")

    # 生成 XML 字符串并格式化
    rough_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return rough_string
    # reparsed = minidom.parseString(rough_string)
    # return reparsed.toprettyxml(indent="  ")



# ==================== 4. 调用接口 ====================
def call_exam_add(api_key, app_secret, xml_data):
    """
    调用体检档案批量保存接口
    """
    # 生成认证参数
    timestamp = str(int(time.time() * 1000))  # 毫秒时间戳
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    sign = generate_sign(api_key, timestamp, nonce, app_secret)

    # 构建 accessTokens 参数值 格式: nonce=xxx&timestamp=xxx&sign=xxx&appKey=xxx
    access_tokens = f"nonce={nonce}&timestamp={timestamp}&sign={sign}&appKey={api_key}"

    # print("timestamp:", timestamp)
    # print("nonce:", nonce)
    # print("sign:", sign)
    # print("accessTokens:", access_tokens)

    # 对 XML 数据进行 AES 加密（文档 2.0 节要求）
    encrypted_body = aes_encrypt(xml_data, app_secret)
    if encrypted_body is None:
        print("AES 加密失败")
        return None

    headers = {
        "accessTokens": access_tokens,
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    }
    # 发送请求
    url = "https://health.hnzfy.com.cn/reveive/v1/examArchive/examAdd"
    try:
        response = requests.post(url, headers=headers, data=encrypted_body, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.json()
    except Exception as e:
        print(f"请求异常: {e}")
        return None



def excel_to_jsons(file_path, sheet_num: int = 0, header_line: int = 1, keys: list = None):
    """
    :param file_path: Excel 文件路径
    :param sheet_num: 工作表索引，从0开始
    :param header_line: 表头所在行号（从1开始）
    :param keys: 需要提取的列名列表，若为 None 则提取所有列
    :return: JSON 字符串列表
    """
    import openpyxl
    wbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wbook[wbook.sheetnames[sheet_num]]

    # 读取所有表头
    headers = [cell.value for cell in sheet[header_line]]

    # 如果指定了 keys，则只保留这些列；否则保留所有列
    if keys is not None:
        # 仅保留在 keys 中出现的列名（按 keys 的顺序保留，便于排序）
        # 如果某个 key 不在 headers 中，此处会被忽略（也可主动抛出异常）
        valid_keys = [k for k in keys if k in headers]
        # 构建列索引映射：列名 -> 列索引（0-based）
        col_indices = {name: idx for idx, name in enumerate(headers) if name in valid_keys}
        # 为了后续 zip 顺序一致，按 valid_keys 顺序取出列值
        # 由于 iter_rows 按列顺序返回，我们需要按索引提取，但更简单的是直接用行字典过滤
    else:
        valid_keys = headers

    results = []
    for row in sheet.iter_rows(min_row=header_line + 1, values_only=True):  # 从表头下一行开始
        # 将整行与所有表头组合成字典
        full_dict = dict(zip(headers, row))
        # 如果指定了 keys，则过滤字典
        if keys is not None:
            row_dict = {k: full_dict[k] for k in valid_keys if k in full_dict}
        else:
            row_dict = full_dict

        # 如果需要写入文件，需要将row_dict转为JSON字符串
        # row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
        results.append(row_dict)

    return results


def deduplicate_by_month(conclusion_list, key):
    seen_months = set()
    unique_list = []
    for item in conclusion_list:
        month = item.get(key)  # 注意字段名需与数据一致（大写）
        if month not in seen_months:
            seen_months.add(month)
            unique_list.append(item)
    return unique_list

# ==================== 5. 示例使用 ====================
if __name__ == "__main__":
    # 配置（请替换为实际申请的 appKey 和 appSecret）
    API_KEY = "iUEIBFsF"
    APP_SECRET = "dd12251fbe08dd5e18ce625a7a53a4b1f320b587"

    data1 = excel_to_jsons("/Users/gaoyanliang/Downloads/dat_202608271822.xlsx")
    data1 = {f"{item.pop('TJBH')}-{item.pop('TJCS')}": item for item in data1}
    data2 = excel_to_jsons("/Users/gaoyanliang/Downloads/dat_202608271823.xlsx")
    data22 = {}
    for item in data2:
        key = f"{item.pop('TJBH')}-{item.pop('TJCS')}"
        if key not in data22:
            data22[key] = []
        data22[key].append(item)
    data3 = excel_to_jsons("/Users/gaoyanliang/Downloads/dat_202608271853.xlsx")
    data33 = {}
    for item in data3:
        key = f"{item.pop('TJBH')}-{item.pop('TJCS')}"
        if key not in data33:
            data33[key] = []
        data33[key].append(item)


    for key, value in data1.items():
        merged = value
        merged = {k: str(v) for k, v in merged.items()}

        v1 = data22.get(key, [])
        for it in v1:
            if it['HARM_AGE_MONTH']:
                it['HARM_AGE_MONTH'] = str(it['HARM_AGE_MONTH'])
            if it['HARM_AGE_YEAR']:
                it['HARM_AGE_YEAR'] = str(it['HARM_AGE_YEAR'])
            if it['HARM_START_DATE']:
                it['HARM_START_DATE'] = it['HARM_START_DATE'].strftime("%Y-%m-%d")
            it = {k: str(v) for k, v in it.items()}
        v2 = data33.get(key, [])
        v2 = deduplicate_by_month(v2, 'EXAM_ITEM_CODE')

        for it in v2:
            it['ABNORMAL'] = str(it['ABNORMAL'])
            it['REFERENCE_RANGE_MIN'] = str(it['REFERENCE_RANGE_MIN'])
            it['REFERENCE_RANGE_MAX'] = str(it['REFERENCE_RANGE_MAX'])
            it = {k: str(v) for k, v in it.items()}
        merged['EXAM_CONCLUSION_LIST'] = v1
        merged['EXAM_ITEM_RESULT_LIST'] = v2

        sign_id = merged.get('SIGN_ID', '').split('_')[0]
        merged['SIGN_ID'] = f"{sign_id}{''.join(random.choices(string.digits, k=4))}"

        print(key, json.dumps(merged, ensure_ascii=False, default=str))

        # print(value)
        test_data = {
            "id": merged.get('SIGN_ID', ''),
            "enterprise_name": merged.get('ENTERPRISE_NAME', ''),
            "credit_code": merged.get('CREDIT_CODE', ''),
            "economic_type_code": merged.get('ECONOMIC_TYPE_CODE', ''),
            "industry_category_code": merged.get('INDUSTRY_CATEGORY_CODE', ''),
            "business_scale_code": merged.get('BUSINESS_SCALE_CODE', ''),
            "address_code": merged.get('ADDRESS_CODE', ''),
            "address_detail": merged.get('ADDRESS_DETAIL', ''),
            "address_zip_code": merged.get('ADDRESS_ZIP_CODE', ''),
            "enterprise_contact": merged.get('ENTERPRISE_CONTACT', ''),
            "contact_telphone": merged.get('CONTACT_TELPHONE', ''),
            "all_name": merged.get('ALL_NAME', ''),
            "issubsidiary": merged.get('ISSUBSIDIARY', ''),
            "twolevelcode": merged.get('TWOLEVELCODE', ''),
            "enterprise_name_employer": merged.get('ENTERPRISE_NAME_EMPLOYER', ''),
            "credit_code_employer": merged.get('CREDIT_CODE_EMPLOYER', ''),
            "economic_type_code_employer": merged.get('ECONOMIC_TYPE_CODE_EMPLOYER', ''),
            "industry_category_code_employer": merged.get('INDUSTRY_CATEGORY_CODE_EMPLOYER', ''),
            "business_scale_code_employer": merged.get('BUSINESS_SCALE_CODE_EMPLOYER', ''),
            "address_code_employer": merged.get('ADDRESS_CODE_EMPLOYER', ''),
            "all_name_employer": merged.get('ALL_NAME_EMPLOYER', ''),
            "issubsidiary_employer": merged.get('ISSUBSIDIARY_EMPLOYER', ''),
            "twolevelcode_employer": merged.get('TWOLEVELCODE_EMPLOYER', ''),
            "worker_name": merged.get('WORKER_NAME', ''),
            "id_card_type_code": merged.get('ID_CARD_TYPE_CODE', ''),
            "id_card": merged.get('ID_CARD', ''),
            "gender_code": merged.get('GENDER_CODE', ''),
            "birth_date": merged.get('BIRTH_DATE', ''),
            "worker_telphone": merged.get('WORKER_TELPHONE', ''),
            "smoking_status": merged.get('SMOKING_STATUS', ''),
            "personal_history_year": merged.get('PERSONAL_HISTORY_YEAR', ''),
            "personal_history_month": merged.get('PERSONAL_HISTORY_MONTH', ''),
            "daily_smoking_volume": merged.get('DAILY_SMOKING_VOLUME', ''),
            "jc_type": merged.get('JC_TYPE', ''),
            "exam_type_code": merged.get('EXAM_TYPE_CODE', ''),
            "exam_date": merged.get('EXAM_DATE', ''),
            "contact_factor_code": merged.get('CONTACT_FACTOR_CODE', ''),
            "contact_factor_other": merged.get('CONTACT_FACTOR_OTHER', ''),
            "factor_code": merged.get('FACTOR_CODE', ''),
            "factor_other": merged.get('FACTOR_OTHER', ''),
            "work_type_code": merged.get('WORK_TYPE_CODE', ''),
            "other_work_type": merged.get('OTHER_WORK_TYPE', ''),
            "is_review": merged.get('IS_REVIEW', ''),
            "protective_equipment_code": merged.get('PROTECTIVE_EQUIPMENT_CODE', ''),
            "area_code": merged.get('AREA_CODE', ''),
            "org_code": merged.get('ORG_CODE', ''),
            "exam_conclusion_list": merged.get('EXAM_CONCLUSION_LIST', []),
            "exam_item_result_list": merged.get('EXAM_ITEM_RESULT_LIST', []),
            "write_person": merged.get('WRITE_PERSON', ''),
            "write_person_telphone": merged.get('WRITE_PERSON_TELPHONE', ''),
            "write_date": merged.get('WRITE_DATE', ''),
            "report_organ_credit_code": merged.get('REPORT_ORGAN_CREDIT_CODE', ''),
            "remark": merged.get('REMARK', ''),
            "exam_physician": merged.get('EXAM_PHYSICIAN', ''),
            "exam_org_type": merged.get('EXAM_ORG_TYPE', ''),
            "sign_id": merged.get('SIGN_ID', '')
        }

        # 生成 XML
        xml_str = build_exam_archive_xml(test_data)
        xml_str = xml_str.replace("None", "")
        print("生成的 XML:\n", xml_str)

        # 调用接口
        result = call_exam_add(API_KEY, APP_SECRET, xml_str)
        print(f"调用结果:", result)




    # 验证加密
    # test_xml = """<DataExchange><Header><DocumentId>411303066-02-202608271725-86392</DocumentId></Header><EventBody><HEALTH_EXAM_RECORD_LIST><HEALTH_EXAM_RECORD ID="20250603fXZU"><ENTERPRISE_INFO><ENTERPRISE_NAME>中石化华北石油工程有限公司河南钻井分公司</ENTERPRISE_NAME><CREDIT_CODE>91411300317248178H</CREDIT_CODE><ECONOMIC_TYPE_CODE>111</ECONOMIC_TYPE_CODE><INDUSTRY_CATEGORY_CODE>0711</INDUSTRY_CATEGORY_CODE><BUSINESS_SCALE_CODE>02</BUSINESS_SCALE_CODE><ADDRESS_CODE>411305002</ADDRESS_CODE><ADDRESS_DETAIL>南阳市官庄工区中南路南段涧河社区</ADDRESS_DETAIL><ADDRESS_ZIP_CODE>473132</ADDRESS_ZIP_CODE><ENTERPRISE_CONTACT>田玉兵</ENTERPRISE_CONTACT><CONTACT_TELPHONE>13598270539</CONTACT_TELPHONE><ALL_NAME>河南省南阳市官庄工区东兴办事处</ALL_NAME><ISSUBSIDIARY>0</ISSUBSIDIARY><TWOLEVELCODE /></ENTERPRISE_INFO><ENTERPRISE_INFO_EMPLOYER><ENTERPRISE_NAME_EMPLOYER>中石化华北石油工程有限公司河南钻井分公司</ENTERPRISE_NAME_EMPLOYER><CREDIT_CODE_EMPLOYER>91411300317248178H</CREDIT_CODE_EMPLOYER><ECONOMIC_TYPE_CODE_EMPLOYER>111</ECONOMIC_TYPE_CODE_EMPLOYER><INDUSTRY_CATEGORY_CODE_EMPLOYER>0711</INDUSTRY_CATEGORY_CODE_EMPLOYER><BUSINESS_SCALE_CODE_EMPLOYER>02</BUSINESS_SCALE_CODE_EMPLOYER><ADDRESS_CODE_EMPLOYER>411305002</ADDRESS_CODE_EMPLOYER><ALL_NAME_EMPLOYER>河南省南阳市官庄工区东兴办事处</ALL_NAME_EMPLOYER><ISSUBSIDIARY_EMPLOYER>0</ISSUBSIDIARY_EMPLOYER><TWOLEVELCODE_EMPLOYER /></ENTERPRISE_INFO_EMPLOYER><WORKER_INFO><WORKER_NAME>周子厚</WORKER_NAME><ID_CARD_TYPE_CODE>01</ID_CARD_TYPE_CODE><ID_CARD>412924197005041515</ID_CARD><GENDER_CODE>1</GENDER_CODE><BIRTH_DATE>19700504</BIRTH_DATE><WORKER_TELPHONE>17637795510</WORKER_TELPHONE></WORKER_INFO><PERSONAL_HISTORY><SMOKING_STATUS>4</SMOKING_STATUS><PERSONAL_HISTORY_YEAR>0</PERSONAL_HISTORY_YEAR><PERSONAL_HISTORY_MONTH>0</PERSONAL_HISTORY_MONTH><DAILY_SMOKING_VOLUME>0</DAILY_SMOKING_VOLUME></PERSONAL_HISTORY><JC_TYPE>01</JC_TYPE><EXAM_TYPE_CODE>02</EXAM_TYPE_CODE><EXAM_DATE>20250603</EXAM_DATE><CONTACT_FACTOR_CODE>3008</CONTACT_FACTOR_CODE><CONTACT_FACTOR_OTHER></CONTACT_FACTOR_OTHER><FACTOR_CODE>3008</FACTOR_CODE><FACTOR_OTHER></FACTOR_OTHER><WORK_TYPE_CODE>40-002</WORK_TYPE_CODE><OTHER_WORK_TYPE /><IS_REVIEW>0</IS_REVIEW><PROTECTIVE_EQUIPMENT_CODE>4</PROTECTIVE_EQUIPMENT_CODE><AREA_CODE>411303000</AREA_CODE><ORG_CODE>411303066</ORG_CODE><EXAM_CONCLUSION_LIST><EXAM_CONCLUSION><ITAM_CODE /><ITAM_NAME /><EXAM_CONCLUSION_CODE>05</EXAM_CONCLUSION_CODE><YSZYB_CODE /><ENTERPRISE_NAME>中石化华北石油工程有限公司河南钻井分公司</ENTERPRISE_NAME><ZYJJZ_NAME /> <QTJB_NAME>其他疾病或异常；</QTJB_NAME> <HARM_START_DATE /><HARM_AGE_YEAR /><HARM_AGE_MONTH /></EXAM_CONCLUSION></EXAM_CONCLUSION_LIST><EXAM_ITEM_RESULT_LIST><EXAM_ITEM_RESULT><EXAM_ITEM_PNAME>症状询问</EXAM_ITEM_PNAME><EXAM_ITEM_NAME>月经异常</EXAM_ITEM_NAME><EXAM_ITEM_CODE>1740000</EXAM_ITEM_CODE><EXAM_RESULT_TYPE>02</EXAM_RESULT_TYPE><EXAM_RESULT>阴性</EXAM_RESULT><DATA_VERSION /><EXAM_ITEM_UNIT_CODE /><REFERENCE_RANGE_MIN /><REFERENCE_RANGE_MAX /><ABNORMAL>0</ABNORMAL></EXAM_ITEM_RESULT></EXAM_ITEM_RESULT_LIST><WRITE_PERSON>郑萌</WRITE_PERSON><WRITE_PERSON_TELPHONE>13838735070</WRITE_PERSON_TELPHONE><WRITE_DATE>20250610</WRITE_DATE><REPORT_ORGAN_CREDIT_CODE>南阳南石医院</REPORT_ORGAN_CREDIT_CODE><REMARK /><EXAM_PHYSICIAN>李风波</EXAM_PHYSICIAN><EXAM_ORG_TYPE>202601041046</EXAM_ORG_TYPE><SIGN_ID>202506030000</SIGN_ID></HEALTH_EXAM_RECORD></HEALTH_EXAM_RECORD_LIST></EventBody></DataExchange>"""
    # result = call_exam_add(API_KEY, APP_SECRET, test_xml)
    # print(f"调用结果:", result)




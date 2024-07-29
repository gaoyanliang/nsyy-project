import json
from datetime import datetime
from xml.dom.minidom import parseString

import requests

from gylmodules import global_config
from gylmodules.medical_record_analysis.build_cda import admission_cda, discharge_cda, hours24_discharge_cda, \
    progress_note_cda, inpatient_homepage_cda
from gylmodules.medical_record_analysis.xml_const import const as xml_const


"""
调用第三方系统获取数据
"""


def call_third_systems_obtain_data(type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
            # 根据住院号/门诊号查询 病人id 主页id
            from tools import orcl_db_read
            data = orcl_db_read(param)

    return data


# 格式化 xml

def prettify_xml(xml_string):
    dom = parseString(xml_string)
    pretty_xml_as_string = dom.toprettyxml()

    # Remove extra blank lines
    lines = pretty_xml_as_string.split('\n')
    non_empty_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_empty_lines)


def query_pat_info_by_pat_no(data):
    # 如果有住院号, 根据住院号, 查询病人信息
    if 'pat_no' in data:
        pat_no = data.get('pat_no')
    elif '住院号' in data:
        pat_no = data.get('住院号')
    else:
        return data

    data['pat_no'] = pat_no
    param = {
        "type": "orcl_db_read",
        "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"SELECT * FROM 病人信息 WHERE 住院号 = '{pat_no}' order by 主页ID desc "
    }
    pat_info = call_third_systems_obtain_data('orcl_db_read', param)
    if pat_info and pat_info[0]:
        data['pat_addr'] = pat_info[0].get('家庭地址', '/')
        data['pat_id_card'] = str(pat_info[0].get('身份证号', '/'))
        data['pat_name'] = pat_info[0].get('姓名', '/')
        data['pat_sex'] = pat_info[0].get('性别', '/')
        data['pat_marriage'] = pat_info[0].get('婚姻状况', '/')
        data['pat_nation'] = pat_info[0].get('民族', '/')
        data['pat_age'] = str(pat_info[0].get('年龄', '/'))
        data['pat_occupation'] = pat_info[0].get('职业', '/')
        data['pat_sex'] = pat_info[0].get('性别', '/')
        data['pat_dept_no'] = str(pat_info[0].get('当前科室ID', '/'))
        data['pat_ward_no'] = str(pat_info[0].get('当前病区ID', '/'))
        if type(pat_info[0].get('入院时间')) == str:
            data['pat_time'] = pat_info[0].get('入院时间')
        else:
            data['pat_time'] = pat_info[0].get('入院时间').strftime('%Y-%m-%d %H:%M:%S')
    else:
        print("没有查询到病人信息")
        return
    return data


# 组装入院记录
def assembling_cda_record(data, type):

    data = query_pat_info_by_pat_no(data)
    if type == 1:
        data['file_title'] = '入院记录'
    elif type == 2:
        data['file_title'] = '出院记录'
    elif type == 3:
        data['file_title'] = '24小时入出院记录'
    elif type == 4:
        data['file_title'] = '首次病程记录'
    elif type == 5:
        data['file_title'] = '住院病案首页'

    data['file_no'] = 'nsyy001'
    data['hospital_no'] = '0000'
    data['hospital_name'] = '南阳南石医院'
    # xml 声明
    admission_record = xml_const.xml_statement
    # xml 开始
    admission_record = admission_record + xml_const.xml_start

    if type == 1:
        # 组装 header
        admission_record = admission_cda.assembling_header(admission_record, data)
        # xml body 开始
        admission_record = admission_record + xml_const.xml_body_start
        # 组装 body
        admission_record = admission_cda.assembling_body(admission_record, data)
    elif type == 2:
        admission_record = discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = discharge_cda.assembling_body(admission_record, data)
    elif type == 3:
        admission_record = hours24_discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = hours24_discharge_cda.assembling_body(admission_record, data)
    elif type == 4:
        admission_record = progress_note_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = progress_note_cda.assembling_body(admission_record, data)
    elif type == 5:
        admission_record = inpatient_homepage_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = inpatient_homepage_cda.assembling_body(admission_record, data)
    else:
        print("不支持 type", type)

    # xml body 结束
    admission_record = admission_record + xml_const.xml_body_end

    # xml 结束
    admission_record = admission_record + xml_const.xml_end

    # print(admission_record)

    # 格式化 xml
    pretty_xml = prettify_xml(admission_record)
    # print(pretty_xml)

    return pretty_xml


# ========================== 以下内容测试使用 ==========================

def load_sid():
    # JSON文件路径
    file_path = '../all_sid.json'
    # 打开文件并加载JSON数据
    with open(file_path, 'r') as file:
        data = json.load(file)
    # 打印加载的数据
    print(data)



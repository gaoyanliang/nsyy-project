import json
from datetime import datetime
from xml.dom.minidom import parseString

import requests

from gylmodules import global_config
from gylmodules.medical_record_analysis.build_cda import admission_cda, discharge_cda, hours24_discharge_cda, \
    progress_note_cda, inpatient_homepage_cda, daily_medical_record_cda, inspection_record_cda, \
    difficult_cases_record_cda, handover_record_cda, transfer_record_cda, stage_summary_cda, rescue_record_cda, \
    consultation_record_cda, preoperative_summary_cda
from gylmodules.medical_record_analysis.xml_const import const as xml_const


"""
调用第三方系统获取数据
"""


def call_third_systems_obtain_data(type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.3.12:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
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
        data['file_title'] = '住院病案首页'
    elif type == 5:
        data['file_title'] = '首次病程记录'
    elif type == 6:
        data['file_title'] = '日常病程记录'
    elif type == 7:
        data['file_title'] = '上级医师查房记录'
    elif type == 8:
        data['file_title'] = '疑难病例讨论记录'
    elif type == 9:
        data['file_title'] = '交接班记录'
    elif type == 10:
        data['file_title'] = '转科记录'
    elif type == 11:
        data['file_title'] = '阶段小结'
    elif type == 12:
        data['file_title'] = '抢救记录'
    elif type == 13:
        data['file_title'] = '会诊记录'
    elif type == 14:
        data['file_title'] = '术前小结'
    elif type == 15:
        data['file_title'] = '术前讨论'
    elif type == 16:
        data['file_title'] = '术后首次病程记录'
    elif type == 17:
        data['file_title'] = '死亡记录'
    elif type == 18:
        data['file_title'] = '死亡病例讨论记录'

    data['hospital_no'] = '0000'
    data['hospital_name'] = '南阳南石医院'
    # xml 声明
    admission_record = xml_const.xml_statement
    # xml 开始
    admission_record = admission_record + xml_const.xml_start

    if type == 1:
        # 入院记录
        # 组装 header
        admission_record = admission_cda.assembling_header(admission_record, data)
        # xml body 开始
        admission_record = admission_record + xml_const.xml_body_start
        # 组装 body
        admission_record = admission_cda.assembling_body(admission_record, data)
    elif type == 2:
        # 出院记录
        admission_record = discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = discharge_cda.assembling_body(admission_record, data)
    elif type == 3:
        # 24小时入出院记录
        admission_record = hours24_discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = hours24_discharge_cda.assembling_body(admission_record, data)
    elif type == 4:
        # 住院病案首页
        admission_record = inpatient_homepage_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = inpatient_homepage_cda.assembling_body(admission_record, data)
    elif type == 5:
        # 首次病程记录
        admission_record = progress_note_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = progress_note_cda.assembling_body(admission_record, data)
    elif type == 6:
        # 日常病程记录
        admission_record = daily_medical_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = daily_medical_record_cda.assembling_body(admission_record, data)
    elif type == 7:
        # 上级医师查房记录
        admission_record = inspection_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = inspection_record_cda.assembling_body(admission_record, data)
    elif type == 8:
        # 疑难病例讨论记录
        admission_record = difficult_cases_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = difficult_cases_record_cda.assembling_body(admission_record, data)
    elif type == 9:
        # 交接班记录
        admission_record = handover_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = handover_record_cda.assembling_body(admission_record, data)
    elif type == 10:
        # 转科记录
        admission_record = transfer_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = transfer_record_cda.assembling_body(admission_record, data)
    elif type == 11:
        # 阶段小结
        admission_record = stage_summary_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = stage_summary_cda.assembling_body(admission_record, data)
    elif type == 12:
        # 抢救记录
        admission_record = rescue_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = rescue_record_cda.assembling_body(admission_record, data)
    elif type == 13:
        # 会诊记录
        admission_record = consultation_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = consultation_record_cda.assembling_body(admission_record, data)
    elif type == 14:
        # 会诊记录
        admission_record = preoperative_summary_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = preoperative_summary_cda.assembling_body(admission_record, data)
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


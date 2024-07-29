import xml.etree.ElementTree as ET
import json
import os

from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_hpi, clean_dict
from gylmodules.medical_record_analysis.build_cda.build_cda import assembling_cda_record

"""
====================================================================================================
============================================ 出院记录解析 ============================================
====================================================================================================
"""


def parse_patient_document_by_str(xml_str):
    root = ET.fromstring(xml_str)
    patient_info = {}

    document = root.find('subdocuments').find('header').find('document')
    if document is not None:
        for element in document.iter('element'):
            key = element.get('title').replace(' ', '') if element.get('title') is not None else ''
            value = element.text
            if key is not None and value is not None:
                if element.get('sid') is not None and element.get('sid') == '6A67D9D88F06411096CFD9690C452186':
                    patient_info['pat_no'] = value
                elif element.get('sid') is not None and element.get('sid') == 'CEB7B32AE5C745BA8A800A93E9BBE5A5':
                    patient_info['pat_bed'] = value
                else:
                    patient_info[key] = value


    document = root.find('./document')
    for element in document.iter('element'):
        key = element.get('title').replace(' ', '') if element.get('title') is not None else ''
        value = element.get('value') if element.get('value') else element.text
        if key is not None and value is not None:
            patient_info[key] = value

    # 性别特殊处理
    if not patient_info.get('pat_sex'):
        patient_info['pat_sex'] = document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']").get('title') if document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']") is not None else ''

    for section in document.iter('section'):
        parse_hpi(section, patient_info,  patient_info['姓名'] + '出院记录')

    return patient_info


def parse_patient_document(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    patient_info = {}

    document = root.find('subdocuments').find('header').find('document')
    if document is not None:
        for element in document.iter('element'):
            key = element.get('title').replace(' ', '') if element.get('title') is not None else ''
            value = element.text
            if key is not None and value is not None:
                if element.get('sid') is not None and element.get('sid') == '6A67D9D88F06411096CFD9690C452186':
                    patient_info['pat_no'] = value
                elif element.get('sid') is not None and element.get('sid') == 'CEB7B32AE5C745BA8A800A93E9BBE5A5':
                    patient_info['pat_bed'] = value
                else:
                    patient_info[key] = value


    document = root.find('./document')
    for element in document.iter('element'):
        key = element.get('title').replace(' ', '') if element.get('title') is not None else ''
        value = element.get('value') if element.get('value') else element.text
        if key is not None and value is not None:
            patient_info[key] = value

    # 性别特殊处理
    if not patient_info.get('pat_sex'):
        patient_info['pat_sex'] = document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']").get('title') if document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']") is not None else ''

    for section in document.iter('section'):
        parse_hpi(section, patient_info, xml_file)

    return patient_info


def parse_discharge_record(data):
    patient_info = parse_patient_document_by_str(data)
    # 将 Python 对象转换为格式化的 JSON 字符串
    # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    # print(formatted_json)
    patient_info = clean_dict(patient_info)
    cda_data = assembling_cda_record(patient_info, 2)
    return cda_data


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 遍历所有目录中xml 文件完成解析，并生成入院记录 cda 文档
    # index = 0
    # directory = '/Users/gaoyanliang/nsyy/病历解析/24小时内入出院记录/bingli/'
    # # directory = '/Users/gaoyanliang/nsyy/病历解析/出院记录/bingli/'
    # for root, dirs, files in os.walk(directory):
    #     for file in files:
    #         if file.endswith(".xml"):
    #             patient_info = parse_patient_document(os.path.join(root, file))
    #             patient_info = clean_dict(patient_info)
    #             index = index + 1
    #
    #             # 将 Python 对象转换为格式化的 JSON 字符串
    #             # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    #             # print(formatted_json)
    #             try:
    #                 assembling_cda_record(patient_info, 3)
    #                 # assembling_cda_record(patient_info, 2)
    #             except Exception as e:
    #                 print('===> 解析异常', file)
    # print(index)

    patient_info = parse_patient_document('/Users/gaoyanliang/nsyy/病历解析/24小时内入出院记录/bingli/24小时内入出院记录_2024-03-04_12-40-00.xml')
    patient_info = clean_dict(patient_info)
    # patient_info = parse_patient_document('/Users/gaoyanliang/nsyy/病历解析/出院记录/bingli/出院记录_2024-03-03_00-08-15.xml')
    formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    print(formatted_json)

    print('------------------------------')
    assembling_cda_record(patient_info, 3)
    # assembling_cda_record(patient_info, 2)











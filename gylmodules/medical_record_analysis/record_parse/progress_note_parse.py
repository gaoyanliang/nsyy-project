import xml.etree.ElementTree as ET
import json
import os

from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_hpi, clean_dict
from gylmodules.medical_record_analysis.build_cda.cda_xml_data_build import assembling_cda_record

"""
====================================================================================================
============================================ 病程记录解析 ============================================
====================================================================================================
"""

subdoc_name_dict = {
    '6584489821AF412B965461E5A1832793': '首次病程记录',
    '960FFBFF811949E9BB42E41C781F37E1': '上级医师查房记录',
    'EC86BA05EFFE43B3BCB93417CCDBF504': '日常病程记录',
    '103ED3475F5443FEAA1D77EA842D6C9A': '出院当日病程记录',
    '870E9708C9C8421FBA23C093F397068D': '危急值报告处理记录',
    '0182956BBCDE4D1FB8BAE50B2CD38588': '术前小结',
    '0EFE9798AA6E416CBD70291FB88829B4': '术后首次病程记录',
    '4B86BE6477AC414CBB8ED525E2D6A847': '术后上级查房记录',
    'FDBE6AE727B747568CC87E94604CBE45': '转出记录',
    'BAFB050135AA4C119B0E24446EB3C723': '转入记录',
    '7F5F990B46CF4F07B0419E297604D02F': '有创操作记录',
    'D7CF4ED4C58645D3AD874949C3119D6C': '输血记录',
    '38C4730AD1EF42BAAA953AF74A1BBEDA': '中医科首次病程记录',
    '9370D17BBD43440AAD7F43278DEBEC6C': '会诊记录',
    '0FBB8AC2C758451CB9350BBBA010F147': '阶段小结',
    '0CF4B6CB786D44D88DBF9ED3BD3234D3': '抢救记录',
    '943B7ECD19694804A8128B1F6DF67071': '新生儿首次病程记录',
    '42E65F045E4E4D37A79A957877443CAD': '交班记录'
}


def parse_patient_document(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    patient_info = {}

    # 解析 header
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

    # 性别特殊处理
    if not patient_info.get('pat_sex'):
        patient_info['pat_sex'] = document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']").get('title') if document.find(".//element[@sid='B8DEF0D495FA45BFBCDC7CD2045EDBCD']") is not None else ''

    patient_info['sub_doc'] = []
    for subdoc in root.find('document').iter('subdoc'):
        new_dict = {}
        parse_hpi(subdoc, new_dict, xml_file)
        for section in subdoc.iter('section'):
            parse_hpi(section, new_dict, xml_file)
        new_dict['title'] = subdoc.get('title')
        new_dict['antetypeid'] = subdoc.get('antetypeid')
        patient_info['sub_doc'].append(new_dict)

    return patient_info


# 查看有哪些 subdoc
subdoc_info = dict()
def parse_test(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    document = root.find('./document')
    for element in document.iter('subdoc'):
        key = element.get('title').replace(' ', '') if element.get('title') is not None else ''
        antetypeid = element.get('antetypeid')
        if key:
            subdoc_info[antetypeid] = key


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 遍历所有目录中xml 文件完成解析，并生成入院记录 cda 文档
    # index = 0
    # directory = '/Users/gaoyanliang/nsyy/病历解析/病程记录/bingli/'
    # for root, dirs, files in os.walk(directory):
    #     for file in files:
    #         if file.endswith(".xml"):
    #             # parse_test(os.path.join(root, file))
    #             index = index + 1
    #             patient_info = parse_patient_document(os.path.join(root, file))
    #             patient_info = clean_dict(patient_info)
    #
    #             # 将 Python 对象转换为格式化的 JSON 字符串
    #             # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    #             # print(formatted_json)
    #             # try:
    #             #     assembling_cda_record(patient_info, 3)
    #             #     # assembling_cda_record(patient_info, 2)
    #             # except Exception as e:
    #             #     print('===> 解析异常', file)
    # print(index)
    # # print(subdoc_info)

    patient_info = parse_patient_document('/Users/gaoyanliang/nsyy/病历解析/病程记录/bingli/病程记录_2024-03-03_00-07-58.xml')
    patient_info = clean_dict(patient_info)
    formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    print(formatted_json)

    # print('------------------------------')
    # assembling_cda_record(patient_info, 3)











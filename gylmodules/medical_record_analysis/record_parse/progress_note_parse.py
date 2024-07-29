import xml.etree.ElementTree as ET
import json
import os

from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_hpi, clean_dict
from gylmodules.medical_record_analysis.build_cda.build_cda import assembling_cda_record

"""
====================================================================================================
============================================ 病程记录解析 ============================================
====================================================================================================
"""


def parse_patient_document_by_str(xml_str):
    root = ET.fromstring(xml_str)
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
        parse_hpi(subdoc, new_dict, patient_info['姓名'] + '病程记录')
        for section in subdoc.iter('section'):
            parse_hpi(section, new_dict, patient_info['姓名'] + '病程记录')
        new_dict['title'] = subdoc.get('title')
        new_dict['antetypeid'] = subdoc.get('antetypeid')
        patient_info['sub_doc'].append(new_dict)

    return patient_info


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


def parse_progress_note_record(data):
    patient_info = parse_patient_document_by_str(data)
    patient_info = clean_dict(patient_info)

    is_find = False
    subd = patient_info.get('sub_doc')
    for doc in subd:
        if doc.get('antetypeid') == '6584489821AF412B965461E5A1832793':
            patient_info.update(doc)
            is_find = True
            break

    if not is_find:
        raise Exception('当前病历未找到首次病程记录')

    # 将 Python 对象转换为格式化的 JSON 字符串
    # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    # print(formatted_json)
    cda_data = assembling_cda_record(patient_info, 4)
    return cda_data



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
    #             subd = patient_info.get('sub_doc')
    #             for doc in subd:
    #                 if doc.get('antetypeid') == '6584489821AF412B965461E5A1832793':
    #                     patient_info.update(doc)
    #                     break
    #
    #             # 将 Python 对象转换为格式化的 JSON 字符串
    #             # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    #             # print(formatted_json)
    #             try:
    #                 assembling_cda_record(patient_info, 4)
    #             except Exception as e:
    #                 print('===> 解析异常', file)
    # print(index)
    # print(subdoc_info)

    patient_info = parse_patient_document('/Users/gaoyanliang/nsyy/病历解析/病程记录/bingli/病程记录_2024-03-05_00-39-07.xml')
    patient_info = clean_dict(patient_info)

    is_find = False
    subd = patient_info.get('sub_doc')
    for doc in subd:
        if doc.get('antetypeid') == '6584489821AF412B965461E5A1832793':
            patient_info.update(doc)
            is_find = True
            break

    if not is_find:
        raise Exception('当前病历未找到首次病程记录')

    formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    print(formatted_json)

    print('------------------------------')
    assembling_cda_record(patient_info, 4)











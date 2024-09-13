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


# 从病程记录中解析危急值记录
def parse_cv_by_str(xml_str):
    # tree = ET.parse(xml_str)
    # root = tree.getroot()
    try:
        root = ET.fromstring(xml_str)
        cv_info = {}
        for subdoc in root.find('document').iter('subdoc'):
            title = subdoc.get('title') if subdoc.get('title') is not None else ''
            antetypeid = subdoc.get('antetypeid') if subdoc.get('antetypeid') is not None else ''
            if title.__contains__('危急值报告处理记录') or antetypeid == '870E9708C9C8421FBA23C093F397068D':
                element = subdoc.find(".//element[@sid='CE6A04DE74264F938FC1A903103BFC5E']")
                record_time = ''
                if element is not None:
                    record_time = element.get('value')
                cv_record = ''
                for utext in subdoc.iter('utext'):
                    if utext.text is not None and not utext.text.__contains__('家属签字确认'):
                        cv_record = cv_record + utext.text.strip() if utext.text else ''
                if record_time:
                    cv_info[record_time] = cv_record
        return cv_info
    except Exception as e:
        return {}


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


def parse_progress_note_record(file, data, test: bool = False):
    if test:
        patient_info = data
    else:
        patient_info = parse_patient_document_by_str(data.get('CONTENT'))
        patient_info = clean_dict(patient_info)

        patient_info['文档作者'] = data.get('文档作者')
        patient_info['文档ID'] = data.get('文档ID')
        patient_info['文档创建时间'] = data.get('记录时间')

    # 将 Python 对象转换为格式化的 JSON 字符串
    # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    # print(formatted_json)

    cda_list = []
    # 转科目的
    purpose_of_transfer = '/'
    # 转出签字
    sign_of_transfer = {}
    subd = patient_info.get('sub_doc')
    for sub in subd:
        cda_data = ''
        shallow_copy = patient_info.copy()
        try:
            if sub.get('antetypeid') in ('6584489821AF412B965461E5A1832793',
                                         '0EFE9798AA6E416CBD70291FB88829B4',
                                         '38C4730AD1EF42BAAA953AF74A1BBEDA',
                                         '943B7ECD19694804A8128B1F6DF67071'):
                # 首次病程记录, 术后首次病程记录
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 5)
            elif sub.get('antetypeid') in ('EC86BA05EFFE43B3BCB93417CCDBF504',
                                           '103ED3475F5443FEAA1D77EA842D6C9A'):
                # 日常病程记录, 签名和日常病程记录内容
                shallow_copy['日常病程记录'] = sub.get('日常病程记录') if sub.get('日常病程记录') else sub.get('日常病程记录.')
                sign = [v for k, v in sub.items() if '签名' in k]
                if sign:
                    shallow_copy['医师签名'] = sign[0]
                cda_data = assembling_cda_record(shallow_copy, 6)
            elif sub.get('antetypeid') in ('960FFBFF811949E9BB42E41C781F37E1',
                                           '4B86BE6477AC414CBB8ED525E2D6A847'):
                # 上级医师查房记录
                shallow_copy['查房记录'] = sub.get('上级医师查房记录', '/')
                shallow_copy['主任医师'] = sub.get('主任医师', {})
                shallow_copy['经治医师'] = sub.get('经治医师', {})
                cda_data = assembling_cda_record(shallow_copy, 7)
            elif sub.get('antetypeid') == '42E65F045E4E4D37A79A957877443CAD':
                # 交班记录
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 9)
            elif sub.get('antetypeid') == 'FDBE6AE727B747568CC87E94604CBE45':
                # 转出科室-转入科室，一般是一一对应的，但是有些文件中 仅有转入记录，没有转出记录
                # 从转出记录中获取 转科目的
                purpose_of_transfer = sub.get('转科目的', '/')
                if '住院医师' in sub:
                    sign_of_transfer = sub.get('住院医师')
                elif '主治医师' in sub:
                    sign_of_transfer = sub.get('主治医师')
                elif '经治医师' in sub:
                    sign_of_transfer = sub.get('经治医师')
                else:
                    sign_of_transfer = {}
            elif sub.get('antetypeid') == 'BAFB050135AA4C119B0E24446EB3C723':
                # 遇到转入记录，构造转科记录
                shallow_copy.update(sub)
                shallow_copy['转科目的'] = purpose_of_transfer
                shallow_copy['转出医师签名'] = sign_of_transfer
                cda_data = assembling_cda_record(shallow_copy, 10)
            elif sub.get('antetypeid') == '0FBB8AC2C758451CB9350BBBA010F147':
                # 阶段小结
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 11)
            elif sub.get('antetypeid') == '0CF4B6CB786D44D88DBF9ED3BD3234D3':
                # 抢救记录
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 12)
            elif sub.get('antetypeid') == '9370D17BBD43440AAD7F43278DEBEC6C':
                # 会诊记录
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 13)
            elif sub.get('antetypeid') == '0182956BBCDE4D1FB8BAE50B2CD38588':
                # 术前小结
                shallow_copy.update(sub)
                cda_data = assembling_cda_record(shallow_copy, 14)
        except Exception as e:
            print(file, sub.get('antetypeid'), sub.get('title'), '解析异常', e)

        if cda_data:
            cda_list.append(cda_data)

    return cda_list


#  todo cda 有疑难病例讨论记录， 病程记录 xml 没有
#  todo cda 有术前讨论， 病程记录 xml 没有

subdoc_name_dict = {
    '6584489821AF412B965461E5A1832793': '首次病程记录',
    'EC86BA05EFFE43B3BCB93417CCDBF504': '日常病程记录',
    '960FFBFF811949E9BB42E41C781F37E1': '上级医师查房记录',
    '42E65F045E4E4D37A79A957877443CAD': '交班记录',
    '0FBB8AC2C758451CB9350BBBA010F147': '阶段小结',
    '0CF4B6CB786D44D88DBF9ED3BD3234D3': '抢救记录',
    '9370D17BBD43440AAD7F43278DEBEC6C': '会诊记录',
    'FDBE6AE727B747568CC87E94604CBE45': '转出记录',
    'BAFB050135AA4C119B0E24446EB3C723': '转入记录',
    '0182956BBCDE4D1FB8BAE50B2CD38588': '术前小结',
    '0EFE9798AA6E416CBD70291FB88829B4': '术后首次病程记录',
    '4B86BE6477AC414CBB8ED525E2D6A847': '术后上级查房记录',
    '103ED3475F5443FEAA1D77EA842D6C9A': '出院当日病程记录',
    '38C4730AD1EF42BAAA953AF74A1BBEDA': '中医科首次病程记录',
    '943B7ECD19694804A8128B1F6DF67071': '新生儿首次病程记录',
    
    '870E9708C9C8421FBA23C093F397068D': '危急值报告处理记录',
    '7F5F990B46CF4F07B0419E297604D02F': '有创操作记录',
    'D7CF4ED4C58645D3AD874949C3119D6C': '输血记录'

}





# =========================================== 以下代码为测试使用 ===========================================

# 查看有哪些 subdoc
subdoc_info = dict()
def parse_test(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    document = root.find('./document')
    for element in document.iter('subdoc'):
        key = element.get('title') if element.get('title') is not None else ''
        antetypeid = element.get('antetypeid')
        if key:
            subdoc_info[antetypeid] = key
            if antetypeid == '870E9708C9C8421FBA23C093F397068D':
                print(key, antetypeid, xml_file)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # 遍历所有目录中xml 文件完成解析，并生成入院记录 cda 文档
    index = 0
    directory = '/Users/gaoyanliang/nsyy/病历解析/病程记录/bingli/'
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".xml"):
                # index = index + 1
                # patient_info = parse_patient_document(os.path.join(root, file))
                # patient_info = clean_dict(patient_info)

                # parse_test(os.path.join(root, file))

                cv_info = parse_cv_by_str(os.path.join(root, file))
                if cv_info:
                    print(cv_info)
                    print('----------', file)
                # 将 Python 对象转换为格式化的 JSON 字符串
                # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
                # print(formatted_json)
                # try:
                #     parse_progress_note_record(file, patient_info, True)
                # except Exception as e:
                #     print('=========> 解析异常', file)
    # print(index)
    # print(subdoc_info)

    # patient_info = parse_patient_document('/Users/gaoyanliang/nsyy/病历解析/病程记录/0304/病程记录_2024-03-04_11-13-47.xml')
    # patient_info = clean_dict(patient_info)
    # formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
    # print(formatted_json)
    #
    # try:
    #     cda_list = parse_progress_note_record('file', patient_info, True)
    #     print('------------------------------')
    #     # for cda in cda_list:
    #     #     print(cda)
    # except Exception as e:
    #     print('===> 解析异常', e)

    # patient_info = parse_cv_by_str('/Users/gaoyanliang/nsyy/病历解析/病程记录/bingli/病程记录_2024-03-05_21-24-43.xml')
    # print(patient_info)












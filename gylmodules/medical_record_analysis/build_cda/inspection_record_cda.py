from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
======================================= 上级医师查房记录CDA 文档构建 ==================================
====================================================================================================
"""


def get_birthday_from_id(id_number):
    if len(id_number) == 18:
        birthday = id_number[6:14]  # 截取第7位到第14位
        return birthday[:4] + birthday[4:6] + birthday[6:]
    else:
        print("身份证号码格式不正确")
        return '/'


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    re = data.get('查房记录')
    if re and type(re) == dict:
        ct = re.get('日期时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.59") \
        .replace('{文档类型}', "C0039") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', str(ct))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target3 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', '1') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
        .replace('{pat_birth_time}', get_birthday_from_id(data.get('pat_id_card', '/'))) \
        .replace('{pat_age}', data.get('pat_age', '/'))

    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author \
        .replace('{文档创作时间}', data.get('文档创建时间', '/')) \
        .replace('{文档创作者id}', '/') \
        .replace('{文档创作者}', data.get('文档作者', '/'))

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name'))

    # 最终审核者签名
    legal_doc = data.get('主任医师')
    if not legal_doc:
        legal_doc = {}
    admission_record = admission_record + xml_header.xml_header_legal_authenticator \
        .replace('{医师id}', '/') \
        .replace('{展示医师}', '上级医师') \
        .replace('{医师}', legal_doc.get('displayinfo', '/'))

    if '住院医师' in data:
        sign_doc = data.get('住院医师')
    elif '主治医师' in data:
        sign_doc = data.get('主治医师')
    elif '经治医师' in data:
        sign_doc = data.get('经治医师')
    else:
        sign_doc = {}
    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', sign_doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', sign_doc.get('displayinfo', '/')) \
        .replace('{显示医师名字}', '记录人签名')

    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', sign_doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', sign_doc.get('displayinfo', '/')) \
        .replace('{显示医师名字}', '主治医师签名')

    # 关联文档
    admission_record = admission_record + xml_header.xml_header_related_document

    # 病床号、病房、病区、科室和医院的关联
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter \
        .replace('{入院时间}', data.get('pat_time', '/')) \
        .replace('{pat_bed_no}', data.get('pat_bed', '/') if data.get('pat_bed') else '/') \
        .replace('{pat_bed}', data.get('pat_bed', '/') if data.get('pat_bed') else '/') \
        .replace('{pat_room_no}', '/') \
        .replace('{pat_room}', '/') \
        .replace('{pat_dept_no}', data.get('pat_dept_no', '/')) \
        .replace('{pat_dept}', data.get('pat_dept', '/')) \
        .replace('{pat_ward_no}', '/') \
        .replace('{pat_ward}', '/') \
        .replace('{医院编码}', data.get('hospital_no')) \
        .replace('{医院}', data.get('hospital_name'))

    return admission_record


# 组装 body 信息
def assembling_body(admission_record: str, data: dict):
    re = data.get('查房记录')
    if re and type(re) == dict:
        re = re.get('value', '/')
    if not re:
        re = '/'
    # 查房记录
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '51848-0')
                 .replace('{section_name}', 'Assessment note')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '查房记录') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.181.00')
                 .replace('{entry_name}', '查房记录')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', re)))

    # 诊断章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29548-5')
                 .replace('{section_name}', 'Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '诊断章节') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医“四诊”观察结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中医四诊', '/'))))

    # 用药章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10160-0')
                 .replace('{section_name}', 'HISTORY OF MEDICATION USE')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '中药煎煮法') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE08.50.047.00')
                 .replace('{entry_name}', '中药饮片煎煮法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中药饮片煎煮法', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.136.00')
                 .replace('{entry_name}', '中药用药方法的描述')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('中药用药方法', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 治疗计划章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '辩证论治') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.025.00')
                 .replace('{entry_name}', '诊疗计划')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('诊疗计划', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.131.00')
                 .replace('{entry_name}', '辩证论治')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('辩证论治', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 住院医嘱章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '46209-3')
                 .replace('{section_name}', 'Provider Orders')) \
        .replace('{text}', '<title>住院医嘱</title>') \
        .replace('{entry_observation_name}', '住院医嘱') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.287.00')
                 .replace('{entry_name}', '医嘱内容')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('住院医嘱', '/'))))



    return admission_record

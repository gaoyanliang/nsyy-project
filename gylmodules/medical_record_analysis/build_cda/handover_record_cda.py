from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 交班记录CDA 文档构建 ======================================
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
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.61") \
        .replace('{文档类型}', "C0041") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', data.get('文档创建时间', '/'))

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

    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', data.get('签名时间', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', data.get('交班者', '/')) \
        .replace('{显示医师名字}', '交班者')

    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', data.get('签名时间', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', data.get('接班者', '/')) \
        .replace('{显示医师名字}', '接班者')

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
    # 主诉
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10154-3')
                 .replace('{section_name}', 'CHIEF COMPLAINT')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '主诉') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.01.119.00')
                 .replace('{entry_name}', '主诉')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('主诉', '/'))))

    # 入院诊断
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '46241-6')
                 .replace('{section_name}', 'HOSPITAL ADMISSION DX')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '入院诊断') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.148.00')
                 .replace('{entry_name}', '入院情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('入院情况', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '入院诊断-西医诊断名称')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('入院西医诊断', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.130.00')
                 .replace('{entry_name}', '初步诊断-中医病名代码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医病名代码', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.130.00')
                 .replace('{entry_name}', '入院诊断-中医证候代码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医证候代码', '/')))) \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 诊断章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29548-5')
                 .replace('{section_name}', 'Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '目前情况') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.184.00')
                 .replace('{entry_name}', '目前情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('目前情况', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '目前诊断-西医诊断名')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('西医诊断名', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.130.00')
                 .replace('{entry_name}', '目前诊断-中医病名代码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('目前诊断中医病名代码', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.130.00')
                 .replace('{entry_name}', '目前诊断-中医证候代码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('目前诊断中医证候代码', '/')))) \
        .replace('{entry5}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医“四诊”观察结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中医四诊', '/')))) \
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
        .replace('{entry_observation_name}', '治疗计划') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.298.00')
                 .replace('{entry_name}', '接班诊疗计划')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('接班诊疗计划', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.300.00')
                 .replace('{entry_name}', '治则治法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('治则治法', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE09.00.119.00')
                 .replace('{entry_name}', '注意事项')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('注意事项', '/')))) \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 住院过程章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8648-8')
                 .replace('{section_name}', 'Hospital Course')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '诊疗过程') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.296.00')
                 .replace('{entry_name}', '诊疗过程')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗过程', '/'))))


    return admission_record

from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
======================================= 首次病程记录CDA 文档构建 ======================================
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
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.57") \
        .replace('{文档类型}', "C0037") \
        .replace('{文档标识编码}', data.get('file_no')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', datetime.now().strftime('%Y%m%d%H%M%S'))

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
        .replace('{文档创作时间}', datetime.now().strftime('%Y%m%d%H%M%S')) \
        .replace('{文档创作者id}', data.get('hospital_no')) \
        .replace('{文档创作者}', data.get('hospital_name'))

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name'))

    # 最终审核者签名
    admission_record = admission_record + xml_header.xml_header_legal_authenticator \
        .replace('{医师id}', '/') \
        .replace('{展示医师}', '上级医师') \
        .replace('{医师}', data.get('主任医师', '/'))

    if '住院医师' in data:
        doc_name = data.get('住院医师')
    elif '主治医师' in data:
        doc_name = data.get('主治医师')
    elif '经治医师' in data:
        doc_name = data.get('经治医师')
    else:
        doc_name = '/'
    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator1 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '住院医师') \
        .replace('{医师名字}', doc_name)

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

    tedian = data.get('病例特点', '/')
    if tedian and type(tedian) == dict:
        tedian = tedian.get('value')
    yiju = data.get('诊断依据', '/')
    if yiju and type(yiju) == dict:
        yiju = yiju.get('value')
    chu = data.get('初步诊断', '/')
    if chu and type(chu) == dict:
        chu = chu.get('value')
    jian = data.get('鉴别诊断', '/')
    if jian and type(jian) == dict:
        jian = jian.get('value')
    # 诊断章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29548-5')
                 .replace('{section_name}', 'Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '诊断章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.133.00')
                 .replace('{entry_name}', '病例特点')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', tedian))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医“四诊”观察结果')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('中医四诊', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.070.00')
                 .replace('{entry_name}', '诊断依据')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', yiju))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '初步诊断-西医诊断编码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', chu))) \
        .replace('{entry5}', xml_body.body_section_entry3
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '初步诊断-中医病名代码')
                          .replace('{obs_name}', "中医病名代码"))
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', chu))) \
        .replace('{entry6}', xml_body.body_section_entry3
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '初步诊断-中医证候代码')
                          .replace('{obs_name}', "中医证候代码"))
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医证候', '/')))) \
        .replace('{entry7}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.025.00')
                 .replace('{entry_name}', '鉴别诊断-西医诊断名称')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', jian))) \
        .replace('{entry8}', xml_body.body_section_entry3
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '鉴别诊断-中医病名名称')
                          .replace('{obs_name}', "中医病名名称"))
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', jian))) \
        .replace('{entry9}', xml_body.body_section_entry3
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '鉴别诊断-中医证候名称')
                          .replace('{obs_name}', "中医证候名称"))
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('中医证候', '/'))))

    plan = data.get('诊疗计划', '/')
    if plan and type(plan) == dict:
        plan = plan.get('value')
    # 治疗计划章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '治疗计划章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.025.00')
                 .replace('{entry_name}', '诊疗计划')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', plan))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.300.00')
                 .replace('{entry_name}', '治则治法')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('治则治法', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    return admission_record

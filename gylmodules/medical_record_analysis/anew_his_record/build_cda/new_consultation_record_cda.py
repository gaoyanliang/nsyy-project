from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 会诊记录CDA 文档构建 ======================================
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
    re = data.get('会诊记录')
    if re and type(re) == dict:
        ct = re.get('日期时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.65") \
        .replace('{文档类型}', "C0045") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', ct)

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target6 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{电子申请单编号}', data.get('电子申请单编号', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', data.get("性别代码", '/') if data.get("性别代码") else '/') \
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

    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '会诊申请医师') \
        .replace('{医师名字}', '/')

    admission_record = admission_record + xml_header.xml_header_authenticator5 \
        .replace('{签名时间}', '/') \
        .replace('{医师id}', '/') \
        .replace('{会诊医师所在医疗机构名称}', data.get('会诊医师所在医疗机构名称', '/')) \
        .replace('{医师名字}', data.get('会诊医师', '/'))

    admission_record = admission_record + xml_header.xml_header_authenticator6 \
        .replace('{display_name}', '会诊申请医疗机构') \
        .replace('{申请会诊科室}', data.get('申请会诊科室', '/')) \
        .replace('{会诊申请医疗机构名称}', data.get('会诊申请医疗机构名称', '/'))

    admission_record = admission_record + xml_header.xml_header_authenticator6 \
        .replace('{display_name}', '会诊所在机构') \
        .replace('{申请会诊科室}', data.get('会诊科室名称', '/')) \
        .replace('{会诊申请医疗机构名称}', data.get('会诊所在医疗机构名称', '/'))

    # 关联文档
    admission_record = admission_record + xml_header.xml_header_related_document

    # 病床号、病房、病区、科室和医院的关联
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter \
        .replace('{入院时间}', data.get('pat_time', '/')) \
        .replace('{pat_bed_no}', data.get('当前床位id', '/') if data.get('当前床位id') else '/') \
        .replace('{pat_bed}', data.get('当前床位编码', '/') if data.get('当前床位编码') else '/') \
        .replace('{pat_room_no}', data.get('当前房间id', '/') if data.get('当前房间id') else '/') \
        .replace('{pat_room}', data.get('当前房间号', '/') if data.get('当前房间号') else '/') \
        .replace('{pat_dept_no}', data.get('pat_dept_no', '/')) \
        .replace('{pat_dept}', data.get('pat_dept', '/')) \
        .replace('{pat_ward_no}', data.get('当前病区id', '/') if data.get('当前病区id') else '/') \
        .replace('{pat_ward}', data.get('当前病区名称', '/') if data.get('当前病区名称') else '/') \
        .replace('{医院编码}', data.get('hospital_no', '/')) \
        .replace('{医院}', data.get('hospital_name', '/'))

    return admission_record


# 组装 body 信息
def assembling_body(admission_record: str, data: dict):
    re = data.get('会诊记录')
    if not re:
        re = '/'
    elif type(re) == dict:
        re = re.get('value', '/')
    # 健康评估章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '51848-0')
                 .replace('{section_name}', 'Assessment note')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '病历摘要') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.182.00')
                 .replace('{entry_name}', '病历摘要')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', re)))

    # 诊断章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29548-5')
                 .replace('{section_name}', 'Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '诊断章节') \
        .replace('{entry1}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_observation_code1
                          .replace('{obs_code}', 'DE05.01.025.00')
                          .replace('{obs_display_name}', '西医诊断名称'))
                 .replace('{entry_ship_name}', '西医诊断')
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('西医诊断', '/')))
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE05.01.024.00')
                          .replace('{obs_display_name}', '西医诊断编码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('西医诊断编码', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_observation_code2
                          .replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '中医诊断名称')
                          .replace('{obs_name}', '中医诊断名称'))
                 .replace('{entry_ship_name}', '中医病名')
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('中医病名', '/')))
                 .replace('{obs_code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '中医病名代码').replace('{obs_name}', '中医病名代码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医病名代码', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_observation_code2
                          .replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '中医诊断证候名称')
                          .replace('{obs_name}', '中医证候名称'))
                 .replace('{entry_ship_name}', '中医证候')
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('中医证候', '/')))
                 .replace('{obs_code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '中医证候代码').replace('{obs_name}', '中医证候代码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医证候代码', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医“四诊”观察结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中医四诊', '/')))) \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 辅助检查章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '辅助检查章节')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '辅助检查结果') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.30.009.00')
                 .replace('{entry_name}', '辅助检查结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('辅助检查结果', '/'))))

    # 治疗计划章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '治疗计划') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.297.00')
                 .replace('{entry_name}', '诊疗过程名称')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗过程名称', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO6.00.300.00')
                 .replace('{entry_name}', '治则治法')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('治则治法', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.214.00')
                 .replace('{entry_name}', '会诊目的')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('会诊目的', '/')))) \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 会诊原因章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '会诊原因')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '会诊原因') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.319.00')
                 .replace('{entry_name}', '会诊类型')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('会诊类型', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.039.00')
                 .replace('{entry_name}', '会诊原因')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('会诊原因', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 会诊意见章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '会诊意见')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '辅助检查结果') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.018.00')
                 .replace('{entry_name}', '会诊意见')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('会诊意见', '/'))))

    # 住院过程章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8648-8')
                 .replace('{section_name}', 'Hospital Course')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '诊疗过程') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.296.00')
                 .replace('{entry_name}', '诊疗过程描述')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗过程', '/'))))

    return admission_record

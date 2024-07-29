from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 24小时入出院CDA 文档构建 ==================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.55") \
        .replace('{文档类型}', "C0035") \
        .replace('{文档标识编码}', data.get('file_no')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', datetime.now().strftime('%Y%m%d%H%M%S'))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target1 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{addr_house_num}', data.get('pat_addr', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', '1') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
        .replace('{pat_marriage_no}', '1') \
        .replace('{pat_marriage}', data.get('pat_marriage', '/')) \
        .replace('{pat_nation_no}', '1') \
        .replace('{pat_nation}', data.get('pat_nation', '/')) \
        .replace('{pat_age}', data.get('pat_age', '/')) \
        .replace('{pat_occupation_no}', '20') \
        .replace('{pat_occupation}', data.get('pat_occupation', '/'))

    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author \
        .replace('{文档创作时间}', datetime.now().strftime('%Y%m%d%H%M%S')) \
        .replace('{文档创作者id}', data.get('hospital_no')) \
        .replace('{文档创作者}', data.get('hospital_name'))

    # 病史陈述者
    admission_record = admission_record + xml_header.xml_header_informant \
        .replace('{presenter_id_card}', '/') \
        .replace('{presenter_relation_no}', '/') \
        .replace('{presenter_relation}', data.get('病史叙述者', '/')) \
        .replace('{presenter_name}', '/')

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name'))

    # 最终审核者签名
    admission_record = admission_record + xml_header.xml_header_legal_authenticator \
        .replace('{医师id}', '/') \
        .replace('{展示医师}', '主任医师') \
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
        .replace('{显示医师名字}', '接诊医师') \
        .replace('{医师名字}', doc_name)
    admission_record = admission_record + xml_header.xml_header_authenticator1 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '住院医师') \
        .replace('{医师名字}', doc_name)
    admission_record = admission_record + xml_header.xml_header_authenticator1 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '主治医师') \
        .replace('{医师名字}', doc_name)

    # 关联文档
    admission_record = admission_record + xml_header.xml_header_related_document

    # 病床号、病房、病区、科室和医院的关联
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter2 \
        .replace('{入院日期}', data.get('入院日期', '/')) \
        .replace('{出院日期}', data.get('出院日期', '/'))

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

    present_illness = data.get('现病史')
    if present_illness and type(present_illness) == dict:
        present_illness = present_illness.get('value')
    if present_illness:
        # 现病史
        admission_record = admission_record + xml_body.body_component \
            .replace('{code}', xml_body.body_section_code
                     .replace('{section_code}', '10164-2')
                     .replace('{section_name}', 'HISTORY OF PRESENT ILLNESS')) \
            .replace('{text}', '<text />') \
            .replace('{entry_observation_name}', '现病史') \
            .replace('{entry}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DE02.10.071.00')
                     .replace('{entry_name}', '现病史')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', present_illness)))

    admission_record = admission_record + xml_body.body_main_health_problem2 \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11450-4')
                 .replace('{section_name}', 'PROBLEM LIST')) \
        .replace('{text}', '<text />') \
        .replace('{陈述内容可靠标志}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO5.10.143.00')
                 .replace('{entry_name}', '陈述内容可靠标志')
                 .replace('{entry_body}', xml_body.value_bl.replace('{value}', 'false'))) \
        .replace('{症状名称}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code
                          .replace('{section_code}', 'DE04.01.118.00')
                          .replace('{section_name}', '症状名称'))
                 .replace('{entry_ship_name}', '症状名称')
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('症状名称', '/')))
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE04.01.117.00')
                          .replace('{obs_display_name}', '症状描述'))
                 .replace('{entry_ship_body}', xml_body.value_st.replace('{value}', data.get('症状名称', '/')))) \
        .replace('{中医四诊}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医四诊观察结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中医四诊', '/'))))

    # 入院诊断
    admission_record = admission_record + xml_body.body_discharge_entry2 \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '46241-6')
                 .replace('{section_name}', 'HOSPITAL DISCHARGE DX')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '入院诊断') \
        .replace('{entry1}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code.replace('{section_code}', 'DE05 01.025.00')
                          .replace('{section_name}', '入院诊断-西医诊断名称'))
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('入院诊断', '/')))
                 .replace('{entry_ship_name}', '入院诊断-西医诊断编码')
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE05.01.024.00')
                          .replace('{obs_display_name}', '入院诊断-西医诊断编码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('西医诊断', '/')))) \
        .replace('{中医诊断}', data.get('中医诊断', '/')) \
        .replace('{中医诊断编码}', data.get('中医诊断编码', '/')) \
        .replace('{中医证候}', data.get('中医证候', '/')) \
        .replace('{中医证候编码}', data.get('中医证候编码', '/'))

    if data.get('出院情况') and type(data.get('出院情况')) == dict:
        chu_info = data.get('出院情况').get('value')
    elif data.get('出院情况') and type(data.get('出院情况')) == str:
        chu_info = data.get('出院情况')
    else:
        chu_info = '/'

    if data.get('入院情况') and type(data.get('入院情况')) == dict:
        ru_info = data.get('入院情况').get('value')
    elif data.get('入院情况') and type(data.get('入院情况')) == str:
        ru_info = data.get('入院情况')
    else:
        ru_info = '/'

    # 住院过程
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8648-8')
                 .replace('{section_name}', 'Hospital Course')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '住院过程') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.148.00')
                 .replace('{entry_name}', '入院情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', ru_info))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.296.00')
                 .replace('{entry_name}', '诊疗过程描述')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗经过', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.193.00')
                 .replace('{entry_name}', '出院情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', chu_info))) \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 出院诊断
    admission_record = admission_record + xml_body.body_discharge_entry2 \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11535-2')
                 .replace('{section_name}', 'Discharge Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '出院诊断') \
        .replace('{entry1}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code.replace('{section_code}', 'DE05 01.025.00')
                          .replace('{section_name}', '出院诊断-西医诊断名称'))
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('出院诊断', '/')))
                 .replace('{entry_ship_name}', '出院诊断-西医诊断编码')
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE05.01.024.00')
                          .replace('{obs_display_name}', '出院诊断-西医诊断编码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('西医诊断', '/')))) \
        .replace('{中医诊断}', data.get('中医诊断', '/')) \
        .replace('{中医诊断编码}', data.get('中医诊断编码', '/')) \
        .replace('{中医证候}', data.get('中医证候', '/')) \
        .replace('{中医证候编码}', data.get('中医证候编码', '/'))

    if data.get('出院医嘱') and type(data.get('出院医嘱')) == dict:
        yizhu_info = data.get('出院医嘱').get('value')
    elif data.get('出院医嘱') and type(data.get('出院医嘱')) == str:
        yizhu_info = data.get('出院医嘱')
    else:
        yizhu_info = '/'
    # 出院医嘱
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '46209-3')
                 .replace('{section_name}', 'PROVIDER ORDERS')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '出院医嘱') \
        .replace('{entry}', xml_body.body_section_entry2
                 .replace('{entry_code}', 'DE06.00.287.00')
                 .replace('{entry_name}', '出院医嘱')
                 .replace('{time}', data.get('出院日期', '/'))
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', yizhu_info)))

    return admission_record

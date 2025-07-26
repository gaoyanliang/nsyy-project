from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 抢救记录CDA 文档构建 ======================================
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
    rescue = data.get('抢救记录', '/')
    if rescue and type(rescue) == dict:
        ct = rescue.get('日期时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.64") \
        .replace('{文档类型}', "C0044") \
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

    if '住院医师' in data:
        doc = data.get('住院医师')
    elif '主治医师' in data:
        doc = data.get('主治医师')
    elif '经治医师' in data:
        doc = data.get('经治医师')
    else:
        doc = {}
    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator4 \
        .replace('{签名时间}', doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{显示医师名称}', '医师签名') \
        .replace('{医师名字}', doc.get('displayinfo', '/')) \
        .replace('{职称编码}', '/') \
        .replace('{医师职称}', doc.get('职称', '/')) \

    admission_record = admission_record + xml_header.xml_header_associated_person \
        .replace('{type_code}', 'CON') \
        .replace('{class_code}', 'ECON') \
        .replace('{name1}', data.get('参与抢救人员', '/')) \
        .replace('{name2}', '/') \
        .replace('{name3}', '/')

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
                          .replace('{obs_display_name}', '疾病诊断名称'))
                 .replace('{entry_ship_name}', '疾病诊断')
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('疾病诊断名称', '/')))
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE02.10.026.00')
                          .replace('{obs_display_name}', '疾病诊断编码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('疾病诊断编码', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.134.00')
                 .replace('{entry_name}', '病情变化情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('病情变化情况', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 治疗计划章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '治疗计划') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE09.00.119.00')
                 .replace('{entry_name}', '注意事项')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('注意事项', '/'))))

    # 手术操作章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '47519-4')
                 .replace('{section_name}', 'HISTORY OF PROCEDURES')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '手术操作') \
        .replace('{entry1}', xml_body.body_section_entry4
                 .replace('{手术部位}', data.get('手术部位', '/'))
                 .replace('{entry_ship1}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE06.00.094.00')
                          .replace('{display_name}', '手术(操作)名称')
                          .replace('{value}', xml_body.value_st.replace('{value}', data.get('手术操作名称', '/'))))
                 .replace('{entry_ship2}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE08.50.037.00')
                          .replace('{display_name}', '介入物名称')
                          .replace('{value}', xml_body.value_st.replace('{value}', data.get('介入物名称', '/'))))
                 .replace('{entry_ship3}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE06.00.251.00')
                          .replace('{display_name}', '操作方法')
                          .replace('{value}', xml_body.value_st.replace('{value}', data.get('操作方法', '/'))))
                 .replace('{entry_ship4}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE06.00.250.00')
                          .replace('{display_name}', '操作次数')
                          .replace('{value}', xml_body.value_pq.replace('{value}', data.get('操作次数', '/')).replace('{unit}', '次')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.094.00')
                 .replace('{entry_name}', '抢救措施')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('抢救措施', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.221.00')
                 .replace('{entry_name}', '抢救开始日期时间')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('抢救开始日期时间', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.218.00')
                 .replace('{entry_name}', '抢救结束日期时间')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('抢救结束日期时间', '/')))) \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 实验室检查章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '30954-2')
                 .replace('{section_name}', 'STUDIES SUMMARY')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '实验室检查') \
        .replace('{entry}', xml_body.body_section_entry5
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('检查/检验项目名称', '/')))
                 .replace('{entry_ship1}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE04.30.009.00')
                          .replace('{display_name}', '检查/检验结果')
                          .replace('{value}', xml_body.value_st.replace('{value}', data.get('检查/检验结果', '/'))))
                 .replace('{entry_ship2}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE04.30.015.00')
                          .replace('{display_name}', '检查/检验结果定量结果')
                          .replace('{value}', xml_body.value_pq.replace('{value}', data.get('定量结果', '/')).replace('{unit}', 'mmHg')))
                 .replace('{entry_ship3}', xml_body.body_section_entry_relation_ship1
                          .replace('{code}', 'DE06.00.251.00')
                          .replace('{display_name}', '检查/检验结果代码')
                          .replace('{value}', xml_body.value_cd.replace('{code}', data.get('检查/检验结果代码', '/')).replace('{display_name}', data.get('检查/检验结果', '/')))))
    return admission_record

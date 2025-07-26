from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 术前小结CDA 文档构建 ======================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    stage = data.get('术前小结', '/')
    if stage and type(stage) == dict:
        ct = stage.get('日期时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.66") \
        .replace('{文档类型}', "C0046") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', str(ct))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target2 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', '1') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
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
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', doc.get('displayinfo', '/')) \
        .replace('{显示医师名字}', '手术者')
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', doc.get('displayinfo', '/')) \
        .replace('{显示医师名字}', '医师')

    admission_record = admission_record + xml_header.xml_header_participant2 \
        .replace('{联系人电话}', data.get('联系人电话', '/')) \
        .replace('{联系人姓名}', data.get('联系人姓名', '/'))

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
    # 简要病情
    abstract = data.get('简要病情', '/')
    if abstract and type(abstract) == dict:
        abstract = abstract.get('value', '/')
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', 'DE06.00.182.00')
                 .replace('{section_name}', '病历摘要章节')) \
        .replace('{text}', '<text>' + abstract + '</text>') \
        .replace('{entry_observation_name}', '病历摘要章节') \
        .replace('{entry}', '')

    # 术前诊断章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11535-2')
                 .replace('{section_name}', 'HOSPITAL DISCHARGE DX')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '术前诊断章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'D05.01.024.00')
                 .replace('{entry_name}', '术前诊断编码')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', ''))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.070.00')
                 .replace('{entry_name}', '诊断依据')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊断依据', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 既往史
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11348-0')
                 .replace('{section_name}', 'HISTORY OF PAST ILINESS')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '术前诊断章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'D05.01.024.00')
                 .replace('{entry_name}', '过敏史标志')
                 .replace('{entry_body}', xml_body.value_bl.replace('{value}', 'false')
                          .replace('{display_name}', ''))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.022.00')
                 .replace('{entry_name}', '过敏史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('过敏史', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 辅助检查章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '辅助检査章节')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '辅助检查') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.30.009.00')
                 .replace('{entry_name}', '辅助检查结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('辅助检查', '/'))))

    # 手术章节
    zhizheng = data.get('手术指征', '/')
    if zhizheng and type(zhizheng) == dict:
        zhizheng = zhizheng.get('value', '/')
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '47519-4')
                 .replace('{section_name}', 'HISTORY OF PROCEDURES')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '手术章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.151.00')
                 .replace('{entry_name}', '手术适应证')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('手术适应证', '/'))
                          .replace('{display_name}', ''))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.141.00')
                 .replace('{entry_name}', '手术禁忌症')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('手术禁忌症', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.340.00')
                 .replace('{entry_name}', '手术指征')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', zhizheng))) \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 会诊章节
    taolun = data.get('术前讨论意见', '/')
    if taolun and type(taolun) == dict:
        taolun = taolun.get('value', '/')
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '会诊意见')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '会诊意见') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.018.00')
                 .replace('{entry_name}', '会诊意见')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', taolun)))

    # 治疗计划章节
    shoushu = data.get('拟行手术名称和方式', '/')
    if shoushu and type(shoushu) == dict:
        shoushu = shoushu.get('value', '/')
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '治疗计划') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.093.00')
                 .replace('{entry_name}', '拟实施手术及操作编码')
                 .replace('{entry_body}', xml_body.value_cd2.replace('{code}', '/'))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.094.00')
                 .replace('{entry_name}', '拟实施手术及操作名称')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', shoushu))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.187.00')
                 .replace('{entry_name}', '拟实施手术目标部位名称')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('拟实施手术目标部位名称', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.221.00')
                 .replace('{entry_name}', '拟实施手术及操作日期时间')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('拟实施手术及操作日期时间', '/')))) \
        .replace('{entry5}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.073.00')
                 .replace('{entry_name}', '拟实施麻醉方法代码')
                 .replace('{entry_body}', xml_body.value_cd2.replace('{code}', '/'))) \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 注意事项
    zhuyi = data.get('手术注意事项', '/')
    if zhuyi and type(zhuyi) == dict:
        zhuyi = zhuyi.get('value', '/')
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', 'DE09.00.119.00')
                 .replace('{section_name}', '注意事项')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '注意事项') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE09.00.119.00')
                 .replace('{entry_name}', '注意事项')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', zhuyi))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.254.00')
                 .replace('{entry_name}', '手术要点')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('手术要点', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.271.00')
                 .replace('{entry_name}', '术前准备')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('术前准备', '/')))) \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    return admission_record

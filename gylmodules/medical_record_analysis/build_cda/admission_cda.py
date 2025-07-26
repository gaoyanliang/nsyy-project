from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 入院CDA 文档构建 ==========================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.54") \
        .replace('{文档类型}', "C0034") \
        .replace('{文档标识编码}', data.get('file_no', '/')) \
        .replace('{文档标题}', data.get('file_title', '/')) \
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
        .replace('{医师}', '/')

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
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter \
        .replace('{入院时间}', str(data.get('pat_time'))) \
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

    present_illness = data.get('现病史')
    if present_illness and type(present_illness) == dict:
        present_illness = present_illness.get('value')
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

    past_illness = data.get('既往史')
    if '外伤史' in past_illness and type(past_illness) == dict:
        his_illness = past_illness.get('外伤史')
    elif '疾病史' in past_illness and type(past_illness) == dict:
        his_illness = past_illness.get('疾病史')
    elif '既往疾病史' in past_illness and type(past_illness) == dict:
        his_illness = past_illness.get('既往疾病史')
    else:
        his_illness = '/'

    if '药物及食物过敏史' in past_illness and type(past_illness) == dict:
        allergy_his = past_illness.get('药物及食物过敏史')
    elif '药品及食物过敏史' in past_illness and type(past_illness) == dict:
        allergy_his = past_illness.get('药品及食物过敏史')
    else:
        allergy_his = '/'

    value = past_illness.get('value') if past_illness and type(past_illness) == dict else past_illness
    # 既往史
    admission_record = admission_record + xml_body.body_history_of_past_illness \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11348-0')
                 .replace('{section_name}', 'HISTORY OF PAST ILLNESS')) \
        .replace('{text}', '<text>' + value + '</text>') \
        .replace('{history_of_illness}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code
                          .replace('{section_code}', 'DE05.10.031.00')
                          .replace('{section_name}', '—般健康状况标志'))
                 .replace('{entry_ship_name}', '疾病史(含外伤)')
                 .replace('{value}', xml_body.value_bl.replace('{value}', 'false'))
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE02.10.026.00')
                          .replace('{obs_display_name}', '疾病史含外伤'))
                 .replace('{entry_ship_body}', xml_body.value_st.replace('{value}', his_illness))) \
        .replace('{history_of_infectious_diseases}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code
                          .replace('{section_code}', 'DE05.10.119.00')
                          .replace('{section_name}', '患者传染性标志'))
                 .replace('{entry_ship_name}', '传染病史')
                 .replace('{value}', xml_body.value_bl.replace('{value}', 'true'))
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE02.10.008.00')
                          .replace('{obs_display_name}', '传染病史'))
                 .replace('{entry_ship_body}', xml_body.value_st.replace('{value}', past_illness.get('传染病史',
                                                                                                     '/') if past_illness and type(
        past_illness) == dict else '/'))) \
        .replace('{marriage_and_childbearing_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.098.00')
                 .replace('{entry_name}', '婚育史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', past_illness.get('婚育史',
                                                                                                '/') if past_illness and type(
        past_illness) == dict else '/'))) \
        .replace('{allergy_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.022.00')
                 .replace('{entry_name}', '过敏史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', allergy_his))) \
        .replace('{surgical_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.022.00')
                 .replace('{entry_name}', '手术史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', past_illness.get('手术史',
                                                                                                '/') if past_illness and type(
        past_illness) == dict else '/')))

    # 预防接种史
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11369-6')
                 .replace('{section_name}', 'HISTORY OF IMMUNIZATIONS')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '预防接种史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.101.00')
                 .replace('{entry_name}', '预防接种史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', past_illness.get('预防接种史',
                                                                                                '/') if past_illness and type(
        past_illness) == dict else '/')))

    # 输血史
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '56836-0')
                 .replace('{section_name}', 'History of blood transfusion')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '输血史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.100.00')
                 .replace('{entry_name}', '输血史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', past_illness.get('输血史',
                                                                                                '/') if past_illness and type(
        past_illness) == dict else '/')))

    social_his = data.get('个人史')
    if social_his is None:
        social_his = '/'
    if social_his and type(social_his) == dict:
        social_his = social_his.get('value')
    # 个人史
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29762-2')
                 .replace('{section_name}', 'Social history')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '个人史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.097.00')
                 .replace('{entry_name}', '个人史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', social_his)))

    # 月经史
    menstrual_his = data.get('月经史')
    if menstrual_his is None:
        menstrual_his = '/'
    if menstrual_his and type(menstrual_his) == dict:
        menstrual_his = menstrual_his.get('value')
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '49033-4')
                 .replace('{section_name}', 'Menstrual History')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '月经史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.102.00')
                 .replace('{entry_name}', '月经史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', menstrual_his)))

    family_his = data.get('家族史')
    if family_his is None:
        family_his = '/'
    if family_his and type(family_his) == dict:
        family_his = family_his.get('value')
    # 家族史
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10157-6')
                 .replace('{section_name}', 'HISTORY OF FAMILY MEMBER DISEASES')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '家族史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.103.00')
                 .replace('{entry_name}', '家族史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', family_his)))

    vital_signs = data.get('体格检查')
    if 'value' in vital_signs:
        xueya = []
        if '血压' in vital_signs:
            # 使用 split 方法将字符串按斜杠分割
            xueya = vital_signs.get('血压').split("/")
        # 生命体征
        admission_record = admission_record + xml_body.body_vital_signs \
            .replace('{code}', xml_body.body_section_code
                     .replace('{section_code}', '8716-3')
                     .replace('{section_name}', 'VITAL SIGNS')) \
            .replace('{text}', '<text />') \
            .replace('{body_temperature}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.186.00')
                     .replace('{entry_name}', '体温°C')
                     .replace('{entry_body}',
                              xml_body.value_pq.replace('{value}', vital_signs.get('体温', '/')).replace('{unit}',
                                                                                                         '°C'))) \
            .replace('{pulse_rate}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.118.00')
                     .replace('{entry_name}', '脉率(次/min)')
                     .replace('{entry_body}',
                              xml_body.value_pq.replace('{value}', vital_signs.get('脉搏', '/')).replace('{unit}',
                                                                                                         '次/min'))) \
            .replace('{respiratory_rate}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.082.00')
                     .replace('{entry_name}', '呼吸频率(次/min)')
                     .replace('{entry_body}',
                              xml_body.value_pq.replace('{value}', vital_signs.get('呼吸', '/')).replace('{unit}',
                                                                                                         '次/min'))) \
            .replace('{systolic}', xueya[0] if xueya else '/') \
            .replace('{diastolic}', xueya[1] if xueya else '/') \
            .replace('{height}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.167.00')
                     .replace('{entry_name}', '身高（cm）')
                     .replace('{entry_body}',
                              xml_body.value_pq.replace('{value}', vital_signs.get('身高', '/')).replace('{unit}',
                                                                                                         'cm'))) \
            .replace('{weight}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.188.00')
                     .replace('{entry_name}', '体重（kg）')
                     .replace('{entry_body}',
                              xml_body.value_pq.replace('{value}', vital_signs.get('体重', '/')).replace('{unit}',
                                                                                                         'kg')))

        # 体格检査章节
        admission_record = admission_record + xml_body.body_physical_examination \
            .replace('{code}', xml_body.body_section_code
                     .replace('{section_code}', '29545-1')
                     .replace('{section_name}', 'PHYSICAL EXAMINATION')) \
            .replace('{text}', '<text>' + vital_signs.get('value', '/') + '</text>') \
            .replace('{一般状况检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.219.00')
                     .replace('{entry_name}', '一般状况检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('一般状况检查', '/')))) \
            .replace('{皮肤和粘膜检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.126.00')
                     .replace('{entry_name}', '皮肤和粘膜检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('皮肤和粘膜检査', '/')))) \
            .replace('{全身浅表淋巴结检查}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.114.00')
                     .replace('{entry_name}', '全身浅表淋巴结检查结果')
                     .replace('{entry_body}',
                              xml_body.value_st.replace('{value}', data.get('全身浅表淋巴结检查', '/')))) \
            .replace('{头部及其器官检查}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.261.00')
                     .replace('{entry_name}', '头部及其器官检查结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('头部检查', '/')))) \
            .replace('{颈部检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.255.00')
                     .replace('{entry_name}', '颈部检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('颈部检查', '/')))) \
            .replace('{胸部检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.263.00')
                     .replace('{entry_name}', '胸部检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('胸部检查', '/')))) \
            .replace('{腹部检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.046.00')
                     .replace('{entry_name}', '腹部检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('腹部检查', '/')))) \
            .replace('{肛门指诊检查}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.065.00')
                     .replace('{entry_name}', '肛门指诊检查结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('肛门指诊检查', '/')))) \
            .replace('{外生殖器检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.195.00')
                     .replace('{entry_name}', '外生殖器检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('外生殖器检査', '/')))) \
            .replace('{脊柱检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.093.00')
                     .replace('{entry_name}', '脊柱检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('脊柱检査', '/')))) \
            .replace('{四肢检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.179.00')
                     .replace('{entry_name}', '四肢检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('四肢检査', '/')))) \
            .replace('{脊柱检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO4.10.093.00')
                     .replace('{entry_name}', '脊柱检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('脊柱检査', '/')))) \
            .replace('{神经系统检査}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO5.10.149.00')
                     .replace('{entry_name}', '神经系统检査结果')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('神经系统检査', '/')))) \
            .replace('{专科情况}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO8.10.061.00')
                     .replace('{entry_name}', '专科情况')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}',
                                                                        data.get('专科情况').get('value') if data.get(
                                                                            '专科情况') and type(
                                                                            data.get('专科情况')) == dict else data.get(
                                                                            '专科情况', '/'))))

    # 辅助检査章节
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', '<code displayName="辅助检查" />') \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '辅助检查') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.30.009.00')
                 .replace('{entry_name}', '辅助检查')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('辅助检查', '/'))))

    admission_record = admission_record + xml_body.body_main_health_problem \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11450-4')
                 .replace('{section_name}', 'PROBLEM LIST')) \
        .replace('{text}', '<text />') \
        .replace('{陈述内容可靠标志}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO5.10.143.00')
                 .replace('{entry_name}', '陈述内容可靠标志')
                 .replace('{entry_body}', xml_body.value_bl.replace('{value}', 'false'))) \
        .replace('{西医初步诊断}', xml_body.body_health_entry_western
                 .replace('{code1}', 'DE05.01.025.00')
                 .replace('{display_name1}', '初步诊断-西医诊断名称')
                 .replace('{time}', '/')
                 .replace('{value1}', data.get('西医诊断', '/'))
                 .replace('{code2}', 'DEO5.01.024.00')
                 .replace('{display_name2}', '初步诊断-西医诊断编码')
                 .replace('{code3}', '/')
                 .replace('{display_name3}', data.get('西医诊断', '/'))
                 .replace('{code4}', 'DEO5.01.080.00')
                 .replace('{display_name4}', '入院诊断顺位')
                 .replace('{value2}', '/')) \
        .replace('{中医四诊}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.028.00')
                 .replace('{entry_name}', '中医四诊观察结果')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中医四诊', '/')))) \
        .replace('{中医初步诊断}', xml_body.body_health_entry_chinese
                 .replace('{code1}', 'DE05.10.172.00')
                 .replace('{display_name1}', '初步诊断-中医病名名称')
                 .replace('{time}', '/')
                 .replace('{value1}', data.get('中医诊断', '/'))
                 .replace('{code2}', 'DEO5.10.130.00')
                 .replace('{display_name2}', '初步诊断-中医病名代码')
                 .replace('{code3}', '/')
                 .replace('{display_name3}', data.get('中医诊断', '/'))
                 .replace('{code4}', 'DEO5.10.172.00')
                 .replace('{display_name4}', '初步诊断-中医证候名称')
                 .replace('{value2}', data.get('证型', '/'))
                 .replace('{code5}', 'DEO5.10.130.00')
                 .replace('{display_name5}', '初步诊断-中医证候代码')
                 .replace('{code6}', '/')
                 .replace('{display_name6}', data.get('证型', '/'))
                 .replace('{code7}', 'DEO5.01.080.00')
                 .replace('{display_name7}', '入院诊断顺位')
                 .replace('{value3}', '/')) \
        .replace('{西医修正诊断}', '') \
        .replace('{中医修正诊断}', '') \
        .replace('{西医确定诊断}', '') \
        .replace('{中医确定诊断}', '') \
        .replace('{西医补充诊断}', '')

    # todo 主要健康问题章节

    if '治则治法' in data:
        # 治疗计划章节
        admission_record = admission_record + xml_body.body_component \
            .replace('{code}', xml_body.body_section_code
                     .replace('{section_code}', '18776-5')
                     .replace('{section_name}', 'TREATMENT PLAN')) \
            .replace('{text}', '<text />') \
            .replace('{entry}', xml_body.body_section_entry
                     .replace('{entry_code}', 'DEO6.00.300.00')
                     .replace('{entry_name}', '治则治法')
                     .replace('{entry_body}', xml_body.value_st.replace('{value}', "治则治法")))

    return admission_record

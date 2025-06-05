from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
========================================== 出院CDA 文档构建 ==========================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.69") \
        .replace('{文档类型}', "C0049") \
        .replace('{文档标识编码}', data.get('file_no', '/')) \
        .replace('{文档标题}', data.get('file_title', '/')) \
        .replace('{文档生成时间}', datetime.now().strftime('%Y%m%d%H%M%S'))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target2 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', data.get('性别代码', '/') if data.get('性别代码') else '/') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
        .replace('{pat_age}', data.get('pat_age', '/')) \


    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author \
        .replace('{文档创作时间}', datetime.now().strftime('%Y%m%d%H%M%S')) \
        .replace('{文档创作者id}', data.get('hospital_no', '/')) \
        .replace('{文档创作者}', data.get('hospital_name', '/'))

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no', '/')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name', '/'))

    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', '/') \
        .replace('{医师id}', data.get('主任医师', '/') if data.get('主任医师') else '/') \
        .replace('{显示医师名字}', '主任医师') \
        .replace('{医师名字}', data.get('主任医师姓名', '/') if data.get('主任医师姓名') else '/')
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', '/') \
        .replace('{医师id}', data.get('住院医师', '/') if data.get('住院医师') else '/') \
        .replace('{显示医师名字}', '住院医师') \
        .replace('{医师名字}', data.get('住院医师姓名', '/') if data.get('住院医师姓名') else '/')
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', '/') \
        .replace('{医师id}', data.get('主治医师', '/') if data.get('主治医师') else '/') \
        .replace('{显示医师名字}', '主治医师') \
        .replace('{医师名字}', data.get('主治医师姓名', '/') if data.get('主治医师姓名') else '/')

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
    if data.get('出院记录_入院情况') and type(data.get('出院记录_入院情况')) == dict:
        info = data.get('入院情况').get('value')
    elif data.get('出院记录_入院情况') and type(data.get('出院记录_入院情况')) == str:
        info = data.get('出院记录_入院情况')
    else:
        info = '/'
    # 入院情况
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11450-4')
                 .replace('{section_name}', 'Problem list')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '入院情况') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.10.148.00')
                 .replace('{entry_name}', '入院情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', info)))

    # 入院诊断
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11535-2')
                 .replace('{section_name}', 'HOSPITAL DISCHARGE DX')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '入院诊断') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '入院诊断编码')
                 .replace('{entry_body}',
                          xml_body.value_cd.replace('{code}', '/').replace('{display_name}',
                                                                           data.get('入院诊断', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.092.00')
                 .replace('{entry_name}', '入院日期时间')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('入院日期', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.50.128.00')
                 .replace('{entry_name}', '阳性辅助检査结果')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/').replace('{display_name}',
                                                                                           data.get('阳性辅助检査',
                                                                                                    '/')))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.300.00')
                 .replace('{entry_name}', '治则治法')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/').replace('{display_name}',
                                                                                           data.get('治则治法', '/')))) \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    zhenliaojg = data.get('诊疗经过')
    if not zhenliaojg:
        zhenliaojg = '/'
    elif type(zhenliaojg) == dict:
        zhenliaojg = zhenliaojg.get('value', '/')
    # 住院过程
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8648-8')
                 .replace('{section_name}', 'Hospital Course')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '住院过程') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.296.00')
                 .replace('{entry_name}', '诊疗过程描述')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', zhenliaojg)))

    # 医嘱用药
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '46209-3')
                 .replace('{section_name}', 'Provider Orders')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '医嘱用药') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE08.50.047.00')
                 .replace('{entry_name}', '中药煎煮方法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中药煎煮方法', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.136.00')
                 .replace('{entry_name}', '中药用药方法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中药用药方法', '/')))) \
        .replace('{entry3}', '') \
        .replace('{entry4}', '') \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    if data.get('出院情况') and type(data.get('出院情况')) == dict:
        chu_info = data.get('出院情况').get('value')
    elif data.get('出院情况') and type(data.get('出院情况')) == str:
        chu_info = data.get('出院情况')
    else:
        chu_info = '/'

    if data.get('出院医嘱') and type(data.get('出院医嘱')) == dict:
        yizhu_info = data.get('出院医嘱').get('value')
    elif data.get('出院医嘱') and type(data.get('出院医嘱')) == str:
        yizhu_info = data.get('出院医嘱')
    else:
        yizhu_info = '/'

    chuyuanqk = data.get('出院情况')
    if not chuyuanqk:
        chuyuanqk = '/'
    elif type(chuyuanqk) == dict:
        chuyuanqk = chuyuanqk.get('value', '/')


    # 出院诊断
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11535-2')
                 .replace('{section_name}', 'Discharge Diagnosis')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '出院诊断') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.193.00')
                 .replace('{entry_name}', '出院情况')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', chu_info))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.017.00')
                 .replace('{entry_name}', '出院日期时间')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('出院日期时间', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code.replace('{section_code}', 'DE05.01.025.00')
                          .replace('{section_name}', '出院诊断-西医诊断名称'))
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('西医诊断', '/')))
                 .replace('{entry_ship_name}', '出院诊断-西医诊断名称')
                 .replace('{obs_code}', xml_body.body_observation_code1.replace('{obs_code}', 'DE05.01.024.00')
                          .replace('{obs_display_name}', '出院诊断-西医诊断编码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('西医诊断', '/')))) \
        .replace('{entry4}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '出院诊断-中医医诊断名称')
                          .replace('{obs_name}', data.get('中医诊断', '/')))
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('中医诊断', '/')))
                 .replace('{entry_ship_name}', '出院诊断-中医诊断名称')
                 .replace('{obs_code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '出院诊断-中医病名代码')
                          .replace('{obs_name}', '中医病名代码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医诊断', '/')))) \
        .replace('{entry5}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.172.00')
                          .replace('{obs_display_name}', '出院诊断-中医证候名称')
                          .replace('{obs_name}', data.get('中医证候', '/')))
                 .replace('{value}', xml_body.value_st.replace('{value}', data.get('中医证候', '/')))
                 .replace('{entry_ship_name}', '出院诊断-中医证候名称')
                 .replace('{obs_code}', xml_body.body_observation_code2.replace('{obs_code}', 'DE05.10.130.00')
                          .replace('{obs_display_name}', '出院诊断-中医证候代码')
                          .replace('{obs_name}', '中医证候代码'))
                 .replace('{entry_ship_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('中医证候', '/')))) \
        .replace('{entry6}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.01.117.00')
                 .replace('{entry_name}', '出院时症状与体征')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', chuyuanqk))) \
        .replace('{entry7}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.287.00')
                 .replace('{entry_name}', '出院医嘱')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', yizhu_info))) \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')
    return admission_record

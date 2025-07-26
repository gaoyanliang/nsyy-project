from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime
import re

"""
====================================================================================================
========================================== 转科记录CDA 文档构建 ======================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    re = data.get('转入记录')
    if re:
        ct = re.get('日期时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.62") \
        .replace('{文档类型}', "C0042") \
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

    doc = data.get('转出医师签名', '/')
    admission_record = admission_record + xml_header.xml_header_authenticator2 \
        .replace('{签名时间}', doc.get('signtime', '/')) \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', doc.get('displayinfo', '/')) \
        .replace('{显示医师名字}', '转出医师签名')

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
        .replace('{显示医师名字}', '转入医师签名')

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
    zhusu = data.get('主诉')
    if zhusu and type(zhusu) == dict:
        zhusu = zhusu.get('value')
    admission_record = admission_record + xml_body.body_component \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10154-3')
                 .replace('{section_name}', 'CHIEF COMPLAINT')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '主诉') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.01.119.00')
                 .replace('{entry_name}', '主诉')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', zhusu)))

    ruyuan = data.get('入院情况')
    if ruyuan and type(ruyuan) == dict:
        ruyuan = ruyuan.get('value')

    zhenduan = data.get('入院诊断')
    if zhenduan and type(zhenduan) == dict:
        zhenduan = zhenduan.get('value')

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
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', ruyuan))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '入院诊断-西医诊断名称')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', zhenduan))) \
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

    qingkuang = data.get('目前情况')
    if qingkuang and type(qingkuang) == dict:
        qingkuang = qingkuang.get('value')

    muqianzhenduan = data.get('目前诊断')
    if muqianzhenduan and type(muqianzhenduan) == dict:
        muqianzhenduan = muqianzhenduan.get('value')

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
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', qingkuang))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE05.01.024.00')
                 .replace('{entry_name}', '目前诊断-西医诊断名')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', muqianzhenduan))) \
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
                 .replace('{entry_name}', '转入诊疗计划')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗计划', '/')))) \
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

    # 转科记录章节
    if zhusu:
        pattern = r"由([\u4e00-\u9fa5]+)转入([\u4e00-\u9fa5]+)"
        matches = re.findall(pattern, zhusu)
        chu = '/'
        ru = '/'
        if matches:
            chu = matches[0][0]
            ru = matches[0][1]
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '/')
                 .replace('{section_name}', '转科记录')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '转科记录') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.314.00')
                 .replace('{entry_name}', '转科记录类型')
                 .replace('{entry_body}', xml_body.value_cd.replace('{code}', '1')
                          .replace('{display_name}', '转入记录'))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE08.10.026.00')
                 .replace('{entry_name}', '转出科室名称')
                 .replace('{entry_body}',  xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', chu))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE08.10.026.00')
                 .replace('{entry_name}', '转入科室名称')
                 .replace('{entry_body}',  xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', ru))) \
        .replace('{entry4}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.315.00')
                 .replace('{entry_name}', '转科目的')
                 .replace('{entry_body}',  xml_body.value_cd.replace('{code}', '/')
                          .replace('{display_name}', data.get('转科目的', '/')))) \
        .replace('{entry5}', '') \
        .replace('{entry6}', '') \
        .replace('{entry7}', '') \
        .replace('{entry8}', '') \
        .replace('{entry9}', '')

    # 用药章节
    admission_record = admission_record + xml_body.body_discharge_entry \
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10160-0')
                 .replace('{section_name}', 'HISTORY OF MEDICATION USE')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '用药章节') \
        .replace('{entry1}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.287.00')
                 .replace('{entry_name}', '中药处方医嘱内容')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中药处方医嘱', '/')))) \
        .replace('{entry2}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE08.50.047.00')
                 .replace('{entry_name}', '中药饮片煎煮法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('中药饮片煎煮法', '/')))) \
        .replace('{entry3}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE06.00.136.00')
                 .replace('{entry_name}', '中药用药方法的描述')
                 .replace('{entry_body}', xml_body.value_ts.replace('{value}', data.get('中药用药方法', '/')))) \
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
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', data.get('诊疗经过', '/'))))

    return admission_record

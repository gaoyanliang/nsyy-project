from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime
import re

"""
====================================================================================================
========================================== 术前讨论 CDA 文档构建 ======================================
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
    ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.62") \
        .replace('{文档类型}', "C0042") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', str(ct))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target5 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', data.get('性别代码', '/') if data.get('性别代码') else '/') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
        .replace('{pat_birth_time}', get_birthday_from_id(data.get('pat_id_card', '/'))) \
        .replace('{pat_age}', data.get('pat_age', '/')) \
        .replace('{讨论时间}', str(data.get('记录时间', '/')) if data.get('记录时间') else '/') \
        .replace('{讨论地点}', data.get('地点', '/') if data.get('地点') else '/')

    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author \
        .replace('{文档创作时间}', str(data.get('文档创建时间', '/'))) \
        .replace('{文档创作者id}', '/') \
        .replace('{文档创作者}', data.get('文档作者', '/'))

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name'))

    admission_record = admission_record + xml_header.xml_header_authenticator4 \
        .replace('{签名时间}', '/') \
        .replace('{显示医师名称}', '手术者') \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', '/') \
        .replace('{职称编码}', '/') \
        .replace('{医师职称}', data.get('医师职称', '/'))

    admission_record = admission_record + xml_header.xml_header_authenticator4 \
        .replace('{签名时间}', '/') \
        .replace('{显示医师名称}', '麻醉医师') \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', data.get('麻醉医师', '/') if data.get('麻醉医师') else '/') \
        .replace('{职称编码}', '/') \
        .replace('{医师职称}', data.get('医师职称', '/'))

    admission_record = admission_record + xml_header.xml_header_authenticator4 \
        .replace('{签名时间}', '/') \
        .replace('{显示医师名称}', '医师') \
        .replace('{医师id}', '/') \
        .replace('{医师名字}', data.get('主治医师', '/') if data.get('主治医师') else '/') \
        .replace('{职称编码}', '/') \
        .replace('{医师职称}', data.get('医师职称', '/'))

    admission_record = admission_record + xml_header.xml_header_participant2 \
        .replace('{联系人电话}', data.get('联系人电话', '/')) \
        .replace('{联系人姓名}', data.get('联系人姓名', '/'))

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
    # 主诉
    zhusu = data.get('主诉')
    if not zhusu:
        zhusu = '/'
    elif type(zhusu) == dict:
        zhusu = zhusu.get('value', '/')
    admission_record = admission_record + f"""
            <section>
                <!--术前诊断章节-->
                <component>
                    <section>
                        <code code="10219-4" displayName="Surgical operation note preoperative Dx" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
                        <text/>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE05.01.024.00" codesystem="2.16.156.10011.2.2.1" codeSystemName=" 卫生信息数据元目录" displayName="术前诊断编码"/>
                                <value xsi:type="CD" code="01" codeSystem="2.16.156.10011.23.3.11.3" codeSystemName="ICD-10 诊断编码表"/>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.092.00" codeSystem="2.16.156.10011.2.2.1" codeSystemame="卫生信息数据元目录" displayName="入院日期时间"/>
                                <value xsi:type="TS" value="{data.get('入院日期', '/')}"/>
                            </observation>
                        </entry>
                    </section>
                </component>
                <!-- 治疗计划章节-->
                <component>
                    <section>
                        <code code="18776-5" displayName="TREATMENT PLAN" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
                        <text/>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.094.00" codesystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="拟实施手术及操作名称"/>
                                <value xsi:type="ST">/</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.093.00"
                                      codeSystem="2.16.156.10011.2.2.1" codeSystemName=" 卫生信息数据元目录"
                                      displayName="拟实施手术及操作编码"/>
                                <value xsi:type="CD" code="01"
                                       codeSystem="2.16.156.10011.23.3.12" codeSystemName="ICD-9-CM-3"/>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                            <code code="DE06.00.187.00" codesystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="拟实施手术目标部位名称"/>
                            <value xsi:type="ST">/</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.221.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="拟实施手术及操作日期时间"/>
                                <value xsi:type="TS" value="/"/>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.073.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="拟实施麻醉方法代码"/>
                                <value xsi:type="CD" code="01" codeSystem="2.16.156.10011.2.3.1.159" codeSystemName="实施麻醉方法代码表"/>
                            </observation>
                        </entry>
                    </section>
                </component>
                <!--        手术操作章节-->
                <component>
                    <section>
                        <code code="47519-4" displayName="HISTORY OF PROCEDURES" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
                        <text/>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                            <code code="DE06.00.254.00" codesystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="手术要点"/>
                            <value xsi:type="ST">{data.get('手术要点', '/')}</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.271.00" codesystem="2.16.156.10011.2.2.1"
                                      codeSystemame="卫生信息数据元目录" displayName="术前准备"/>
                                <value xsi:type="ST">{data.get('术前准备', '/')}</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.340.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="手术指征"/>
                                <value xsi:type="ST">{data.get('手术指征', '/')}</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.301.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="手术方案"/>
                                <value xsi:type="ST">{data.get('手术方案', '/')}</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE09.00.119.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="注意事项"/>
                                <value xsi:type="ST">{data.get('注意事项', '/')}</value>
                            </observation>
                        </entry>
                    </section>
                </component>
                <!--术前总结章节-->
                <component>
                    <section>
                        <code displayName="讨论总结"/>
                        <text/>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.018.00" codesystem="2.16.156.10011.2.2.1" codeSystemame="卫生信息数据元目录" displayName="讨论意见"/>
                                <value xsi:type="ST">{data.get('讨论意见', '/')}</value>
                            </observation>
                        </entry>
                        <entry>
                            <observation classCode="OBS" moodCode="EVN">
                                <code code="DE06.00.018.00" codesystem="2.16.156.10011.2.2.1" codeSystemame=" 卫生信息数据元目录" displayName="讨论结论"/>
                                <value xsi:type="ST">{data.get('综合讨论意见', '/')}</value>
                            </observation>
                        </entry>
                    </section>
                </component>
            </section>
    """

    return admission_record

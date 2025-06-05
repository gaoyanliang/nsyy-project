from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
======================================= 术后首次病程记录CDA 文档构建 ====================================
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
    re = data.get('首次病程记录')
    if re:
        ct = re.get('记录时间', '/')
    else:
        ct = datetime.now().strftime('%Y%m%d%H%M%S')
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.57") \
        .replace('{文档类型}', "C0037") \
        .replace('{文档标识编码}', data.get('文档ID', '/')) \
        .replace('{文档标题}', data.get('file_title', '/')) \
        .replace('{文档生成时间}', ct)

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target3 \
        .replace('{pat_no}', data.get('pat_no', '/')) \
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
        .replace('{医疗卫生机构编号}', data.get('hospital_no', '/')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name', '/'))

    # 最终审核者签名
    admission_record = admission_record + xml_header.xml_header_legal_authenticator \
        .replace('{医师id}', '/') \
        .replace('{展示医师}', '上级医师') \
        .replace('{医师}', data.get('主任医师姓名', '/') if data.get("主任医师姓名", '/') else '/')

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
    admission_record = admission_record + f"""
            <！--手术操作章节-->
            <component>
                <section>
                    <code code = "47519-4" displayName = "HISTORY OF PROCEDURES" codeSystem = "2.16.840.1.113883.6.1"codeSystemName = "LOINC"/>
                    <text/>
                    <！--手术及操作编码 DE06.00.093.00-->
                    <entry>
                        <procedure classCode = "PROC" moodCode = "EVN">
                        <code xsi:type = "CD" code = "/" displayName = "{data.get('手术名称', '/')}" codeSystem = "2.16.156.10011.2.3.3.12" codeSystemName = "手术（操作>代码表（ICD-9-CM>"/>
                        </procedure>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                            <code code = "DE06.00.094.00" codeSystem =" 2.16.156.10011.2.2.1" codeSystemName = "卫生信息数据元日录" displayName= "手术名称"/>
                        <value xsi:type ="ST">{data.get('手术名称', '/')}</value>
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                            <code code = "DE06.00.187.00" codeSystem = "2.16.156.10011.2.2.1" codeSystemName = "卫生信息数据元目录" displayName ="手术目标部位名称"/>
                            <value xsi:type= "ST">{data.get('手术部位名称', '/')}</value>
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = " EVN">
                        <code code = "DE06.00.221.00" codesystem = "2.16.156.10011.2.2.1" codeSystemName ="卫生信息数据元目录" displayName="手术日期时间"/>
                        <value xsi:type = "TS" value = "{data.get('手术日期时间', '/')}"/>
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                        <code code = "DE06.00.073.00" codeSystem = "2.16.156.10011.2.2.1" codeSystemName ="卫生信息数据元目录" displayName="麻醉方法代码"/>
                        <value xsi:type= "CD"code ="01" codeSystem = "2.16.156.10011.2.3.1.159" codeSystemName ="麻醉方法代码表"/>
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                        <code code = "DE05.10.063.00" codeSystem = "2.16.156.10011.2.2.1" codeSystemName = "卫生信息数据元目录" displayName="手术过程"/>
                        <value xsi:type= "ST">{data.get('手术过程', '/')}</value>
                        </observation>
                    </entry>
                </section>
            </component>
            <！--术后诊断章节-->
            <component>
                <section>
                    <code code = "10218-6" displayName = " Surgical operation note postoperative Dx" codeSystem = "2.16.840.1.113883.6.1"codeSystemName = "LOINC"/>
                    <text/>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                        <code code = "DE05.01.025.00" codeSystem = "2.16.156.10011.2.2.1" codeSystemName ="卫生信息数据元目录" displayName="术后诊断名称"/>
                        <value xsi:type = "ST">{data.get('术后诊断名称', '/')}</value>
                        <entryRelationship typeCode = "COMP">
                            <observation classCode = "OBS" moodCode = "EVN">
                                <code code = "DE05.01.024.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName ="卫生信息数据元目录" displayName ="术后诊断编码"/>
                                <value xsi:type= "cp" code ="01" codeSystem = "2.16.156.10011.2.3.3.11.3"codeSystemName = "ICD-10 诊断编码表"/>
                            </observation>
                        </entryRelationship>
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode = "OBS" moodCode = "EVN">
                        <code code = " DE05.01.070.00" codeSystem = " 2.16.156.10011.2.2.1" codeSystemName ="卫生信息数据元目录" displayName="诊断依据"/>
                        <value xsi:type = "ST">{data.get('诊断依据', '/')}</value>
                        </observation>
                    </entry>
                    </section>
                    </component>
            
            <！--注意事项章节-->
            <component>
                <section>
                    <code code = "DE09.00.119.00" codeSystem = "2.16.156.10011.2.2.1" codeSystenName ="卫生信息数据元目录" displayName="注意事项章节"/>
                    <text/> 
                </section>
            </component>
    """

    return admission_record

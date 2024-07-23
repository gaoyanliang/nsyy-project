

"""
# xml Header 文档信息
"""
xml_header_file_info = """
<!-- ************************ Header ************************ -->
<realmCode code="CN" />
<typeld root="2.16.840.1.113883.1.3" extension="POCD_MT000040" />
<templateId root="2.16.156.10011.2.1.1.54" />

<!-- 文档流水号 -->
<id root="2.16.156.10011.1.1" extension="{文档标识编码}" />
<code code="C0034" codeSystem="2.16.156.10011.2.4" codeSystemName="卫生信息共享文档编码体系" />
<title>{文档标题}</title>

<!--文档机器生成时间 -->
<effectiveTime value="{文档生成时间}" />
<confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"
    codeSystemName="Confidentiality" displayName="正常访问保密级别" />
<languageCode code="zh-CN" />
<setId />
<versionNumber />
"""

"""
# xml Header 患者信息
"""
xml_header_record_target = """
<!-- 文档记录对象（患者） -->
<recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}" />
        <!-- 现住址 -->
        <addr use="H">
            <houseNumber>{addr_house_num}</houseNumber>
            <streetName>/</streetName>
            <township>/</township>
            <county>/</county>
            <city>/</city>
            <state>/</state>
        </addr>
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}" />
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <maritalStatusCode code="{pat_marriage_no}" displayName="{pat_marriage}" codeSystem="2.16.156.10011.2.3.3.5"
                codeSystemName="婚姻状况代码表(GB/T2261.2)" />
            <ethnicGroupCode code="{pat_nation_no}" displayName="{pat_nation}" codeSystem="2.16.156.10011.2.3.3.3"
                codeSystemName="民族类别代码表(GB/T3304)" />

            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
            <!-- 职业状况 -->
            <occupation>
                <occupationCode code="{pat_occupation_no}" displayName="{pat_occupation}"
                    codeSystem="2.16.156.10011.2.3.3.13"
                    codeSystemName="从业状况(个人身体)代码表(GB/T2261.4)" />
            </occupation>
        </patient>
    </patientRole>
</recordTarget>
"""

"""
# xml Header 创作者信息
"""
xml_header_author = """
<!-- 文档创作者 -->
<author typeCode="AUT" contextControlCode="OP">
    <time xsi:type="TS" value="{文档创作时间}" />
    <assignedAuthor classCode="ASSIGNED">
        <id root="2.16.156.10011.1.7" extension="{文档创作者id}" />
        <assignedPerson>
            <name>{文档创作者}</name>
        </assignedPerson>
    </assignedAuthor>
</author>
"""

"""
# xml Header 病史陈述者
"""
xml_header_informant = """
<!-- 病史陈述者 -->
<informant>
    <assignedEntity>
        <id root="2.16.156.10011.1.3" extension="{presenter_id_card}" />
        <!-- 陈述者与患者的关系代码 -->
        <code code="{presenter_relation_no}" displayName="{presenter_relation}" codeSystem="2.16.156.10011.2.3.3.8"
            codeSystemName="家庭关系代码表(GB/T 4761)" />
        <assignedPerson>
            <name>{presenter_name}</name>
        </assignedPerson>
    </assignedEntity>
</informant>
"""

"""
# xml Header 保管机构
"""
xml_header_custodian = """
<!-- 保管机构 -->
<custodian typeCode="CST">
    <assignedCustodian classCode="ASSIGNED">
        <representedCustodianOrganization classCode="ORG" determinerCode="INSTANCE">
            <id root="2.16.156.10011.1.5" extension="{医疗卫生机构编号}" />
            <name>{医疗卫生机构名称}</name>
        </representedCustodianOrganization>
    </assignedCustodian>
</custodian>
"""

"""
# xml Header 最终审核者签名
"""
xml_header_legal_authenticator = """
<!-- 最终审核者签名 -->
<legalAuthenticator>
    <time />
    <signatureCode />
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{主任医师id}" />
        <code displayName="主任医师" />
        <assignedPerson>
            <name>{主任医师}</name>
        </assignedPerson>
    </assignedEntity>
</legalAuthenticator>
"""


"""
# xml Header 医师签名
"""
xml_header_authenticator = """
<!-- 接诊医师签名/住院医师签名/主治医师签名 -->
<authenticator>
    <time />
    <signatureCode />
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{医师id}" />
        <code displayName="{显示医师名字}" />
        <assignedPerson>
            <name>{医师名字}</name>
        </assignedPerson>
    </assignedEntity>
</authenticator>
"""

"""
# xml Header 关联文档信息
"""
xml_header_related_document = """
<relatedDocument typeCode="RPLC">
    <parentDocument>
        <id />
        <setId />
        <versionNumber />
    </parentDocument>
</relatedDocument>
"""


"""
# xml Header 病床号、病房、病区、科室和医院的关联
"""
xml_header_encompassing_encounter = """
<!-- 病床号、病房、病区、科室和医院的关联 -->
<componentOf>
    <encompassingEncounter>
        <!-- 入院日期时间 DE06.00.092.00 -->
        <effectiveTime value="{入院时间}" />
        <location>
            <healthCareFacility>
                <serviceProviderOrganization>
                    <asOrganizationPartOf classCode="PART">
                        <!-- DE01.00.026.00 病床号 -->
                        <wholeOrganization classCode="ORG" determinerCode="INSTANCE">
                            <id root="2.16.156.10011.1.22" extension="{pat_bed_no}" />
                            <name>{pat_bed}</name>
                            <!-- DE01.00.019.00 病房号 -->
                            <asOrganizationPartOf classCode="PART">
                                <wholeOrganization classCode="ORG" determinerCode="INSTANCE">
                                    <id root="2.16.156.10011.1.21" extension="{pat_room_no}" />
                                    <name>{pat_room}</name>
                                    <!-- DE08.10.026.00   科室名称 -->
                                    <asOrganizationPartOf classCode="PART">
                                        <wholeOrganization classCode="ORG"
                                            determinerCode="INSTANCE">
                                            <id root="2.16.156.10011.1.26" extension="{pat_dept_no}" />
                                            <name>{pat_dept}</name>
                                            <!-- DE08.10.054.00 病区名称 -->
                                            <asOrganizationPartOf classCode="PART">
                                                <wholeOrganization classCode="ORG"
                                                    determinerCode="INSTANCE">
                                                    <id root="2.16.156.10011.1.27"
                                                        extension="{pat_ward_no}" />
                                                    <name>{pat_ward}</name>
                                                    <!-- XXX医院 -->
                                                    <asOrganizationPartOf classCode="PART">
                                                        <wholeOrganization classCode="ORG"
                                                            determinerCode="MINSTANCE">
                                                            <id root="2.16.156.10011.1.5"
                                                                extension="{医院编码}" />
                                                            <name>{医院}</name>
                                                        </wholeOrganization>
                                                    </asOrganizationPartOf>
                                                </wholeOrganization>
                                            </asOrganizationPartOf>
                                        </wholeOrganization>
                                    </asOrganizationPartOf>
                                </wholeOrganization>
                            </asOrganizationPartOf>
                        </wholeOrganization>
                    </asOrganizationPartOf>
                </serviceProviderOrganization>
            </healthCareFacility>
        </location>
    </encompassingEncounter>
</componentOf>
"""
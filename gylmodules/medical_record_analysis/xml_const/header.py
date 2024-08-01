

"""
# xml Header 文档信息
"""
xml_header_file_info = """
<!-- ************************ Header ************************ -->
<realmCode code="CN" />
<typeld root="2.16.840.1.113883.1.3" extension="POCD_MT000040" />
<templateId root="{文档模版编号}" />

<!-- 文档流水号 -->
<id root="2.16.156.10011.1.1" extension="{文档标识编码}" />
<code code="{文档类型}" codeSystem="2.16.156.10011.2.4" codeSystemName="卫生信息共享文档编码体系" />
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
# xml Header 患者信息 （入院记录）
"""
xml_header_record_target1 = """
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
# xml Header 患者信息 （出院记录）
"""
xml_header_record_target2 = """
<!-- 文档记录对象（患者） -->
<recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}" />
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}" />
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
        </patient>
    </patientRole>
</recordTarget>
"""

xml_header_record_target3 = """
<!-- 文档记录对象（患者） -->
<recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}" />
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}" />
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <!--1 数据集里是年龄（年）、年龄（月） -->
            <birthTime value="{pat_birth_time}"/>
            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
        </patient>
    </patientRole>
</recordTarget>
"""


xml_header_record_target4 = """
<!-- 文档记录对象（患者） -->
<recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!--健康卡号-->
        <id root="2.16.156.10011.1.19" extension="{health_card}"/>
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}"/>
        <!--病案号标识-->
        <id root="2.16.156.10011.1.13" extension="{bing_an}"/>
        <!-- 现住址 -->
        <addr use="H">
            <houseNumber>{addr_house_num}</houseNumber>
            <streetName>/</streetName>
            <township>/</township>
            <county>/</county>
            <city>/</city>
            <state>/</state>
            <postalCode>{postal_code}</postalCode>
        </addr>
        <telecom value="{电话}"/>
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}"/>
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <maritalStatusCode code="{pat_marriage_no}" displayName="{pat_marriage}" codeSystem="2.16.156.10011.2.3.3.5"
                codeSystemName="婚姻状况代码表(GB/T2261.2)" />
            <ethnicGroupCode code="{pat_nation_no}" displayName="{pat_nation}" codeSystem="2.16.156.10011.2.3.3.3"
                codeSystemName="民族类别代码表(GB/T3304)" />
            <!--出生地-->
            <birthplace>
                <place classCode="PLC" determinerCode="INSTANCE">
                    <addr>
                        <county>{出生地}</county>
                        <city>/</city>
                        <state>/</state>
                        <postalCode>{出生地邮编}</postalCode>
                    </addr>
                </place>
            </birthplace>
            <!--国籍-->
            <nationality code="{国籍编码}" codeSystem="2.16.156.10011.2.3.3.1" codeSystemName
                    ="世界各国和地区名称代码(GB/T 2659)" displayName="{国籍}"/>
            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
            <!-- 工作单位 -->
            <employerOrganization>
                <name>{工作单位名称}</name>
                <telecom value="{工作单位电话}"></telecom>
                <!--工作地址 -->
                <addr use="WP">
                    <houseNumber>{工作地址}</houseNumber>
                    <streetName>/</streetName>
                    <township>/</township>
                    <county>/</county>
                    <city>/</city>
                    <state>/</state>
                    <postalCode>{工作邮编}</postalCode>
                </addr>
            </employerOrganization>
            <!--户口信息-->
            <household>
                <place classCode="PLC" determinerCode="INSTANCE">
                    <addr>
                        <houseNumber>{户口地址}</houseNumber>
                        <streetName>/</streetName>
                        <township>/</township>
                        <county>/</county>
                        <city>/</city>
                        <state>/</state>
                        <postalCode>{户口邮编}</postalCode>
                    </addr>
                </place>
            </household>
            <!--籍贯信息 -->
            <nativePlace>
                <place classCode="PLC" determinerCode="INSTANCE">
                    <addr>
                        <city>{籍贯}</city>
                        <state>/</state>
                    </addr>
                </place>
            </nativePlace>
            <!--职业状况-->
            <occupation>
                <occupationCode code="{职业编码}" codeSystem="2.16.156.10011.2.3.3.13" codeSystemName=" 从业状况(个人身体)代码表(GB/T 2261.4)" displayhame="{职业}"/>
            </occupation>
        </patient>
        <!--提供患者服务机构-->
        <providerOrganization classCode="ORG" determinerCode="INSTANCE">
            <!--机构标识号-->
            <id root="2.16.156.10011.1.5" extension="{医疗机构编号}"/>
            <!--住院机构名称-->
            <name>{医疗机构名称}</name>
        </providerOrganization>
    </patientRole>
</recordTarget>
"""


xml_header_record_target5 = """
    <!-- 文档记录对象（患者）-->
    <recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}" />
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}" />
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <!--1 数据集里是年龄（年）、年龄（月） -->
            <birthTime value="{pat_birth_time}"/>
            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
            <!--DE06.00.218.00讨论日期时间 DE06.00.274.00讨论地点-->
            <providerOrganization classCode="ORG" determinerCode="INSTANCE">
                <asOrganizationPartOf classCode="PART">
                    <!--讨论时间-->
                    <effectiveTime value="{讨论时间}"></effectiveTime>
                    <wholeOrganization>
                        <addr>{讨论地点}</addr>
                    </wholeOrganization>
                </asOrganizationPartOf>
            </providerOrganization>
        </patientRole>
    </recordTarget>
"""


xml_header_record_target6 = """
<!-- 文档记录对象（患者） -->
<recordTarget typeCode="RCT" contextControlCode="OP">
    <patientRole classCode="PAT">
        <!-- 住院号标识 具体的编号放入 extension -->
        <id root="2.16.156.10011.1.12" extension="{pat_no}" />
        <!-- 电子申请单编号标识 -->
        <id root="2.16.156.10011.1.24" extension="{电子申请单编号}"/>
        <patient classCode="PSN" determinerCode="INSTANCE">
            <!-- 患者身份证号 -->
            <id root="2.16.156.10011.1.3" extension="{pat_id_card}" />
            <name>{pat_name}</name>
            <administrativeGenderCode code="{pat_sex_no}" displayName="{pat_sex}"
                codeSystem="2.16.156.10011.2.3.3.4" codeSystemName="生理性别代码表(GB/T2261.1)" />
            <!--1 数据集里是年龄（年）、年龄（月） -->
            <birthTime value="{pat_birth_time}"/>
            <!-- 年龄 -->
            <age unit="岁" value="{pat_age}"></age>
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

xml_header_author1 = """
<!-- 文档创作者 -->
<author typeCode="AUT" contextControlCode="OP">
    <time/>
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
        <id root="2.16.156.10011.1.4" extension="{医师id}" />
        <code displayName="{展示医师}" />
        <assignedPerson>
            <name>{医师}</name>
        </assignedPerson>
    </assignedEntity>
</legalAuthenticator>
"""


"""
# xml Header 医师签名（入院记录）
"""
xml_header_authenticator1 = """
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
# xml Header 医师签名（出院记录）
"""
xml_header_authenticator2 = """
<!-- 接诊医师签名/住院医师签名/主治医师签名 -->
<authenticator>
    <time value="{签名时间}" />
    <signatureCode />
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{医师id}" />
        <code displayName="{显示医师名字}" />
        <assignedPerson classCode="PSN" determinerCode="INSTANCE">
            <name>{医师名字}</name>
        </assignedPerson>
    </assignedEntity>
</authenticator>
"""


"""
# xml Header 医师签名（病案首页）
"""
xml_header_authenticator3 = """
<!-- 接诊医师签名/住院医师签名/主治医师签名 -->
<authenticator>
    <time/>
    <signatureCode/>
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{医师id}" />
        <code displayName="{显示医师名字}" />
        <assignedPerson classCode="PSN" determinerCode="INSTANCE">
            <name>{医师名字}</name>
        </assignedPerson>
    </assignedEntity>
</authenticator>
"""


"""
# xml Header 医师签名（日常病程记录）
"""
xml_header_authenticator4 = """
<authenticator>
    <time value="{签名时间}"/>
    <signatureCode/>
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{医师id}"/>
        <code displayName="医师签名"></code>
        <assignedPerson classCode="PSN" determinerCode="INSTANCE">
            <name>{医师名字}</name>
            <protessionalTecmnicalPosition>
                <professionaltechnicalpositionCode code="{职称编码}" codeSystem="2.16.156.10011.2.3.1.209" codeSystemName="专业技术职务类别代码表"
                                                   displayName="{医师职称}"></professionaltechnicalpositionCode>
            </protessionalTecmnicalPosition>
        </assignedPerson>
    </assignedEntity>
</authenticator>
"""

"""
# xml Header  会诊医师相关
"""
xml_header_authenticator5 = """
<authenticator>
    <time xsi:type="TS" value="{签名时间}"/>
    <signatureCode/>
    <assignedEntity>
        <id root="2.16.156.10011.1.4" extension="{医师id}"/>
        <code displayName="会诊医师"/>
        <assignedPerson classCode="PSN" determinerCode=" INSTANCE">
            <name>{医师名字}</name>
        </assignedPerson>
        <representedOrqanization>
            <name>{会诊医师所在医疗机构名称}</name>
        </representedOrqanization>
    </assignedEntity>
</authenticator>
"""


xml_header_authenticator6 = """
<authenticator>
    <time/>
    <signatureCode/>
    <assignedEntity>
        <id/>
        <code displayName="{display_name}"/>
        <representedOrganization>
            <asOrganizationPartOf>
                <wholeOrganization>
                    <id root="2.16.156.10011.1.26" extension="{申请会诊科室}"/>
                    <name>{申请会诊科室}</name>
                    <asOrganizationPartOf>
                        <wholeOrganization>
                            <id root="2.16.156.10011.1.5" extension="{会诊申请医疗机构名称}"/>
                            <name>{会诊申请医疗机构名称}</name>
                        </wholeOrganization>
                    </asOrganizationPartOf>
                </wholeOrganization>
            </asOrganizationPartOf>
        </representedOrganization>
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


"""
# xml Header 病床号、病房、病区、科室和医院的关联 (病案首页)
"""
xml_header_encompassing_encounter1 = """
<!-- 文档中医疗卫生时间的就诊场景,即入院场景记录-->
<componentOf typeCode="COMP">
    <!--就诊-->
    <encompassingEncounter classCode="ENC" moodCode="EVN">
        <!--入院途径-->
        <code code="{入院途径编码}" displayName="{入院途径名称}" codeSystem="2.16.156.10011.2.3.1.270" codeSystemame="入院途径代码表"/>
        <!--就诊时间-->
        <effectiveTime>
            <!--入院日期-->
            <low value="{入院日期}"/>
            <!--出院日期-->
            <high value="{出院日期}"/>
        </effectiveTime>
        <location typeCode="LOC">
            <healthCareFacility classCode="SDLOC">
                <!-- 机构角色-->
                <serviceProvider0rganization classCode="ORG" determinerCode=" INSTANCE">
                    <!--入院病房-->
                    <asOrganizationPartOf classCode="PART">
                        <whole0rganization classCode="ORG" determinerCode="INSTANCE">
                            <id root="2.16.156.10011.1.21" extension="{病房}" />
                            <name>{病房}病房</name>
                            <!--入院科室-->
                            <asOrganizationPartOf classCode="PART">
                                <whole0rganization classCode="ORG"
                                    determinerCode=" INSTANCE">
                                    <id root="2.16.156.10011.1.26" extension="{科室id}" />
                                    <name>{入院科别}</name>
                                </whole0rganization>
                            </asOrganizationPartOf>
                        </whole0rganization>
                    </asOrganizationPartOf>
                </serviceProvider0rganization>
            </healthCareFacility>
        </location>
    </encompassingEncounter>
</componentOf>
"""

"""
# xml Header 病床号、病房、病区、科室和医院的关联
"""
xml_header_encompassing_encounter2 = """
<!-- 病床号、病房、病区、科室和医院的关联 -->
<componentOf>
    <encompassingEncounter>
        <effectiveTime>
            <!-- 入院日期时间  -->
            <low value="{入院日期}"/>
            <!-- 出院日期时间-->
            <high value="{出院日期}"/>
        </effectiveTime>
    </encompassingEncounter>
</componentOf>
"""


"""
# xml Header 其他参与者(联系人) (病案首页)
"""
xml_header_participant = """
<!-- 其他参与者(联系人)@typeCode:NOT(ugent notification contact),固定值,表示不同的参与者 -->
<participant typeCode=" NOT">
    <!--联系人@classCode:CON,固定值,表示角色是联系人 -->
    <associatedEntity classCode="ECON">
        <!--联系人类别,表示与患者之间的关系-->
        <code code="{联系人与患者关系}" codeSystem="2.16.156.10011.2.3.3.8" codeSystemName="家庭关系代码表"/>
        <!--联系人地址-->
        <addr use="H">
            <houseNumber>{联系人地址}</houseNumber>
            <streetName>/</streetName>
            <township>/</township>
            <county>/</county>
            <city>/</city>
            <state>/</state>
            <postalCode>{联系人邮编}</postalCode>
        </addr>
        〈!--电话号码-->
        <telecom use="H" value="tel:{联系人电话}"/>
        <!--联系人-->
        <associatedPerson classCode="PSN" determinerCode="INSTANCE">
            <!--姓名-->
            <name>{联系人姓名}</name>
        </associatedPerson>
    </associatedEntity>
</participant>
"""


"""
参加人员讨论名单
"""
xml_header_associated_person = """
    <!--参加人员讨论名单-->
    <parentDocument typeCode="{type_code}">
        <associatedEntity classCode="{class_code}">
            <associatedPerson>
                {name1}
                {name2}
                {name3}
            </associatedPerson>
        </associatedEntity>
"""


"""
讨论日期和地点
"""
xml_header_associated_time = """
    <!--讨论的日期时间-->
    <componentOf>
        <encompassingEncounter>
            <code displayName="讨论日期时间"></code>
            <effectiveTime xsi:type="IVL_TS" value="{讨论时间}"/>
            <location>
                <healthCareFacility>
                    <serviceProviderOrganization classCode="ORG" determinerCode="INSTANCE">
                        <addr>{讨论地点}</addr>
                    </serviceProviderOrganization>
                </healthCareFacility>
            </location>
        </encompassingEncounter>
    </componentOf>
"""

"""
小结日期时间
"""

xml_header_stage_time = """
    <!-- 小结日期时间 -->
    <documentationOf>
        <serviceEvent>
            <code/>
            <effectiveTime value = "{小结日期}" />
        </serviceEvent>
    </documentationOf>
"""
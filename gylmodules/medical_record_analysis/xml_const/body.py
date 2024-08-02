

body_section_code = """
<code code="{section_code}" displayName="{section_name}"
            codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
"""

body_observation_code1 = """
<code code="{obs_code}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{obs_display_name}" />
"""

body_observation_code2 = """
<code code="{obs_code}" codeSystem="2.16.156.10011.2.2.1" codesystemName=" 卫生信息数据元目录" displayName="{obs_display_name}">
    <qualifier>
        <name displayName="{obs_name}">
        </name>
    </qualifier>
</code>
"""


body_section_entry = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        <code code="{entry_code}" codeSystem="2.16.156.10011.2.2.1"
            codeSystemName="卫生信息数据元目录" displayName="{entry_name}" />
        {entry_body}
    </observation>
</entry>
"""

body_section_entry2 = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        <code code="{entry_code}" codeSystem="2.16.156.10011.2.2.1"
            codeSystemName="卫生信息数据元目录" displayName="{entry_name}" />
        <effectiveTime value="{time}"/>
        {entry_body}
    </observation>
</entry>
"""

body_section_entry3 = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        {code}
        {entry_body}
    </observation>
</entry>
"""

body_section_entry4 = """
<entry>
<!-- 手术记录 -->
<procedure classCode="PROC" moodCode="EVN">
    <code code="1" codeSystem="2.16.156.10011.2.3.3.12"
        codeSystemName="手术(操作)代码表(ICD-9-CM)" />
    <statusCode />

    <!-- 手术操作目标部位名称 -->
    <targetSiteCode code = "{手术部位}" codesystem = "2.16.156.10011.2.3.1.266" codeSystemName ="操作部位代码表"></targetSiteCode>

    {entry_ship1}
    {entry_ship2}
    {entry_ship3}
    {entry_ship4}
</procedure>
</entry>
"""

body_section_entry5 = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        <code code="DE04.30.020.00" codeSystem="2.16.156.10011.2.3.3.11" codeSystemName=" 卫生信息数据元目录" displayName="检查/检验项目名称"/>
        {value}
        {entry_ship1}
        {entry_ship2}
        {entry_ship3}        
    </observation>
</entry>
"""




body_section_entry_relation_ship = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        {code}
        {value}
        <!-- {entry_ship_name} -->
        <entryRelationship typeCode="COMP">
            <observation ulassCode="OBS" moodCode="EVN">
                {obs_code}
                {entry_ship_body}
            </observation>
        </entryRelationship>
    </observation>
</entry>
"""

body_section_entry_relation_ship1 = """
<entryRelationship typeCode=" COMP">
    <observation classCode="OBS" moodCode="EVN">
        <code code="{code}" codeSystem="2.16.156.10011.2.2.1"
            codeSystemName="卫生信息数据元目录" displayName="{display_name}" />
        {value}
    </observation>
</entryRelationship>
"""


value_st = """
<value xsi:type="ST">{value}</value>
"""

value_bl = """
<value xsi:type="BL" value="{value}" />
"""

value_pq = """
<value xsi:type="PQ" value="{value}" unit="{unit}" />
"""

value_ts = """
<value xsi:type="TS" value="{value}" />
"""

value_cd = """
<value xsi:type="CD" code="{code}" codeSystem="2.16.156.10011.2.3.3.11.3" codeSystemName="ICD-10 诊断编码表"
                                           displayName="{display_name}"/>
"""

value_cd2 = """
<value xsi:type="CD" code="{code}" codeSystem="2.16.156.10011.2.3.3.12" codeSystemName="ICD-9-CM-3"/>
"""




# 主诉 / 现病史 / 预防接种史 / 输血史 / 个人史 / 月经史 / 家族史

body_component = """
<!-- {entry_observation_name}章节 -->
<component>
    <section>
        {code}
        {text}
        <!-- {entry_observation_name}条目 -->
        {entry}
    </section>
</component>
"""

# 既往史

body_history_of_past_illness = """
<!-- 既往史章节 -->
<component>
    <section>
        {code}
        {text}
        
        <!-- 一般健康状况标志 -->
        {history_of_illness}

        {history_of_infectious_diseases}
        
        <!-- 婚育史条目 -->
        {marriage_and_childbearing_history}
        
        <!-- 过敏史条目 -->
        {allergy_history}
        
        <!-- 手术史条目 -->
        {surgical_history}

    </section>
</component>
"""

# 生命体征

body_vital_signs = """
<!-- 生命体征章节 -->
<component>
    <section>
        {code}
        {text}

        <!-- 体格检査•体温 -->
        {body_temperature}
        
        <!-- 体格检査•脉率<次/min> -->
        {pulse_rate}

        <!-- 体格检査•呼吸频率脉率<次/min> -->
        {respiratory_rate}

        <!-- 体格检査•血压（mmHg） -->
        <entry>
            <organizer classCode="BATTERY" moodCode="EVN">
                <code dispiayName="血压" />
                <statusCode />
                <component>
                    <observation classCode="OBS" moodCode="EVN">
                        <code code="DE04.10.174.00" codeSystem="2.16.156.10011.2.2.1"
                            codeSystemName="卫生信息数据元目录" displayName="收缩压" />
                        <value xsi:type="PQ" value="{systolic}" unit="mmHg" />
                    </observation>
                </component>
                <component>
                    <observation classCode="OBS" moodCode="EVN">
                        <code code="DE04.10.176.00" codeSystem="2.16.156.10011.2.2.1"
                            codeSystemName="卫生信息数据元目录" displayName="舒张压" />
                        <value xsi:type="PQ" value="{diastolic}" unit="mmHg" />
                    </observation>
                </component>
            </organizer>
        </entry>

        <!-- 体格检査•身高（cm） -->
        {height}

        <!-- 体格检査•体重（kg） -->
        {weight}
    </section>
</component>
"""

# 体格检查

body_physical_examination = """
<!-- 体格检査章节 -->
<component>
    <section>
        {code}
        {text}
        <!-- 体格检査-一般状况检査结果 -->
        {一般状况检査}

        <!-- 体格检査-皮肤和粘膜检査结果 -->
        {皮肤和粘膜检査}

        <!-- 体格检査-全身浅表淋巴结检查结果 -->
        {全身浅表淋巴结检查}

        <!-- 体格检査-头部及其器官检查结果 -->
        {头部及其器官检查}

        <!-- 体格检査-颈部检査结果 -->
        {颈部检査}

        <!-- 体格检査-胸部检査结果 -->
        {胸部检査}

        <!-- 体格检査-腹部检査结果 -->
        {腹部检査}

        <!-- 体格检査-肛门指诊检查结果 -->
        {肛门指诊检查}

        <!-- 体格检査-外生殖器检査结果 -->
        {外生殖器检査}

        <!-- 体格检査-脊柱检査结果 -->
        {脊柱检査}

        <!-- 体格检査-四肢检査结果 -->
        {四肢检査}

        <!-- 体格检査-神经系统检査结果 -->
        {神经系统检査}

        <!-- 专科情况 -->
        {专科情况}
    </section>
</component>

"""

# 主要健康问题

# 中医诊断
body_health_entry_chinese = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        <code code="{code1}" codeSystem="2.16.156.10011.2.2.1"
            codeSystemName="卫生信息数据元目录" displayName="{display_name1}" />
        <effectiveTime value="{time}" />
        <value xsi:type="ST">{value1}</value>
        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code2}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name2}" />
                <value xsi:type="CD" code="{code3}" displayName="{display_name3}"
                    codeSystem="2.16.156.10011.2.3.3.14"
                    codeSystemName="中医病症分类与代码表(GB/T15657)" />
            </observation>
        </entryRelationship>
        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code4}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name4}" />
                <value xsi:type="ST">{value2}</value>
            </observation>
        </entryRelationship>

        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code5}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name5}" />
                <value xsi:type="CD" code="{code6}" displayName="{display_name6}"
                    codeSystem="2.16.156.10011.2.3.3.14"
                    codeSystemName="中医病症分类与代码表(GB/T 15657)" />
            </observation>
        </entryRelationship>
        <!-- 入院诊断顺位 -->
        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code7}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name7}" />
                <value xsi:type="INT" value="{value3}" />
            </observation>
        </entryRelationship>
    </observation>
</entry>

"""

# 西医诊断
body_health_entry_western = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        <code code="{code1}" codeSystem="2.16.156.10011.2.2.1"
            codeSystemName="卫生信息数据元目录" displayName="{display_name1}" />
        <!-- {display_name1} -->
        <effectiveTime value="{time}" />
        <value xsi:type="ST">{value1}</value>
        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code2}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name2}" />
                <value xsi:type="CD" code="{code3}" displayName="{display_name3}"
                    codeSystem="2.16.156.10011.2.3.3.11.3"
                    codeSystemName="诊断代码表(ICD-10)" />
            </observation>
        </entryRelationship>
        <!-- {display_name4} -->
        <entryRelationship typeCode="COMP">
            <observation classCode="OBS" moodCode="EVN">
                <code code="{code4}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{display_name4}" />
                <value xsi:type="INT" value="{value2}" />
            </observation>
        </entryRelationship>
    </observation>
</entry>
"""

# 主要健康问题
body_main_health_problem = """
<!-- ************************ 主要健康问题章节 ************************ -->

<!-- 陈述可靠性/初步诊断（中西）/中医四诊/修正诊断（中西）/确定诊断（中西）/补充诊断（西） -->
<component>
    <section>
        {code}
        {text}
        
        <!-- 陈述内容可靠标志 -->
        {陈述内容可靠标志}

        <!-- 初步诊断•西医条目 -->
        {西医初步诊断}

        <!-- 中医"四诊"观察结果 -->
        {中医四诊}

        <!-- 初步诊断•中医条目 -->
        {中医初步诊断}

        <!-- 修正诊断•西医条目 -->
        {西医修正诊断}

        <!-- 修正诊断•中医条目 -->
        {中医修正诊断}

        <!-- 确定诊断•西医条目 -->
        {西医确定诊断}

        <!-- 确定诊断•中医条目 -->
        {中医确定诊断}

        <!-- 补充诊断-西医条目 -->
        {西医补充诊断}
        
    </section>
</component>
"""

# 主要健康问题
body_main_health_problem2 = """
<!-- ************************ 主要健康问题章节 ************************ -->

<!-- 陈述可靠性/症状名称/中医四诊 -->
<component>
    <section>
        {code}
        {text}

        <!-- 陈述内容可靠标志 -->
        {陈述内容可靠标志}

        <!-- 症状名称 -->
        {症状名称}

        <!-- 中医"四诊"观察结果 -->
        {中医四诊}
        
    </section>
</component>
"""

# ================================= 出院记录 ============================

body_discharge_entry = """
<!-- {entry_observation_name}章节 -->
<component>
    <section>
        {code}
        {text}
        <!-- {entry_observation_name}条目 -->
        {entry1}
        {entry2}
        {entry3}
        {entry4}
        {entry5}
        {entry6}
        {entry7}
        {entry8}
        {entry9}
    </section>
</component>
"""

body_discharge_entry2 = """
<!-- {entry_observation_name}章节 -->
<component>
    <section>
        {code}
        {text}
        <!-- {entry_observation_name}条目 -->
        {entry1}
        <!--入/出院诊断-中医条目-->
        <entry>
            <observation classCode="OBS" moodCode="EVN">
                <code code="DE05.10.172.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录" displayName="入/出院诊断-中医病名名称"/>
                <value xsi:type="ST">{中医诊断}</value>
                <entryRelationship typeCode=" COMP">
                    <observation classCode="OBS" moodCode="EVN">
                        <!--入/出院诊断-中医诊断编码-代码-->
                        <code code="DE05.10.130.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                              displayName="入/出院诊断-中医病名代码"/>
                        <value xsi:type="CD" code="{中医诊断编码}" displayName="{中医诊断}" codeSystem="2.16.156.10011.2.3.3.14"
                               codeSystemName="中医病证分类与代码表(GB/T 15657)"/>
                    </observation>
                </entryRelationship>
                <entryRelationship typeCode="COMP">
                    <observation classCode="OBS" moodCode="EVN">
                        <!--入/出院诊断-中医证候编码-名称-->
                        <code code="DE05.10.172.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                              displayName="入/出院诊断-中医证候名称"/>
                        <value xsi:type="ST">{中医证候}</value>
                    </observation>
                </entryRelationship>
                <entryRelationship typeCode=" COMP">
                    <observation classCode="OBS" moodCode="EVN">
                        <!--入/出院诊断-中医证候编码-代码-->
                        <code code="DE05.10.130.00" codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                              displayName="入/出院诊断-中医证候代码"/>
                        <value xsi:type="CD" code="{中医证候编码}" displayName="{中医证候}" codesystem="2.16.156.10011.2.3.3.14"
                               codesystemName="中医病证分类与代码表（GB/T 15657）"/>
                    </observation>
                </entryRelationship>
            </observation>
        </entry>
    </section>
</component>
"""


"""
住院病案首页 body
"""
body_inpatient_homepage_body = """
            <!-- 生命体征章节-->
            <component>
                <section>
                    <code code="8716-3" displayName="VITAL SIGNS" codeSystem="2.16.840.1.113883.6.1"
                        codeSystemName="LOINC" />
                    <text />
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE04.10.019.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName=" 卫生信息数据元目录" displayName="入院体重">
                                <qualifier>
                                    <name displayName="新生儿入院体重"></name>
                                </qualifier>
                            </code>
                            <value xsi:type="PQ" value="{新生儿入院体重}" unit="g" />
                        </observation>
                    </entry>
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE04.10.019.00" codesystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="出生体重">
                                <qualifier>
                                    <name displayName="新生儿出生体重"></name>
                                </qualifier>
                            </code>
                            <value xsi:type="PQ" value="{新生儿出生体重}" unit="g" />
                        </observation>
                    </entry>
                </section>
            </component>
            <!--诊断章节-->
            <component>
                <section>
                    <code code="29548-5" displayName="Diagnosis" codeSystem="2.16.840.1.113883.6.1"
                        codeSystemName="LOINC" />
                    <text />
                    <!--门(急)诊诊断-->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.025.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSvstemName="卫生信息数据元目录"
                                        displayName="门(急)诊诊断名称">
                                        <qualifier>
                                            <name displayame="门(急)诊诊断"></name>
                                        </qualifier>
                                    </code>
                                    <value xsi:type="ST">{门急诊诊断}
                                    </value>
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.024.00"
                                        codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                                        displayName="门(急)诊诊断疾病编码">
                                        <qualifier>
                                            <name displayName="门(急)诊诊断"></name>
                                        </qualifier>
                                    </code>
                                    <value xsi:type="CD" code="{门急诊诊断编码}"
                                        codeSystem="2.16.156.10011.2.3.3.11.5"
                                        codesystemName="疾病代码表(ICD-10)" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!--病理诊断-->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <!--病理号标识-->
                                    <id root="2.16.156.10011.1.8" extension="PA345677"></id>
                                    <code code="DE05.01.025.00"
                                        CoaeCoeDE05.01.025.00codesystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="病理诊断-疾病名称">
                                        <qualifier>
                                            <name displayName="病理诊断"></name>
                                        </qualifier>
                                    </code>
                                    <value xsi:type="ST">{疾病名称描述}</value>
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.024.00" codesystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="病理诊断-疾病编码">
                                        <gualifier>
                                            <name displayName="病理诊断"></name>
                                        </gualifier>
                                    </code>
                                    <value xsi:type="CD" code="{疾病名称编码}"
                                        codeSystem="2.16.156.10011.2.3.3.11.5"
                                        codeSystemName="疾病代码表(ICD-10)" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                </section>
            </component>
            <!--主要健康问题章节-->
            <component>
                <section>
                    <code code="11450-4" displayName="PROBLEM LIST"
                        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
                    <text />
                    <entry typeCode="COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE05.10.119.00"
                                codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                                displayName="住院者疾病状态代码" />
                            <value xsi:type="CD" code="{住院者疾病状态代码}" codeSystem="2.16.156.10011.2.3.1.100"
                                codeSystemName="住院者疾病状态代码表" />
                        </observation>
                    </entry>
                    <!--住院患者损伤和中毒外部原因-->
                    <entry typeCode="COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE05.10.152.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName=" 卫生信息数据元目录" displayName="损伤中毒的外部原因" />
                            <value xsi:type="ST">{损伤外部原因描述}</value>
                            <entryRelationship typeCode="REFR" negationInd="false">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.078.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="损伤中毒的外部原因-疾病编码" />
                                    <value xsi:type="CD" code="{损伤中毒的外部原因-疾病编码}"
                                        codeSystem="2.16.156.10011.2.3.3.11.5"
                                        codesystemName="疾病代码表(ICD-10)" />
                                </observation>
                            </entryRelationship>
                        </observation>
                    </entry>
                    <!--颅脑损伤患者入院前昏迷时间-->
                    <entry typeCode="COMP">
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <code displaywame="颅脑损伤患者入院前昏迷时间" />
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.01" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="颅脑损伤患者入院前昏迷时间-d" />
                                    <value xsi:type="PQ" unit="d" value="{入院前昏迷时间d}" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.02" codeSystem="2.16.156.10011.2.2.1"
                                        codesystemName="卫生信息数据元目录"
                                        displayName="颅脑损伤患者入院前昏迷时间-h" />
                                    <value xsi:type="PQ" unit="h" value="{入院前昏迷时间h}" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.03" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="颅脑颅脑损伤患者入院前昏迷时间-min" />
                                </observation>
                                <value xsi:type="PQ" unit="min" value="{入院前昏迷时间min}" />
                            </component>
                        </organizer>
                    </entry>
                    <!--颅脑损伤患者入院后昏迷时间-->
                    <entry typeCode="COMP">
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <code displaywame="颅脑损伤患者入院后昏迷时间" />
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.01"
                                        codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                                        displayName="颅脑损伤患者入院后昏迷时间-d" />
                                    <value xsi:type="PQ" unit="d" value="{入院后昏迷时间d}" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.02" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="颅脑损伤患者入院后昏迷时间-h" />
                                    <value xsi:type="PQ" unit="h" value="{入院后昏迷时间h}" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.138.03" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="颅脑损伤患者入院后昏迷时间-min" />
                                    <value xsi:type="PQ" unit="min" value="{入院后昏迷时间min}" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                </section>
            </component>
            <!--转科记录章节-->
            <component>
                <section>
                    <code code="42349-1" displayName="REASON FOR REFERRAL"
                        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
                    <text />
                    <!--转科条目-->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code />
                            <!--转科原因(数据元)-->
                            <author>
                                <time />
                                <assignedAuthor>
                                    <id />
                                    <representedOrqanization>
                                        <!-- 住院患者转科科室名称-->
                                        <name>{转科科室名称}</name>
                                    </representedOrqanization>
                                </assignedAuthor>
                            </author>
                        </observation>
                    </entry>
                </section>
            </component>
            <!--出院诊断章节-->
            <component>
                <section>
                    <code code="11535-2" displayName="HOSPITAL DISCHARGE DX"
                        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
                    <text />
                    <!--出院诊断-主要诊断条目-->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.025.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断-主要诊断名称">
                                        <qualifier>
                                            <name displayame="主要诊断名称"></name>
                                        </qualifier>
                                    </code>
                                    <!-- 确诊日期-->
                                    <effectiveTime value="{确诊日期}" />
                                    <value xsi:type="ST">{疾病名称}</value>
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <!--住院患者疾病诊断类型-代码/住院患者疾病诊断类型详细描述-->
                                    <code code="DE05.01.024.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断-主要诊断疾病编码">
                                        <qualifier>
                                            <name displayName="主要诊断疾病编码"></name>
                                        </qualifier>
                                    </code>
                                    <!--疾病诊断代码/疾病诊断名称-->
                                    <value xsi:type="CD" code="{疾病编码}"
                                        codeSystem="2.16.156.10011.2.3.3.11.3"
                                        codesystemName="诊断代码表(ICD-10)" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE09.00.104.00"
                                        codeSystem="2.16.156.10011.2.2.1" codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断—主要诊断人病情代码">
                                        <qualifier>
                                            <name displayName="主要诊断入院病情代码"></name>
                                        </qualifier>
                                    </code>
                                    <value xsi:type="CD" code="{病情代码}"
                                        codeSystem="2.16.156.10011.2.3.1.253"
                                        codeSystemName="入院病情代码表"></value>
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!--出院诊断-其他诊断条目-->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode />
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.01.025.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断-其他诊断名称">
                                        <qualifier>
                                            <name displayiame="其他诊断名称"></name>
                                        </qualifier>
                                    </code>
                                    <!--确诊日期-->
                                    <effectiveTime value="{确诊日期}" />
                                    <value xsi:type="ST">{疾病名称}</value>
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <!--住院患者疾病诊断类型-代码/住院患者疾病诊断类型详细描述-->
                                    <code code="DE05.01.024.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断-其他诊断疾病编码">
                                        <qualifier>
                                            <name displayame="其他诊断疾病编码"></name>
                                        </qualifier>
                                    </code>
                                    <!--疾病诊断代码/疾病诊断名称-->
                                    <value xsi:type="CD" code="{疾病编码}"
                                        codeSystem="2.16.156.10011.2.3.3.11.3"
                                        codesystemName="诊断代码表(ICD-10)" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE09.00.104.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录"
                                        displayName="出院诊断-其他诊断入院病情代码">
                                        <qualifier>
                                            <name displayName="其他诊断入院病情代码"></name>
                                        </qualifier>
                                    </code>
                                    <value xsi:type="CD" code="{病情代码}"
                                        codeSystem="2.16.156.10011.2.3.1.253"
                                        codeSystemName="入院病情代码表"></value>
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 离院方式 -->
                    <entry typeCode="COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE06.00.223.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="离院方式"
                            />
                            <value xsi:type="CD" code="{离院方式代码}" codeSystem="2.16.156.10011.2.3.1.265"
                                codeSystemName="离院方式代码表" />
                            <entryRelationship typeCode="00MP" negationInd="false">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE08.10.013.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="拟接受医疗机构名称" />
                                    <value xsi:type="ST">拟接受医疗机构具体名称</value>
                                </observation>
                            </entryRelationship>
                        </observation>
                    </entry>
                </section>
            </component>
            <!--过敏史章节-->
            <component>
                <section>
                    <code code="48765-2" displayName="Allergies, adverse reactions, alerts"
                        codeSystem="2.16.840.1.113883.6.1"
                        codeSystemName="LOINC" />
                    <text />
                    <entry typeCode="DRIV">
                        <act classCode="ACT" moodCode="EVN">
                            <code nullFlavor="NA" />
                            <entryRelationship typeCode="SUBJ">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE02.10.023.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" />
                                    <value xsi:type="BL" value="true"></value>
                                    <participant typeCode="CSM">
                                        <participantRole classCode="MANU">
                                            <playingEntity classCode="MMAT">
                                                <!--住院患者过敏源-->
                                                <code code="DE02.10.022.00"
                                                    codeSystem="2.16.156.10011.2.2.1"
                                                    codeSystemName="卫生信息数据元目录"
                                                    displayame="过敏药物" />
                                                <desc xsi:type="ST">{过敏药物}</desc>
                                            </playingEntity>
                                        </participantRole>
                                    </participant>
                                </observation>
                            </entryRelationship>
                        </act>
                    </entry>
                </section>
            </component>
            <!--实验室检查章节-->
            <component>
                <section>
                    <code code="30954-2" displayName="STUDIES SUMMARY"
                        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
                    <text />
                    <entry typeCode="COMP">
                        <!--血型-->
                        <organizer classCode="BATTERY" moodCode="EVN">
                            <statusCode />
                            <component typeCode="COMP">
                                <!--ABO 血型-->
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE04.50.001.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" />
                                    <value xsi:type="CD" code="{ABO血型代码}"
                                        codeSystem="2.16.156.10011.2.3.1.85"
                                        codeSystemName="ABO血型代码表" displayName="{ABO血型}" />
                                </observation>
                            </component>
                            <component typeCode=" COMP">
                                <!--Rh血型-->
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE04.50.010.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" />
                                    <value xsi:type="CD" code="{RH血型代码}"
                                        codeSystem="2.16.156.10011.2 3.1.250"
                                        codeSystemName="Rh血型代码表" displayame="{RH血型}" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                </section>
            </component>
            <!--手术操作章节-->
            <component>
                <section>
                    <code code="47519-4" displayName="HISTORY OF PROCEDURES"
                        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
                    <text />
                    <entry>
                        <!-- 1..1 手术记录 -->
                        <procedure classCode="PROC" moodCode="EVN">
                            <code code="1" codeSystem="2.16.156.10011.2.3.3.12"
                                codeSystemName="手术(操作)代码表(ICD-9-CM)" />
                            <statusCode />
                            <!--操作日期/时间-->
                            <effectiveTime value="{手术操作日期}" />
                            <!--手术者-->
                            <performer>
                                <assignedEntity>
                                    <id root="2.16.156.10011.1.4" extension="{手术者id}" />
                                    <assignedPerson>
                                        <name>{手术者}</name>
                                    </assignedPerson>
                                </assignedEntity>
                            </performer>
                            <!--第一助手-->
                            <participant typeCode="ATND">
                                <participantRole classCode="ASSIGNED">
                                    <id root="2.16.156.10011.1.4" extension="{第一助手id}" />
                                    <code displayName="第一助手" />
                                    <playingEntity classcode="PSN" determinerCode="INSTANCE">
                                        <name>{第一助手}</name>
                                    </playingEntity>
                                </participantRole>
                            </participant>
                            <!--第二助手-->
                            <participant typeCode="ATND">
                                <participantRole classCode="ASSIGNED">
                                    <id root="2.16.156.10011.1.4" extension="{第二助手id}" />
                                    <code displayName="第二助手" />
                                    <playingEntity classCode="PSN" determinerCode="INSTANCE">
                                        <name>{第二助手}</name>
                                    </playingEntity>
                                </participantRole>
                            </participant>
                            <entryRelationship typeCode=" COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE06.00.094.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="手术(操作)名称" />
                                    <value xsi:type="ST">{手术名称}</value>
                                </observation>
                            </entryRelationship>
                            <entryRelationship typeCode="COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE06.00.255.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="手术级别" />
                                    <!--手术级别-->
                                    <value xsi:type="CD" code="{手术级别}"
                                        codeSystem="2.16.156.10011.2.3.1.258"
                                        codeSystemName="手术级别代码表" />
                                </observation>
                            </entryRelationship>
                            <!--手术切口类别 -->
                            <entryRelationship typeCode=" COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE06.00.257.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName=" 手术切口类别代码" />
                                    <!--手术切口类别代码-->
                                    <value xsi:type="CD" code="{手术切口类别代码}"
                                        codeSystem="2.16.156.10011.2.3.1.256"
                                        codeSystemName="手术切口类别代码表" />
                                </observation>
                            </entryRelationship>
                            <!-- 手术切口愈合等级-->
                            <entryRelationship typeCode=" COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE05.10.147.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="手术切口愈合等级" />
                                    <!--手术切口愈合等级-->
                                    <value xsi:type="CD" code="{手术切口愈合等级}" displayName="{手术切口愈合等级名称}"
                                        codeSystem="2.16.156.10011.2.3.1.257"
                                        codeSystemName="手术切口愈合等级代码表" />
                                </observation>
                            </entryRelationship>
                            <!--0..1 麻醉信息-->
                            <entryRelationship typeCode="COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE06.00.073.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="麻醉方式代码" />
                                    <value code="1" codeSystem="2.16.156.10011.2.3.1.159"
                                        codeSystemName=" 麻醉方式代码表" xsi:type="CD"></value>
                                    <performer>
                                        <assignedEntity>
                                            <id root="2.16.156.10011.1.4" extension="{麻醉员编码}" />
                                            <assiqnedPerson>
                                                <name>{麻醉员}</name>
                                            </assiqnedPerson>
                                        </assignedEntity>
                                    </performer>
                                </observation>
                            </entryRelationship>
                        </procedure>
                    </entry>
                </section>
            </component>
            <!--住院史章节-->
            <component>
                <section>
                    <code code="11336-5" codeSystem="2.16.840.1.113883.6.1"
                        displayName=" HISTORY OF HOSPITALIZATIONS" codeSystemName="LOINC" />
                    <text />
                    <!--住院次数-->
                    <entry typeCode=" COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE02.10.090.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="住院次数" />
                            <value xsi:type="INT" value="{住院次数}" />
                        </observation>
                    </entry>
                </section>
            </component>
            <!--住院过程章节-->
            <component>
                <section>
                    <code code="8648-8" codeSystem="2.16.840.1.113883.6.1" codeSystemName=" LOINC"
                        displayName="Hospital Course" />
                    <text />
                    <!--实际住院天数-->
                    <entry typeCode="COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE06.00.310.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="实际住院天数" />
                            <value xsi:type="PQ" value="{住院天数}" unit="天" />
                        </observation>
                    </entry>
                    <entry>
                        <!--出院科室及病房-->
                        <act classCode="ACT" moodCode="EVN">
                            <code />
                            <author>
                                <time />
                                <assignedAuthor>
                                    <id />
                                    <representedOrganization>
                                        <!-- 住院患者出院病房、科室名称 -->
                                        <id root="2.16.156.10011.1.21" extension="{病房id}" />
                                        <name>{病房}</name>
                                        <asOrganizationPartOf classCode="PART">
                                            <wholeOrganization classCode="ORG"
                                                determinerCode="INSTANCE">
                                                <id root="2.16.156.10011.1.26" extension="{科室id}" />
                                                <name>{科室}</name>
                                            </wholeOrganization>
                                        </asOrganizationPartOf>
                                    </representedOrganization>
                                </assignedAuthor>
                            </author>
                        </act>
                    </entry>
                </section>
            </component>
            <!--行政管理章节-->
            <component>
                <section>
                    <code displayName="行政管理" />
                    <text />
                    <!-- 亡患者尸检标志 -->
                    <entry typeCode="COMP">
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE09.00.108.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="死亡患者尸检标志" />
                            <value xsi:type="BL" value="{死亡患者尸检标志}" />
                        </observation>
                    </entry>
                    <!--病案质量-->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE09.00.103.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="病案质量" />
                            <!--质控日期-->
                            <effectiveTime value="{质控日期}"></effectiveTime>
                            <value xsi:type="CD" code="{病案质量等级表}" codeSystem="2.16.156.10011.2.3.2.29"
                                codeSystemName="病案质量等级表”" />
                            <author>
                                <time />
                                <assignedAuthor>
                                    <id root="2.16.156.10011.1.4" extension="{质控医生id}" />
                                    <code displayName="质控医生" />
                                    <assignedPerson>
                                        <name>{质控医生}</name>
                                    </assignedPerson>
                                </assignedAuthor>
                            </author>
                            <author>
                                <time />
                                <assignedAuthor>
                                    <id root="2.16.156.10011.1.4" extension="{质控护士id}" />
                                    <code displayName="质控护士" />
                                    <assignedPerson>
                                        <name>{质控护士}</name>
                                    </assignedPerson>
                                </assignedAuthor>
                            </author>
                        </observation>
                    </entry>
                </section>
            </component>
            <!--治疗计划章节-->
            <component>
                <section>
                    <code code="18776-5" displayName="TREATMENT PLAN"
                        codeSystem="2.16.840.1.113883.6.1" codesvstemName="LOINC" />
                    <text />
                    <!-- 有否出院31d内再住院计划 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE06.00.194.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="出院31d内再住院标志" />
                            <value xsi:type="BL" value="{出院31天内再住院标志}" />
                            <entryRelationship typeCode="GEVL" negationInd="false">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="DE06.00.195.00" codeSystem="2.16.156.10011.2.2.1"
                                        codeSystemName="卫生信息数据元目录" displayName="出院 31d内再住院目的" />
                                    <value xsi:type="ST">{出院31天内再住院目的}</value>
                                </observation>
                            </entryRelationship>
                        </observation>
                    </entry>
                </section>
            </component>
            <!--治疗计划章节-->
            <component>
                <section>
                    <code code="48768-6" displayName="PAYMENT SOURCES"
                        codeSystem="2.16.840.1.113883.6.1" codesvstemName="LOINC" />
                    <text />
                    <!-- 医疗付费方式 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="DE07.00.007.00" codeSystem="2.16.156.10011.2.2.1"
                                codeSystemName="卫生信息数据元目录" displayName="医疗付费方式代码" />
                            <value xsi:type="CD" code="{医疗付费方式编码}" codeSystem="2.16.156.10011.2.3.1.269"
                                displayName="{医疗付费方式}" codeSystemName="医疗付费方式代码表" />
                        </observation>
                    </entry>
                    <!-- 住院总费用 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="HDSD00.11.142" codeSystem="2.16.156.10011.2.2.4"
                                codeSystemName="住院病案首页基本数据集" displayName="住院总费用" />
                            <value xsi:type="MO" value="{总费用}" currency="元" />
                            <entryRelationship typeCode="COMP" negationInd="false">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="HDSD00.11.1430" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="住院总费用—自付金额（元）" />
                                    <value xsi:type="MO" value="{自付金额}" currency="元" />
                                </observation>
                            </entryRelationship>
                        </observation>
                    </entry>
                    <!-- 综合医疗服务费 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.147" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="综合医疗服务费—一般医疗服务费" />
                                    <value xsi:type="MO" value="{一般医疗服务费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.148" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="综合医疗服务费—一般治疗操作费" />
                                    <value xsi:type="MO" value="{一般治疗操作费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.145" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="综合医疗服务费—护理费" />
                                    <value xsi:type="MO" value="{护理费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.146" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="综合医疗服务费—其他费用" />
                                    <value xsi:type="MO" value="{综合医疗服务费—其他费用}" currency="元" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 诊断类服务费 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.121" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="诊断—病理诊断费" />
                                    <value xsi:type="MO" value="{病理诊断费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.123" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="诊断—实验室诊断费" />
                                    <value xsi:type="MO" value="{实验室诊断费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.124" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="诊断—影像学诊断费" />
                                    <value xsi:type="MO" value="{影像学诊断费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.122" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="诊断—临床诊断项目费" />
                                    <value xsi:type="MO" value="{临床诊断项目费}" currency="元" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 治疗类服务费 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.129" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="治疗—非手术治疗项目费" />
                                    <value xsi:type="MO" value="{非手术治疗项目费}" currency="元" />
                                    <entryRelationship typeCode="COMP">
                                        <observation classCode="OBS" moodCode="EVN">
                                            <code code="HDSD00.11.130"
                                                codeSystem="2.16.156.10011.2.2.4"
                                                codeSystemName="住院病案首页基本数据集"
                                                displayName="治疗—非手术治疗项目费—临床物理治疗费" />
                                            <value xsi:type="MO" value="{临床物理治疗费}" currency="元" />
                                        </observation>
                                    </entryRelationship>
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.131" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="治疗—手术治疗费" />
                                    <value xsi:type="MO" value="{手术治疗费}" currency="元" />
                                    <entryRelationship typeCode="COMP">
                                        <observation classCode="OBS" moodCode="EVN">
                                            <code code="HDSD00.11.132"
                                                codeSystem="2.16.156.10011.2.2.4"
                                                codeSystemName="住院病案首页基本数据集"
                                                displayName="治疗—手术治疗费—麻醉费" />
                                            <value xsi:type="MO" value="{麻醉费}" currency="元" />
                                        </observation>
                                    </entryRelationship>
                                    <entryRelationship typeCode="COMP">
                                        <observation classCode="OBS" moodCode="EVN">
                                            <code code="HDSD00.11.133"
                                                codeSystem="2.16.156.10011.2.2.4"
                                                codeSystemName="住院病案首页基本数据集"
                                                displayName="治疗—手术治疗费—手术费" />
                                            <value xsi:type="MO" value="{手术费}" currency="元" />
                                        </observation>
                                    </entryRelationship>
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 康复费类服务费 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="HDSD00.11.055" codeSystem="2.16.156.10011.2.2.4"
                                codeSystemName="住院病案首页基本数据集" displayName="康复费" />
                            <value xsi:type="MO" value="{康复费}" currency="元" />
                        </observation>
                    </entry>
                    <!-- 中医治疗费 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="HDSD00.11.136" codeSystem="2.16.156.10011.2.2.4"
                                codeSystemName="住院病案首页基本数据集" displayName="中医治疗费" />
                            <value xsi:type="MO" value="{中医治疗费}" currency="元" />
                        </observation>
                    </entry>
                    <!-- 西药费 -->
                    <entry>
                        <observation classCode="OBS" moodCode="EVN">
                            <code code="HDSD00.11.098" codeSystem="2.16.156.10011.2.2.4"
                                codeSystemName="住院病案首页基本数据集" displayName="西药费" />
                            <value xsi:type="MO" value="{西药费}" currency="元" />
                            <entryRelationship typeCode="COMP">
                                <observation classCode="OBS" moodCode="EVN">
                                    <code code="HDSD00.11.099" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="西药费—抗菌药物费用" />
                                    <value xsi:type="MO" value="{抗菌药物费用}" currency="元" />
                                </observation>
                            </entryRelationship>
                        </observation>
                    </entry>
                    <!-- 中药费 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.135" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="中药费—中成药费" />
                                    <value xsi:type="MO" value="{中成药费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.134" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="中药费—中草药费" />
                                    <value xsi:type="MO" value="{中草药费}" currency="元" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 血液和血液制品类服务费 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.115" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="血费" />
                                    <value xsi:type="MO" value="{血费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.111" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="白蛋白类制品费" />
                                    <value xsi:type="MO" value="{白蛋白类制品费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.113" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="球蛋白类制品费" />
                                    <value xsi:type="MO" value="{球蛋白类制品费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.112" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="凝血因子类制品费" />
                                    <value xsi:type="MO" value="{凝血因子类制品费}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.114" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="细胞因子类制品费" />
                                    <value xsi:type="MO" value="{细胞因子类制品费}" currency="元" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 耗材类费用 -->
                    <entry>
                        <organizer classCode="CLUSTER" moodCode="EVN">
                            <statusCode></statusCode>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.038" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="一次性医用材料费—检查用" />
                                    <value xsi:type="MO" value="{一次性医用材料费—检查用}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.040" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="一次性医用材料费—治疗用" />
                                    <value xsi:type="MO" value="{一次性医用材料费—治疗用}" currency="元" />
                                </observation>
                            </component>
                            <component>
                                <observation classCode="ORS" moodCodo="EVN">
                                    <code code="HDSD00.11.039" codeSystem="2.16.156.10011.2.2.4"
                                        codeSystemName="住院病案首页基本数据集" displayName="一次性医用材料费—手术用" />
                                    <value xsi:type="MO" value="{一次性医用材料费—手术用}" currency="元" />
                                </observation>
                            </component>
                        </organizer>
                    </entry>
                    <!-- 其他费用 -->
                    <entry>
                        <observation classCode="ORS" moodCodo="EVN">
                            <code code="HSDB05.10.130" codeSystem="2.16.156.10011.2.2.4"
                                codeSystemName="住院病案首页基本数据集" displayName="其他费" />
                            <value xsi:type="MO" value="{其他费}" currency="元" />
                        </observation>
                    </entry>
                </section>
            </component>
"""

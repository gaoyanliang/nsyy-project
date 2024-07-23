

body_section_code = """
<code code="{section_code}" displayName="{section_name}"
            codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC" />
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

body_section_entry_relation_ship = """
<entry>
    <observation classCode="OBS" moodCode="EVN">
        {code}
        {value}
        <!-- {entry_ship_name} -->
        <entryRelationship typeCode="COMP">
            <observation ulassCode="OBS" moodCode="EVN">
                <code code="{entry_ship_code}" codeSystem="2.16.156.10011.2.2.1"
                    codeSystemName="卫生信息数据元目录" displayName="{entry_ship_name}" />
                {entry_ship_body}
            </observation>
        </entryRelationship>
    </observation>
</entry>
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

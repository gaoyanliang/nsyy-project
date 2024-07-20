import time
from datetime import datetime
from xml.dom.minidom import parseString

from gylmodules.apoplexy_analysis.xml_const import const as xml_const
from gylmodules.apoplexy_analysis.xml_const import header as xml_header
from gylmodules.apoplexy_analysis.xml_const import body as xml_body


# 组装 header 信息

def assembling_header(admission_record: str, data: dict):
    # xml header
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档标识编码}', 'nsyy001') \
        .replace('{文档标题}', '入院记录') \
        .replace('{文档生成时间}', datetime.now().strftime('%Y%m%d%H%M%S'))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target \
        .replace('{住院号}', '123456') \
        .replace('{患者所在小区}', '南石小区') \
        .replace('{患者所在街道}', '南石街道') \
        .replace('{患者所在乡镇}', '南石镇') \
        .replace('{患者所在区}', '南石区') \
        .replace('{患者所在市}', '南石市') \
        .replace('{患者所在省}', '南石省') \
        .replace('{患者身份证号}', '123456789012345678') \
        .replace('{患者姓名}', '张三') \
        .replace('{患者性别编码}', '1') \
        .replace('{患者性别}', '男') \
        .replace('{患者婚姻状况编码}', '1') \
        .replace('{患者婚姻状况}', '未婚') \
        .replace('{患者民族编码}', '1') \
        .replace('{患者民族}', '汉族') \
        .replace('{患者年龄}', '20') \
        .replace('{患者职业编码}', '20') \
        .replace('{患者职业}', '教师')

    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author \
        .replace('{文档创作时间}', datetime.now().strftime('%Y%m%d%H%M%S')) \
        .replace('{文档创作者id}', '120') \
        .replace('{文档创作者}', '南石医院')

    # 病史陈述者
    admission_record = admission_record + xml_header.xml_header_informant \
        .replace('{病史陈述者身份证号码}', '') \
        .replace('{陈述者与患者的关系代码}', '1') \
        .replace('{陈述者与患者的关系}', '本人') \
        .replace('{病史陈述者姓名}', '张三')

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', '120') \
        .replace('{医疗卫生机构名称}', '南阳南石医院')

    # 最终审核者签名
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{最终审核者id}', '120') \
        .replace('{最终审核者}', '李主任')

    # 接诊医师签名/住院医师签名/主治医师签名
    admission_record = admission_record + xml_header.xml_header_authenticator \
        .replace('{接诊医师id}', '120') \
        .replace('{显示医师名字}', '接诊医师') \
        .replace('{医师名字}', '李接诊')
    admission_record = admission_record + xml_header.xml_header_authenticator \
        .replace('{接诊医师id}', '120') \
        .replace('{显示医师名字}', '住院医师') \
        .replace('{医师名字}', '李住院')
    admission_record = admission_record + xml_header.xml_header_authenticator \
        .replace('{接诊医师id}', '120') \
        .replace('{显示医师名字}', '主治医师') \
        .replace('{医师名字}', '李主治')

    # 关联文档
    admission_record = admission_record + xml_header.xml_header_related_document

    # 病床号、病房、病区、科室和医院的关联
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter \
        .replace('{入院时间}', datetime.now().strftime('%Y%m%d%H%M%S')) \
        .replace('{病床编码}', '1') \
        .replace('{病床}', '1床') \
        .replace('{病房编码}', '514') \
        .replace('{病房}', '514室') \
        .replace('{科室编码}', '120') \
        .replace('{科室}', '神经内科') \
        .replace('{病区编码}', '120') \
        .replace('{病区}', '神经内科一病区') \
        .replace('{医院编码}', '120') \
        .replace('{医院}', '南阳南石医院')

    return admission_record


# 组装 body
def assembling_body(admission_record: str, data: dict):
    # 主诉
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10154-3')
                 .replace('{section_name}', 'CHIEF COMPLAINT')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '主诉') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE04.01.119.00')
                 .replace('{entry_name}', '主诉')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', '右眼无痛性视力渐降3年')))

    # 现病史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10164-2')
                 .replace('{section_name}', 'HISTORY OF PRESENT ILLNESS')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '现病史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DE02.10.071.00')
                 .replace('{entry_name}', '现病史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "3年前，患者无明显诱因感右眼视物不清、视力下降，似眼前有雾遮挡，无眼红、眼痛等不适，未作治疗，今为求诊治前来我院。门诊以\"白内障\"入院。发病以来，精神状态正常饮食正常睡眠状况正常小便正常大便正常体力正常体重无变化。发现糖尿病13年，最高血糖16mmol/L，规律皮下注射胰岛素针  早24U  晚22U，具体不详，血糖控制情况不详。发现\"右眼角膜溃疡\"1年余,主要表现为右眼红、磨、流泪，在我院住院治疗，好转后出院，具体详见上次大病历。")))

    # 既往史
    admission_record = admission_record + xml_body.body_history_of_past_illness\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11348-0')
                 .replace('{section_name}', 'HISTORY OF PAST ILLNESS')) \
        .replace('{text}', '<text />') \
        .replace('{history_of_illness}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code
                          .replace('{section_code}', 'DE05.10.031.00')
                          .replace('{section_name}', '—般健康状况标志'))
                 .replace('{value}', xml_body.value_bl.replace('{value}', 'false'))
                 .replace('{entry_ship_code}', 'DE02.10.026.00')
                 .replace('{entry_ship_name}', '疾病史(含外伤)')
                 .replace('{entry_ship_body}',  xml_body.value_st.replace('{value}', '否认糖尿病、肾病等慢性病史'))) \
        .replace('{history_of_infectious_diseases}', xml_body.body_section_entry_relation_ship
                 .replace('{code}', xml_body.body_section_code
                          .replace('{section_code}', 'DE05.10.119.00')
                          .replace('{section_name}', '患者传染性标志'))
                 .replace('{value}', xml_body.value_bl.replace('{value}', 'true'))
                 .replace('{entry_ship_code}', 'DE02.10.008.00')
                 .replace('{entry_ship_name}', '传染病史')
                 .replace('{entry_ship_body}', xml_body.value_st.replace('{value}', '否认传染病史'))) \
        .replace('{marriage_and_childbearing_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.098.00')
                 .replace('{entry_name}', '婚育史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "23 岁结婚配偶健康状况良好。夫妻关系和睦。育1子1女。"))) \
        .replace('{allergy_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.022.00')
                 .replace('{entry_name}', '过敏史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "否认药物及食物过敏史"))) \
        .replace('{surgical_history}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.022.00')
                 .replace('{entry_name}', '手术史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "否认手术史")))

    # 预防接种史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '11369-6')
                 .replace('{section_name}', 'HISTORY OF IMMUNIZATIONS')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '预防接种史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.101.00')
                 .replace('{entry_name}', '预防接种史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "预防接种史随社会进行")))

    # 输血史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '56836-0')
                 .replace('{section_name}', 'History of blood transfusion')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '输血史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.100.00')
                 .replace('{entry_name}', '输血史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "否认输血史及献血史")))

    # 个人史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '29762-2')
                 .replace('{section_name}', 'Social history')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '个人史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.097.00')
                 .replace('{entry_name}', '个人史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "生长于原籍；无外地长期居住史；无疫区疫水接触史；无毒物接触史无放射性工作史；无烟酒嗜好史；否认性病及冶游史。")))

    # 月经史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '49033-4')
                 .replace('{section_name}', 'Menstrual History')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '月经史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.102.00')
                 .replace('{entry_name}', '月经史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "绝经后无阴道不规则出血。。孕2次，产2次。")))

    # 家族史
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '10157-6')
                 .replace('{section_name}', 'HISTORY OF FAMILY MEMBER DISEASES')) \
        .replace('{text}', '<text />') \
        .replace('{entry_observation_name}', '家族史') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO2.10.103.00')
                 .replace('{entry_name}', '家族史')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "父母均年高已故，1哥1弟已故，死因不详，3弟体健，家族中无同类病人。无遗传倾向疾患。")))

    # 生命体征
    admission_record = admission_record + xml_body.body_vital_signs\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8716-3')
                 .replace('{section_name}', 'VITAL SIGNS')) \
        .replace('{text}', '<text />') \
        .replace('{body_temperature}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.186.00')
                 .replace('{entry_name}', '体温°C')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "36.5").replace('{unit}', '°C'))) \
        .replace('{pulse_rate}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.118.00')
                 .replace('{entry_name}', '脉率(次/min)')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "70").replace('{unit}', '次/min'))) \
        .replace('{respiratory_rate}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.082.00')
                 .replace('{entry_name}', '呼吸频率(次/min)')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "20").replace('{unit}', '次/min'))) \
        .replace('{systolic}', "120") \
        .replace('{diastolic}', "60") \
        .replace('{height}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.167.00')
                 .replace('{entry_name}', '身高（cm）')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "170").replace('{unit}', 'cm'))) \
        .replace('{weight}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.188.00')
                 .replace('{entry_name}', '体重（kg）')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "60").replace('{unit}', 'kg')))

    # todo 体格检査章节

    # 辅助检査章节
    admission_record = admission_record + xml_body.body_component\
        .replace('{text}', '<code displayName="辅助检查" /> <text />') \
        .replace('{entry_observation_name}', '辅助检查') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.30.009.00')
                 .replace('{entry_name}', '辅助检查')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "浅表组织器官B超：右眼玻璃体浑浊。(我院2024-02-20)眼科A超：眼轴：OD：(22.39)mm。(我院2024-02-20)角膜曲率：OD：( K1：45.59D，K2：45.87D)。(我院2024-02-20)人工晶体度数测量：OD：（+21.00D ）。(我院2024-02-20)角膜内皮计数：OD:2632/mm2。  (我院2024-02-20)角膜厚度：OD：505um.(我院2024-02-20)OCT检查：右眼视网膜结构可。(我院2024-02-20)")))

    # todo 主要健康问题章节

    # 治疗计划章节
    admission_record = admission_record + xml_body.body_component\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '18776-5')
                 .replace('{section_name}', 'TREATMENT PLAN')) \
        .replace('{text}', '<text />') \
        .replace('{entry}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO6.00.300.00')
                 .replace('{entry_name}', '治则治法')
                 .replace('{entry_body}', xml_body.value_st.replace('{value}', "治则治法")))


    return admission_record


# 格式化 xml

def prettify_xml(xml_string):
    dom = parseString(xml_string)
    pretty_xml_as_string = dom.toprettyxml()

    # Remove extra blank lines
    lines = pretty_xml_as_string.split('\n')
    non_empty_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_empty_lines)


# 组装入院记录
def assembling_admission_record():
    # xml 声明
    admission_record = xml_const.xml_statement
    # xml 开始
    admission_record = admission_record + xml_const.xml_start

    # 组装 header
    admission_record = assembling_header(admission_record, {})

    # xml body 开始
    admission_record = admission_record + xml_const.xml_body_start

    # 组装 body
    admission_record = assembling_body(admission_record, {})

    # xml body 结束
    admission_record = admission_record + xml_const.xml_body_end
    # xml 结束
    admission_record = admission_record + xml_const.xml_end

    # 格式化 xml
    pretty_xml = prettify_xml(admission_record)
    print(pretty_xml)


assembling_admission_record()









# ===================== test




data = xml_body.body_vital_signs\
        .replace('{code}', xml_body.body_section_code
                 .replace('{section_code}', '8716-3')
                 .replace('{section_name}', 'VITAL SIGNS')) \
        .replace('{text}', '<text />') \
        .replace('{body_temperature}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.186.00')
                 .replace('{entry_name}', '体温°C')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "36.5").replace('{unit}', '°C'))) \
        .replace('{pulse_rate}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.118.00')
                 .replace('{entry_name}', '脉率(次/min)')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "70").replace('{unit}', '次/min'))) \
        .replace('{respiratory_rate}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.082.00')
                 .replace('{entry_name}', '呼吸频率(次/min)')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "20").replace('{unit}', '次/min'))) \
        .replace('{systolic}', "120") \
        .replace('{diastolic}', "60") \
        .replace('{height}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.167.00')
                 .replace('{entry_name}', '身高（cm）')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "170").replace('{unit}', 'cm'))) \
        .replace('{weight}', xml_body.body_section_entry
                 .replace('{entry_code}', 'DEO4.10.188.00')
                 .replace('{entry_name}', '体重（kg）')
                 .replace('{entry_body}', xml_body.value_pq.replace('{value}', "60").replace('{unit}', 'kg')))

# print(data)
#
# pretty_xml = prettify_xml(data)
# print(pretty_xml)


# json_data = {
#     "pat_no": '400657',
#     "pat_type": 3,
#     "record": {'time': datetime.now()},
#     "handler_name": "handler_name",
#     "timer": '2024-07-19 15:19:19',
#     "method": "method",
#     "analysis": "analysis"
# }
#
# medical_record_writing_back(json_data)
#









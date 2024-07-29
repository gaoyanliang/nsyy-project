from gylmodules.medical_record_analysis.xml_const import header as xml_header
from gylmodules.medical_record_analysis.xml_const import body as xml_body
from datetime import datetime

"""
====================================================================================================
======================================= 住院病案首页CDA 文档构建 ======================================
====================================================================================================
"""


# 组装 header 信息
# todo 文档标识编码
def assembling_header(admission_record: str, data: dict):
    # xml header
    admission_record = admission_record + xml_header.xml_header_file_info \
        .replace('{文档模版编号}', "2.16.156.10011.2.1.1.52") \
        .replace('{文档类型}', "C0032") \
        .replace('{文档标识编码}', data.get('file_no')) \
        .replace('{文档标题}', data.get('file_title')) \
        .replace('{文档生成时间}', datetime.now().strftime('%Y%m%d%H%M%S'))

    # 文档记录对象（患者信息）
    admission_record = admission_record + xml_header.xml_header_record_target4 \
        .replace('{health_card}', data.get('health_card', '/')) \
        .replace('{pat_no}', data.get('pat_no', '/')) \
        .replace('{bing_an}', data.get('bing_an', '/')) \
        .replace('{addr_house_num}', data.get('pat_addr', '/')) \
        .replace('{postal_code}', data.get('postal_code', '/')) \
        .replace('{电话}', data.get('电话', '/')) \
        .replace('{pat_id_card}', data.get('pat_id_card', '/')) \
        .replace('{pat_name}', data.get('pat_name', '/')) \
        .replace('{pat_sex_no}', '1') \
        .replace('{pat_sex}', data.get('pat_sex', '/')) \
        .replace('{pat_marriage_no}', '1') \
        .replace('{pat_marriage}', data.get('pat_marriage', '/')) \
        .replace('{pat_nation_no}', '1') \
        .replace('{pat_nation}', data.get('pat_nation', '/')) \
        .replace('{出生地}', data.get('出生地', '/')) \
        .replace('{出生地邮编}', data.get('出生地邮编', '/')) \
        .replace('{国籍编码}', data.get('国籍编码', '/')) \
        .replace('{国籍}', data.get('国籍', '/')) \
        .replace('{pat_age}', data.get('pat_age', '/')) \
        .replace('{工作单位名称}', data.get('工作单位名称', '/')) \
        .replace('{工作单位电话}', data.get('工作单位电话', '/')) \
        .replace('{工作地址}', data.get('工作地址', '/')) \
        .replace('{工作邮编}', data.get('工作邮编', '/')) \
        .replace('{户口地址}', data.get('户口地址', '/')) \
        .replace('{户口邮编}', data.get('户口邮编', '/')) \
        .replace('{籍贯}', data.get('籍贯', '/')) \
        .replace('{职业编码}', data.get('pat_occupation_no', '/')) \
        .replace('{职业}', data.get('pat_occupation', '/')) \
        .replace('{医疗机构编号}', data.get('医疗机构编号', '/')) \
        .replace('{医疗机构名称}', data.get('医疗机构名称', '/'))

    # 文档创作者
    admission_record = admission_record + xml_header.xml_header_author1 \
        .replace('{文档创作者id}', data.get('hospital_no')) \
        .replace('{文档创作者}', data.get('hospital_name'))

    # 保管机构
    admission_record = admission_record + xml_header.xml_header_custodian \
        .replace('{医疗卫生机构编号}', data.get('hospital_no')) \
        .replace('{医疗卫生机构名称}', data.get('hospital_name'))

    # 最终审核者签名
    admission_record = admission_record + xml_header.xml_header_legal_authenticator \
        .replace('{医师id}', '/') \
        .replace('{展示医师}', '科主任') \
        .replace('{医师}', data.get('科主任', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '主任(副主任)医师') \
        .replace('{医师名字}', data.get('主任医师', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '主治医师') \
        .replace('{医师名字}', data.get('主治医师', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '住院医师') \
        .replace('{医师名字}', data.get('住院医师', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '责任护士') \
        .replace('{医师名字}', data.get('责任护士', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '进修医师') \
        .replace('{医师名字}', data.get('进修医师', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '实习医师') \
        .replace('{医师名字}', data.get('实习医师', '/'))
    admission_record = admission_record + xml_header.xml_header_authenticator3 \
        .replace('{医师id}', '/') \
        .replace('{显示医师名字}', '编码员') \
        .replace('{医师名字}', data.get('编码员', '/'))

    # 其他参与者(联系人)
    admission_record = admission_record + xml_header.xml_header_participant \
        .replace('{联系人与患者关系}', data.get('联系人关系', '/')) \
        .replace('{联系人地址}',  data.get('联系人地址', '/')) \
        .replace('{联系人邮编}',  data.get('联系人邮编', '/')) \
        .replace('{联系人电话}',  data.get('联系人电话', '/')) \
        .replace('{联系人姓名}',  data.get('联系人姓名', '/'))

    # 关联文档
    admission_record = admission_record + xml_header.xml_header_related_document

    # 病床号、病房、病区、科室和医院的关联
    admission_record = admission_record + xml_header.xml_header_encompassing_encounter1 \
        .replace('{入院途径编码}', data.get('入院途径编码', '/')) \
        .replace('{入院途径名称}', data.get('入院途径', '/')) \
        .replace('{入院日期}', data.get('入院日期', '/')) \
        .replace('{出院日期}', data.get('出院日期', '/')) \
        .replace('{病房}', data.get('病房', '/')) \
        .replace('{科室id}', data.get('科室id', '/')) \
        .replace('{入院科别}', data.get('入院科别', '/'))

    return admission_record


# 组装 body 信息
def assembling_body(admission_record: str, data: dict):
    admission_record = admission_record + xml_body.body_inpatient_homepage_body\
        .replace('{新生儿入院体重}', data.get('新生儿入院体重', '/')) \
        .replace('{新生儿出生体重}', data.get('新生儿出生体重', '/')) \
        .replace('{门急诊诊断}', data.get('门急诊诊断名称', '/')) \
        .replace('{门急诊诊断编码}', data.get('门急诊诊断疾病编码', '/')) \
        .replace('{疾病名称描述}', data.get('疾病名称描述', '/')) \
        .replace('{疾病名称编码}', data.get('疾病编码', '/')) \
        .replace('{住院者疾病状态代码}', data.get('住院者疾病状态代码', '/')) \
        .replace('{损伤外部原因描述}', data.get('损伤中毒原因', '/')) \
        .replace('{损伤中毒的外部原因-疾病编码}', data.get('损伤中毒疾病编码', '/')) \
        .replace('{入院前昏迷时间d}', data.get('入院前昏迷时间d', '/')) \
        .replace('{入院前昏迷时间h}', data.get('入院前昏迷时间h', '/')) \
        .replace('{入院前昏迷时间min}', data.get('入院前昏迷时间min', '/')) \
        .replace('{入院后昏迷时间d}', data.get('入院后昏迷时间d', '/')) \
        .replace('{入院后昏迷时间h}', data.get('入院后昏迷时间h', '/')) \
        .replace('{入院后昏迷时间min}', data.get('入院后昏迷时间min', '/')) \
        .replace('{转科科室名称}', data.get('转科科别', '/')) \
        .replace('{确诊日期}', data.get('确诊日期', '/')) \
        .replace('{疾病名称}', data.get('疾病名称', '/')) \
        .replace('{疾病编码}', data.get('疾病编码', '/')) \
        .replace('{病情代码}', data.get('病情代码', '/')) \
        .replace('{离院方式代码}', data.get('离院方式', '/')) \
        .replace('{过敏药物}', data.get('过敏药物', '/')) \
        .replace('{ABO血型代码}', data.get('ABO血型代码', '/')) \
        .replace('{ABO血型}', data.get('ABO血型', '/')) \
        .replace('{RH血型代码}', data.get('RH血型代码', '/')) \
        .replace('{RH血型}', data.get('RH血型', '/')) \
        .replace('{手术操作日期}', data.get('手术操作日期', '/')) \
        .replace('{手术者id}', data.get('手术者id', '/')) \
        .replace('{手术者}', data.get('手术者', '/')) \
        .replace('{第一助手id}', data.get('第一助手id', '/')) \
        .replace('{第一助手}', data.get('第一助手', '/')) \
        .replace('{第二助手id}', data.get('第二助手id', '/')) \
        .replace('{第二助手}', data.get('第二助手', '/')) \
        .replace('{手术名称}', data.get('手术名称', '/')) \
        .replace('{手术级别}', data.get('手术级别', '/')) \
        .replace('{手术切口类别代码}', data.get('手术切口类别代码', '/')) \
        .replace('{手术切口愈合等级}', data.get('手术切口愈合等级', '/')) \
        .replace('{手术切口愈合等级名称}', data.get('手术切口愈合等级名称', '/')) \
        .replace('{麻醉员编码}', data.get('麻醉员编码', '/')) \
        .replace('{麻醉员}', data.get('麻醉员', '/')) \
        .replace('{住院次数}', data.get('住院次数', '/')) \
        .replace('{住院天数}', data.get('实际住院天数', '/')) \
        .replace('{病房id}', data.get('病房id', '/')) \
        .replace('{病房}', data.get('病房', '/')) \
        .replace('{科室id}', data.get('科室id', '/')) \
        .replace('{科室}', data.get('入院科室', '/')) \
        .replace('{死亡患者尸检标志}', data.get('死亡患者尸检标志', '/')) \
        .replace('{质控日期}', data.get('质控日期', '/')) \
        .replace('{病案质量等级表}', data.get('病案质量等级表', '/')) \
        .replace('{质控医生id}', data.get('质控医生id', '/')) \
        .replace('{质控医生}', data.get('质控医生', '/')) \
        .replace('{质控护士id}', data.get('质控护士id', '/')) \
        .replace('{质控护士}', data.get('质控护士', '/')) \
        .replace('{出院31天内再住院标志}', data.get('出院31天内再住院标志', '/')) \
        .replace('{出院31天内再住院目的}', data.get('出院31天内再住院目的', '/')) \
        .replace('{医疗付费方式编码}', data.get('医疗付费方式编码', '/')) \
        .replace('{医疗付费方式}', data.get('医疗付款方式', '/')) \
        .replace('{总费用}', data.get('总费用', '/')) \
        .replace('{自付金额}', data.get('自付金额', '/')) \
        .replace('{一般医疗服务费}', data.get('壹', '/')) \
        .replace('{一般治疗操作费}', data.get('贰', '/')) \
        .replace('{护理费}', data.get('叁', '/')) \
        .replace('{综合医疗服务费—其他费用}', data.get('肆', '/')) \
        .replace('{病理诊断费}', data.get('病理诊断费', '/')) \
        .replace('{实验室诊断费}', data.get('实验室诊断费', '/')) \
        .replace('{影像学诊断费}', data.get('影像学诊断费', '/')) \
        .replace('{临床诊断项目费}', data.get('临床诊断项目费', '/')) \
        .replace('{非手术治疗项目费}', data.get('非手术治疗项目费', '/')) \
        .replace('{临床物理治疗费}', data.get('临床物理治疗费', '/')) \
        .replace('{手术治疗费}', data.get('手术治疗费', '/')) \
        .replace('{一般治疗操作费}', data.get('一般治疗操作费', '/')) \
        .replace('{麻醉费}', data.get('麻醉费', '/')) \
        .replace('{手术费}', data.get('手术费', '/')) \
        .replace('{康复费}', data.get('壹拾壹', '/')) \
        .replace('{中医治疗费}', data.get('壹拾贰', '/')) \
        .replace('{西药费}', data.get('壹拾叁', '/')) \
        .replace('{抗菌药物费用}', data.get('壹叁点一', '/')) \
        .replace('{中成药费}', data.get('壹拾肆', '/')) \
        .replace('{中草药费}', data.get('壹拾伍', '/')) \
        .replace('{血费}', data.get('壹拾陆', '/')) \
        .replace('{白蛋白类制品费}', data.get('壹拾柒', '/')) \
        .replace('{球蛋白类制品费}', data.get('壹拾捌', '/')) \
        .replace('{凝血因子类制品费}', data.get('壹拾玖', '/')) \
        .replace('{细胞因子类制品费}', data.get('贰拾', '/')) \
        .replace('{一次性医用材料费—检查用}', data.get('贰拾壹', '/')) \
        .replace('{一次性医用材料费—治疗用}', data.get('贰拾贰', '/')) \
        .replace('{一次性医用材料费—手术用}', data.get('贰拾叁', '/')) \
        .replace('{其他费}', data.get('贰拾肆', '/'))
    return admission_record


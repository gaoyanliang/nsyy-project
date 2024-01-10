# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from xml.dom.minidom import parse
import xml.dom.minidom
import xml.etree.ElementTree as ET
import csv


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


def parse_xml(path):
    tree = ET.ElementTree(file=path)
    root = tree.getroot()

    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(path)
    collection = DOMTree.documentElement
    if collection.hasAttribute("shelf"):
        print("Root element : %s" % collection.getAttribute("shelf"))


def parse_xml_use_elementtree(path):
    # Parse the XML data
    tree = ET.ElementTree(file=path)  # Replace 'xml_data' with your actual XML data
    root = tree.getroot()

    patient_info = {
        '科室': '',
        '床号': '',
        '住院号': '',
        '入院科室': '',
        '住院次数': '',
        '入院情况': '',
        '过敏史': '',
        '姓名': '',
        '性别': '',
        '年龄': '',
        '籍贯': '',
        '职业': '',
        '婚姻': '',
        '民族': '',
        '身份证号': '',
        '工作单位': '',
        '入院时间': '',
        '现住址': '',
        '病史采集时间': '',
        '联系人姓名': '',
        '与患者关系': '',
        '记录时间': '',
        '联系人电话': '',
        '电话号码': '',
        '病史叙述者': '',
    }

    # 提取科室，床号，住院号等信息
    patient_info['科室'] = root.find(".//element[@title='科室']").text
    patient_info['床号'] = root.find(".//element[@title='床号']").text
    patient_info['住院号'] = root.find(".//element[@title='住院号']").text
    patient_info['入院科室'] = root.find(".//element[@title='入院科室']").text
    patient_info['住院次数'] = root.find(".//element[@title='住院次数（次）']").text
    patient_info['入院情况'] = root.find(".//e_enum[@title='入院情况']").find('enumvalues/element').text
    # patient_info['过敏史'] = root.find(".//group[@code='05JZS085']/groupstart/utext").text

    # 提取姓名，性别，年龄等基本信息
    patient_info['姓名'] = root.find(".//element[@title='姓名']").text
    patient_info['性别'] = root.find(".//e_enum[@title='性别']").find('enumvalues/element').text
    patient_info['年龄'] = root.find(".//element[@title='年龄']").text
    patient_info['籍贯'] = root.find(".//element[@title='籍贯']").text
    patient_info['职业'] = root.find(".//element[@title='职业']").text
    patient_info['婚姻'] = root.find(".//utext[@no='31']").text.strip(': ')
    patient_info['民族'] = root.find(".//element[@title='民族']").text
    patient_info['身份证号'] = root.find(".//element[@title='身份证件号码']").text
    patient_info['工作单位'] = root.find(".//utext[@no='38']").text.strip(': ')
    patient_info['入院时间'] = root.find(".//element[@title='入院日期']").text
    patient_info['现住址'] = root.find(".//element[@title='家庭地址']").text
    patient_info['病史采集时间'] = root.find(".//element[@title='信息录入日期时间']").text
    patient_info['联系人姓名'] = root.find(".//utext[@no='49']").text.strip(': ')
    patient_info['与患者关系'] = root.find(".//utext[@no='52']").text.strip(': ')
    patient_info['记录时间'] = root.find(".//element[@title='记录时间']").text
    patient_info['联系人电话'] = root.find(".//utext[@no='412']").text
    patient_info['电话号码'] = root.find(".//element[@title='电话号码']").text
    patient_info['病史叙述者'] = root.find(".//e_enum[@title='病史陈述者']").find('enumvalues/element').text

    # 病人信息
    patient_info['主诉'] = root.find(".//utext[@no='65']").text
    patient_info['精神状态'] = root.find(".//e_enum[@title='神态']").find('enumvalues/element').text
    patient_info['饮食情况'] = root.find(".//e_enum[@title='饮食情况']").find('enumvalues/element').text
    patient_info['睡眠状态'] = root.find(".//e_enum[@title='睡眠状态']").find('enumvalues/element').text
    patient_info['小便'] = root.find(".//e_enum[@title='小便']").find('enumvalues/element').text
    patient_info['大便'] = root.find(".//e_enum[@title='大便']").find('enumvalues/element').text
    patient_info['体力'] = root.find(".//e_enum[@title='体力描述']").find('enumvalues/element').text
    patient_info['体重'] = root.find(".//e_enum[@title='体重']").find('enumvalues/element').text

    patient_info['既往史'] = root.find(".//utext[@no='82']").text.strip(": ")
    patient_info['个人史'] = root.find(".//utext[@no='83']").text.strip(": ")
    patient_info['婚育史'] = root.find(".//utext[@no='84']").text.strip(": ")

    patient_info['月经周期'] = root.find(".//e_enum[@title='月经周期']").find('enumvalues/element').text
    patient_info['月经颜色'] = root.find(".//e_enum[@title='月经颜色']").find('enumvalues/element').text
    patient_info['月经出血量类别'] = root.find(".//e_enum[@title='月经出血量类别']").find('enumvalues/element').text
    patient_info['有无痛经'] = root.find(".//e_enum[@title='有无痛经']").find('enumvalues/element').text
    patient_info['家族史'] = root.find(".//utext[@no='96']").text.strip(": ")
    patient_info['体温'] = root.find(".//e_enum[@title='体温']").find('enumvalues/element').text + root.find(".//utext[@no='102']").text
    patient_info['脉搏'] = root.find(".//e_enum[@title='脉搏']").find('enumvalues/element').text + root.find(".//utext[@no='104']").text
    patient_info['呼吸'] = root.find(".//e_enum[@title='呼吸']").find('enumvalues/element').text + root.find(".//utext[@no='106']").text
    patient_info['血压'] = root.find(".//e_enum[@title='血压']").find('enumvalues/element').text + root.find(".//utext[@no='108']").text
    patient_info['体型'] = root.find(".//e_enum[@title='体型']").find('enumvalues/element').text
    patient_info['营养'] = root.find(".//e_enum[@title='营养']").find('enumvalues/element').text
    patient_info['皮肤水肿'] = root.find(".//e_enum[@title='皮肤水肿']").find('enumvalues/element').text
    patient_info['有无皮疹'] = root.find(".//e_enum[@title='有无皮疹']").find('enumvalues/element').text
    patient_info['有无褥疮'] = root.find(".//e_enum[@title='有无褥疮']").find('enumvalues/element').text
    patient_info['淋巴结触及'] = root.find(".//utext[@no='115']").text
    patient_info['眼科神经'] = root.find(".//utext[@no='121']").text
    patient_info['耳科神经'] = root.find(".//utext[@no='123']").text
    patient_info['神经口唇'] = root.find(".//e_enum[@title='神经口唇']").find('enumvalues/element').text
    patient_info['神经咽部'] = root.find(".//e_enum[@title='神经咽部']").find('enumvalues/element').text
    patient_info['颈动脉搏动: 左'] = root.find(".//e_enum[@iid='AC40BF91A59D44D4B1FE6E9E51440205']").find('enumvalues/element').text
    patient_info['颈动脉搏动: 右'] = root.find(".//e_enum[@iid='D8513C1E48AD4CE6B5D31C3ED48676B2']").find('enumvalues/element').text
    patient_info['扁桃体情况'] = root.find(".//e_enum[@title='扁桃体情况']").find('enumvalues/element').text

    patient_info['胸部对称'] = root.find(".//e_enum[@title='胸部对称']").find('enumvalues/element').text
    patient_info['胸廓畸形'] = root.find(".//e_enum[@title='胸廓畸形']").find('enumvalues/element').text
    patient_info['胸部活动度'] = root.find(".//e_enum[@title='胸部活动度']").find('enumvalues/element').text
    patient_info['啰音'] = root.find(".//e_enum[@title='啰音']").find('enumvalues/element').text

    patient_info['甲状腺'] = root.find(".//utext[@no='130']").text
    patient_info['肺部语颤'] = root.find(".//utext[@no='136']").text
    patient_info['心前区隆起'] = root.find(".//utext[@no='142']").text
    patient_info['心脏震颤'] = root.find(".//utext[@no='144']").text
    patient_info['心界情况'] = root.find(".//utext[@no='146']").text
    patient_info['心率'] = root.find(".//element[@title='脉搏']").text + root.find(
        ".//utext[@no='148']").text
    patient_info['心律描述'] = root.find(".//utext[@no='149']").text
    patient_info['听诊心音'] = root.find(".//utext[@no='151']").text
    patient_info['额外心音'] = root.find(".//utext[@no='153']").text
    patient_info['心脏杂音'] = root.find(".//utext[@no='155']").text

    patient_info['腹部形态'] = root.find(".//e_enum[@title='神经腹部']").find('enumvalues/element').text
    patient_info['腹部情况'] = root.find(".//utext[@no='159']").text
    patient_info['腹部包块描述'] = root.find(".//utext[@no='161']").text
    patient_info['腹部压痛'] = root.find(".//utext[@no='163']").text
    patient_info['移动性浊音'] = root.find(".//e_enum[@title='移动性浊音']").find('enumvalues/element').text
    patient_info['肝脾触诊'] = root.find(".//utext[@no='166']").text
    patient_info['腹部叩诊'] = root.find(".//utext[@no='168']").text
    patient_info['肠鸣音'] = root.find(".//e_enum[@title='肠鸣音']").find('enumvalues/element').text
    patient_info['膀胱'] = root.find(".//e_enum[@title='膀胱充盈']").find('enumvalues/element').text
    patient_info['四肢及脊柱畸形'] = root.find(".//utext[@no='175']").text
    patient_info['四肢及脊柱压痛'] = root.find(".//utext[@no='177']").text
    patient_info['运动受限'] = root.find(".//utext[@no='179']").text
    patient_info['外生殖器情况'] = root.find(".//utext[@no='181']").text
    patient_info['意识'] = root.find(".//e_enum[@title='意识状态']").find('enumvalues/element').text
    patient_info['情感反应'] = root.find(".//e_enum[@title='情感反应']").find('enumvalues/element').text
    patient_info['妄想'] = root.find(".//e_enum[@title='妄想']").find('enumvalues/element').text
    patient_info['幻想'] = root.find(".//e_enum[@title='幻想']").find('enumvalues/element').text
    patient_info['自知力'] = root.find(".//e_enum[@title='自知力']").find('enumvalues/element').text
    patient_info['远期记忆'] = root.find(".//e_enum[@title='远期记忆']").find('enumvalues/element').text
    patient_info['近期记忆'] = root.find(".//e_enum[@title='近期记忆']").find('enumvalues/element').text
    patient_info['计算力'] = root.find(".//e_enum[@title='计算力']").find('enumvalues/element').text
    patient_info['理解判断力'] = root.find(".//e_enum[@title='理解判断力']").find('enumvalues/element').text
    patient_info['人物定向力'] = root.find(".//e_enum[@title='人物定向力']").find('enumvalues/element').text
    patient_info['地点定向力'] = root.find(".//e_enum[@title='地点定向力']").find('enumvalues/element').text
    patient_info['失语情况'] = root.find(".//e_enum[@title='失语情况']").find('enumvalues/element').text
    patient_info['构音不良'] = root.find(".//e_enum[@title='构音不良']").text
    patient_info['左（嗅觉）'] = root.find(".//e_enum[@title='左（嗅觉）']").find('enumvalues/element').text
    patient_info['右（嗅觉）'] = root.find(".//e_enum[@title='右（嗅觉）']").find('enumvalues/element').text
    patient_info['视力检查(左)'] = root.find(".//e_enum[@title='视力检查(左)']").find('enumvalues/element').text
    patient_info['视力检查(右)'] = root.find(".//e_enum[@title='视力检查(右)']").find('enumvalues/element').text
    patient_info['视野检查'] = root.find(".//utext[@no='217']").text
    patient_info['视乳头颜色'] = root.find(".//e_enum[@title='视乳头颜色']").find('enumvalues/element').text
    patient_info['视乳头边界'] = root.find(".//e_enum[@title='视乳头边界']").find('enumvalues/element').text
    patient_info['视乳头生理凹陷'] = root.find(".//e_enum[@title='视乳头生理凹陷']").find('enumvalues/element').text
    patient_info['眼底静脉搏动'] = root.find(".//e_enum[@title='眼底静脉搏动']").find('enumvalues/element').text
    patient_info['眼底动静脉血管比例'] = root.find(".//e_enum[@title='眼底动静脉血管比例']").find('enumvalues/element').text
    patient_info['眼底血管情况'] = root.find(".//utext[@no='224']").text
    patient_info['视网膜出血'] = root.find(".//e_enum[@iid='9B13DCF6788944FC91D7FEA5F8A81470']").text
    patient_info['眼裂'] = root.find(".//utext[@no='229']").text
    patient_info['上睑下垂-左'] = root.find(".//e_enum[@iid='91549E0831B642F38A23B961F7C8D9BB']").text
    patient_info['上睑下垂-右'] = root.find(".//e_enum[@iid='74580DB37ABD4D7186B3FD1D109C2B97']").text
    patient_info['眼球位置'] = root.find(".//utext[@no='233']").text
    patient_info['眼球活动（左）'] = root.find(".//e_enum[@title='眼球活动（左）']").find('enumvalues/element').text
    patient_info['眼球活动（右）'] = root.find(".//e_enum[@title='眼球活动（右）']").find('enumvalues/element').text
    patient_info['复视'] = root.find(".//e_enum[@title='复视']").find('enumvalues/element').text
    patient_info['眼球分离'] = root.find(".//e_enum[@title='眼球分离']").find('enumvalues/element').text
    patient_info['同向凝视'] = root.find(".//e_enum[@title='同向凝视']").find('enumvalues/element').text
    patient_info['眼震'] = root.find(".//e_enum[@iid='97EEF57E42DB4919AC863B1B666E5144']").text

    # 写入文件
    with open('data.txt', 'w', encoding='utf-8') as f:
        for key, value in patient_info.items():
            f.write(f"{key}: {value}\n")

    print("Data has been written to 'data.txt'")


def test():
    # XML data

    xml_data = '''
    <root>
        <tab br="0" textstyleno="0"/>
        <utext no="62" textstyleno="5" br="0">病史叙述者</utext>
        <utext no="63" br="0">：</utext>
        <e_enum sid="F0F8530EE8DD4AEC869F2E4F4BE51867" iid="37E58D9AF17E487B9E5B9264DD4BEEF8" range_kind="2" isnull="0" title="病史陈述者" datatype="S" code="ZLEMR.SE.0075" placeholder="病史陈述者" value_form="S" min_length="0" max_length="50" min_scale="0" max_scale="0" choicestyle="0" displaystyle="0" textstyleno="6" br="0">
            <enumvalues>
                <element sid="F0F8530EE8DD4AEC869F2E4F4BE51867" title="病史陈述者" showtext="" datatype="S">1</element>
            </enumvalues>
            <![CDATA[ rangexml='<root><multisel>0</multisel><item><value>1</value><meaning>患者本人</meaning></item><item><value>2</value><meaning>患者子女</meaning></item><item><value>3</value><meaning>患者父母</meaning></item><item><value>4</value><meaning>患者直系亲属</meaning></item><item><value>5</value><meaning>患者陪行人员</meaning></item><showmode>2</showmode></root>']]>
            患者本人
        </e_enum>
    </root>
    '''

    # Map enum value to corresponding meaning
    enum_meaning = {
        '1': '患者本人',
        '2': '患者子女',
        '3': '患者父母',
        '4': '患者直系亲属',
        '5': '患者陪行人员'
    }

    # Parse XML data
    root = ET.fromstring(xml_data)

    # Extract information
    medical_history_narrator = root.find(".//utext[@textstyleno='5']").text.strip()
    enum_value = root.find(".//e_enum/enumvalues/element").text.strip()

    enum_meaning_value = enum_meaning.get(enum_value, 'Unknown')

    print(medical_history_narrator)
    print(enum_value)
    print(enum_meaning_value)


def parse_xml_test(path):
    # Parse the XML file
    tree = ET.parse(path)
    # tree = ET.ElementTree(file=path)
    root = tree.getroot()
    for child in root:
        print(child.tag, child.attrib)


def parse_patient_subdocuments(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    patient_info = {}

    # Extract information from the header
    header = root.find('./subdocuments/header/document')
    for enum in header.iter('e_enum'):
        title = enum.get("title")
        value = enum.find('./enumvalues/element').text
        patient_info[title] = value
    for element in header.iter('element'):
        # 排除枚举值中的 element 标签
        if element.attrib.__len__() < 4:
            continue
        title = element.get('title')
        value = element.text.strip() if element.text else ""
        patient_info[title] = value

    __update_enumvalue(patient_info)

    # 写入文件
    with open('subdocuments.txt', 'w', encoding='utf-8') as f:
        for key, value in patient_info.items():
            print(f"{key}:  {value}")
            f.write(f"{key}: {value}\n")

    print("Data has been written to 'subdocuments.txt'")

    return patient_info


def parse_patient_document(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    patient_info = {}

    # Extract information from the header
    header = root.find('./document')
    for enum in header.iter('e_enum'):
        # 跳过不规则的结构
        if enum.find('./enumvalues/element') is None:
            continue
        title = enum.get("title")
        value = enum.find('./enumvalues/element').text
        patient_info[title] = value
    for element in header.iter('element'):
        # 排除枚举值中的 element 标签
        if element.attrib.__len__() < 4:
            continue
        title = element.get('title')
        value = element.text.strip() if element.text else ""
        patient_info[title] = value
    for group in header.iter('group'):
        if group.find('./utext') is None:
            continue
        title = group.get("title")
        value = group.find('./utext').text
        patient_info[title] = value
    for section in header.iter('section'):
        # subs_ections = section.findall('./')
        # # section 中仅包含 break 标签，直接跳过不处理
        # if len(subs_ections) == 1 and subs_ections[0].tag == 'break':
        #     print("====> 跳过 section： " + section.get('title'))
        #     continue
        extract_section_utext_info(section, patient_info)

        # 特殊处理 签名
        if section.get('title').strip() == '签名':
            enum = section.find('./e_enum')
            title = '签名'
            value = enum.find('./enumvalues/element').text
            patient_info[title] = value
        if section.get('title').strip() == '住院医师':
            enum = section.find('./e_enum')
            title = '住院医师'
            value = enum.find('./enumvalues/element').text
            patient_info[title] = value


    # 特殊处理
    for utext in header.iter('utext'):
        if utext.text is None:
            continue
        text = utext.text.replace(' ', '')
        text = text.replace(':', '')
        text = text.replace('：', '')
        if text == '婚姻':
            utest_no = int(utext.get('no'))
            value_no = str(utest_no + 1)
            patient_info['婚姻'] = root.find(".//utext[@no=" + "\'" + value_no + "\'" "]").text.strip(": ")
        if text.strip() == '联系人姓名':
            utest_no = int(utext.get('no'))
            value_no = str(utest_no + 1)
            patient_info['联系人姓名'] = root.find(".//utext[@no=" + "\'" + value_no + "\'" "]").text.strip(": ")
        if text == '与患者关系':
            utest_no = int(utext.get('no'))
            value_no = str(utest_no + 1)
            patient_info['与患者关系'] = root.find(".//utext[@no=" + "\'" + value_no + "\'" "]").text.strip(": ")

    # __update_enumvalue(patient_info)
    # 写入文件
    with open('document.txt', 'w', encoding='utf-8') as f:
        for key, value in patient_info.items():
            print(f"{key}:  {value}")
            f.write(f"{key}: {value}\n")

    print("Data has been written to 'document.txt'")

    return patient_info


# 提取 section 标签的 utext 值，仅包含同级的 utext
def extract_section_utext_info(element, info_dict):
    title = element.get('title')
    value = ''
    for child in element:
        if child.tag == 'utext' and child.text is not None:
            value = value + child.text
    info_dict[title] = value


def __update_enumvalue(patient_info):
    enum = {
        '1': '男',
        '2': '女',
        '3': '未知的性别'
    }
    patient_info['性别'] = enum[patient_info['性别']]

    enum = {
        '1': '危',
        '2': '重',
        '3': '一般',
        '4': '教学',
        '5': '科研',
    }
    patient_info['入院情况'] = enum[patient_info['入院情况']]

    enum = {
        '1': '患者本人',
        '2': '患者子女',
        '3': '患者父母',
        '4': '患者直系亲属',
        '5': '患者陪行人员',
    }
    patient_info['病史陈述者'] = enum[patient_info['病史陈述者']]

    enum = {
        '1': '正常',
        '2': '一般',
        '3': '差',
    }
    patient_info['神态'] = enum[patient_info['神态']]

    enum = {
        '1': '正常',
        '2': '良好',
        '3': '一般',
        '4': '较差',
    }
    patient_info['饮食情况'] = enum[patient_info['饮食情况']]

    enum = {
        '1': '正常',
        '2': '一般',
        '3': '差',
    }
    patient_info['睡眠状态'] = enum[patient_info['睡眠状态']]

    enum = {
        '1': '正常',
        '2': '增多',
        '3': '减少',
        '4': '潴留',
        '5': '失禁',
    }
    patient_info['小便'] = enum[patient_info['小便']]

    enum = {
        '1': '正常',
        '2': '失禁',
        '3': '便结',
    }
    patient_info['大便'] = enum[patient_info['大便']]

    enum = {
        '1': '正常',
        '2': '下降',
    }
    patient_info['体力描述'] = enum[patient_info['体力描述']]

    enum = {
        '1': '无变化',
        '2': '增加',
        '3': '下降',
    }
    patient_info['体重'] = enum[patient_info['体重']]

    enum = {
        '1': '规律',
        '2': '不规律',
    }
    patient_info['月经周期'] = enum[patient_info['月经周期']]

    enum = {
        '1': '红',
        '2': '暗',
    }
    patient_info['月经颜色'] = enum[patient_info['月经颜色']]

    enum = {
        '1': '多',
        '2': '中',
        '3': '少',
    }
    patient_info['月经出血量类别'] = enum[patient_info['月经出血量类别']]

    enum = {
        '1': '无痛经',
        '2': '有痛经',
    }
    patient_info['有无痛经'] = enum[patient_info['有无痛经']]

    enum = {
        '1': '正常',
        '2': '肥胖',
        '3': '消瘦',
        '4': '适中',
    }
    patient_info['体型'] = enum[patient_info['体型']]

    enum = {
        '1': '良好',
        '2': '中等',
        '3': '不良',
        '4': '恶病质',
        '5': '肥胖',
    }
    patient_info['营养'] = enum[patient_info['营养']]

    enum = {
        '1': '有',
        '2': '无',
    }
    patient_info['皮肤水肿'] = enum[patient_info['皮肤水肿']]

    enum = {
        '1': '有',
        '2': '无',
    }
    patient_info['有无皮疹'] = enum[patient_info['有无皮疹']]

    enum = {
        '1': '有',
        '2': '无',
    }
    patient_info['有无褥疮'] = enum[patient_info['有无褥疮']]

    enum = {
        '1': '正常',
        '2': '发绀',
    }
    patient_info['神经口唇'] = enum[patient_info['神经口唇']]

    enum = {
        '1': '正常',
        '2': '充血',
    }
    patient_info['神经咽部'] = enum[patient_info['神经咽部']]

    enum = {
        '1': '无肿大',
        '2': 'Ⅰ度肿大',
        '3': 'II度肿大',
        '4': 'III度肿大',
    }
    patient_info['扁桃体情况'] = enum[patient_info['扁桃体情况']]

    enum = {
        '1': '正常',
        '2': '增强',
        '3': '减弱',
    }
    patient_info['颈动脉搏动情况'] = enum[patient_info['颈动脉搏动情况']]

    enum = {
        '1': '对称',
        '2': '不对称',
    }
    patient_info['胸部对称'] = enum[patient_info['胸部对称']]

    enum = {
        '1': '无畸形',
        '2': '鸡胸',
        '3': '漏斗胸',
        '4': '扁平胸',
        '5': '桶状胸',
        '6': '佝偻病串珠',
    }
    patient_info['胸廓畸形'] = enum[patient_info['胸廓畸形']]

    enum = {
        '1': '两侧呼吸运动度相等',
        '2': '两侧呼吸运动度不等',
    }
    patient_info['胸部活动度'] = enum[patient_info['胸部活动度']]

    enum = {
        '1': '有干湿性啰音',
        '2': '无干湿性啰音',
    }
    patient_info['啰音'] = enum[patient_info['啰音']]

    enum = {
        '1': '平坦',
        '2': '膨隆',
        '3': '凹陷',
    }
    patient_info['神经腹部'] = enum[patient_info['神经腹部']]

    enum = {
        '1': '移动性浊音',
        '2': '无移动性浊音',
    }
    patient_info['移动性浊音'] = enum[patient_info['移动性浊音']]

    enum = {
        '1': '正常',
        '2': '增强',
        '3': '减弱',
        '4': '消失',
        '5': '活跃',
    }
    patient_info['肠鸣音'] = enum[patient_info['肠鸣音']]

    enum = {
        '1': '无叩痛',
        '2': '叩击痛',
    }
    patient_info['肾区叩痛'] = enum[patient_info['肾区叩痛']]

    enum = {
        '1': '无充盈',
        '2': '充盈',
    }
    patient_info['膀胱充盈'] = enum[patient_info['膀胱充盈']]

    enum = {
        '1': '清醒',
        '2': '嗜睡',
        '3': '昏睡',
        '4': '浅昏迷',
        '5': '中昏迷',
        '6': '深昏迷',
    }
    patient_info['意识状态'] = enum[patient_info['意识状态']]

    enum = {
        '1': '正常',
        '2': '迟钝',
        '3': '不合作',
    }
    patient_info['情感反应'] = enum[patient_info['情感反应']]

    enum = {
        '1': '无',
        '2': '存在',
        '3': '不合作',
    }
    patient_info['妄想'] = enum[patient_info['妄想']]

    enum = {
        '1': '存在',
        '2': '无',
        '3': '不合作',
    }
    patient_info['幻想'] = enum[patient_info['幻想']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '不合作',
    }
    patient_info['自知力'] = enum[patient_info['自知力']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '不合作',
    }
    patient_info['远期记忆'] = enum[patient_info['远期记忆']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '不合作',
    }
    patient_info['近期记忆'] = enum[patient_info['近期记忆']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '无法检查',
    }
    patient_info['计算力'] = enum[patient_info['计算力']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '不合作',
    }
    patient_info['理解判断力'] = enum[patient_info['理解判断力']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '不合作',
    }
    patient_info['地点定向力'] = enum[patient_info['地点定向力']]

    enum = {
        '1': '正常',
        '2': '完全感觉性',
        '3': '不完全运动性',
        '4': '完全运动性',
        '5': '混合型',
        '6': '不完全感觉性失语',
        '7': '命名型失语',
        '8': '完全性失语',
        '9': '传导性失语',
        '10': '皮层下失语',
    }
    patient_info['失语情况'] = enum[patient_info['失语情况']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['左（嗅觉）'] = enum[patient_info['左（嗅觉）']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['右（嗅觉）'] = enum[patient_info['右（嗅觉）']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '失明',
        '4': '不合作',
    }
    patient_info['视力检查(左)'] = enum[patient_info['视力检查(左)']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '失明',
        '4': '不合作',
    }
    patient_info['视力检查(右)'] = enum[patient_info['视力检查(右)']]

    enum = {
        '1': '淡红',
        '2': '苍白',
    }
    patient_info['视乳头颜色'] = enum[patient_info['视乳头颜色']]

    enum = {
        '1': '清',
        '2': '不清',
    }
    patient_info['视乳头边界'] = enum[patient_info['视乳头边界']]

    enum = {
        '1': '存在',
        '2': '消失',
    }
    patient_info['视乳头生理凹陷'] = enum[patient_info['视乳头生理凹陷']]

    enum = {
        '1': '存在',
        '2': '消失',
    }
    patient_info['眼底静脉搏动'] = enum[patient_info['眼底静脉搏动']]

    enum = {
        '1': 'A:V=1:3',
        '2': 'A:V=1:2',
        '3': 'A:V=1:1',
    }
    patient_info['眼底动静脉血管比例'] = enum[patient_info['眼底动静脉血管比例']]

    enum = {
        '1': '自如',
        '2': '受限',
    }
    patient_info['眼球活动（左）'] = enum[patient_info['眼球活动（左）']]

    enum = {
        '1': '自如',
        '2': '受限',
    }
    patient_info['眼球活动（右）'] = enum[patient_info['眼球活动（右）']]

    enum = {
        '1': '无',
        '2': '有',
        '3': '不能配合检查',
    }
    patient_info['复视'] = enum[patient_info['复视']]

    enum = {
        '1': '无',
        '2': '有',
        '3': '不能配合检查',
    }
    patient_info['眼球分离'] = enum[patient_info['眼球分离']]

    enum = {
        '1': '无',
        '2': '有',
        '3': '不能配合检查',
    }
    patient_info['同向凝视'] = enum[patient_info['同向凝视']]

    enum = {
        '1': '灵敏',
        '2': '迟钝',
        '3': '消失',
        '4': '眼疾',
    }
    patient_info['光反应'] = enum[patient_info['光反应']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['调幅反应'] = enum[patient_info['调幅反应']]

    enum = {
        '1': '有力',
        '2': '萎缩',
        '3': '不能配合检查',
    }
    patient_info['咬肌'] = enum[patient_info['咬肌']]

    enum = {
        '1': '有力',
        '2': '萎缩',
        '3': '不能配合检查',
    }
    patient_info['颞肌'] = enum[patient_info['颞肌']]

    enum = {
        '1': '正常',
        '2': '左偏',
        '3': '右偏',
        '4': '受限',
        '5': '不能配合检查',
    }
    patient_info['张口'] = enum[patient_info['张口']]

    enum = {
        '1': '正常',
        '2': '左偏',
        '3': '右偏',
    }
    patient_info['下颌偏斜'] = enum[patient_info['下颌偏斜']]

    enum = {
        '1': '存在',
        '2': '消失',
        '3': '迟钝',
    }
    patient_info['角膜反射（左）'] = enum[patient_info['角膜反射（左）']]

    enum = {
        '1': '存在',
        '2': '消失',
        '3': '迟钝',
    }
    patient_info['角膜反射（右）'] = enum[patient_info['角膜反射（右）']]

    enum = {
        '1': '阴性',
        '2': '阳性',
    }
    patient_info['下颌反射'] = enum[patient_info['下颌反射']]

    enum = {
        '1': '阴性',
        '2': '阳性',
    }
    patient_info['唇反射'] = enum[patient_info['唇反射']]

    enum = {
        '1': '正常',
        '2': '变浅',
        '3': '消失',
    }
    patient_info['神经额纹(左)'] = enum[patient_info['神经额纹(左)']]

    enum = {
        '1': '正常',
        '2': '变浅',
        '3': '消失',
    }
    patient_info['神经额纹(右)'] = enum[patient_info['神经额纹(右)']]

    enum = {
        '1': '完全',
        '2': '不完全',
        '3': '不能',
        '4': '不能配合检查',
    }
    patient_info['左侧闭目'] = enum[patient_info['左侧闭目']]

    enum = {
        '1': '完全',
        '2': '不完全',
        '3': '不能',
        '4': '不能配合检查',
    }
    patient_info['右侧闭目'] = enum[patient_info['右侧闭目']]

    enum = {
        '1': '正常',
        '2': '变浅',
        '3': '消失',
    }
    patient_info['左侧鼻唇沟'] = enum[patient_info['左侧鼻唇沟']]

    enum = {
        '1': '正常',
        '2': '变浅',
        '3': '消失',
    }
    patient_info['右侧鼻唇沟'] = enum[patient_info['右侧鼻唇沟']]

    enum = {
        '1': '无',
        '2': '向左偏斜',
        '3': '向右偏斜',
    }
    patient_info['神经口角'] = enum[patient_info['神经口角']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['舌前2/3味觉（左）'] = enum[patient_info['舌前2/3味觉（左）']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['舌前2/3味觉（右）'] = enum[patient_info['舌前2/3味觉（右）']]

    enum = {
        '1': '无',
        '2': '存在',
        '3': '不合作',
    }
    patient_info['鼓腮漏气'] = enum[patient_info['鼓腮漏气']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '丧失',
        '4': '不合作',
    }
    patient_info['左神经听力'] = enum[patient_info['左神经听力']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '丧失',
        '4': '不合作',
    }
    patient_info['右神经听力'] = enum[patient_info['右神经听力']]

    enum = {
        '1': '居中',
        '2': '偏左',
        '3': '偏右',
        '4': '不能配合检查',
    }
    patient_info['Weber试验'] = enum[patient_info['Weber试验']]

    enum = {
        '1': '骨导 < 气导',
        '2': '骨导 = 气导',
        '3': '骨导 > 气导',
    }
    patient_info['瑞内Rinne实验（左）'] = enum[patient_info['瑞内Rinne实验（左）']]

    enum = {
        '1': '骨导 < 气导',
        '2': '骨导 = 气导',
        '3': '骨导 > 气导',
    }
    patient_info['瑞内Rinne实验(右)'] = enum[patient_info['瑞内Rinne实验(右)']]

    enum = {
        '1': '正常',
        '2': '呛咳',
        '3': '不合作',
    }
    patient_info['神经饮水'] = enum[patient_info['神经饮水']]

    enum = {
        '1': '正常',
        '2': '困难',
        '3': '不合作',
    }
    patient_info['神经吞咽'] = enum[patient_info['神经吞咽']]

    enum = {
        '1': '正常',
        '2': '欠清晰',
        '3': '困难',
        '4': '不合作',
    }
    patient_info['神经发音'] = enum[patient_info['神经发音']]

    enum = {
        '1': '有力',
        '2': '无力',
        '3': '不合作',
    }
    patient_info['左侧软腭'] = enum[patient_info['左侧软腭']]

    enum = {
        '1': '有力',
        '2': '无力',
        '3': '不合作',
    }
    patient_info['右侧软腭'] = enum[patient_info['右侧软腭']]

    enum = {
        '1': '正常',
        '2': '偏左',
        '3': '偏右',
        '4': '张口不合作',
    }
    patient_info['神经悬雍垂'] = enum[patient_info['神经悬雍垂']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['左侧咽反射'] = enum[patient_info['左侧咽反射']]

    enum = {
        '1': '正常',
        '2': '减退',
        '3': '消失',
        '4': '不能配合检查',
    }
    patient_info['右侧咽反射'] = enum[patient_info['右侧咽反射']]

    enum = {
        '1': '有力',
        '2': '无力',
        '3': '不合作',
    }
    patient_info['左侧胸锁乳突肌'] = enum[patient_info['左侧胸锁乳突肌']]

    enum = {
        '1': '有力',
        '2': '无力',
        '3': '不合作',
    }
    patient_info['右侧胸锁乳突肌'] = enum[patient_info['右侧胸锁乳突肌']]

    enum = {
        '1': '有力',
        '2': '无力',
        '3': '不合作',
    }
    patient_info['左侧斜方肌'] = enum[patient_info['左侧斜方肌']]

    enum = {
        '1': '充分',
        '2': '不充分',
    }
    patient_info['伸舌充分'] = enum[patient_info['伸舌充分']]

    enum = {
        '1': '居中',
        '2': '偏左',
        '3': '偏右',
    }
    patient_info['神经伸舌'] = enum[patient_info['神经伸舌']]

    enum = {
        '1': '无',
        '2': '有',
    }
    patient_info['左侧舌肌萎缩'] = enum[patient_info['左侧舌肌萎缩']]

    enum = {
        '1': '无',
        '2': '有',
    }
    patient_info['右侧舌肌萎缩'] = enum[patient_info['右侧舌肌萎缩']]

    enum = {
        '1': '无',
        '2': '有',
    }
    patient_info['左侧肌束颤动'] = enum[patient_info['左侧肌束颤动']]

    enum = {
        '1': '无',
        '2': '有',
    }
    patient_info['右侧肌束颤动'] = enum[patient_info['右侧肌束颤动']]

    enum = {
        '1': '正常',
        '2': '偏瘫步态',
        '3': '慌张步态',
        '4': '剪刀步态',
        '5': '摇摆步态',
        '6': '小脑步态',
        '7': '共济失调步态',
        '8': '不合作',
    }
    patient_info['神经内科步态'] = enum[patient_info['神经内科步态']]

    enum = {
        '1': '正常',
        '2': '萎缩',
        '3': '肥大',
    }
    patient_info['神经肌容积'] = enum[patient_info['神经肌容积']]

    enum = {
        '1': '正常',
        '2': '增高',
        '3': '下降',
    }
    patient_info['左上肢肌张力'] = enum[patient_info['左上肢肌张力']]

    enum = {
        '1': '正常',
        '2': '增高',
        '3': '下降',
    }
    patient_info['右上肢肌张力'] = enum[patient_info['右上肢肌张力']]

    enum = {
        '1': '正常',
        '2': '增高',
        '3': '下降',
    }
    patient_info['左下肢肌张力'] = enum[patient_info['左下肢肌张力']]

    enum = {
        '1': '正常',
        '2': '增高',
        '3': '下降',
    }
    patient_info['右下肢肌张力'] = enum[patient_info['右下肢肌张力']]

    enum = {
        '1': '0',
        '2': 'I',
        '3': 'II',
        '4': 'III',
        '5': 'IV',
        '6': 'V',
    }
    patient_info['左下肢肌力'] = enum[patient_info['左下肢肌力']]

    enum = {
        '1': '0',
        '2': 'I',
        '3': 'II',
        '4': 'III',
        '5': 'IV',
        '6': 'V',
    }
    patient_info['右上肢肌力'] = enum[patient_info['右上肢肌力']]

    enum = {
        '1': '0',
        '2': 'I',
        '3': 'II',
        '4': 'III',
        '5': 'IV',
        '6': 'V',
    }
    patient_info['右下肢肌力'] = enum[patient_info['右下肢肌力']]

    enum = {
        '1': '0',
        '2': 'I',
        '3': 'II',
        '4': 'III',
        '5': 'IV',
        '6': 'V',
    }
    patient_info['左上肢肌力'] = enum[patient_info['左上肢肌力']]

    enum = {
        '1': '正常',
        '2': '欠稳准',
        '3': '不合作',
    }
    patient_info['左侧指鼻试验'] = enum[patient_info['左侧指鼻试验']]

    enum = {
        '1': '正常',
        '2': '欠稳准',
        '3': '不合作',
    }
    patient_info['右侧指鼻试验'] = enum[patient_info['右侧指鼻试验']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['左侧轮替'] = enum[patient_info['左侧轮替']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['右侧轮替'] = enum[patient_info['右侧轮替']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['左侧反跳实验'] = enum[patient_info['左侧反跳实验']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['右侧反跳实验'] = enum[patient_info['右侧反跳实验']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['左侧跟膝胫实验'] = enum[patient_info['左侧跟膝胫实验']]

    enum = {
        '1': '正常',
        '2': '笨拙',
        '3': '不合作',
    }
    patient_info['右侧跟膝胫实验'] = enum[patient_info['右侧跟膝胫实验']]

    enum = {
        '1': '阴性',
        '2': '阳性',
        '3': '不合作',
    }
    patient_info['神经1昂伯氏征'] = enum[patient_info['神经1昂伯氏征']]

    enum = {
        '1': '无',
        '2': '有',
    }
    patient_info['不自主动'] = enum[patient_info['不自主动']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['左侧图形觉'] = enum[patient_info['左侧图形觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['右侧图形觉'] = enum[patient_info['右侧图形觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['左侧实体觉'] = enum[patient_info['左侧实体觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['右侧实体觉'] = enum[patient_info['右侧实体觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['左侧两点辨别觉'] = enum[patient_info['左侧两点辨别觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['右侧两点辨别觉'] = enum[patient_info['右侧两点辨别觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['左侧皮肤定位觉'] = enum[patient_info['左侧皮肤定位觉']]

    enum = {
        '1': '正常',
        '2': '异常',
        '3': '不合作',
    }
    patient_info['右侧皮肤定位觉'] = enum[patient_info['右侧皮肤定位觉']]

    enum = {
        '1': '-<',
        '2': '+<',
        '3': '++',
        '4': '±',
    }
    patient_info['--'] = enum[patient_info['--']]

    enum = {
        '1': '-<',
        '2': '±',
        '3': '++',
        '4': '+++',
        '5': '++++',
        '6': '+++++',
    }
    patient_info['-.'] = enum[patient_info['-.']]

    enum = {
        '1': '阴性',
        '2': '弱阳性',
        '3': '阳性',
        '4': '不能配合检查',
    }
    patient_info['颈强直（神外）'] = enum[patient_info['颈强直（神外）']]

    enum = {
        '1': '阴性',
        '2': '弱阳性',
        '3': '阳性',
        '4': '不能配合检查',
    }
    patient_info['Brudzinski征'] = enum[patient_info['Brudzinski征']]

    enum = {
        '1': '阴性',
        '2': '弱阳性',
        '3': '阳性',
        '4': '不能配合检查',
    }
    patient_info['Kernig征'] = enum[patient_info['Kernig征']]

    enum = {
        '1': '阴性',
        '2': '弱阳性',
        '3': '阳性',
        '4': '不能配合检查',
    }
    patient_info['神经干牵引征'] = enum[patient_info['神经干牵引征']]

    # enum = {
    #     '1': '阴性',
    #     '2': '弱阳性',
    #     '3': '阳性',
    #     '4': '不能配合检查',
    # }
    # patient_info['左侧拉塞格征'] = enum[patient_info['左侧拉塞格征']]

    enum = {
        '1': '阴性',
        '2': '弱阳性',
        '3': '阳性',
        '4': '不能配合检查',
    }
    patient_info['右侧拉塞格征'] = enum[patient_info['右侧拉塞格征']]

    enum = {
        '1': '住院医师',
        '2': '主治医师',
        '3': '副主任医师',
        '4': '主任医师',
    }
    patient_info['住院医师'] = enum[patient_info['住院医师']]

    enum = {
        '1': '副主任医师',
        '2': '主任医师',
    }
    patient_info['签名'] = enum[patient_info['签名']]


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    # parse_xml_use_elementtree("/Users/gaoyanliang/nsyy/apoplexy/test.xml")
    # parse_xml_test("/Users/gaoyanliang/nsyy/apoplexy/test.xml")
    # parse_xml_document("/Users/gaoyanliang/nsyy/apoplexy/test.xml")

    # patient_info = parse_patient_subdocuments("/Users/gaoyanliang/nsyy/apoplexy/test.xml")
    patient_info = parse_patient_document("/Users/gaoyanliang/nsyy/apoplexy/test.xml")


import traceback

import xml.etree.ElementTree as ET
import json

from gylmodules import global_tools
from gylmodules.medical_record_analysis.anew_his_record import parse_new_his_xml
from gylmodules.medical_record_analysis.anew_his_record.build_cda import new_build_cda
from gylmodules.medical_record_analysis.parse_server import clean_dict


def simplify_node(node):
    children = list(node)

    # 没有子节点
    if not children:
        text = (node.text or '').strip()
        return text if text else None

    # 有子节点
    simplified = {}
    value_parts = []

    if node.text and node.text.strip():
        value_parts.append(node.text.strip())

    for child in children:
        child_name = child.get('name')
        simplified[child_name] = simplify_node(child)
        if isinstance(simplified[child_name], str) and simplified[child_name].strip():
            value_parts.append(f"{child_name} {simplified[child_name].strip()}")

        if child.tail and child.tail.strip():
            value_parts.append(child.tail.strip())

    simplified['value'] = ' '.join(value_parts).strip()
    return simplified

def parse_xml_simplified(xml_string):
    root = ET.fromstring(xml_string)
    result = {}

    for node in root:
        if node.tag != "node":
            continue
        name = node.get("name")
        simplified = simplify_node(node)
        result[name] = simplified

    return result


# if __name__ == "__main__":
#     xml_string = """<你的XML内容放在这里>"""  # 请将整个XML字符串粘贴到这里
#     xml_string = """<?xml version="1.0"  encoding="utf-8"?>
# <doc>
#     <node name="入院科室" code="ZSK_RuYuanKS">神经介入科一病区</node>第
#     <node name="住院次数" code="ZSK_ZhuYuanCS">2</node>次入院记录入院情况:
#     <node name="入院情况" code="ZSK_RuYuanQingK">一般</node>过敏史:
#     <node name="过敏史" code="ZSK_GuoMinShi">无药物及食物过敏史</node>姓名:
#     <node name="患者姓名" code="ZSK_HuanZheXM">侯强</node>性别:
#     <node name="性别" code="ZSK_XingBie">男</node>年龄:
#     <node name="年龄" code="ZSK_NianLing">43岁</node>籍贯:
#     <node name="患者籍贯" code="ZSK_HuanZheJG">河南省南阳市</node>出生年月:
#     <node name="出生日期" code="ZSK_ChuShengRQ">1982-02-17</node>职业:
#     <node name="职业" code="ZSK_ZhiYe">其他</node>婚姻:
#     <node name="婚姻状况" code="ZSK_HunYinZK">已婚</node>民族:
#     <node name="民族" code="ZSK_MinZu">汉族</node>身份证号:
#     <node name="患者身份证件号码" code="ZSK_HuanZheSFZJHM">412822198202171171</node>工作单位:
#     <node name="工作单位名称" code="ZSK_GongZuoDWMC">-</node>邮编:
#     <node name="现住址邮编" code="ZSK_XianZhuZYB">463700</node>入院时间:
#     <node name="入院日期" code="ZSK_RuYuanRQ">2025-05-27 22:00</node>现住址:
#     <node name="家庭地址" code="ZSK_JiaTingDZ">河南省驻马店市泌阳县双庙乡桑盘村委小候庄</node>病史采集时间:
#     <node name="N病史采集时间" code="NBSCJSJ">2025-05-27 22:01</node>联系人姓名:
#     <node name="联系人姓名" code="ZSK_LianXiRXM">袁丽金</node>与患者关系:
#     <node name="与患者关系" code="ZSK_YuHuanZGX">配偶</node>记录时间:
#     <node name="记录时间" code="ZSK_JiLuSJ">2025-05-27 23:30</node>联系人电话:
#     <node name="联系人电话号码" code="ZSK_LianXiRDHHM">18739930368</node>患者电话:
#     <node name="联系电话" code="ZSK_LianXiDH">15565961999</node>病史陈述者:
#     <node name="病史陈述者" code="ZSK_BingShiCSZ">患者本人</node>文化程度:
#     <node name="文化程度" code="ZSK_WenHuaCD">初中</node>居住状况:
#     <node name="N居住状况" code="NJZZK">与配偶和/或子女同住</node>可靠程度:
#     <node name="病史可靠程度" code="ZSK_BingShiKKCD">可靠</node>  主 诉:
#     <node name="主诉" code="ZSK_ZhuSu">突发头痛1天余</node>。  现病史:
#     <node name="现病史">1天余前患者在家休息时突发头痛，伴恶心，无呕吐，无意识障碍，无肢体抽搐及大小便失禁，症状持续不缓解，遂就诊于当地医院，完善头颅磁共振提示右侧颞叶、右侧额顶叶脑梗塞，具体治疗不详，7小时余前出现言语不清，左下肢无力，行走乏力，为求进一步诊治来我院，查头颅CT排除颅内出血，以&quot;急性脑梗死&quot;为诊断收入我科。发病来，患者神志清，精神差，饮食睡眠可，大小便正常，体重无明显变化。  患&quot;高血压&quot;病史7年，血压最高达190/110mmHg，平时口服&quot;缬沙坦胶囊 80mg/粒 每次1片，每天1次&quot;&quot;硝苯地平缓释片 20mg/片，每次1片，每天2次&quot;降压治疗，血压控制在140/90mmHg上下，无特殊不适。  患&quot;脑梗死&quot;病史4年，4年前因“脑梗死”于我院住院治疗，未遗留明显后遗症，详见上次病历。</node>  既往史：
#     <node name="既往史">
#         <node name="N有无高血压史" code="NYWGXYS">平素身体健康状况一般，无“冠心病”、“糖尿病”等其它慢性病史。无“肝炎”、“结核”等慢性传染病史；无重大外伤、手术史，无药物、食物过敏史。曾在泌阳县献过2次血，具体情况不详，无献血史，预防接种随当地社会进行。</node>
#     </node>  个人史：
#     <node name="个人史" code="ZSK_GeRenS">出生于原籍，常住本地，否认疫区居住史，无粉尘放射性物质接触史，无毒品接触史，否认性病及冶游史，无吸烟史，饮酒20年，平均每天约250g，右利手。</node>  婚育史：
#     <node name="婚育史" code="NHYS">22岁结婚，配偶身体一般，夫妻关系和睦，育有2子2女。</node>  家族史：
#     <node name="家族史" code="ZSK_JiaZuS">
#         <node name="身体健康家族成员" code="STJKJZCY">父母已故，死因不详。1姐1哥均体健，子女均体健，无家族慢性传染性及遗传性疾病史。</node>
#     </node>体格检查
#     <node name="体格检查_体征">  T:
#         <node name="体温" code="ZSK_TiWen">36.8</node>℃ P:
#         <node name="脉搏" code="ZSK_MaiBo">76</node>次/分 R:
#         <node name="呼吸频率" code="ZSK_HuXiPL">18</node>次/分 BP:
#         <node name="收缩压" code="ZSK_ShouSuoY">150</node>/
#         <node name="舒张压" code="ZSK_ShuZhangY">100</node>mmHg   W:
#         <node name="体重" code="ZSK_TiZhong">70</node>kg H：
#         <node name="身高" code="ZSK_ShenGao">170</node>cm
#     </node>
#     <node name="体格检查">  一般情况：发育
#         <node name="N发育" code="NFY">正常</node>,营养
#         <node name="N营养" code="NYY">良好</node>，体型
#         <node name="N体型" code="NTX">匀称</node>，
#         <node name="N体位" code="NTW">自主</node>体位，
#         <node name="N面容" code="NMR">正常面容</node>，表情
#         <node name="N表情" code="NBQ">自如</node>,查体
#         <node name="查体" code="CT">合作</node>。  皮肤黏膜：全身
#         <node name="全身" code="QS">正常</node>，
#         <node name="皮下" code="PX">无皮疹、皮下出血、皮下结节、瘢痕</node>，
#         <node name="N毛发分布" code="NMFFB">毛发分布正常</node>，皮下
#         <node name="皮下水肿" code="PXSZ">无水肿</node>，
#         <node name="有无肝掌及蜘蛛痣" code="YWGZJZZZ">无肝掌、蜘蛛痣</node>。  淋巴结：
#         <node name="淋巴结" code="LBJ">全身浅表淋巴结未触及</node>。  头颅五官：头颅
#         <node name="头颅畸形" code="ZSK_TouLuJX">无畸形、压痛、包块</node>。头发
#         <node name="头发" code="TF">疏密、色泽、分布</node>
#         <node name="...">正常</node>。
#         <node name="眉毛情况" code="MMQK">眉毛无脱落</node>,
#         <node name="眉毛是否倒睫" code="MMSFDJ">无倒睫</node>，眼脸
#         <node name="眼睑情况" code="YJQK">无水肿、下垂、挛缩</node>。眼球
#         <node name="眼球情况" code="YQQK">无凸出、下陷、震颤、斜视</node>。结膜
#         <node name="结膜" code="ZSK_JieMo">无充血、水肿、出血、苍白、滤泡</node>。巩膜
#         <node name="巩膜" code="ZSK_GongMo">无黄染、斑点</node>。角膜
#         <node name="角膜" code="JM">无云翳、白斑、软化、溃疡、瘢痕、反射、色素环</node>。耳廓
#         <node name="耳廓情况" code="EKQK">无畸形</node>。乳突
#         <node name="乳突有无压痛" code="RTYWYT">无压痛</node>。
#         <node name="外耳道无分泌物" code="WEDWFMW">外耳道无分泌物</node>。听力
#         <node name="听力粗测" code="ZSK_TingLiCC">正常</node>。鼻
#         <node name="鼻腔" code="BQ">无畸形</node>,鼻中隔
#         <node name="鼻中隔" code="BZG">正常</node>,鼻甲
#         <node name="下鼻甲情况" code="XBJQK">正常</node>，鼻窦
#         <node name="鼻窦压痛情况描述" code="BDYTQKMS">无压痛</node>。唇
#         <node name="口唇" code="KC">无畸形</node>,牙龈
#         <node name="牙龈" code="ZSK_YaZuo">无肿胀、溃疡、溢脓、出血、铅线</node>。舌
#         <node name="舌" code="S1">无溃疡、震颤、偏斜</node>。口唇黏膜
#         <node name="口唇黏膜" code="KCNM">无斑疹、溃疡、出血点</node>。悬雍垂位置
#         <node name="悬雍垂" code="XYC">居中</node>。扁桃体
#         <node name="扁桃体" code="ZSK_BianTaoT">无肿大</node>，声音
#         <node name="声音描述" code="SYMS">正常</node>。  颈部:颈
#         <node name="颈部" code="JB">软</node>、
#         <node name="颈部强直" code="ZSK_JingBuQZ">无抵抗</node>。颈动脉
#         <node name="颈动脉" code="ZSK_JingDongM">搏动正常</node>。颈动脉血管
#         <node name="颈动脉血管" code="JDMXG">无杂音</node>，颈静脉
#         <node name="颈静脉" code="ZSK_JingJingM">无怒张</node>。气管
#         <node name="气管位置" code="ZSK_QiGuanWZ">居中</node>。肝颈静脉回流征
#         <node name="肝颈静脉回流征" code="ZSK_GanJingJMHLZ">阴性</node>。甲状腺
#         <node name="甲状腺" code="ZSK_JiaZhuangX">无肿大</node>、
#         <node name="甲状腺压痛" code="JZXYT">无压痛、震颤、血管杂音</node>。  胸部：胸廓
#         <node name="胸部对称" code="XBDC">正常对称</node>，
#         <node name="胸部形态" code="XBXT">无局部隆起、塌陷、压痛</node>，呼吸运动
#         <node name="胸部呼吸运动" code="XBHXYD">正常</node>。乳房
#         <node name="乳房对称性" code="ZSK_RuFangDCX">正常对称</node>、
#         <node name="乳房情况" code="RFQK">无包块、红肿、压痛</node>,
#         <node name="左、右">
#             <node name="左右选项" code="ZYXX">左、右</node>
#         </node>乳头
#         <node name="乳头分泌物" code="ZSK_RuTouFMW">无异常分泌物</node>。胸壁
#         <node name="胸壁" code="XB">无静脉曲张、皮下气肿</node>，胸骨
#         <node name="有无" code="YW">无</node>叩痛。  肺部：呼吸运动
#         <node name="胸部呼吸运动" code="XBHXYD">正常</node>，
#         <node name="呼吸评估" code="HXPG">经鼻呼吸（正常呼吸）</node>，肋间隙
#         <node name="肋间隙" code="ZSK_LeiJianX">正常</node>，语颤
#         <node name="语颤" code="YC">正常</node>，
#         <node name="胸膜摩擦感" code="ZSK_XiongMoMCG">无胸膜摩擦感</node>，
#         <node name="捻发感" code="ZSK_NianFaG">无皮下捻发感</node>，叩诊
#         <node name="叩诊音" code="ZSK_ZuoZhenY">清音</node>，
#         <node name="叩诊双肺部位" code="KZSFBW">双肺</node>
#         <node name="叩诊呼吸音" code="KZHXY">呼吸音清晰</node>、
#         <node name="干湿性啰音" code="GSXLY">无干湿性啰音</node>，
#         <node name="胸膜摩擦音" code="ZSK_XiongMoMCY">无胸膜摩擦音</node>，语音共振
#         <node name="语音共振" code="ZSK_YuYinGZ">正常</node>。  心脏：
#         <node name="心前区隆起" code="ZSK_XinQianQLQ">心前区无隆起</node>，心尖搏动
#         <node name="心尖搏动情况" code="XJBDQK">位置正常</node>，心浊音界
#         <node name="心浊音界是否正常" code="XZYJSFZC">正常</node>，
#         <node name="心前区异常搏动" code="ZSK_XinQianQYCBD">心前区无异常搏动</node>，心率
#         <node name="心率" code="ZSK_XinLv">76</node>次/分，
#         <node name="心律" code="ZSK_XL">心律整齐</node>，心脉率
#         <node name="心脉率" code="XML">一致</node>，
#         <node name="各瓣膜闻及病理性杂音" code="ZSK_GeBanMWJBLXZY">未闻及病理性杂音</node>，
#         <node name="心包摩擦音" code="ZSK_XinBaoMCY">无心包摩擦音</node>。周围血管搏动
#         <node name="血管搏动" code="XGBD">正常</node>，
#         <node name="毛细血管搏动" code="MXXGBD">无毛细血管搏动</node>，
#         <node name="异常血管征" code="YCXGZ">无异常血管征</node>，
#         <node name="Duroziez 双重杂音" code="DUROZIEZSZ">无Duroziez 双重杂音</node>，
#         <node name="脉搏短绌" code="MBDC">无脉搏短绌</node>，
#         <node name="有无奇脉" code="YWQM">无奇脉</node>，
#         <node name="交替脉" code="JTM">无交替脉</node>，
#         <node name="枪击音" code="QJY">无枪击音</node>，
#         <node name="水冲脉" code="SCM">无水冲脉</node>，
#         <node name="颈动脉异常搏动" code="ZSK_JingDongMYCBD">无动脉异常搏动</node>。  腹部：腹
#         <node name="腹部形态" code="ZSK_FuBuXT">平坦</node>，
#         <node name="腹壁静脉曲张" code="FBJMQZ">无腹壁静脉曲张</node>，
#         <node name="胃肠型" code="WCX">无胃肠型</node>，
#         <node name="有/无蠕动波" code="YWRDB">无蠕动波</node>，腹式呼吸
#         <node name="腹式呼吸" code="ZSK_FuShiHW">存在</node>。脐部
#         <node name="脐情况" code="QQK">正常</node>、
#         <node name="脐有/无分泌物" code="QYWFMW">无分泌物</node>。腹部
#         <node name="腹部压痛情况" code="FBYTQK">无压痛、反跳痛</node>。腹部
#         <node name="腹部柔软情况" code="FBRRQK">全腹柔软</node>、
#         <node name="包块" code="ZSK_BaoKuai">腹部无包块</node>。肝脏肋边缘下
#         <node name="肝脏肋边缘下" code="GZLBYX">未触及</node>，脾脏肋边缘下
#         <node name="脾脏肋边缘下" code="PZLBYX">未触及</node>，Murphy氏征
#         <node name="Murphy征" code="ZSK_MURPHYZ">阴性</node>，
#         <node name="左右侧" code="ZYC">双侧</node>
#         <node name="双肾区叩击痛" code="ZSK_ShuangShenQKJT">肾区无叩击痛</node>，
#         <node name="输尿管压痛点" code="SNGYTD">无输尿管压痛点</node>，
#         <node name="移动性浊音" code="ZSK_YiDongXZY">阴性移动性浊音</node>，
#         <node name="液波震颤" code="ZSK_YeBoZC">无液波震颤</node>，肠鸣音
#         <node name="肠鸣音" code="ZSK_ChangMingY">正常</node>、
#         <node name="频次">5</node>次/分,
#         <node name="肠鸣音过水声" code="CMYGSS">无</node>过水声，
#         <node name="振水音及血管杂音" code="ZSK_ZhenShuiYJXGZY">无血管杂音</node>。  肛门及外生殖器：肛门及外生殖器
#         <node name="肛门及外生殖器" code="GMJWSZQ">未查</node>。  脊柱四肢：脊柱活动
#         <node name="脊柱四肢活动" code="JZSZHD">正常</node>，
#         <node name="脊柱变形" code="ZSK_JiZhuBX">无畸形</node>，棘突
#         <node name="棘突病变" code="ZSK_JiTuBB">无压痛、叩击痛</node>，四肢
#         <node name="四肢活动" code="ZSK_SiZhiHD">活动自如</node>，四肢
#         <node name="四肢异常" code="SZYC">无畸形、下肢静脉曲张、杵状指（趾）、水肿、骨折</node>。关节
#         <node name="四肢关节" code="SZGJ">无红肿、疼痛、压痛、积液、活动度受限、畸形</node>，肌肉
#         <node name="四肢肌肉" code="SZJR">无萎缩</node>。  神经系统：详见专科检查。
#     </node>神经系统查体  一般情况   意识
#     <node name="意识" code="YS">清醒</node>，语言
#     <node name="语言" code="ZSK_YuYan">不清</node>，记忆力
#     <node name="记忆力" code="ZSK_JiYiL">正常</node>，理解力
#     <node name="理解判断" code="ZSK_LiJiePD">无异常</node>，计算力
#     <node name="计算力" code="JSL1">正常</node>，判断力
#     <node name="理解判断" code="ZSK_LiJiePD">无异常</node>，定向力
#     <node name="定向" code="ZSK_DingXiang">正确</node>，
#     <node name="左右利手" code="ZYLS">右利手</node>。  颅神经检查  嗅神经：粗测嗅觉：左侧
#     <node name="粗测嗅觉" code="CCXJ">正常</node>，右侧
#     <node name="粗测嗅觉" code="CCXJ">正常</node>。   视神经：粗测视力：左侧
#     <node name="粗测视力" code="CCSL">正常</node>，右侧
#     <node name="粗测视力" code="CCSL">正常</node>，
#     <node name="粗测视力双眼" code="CCSLSY">双眼</node>视野
#     <node name="粗测视力视野缺损" code="CCSLSYQS">无</node>缺损。   动眼、滑车、外展神经：
#     <node name="动眼、滑车、外展神经双眼" code="DYHCWZSJSY">双眼</node>
#     <node name="动眼、滑车、外展神经上睑下垂" code="DYHCWZSJSJ">无上睑下垂</node>，眼球位置
#     <node name="动眼、滑车、外展神经眼球位置" code="DYHCWZSJYQ">居中</node>，
#     <node name="动眼、滑车、外展神经运动充分" code="DYHCWZSJYD">各方向</node>运动充分，
#     <node name="动眼、滑车、外展神经复视" code="DYHCWZSJFS">无复视</node>，
#     <node name="动眼、滑车、外展神经眼震，瞳孔等大等圆" code="DYHCWZSJYZ">无</node>眼震，瞳孔等大等圆，直径左侧
#     <node name="左侧">2.5</node>mm，右侧
#     <node name="右侧">2.5</node>mm，直接、间接对光反射
#     <node name="动眼、滑车、外展神经直接、间接对光反射" code="DYHCWZSJZJ">灵敏</node>，调节反射
#     <node name="动眼、滑车、外展神经调节反射" code="DYHCWZSJDJ">正常</node>。  三叉神经：
#     <node name="三叉神经描述">感觉无异常，咬肌：有力，颞肌：有力，张口：正常，下颌偏斜：无，角膜反射：左：存在,右：存在，下颌反射：阴性，唇反射：阴性。</node>  面神经：
#     <node name="面神经">额纹：左:正常,右:正常，闭目：左：完全，右：完全，鼻唇沟：左：变浅，右：正常，示齿口角偏向：向右偏斜，鼓腮漏气：存在，舌前2/3味觉 左：未查，右：未查。</node>  位听神经：
#     <node name="位听神经">听力 左：正常，右：正常，韦伯(Weber)实验：居中；瑞内Rinne实验 左：骨导&amp;lt;气导，右：骨导&amp;lt;气导。</node>   舌咽、迷走神经：
#     <node name="舌咽、迷走神经">饮水：正常，吞咽：正常，发音：欠清晰，软腭上提 左：有力，右：有力。悬雍垂：正常 ，咽反射 左：正常，右：正常。</node>  副神经：
#     <node name="副神经">双侧胸锁乳突肌、斜方肌无萎缩，转颈、耸肩有力</node>。   舌下神经：
#     <node name="舌下神经">伸舌
#         <node name="舌下神经伸舌" code="SXSJSS">左偏</node>，舌尖
#         <node name="位置居中" code="WZJZ">位置左偏</node>，
#         <node name="有无" code="YW">无</node>舌肌萎缩及肌束震颤。
#     </node>   运动系统检查
#     <node name="运动系统检查">     步态：偏瘫步态；肌容积(萎缩或肥大）：正常；肌束颤动部位：无。肌张力 左上肢：正常，左下肢：下降，右上肢：正常，右下肢：正常；肌力(0-V) 左上肢：Ⅴ，左下肢：Ⅳ，右上肢：Ⅴ，右下肢：Ⅴ。     指鼻实验 左：正常，右：正常；轮替 运动左：正常，右：正常；反跳实验 左：正常 右：正常；跟膝胫实验 左：正常，右：正常；昂伯氏(Romberg)征：正常；不自主动：无。</node>  感觉系统检查
#     <node name="感觉系统检查">      痛温觉障碍部位：无，触觉障碍部位：无；运动觉障碍部位：无；震动觉障碍部位：无。      图形觉 左：正常，右：正常；实体觉 左：正常，右：正常：两点辨别觉 左：正常， 右：正常；皮肤定位觉 左：正常，右：正常。</node>反射右左反射右左桡骨膜
#     <node name="反射" code="ZSK_FanShe">++</node>
#     <node name="反射" code="ZSK_FanShe">++</node>Babinski征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">+</node>肱二头肌
#     <node name="反射" code="ZSK_FanShe">++</node>
#     <node name="反射" code="ZSK_FanShe">++</node>Chaddock征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">+</node>肱三头肌
#     <node name="反射" code="ZSK_FanShe">++</node>
#     <node name="反射" code="ZSK_FanShe">++</node>Pussep征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">-</node>腹壁上
#     <node name="反射" code="ZSK_FanShe">+</node>
#     <node name="反射" code="ZSK_FanShe">+</node>Oppenheim征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">-</node>中
#     <node name="反射" code="ZSK_FanShe">+</node>
#     <node name="反射" code="ZSK_FanShe">+</node>Gordon征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">-</node>下
#     <node name="反射" code="ZSK_FanShe">+</node>
#     <node name="反射" code="ZSK_FanShe">+</node>Hoffmann征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">-</node>膝腱
#     <node name="反射" code="ZSK_FanShe">++</node>
#     <node name="反射" code="ZSK_FanShe">++</node>Rossolimo征
#     <node name="反射" code="ZSK_FanShe">-</node>
#     <node name="反射" code="ZSK_FanShe">-</node>跟腱
#     <node name="反射" code="ZSK_FanShe">++</node>
#     <node name="反射" code="ZSK_FanShe">++</node>注：腱反射阵挛++++，亢进+++，正常++，减弱+，可疑±，消失-；其余 存在+，消失-  髌阵挛:
#     <node name="髌阵挛">左侧
#         <node name="阴性" code="YX">阴性</node>，右侧
#         <node name="阴性" code="YX">阴性</node>；踝阵挛，左侧
#         <node name="阴性" code="YX">阴性</node>，右侧
#         <node name="阴性" code="YX">阴性</node>。
#     </node>  额叶释放征：
#     <node name="额叶释放征">唇反射
#         <node name="阴性" code="YX">阴性</node>，下颌反射
#         <node name="阴性" code="YX">阴性</node>；掌颏反射左侧
#         <node name="阴性" code="YX">阴性</node>，右侧
#         <node name="阴性" code="YX">阴性</node>；强握反射
#         <node name="阴性" code="YX">阴性</node>。
#     </node>  自主神经检查
#     <node name="自主神经检查">皮肤色泽
#         <node name="皮肤颜色" code="ZSK_PiFuYS">正常</node>，
#         <node name="有无" code="YW">无</node>干燥，毛发分布
#         <node name="毛发分布" code="ZSK_MaoFaFB">正常</node>，指（趾）甲
#         <node name="指甲" code="ZSK_ZhiJia">正常，有光泽</node>，泌汗
#         <node name="出汗" code="ZSK_ChuHan">无</node>，皮肤划痕试验
#         <node name="阴性" code="YX">阴性</node>，大小便
#         <node name="大便" code="ZSK_DaBian">正常</node>。
#     </node>  脑膜刺激征
#     <node name="脑膜刺激征">颈
#         <node name="颈部" code="JB">软</node>，
#         <node name="有无" code="YW">无</node>抵抗，Kernig征左侧
#         <node name="Kernig征" code="KERNIGZ">阴性</node>，右侧
#         <node name="Kernig征" code="KERNIGZ">阴性</node>，Brudzinski征
#         <node name="Brudzinski征" code="BRUDZINSKI">阴性</node>。
#     </node>  神经干牵拉试验
#     <node name="神经干牵拉试验">Lasegue征左侧
#         <node name="Lasegue征" code="LASEGUEZ">阴性</node>，右侧
#         <node name="Lasegue征" code="LASEGUEZ">阴性</node>。       格拉斯哥昏迷评分：15分（睁眼4分，语言5分，运动6分）；NIHSS评分：3分（面瘫1分，左下肢运动1分，构音1分）；MRS分级：2级。
#     </node>辅助检查
#     <node name="辅助检查">头颅磁共振示：DWI示：右侧颞叶、右侧额顶叶新鲜脑梗塞，右侧基底节区、左侧侧脑室旁、右侧枕顶叶多发脑梗塞、脑软化灶，脑白质脱髓鞘、脑萎缩；MRA：右侧颈内动脉虹吸段、左侧大脑后动脉P2段狭窄，右侧颈内动脉显影淡，右侧大脑中动脉未见显示（闭塞？）（2025-5-27 泌阳县中医院）。头胸CT（2025-5-27 本院）：</node>初步诊断
#     <node name="初步诊断" code="ZSK_ChuBuZD">1.急性脑梗死（右侧颈内动脉系统）    TOAST分型：大动脉粥样硬化型；2.右侧大脑中动脉闭塞；3.高血压3级 很高危组</node>
#     <node name="医师签名" code="ZSK_YiShiQM">
#         <node name="CA签名" code="5356097">住院医师:</node>
#     </node>
#     <node name="医师签名" code="ZSK_YiShiQM"></node>
# </doc>"""
#
#     result = parse_xml_simplified(xml_string)
#     print(json.dumps(result, ensure_ascii=False, indent=4))




if __name__ == "__main__":
    sql = """select wb2.wenjiannr ,wb.binglimc, wb.binglijlid, wb.bingrenid, wb.bingrenzyid from df_bingli.ws_binglijl wb
        join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid
        and wb.zuofeibz ='0' where wb.binglimc like '%入出院记录%' and jilusj > '2025-01-01 00:00:00' order by jilusj desc LIMIT 10
    """
    records = global_tools.call_new_his_pg(sql)
    print('病历数量： ', len(records))

    for record in records:
        cur_record = record.get('wenjiannr')
        record.pop('wenjiannr')
        patient_info = parse_new_his_xml.main_parse_func(cur_record, True)
        patient_info = clean_dict(patient_info)
        patient_info['bingrenzyid'] = record.get('bingrenzyid')
        patient_info['pat_no'] = record.get('bingrenid')
        patient_info['file_name'] = record.get('binglimc')
        try:
            if record.get('binglimc').__contains__("入出院记录"):
                cda = new_build_cda.assembling_cda_record(patient_info, 3)
        except Exception as e:
            print('异常二', record.get('binglijlid'), traceback.print_exc())
            print(patient_info)

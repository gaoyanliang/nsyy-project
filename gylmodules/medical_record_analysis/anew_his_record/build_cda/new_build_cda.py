import json
import traceback
from datetime import datetime
from xml.dom.minidom import parseString

import requests

from gylmodules import global_tools
from gylmodules.medical_record_analysis.anew_his_record.build_cda import new_admission_cda, new_discharge_cda, \
    new_hours24_discharge_cda, new_progress_note_cda, new_daily_medical_record_cda, new_inspection_record_cda, \
    new_difficult_cases_record_cda, new_handover_record_cda, new_transfer_record_cda, new_stage_summary_cda, \
    new_rescue_record_cda, new_consultation_record_cda, new_preoperative_summary_cda, preoperative_discussion_cda, \
    obituary_cda, discussion_record_death_cases_cda
from gylmodules.medical_record_analysis.xml_const import const as xml_const


def prettify_xml(xml_string):
    """
    格式化 xml
    :param xml_string:
    :return:
    """
    dom = parseString(xml_string)
    pretty_xml_as_string = dom.toprettyxml()
    # Remove extra blank lines
    lines = pretty_xml_as_string.split('\n')
    non_empty_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_empty_lines)


def query_pat_info_by_pat_no(data):
    bingrenzyid = data.get('bingrenzyid')
    jiuzhenid = data.get('jiuzhenid')

    if not jiuzhenid and not bingrenzyid:
        print(datetime.now(), '就诊id 和 患者住院id不能同时为空，数据异常，无法查询患者信息')
        return data
    query_sql = ''
    if not bingrenzyid:
        query_sql = f"""
            select zj.bingrenid 病人ID, zj.xingming 姓名, zj.xingbiemc 性别, zj.nianling 年龄, gb.shenfenzh 身份证号, 
                    gb.chushengrq 出生日期, coalesce(zj.gongzuodw,gb.gongzuodw) 工作单位, coalesce(zj.danweidh,gb.danweidh) 单位电话,
                    gb.danweiyb 单位邮编, coalesce(zj.xianzhuzhidh,gb.xianzhuzhidh) 现住址电话,   
                    gb.xianzhuzhiyb 现住址邮编, gb.xuexingmc 血型名称, gb.hunyinmc 婚姻状况, gb.zhiyemc 职业, gb.guojimc 国籍, gb.minzumc 民族,    
                    gb.lianxiren 联系人, gb.guanxidm 关系, gb.lianxirdz 联系人地址, gb.lianxirdh 联系人电话, gb.lianxiryb 联系人邮编, 
                     zj.jiuzhenksid 当前科室id,zj.jiuzhenysid 门诊医师, zj.shouzhenysid 收治医师,zj.jiuzhenksmc    当前科室名称,  
                     zj.jiuzhenysxm 门诊医师姓名,zj.shouzhenysxm 收治医师姓名, zj.jiuzhenksmc 当前科室名称,
                    gb.hukoudzyb 户口地址邮编, zj.xingbiedm 性别代码, gb.xuexingdm 血型代码, gb.hunyindm 婚姻代码, gb.zhiyedm 职业代码,
                    gb.guojidm 国籍代码, gb.minzudm 民族代码, gb.xianzhuzhidm_sheng  现住址省份, gb.xianzhuzhimc_sheng 现住址省份名称,
                    gb.xianzhuzhisdm_shi 现住址市地区代码, gb.xianzhuzhismc_shi   现住址市地区名称, gb.xianzhuzhidm_xian 现住址县区代码,
                    gb.xianzhuzhimc_xian 现住址县区名称, gb.xianzhuzhidm_jd 现住址乡镇街道代码, gb.xianzhuzhimc_jd 现住址乡镇街道名称,
                    gb.xianzhuzhimc_ssx  现住址省市县, gb.xianzhuzhixxdz 家庭地址,
                    zj.chuangjianren 创建人, zj.chuangjiansj 创建时间,  gb.hukoudz 户口地址
                from df_lc_menzhen.zj_jiuzhenxx zj
                join df_bingrenzsy.gy_bingrenxx gb on zj.bingrenid=gb.bingrenid 
                where zj.zuofeibz=0 and zj.jiuzhenid= '{jiuzhenid}'
        """

    if not jiuzhenid:
        # 新his 根据患者住院id 查询患者信息
        query_sql = f"""select bingrenzyid , xingming 姓名, xingbiemc 性别, nianling 年龄, shenfenzh 身份证号, 
                chushengrq 出生日期, gongzuodw 工作单位, danweidh 单位电话,danweiyb 单位邮编, xianzhuzhidh 现住址电话,   
                xianzhuzhiyb 现住址邮编, xuexingmc 血型名称, hunyinmc 婚姻状况, zhiyemc 职业, guojimc 国籍, minzumc 民族,    
                lianxiren 联系人, guanxidm 关系, lianxirdz 联系人地址, lianxirdh 联系人电话, lianxiryb 联系人邮编, ruyuanrq 入院日期,    
                chuyuanrq 出院日期, ruyuanksid 入院科室id, ruyuanbqid 入院病区id, ruyuancwid  入院床位id, ruyuancwbm 入院床位编码, 
                ruyuanfjid 入院房间ID, ruyuanfjh 入院房间号, dangqianksid 当前科室id, dangqianbqid 当前病区id, dangqiancwid 当前床位id,    
                dangqiancwbm 当前床位编码, dangqianfjid 当前房间ID, dangqianfjh 当前房间号, zhuyuanhao  住院号, bingrenid 病人ID,    
                menzhenysid 门诊医师, shouzhiysid 收治医师, zhuyuanysid 住院医师, zhuzhiysid  主治医师, ruyuanksmc 入院科室名称,  
                ruyuanbqmc 入院病区名称, dangqianksmc    当前科室名称, dangqianbqmc    当前病区名称, menzhenysxm 门诊医师姓名,
                shouzhiysxm 收治医师姓名, zhuyuanysxm 住院医师姓名, zhuzhiysxm  主治医师姓名, zerenhsid   责任护士, zerenhsxm 责任护士姓名,
                hukoudzyb 户口地址邮编, xingbiedm 性别代码, xuexingdm 血型代码, hunyindm 婚姻代码, zhiyedm 职业代码,
                guojidm 国籍代码, minzudm 民族代码, xianzhuzhidm_sheng  现住址省份, xianzhuzhimc_sheng 现住址省份名称,
                xianzhuzhisdm_shi 现住址市地区代码, xianzhuzhismc_shi   现住址市地区名称, xianzhuzhidm_xian 现住址县区代码,
                xianzhuzhimc_xian 现住址县区名称, xianzhuzhidm_jd 现住址乡镇街道代码, xianzhuzhimc_jd 现住址乡镇街道名称,
                xianzhuzhimc_ssx  现住址省市县, xianzhuzhixxdz 家庭地址, zhurenysid 主任医师, zhurenysxm 主任医师姓名,
                chuangjianren 创建人, chuangjiansj 创建时间, ruyuantj 入院途径, hukoudz 户口地址
            from df_jj_zhuyuan.zy_bingrenxx where bingrenzyid = '{bingrenzyid}' """

    pat_info = global_tools.call_new_his_pg(query_sql)
    if pat_info and pat_info[0]:
        data['pat_addr'] = pat_info[0].pop('家庭地址', '/')
        data['pat_id_card'] = str(pat_info[0].pop('身份证号', '/'))
        data['pat_name'] = pat_info[0].pop('姓名', '/')
        data['pat_sex'] = pat_info[0].pop('性别', '/')
        data['pat_marriage'] = pat_info[0].pop('婚姻状况', '/')
        data['pat_nation'] = pat_info[0].pop('民族', '/')
        data['pat_age'] = str(pat_info[0].pop('年龄', '/'))
        data['pat_occupation'] = pat_info[0].pop('职业', '/')
        data['联系人地址'] = pat_info[0].pop('联系人地址', '/')
        data['联系人电话'] = pat_info[0].pop('联系人电话', '/')
        data['pat_no'] = pat_info[0].pop('病人id', '/')
        data['pat_dept_no'] = str(pat_info[0].pop('当前科室id', '/'))
        data['pat_dept'] = str(pat_info[0].pop('当前科室名称', '/'))
        data['pat_ward_no'] = str(pat_info[0].pop('当前病区id', '/'))
        data['pat_ward'] = str(pat_info[0].pop('当前病区名称', '/'))
        data['入院科室id'] = str(pat_info[0].pop('入院科室id', '/'))
        data['入院科室名称'] = str(pat_info[0].pop('入院科室名称', '/'))
        data['入院病区id'] = str(pat_info[0].pop('入院病区id', '/'))
        data['入院病区名称'] = str(pat_info[0].pop('入院病区名称', '/'))
        data['pat_birth_time'] = pat_info[0].pop('出生日期').strftime('%Y-%m-%d') if pat_info[0].get('出生日期') else '/'
        data['pat_time'] = pat_info[0].pop('入院日期').strftime('%Y-%m-%d %H:%M:%S') if pat_info[0].get('入院日期') else '/'
        data['出院时间'] = pat_info[0].pop('出院日期').strftime('%Y-%m-%d %H:%M:%S') if pat_info[0].get('出院日期') else '/'
        data = {**data, **pat_info[0]}
    else:
        print("没有查询到病人信息")
        return

    # print(datetime.now(), "患者信息", data)
    return data


# 组装入院记录
def assembling_cda_record(data, type):
    data = query_pat_info_by_pat_no(data)
    if type == 1:
        data['file_title'] = '入院记录'
    elif type == 2:
        data['file_title'] = '出院记录'
    elif type == 3:
        data['file_title'] = '24小时入出院记录'
    elif type == 4:
        data['file_title'] = '住院病案首页'
    elif type == 5:
        data['file_title'] = '首次病程记录'
    elif type == 6:
        data['file_title'] = '日常病程记录'
    elif type == 7:
        data['file_title'] = '上级医师查房记录'
    elif type == 8:
        data['file_title'] = '疑难病例讨论记录'
    elif type == 9:
        data['file_title'] = '交接班记录'
    elif type == 10:
        data['file_title'] = '转科记录'
    elif type == 11:
        data['file_title'] = '阶段小结'
    elif type == 12:
        data['file_title'] = '抢救记录'
    elif type == 13:
        data['file_title'] = '会诊记录'
    elif type == 14:
        data['file_title'] = '术前小结'
    elif type == 15:
        data['file_title'] = '术前讨论'
    elif type == 16:
        data['file_title'] = '术后首次病程记录'
    elif type == 17:
        data['file_title'] = '死亡记录'
    elif type == 18:
        data['file_title'] = '死亡病例讨论记录'

    data['hospital_no'] = '0000'
    data['hospital_name'] = '南阳南石医院'
    # xml 声明
    admission_record = xml_const.xml_statement
    # xml 开始
    admission_record = admission_record + xml_const.xml_start

    if type == 1:
        # 入院记录
        # 组装 header
        admission_record = new_admission_cda.assembling_header(admission_record, data)
        # xml body 开始
        admission_record = admission_record + xml_const.xml_body_start
        # 组装 body
        admission_record = new_admission_cda.assembling_body(admission_record, data)
    elif type == 2:
        # 出院记录
        admission_record = new_discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_discharge_cda.assembling_body(admission_record, data)
    elif type == 3:
        # 24小时入出院记录
        admission_record = new_hours24_discharge_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_hours24_discharge_cda.assembling_body(admission_record, data)
    elif type == 4:
        # 住院病案首页
        print("住院病案首页 在 parse_server 中特殊处理")
    elif type == 5:
        # 首次病程记录
        admission_record = new_progress_note_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_progress_note_cda.assembling_body(admission_record, data)
    elif type == 6:
        # 日常病程记录
        admission_record = new_daily_medical_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_daily_medical_record_cda.assembling_body(admission_record, data)
    elif type == 7:
        # 上级医师查房记录
        admission_record = new_inspection_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_inspection_record_cda.assembling_body(admission_record, data)
    elif type == 8:
        # 疑难病例讨论记录
        admission_record = new_difficult_cases_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_difficult_cases_record_cda.assembling_body(admission_record, data)
    elif type == 9:
        # 交接班记录
        admission_record = new_handover_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_handover_record_cda.assembling_body(admission_record, data)
    elif type == 10:
        # 转科记录
        admission_record = new_transfer_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_transfer_record_cda.assembling_body(admission_record, data)
    elif type == 11:
        # 阶段小结
        admission_record = new_stage_summary_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_stage_summary_cda.assembling_body(admission_record, data)
    elif type == 12:
        # 抢救记录
        admission_record = new_rescue_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_rescue_record_cda.assembling_body(admission_record, data)
    elif type == 13:
        # 会诊记录
        admission_record = new_consultation_record_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_consultation_record_cda.assembling_body(admission_record, data)
    elif type == 14:
        # 术前小结
        admission_record = new_preoperative_summary_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = new_preoperative_summary_cda.assembling_body(admission_record, data)
    elif type == 15:
        # 术前讨论
        admission_record = preoperative_discussion_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = preoperative_discussion_cda.assembling_body(admission_record, data)
    elif type == 16:
        # 术后首次病程记录
        admission_record = preoperative_discussion_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = preoperative_discussion_cda.assembling_body(admission_record, data)
    elif type == 17:
        # 死亡记录
        admission_record = obituary_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = obituary_cda.assembling_body(admission_record, data)
    elif type == 18:
        # 死亡病例讨论记录
        admission_record = discussion_record_death_cases_cda.assembling_header(admission_record, data)
        admission_record = admission_record + xml_const.xml_body_start
        admission_record = discussion_record_death_cases_cda.assembling_body(admission_record, data)

    else:
        print(datetime.now(), "不支持 type", type, data['file_title'])

    # xml body 结束
    admission_record = admission_record + xml_const.xml_body_end
    # xml 结束
    admission_record = admission_record + xml_const.xml_end

    # print(admission_record)

    # 格式化 xml
    pretty_xml = prettify_xml(admission_record)
    # print(pretty_xml)

    return pretty_xml


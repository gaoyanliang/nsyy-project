import json
import logging
import requests

from datetime import datetime
from gylmodules import global_config, global_tools
from gylmodules.medical_record_analysis import parse_cda
from gylmodules.medical_record_analysis.anew_his_record import parse_new_his_xml
from gylmodules.medical_record_analysis.anew_his_record.build_cda import new_build_cda
from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_admission_record
from gylmodules.medical_record_analysis.record_parse.discharge_record_parse import parse_discharge_record
from gylmodules.medical_record_analysis.record_parse.inpatient_homepage_parse import parse_homepage_record
from gylmodules.medical_record_analysis.record_parse.progress_note_parse import parse_progress_note_record

logger = logging.getLogger(__name__)


def call_third_systems_obtain_data(type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            response = requests.post("http://192.168.124.53:6080/int_api", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            logger.error(f'查询老 hi 病历失败：type = {type}, param = {param}, {e}')
    else:
        if type == 'orcl_db_read':
            # 根据住院号/门诊号查询 病人id 主页id
            from tools import orcl_db_read
            data = orcl_db_read(param)

    return data


def query_record_and_parse(json_data):
    """
    "pat_no": 病人ID（564646）,
    "pat_page": 主页ID（12）,
    "file_name": 文件名称（入院记录/出院记录/病程记录/病案首页）,
    "data": 病案首页数据
    :param json_data:
    :return:
    """
    pat_no = json_data.get('pat_no')
    pat_page = json_data.get('pat_page')
    file_name = json_data.get('file_name')
    data = json_data.get('data')
    if not pat_no or not pat_page or not file_name:
        raise Exception('缺少必要参数', json_data)

    if file_name.__contains__('住院病案首页') and data is not None:
        try:
            cda = parse_homepage_record(data)
        except Exception as e:
            cda = 'cda 生成失败，请联系信息科人工处理'
            print(datetime.now(), f'住院病案首页 cda 生成失败，pat_no={pat_no}, pat_page={pat_page}')

        # 解析cda ，获取结构
        try:
            if cda:
                structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print(datetime.now(), f'住院病案首页 cda 结构解析失败，请联系信息科人工处理, {e}')
        return cda, structure

    param = {
        "type": "orcl_db_read", "db_source": "nsbingli",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "clob": ['CONTENT'],
        "sql": f"""select * from (select * from (Select b.病人id, b.主页id, t.title as 文档名称, a.title 文档类型, 
                    t.creat_time 记录时间, t.creator 文档作者, RAWTOHEX(t.id) 文档ID, t.content.getclobval() content
                    From Bz_Doc_Log t left join Bz_Act_Log a on a.Id = t.Actlog_Id
                    left join 病人变动记录@HISINTERFACE b on a.extend_tag = 'BD_' || to_char(b.id)) order by 记录时间)
                    where 病人ID = {pat_no} and 主页ID = {pat_page} and 文档名称 LIKE '%{file_name}%' """
    }
    records = call_third_systems_obtain_data('orcl_db_read', param)
    if not records:
        raise Exception('当前病人未查询到任何病历', json_data)

    try:
        cda = ''
        structure = ''
        cur_record = ''
        try:
            for record in records:
                cur_record = record
                if record.get('文档名称') and record.get('文档名称').__contains__("入院记录"):
                    cda = parse_admission_record(record.get('CONTENT'))
                elif record.get('文档名称') and record.get('文档名称').__contains__("出院记录") and not record.get(
                        '文档名称').__contains__("24小时"):
                    cda = parse_discharge_record(record.get('CONTENT'))
                elif record.get('文档名称') and record.get('文档名称').__contains__("病程记录"):
                    cda = parse_progress_note_record(record)
                else:
                    raise Exception('无法处理 ', file_name, " 文件类型")
                break
        except Exception as e:
            cda = 'cda 生成失败，请联系信息科人工处理'
            print(datetime.now(), f'{pat_no} {pat_page} {file_name} cda 生成失败，请联系信息科人工处理 {e}')

        # 解析cda ，获取结构
        try:
            if cda:
                if type(cda) == list:
                    structure = []
                    for c in cda:
                        structure.append(parse_cda.parse_cda_xml_document_by_str(c))
                else:
                    structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print(datetime.now(), f'{pat_no} {pat_page} {file_name} cda 结构解析失败，请联系信息科人工处理 {e}')
    except Exception as e:
        if cur_record:
            cur_record.pop('CONTENT')
        raise Exception('解析记录失败, 人工处理', json_data, cur_record, e)

    return cda, structure


def query_new_his_record_and_parse(json_data):
    """
    "pat_no": 病人ID（564646）,
    "pat_page": 主页ID（12）,
    "file_name": 文件名称（入院记录/出院记录/病程记录/病案首页）,
    "data": 病案首页数据
    :param json_data:
    :return:
    """
    binglijlid = json_data.get('binglijlid')
    file_name = json_data.get('file_name')
    data = json_data.get('data')
    if file_name.__contains__('住院病案首页') and data is not None:
        try:
            cda = parse_homepage_record(data)
        except Exception as e:
            cda = 'cda 生成失败，请联系信息科人工处理'
            print(datetime.now(), f'住院病案首页 cda 生成失败，binglijlid={binglijlid}')

        # 解析cda ，获取结构
        structure = {}
        try:
            if cda:
                structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print(datetime.now(), f'住院病案首页 cda 结构解析失败，请联系信息科人工处理 {e}')
        return cda, structure

    # TODO  根据病历记录id 查询病历 xml数据
    query_record_sql = f"""select wb2.wenjiannr, wb.binglijlid, wb.bingrenid, wb.binglimc, wb.bingrenzyid, 
                wb.jiuzhenid, wb.menzhenzybz from df_bingli.ws_binglijl wb join df_bingli.ws_binglijlnr wb2 
                on wb.binglijlid =wb2.binglijlid and wb.zuofeibz ='0' where wb.binglijlid = '{binglijlid}'"""
    records = global_tools.call_new_his_pg(sql=query_record_sql)
    if not records:
        raise Exception('当前病人未查询到任何病历', json_data)

    cda = ''
    structure = ''
    cur_record = ''
    try:
        try:
            # 新his所有病历都是同一个结构，可以用同一个解析逻辑
            for record in records:
                cur_record = record
                patient_info = parse_new_his_xml.main_parse_func(record.get('wenjiannr'))
                patient_info = clean_dict(patient_info)
                patient_info['bingrenzyid'] = record.get('bingrenzyid')
                patient_info['jiuzhenid'] = record.get('jiuzhenid')
                patient_info['pat_no'] = record.get('bingrenid')
                patient_info['file_name'] = record.get('binglimc')
                if record.get('binglimc').__contains__("入院记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 1)
                elif record.get('binglimc').__contains__("出院记录") and not record.get('binglimc').__contains__("24小时"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 2)
                elif record.get('binglimc').__contains__("24小时内入出院记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 3)
                elif record.get('binglimc').__contains__("首次病程记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 5)
                elif record.get('binglimc').__contains__("日常病程记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 6)
                elif record.get('binglimc').__contains__("查房记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 7)
                elif record.get('binglimc').__contains__("疑难病例讨论"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 8)
                elif record.get('binglimc').__contains__("交班记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 9)
                elif record.get('binglimc').__contains__("转入") or record.get('binglimc').__contains__("转出"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 10)
                elif record.get('binglimc').__contains__("阶段小结"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 11)
                elif record.get('binglimc').__contains__("抢救记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 12)
                elif record.get('binglimc').__contains__("会诊记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 13)
                elif record.get('binglimc').__contains__("术前小结"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 14)
                elif record.get('binglimc').__contains__("术前讨论记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 15)
                elif record.get('binglimc').__contains__("术后首次病程记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 16)
                elif record.get('binglimc').__contains__("死亡记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 17)
                elif record.get('binglimc').__contains__("死亡病例讨论记录"):
                    cda = new_build_cda.assembling_cda_record(patient_info, 18)
                else:
                    cda = ''
                break
        except Exception as e:
            cda = 'cda 生成失败，请联系信息科人工处理'
            print(datetime.now(), f'binglijlid={binglijlid} {file_name} cda 生成失败，请联系信息科人工处理 {e}')

        # 解析cda ，获取结构
        try:
            if cda:
                if type(cda) == list:
                    structure = []
                    for c in cda:
                        structure.append(parse_cda.parse_cda_xml_document_by_str(c))
                else:
                    structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print(datetime.now(), f'cda 结构解析失败，请联系信息科人工处理 {e}')
    except Exception as e:
        if cur_record:
            cur_record.pop('WENJIANNR')
        raise Exception('解析记录失败, 人工处理', json_data, cur_record, e)

    return cda, structure


def clean_dict(d):
    """
    递归地清理字典中的所有键和值，并忽略 None 或 null 的键和值。
    """
    if isinstance(d, dict):
        cleaned_dict = {}
        for k, v in d.items():
            # 忽略 None 或 null 的键
            if k is None or k == "null":
                continue
            # 清理键（去除空格和 <> 符号）
            cleaned_key = clean_string(str(k)) if isinstance(k, str) else k
            # 递归清理值
            cleaned_value = clean_dict(v)
            # 忽略 None 或 null 的值
            if cleaned_value is None or cleaned_value == "null":
                continue
            cleaned_dict[cleaned_key] = cleaned_value
        return cleaned_dict if cleaned_dict else None
    elif isinstance(d, list):
        cleaned_list = [clean_dict(i) for i in d]
        # 过滤掉 None 或 "null" 的项
        cleaned_list = [i for i in cleaned_list if i is not None and i != "null"]
        return cleaned_list if cleaned_list else None
    elif isinstance(d, str):
        cleaned_str = clean_string(d)
        return cleaned_str if cleaned_str else None
    else:
        return d


def clean_string(s):
    """
    去除字符串中的空格和 <> 符号。
    """
    if not isinstance(s, str):
        return s
    # 去除空格
    s = s.replace(" ", "")
    # 替换 <> 符号
    s = s.replace("<", "&lt;").replace(">", "&gt;").replace('"', "'")
    return s if s else None

import json

import requests

from gylmodules import global_config
from gylmodules.medical_record_analysis import parse_cda
from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_admission_record
from gylmodules.medical_record_analysis.record_parse.discharge_record_parse import parse_discharge_record
from gylmodules.medical_record_analysis.record_parse.inpatient_homepage_parse import parse_homepage_record
from gylmodules.medical_record_analysis.record_parse.progress_note_parse import parse_progress_note_record


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
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
            # 根据住院号/门诊号查询 病人id 主页id
            from tools import orcl_db_read
            data = orcl_db_read(param)

    return data


def query_record_and_parse(json_data):
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
            print('cda 生成失败，请联系信息科人工处理', e, data, json_data)

        # 解析cda ，获取结构
        try:
            if cda:
                structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print('cda 结构解析失败，请联系信息科人工处理', e)
        return cda, structure

    param = {
        "type": "orcl_db_read",
        "db_source": "nsbingli",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "clob": ['CONTENT'],
        "sql": f"""
            select *
              from (select *
                      from (Select b.病人id,
                                   b.主页id,
                                   t.title       as 文档名称,
                                   a.title       文档类型,
                                   t.creat_time  记录时间,
                                   t.creator     文档作者,
                                   RAWTOHEX(t.id) 文档ID,
                                   -- t.contenttext.getclobval() contenttext, 
                                   t.content.getclobval() content
                              From Bz_Doc_Log t
                              left join Bz_Act_Log a
                                on a.Id = t.Actlog_Id
                              left join 病人变动记录@HISINTERFACE b
                                on a.extend_tag = 'BD_' || to_char(b.id))
                     order by 记录时间)
             where 病人ID = {pat_no}
               and 主页ID = {pat_page}
               and 文档名称 LIKE '%{file_name}%'
        """
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
            print('cda 生成失败，请联系信息科人工处理', e)

        # 解析cda ，获取结构
        try:
            if cda:
                structure = parse_cda.parse_cda_xml_document_by_str(cda)
        except Exception as e:
            structure = 'cda 结构解析失败，请联系信息科人工处理'
            print('cda 结构解析失败，请联系信息科人工处理', e)
    except Exception as e:
        if cur_record:
            cur_record.pop('CONTENT')
        raise Exception('解析记录失败, 人工处理', json_data, cur_record, e)

    return cda, structure

import json
import time

import requests

from gylmodules import global_config
from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_admission_record


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
    if not pat_no or not pat_page or not file_name:
        raise Exception('参数错误', json_data)

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
        raise Exception('未查询到任何记录', json_data)

    try:
        cur_record = ''
        for record in records:
            cur_record = record
            if record.get('文档名称') and record.get('文档名称').__contains__("入院记录"):
                parse_admission_record(record.get('CONTENT'))
            else:
                raise Exception('无法处理 ', file_name, " 文件类型")
    except Exception as e:
        if cur_record:
            cur_record.pop('CONTENT')
        raise Exception('解析记录失败, 人工处理', json_data, cur_record, e)

import json
import time

import requests
from ping3 import ping
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from gylmodules import global_config
from gylmodules.critical_value import cv_config, cv_manage
import asyncio
from datetime import datetime
import xml.etree.ElementTree as ET
import re
import redis
from openpyxl import Workbook

import random
import string

from gylmodules.medical_record_analysis.record_parse import death_record_parse, progress_note_parse
from gylmodules.medical_record_analysis.record_parse.admission_record_parse import clean_dict
from gylmodules.utils.db_utils import DbUtil


# # ========================= 测试 Redis
# pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
#                             db=3, decode_responses=True)
# redis_client = redis.Redis(connection_pool=pool)
# redis_client.set("a:b:c:d", 12)
# redis_client.set("a:b:c:e", 12)
# redis_client.set("a:b:c:f", 12)
#
# # 扫描所有以 'a:' 开头的键
# keys_to_delete = redis_client.scan_iter("a:*")
#
# # 删除这些键
# for key in keys_to_delete:
#     print(key)




# # ========================= 测试数据库
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# query_sql = """
# SELECT * FROM nsyy_gyl.cv_info where id = 3375
# """
#
# record = db.query_one(query_sql)
#
# print()
# insert_sql = """
# INSERT INTO nsyy_gyl.cv_info (patient_treat_id,req_docno,alertman,cv_flag,patient_type,cv_type,cv_name,cv_result,cv_unit,cv_ref,
# patient_gender,patient_name,patient_age,dept_id,dept_name,alert_dept_id,alert_dept_name,alertman_name,alertman_pers_id,cv_id,cv_source,alertdt,time,state,nurse_recv_timeout,nurse_send_timeout,doctor_recv_timeout,doctor_handle_timeout,total_timeout)
# VALUES (120, '谭宗章', '0248', '', 5, 2, '*血小板', '18 10^9/L', '', '125-350',
#  '1', '孙绍连', '59岁', 140, '呼吸科门诊', 140, '呼吸科门诊', '谭宗章', '9910', '1721984666261', 10, '2024-07-26 17:04:26', '2024-07-26 17:04:26', 1, '420', '60', '300', '120', '600')
#
# """
# try:
#     ret = db.execute(insert_sql, need_commit=True)
#     print(ret)
# except Exception as e:
#     print(' ------------- ')
#     print(e)
# del db






#
# def call_third_systems_obtain_data(type: str, param: dict):
#     data = []
#     if global_config.run_in_local:
#         try:
#             # 发送 POST 请求，将字符串数据传递给 data 参数
#             response = requests.post("http://192.168.124.53:6080/int_api", json=param)
#             data = response.text
#             data = json.loads(data)
#             data = data.get('data')
#         except Exception as e:
#             print(datetime.now(), '调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#     else:
#         if type == 'data_feedback':
#             # 数据回传
#             from tools import orcl_db_update
#             orcl_db_update(param)
#         elif type == 'get_dept_info_by_emp_num':
#             # 根据员工号，查询科室信息
#             from tools import his_dept_pers
#             data = his_dept_pers(param)
#         elif type == 'cache_all_dept_info':
#             from tools import his_dept
#             data = his_dept(param)
#         elif type == 'orcl_db_read':
#             # 根据住院号/门诊号查询 病人id 主页id
#             from tools import orcl_db_read
#             data = orcl_db_read(param)
#         elif type == 'his_procedure':
#             # 危机值病历回写
#             from tools import his_procedure
#             data = his_procedure(param)
#         elif type == 'send_wx_msg':
#             # 向企业微信推送消息
#             from tools import send_wx_msg
#             data = send_wx_msg(param)
#     return data
#
# def data_feedback(cv_id, cv_source, confirmer, timer, confirm_info, type: int):
#     datal = []
#     updatel = []
#     datel = []
#     intl = []
#     if type == 1:
#         # 护士确认
#         datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN": confirmer, "HISCHECKDT": timer,
#                   "HISCHECKINFO": confirm_info}]
#         updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO"]
#         datel = ["HISCHECKDT"]
#     elif type == 2:
#         # 医生确认
#         datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN": confirmer, "HISCHECKDT": timer,
#                   "HISCHECKINFO": confirm_info}]
#         updatel = ["HISCHECKMAN", "HISCHECKDT", "HISCHECKINFO"]
#         datel = ["HISCHECKDT"]
#     elif type == 3:
#         # 医生处理
#         datal = [{"RESULTALERTID": cv_id, "HISCHECKMAN1": confirmer, "HISCHECKDT1": timer,
#                   "HISCHECKINFO1": confirm_info}]
#         updatel = ["HISCHECKMAN1", "HISCHECKDT1", "HISCHECKINFO1"]
#         datel = ["HISCHECKDT1"]
#
#     if cv_source == 2:
#         table_name = "inter_lab_resultalert"
#     else:
#         table_name = "NS_EXT.PACS危急值上报表"
#     param = {
#         "type": "orcl_db_update",
#         "db_source": "ztorcl",
#         "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#         "table_name": table_name,
#         "datal": datal,
#         "updatel": updatel,
#         "datel": datel,
#         "intl": intl,
#         "keyl": ["RESULTALERTID"]
#     }
#
#     call_third_systems_obtain_data('data_feedback', param)
#
#
# data_feedback(12422, 2, "李永青", "2024-09-09 08:26:17", '已确认', 2)






# # # =========================  查询病历
#
# def call_third_systems_obtain_data(type: str, param: dict):
#     data = []
#     if global_config.run_in_local:
#         try:
#             # 发送 POST 请求，将字符串数据传递给 data 参数
#             response = requests.post("http://192.168.3.12:6080/int_api", json=param)
#             data = response.text
#             data = json.loads(data)
#             data = data.get('data')
#         except Exception as e:
#             print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#     else:
#         if type == 'orcl_db_read':
#             # 根据住院号/门诊号查询 病人id 主页id
#             from tools import orcl_db_read
#             data = orcl_db_read(param)
#
#     return data
#
#
# param = {
#     "type": "orcl_db_read",
#     # "db_source": "ztorcl",
#     "db_source": "nsbingli",
#     "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#     "clob": ['CONTENT'],
#     # "strcol": ['ALERTDT'],
#     # "sql": "select 1 t from dual"
#     # "sql": "select RPTUNITNAME from inter_lab_resultalert where RESULTALERTID in (select RESULTALERTID from inter_lab_resultalert where ALERTDT > to_date('2023-01-01 08:30:59', 'yyyy-mm-dd hh24:mi:ss')) group by RPTUNITNAME"
#     # "sql": "select title from Bz_Doc_Log where id in (select id from Bz_Doc_Log where creat_time > to_date('2024-01-01 00:00:00', 'yyyy-mm-dd hh24:mi:ss')) and title in ('死亡讨论记录', '疑难病历讨论记录', '术前讨论记录', '死亡记录')"
#     "sql": """
# select *
#   from (select *
#           from (Select b.病人id,
#                        b.主页id,
#                        t.title       文档名称,
#                        a.title       文档类型,
#                        t.creat_time  创建时间,
#                        t.creator     文档作者,
#                        RAWTOHEX(t.id) 文档ID,
#                        -- t.contenttext.getclobval() contenttext,
#                        t.content.getclobval() content
#                   From Bz_Doc_Log t
#                   left join Bz_Act_Log a
#                     on a.Id = t.Actlog_Id
#                   left join 病人变动记录@HISINTERFACE b
#                     on a.extend_tag = 'BD_' || to_char(b.id))
#          order by 创建时间)
#  where 病人ID = '3597120'  and  创建时间 > to_date('2024-08-04 00:00:10', 'yyyy-mm-dd hh24:mi:ss') and 创建时间 < to_date('2024-08-04 23:59:10', 'yyyy-mm-dd hh24:mi:ss')
#     """
# }
#
#
# title_set = set()
# records = call_third_systems_obtain_data('orcl_db_read', param)
#
# for rec in records:
#     # rec.pop('CONTENT')
#     # rec.pop('文档ID')
#     # rec.pop('创建时间')
#     # print(rec)
#     print(rec.get('文档名称'))
#     if rec.get('文档名称').__contains__('病程记录'):
#         patient_info = progress_note_parse.parse_patient_document_by_str(rec.get('CONTENT'))
#         patient_info = clean_dict(patient_info)
#         formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
#         print(formatted_json)
#
#     patient_info = death_record_parse.parse_patient_document_by_str(rec.get('CONTENT'))
#     patient_info = clean_dict(patient_info)
#     formatted_json = json.dumps(patient_info, indent=4, ensure_ascii=False)
#     print(formatted_json)


#
# for rec in records:
#     title = rec.get('TITLE')
#     # if title.__contains__('选择签字书') or \
#     #     title.__contains__('同意书') or \
#     #     title.__contains__('报告卡') or \
#     #     title.__contains__('审批表') or \
#     #     title.__contains__('风险评估') or \
#     #     title.__contains__('量表') or \
#     #     title.__contains__('评定表') or \
#     #     title.__contains__('评估表') or \
#     #     title.__contains__('协议书') or \
#     #     title.__contains__('结算凭据') or \
#     #     title.__contains__('登记表') or \
#     #     title.__contains__('筛查表') or \
#     #     title.__contains__('患者声明') or \
#     #     title.__contains__('留观证') or \
#     #     title.__contains__('安全核查表') or \
#     #     title.__contains__('记录单') or \
#     #     title.__contains__('承诺书') or \
#     #     title.__contains__('沟通记录') or \
#     #     title.__contains__('处理记录') or \
#     #     title.__contains__('申请表') or \
#     #     title.__contains__('告知书') or \
#     #     title.__contains__('单项指标') or \
#     #     title.__contains__('时间节点表') or \
#     #     title.__contains__('粘贴单') or \
#     #     title.__contains__('上报表') or \
#     #     title.__contains__('观察室记录') or \
#     #     title.__contains__('观察记录') or \
#     #     title.__contains__('负荷试验') or \
#     #     title.__contains__('HoehnYahr分期') or \
#     #     title.__contains__('评估单') or \
#     #     title.__contains__('功能评定') or \
#     #     title.__contains__('出观证') or \
#     #     title.__contains__('申请单') or \
#     #     title.__contains__('通知书') or \
#     #     title.__contains__('活动度表') or \
#     #     title.__contains__('诊断标准') or \
#     #     title.__contains__('卧立位血压') or \
#     #     title.__contains__('上报表') or \
#     #     title.__contains__('下肢评定') or \
#     #     title.__contains__('证明书') or \
#     #     title.__contains__('证明书') or \
#     #     title.__contains__('委托书') or \
#     #     title.__contains__('移交书') or \
#     #     title.__contains__('使用记录') or \
#     #     title.__contains__('知情书') or \
#     #     title.__contains__('住院证') or \
#     #     title.__contains__('同意单') or \
#     #     title.__contains__('外出申请') or \
#     #     title.__contains__('追踪表') or \
#     #     title.__contains__('重建策略') or \
#     #     title.__contains__('报告单') or \
#     #     title.__contains__('直报表') or \
#     #     title.__contains__('信息表') or \
#     #     title.__contains__('检查表') or \
#     #     title.__contains__('诊断证明') or \
#     #     title.__contains__('计划单') or \
#     #     title.__contains__('出院证') or \
#     #     title.__contains__('邀请函') or \
#     #     title.__contains__('评价') or \
#     #     title.__contains__('评定') or \
#     #     title.__contains__('评估') or \
#     #     title.__contains__('评分'):
#     #     continue
#     title_set.add(title)
#
# for title in title_set:
#     print(title)





#
#
# def call_third_systems_obtain_data(type: str, param: dict, db_source: str):
#     param['db_source'] = db_source
#     data = []
#     if global_config.run_in_local:
#         try:
#             # 发送 POST 请求，将字符串数据传递给 data 参数
#             response = requests.post("http://192.168.124.53:6080/int_api", json=param)
#             data = response.text
#             data = json.loads(data)
#             data = data.get('data')
#         except Exception as e:
#             print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#     else:
#         if type == 'orcl_db_read':
#             # 根据住院号/门诊号查询 病人id 主页id
#             from tools import orcl_db_read
#             data = orcl_db_read(param)
#
#     return data
#
#
#
# param = {
#     "type": "orcl_db_read",
#     # "db_source": "nshis",
#     "db_source": "nsbingli",
#     "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#     "clob": ['CONTENT'],
#     # "strcol": ['ALERTDT'],
#
#     # 原有患者人数
#     "sql": """
# select  count(1),c.名称 ,q.出院科室id from 病案主页 q  left join 部门表 c
#   on c.id = q.出院科室id   where 出院日期 is null and q.入院日期  >= to_date('2024-08-26:18:00','yyyy-mm-dd:hh24:mi')
#   and q.入院日期  <= to_date('2024-08-27:08:00','yyyy-mm-dd:hh24:mi') -- and 出院科室id = 159
#   group by q.出院科室id ,c.名称
#     """
#
# }
#
# records = call_third_systems_obtain_data('orcl_db_read', param, 'nsbingli')
# # records = call_third_systems_obtain_data('orcl_db_read', param, 'nshis')
#
# for d in records:
#     print(d)


tup1 = []

tup1.append((1, None, "msg"))
tup1.append((2, 2, "msg"))
tup1.append((3, None, "msg"))
tup1.append((4, None, "msg"))

for i in tup1:
    print(i[0], i[1], i[2])







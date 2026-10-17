# -*- coding: utf-8 -*-
import base64
import concurrent
import json
import os
import random
import re
import ssl
import threading
import time
import urllib
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from itertools import groupby
from operator import itemgetter
from typing import Dict, List
from urllib.parse import quote, unquote
from uuid import uuid4

import openpyxl
import requests
from openpyxl import Workbook

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils_new import DbUtil

#
#
# def query_menzhen(sql):
#     results = []
#     try:
#         import psycopg2
#         conn = psycopg2.connect(dbname="df_his", user="ogg", password="nyogg@2024", host="192.168.8.57", port="6000")
#         cur = conn.cursor()
#         cur.execute(sql)
#         results = cur.fetchall()
#         cur.close()
#         conn.close()
#     except Exception as e:
#         print(datetime.now(), '高压氧门诊费用记录查询失败', e)
#         results = []
#     return results
#
#
# # ================================================
# # # ========================= 测试 Redis
# # ================================================
#
# pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
#                             db=global_config.REDIS_DB, decode_responses=True)
# # redis_client = redis.Redis(connection_pool=pool)
# # redis_client.set("a:b:c:d", 12)
# # redis_client.set("a:b:c:e", 12)
# # redis_client.set("a:b:c:f", 12)
# #
# # # 扫描所有以 'a:' 开头的键
# # keys_to_delete = redis_client.scan_iter("a:*")
# #
# # # 删除这些键
# # for key in keys_to_delete:
# #     print(redis_client.delete(key))
# #
# # print(redis_client.delete("0000000"))
#
#
# # ================================================
# # ========================= 测试数据库
# # ================================================
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# # # db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# #
# # query_sql = "select id, report_id, patient_name, cv_name, alertdt from nsyy_gyl.cv_info " \
# #             "where report_id is not None and cv_source = 3 and alertdt > '2024-09-01 00:00:00' "
# # records = db.query_all(query_sql)
# #
# # for record in records:
# #     print(record)
# # del db
# #
# #
# # ================================================
# # 调用 sql 查询接口获取数据（后面连接的 oracle 数据库）
# # 数据有可能和 PG 数据库不一致，可以在 navicat 中连接 PG 查询
# # ================================================
#
# sql = """
#      select t.jiluid, t.yzid AS "doc_advice_id", t.jianchamd AS "item_name", jymx.zhongwenmc AS "item_sub_name",
#         jymx.jianyanjg AS "item_sub_result", jymx.cankaofw AS "item_sub_refer", jymx.dangwei AS "item_sub_unit",
#         jymx.yichangbz, jymx.jianyanxmid AS "item_sub_id",
#         CASE
#             WHEN jymx.yichangbz = 'L' THEN '低'
#             WHEN jymx.yichangbz = 'H' THEN '高'
#             WHEN jymx.yichangbz = 'E' THEN '阳性'
#             WHEN jymx.yichangbz = 'D' THEN '阴性'
#             ELSE '正常' END AS "item_sub_flag"
#  from (select  LISTAGG(sqd.yizhubh, '+') WITHIN GROUP (ORDER BY sqd.yizhubh) as yzid,jy2.jianchamd,jy2.jiluid
#        from  df_shenqingdan.yj_jianyansqd sqd left  join df_cdr.yj_jianyanbg jy2 on jy2.bingrenid=sqd.bingrenid and
#        instr(jy2.shenqingdid,sqd.jianyansqdid)>0  and jy2.jianyanzt=1 where sqd.bingrenid='10105433'
#        and sqd.zuofeibz = 0  and sqd.kaidanrq >= to_date('2025-02-28','yyyy-mm-dd')
# group by jy2.jiluid,jy2.jianchamd) t left join df_cdr.yj_jianyanbgmx jymx ON t.jiluid = jymx.jiluid
# """
#
# start_time = time.time()
# data = call_new_his(sql)
# # data = query_menzhen(sql)
# # print(data)
# for d in data:
#     print(d)
# print('耗时：', time.time() - start_time, '数量: ', len(data))
#
#
# # ================================================
# # 测试： 调用 Ai 接口，获取结果
# # ================================================
#
# # start_time = time.time()
# # medical_data = ""
# # medical_data = medical_data + "主诉：发现血压高1年伴头懵1天。; "
# # medical_data = medical_data + "现病史：患者不清楚发病诱因，发作性头晕头懵10年，加重5天，最高血压170/130mmHg，" \
# #                               "最低血压100/90mmHg，伴头懵症状，用药物后缓解，未进行过检查，使用过具体不详，神志精神正常，饮食正常，" \
# #                               "睡眠正常，大便正常，小便正常，体力正常，体重无变化。; "
# # medical_data = medical_data + "平素身体良好，无。; "
# # medical_data = medical_data + "体温36.5°C，脉搏82次/分，呼吸20次/分，血压138/87mmHg，身高170CM，体重75公斤，BMI一度肥胖，神志清醒，步态正常，自动体位，精神正常。; "
# # medical_data = medical_data + "以上为患者基本信息，请根据该患者病历信息，给出初步诊断和推荐做的检查检验项目。"
# #
# # data = None
# # try:
# #     data = call_ai_api({"message": medical_data})
# # except Exception as e:
# #     print(datetime.now(), '调用 ai api 失败： ' + e.__str__())
# #
# # if data:
# #     print(data)
# #     # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #     #             global_config.DB_DATABASE_GYL)
# #     # db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# #     # update_sql = f"UPDATE nsyy_gyl.sq_surveys_detail set ai_result1 = '{data.get('data')}' where id = 173"
# #     # db.execute(update_sql, need_commit=True)
# #     # del db
# #     # print(datetime.now(), 'ai 耗时：', time.time() - start_time, f's, {id}')
#
#


# # # ================================================
# # # 综合预约排班数据生成
# # # 将 nsyy_gyl.appt_schedules 中的排班数据插入到
# # # nsyy_gyl.appt_schedules_doctor 中（需要确定构造哪一周的数据）
# # # ================================================
# #
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# # query_sql = """
# # select id, name from nsyy_gyl.appt_doctor where his_status = 1 and id not in
# # 		(
# # select distinct a.did
# # from nsyy_gyl.appt_schedules_doctor a
# # where a.shift_date >= '2026-05-18'
# # )
# # """
# # query_sql = """
# # select id, name from nsyy_gyl.appt_doctor where his_status = 1 and id in
# # 		(
# # select distinct a.did
# # from nsyy_gyl.appt_schedules_doctor a
# # where a.shift_date >= '2026-05-18'
# # )
# # """
# # doctors = db.query_all(query_sql)
# print('---')
# doctors = [{'id': 138}, {'id': 99}, {'id': 417}, {'id': 98}, {'id': 410}, {'id': 752}]
#
# doc_s_data = []
# for doctor in doctors:
#     doc_s_data.append((int(doctor.get('id')), '2026-06-22', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-22', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-23', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-23', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-24', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-24', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-25', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-25', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-26', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-26', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-27', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-27', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-28', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-28', 2, 1))
#
#     doc_s_data.append((int(doctor.get('id')), '2026-06-29', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-29', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-30', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-06-30', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-01', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-01', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-02', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-02', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-03', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-03', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-04', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-04', 2, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-05', 1, 1))
#     doc_s_data.append((int(doctor.get('id')), '2026-07-05', 2, 1))
#
#
# insert_sql = """INSERT IGNORE INTO nsyy_gyl.appt_schedules_doctor (did, shift_date, shift_type, status)
#                                 VALUES (%s, %s, %s, %s)"""
# db.execute_many(insert_sql, doc_s_data, need_commit=True)
# del db









# =============================================================================================
# 向his上报危急值 start
# =============================================================================================

# source_2_cv = global_tools.call_new_his_pg("select weijizhiid from df_cdr.jyjc_weijizhi where leixing = 1 and fasongsj >= '2025-08-01 00:00:00'")
#
# # print(source_2_cv)
# print(len(source_2_cv))
#
# source_2_cv_ids = [cv.get('weijizhiid') for cv in source_2_cv]
#
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# #
# query_sql = f"select * from nsyy_gyl.cv_info where cv_source = 2 and cv_id not in {tuple(source_2_cv_ids)} and alertdt >= '2025-08-01 00:00:00' "
# # # query_sql = f"select * from nsyy_gyl.cv_info where cv_source = 3 and cv_id in ('BG2026052300007B') "
# # # query_sql = f"select * from nsyy_gyl.cv_info where alertdt >= '2026-06-01 00:00:00' "
# records = db.query_all(query_sql)
# del db
# print(len(records))
#
# for record in records:
#     # record['cv_id'] = f"{record['cv_id']}-test1"
#     critical_value.send_to_his(record)
#
# # print(f"{record.get('alertdt')}  {record.get('cv_name')} 危机值ID {record.get('cv_id')} 患者姓名 {record.get('patient_name')} zhuyuanhao {record.get('patient_treat_id')}  {record.get('report_id')}", critical_value.query_shenqingdan_info(record))
# # print(f"患者 {record.get('patient_name')} 危机值id {record.get('cv_id')} 报告id {record.get('report_id')} 危机值内容 {record.get('cv_name')}  上报时间 {record.get('alertdt').strftime('%Y-%m-%d %H:%M:%S')}")
# # sqd_data = critical_value.query_shenqingdan_info(record)
# # if sqd_data:
# #     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息 {sqd_data} ")
# # else:
# #     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息未查询到")
# =============================================================================================
# 向his上报危急值 end
# =============================================================================================














#
# # 测试推送
# # failed = ios_push_batch(
# #     title="紧急通知1111",
# #     body="请立即处理1111！",
# #     device_tokens=[
# #         "11111111111111",
# #         "50f640ae09f0a07fa4c9d0b4aeb2f9e7907d840f36528e753506cc8f22888eee",
# #         "c8375b64e77cc773b81c0fb6c112fdd39828702d90a057ffbc882ba0f5be1a96",
# #         "d521928ce241c5f0fef0b8a4ffb944190caaaadc854feaae78590a30d57f1893",
# #         "d54f831d6a328bf77771825a11d47bdc52da3aa59208f64024d546fd5aa133f8",
# #         "dcb62abfb806741bb852c097f4bbd2585857a6a8b91084326273dbfab1315b8f",
# #         "dd1943a76356b81b5662aab75db1a425f1446d3e620a6d4e082be73a28118052",
# #         "f042c7a0d4b1f3b64f088c0a2a5f25c44703da1b74b3497e68863d01737b0394"
# #     ],
# #     max_workers=20  # 根据服务器性能调整
# # )
# # print("失败设备:", failed)
#
#


# # ================================================
# # ========================= 测试数据库
# # ================================================
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
#
# query_sql = "select * from nsyy_gyl.cv_info where patient_name = '' and cv_source = 5 and alertdt > '2025-09-01 00:00:00' "
# records = db.query_all(query_sql)
#
#
# oracle_sql = """
#                 SELECT xingming 姓名, xingbiemc 性别, nianling 年龄, xianzhuzhidh 联系电话, dangqianksid 所属科室ID,
#                 zhuyuanysxm 住院医师 FROM df_jj_zhuyuan.zy_bingrenxx
#                 WHERE quxiaorybz = 0 AND zhuyuanhao = '{patient_treat_id}'
#             """
#
#
# for record in records:
#     patient_data = global_tools.call_new_his(oracle_sql.replace('{patient_treat_id}', record.get('patient_treat_id')))
#     patient_data = patient_data[0] if patient_data else {}
#     sex = patient_data.get('性别') if patient_data.get('性别') else ''
#     if sex and '女' in sex:
#         sex = '2'
#     else:
#         sex = '1'
#
#     patient_name = patient_data.get('姓名') if patient_data.get('姓名') else ''
#     age = patient_data.get('年龄') if patient_data.get('年龄') else ''
#     phone = patient_data.get('联系电话') if patient_data.get('联系电话') else ''
#     doctor = patient_data.get('住院医师') if patient_data.get('住院医师') else ''
#
#     # print(f"患者 {patient_name} 性别 {sex} 年龄 {age} 联系电话 {phone} 住院医师 {doctor}")
#
#     db.execute(f"UPDATE nsyy_gyl.cv_info SET  patient_name = '{patient_name}', patient_gender = '{sex}', patient_age = '{age}', "
#                f"patient_phone = '{phone}', req_docno = '{doctor}' WHERE id = {record.get('id')}", need_commit=True)
#
# del db






# # ================================================
# # ========================= 测试数据库
# # ================================================
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
#
#
# query_sql = "select register_id, field_value from nsyy_gyl.phs_record_data " \
#             "where record_id = 2 and field_name = 'venous_treatment' "
# records = db.query_all(query_sql)
# zhenduan_dict = {}
# for item in records:
#     zhenduan_dict[str(item.get('register_id'))] = item.get('field_value')
#
# query_sql = "select * from nsyy_gyl.phs_patient_registration "
# records = db.query_all(query_sql)
#
# for item in records:
#     if zhenduan_dict.get(str(item.get('register_id'))):
#         da = zhenduan_dict.get(str(item.get('register_id')), '')
#         value_list = zhenduan_dict.get(str(item.get('register_id'))).split(",")
#         results = ''
#         for value in value_list:
#             if "外周静脉留置针-" in value:
#                 _, _, suffix = value.partition("-")
#                 results = results + suffix
#             if "中心静脉导管" in value or "PICC" in value:
#                 results = results + "带入"
#             if "头皮针" in value:
#                 results = results + "头皮针"
#         if (da.__contains__("中心静脉导管") or da.__contains__("PICC")) and not results.__contains__("带入"):
#             results = results + "带入"
#         if results:
#             print(f"register_id {item.get('register_id')} = {results}")
#             db.execute(f"UPDATE nsyy_gyl.phs_patient_registration SET jingmaitd = '{results}'"
#                    f" WHERE register_id = {item.get('register_id')}", need_commit=True)
#
# del db







# # ================================================ 测试医生交接班


# #
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
# all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
# del db
# reg_sqls = {item.get('sid'): item for item in all_sqls}
#
# # dept_list = ['7903', '1000420', '158', '157', '1000700', '1000561', '172', '1000620', '1001200',
# # '94103', '1001240', '1001100', '51225', '1000701', '1000640', '94223', '1000583', '1000580', '1202',
# # '174', '176', '1000680', '173', '170', '169', '168', '159', '162', '165', '1000440', '1000460',
# # '1000560', '171', '1000149', '1000404', '93043', '93203', '51323', '93183', '1222', '93843',
# # '1000148', '7907', '1282', '7905', '94323', '93163', '51227', '50762', '17487', '1262', '1000152',
# # '1000406', '1000402', '1000120', '93063', '161', '160', '1000780', '93243', '93263', '94743',
# # '94143', '93083', '167', '94224', '1000421', '156', '154']
#
# dept_list = ['7903', '171', '7907']
#
# shift_change_server.doctor_shift_change(reg_sqls, 1, "07:30-17:30", dept_list)



# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# records = db.query_all("select * from nsyy_gyl.ehp_check_result where type = '翻转拍'")
# # del db
#
# for item in records:
#     patient = json.loads(item.get('value'))
#     print(patient)
#     value = {"od": '', "os": '', 'ou': ''}
#     if patient.get('left'):
#         match = re.search(r'\d+\.\d+cpm', patient.get('left'))
#         if match:
#             value['os'] = match.group().replace('cpm', '')
#         if not value['os'] and patient.get('left') and patient.get('left').__contains__('cpm'):
#             value['os'] = '+不通过'
#     if patient.get('right'):
#         match = re.search(r'\d+\.\d+cpm', patient.get('right'))
#         if match:
#             value['od'] = match.group().replace('cpm', '')
#         if not value['od'] and patient.get('right') and patient.get('right').__contains__('cpm'):
#             value['od'] = '+不通过'
#     if patient.get('binoculus'):
#         match = re.search(r'\d+\.\d+cpm', patient.get('binoculus'))
#         if match:
#             value['ou'] = match.group().replace('cpm', '')
#         if not value['ou'] and patient.get('binoculus') and patient.get('binoculus').__contains__('cpm'):
#             value['ou'] = '+不通过'
#     db.execute(f"UPDATE nsyy_gyl.ehp_check_result SET value_well = '{json.dumps(value, ensure_ascii=False, default=str)}' WHERE id = {item.get('id')}", need_commit=True)
#     print(value)
#
# del db







# global_tools.socket_push("邮件通知", {"socketd": ["m_app"], "type": 500,
#                                                       'pers_id': [9640],
#                                                       'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                                                       "socket_data": {
#                                                           "message_id": "<538faaf7-a4f2-4f56-aaca-1b16a773e511@nsyy.com>",
#                                                           "user_account": "U00014",
#                                                           "mailbox": "Inbox"
#                                                       }})


# global_tools.socket_push("新邮件通知", {
#     "socketd": ["m_app"], "type": 400, 'pers_id': [110100],
#     'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     "socket_data": {"chat_type": 0, "context_type": 10, "sender": 9640, "sender_name": "胡海波",
#                     "group_id": None, "receiver": 110100, "receiver_name": "admin",
#                     "context": {
#                         "type": -1, "title": "新邮件通知", "description": f"来自 xxx 的新邮件 xxxxxxxx",
#                         "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                     },
#                     "timer": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                     }})










# ## ================= 从查询到的数据中提取出不同药品信息
#
# def analy_data(file_path):
#     df = pd.read_excel(file_path, dtype=str)
#     data = df.to_dict(orient="records")
#     return data
#
#
#
# data = []
#
# for i in range(1, 7):
#     data = data + analy_data(f"/Users/gaoyanliang/Downloads/his药品名称对应关系_{i}.xlsx")
#
# # keys = ['追溯码', 'his批准文号', 'his药品名称', '医保药品名称', '药品名称', '码状态', '码等级(3大码 2中码 1小码)', '药品类型描述', '包装规格', '制剂规格', '剂型描述', '有效期', '批准文号', '药品id', '企业名称', '企业id', '批次号', '生产日期', '原始生产日期', '有效期至', '原始有效期', '最小包装数量']
# keys = ['医保药品名称', '药品名称', '码等级(3大码 2中码 1小码)', '药品类型描述', '包装规格', '制剂规格', '剂型描述', '批准文号', '药品id', '企业名称', '企业id', '最小包装数量']
#
# ignore_keys = {'追溯码', 'his批准文号', 'his药品名称', '有效期', '批次号', '生产日期', '原始生产日期', '有效期至', '原始有效期', '码状态'}
#
# def all_dicts_equal_ignore_keys(cur_key, data, ignore_keys):
#     if not data:
#         return True
#
#     base = data[0]
#     keys = set(base.keys()) - ignore_keys
#
#     ret = True
#     for d in data[1:]:
#         for k in keys:
#             if d.get(k) != base.get(k):
#                 # print(cur_key, f"{k} 不一致：{d.get(k)} != {base.get(k)}")
#                 ret = False
#     return ret
#
# yaopin_set = set()
# # 根据标准药品名称进行分组
# data.sort(key=lambda x: (str(x['药品名称']), str(x['his价格id'])))
#
# # for item in data:
# #     if str(item.get('医保药品名称')) == 'nan' or str(item.get('药品名称')) == 'nan':
# #         continue
# #     if item['医保药品名称'] != item['药品名称']:
# #         print(f"医保名称和标准名称不一致：追溯码: {item['追溯码']} , {item['医保药品名称']} - {item['药品名称']}")
#
#
# ret_list = []
# for key, group in groupby(data, key=lambda x: (str(x['药品名称']), str(x['his价格id']))):
#     if 'nan' in key[0]:
#         continue
#
#     yaopin_set.add(key[0])
#     # 判断除his药品名称外 是否有其他字段不一致
#     tmp_list = list(group)
#     is_true = all_dicts_equal_ignore_keys(key, tmp_list, ignore_keys)
#     if not tmp_list:
#         continue
#     if is_true:
#         ret_list.append(tmp_list[0])
#     else:
#         ret_list += tmp_list
#
#
# print(f'一共 {len(yaopin_set)} 种药品', yaopin_set)
#
#
# # for item in ret_list:
# #     print(item)
# df = pd.DataFrame(ret_list)
# df.to_excel("/Users/gaoyanliang/Downloads/his药品名称对应关系.xlsx", index=False)






# # ==================================================================================================================
# # ===================================== 根据 结算清单流水号 查询入院记录 出院记录 医嘱 =====================================
# # ==================================================================================================================
#
# excel_path = f'/Users/gaoyanliang/Downloads/清单质控列表__20260101_20260608.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
# ids = []
# for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#     row_dict = dict(zip(headers, row))
#     row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#     ids.append(row_dict.get('医保结算流水号'))
#
#
# ids = ','.join(f"'{item}'" for item in ids)
#
# sql = f"""
#
#     select
# 	zb.xingming ,
# 	zb.zhuyuanhao ,
# 	zb.zhuyuancs,
# 	yz.yibaojyhm ,
# 	(
# 	select
# 		string_agg(case
# 			when zz.shunxuhao = 1 then '主要诊断：'
# 			else '其他诊断：'
# 		end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
# 		'、'
# 	order by
# 		zz.shunxuhao)
# 	from
# 		df_jj_zhuyuan.zy_zhenduanzl zz
# 	where
# 		zz.bingrenzyid = zb.bingrenzyid
# 		and zz.zhenduanlb like '19%'
# 		and zz.zuofeibz = '0') 诊断,
# 		(select
# 	string_agg(case
# 			when bbx.shunxuhao = 1 then '主要诊断：'
# 			else '其他诊断：'
# 		end || bbx.zhenduanmc || '(' || bbx.jibingbm  || ')' ,
# 		'、'
# 	order by
# 		bbx.shunxuhao)
# from
# 	df_bingangl.ba_bingrenjbxx bb
# join df_bingangl.ba_bingrenzd_xy bbx on
# 	bb.binganbrxh = bbx.binganbrxh
# 	and bbx.zuofeibz = '0'
# 	and bbx.zhenduanlb like '19%'
# where bb.hisbrzyid =zb.bingrenzyid) 病案诊断,
# 		(select
# 	string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
# 	'、'
# order by
# 	shunxuhao)
# from
# 	df_jj_zhuyuan.zy_ba_shoushuzl zbs
# where
# 	zbs.zuofeibz = '0'
# 	and zbs.bingrenzyid = zb.bingrenzyid) 手术,
# 	(
# 	select
# 		string_agg( (xpath ( 'string()' :: text,
# 		wb2.wenjiannr :: xml ))[1]::text,
# 		'
# '
# 	order by
# 		wb.jilusj)
# 	from
# 		df_bingli.ws_binglijl wb
# 	join df_bingli.ws_binglijlnr wb2 on
# 		wb.binglijlid = wb2.binglijlid
# 	where
# 		wb.bingrenzyid = zb.bingrenzyid
# 		and wb.zuofeibz = '0'
# 		and wb.wenshuzt = 2
# 		and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
# 		(select
#  string_agg( (xpath ( 'string()' :: text,
# 		wb2.wenjiannr :: xml ))[1]::text,
# 		'
# '
# 	order by
# 		wb.jilusj)
# from
# 	df_bingli.ws_binglijl wb
# join df_bingli.ws_binglijlnr wb2 on
# 	wb.binglijlid = wb2.binglijlid
# 	where  wb.bingrenzyid = zb.bingrenzyid
# 		and wb.zuofeibz = '0'
# 	and wb.wenshuzt = 2
# 	 and fuleimblx ='RuYuanJLFL' ) 入院记录,
# 	 (select
# string_agg( (xpath ( 'string()' :: text,
# 		wb2.wenjiannr :: xml ))[1]::text,
# 		'
# '
# 	order by
# 		wb.jilusj)
# from
# 	df_bingli.ws_binglijl wb
# join df_bingli.ws_binglijlnr wb2 on
# 	wb.binglijlid = wb2.binglijlid
# 	where  wb.bingrenzyid = zb.bingrenzyid
# 		and wb.zuofeibz = '0'
# 	and wb.wenshuzt = 2
# 	 and fuleimblx ='ChuYuanJLFL' ) 出院记录
# 	 ,(select
# 	string_agg(distinct case when yb.yizhufl='21' then '诊疗：' else '手术:' end|| yb.yizhumc ,'、')
# from
# 	df_lc_zhuyuan.yz_bingrenyz yb
# where
# 	yb.bingrenzyid = yb.bingrenzyid and yb.yizhuzt in ('3', '4') and yb.yizhufl in ('21','25')
# 	and yb.yizhuid in (
# 	select
# 		zf.yizhuid
# 	from
# 		df_jj_zhuyuan.zy_feiyong1 zf
# 	where
# 	 zf.bingrenzyid=zb.bingrenzyid	 group by zf.yizhuid
# 	having
# 		sum(zf.jiesuanje)>0)) 医嘱
# from
# 	df_jj_zhuyuan.zy_bingrenxx zb
# join df_jj_zhuyuan.zy_jiesuan1 zj on
# 	zb.bingrenzyid = zj.bingrenzyid
# 	and zb.jiesuanxh = zj.jiesuanxh
# join df_yibao.yb_zhuyuanjsxx yz on
# 	zj.yibaojsid = yz.zhuyuanjsid
# where
# 	yz.yibaojyhm in ({ids})
#     """
#
# patient_data = global_tools.call_new_his_pg(sql)
# for item in patient_data:
#     print(item)
#
# with open("/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/temp/naobingzhongzheng_patients.json", "w", encoding="utf-8") as f:
#     json.dump(patient_data, f, ensure_ascii=False, indent=2)
#















# # # ==================================================================================================================
# # # ===================================== 从指控清单中提取出关键信息 + 病人出入院记录和医嘱 =====================================
# # # ==================================================================================================================
#
#
# with open('/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/temp/naobingzhongzheng_patients.json', "r", encoding="utf-8") as f:
#     patients = json.load(f)
#
# pdata = {item.get('yibaojyhm'):item for item in patients}
#
# # 获取所有行数据
# data_list = []
#
# for i in range(1, 2):
#
#     # excel_path = f'/Users/gaoyanliang/Downloads/清单质控列表_2026-0{str(i)} (1).xlsx'
#     excel_path = f'/Users/gaoyanliang/Downloads/清单质控列表__20260101_20260608.xlsx'
#     num = 0  # 工作表索引，openpyxl从0开始计数
#
#     # 打开工作簿
#     wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
#     # 获取工作表
#     sheet_names = wbook.sheetnames
#     sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
#     headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
#     for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#         row_dict = dict(zip(headers, row))
#         row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#
#         pinfo = pdata.get(row_dict.get('医保结算流水号'))
#
#         djson = {
#             "姓名": row_dict.get('姓名'),
#             "年龄": row_dict.get('年龄'),
#             "性别": row_dict.get('性别'),
#             "住院号": row_dict.get('住院号'),
#             "住院次数": row_dict.get('住院次数'),
#             "病案号": row_dict.get('病案号'),
#             "结算清单流水号": row_dict.get('医保结算流水号'),
#             "总费用": row_dict.get('总费用'),
#             "住院医师": row_dict.get('住院医师'),
#             "实际住院【天】": row_dict.get('实际住院【天】'),
#             "患者费别": row_dict.get('患者费别'),
#             "诊断编码": row_dict.get('主要诊断编码'),
#             "诊断名称": row_dict.get('主要诊断名称'),
#             "手术操作编码": row_dict.get('主要手术及操作编码'),
#             "手术操作名称": row_dict.get('主要手术及操作名称'),
#
#
#
#             "手术记录": pinfo.get('手术记录') if pinfo else '',
#             "手术列表": pinfo.get('手术') if pinfo else '',
#             "病案诊断": pinfo.get('病案诊断') if pinfo else '',
# #             "入院记录": pinfo.get('入院记录') if pinfo else '',
#             "出院记录": pinfo.get('出院记录') if pinfo else '',
#             "医嘱列表": pinfo.get('医嘱') if pinfo else ''
#         }
#         data_list.append(djson)
#         print(djson)
# print(f"总共 {len(data_list)} 行数据")
#
# # 从
# excel_path = "/Users/gaoyanliang/Downloads/naobingzhongzheng-patients.xlsx"
# if not data_list:
#     print('没有需要写入的患者列表')
# wb = Workbook()
# ws = wb.active
# ws.title = "Sheet1"
#
# # 表头
# headers = data_list[0].keys()
# ws.append(list(headers))
#
# # 数据行
# for row in data_list:
#     ws.append([row.get(col, "") for col in headers])
#
# wb.save(excel_path)















#
# # ==================================================================================================================
# # ===================================== 拉出对别列表 =====================================
# # ==================================================================================================================
# excel_path = f'/Users/gaoyanliang/Downloads/清单质控列表__20260101_20260608.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
# old_patient = {}
# for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#     row_dict = dict(zip(headers, row))
#     row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#     old_patient[row_dict.get('医保结算流水号')] = row_dict
#
#
# print(f'指控列表数量： {len(old_patient.keys())}')
#
#
# # excel_path = f'/Users/gaoyanliang/Downloads/这周2026-patients.xlsx'
# # num = 0  # 工作表索引，openpyxl从0开始计数
# #
# # # 打开工作簿
# # wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
# #
# # # 获取工作表
# # sheet_names = wbook.sheetnames
# # sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# # headers = [cell.value for cell in sheet[1]]  # 第一行做 key
# #
# # new_patient = {}
# # for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
# #     row_dict = dict(zip(headers, row))
# #     row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
# #     new_patient[row_dict.get('结算清单流水号')] = row_dict
#
# with open('/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/temp/naobingzhongzheng_ai2.json', "r", encoding="utf-8") as f:
#     data_list = json.load(f)
#
# data_list = {f"{item.get('zhuyuanhao')}-{item.get('zhuyuancs')}": item for item in data_list}
#
# print(f'ai 结果数量： {len(data_list.keys())}')
#
#
# with open('/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/temp/naobingzhongzheng_patients.json', "r", encoding="utf-8") as f:
#     his_list = json.load(f)
#
# his_list = {f"{item.get('yibaojyhm')}": item for item in his_list}
#
#
# diff_patient = []
# for item in old_patient.keys():
#     old = old_patient.get(item)
#     # new = new_patient.get(item)
#
#     ai_result = data_list.get(f"{old.get('住院号')}-{old.get('住院次数')}")
#     his_data = his_list.get(old.get('医保结算流水号'), {})
#
#     try:
#         diff_patient.append({
#             "姓名": old.get('姓名'),
#             "住院号": old.get('住院号'),
#             "住院次数": old.get('住院次数'),
#             "住院医师": old.get('住院医师'),
#             "病案号": old.get('病案号'),
#             "总费用": old.get('总费用'),
#             "患者费别": old.get('患者费别'),
#             '诊断': his_data.get('诊断'),
#             '手术': his_data.get('手术'),
#
#             "主要诊断编码": old.get('主要诊断编码'),
#             "主要诊断名称": old.get('主要诊断名称'),
#             "手术及操作编码": old.get('主要手术及操作编码'),
#             "手术及操作名称": old.get('主要手术及操作名称'),
#
#             "DIP入组代码": old.get('DIP入组代码'),
#             "DIP入组名称": old.get('DIP入组名称'),
#             "AI-入组代码": ai_result.get('recommendations', [])[0].get('dip_code'),
#             "AI-入组名称": ai_result.get('recommendations', [])[0].get('dip_name'),
#
#             "DIP分值": old.get('DIP分值'),
#             "AI-DIP分值": ai_result.get('recommendations', [])[0].get('score'),
#
#             "DIP倍率": old.get('DIP倍率'),
#             "AI-倍率": ai_result.get('recommendations', [])[0].get('dip_rate', ''),
#
#             "DIP结余预测": old.get('DIP结余预测'),
#             "AI-结余预测": ai_result.get('recommendations', [])[0].get('dip_predict', 0),
#             "AI-结余预测2": ai_result.get('recommendations', [])[1].get('dip_predict', 0) if len(ai_result.get('recommendations', [])) > 1 else 0,
#             "AI-结余预测3": ai_result.get('recommendations', [])[2].get('dip_predict', 0) if len(ai_result.get('recommendations', [])) > 2 else 0,
#
#             "AI-入组2": f"{ai_result.get('recommendations', [])[1].get('dip_code')} && {ai_result.get('recommendations', [])[1].get('dip_name')} && {ai_result.get('recommendations', [])[1].get('score')} && {ai_result.get('recommendations', [])[1].get('dip_rate')} && {ai_result.get('recommendations', [])[1].get('type')}" if len(
#                 ai_result.get('recommendations', [])) > 1 else '',
#             "AI-入组3": f"{ai_result.get('recommendations', [])[2].get('dip_code')} && {ai_result.get('recommendations', [])[2].get('dip_name')} && {ai_result.get('recommendations', [])[2].get('score')} && {ai_result.get('recommendations', [])[2].get('dip_rate')} && {ai_result.get('recommendations', [])[2].get('type')}" if len(
#                 ai_result.get('recommendations', [])) > 2 else '',
#
#             "病种类别": old.get('病种类别'),
#             "AI-病种类别": ai_result.get('recommendations', [])[0].get('type'),
#
#             "AI - 分析": ai_result.get('分析'),
#             "AI - 推荐理由及修改意见": ai_result.get('推荐理由及修改意见'),
#
#
#         })
#     except Exception as e:
#         print('old ', old)
#         print('ai ', ai_result)
#
#
# print(f'结果数量： {len(diff_patient)}')
#
# def normalize_value(x):
#     s = str(x).strip()
#     # 如果点号在中间（是小数）
#     if '.' in s:
#         # rstrip 去除右边的0，然后再把点号去掉（如果点号后面没数字了）
#         s = s.rstrip('0').rstrip('.')
#     return s
#
# import openpyxl
# from openpyxl.styles import PatternFill
#
# def write_diff_to_excel(diff_patient, output_file="对比结果.xlsx"):
#     """
#     将 diff_patient 写入 Excel，并对新旧不一致的单元格高亮
#     :param diff_patient: list of dict, 每个 dict 包含所有对比字段
#     :param output_file: 输出文件名
#     """
#     if not diff_patient:
#         print("没有数据可写入")
#         return
#
#     # 1. 定义列顺序（按您代码中的字典键顺序）
#     columns = [
#         "姓名", "住院号", "住院次数", "住院医师", "病案号", "总费用", "患者费别", "诊断", "手术",
#         "主要诊断编码", "主要诊断名称", "手术及操作编码", "手术及操作名称",
#
#         "DIP入组代码", "DIP入组名称", "AI-入组代码", "AI-入组名称",
#
#         "DIP分值", "AI-DIP分值", "DIP倍率", "AI-倍率", "DIP结余预测", "AI-结余预测", "AI-结余预测2", "AI-结余预测3", "病种类别", "AI-病种类别",
#
#         "AI-入组2", "AI-入组3",
#         "AI - 分析", "AI - 推荐理由及修改意见"
#     ]
#
#     # 2. 定义需要对比的字段对 (旧字段, 新字段)
#     compare_pairs = [
#         # ("旧-主要诊断编码", "新-主要诊断编码", ''),
#         # ("旧-主要诊断名称", "新-主要诊断名称", ''),
#         # ("旧-DIP诊断编码", "新-DIP诊断编码", 'AI-诊断编码'),
#         # ("旧-DIP诊断编码名称", "新-DIP诊断编码名称", 'AI-诊断名称'),
#         # ("旧-DIP操作编码", "新-DIP操作编码", 'AI-操作编码'),
#         # ("旧-DIP操作编码名称", "新-DIP操作编码名称", 'AI-操作名称'),
#         # ("旧-DIP入组代码", "新-DIP入组代码", ''),
#         # ("旧-DIP入组名称", "新-DIP入组名称", ''),
#         ("DIP分值", 'AI-DIP分值'),
#         ("病种类别", 'AI-病种类别')
#     ]
#
#     # 高亮样式：浅红色背景
#     highlight_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
#
#     highlight_fill1 = PatternFill(start_color="3FB68C", end_color="3FB68C", fill_type="solid")
#
#     # 创建工作簿和工作表
#     wb = openpyxl.Workbook()
#     ws = wb.active
#     ws.title = "对比结果"
#
#     # 写入表头
#     ws.append(columns)
#
#     # 写入数据行
#     for row_data in diff_patient:
#         row_cells = []
#         for col_name in columns:
#             # 从字典中获取值，若缺失则用空字符串
#             value = row_data.get(col_name, "")
#             row_cells.append(value)
#         ws.append(row_cells)
#
#     # 现在对每个数据行进行高亮处理
#     # 注意：表头占第1行，数据从第2行开始
#     for row_idx, row_data in enumerate(diff_patient, start=2):
#         # 获取列索引映射（列名 -> 列号）
#         col_index = {col_name: idx+1 for idx, col_name in enumerate(columns)}
#         for old_key, ai_key in compare_pairs:
#             old_val = row_data.get(old_key, "")
#             ai_val = row_data.get(ai_key, "")
#             # 比较时统一转为字符串，避免数字/None比较问题
#             if normalize_value(old_val) != normalize_value(ai_val):
#                 # 高亮旧值单元格
#                 # old_cell = ws.cell(row=row_idx, column=col_index[old_key])
#                 # old_cell.fill = highlight_fill
#                 # 高亮新值单元格
#                 ai_cell = ws.cell(row=row_idx, column=col_index[ai_key])
#                 ai_cell.fill = highlight_fill
#
#
#     # 自动调整列宽（简单处理）
#     for col in ws.columns:
#         max_length = 0
#         col_letter = col[0].column_letter
#         for cell in col:
#             try:
#                 if cell.value:
#                     max_length = max(max_length, len(str(cell.value)))
#             except:
#                 pass
#         adjusted_width = min(max_length + 2, 30)
#         ws.column_dimensions[col_letter].width = adjusted_width
#
#     wb.save(output_file)
#     print(f"已保存到 {output_file}")
#
# # 使用方法：假设您的 diff_patient 已经生成
# write_diff_to_excel(diff_patient, "脑病重症2-AI DIP结果对比.xlsx")






































# # # # ================================================
# # # # ========================= 测试数据库
# # # ================================================
# # # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# # #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
#
# query_sql = ("select 医保结算流水号, 住院医师, 住院号, 住院次数, 出院科室, 出院记录, 医嘱, 年龄, 性别, 总费用, 患者费别, 手术, 手术记录, 诊断, 病案诊断 "
#              "from nsyy_gyl.dip_patient where 出院科室 = '烧伤科一病区' ")
# records = db.query_all(query_sql)
#
# print(f"len = {len(records)}")
#
# del db
#
#
#
# # 3. 创建 Excel
# wb = Workbook()
# ws = wb.active
# ws.title = "用户数据"
#
# # 4. 写表头
# headers = ['医保结算流水号', '住院医师', '住院号', '住院次数', '出院科室', '出院记录', '医嘱', '年龄', '性别', '总费用', '患者费别', '手术', '手术记录', '诊断', '病案诊断']
# ws.append(headers)
#
# # 5. 写数据
# for row in records:
#     ws.append([
#         row['医保结算流水号'],
#         row['住院医师'],
#         row['住院号'],
#         row['住院次数'],
#         row['出院科室'],
#         row['出院记录'],
#         row['医嘱'],
#         row['年龄'],
#         row['性别'],
#         row['总费用'],
#         row['患者费别'],
#         row['手术'],
#         row['手术记录'],
#         row['诊断'],
#         row['病案诊断']
#     ])
#
# # 6. 保存
# wb.save('/Users/gaoyanliang/Downloads/重新跑-烧伤科一病区.xlsx')
# print("✅ 写入完成")
# #












# # # ==================================================================================================================
# # # ===================================== 根据 结算清单流水号 查询入院记录 出院记录 医嘱 =====================================
# # # ==================================================================================================================
# #
# #
# excel_path = f'/Users/gaoyanliang/Downloads/南阳南石康复中医院-清单审核列表20260828085605508.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
# ids = []
# for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#     row_dict = dict(zip(headers, row))
#     row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#     ids.append(row_dict.get('结算ID'))
#
# print(len(ids))
#
# import numpy as np
#
# parts = np.array_split(ids, 15)
#
# all_data = []
# for ids in parts:
#
#     ids = ','.join(f"'{item}'" for item in ids)
#
#     yt_sql = f"""
#     with   yz as
#           (
#         select distinct yz.病人Id,yz.主页id, yz.诊疗类别,yz.医嘱内容
#                   from 病人医嘱记录 yz
#                   where yz.诊疗类别  in ('E','F') and yz.医嘱状态 not in (-1, 2, 4)
#            and yz.执行性质 <> -1
#             and yz.id in (
#                   select t2.医嘱序号
#                   from 住院费用记录 t2
#                   where t2.医嘱序号 = yz.id and t2.病人id = yz.病人id
#                    and t2.主页id = yz.主页id
#                    and t2.记录状态 <> 0
#                    and t2.记录性质 < 10
#                    and t2.结帐ID is not null group by t2.医嘱序号 having sum(t2.结帐金额) <> 0
#                   ))
#         select g.姓名,
#                 g.出院日期,
#                g.年龄,
#                g.住院号,
#                g.主页id,
#                t2.支付顺序号 结算id ,
#                (SELECT LISTAGG(CASE
#                                  WHEN z.诊断次序 = 1 THEN
#                                   '主要诊断：'
#                                  ELSE
#                                   '其他诊断：'
#                                END || z.诊断描述,
#                                '、') WITHIN GROUP(ORDER BY z.诊断次序)
#                   FROM 病人诊断记录 z
#                  WHERE z.记录来源 =3
#                    AND z.诊断类型 IN (3, 13)
#                    and z.病人id = g.病人id
#                    and z.主页id = g.主页id) 诊断,
#                (SELECT LISTAGG(CASE
#                                  WHEN z.诊断次序 = 1 THEN
#                                   '主要诊断：'
#                                  ELSE
#                                   '其他诊断：'
#                                END || z.诊断描述,
#                                '、') WITHIN GROUP(ORDER BY z.诊断次序)
#                   FROM 病人诊断记录 z
#                  WHERE z.记录来源 = 4
#                    AND z.诊断类型 IN (3, 13)
#                    and z.病人id = g.病人id
#                    and z.主页id = g.主页id) 病案诊断,
#                (SELECT LISTAGG(t1.名称 || '(' || t1.编码 || ')', '、') WITHIN GROUP(ORDER BY t.手术日期)
#                   FROM 病人手麻记录 t
#                   left join 疾病编码目录 t1
#                     on t.手术操作id = t1.id
#                  WHERE t.记录来源 = 4
#                    and t.病人id = g.病人id
#                    and t.主页id = g.主页id) 手术,
#                    replace(( select
#         xmlagg(case when nvl(b.保留对象,0)<>1 then xmlelement(e,b.内容文本||',')
#         end order by b.父id).extract('//text()').getclobval()
#     from 电子病历记录 a
#   -- join 病案主页 n on a.病人id=n.病人id and a.主页id=n.主页id
#    join 电子病历内容 b on a.id=b.文件id  and nvl(b.保留对象,0)<>1
#     where a.文件id =23  and a.病人Id=g.病人Id and a.主页id=g.主页Id
#                    ),'&' || 'quot;', '') 手术记录,
#                    replace(( select
#         xmlagg(case when nvl(b.保留对象,0)<>1 then xmlelement(e,b.内容文本||',')
#         end order by b.父id).extract('//text()').getclobval()
#     from 电子病历记录 a
#   -- join 病案主页 n on a.病人id=n.病人id and a.主页id=n.主页id
#    join 电子病历内容 b on a.id=b.文件id  and nvl(b.保留对象,0)<>1
#     where a.文件id =963  and a.病人Id=g.病人Id and a.主页id=g.主页Id
#                    ),'&' || 'quot;', '') 操作记录,
#                replace((     select
#         xmlagg(case when nvl(b.保留对象,0)<>1 then xmlelement(e,b.内容文本||',')
#         end order by b.父id).extract('//text()').getclobval()
#     from 电子病历记录 a
#    join 病案主页 n on a.病人id=n.病人id and a.主页id=n.主页id
#    join 电子病历内容 b on a.id=b.文件id  and nvl(b.保留对象,0)<>1
#     where a.文件id =5  and a.病人Id=g.病人Id and a.主页id=g.主页Id
#                    ),'&' || 'quot;', '')入院记录,
#                   replace( (     select
#         xmlagg(case when nvl(b.保留对象,0)<>1 then xmlelement(e,b.内容文本||',')
#         end order by b.父id).extract('//text()').getclobval()
#     from 电子病历记录 a
#   -- join 病案主页 n on a.病人id=n.病人id and a.主页id=n.主页id
#    join 电子病历内容 b on a.id=b.文件id  and nvl(b.保留对象,0)<>1
#     where a.文件id =29  and a.病人Id=g.病人Id and a.主页id=g.主页Id
#                    ),'&' || 'quot;', '') 出院记录,
#           (select  listagg(case when yz.诊疗类别='E' then '诊疗：' else '手术:' end || yz.医嘱内容,'；' ) within group (order by 1) from yz
#           where yz.病人id=g.病人id and yz.主页id =g.主页id
#           group by yz.病人id,yz.主页id
#           )医嘱, g.入院日期
#           from 病案主页 g
#           join 保险结算记录 t2
#             on g.病人id = t2.病人ID
#            and g.主页ID = t2.主页id
#            and t2.冲销ID is  null
#            and not exists
#          (select 1 from 保险结算记录 t3 where t3.冲销id = t2.记录id)
#            and exists
#          (select 1
#                   from 住院费用记录 t2
#          where  t2.病人id = g.病人id
#                    and t2.主页id = g.主页id
#                    and t2.记录状态 <> 0
#                    and t2.记录性质 < 10
#                    and t2.结帐ID is not null having sum(t2.结帐金额) <> 0)
#                    and t2.支付顺序号  in ({ids})
#         """
#     # patient_data = global_tools.call_new_his(yt_sql, 'ythis', clobl=['手术记录', '出院记录', '入院记录'])
#
#     kf_sql = f"""
#     with   yz as
#   (
# select distinct yz.病人Id,yz.主页id, yz.诊疗类别,yz.医嘱内容
#           from 病人医嘱记录@HISINTERFACE yz
#           join 病案主页@HISINTERFACE g on yz.病人Id=g.病人id and yz.主页id=g.主页id
# join 保险结算记录@HISINTERFACE t2 on g.病人id = t2.病人ID and g.主页ID = t2.主页id and t2.冲销ID is  null
# and not exists
#  (select 1 from 保险结算记录@HISINTERFACE t3 where t3.冲销id = t2.记录id)
#  and t2.支付顺序号='20260622152005701849'
#           where yz.诊疗类别  in ('E','F','5','6','7') and yz.医嘱状态 not in (-1, 2, 4)
#    and yz.执行性质 <> -1
#     and yz.id in (
#           select t2.医嘱序号
#           from 住院费用记录@HISINTERFACE t2
#           where t2.医嘱序号 = yz.id and t2.病人id = yz.病人id
#            and t2.主页id = yz.主页id
#            and t2.记录状态 <> 0
#            and t2.记录性质 < 10
#            and t2.结帐ID is not null group by t2.医嘱序号 having sum(t2.结帐金额) <> 0
#           )),
# jy as
# (
# select a.病人id,a.主页id,xmlagg(  xmlparse(content c.中文名 || b.检验结果 || c.单位 || ' ' wellformed)order by b.id).getclobval() 检验
# from 检验申请组合@HISINTERFACE e
# join 检验组合项目@HISINTERFACE d on d.id = e.组合id
# join 检验报告明细@HISINTERFACE b on b.组合id = d.id and b.标本id = e.标本id
# join 检验报告记录@HISINTERFACE a on a.id = b.标本id
# left join 检验指标@HISINTERFACE c on b.项目id=c.id
# join 病案主页@HISINTERFACE g on a.病人Id=g.病人id and a.主页id=g.主页id
# join 保险结算记录@HISINTERFACE t2 on g.病人id = t2.病人ID and g.主页ID = t2.主页id and t2.冲销ID is  null
# and not exists
#  (select 1 from 保险结算记录@HISINTERFACE t3 where t3.冲销id = t2.记录id)
#  and t2.支付顺序号='20260622152005701849'
# group by a.病人id,a.主页id
# )
# select g.姓名,
#        g.年龄,
#        g.住院号,
#        g.主页id,
#        t2.支付顺序号 结算id ,
#        (SELECT LISTAGG(CASE
#                          WHEN z.诊断次序 = 1 and z.诊断类型=3 THEN
#                           '西医主要诊断：'
#                          WHEN z.诊断次序 = 1 and z.诊断类型=13 THEN
#                           '中医主要诊断：'
#                          ELSE
#                           '其他诊断：'
#                        END || z.诊断描述,
#                        '、') WITHIN GROUP(ORDER BY z.诊断次序)
#           FROM 病人诊断记录@HISINTERFACE z
#          WHERE z.记录来源 =3
#            AND z.诊断类型 IN (3, 13)
#            and z.病人id = g.病人id
#            and z.主页id = g.主页id) 诊断,
#        (SELECT LISTAGG(CASE
#                          WHEN z.诊断次序 = 1 and z.诊断类型=3 THEN
#                           '西医主要诊断：'
#                          WHEN z.诊断次序 = 1 and z.诊断类型=13 THEN
#                           '中医主要诊断：'
#                          ELSE
#                           '其他诊断：'
#                        END || z.诊断描述,
#                        '、') WITHIN GROUP(ORDER BY z.诊断次序)
#           FROM 病人诊断记录@HISINTERFACE z
#          WHERE z.记录来源 = 4
#            AND z.诊断类型 IN (3, 13)
#            and z.病人id = g.病人id
#            and z.主页id = g.主页id) 病案诊断,
#
#   from 病案主页@HISINTERFACE g
#   join 保险结算记录@HISINTERFACE t2 on g.病人id = t2.病人ID and g.主页ID = t2.主页id and t2.冲销ID is  null
#    and not exists
#  (select 1 from 保险结算记录@HISINTERFACE t3 where t3.冲销id = t2.记录id)
#    and exists
#  (select 1
#           from 住院费用记录@HISINTERFACE t2
#  where  t2.病人id = g.病人id
#            and t2.主页id = g.主页id
#            and t2.记录状态 <> 0
#            and t2.记录性质 < 10
#            and t2.结帐ID is not null having sum(t2.结帐金额) <> 0)
#            and t2.支付顺序号='20260622152005701849'
#  left join jy on jy.病人Id=g.病人id and jy.主页id=g.主页id
# """
#     patient_data = global_tools.call_new_his(kf_sql, 'kf', clobl=['手术记录', '出院记录', '入院记录'])
#
#     for item in patient_data:
#         print(item)
#     all_data += patient_data
#
# with open("/Users/gaoyanliang/Downloads/kf2_patients.json", "w", encoding="utf-8") as f:
#     json.dump(all_data, f, ensure_ascii=False, indent=2)









# # ==================================================================================================================
# # ===================================== 从指控清单中提取出关键信息 + 病人出入院记录和医嘱 =====================================
# # ==================================================================================================================
# def handle_nianling(age):
#     if str(age).__contains__('月') and not str(age).__contains__('岁'):
#         age = '1'
#     if str(age).__contains__('月'):
#         age = age.split('月')[0]
#     if str(age).__contains__('岁'):
#         age = age.split('岁')[0]
#     return age
#
#
# with open('/Users/gaoyanliang/Downloads/kf2_patients.json', "r", encoding="utf-8") as f:
#     patients = json.load(f)
#
# pdata = {item.get('结算ID'):item for item in patients}
#
# # 获取所有行数据
# data_list = []
#
# for i in range(1, 2):
#
#     # excel_path = f'/Users/gaoyanliang/Downloads/清单质控列表_2026-0{str(i)} (1).xlsx'
#     excel_path = f'/Users/gaoyanliang/Downloads/南阳南石康复中医院-清单查询列表20260706041905816.xlsx'
#     num = 0  # 工作表索引，openpyxl从0开始计数
#
#     # 打开工作簿
#     wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
#     # 获取工作表
#     sheet_names = wbook.sheetnames
#     sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
#     headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
#     for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#         row_dict = dict(zip(headers, row))
#         row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#
#         pinfo = pdata.get(row_dict.get('结算ID'))
#         if not pinfo:
#             continue
#
#         shoushujilu = pinfo.get('手术记录', '').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else ''
#         chaozuojilu = pinfo.get('操作记录', '').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else ''
#
#         djson = {
#             "医保结算流水号": row_dict.get('结算ID'),
#             "姓名": row_dict.get('患者姓名'),
#             "患者费别": row_dict.get('险种类型'),
#             "总费用": row_dict.get('医疗总费用'),
#             "出院科室": row_dict.get('院内出院科室'),
#             "住院医师": row_dict.get('住院医师'),
#
#             "现DIP代码": row_dict.get('预分组编码'),
#             "现DIP名称": row_dict.get('预分组名称'),
#             "现DIP分值": row_dict.get('病例分值'),
#             "现DIP盈亏": row_dict.get('预测盈亏'),
#             "现DIP倍率": row_dict.get('倍率'),
#
#             "住院号": row_dict.get('病案号'),
#             "住院次数": row_dict.get('住院次数'),
#             "入院时间": pinfo.get('入院日期', ''),
#             "出院时间": row_dict.get('出院时间'),
#             "年龄": handle_nianling(pinfo.get('年龄')),
#             "性别": row_dict.get('性别'),
#
#             "手术记录": shoushujilu + chaozuojilu,
#             "手术": pinfo.get('手术').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else '',
#             "诊断": pinfo.get('诊断').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else '',
#             "病案诊断": pinfo.get('病案诊断').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else '',
#             "入院记录": pinfo.get('入院记录', '').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else '',
#             "出院记录": pinfo.get('出院记录').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else '',
#             "医嘱": pinfo.get('医嘱').replace('\n', '').replace('\t', '').replace('\r', '') if pinfo else ''
#         }
#         data_list.append(djson)
#         print(djson)
# print(f"总共 {len(data_list)} 行数据")
#
# for item in data_list:
#     # print(item)
#     sql = """ INSERT INTO nsyy_gyl.dip_patient(医保结算流水号, 姓名, 患者费别, 总费用, 出院科室, 住院医师, 现DIP代码, 现DIP名称,
#                 现DIP分值, 现DIP盈亏, 现DIP倍率, 住院号, 住院次数, 出院时间, 年龄, 性别,
#                 诊断, 病案诊断, 手术, 医嘱, 出院记录, 来源) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#     """
#     params = (
#         item.get('医保结算流水号'),
#         item.get('姓名'),
#         item.get('患者费别'),
#         item.get('总费用'),
#         item.get('出院科室'),
#         item.get('住院医师'),
#         item.get('现DIP代码'),
#         item.get('现DIP名称'),
#         item.get('现DIP分值'),
#         item.get('现DIP盈亏'),
#         item.get('现DIP倍率'),
#         item.get('住院号'),
#         item.get('住院次数'),
#         item.get('出院时间'),
#         item.get('年龄'),
#         item.get('性别'),
#         item.get('诊断'),
#         item.get('病案诊断'),
#         item.get('手术'),
#         item.get('医嘱'),
#         item.get('出院记录'),
#         '南阳南石康复中医院有限公司'
#     )
#     print(params)
#     # with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
#     #             global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
#     #     data = db.execute(sql, params, need_commit=True)
#     with DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl") as db:
#         data = db.execute(sql, params, need_commit=True)







# excel_path = f'/Users/gaoyanliang/Downloads/心内一亏损前50.xlsx'
# out_path = f'/Users/gaoyanliang/Downloads/心内一亏损前50患者数据全.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
# ids = []
# patients = {}
# for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#     row_dict = dict(zip(headers, row))
#     row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
#     patients[row_dict.get('医保结算流水号')] = row_json
#     ids.append(row_dict.get('医保结算流水号'))
#
# print(len(ids))








# excel_path = f'/Users/gaoyanliang/Downloads/心外科室所有患者清单__20260101_20260624.xlsx'
# data = global_tools.excel_to_jsons1(excel_path, keys = ['医保结算流水号', '患者费别', '年龄', '性别', '总费用', '住院医师', '入院时间', '出院时间', 'DIP入组代码', 'DIP入组名称'])
#
# print('患者总数量 ', len(data))
# ids = ','.join(f"'{item.get('医保结算流水号')}'" for item in data)
#
# sql = f"""
# with jy as
# (
# select bingrenzyid,string_agg(jg ,'、') as jg
# from (
# select yj.bingrenzyid,yj.shenhesj::varchar || string_agg(yj1.zhongwenmc || ':' ||yj1.jianyanjg || coalesce(yj1.dangwei,''),'、') as jg
# from df_cdr.yj_jianyanbg yj
# join df_cdr.yj_jianyanbgmx yj1 on yj.jiluid = yj1.jiluid
# join df_jj_zhuyuan.zy_bingrenxx zb on yj.bingrenzyid=zb.bingrenzyid
# join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
# join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
# group by yj.bingrenzyid,yj.shenhesj
# order by yj.shenhesj
# )v
# group by bingrenzyid
# ),
# yz1 as
# (
# select bingrenzyid,
# string_agg( case when yizhufl ='21' then '诊疗：' when yizhufl='25' then '手术：' else null end
# 	|| yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(dw,'') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、') filter (where yizhufl in ('21','25')) as 治疗,
# string_agg( '用药：'
# 	|| yizhumc || ':' || to_char(shuliang,'FM9999990.00') || coalesce(dw,'') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、') filter (where yizhufl in ('11','12','13')) as 用药
# from(
# select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
# from df_lc_zhuyuan.yz_bingrenyz yb
# join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
# join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
# join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
# join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
# where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('11','12','13','21','25')
# group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
# )v
# group by bingrenzyid
# )
# select
#   zb.xingming ,
#   zb.zhuyuanhao ,
#   zb.zhuyuancs,
#   yz.yibaojyhm ,
#   (
#   select
#     string_agg(case
#       when zz.shunxuhao = 1 then '主要诊断：'
#       else '其他诊断：'
#     end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
#     '、'
#   order by
#     zz.shunxuhao)
#   from
#     df_jj_zhuyuan.zy_zhenduanzl zz
#   where
#     zz.bingrenzyid = zb.bingrenzyid
#     and zz.zhenduanlb like '19%'
#     and zz.zuofeibz = '0') 诊断,
#     (select
#   string_agg(case
#       when bbx.shunxuhao = 1 then '主要诊断：'
#       else '其他诊断：'
#     end || bbx.zhenduanmc || '(' || bbx.jibingbm  || ')' ,
#     '、'
#   order by
#     bbx.shunxuhao)
# from
#   df_bingangl.ba_bingrenjbxx bb
# join df_bingangl.ba_bingrenzd_xy bbx on
#   bb.binganbrxh = bbx.binganbrxh
#   and bbx.zuofeibz = '0'
#   and bbx.zhenduanlb like '19%'
# where bb.hisbrzyid =zb.bingrenzyid) 病案诊断,
# (
# select string_agg(yj.baogaosj::varchar || yj.jianchaxmmc || ':' ||nullif(yj.jianchasuojian,''),'、' order by baogaosj asc)
# from df_cdr.yj_jianchabg yj
# where yj.bingrenzyid=zb.bingrenzyid and yj.zuofeibz=0
# ) 检查,
# jy.jg 检验,
#     (select
#   string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
#   '、'
# order by
#   shunxuhao)
# from
#   df_jj_zhuyuan.zy_ba_shoushuzl zbs
# where
#   zbs.zuofeibz = '0'
#   and zbs.bingrenzyid = zb.bingrenzyid) 手术,
#   (
#   select
#     string_agg( (xpath ( 'string()' :: text,
#     wb2.wenjiannr :: xml ))[1]::text,
#     '
# '
#   order by
#     wb.jilusj)
#   from
#     df_bingli.ws_binglijl wb
#   join df_bingli.ws_binglijlnr wb2 on
#     wb.binglijlid = wb2.binglijlid
#   where
#     wb.bingrenzyid = zb.bingrenzyid
#     and wb.zuofeibz = '0'
#     and wb.wenshuzt = 2
#     and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
#         (select
#  string_agg( (xpath ( 'string()' :: text,
#     wb2.wenjiannr :: xml ))[1]::text,
#     '
# '
#   order by
#     wb.jilusj)
# from
#   df_bingli.ws_binglijl wb
# join df_bingli.ws_binglijlnr wb2 on
#   wb.binglijlid = wb2.binglijlid
#   where  wb.bingrenzyid = zb.bingrenzyid
#     and wb.zuofeibz = '0'
#   and wb.wenshuzt = 2
#    and fuleimblx ='RuYuanJLFL' )入院记录,
#     (select
#  string_agg( (xpath ( 'string()' :: text,
#     wb2.wenjiannr :: xml ))[1]::text,
#     '
# '
#   order by wb.jilusj)
# from df_bingli.ws_binglijl wb
# join df_bingli.ws_binglijlnr wb2 on wb.binglijlid = wb2.binglijlid
# where  wb.bingrenzyid = zb.bingrenzyid and wb.zuofeibz = '0' and wb.wenshuzt = 2 and fuleimblx ='ChuYuanJLFL' ) 出院记录 ,
# yz1.治疗 治疗医嘱,yz1.用药 用药医嘱
# from
#   df_jj_zhuyuan.zy_bingrenxx zb
# join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
# join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid
# left join jy on jy.bingrenzyid=zb.bingrenzyid
# left join yz1 on yz1.bingrenzyid=zb.bingrenzyid
# where yz.yibaojyhm in ({ids})
# """
#
# start_time = time.time()
# pdata = global_tools.call_new_his_pg(sql)
#
# print('查询得到的数量 ', len(pdata))
#
# res_data = {}
# for item in pdata:
#     res_data[item.get('yibaojyhm')] = {
#         "医保结算流水号": item.get('yibaojyhm'),
#         "病案诊断": item.get('病案诊断'),
#         "检查列表及结果": item.get('检查'),
#         "检验列表及结果": item.get('检验'),
#         "手术操作": item.get('手术'),
#         "手术记录": item.get('手术记录'),
#         "出院记录": item.get('出院记录'),
#         "治疗医嘱": item.get('治疗医嘱'),
#         "用药医嘱": item.get('用药医嘱'),
#         "入院记录": item.get('入院记录')
#     }
#
#
# for item in data:
#     d = res_data.get(item.get('医保结算流水号'))
#     if not d:
#         print(item)
#         continue
#     item['医生诊断'] = d.get('病案诊断')
#     item['手术操作'] = d.get('手术操作')
#     item['手术记录'] = d.get('手术记录')
#     item['出院记录'] = d.get('出院记录')
#     item['治疗医嘱'] = d.get('治疗医嘱')
#     item['用药医嘱'] = d.get('用药医嘱')
#     item['入院记录'] = d.get('入院记录')
#     # print(item)
#
#
# # 调用示例
# # data = [{"姓名": "张三", "年龄": 25, "城市": "北京"}, {"姓名": "李四", "年龄": 30, "城市": "上海"}]
# global_tools.jsons_to_excel_pandas(data, "/Users/gaoyanliang/Downloads/心外科室所有患者清单1.xlsx")






# excel_path = f'/Users/gaoyanliang/各个系统文档整理/ai-dip/各科室患者DIP数据/脑病重症病区/2026年DIP病种目录库.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
# headers = [cell.value for cell in sheet[1]]  # 第一行做 key
#
# mulu_ku = []
# for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第3行开始
#     row_dict = dict(zip(headers, row))
#     mulu_ku.append(row_dict)
#
# zhenduans = []
# caozuos = []
# for item in mulu_ku:
#     zhenduans.append(f"{item.get('诊断名称')}-{item.get('诊断编码')}")
#     caozuos.append(f"{item.get('手术操作名称')}-{item.get('手术操作编码')}, ")
#
# print(', '.join(list(set(zhenduans))))
# print('--------')
# print(', '.join(list(set(caozuos))))
#
#
#
# import pandas as pd
# import json
# from pathlib import Path
#
# def merge_audit_with_original(excel_path: str, json_path: str, output_path: str = None):
#     """
#     将审核结果JSON与原始患者Excel按流水号合并，生成新的Excel。
#
#     Parameters:
#         excel_path (str): 原始患者数据Excel文件路径（包含50位患者的所有信息）。
#         json_path (str): 审核结果JSON文件路径（包含诊断/操作建议）。
#         output_path (str, optional): 输出Excel路径，默认在原文件目录下生成 *_merged.xlsx。
#
#     Returns:
#         pd.DataFrame: 合并后的DataFrame，并保存为Excel文件。
#     """
#     # 1. 读取原始Excel
#     df_original = pd.read_excel(excel_path, dtype=str)  # 全部保留为字符串，避免数字格式化问题
#     if '医保结算流水号' not in df_original.columns:
#         raise ValueError("原始Excel缺少 '医保结算流水号' 列")
#
#     # 2. 读取审核JSON
#     with open(json_path, 'r', encoding='utf-8') as f:
#         audit_list = json.load(f)
#
#     # 将审核列表转为以流水号为键的字典
#     audit_dict = {item['id']: item for item in audit_list}
#
#     print('json数量 ', len(audit_dict.keys()))
#
#     # 3. 准备新增列
#     new_columns = {
#         '建议主要诊断': [],
#         '建议诊断列表': [],
#         '建议删除诊断': [],
#         '建议补充诊断': [],
#         '建议主要操作': [],
#         '建议操作列表': [],
#         '建议删除操作': [],
#         '建议补充操作': [],
#         '审核备注': []
#     }
#
#     # 4. 逐行填充
#     for idx, row in df_original.iterrows():
#         serial = str(row['医保结算流水号']).strip()
#         if serial in audit_dict:
#             audit = audit_dict[serial]
#             new_columns['建议主要诊断'].append(audit.get('new_main', ''))
#             # 诊断列表：提取所有诊断名称，并标注action
#             diag_str = '；'.join([
#                 f"{d['name']}({d['action']}--{str(d['score'])})" for d in audit.get('diagnosis', []) if d['action'] != 'delete'
#             ])
#             new_columns['建议诊断列表'].append(diag_str)
#             new_columns['建议删除诊断'].append('；'.join(audit.get('del_diagnosis', [])))
#             new_columns['建议补充诊断'].append('；'.join(audit.get('add_diagnosis', [])))
#             # 主要操作：取action为'upgrade'的第一个，否则取列表第一个
#             ops = audit.get('operations', [])
#             main_op = ''
#             for op in ops:
#                 if op.get('action') == 'upgrade':
#                     main_op = op.get('name', '')
#                     break
#             if not main_op and ops:
#                 main_op = ops[0].get('name', '')
#             new_columns['建议主要操作'].append(main_op)
#             # 操作列表
#             op_str = '；'.join([f"{op['name']}({op.get('action','')}--{str(op.get('score',''))})" for op in ops if op['action'] != 'delete'])
#             new_columns['建议操作列表'].append(op_str)
#
#             # 删除、补充诊断
#             new_columns['建议删除操作'].append('；'.join(audit.get('del_operations', [])))
#             new_columns['建议补充操作'].append('；'.join(audit.get('add_operations', [])))
#             new_columns['建议详情'].append(audit.get('note', ''))
#         else:
#             # 若未找到匹配，填充空值
#             new_columns['建议主要诊断'].append('')
#             new_columns['建议诊断列表'].append('')
#             new_columns['建议删除诊断'].append('')
#             new_columns['建议补充诊断'].append('')
#             new_columns['建议主要操作'].append('')
#             new_columns['建议操作列表'].append('')
#             new_columns['建议删除操作'].append('')
#             new_columns['建议补充操作'].append('')
#             new_columns['建议详情'].append('未匹配到审核数据')
#
#     # 5. 添加新列到DataFrame
#     for col_name, col_values in new_columns.items():
#         df_original[col_name] = col_values
#
#     # 6. 保存
#     if output_path is None:
#         base = Path(excel_path)
#         output_path = base.parent / f"{base.stem}_merged.xlsx"
#
#     df_original.to_excel(output_path, index=False, engine='openpyxl')
#     print(f"合并完成，文件已保存至：{output_path}")
#     return df_original
#
# json_file = "/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/temp/audit_results.json"   # 您保存的JSON文件
# merge_audit_with_original(out_path, json_file)



# excel_path = f'/Users/gaoyanliang/各个系统文档整理/ai-dip/各科室患者DIP数据/脑病重症病区/2026年DIP病种目录库.xlsx'
# data = global_tools.excel_to_jsons1(excel_path, keys = ['诊断编码', '诊断名称'])
#
# ids = ','.join(f"{item.get('诊断名称')}({item.get('诊断编码')})" for item in data)
#
# print(ids)




# for item in data:
#     aid = ai_data.get(item.get('医保结算流水号'))
#     fid = final_data.get(item.get('医保结算流水号'))
#
#     item['id'] = item.pop('医保结算流水号')
#     item['age/年龄'] = item.pop('年龄')
#     item['gender/性别'] = item.pop('性别')
#     item['Patient Fee Type/患者费别'] = item.pop('患者费别')
#     item['Total Cost/总费用'] = item.pop('总费用')
#     item['Admission time/入院时间'] = item.pop('入院时间')
#     item['Discharge time/出院时间'] = item.pop('出院时间')
#     item['Surgical record/手术记录'] = item.pop('手术')
#     item['Doctor orders/医嘱'] = item.pop('医嘱')
#     item['discharge records/出院记录'] = item.pop('出院记录')
#     item['surgical records/手术记录'] = item.pop('手术记录')
#     item.pop('住院医师')
#     item['Reasons for AI recommendation/AI推荐原因'] = aid.get('analysis') if aid else ''
#     item['AI Recommended Diagnosis/AI推荐主要诊断'] = aid.get('main_diagnosis') if aid else ''
#     item['Doctor Diagnosis/医生主要诊断'] = f"{fid.get('主要诊断名称')}({fid.get('主要诊断编码')})" if fid else ''
#     item['AI Recommended Group/AI推荐入组'] = f"{aid.get('recommendations')[0].get('dip_name')}({aid.get('recommendations')[0].get('dip_code')})" if aid else ''
#     item['Doctor Group/医生入组'] = f"{fid.get('DIP入组名称')}({fid.get('DIP入组代码')})" if fid else ''
#
#     item['Doctor Diagnosis/医生主要诊断'] = item['Doctor Diagnosis/医生主要诊断'].replace('1、', '')





# excel_path = f'/Users/gaoyanliang/Downloads/心外所有患者清单__20260101_20260625.xlsx'
# final_data = global_tools.excel_to_jsons1(excel_path, keys=['总费用', '住院号', '住院次数'])
# final_data = {str(item.get('总费用')).replace(' ', ''): item for item in final_data}
#
#
# excel_path = f'/Users/gaoyanliang/Downloads/all_201_final1.xlsx'
# ai_data = global_tools.excel_to_jsons1(excel_path)
#
# for item in ai_data:
#     it = final_data.get(str(item.get('total_fee')))
#     if not it:
#         print(item)
#         continue
#     item['住院号'] = it.get('住院号')
#     item['住院次数'] = it.get('住院次数')
#
# global_tools.jsons_to_excel_pandas(ai_data, '/Users/gaoyanliang/Downloads/all_201_final2.xlsx')


















data = [
        {
          "name": "左房前后径",
          "reference": "25-40",
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "左房容积",
          "reference": None,
          "value": "",
          "unit": "ml",
          "abnormal": None
        },
        {
          "name": "右室前后径",
          "reference": "16-30",
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "主肺动脉径",
          "reference": "16-30",
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "室间隔厚度",
          "reference": "8-12",
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "运动幅度-室间隔",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "主动脉瓣环",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "升主动脉内径",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "左室舒张期内径",
          "reference": "男 20-55, 女 20-50",
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "左室收缩期内径",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "左室后壁厚度",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },
        {
          "name": "运动幅度-左室后壁",
          "reference": None,
          "value": "",
          "unit": "mm",
          "abnormal": None
        },

        {
          "name": "主动脉流速",
          "reference": None,
          "value": "",
          "unit": "m/s",
          "abnormal": None
        },
        {
          "name": "二尖瓣E峰",
          "reference": None,
          "value": "",
          "unit": "m/s",
          "abnormal": None
        },
        {
          "name": "肺动脉流速",
          "reference": None,
          "value": "",
          "unit": "m/s",
          "abnormal": None
        },
        {
          "name": "二尖瓣A峰",
          "reference": None,
          "value": "",
          "unit": "m/s",
          "abnormal": None
        },
        {
          "name": "三尖瓣反流流速",
          "reference": None,
          "value": "",
          "unit": "m/s",
          "abnormal": None
        },
        {
          "name": "二尖瓣环间隔侧e’",
          "reference": None,
          "value": "",
          "unit": "cm/s",
          "abnormal": None
        },
        {
          "name": "压力阶差",
          "reference": None,
          "value": "",
          "unit": "mmHg",
          "abnormal": None
        },
        {
          "name": "二尖瓣环侧隔侧e’",
          "reference": None,
          "value": "",
          "unit": "cm/s",
          "abnormal": None
        },
        {
          "name": "估测肺动脉压约",
          "reference": None,
          "value": "",
          "unit": "mmHg",
          "abnormal": None
        },
        {
          "name": "E/e’",
          "reference": None,
          "value": "",
          "unit": None,
          "abnormal": None
        },
        {
          "name": "左室舒张期容积",
          "reference": None,
          "value": "",
          "unit": "ml",
          "abnormal": None
        },
        {
          "name": "每搏输出量",
          "reference": None,
          "value": "",
          "unit": "ml",
          "abnormal": None
        },
        {
          "name": "左室收缩期容积",
          "reference": None,
          "value": "",
          "unit": "ml",
          "abnormal": None
        },
        {
          "name": "每分钟输出量",
          "reference": None,
          "value": "",
          "unit": "L/min",
          "abnormal": None
        },
        {
          "name": "左室射血分数",
          "reference": "50-80",
          "value": "",
          "unit": "%",
          "abnormal": None
        },
        {
          "name": "即时心率",
          "reference": None,
          "value": "",
          "unit": "bpm",
          "abnormal": None
        },
        {
          "name": "左室短轴缩短率",
          "reference": None,
          "value": "",
          "unit": "%",
          "abnormal": None
        }
  ]


# print(json.dumps(data, ensure_ascii=False, default=str))


prompt = """
你是一位医学文本解析专家。请从用户提供的口述转写文本中，提取甲状腺超声检查的关键指标。

处理规则（必须严格按此顺序执行）：

1. 直接提取：若文本中明确提到某指标的数值，直接提取并填入 value。
2. 计算衍生：若文本未直接提及某指标，但提供了其计算公式所需的子指标（例如 E/e’ = E峰 / 平均e’，其中平均e’ = (间隔侧e’ + 侧壁侧e’) / 2），请自动计算该数值并填入 value，并在 reference 中注明“计算值”。
3. 默认填充：若步骤1和2均无法获取数值，请根据患者性别和年龄（文本末尾提供），填入默认正常值（根据经验给出）


其他要求：

对于 abnormal 字段：若 value 有具体数值且 reference 有范围，则判断上升(↑)或下降(↓)；若为计算值或默认值，且未超过临床警戒线，则 abnormal 设为 null。 
针对每个指标给出数据来源（source）：1. 提出 2. 计算 3. 默认

请只输出一个 JSON 数组，不要添加任何其他说明文字。

[
{"name":"甲状腺右叶长径","reference":"40-60","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺右叶前后径","reference":"15-20","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺右叶左右径","reference":"15-20","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺左叶长径","reference":"40-60","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺左叶前后径","reference":"15-20","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺左叶左右径","reference":"15-20","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"甲状腺峡部厚度","reference":"≤3","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"颈部淋巴结短径","reference":"<8","value":"","unit":"mm","abnormal":null,"source":3},
{"name":"颈部淋巴结L/S比值","reference":"≥2","value":"","unit":null,"abnormal":null,"source":3},
{"name":"甲状腺结节最大径","reference":null,"value":"","unit":"mm","abnormal":null,"source":3},
{"name":"TI-RADS分类","reference":null,"value":"","unit":null,"abnormal":null,"source":3}
]

待解析文本：
"""


# param = {"randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "type": "update_templ", "templ_id": 3, "templ_content": prompt}
# # param = {"randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "type": "update_templ", "templ_content": prompt}
# response = requests.post("http://192.168.3.12:6080/chaosheng_bingli", json=param, timeout=30)
# # response = requests.post("http://192.168.124.8:6080/chaosheng_bingli", json=param, timeout=30)
# # 检查 HTTP 状态码
# response.raise_for_status()
# result = response.json()
# print(result)

















# print(f"{'心脏指标数据':^16}"+"1")
# print("心脏指标数据".center(39))
#
# print(f"{'心脏指标数据':<16}" + "1")      # 左对齐，宽度16，后面加"1"
# print("心脏指标数据".ljust(16) + "1")    # 同样效果
#
# str_d = {
#     "1": "34",
#     "2": "0.67",
#     "3": "76",
#     "4": "2.29",
#     "5": "29",
#     "6": "7.14",
#     "7": "29",
#     "8": "24",
#     "9": "8.78",
#     "10": "7.89",
#     "11": "6",
#     "12": "28",
#     "13": "19",
#     "14": "8",
#     "15": "38",
#     "16": "156",
#     "17": "38",
#     "18": "64",
#     "19": "40",
#     "20": "87",
#     "21": "12.16",
#     "22": "3.59",
#     "23": "10",
#     "24": "50",
#     "25": "0.72",
#     "26": "62",
#     "27": "0.77",
#     "28": "23",
#     "29": "0.82",
# }
#
#
# def pad_by_visual(text, target_width):
#     # 使用 GBK 编码计算视觉宽度（终端通常如此）
#     visual_len = len(text.encode('gbk', errors='ignore'))
#     if visual_len >= target_width:
#         return text
#     return text + ' ' * (target_width - visual_len)
#
# str_f = ''
# # 设定第一列视觉宽度为 22，第二列视觉宽度为 12，第三列视觉宽度为 22（可根据数据调整）
# # str_f = str_f + "心脏结构与尺寸".ljust(55) + "\n"
# # str_f = str_f + "-"*75 + "\n"
# str_f += pad_by_visual("左房前后径[25-40]", 23) + pad_by_visual(f"{str_d.get('1')} mm", 15) + pad_by_visual("左房容积", 23) + f"{str_d.get('2')} m/s \n"
# str_f += pad_by_visual("右室前后径[16-30]", 23) + pad_by_visual(f"{str_d.get('5')} mm", 15) + pad_by_visual("主动脉瓣环", 23) + f"{str_d.get('6')} m/s \n"
# str_f += pad_by_visual("主肺动脉径[16-30]", 23) + pad_by_visual(f"{str_d.get('7')} mm", 15) + pad_by_visual("左室后壁厚度", 23) + f"{str_d.get('8')} mmHg \n"
# str_f += pad_by_visual("室间隔厚度[8-12]", 23) + pad_by_visual(f"{str_d.get('9')} mm", 15) + pad_by_visual("升主动脉内径", 23) + f"{str_d.get('10')} cm/s \n"
# str_f += pad_by_visual("运动幅度-左室后壁", 23) + pad_by_visual(f"{str_d.get('11')} mm", 15) + pad_by_visual("左室舒张期内径", 23) + f"{str_d.get('12')} mmHg \n"
# str_f += pad_by_visual("运动幅度-室间隔", 23) + pad_by_visual(f"{str_d.get('3')} ml", 15) + pad_by_visual("左室收缩期内径", 23) + f"{str_d.get('4')} m/s \n"
#
# # str_f = str_f + "\n"
# # str_f = str_f + "心脏泵血功能".ljust(55) + "\n"
# # str_f = str_f + "-"*75 + "\n"
# str_f += pad_by_visual("左室舒张期容积", 23) + pad_by_visual(f"{str_d.get('13')} mm", 15) + pad_by_visual("即时心率", 23) + f"{str_d.get('14')} m/s \n"
# str_f += pad_by_visual("左室收缩期容积", 23) + pad_by_visual(f"{str_d.get('15')} mm", 15) + pad_by_visual("每搏输出量", 23) + f"{str_d.get('16')} ml \n"
# str_f += pad_by_visual("左室射血分数[50-80]", 23) + pad_by_visual(f"{str_d.get('17')} mm", 15) + pad_by_visual("每分钟输出量", 23) + f"{str_d.get('18')} ml \n"
# str_f += pad_by_visual("左室短轴缩短率", 23) + pad_by_visual(f"{str_d.get('19')} mm", 15) + '\n'
#
# # 血液流动与瓣膜
# # str_f = str_f + "\n"
# # str_f = str_f + "血液流动与瓣膜".ljust(55) + "\n"
# # str_f = str_f + "-"*75 + "\n"
# str_f += pad_by_visual("二尖瓣环间隔测", 23) + pad_by_visual(f"{str_d.get('21')} mm", 15) + pad_by_visual("二尖瓣A峰", 23) + f"{str_d.get('22')} L/min \n"
# str_f += pad_by_visual("二尖瓣环侧隔测", 23) + pad_by_visual(f"{str_d.get('23')} mm", 15) + pad_by_visual("二尖瓣E峰", 23) + f"{str_d.get('24')} m/s \n"
# str_f += pad_by_visual("三尖瓣反流流速", 23) + pad_by_visual(f"{str_d.get('25')} m/s", 15) + pad_by_visual("E/e'", 23) + f"{str_d.get('26')} bpm \n"
# str_f += pad_by_visual("肺动脉流速", 23) + pad_by_visual(f"{str_d.get('29')} m/s", 15) + pad_by_visual("主动脉流速", 23) + f"{str_d.get('28')} % \n"
# str_f += pad_by_visual("估测肺动脉压约", 23) + pad_by_visual(f"{str_d.get('27')} m/s", 15) + pad_by_visual("压力阶差", 23) + f"{str_d.get('28')} % \n"
#
#
#
# print(str_f)
# print()
# print()
# print()
# print()
# print()
#
#
#
#
#
#
#
#
# str_f = ''
# # 设定第一列视觉宽度为 22，第二列视觉宽度为 12，第三列视觉宽度为 22（可根据数据调整）
# str_f = str_f + "心脏结构与尺寸".ljust(55) + "\n"
# str_f = str_f + "-"*75 + "\n"
# str_f += pad_by_visual("左房前后径[25-40]", 18) + pad_by_visual(f"{str_d.get('1')} mm", 10) + pad_by_visual("左房容积", 18) + pad_by_visual(f"{str_d.get('2')} m/s ", 10) + pad_by_visual("左室舒张期容积", 23) + pad_by_visual(f"{str_d.get('13')} mm", 15) + pad_by_visual("即时心率", 23) + f"{str_d.get('14')} m/s \n"
# str_f += pad_by_visual("右室前后径[16-30]", 18) + pad_by_visual(f"{str_d.get('5')} mm", 10) + pad_by_visual("主动脉瓣环", 18) + pad_by_visual(f"{str_d.get('6')} m/s ", 10) + pad_by_visual("左室收缩期容积", 23) + pad_by_visual(f"{str_d.get('15')} mm", 15) + pad_by_visual("每搏输出量", 23) + f"{str_d.get('16')} ml \n"
# str_f += pad_by_visual("主肺动脉径[16-30]", 18) + pad_by_visual(f"{str_d.get('7')} mm", 10) + pad_by_visual("左室后壁厚度", 18) + pad_by_visual(f"{str_d.get('8')} mmHg ", 10) + pad_by_visual("左室射血分数[50-80]", 23) + pad_by_visual(f"{str_d.get('17')} mm", 15) + pad_by_visual("每分钟输出量", 23) + f"{str_d.get('18')} ml \n"
# str_f += pad_by_visual("室间隔厚度[8-12]", 18) + pad_by_visual(f"{str_d.get('9')} mm", 10) + pad_by_visual("升主动脉内径", 18) + pad_by_visual(f"{str_d.get('10')} m/s ", 10) + pad_by_visual("左室短轴缩短率", 23) + pad_by_visual(f"{str_d.get('19')} mm", 15) + '\n'
# str_f += pad_by_visual("运动幅度-左室后壁", 18) + pad_by_visual(f"{str_d.get('11')} mm", 10) + pad_by_visual("左室舒张期内径", 18) + f"{str_d.get('12')} mmHg \n"
# str_f += pad_by_visual("运动幅度-室间隔", 18) + pad_by_visual(f"{str_d.get('3')} ml", 10) + pad_by_visual("左室收缩期内径", 18) + f"{str_d.get('4')} m/s \n"
#
# # 血液流动与瓣膜
# str_f = str_f + "\n"
# str_f = str_f + "血液流动与瓣膜".ljust(55) + "\n"
# str_f = str_f + "-"*75 + "\n"
# str_f += pad_by_visual("二尖瓣环间隔测", 23) + pad_by_visual(f"{str_d.get('21')} mm", 15) + pad_by_visual("二尖瓣A峰", 23) + f"{str_d.get('22')} L/min \n"
# str_f += pad_by_visual("二尖瓣环侧隔测", 23) + pad_by_visual(f"{str_d.get('23')} mm", 15) + pad_by_visual("二尖瓣E峰", 23) + f"{str_d.get('24')} m/s \n"
# str_f += pad_by_visual("三尖瓣反流流速", 23) + pad_by_visual(f"{str_d.get('25')} m/s", 15) + pad_by_visual("E/e'", 23) + f"{str_d.get('26')} bpm \n"
# str_f += pad_by_visual("肺动脉流速", 23) + pad_by_visual(f"{str_d.get('29')} m/s", 15) + pad_by_visual("主动脉流速", 23) + f"{str_d.get('28')} % \n"
# str_f += pad_by_visual("估测肺动脉压约", 23) + pad_by_visual(f"{str_d.get('27')} m/s", 15) + pad_by_visual("压力阶差", 23) + f"{str_d.get('28')} % \n"
#
#
#
# print(str_f)
# print()
# print()
# print()
# print()
# print()
#
#
#
#
#
# def xinzang_zhibiao(ai_indicator):
#     def pad_by_visual(text, target_width):
#         # 使用 GBK 编码计算视觉宽度（终端通常如此）
#         visual_len = len(text.encode('gbk', errors='ignore'))
#         if visual_len >= target_width:
#             return text
#         return text + ' ' * (target_width - visual_len)
#
#     str_f = ''
#     try:
#         str_d = {}
#         for item in ai_indicator:
#             if item.get('value'):
#                 str_d[item.get('name')] = f"{item.get('value')}{item.get('unit')} {item.get('abnormal')}" if item.get('abnormal') and item.get('abnormal', '') not in ['null', "None"] else f"{item.get('value')}{item.get('unit')}"
#
#         str_f += (pad_by_visual("左房前后径[25-40]", 18) + pad_by_visual(f"{str_d.get('左房前后径')}", 8) +
#                   pad_by_visual("右室前后径[16-30]", 18) + pad_by_visual(f"{str_d.get('右室前后径')}", 8) +
#                   pad_by_visual("主肺动脉径[16-30]", 18) + pad_by_visual(f"{str_d.get('主肺动脉径')}", 8) +
#                   pad_by_visual("室间隔厚度[8-12]", 18) + pad_by_visual(f"{str_d.get('室间隔厚度')}", 8) +
#                   '\n')
#         str_f += (
#                 pad_by_visual("左室射血分数[50-60]", 18) + pad_by_visual(f"{str_d.get('左室射血分数')}", 8) +
#                 pad_by_visual("运动幅度-左室后壁", 18) + pad_by_visual(f"{str_d.get('运动幅度-左室后壁')}", 8) +
#                 pad_by_visual("运动幅度-室间隔", 18) + pad_by_visual(f"{str_d.get('运动幅度-室间隔')}", 8) +
#                 pad_by_visual("估测肺动脉压约", 18) + pad_by_visual(f"{str_d.get('估测肺动脉压约')}", 8) +
#                 '\n')
#
#         str_f += (
#                 pad_by_visual("左室舒张期内径", 18) + pad_by_visual(f"{str_d.get('左室舒张期内径')} ", 8) +
#                 pad_by_visual("左室收缩期内径", 18) + pad_by_visual(f"{str_d.get('左室收缩期内径')} ", 8) +
#                 pad_by_visual("左室短轴缩短率", 18) + pad_by_visual(f"{str_d.get('左室短轴缩短率')}", 8) +
#                 pad_by_visual("二尖瓣环间隔侧", 18) + pad_by_visual(f"{str_d.get('二尖瓣环间隔测')}", 8) +
#                 '\n')
#
#         str_f += (
#                 pad_by_visual("二尖瓣环侧隔侧", 18) + pad_by_visual(f"{str_d.get('二尖瓣环侧隔测')}", 8) +
#                 pad_by_visual("三尖瓣反流流速", 18) + pad_by_visual(f"{str_d.get('三尖瓣反流流速')}", 8) +
#                 pad_by_visual("左室舒张期容积", 18) + pad_by_visual(f"{str_d.get('左室舒张期容积')}", 8) +
#                 pad_by_visual("左室收缩期容积", 18) + pad_by_visual(f"{str_d.get('左室收缩期容积')}", 8) +
#                 '\n')
#         str_f += (
#                 pad_by_visual("左室后壁厚度", 18) + pad_by_visual(f"{str_d.get('左室后壁厚度')} ", 8) +
#                 pad_by_visual("升主动脉内径", 18) + pad_by_visual(f"{str_d.get('升主动脉内径')} ", 8) +
#                 pad_by_visual("每分钟输出量", 18) + pad_by_visual(f"{str_d.get('每分钟输出量')} ", 8) +
#                 pad_by_visual("每搏输出量", 18) + pad_by_visual(f"{str_d.get('每搏输出量')} ", 8) +
#                 '\n')
#
#         str_f += (
#                 pad_by_visual("主动脉瓣环", 18) + pad_by_visual(f"{str_d.get('主动脉瓣环')} ", 8) +
#                 pad_by_visual("肺动脉流速", 18) + pad_by_visual(f"{str_d.get('肺动脉流速')}", 8) +
#                 pad_by_visual("主动脉流速", 18) + pad_by_visual(f"{str_d.get('主动脉流速')} ", 8) +
#                 pad_by_visual("二尖瓣A峰", 18) + pad_by_visual(f"{str_d.get('二尖瓣A峰')} ", 8) +
#                 '\n')
#
#         str_f += (
#                 pad_by_visual("二尖瓣E峰", 18) + pad_by_visual(f"{str_d.get('二尖瓣E峰')} ", 8) +
#                 pad_by_visual("压力阶差", 18) + pad_by_visual(f"{str_d.get('压力阶差')} ", 8) +
#                 pad_by_visual("即时心率", 18) + pad_by_visual(f"{str_d.get('即时心率')} ", 8) +
#                 pad_by_visual("左房容积", 18) + pad_by_visual(f"{str_d.get('左房容积')} ", 8) +
#                 '\n')
#
#         str_f += (
#                 pad_by_visual("E/e", 18) + pad_by_visual(f"{str_d.get('E/e')} ", 8) +
#
#                 '\n\n')
#
#     except Exception:
#         print("指标数据解析异常")
#         pass
#     return str_f.replace('None', ' ')
#
#
#
# def xinzang_zhibiao11(ai_indicator):
#     """
#     指标排版输出。
#     规则：
#       · 自动读取 ai_indicator 中所有「有值」的指标，按出现顺序排版；
#       · 每行固定 4 组「名称 + 数值」；
#       · 名称列最小宽度 18，数值列固定宽度 8（终端视觉宽度，中文按 2 计）；
#       · 若某名称超过 18，则该列自动加宽，保证同行其余数据不错位。
#     """
#     KEY_WIDTH = 18       # 名称列最小宽度
#     VAL_WIDTH = 8        # 数值列固定宽度
#     PER_ROW   = 4        # 每行数据组数
#
#     # 名称 -> 展示文案（需要带参考范围 / 别名时在此登记；未登记的按 name 原样输出）
#     LABELS = {
#         '左房前后径':     '左房前后径[25-40]',
#         '右室前后径':     '右室前后径[16-30]',
#         '主肺动脉径':     '主肺动脉径[16-30]',
#         '室间隔厚度':     '室间隔厚度[8-12]',
#         '左室射血分数':   '左室射血分数[50-60]',
#         '二尖瓣环间隔测': '二尖瓣环间隔侧',
#         '二尖瓣环侧隔测': '二尖瓣环侧隔侧',
#     }
#
#     def visual_len(text):
#         """按 GBK 编码统计终端视觉宽度（中文 2，ASCII 1）。"""
#         return len(str(text).encode('gbk', errors='ignore'))
#
#     def pad_by_visual(text, width):
#         """右侧补空格到指定视觉宽度；已超宽则原样返回。"""
#         text = str(text)
#         gap = width - visual_len(text)
#         return text + ' ' * gap if gap > 0 else text
#
#     # ---------- 1. 解析数据 ----------
#     data = {}
#     try:
#         for item in ai_indicator:
#             name = (item.get('name') or '').strip()
#             value = item.get('value')
#             if not name or not value:
#                 continue
#
#             unit = item.get('unit') or ''
#             abnormal = item.get('abnormal')
#             text = f"{value}{unit}"
#             if abnormal and str(abnormal) not in ('null', 'None'):
#                 text += f" {abnormal}"
#
#             data[LABELS.get(name, name)] = text.strip()
#     except Exception:
#         print("指标数据解析异常")
#         return ''
#
#     if not data:
#         return ''
#
#     # ---------- 2. 计算每一列的名称宽度 ----------
#     items = list(data.items())
#     col_widths = [KEY_WIDTH] * PER_ROW
#     for idx, (label, _) in enumerate(items):
#         col = idx % PER_ROW
#         col_widths[col] = max(col_widths[col], visual_len(label))
#
#     # ---------- 3. 逐行拼接 ----------
#     lines = []
#     for start in range(0, len(items), PER_ROW):
#         chunk = items[start:start + PER_ROW]
#         line = ''.join(
#             pad_by_visual(label, col_widths[i]) + pad_by_visual(value, VAL_WIDTH)
#             for i, (label, value) in enumerate(chunk)
#         )
#         lines.append(line.rstrip())
#
#     return '\n'.join(lines)
#
#
#
#
# def xinzang_zhibiao22(ai_indicator, max_width=110):
#     """
#     心脏超声指标排版输出（自动列数 + 自动列宽）。
#
#     规则：
#       · 自动读取 ai_indicator 中所有「有值」的指标，按出现顺序排版；
#       · 优先每行 4 组「名称 + 数值」；
#       · 若 4 组总视觉宽度 > max_width，则尝试每行 3 组；若仍超宽，再尝试每行 2 组；
#       · 名称列最小宽度 18，数值列固定宽度 8（终端视觉宽度，中文按 2 计）；
#       · 若某名称超过最小宽度，则该列自动加宽，保证同行其余数据不错位。
#     """
#     KEY_WIDTH = 18       # 名称列最小宽度
#     VAL_WIDTH = 8        # 数值列固定宽度
#
#     # 名称 -> 展示文案（需要带参考范围 / 别名时在此登记；未登记的按 name 原样输出）
#     LABELS = {
#         '左房前后径':     '左房前后径[25-40]',
#         '右室前后径':     '右室前后径[16-30]',
#         '主肺动脉径':     '主肺动脉径[16-30]',
#         '室间隔厚度':     '室间隔厚度[8-12]',
#         '左室射血分数':   '左室射血分数[50-60]',
#         '二尖瓣环间隔测': '二尖瓣环间隔侧',
#         '二尖瓣环侧隔测': '二尖瓣环侧隔侧',
#     }
#
#     def visual_len(text):
#         """按 GBK 编码统计终端视觉宽度（中文 2，ASCII 1）。"""
#         return len(str(text).encode('gbk', errors='ignore'))
#
#     def pad_by_visual(text, width):
#         """右侧补空格到指定视觉宽度；已超宽则原样返回。"""
#         text = str(text)
#         gap = width - visual_len(text)
#         return text + ' ' * gap if gap > 0 else text
#
#     # ---------- 1. 解析数据 ----------
#     data = {}
#     try:
#         for item in ai_indicator:
#             name = (item.get('name') or '').strip()
#             value = item.get('value')
#             if not name or not value:
#                 continue
#
#             unit = item.get('unit') or ''
#             abnormal = item.get('abnormal')
#             text = f"{value}{unit}"
#             if abnormal and str(abnormal) not in ('null', 'None'):
#                 text += f" {abnormal}"
#
#             data[LABELS.get(name, name)] = text.strip()
#     except Exception:
#         print("指标数据解析异常")
#         return ''
#
#     if not data:
#         return ''
#
#     items = list(data.items())
#
#     # ---------- 2. 根据每行指标数计算列宽与总宽度 ----------
#     def try_layout(per_row):
#         """返回 (列宽列表, 满行总视觉宽度)。"""
#         cols = min(per_row, len(items))
#         col_widths = [KEY_WIDTH] * cols
#         for idx, (label, _) in enumerate(items):
#             col = idx % per_row
#             if col < cols:
#                 col_widths[col] = max(col_widths[col], visual_len(label))
#         total_width = sum(w + VAL_WIDTH for w in col_widths)
#         return col_widths, total_width
#
#     # ---------- 3. 选择每行指标数：4 -> 3 -> 2 ----------
#     chosen_per_row = 2
#     chosen_col_widths = None
#     for pr in (4, 3, 2):
#         col_widths, total_width = try_layout(pr)
#         if total_width <= max_width:
#             chosen_per_row = pr
#             chosen_col_widths = col_widths
#             break
#     else:
#         # 即使 2 列也超宽，仍按 2 列输出
#         chosen_per_row = 2
#         chosen_col_widths, _ = try_layout(2)
#
#     # ---------- 4. 逐行拼接 ----------
#     lines = []
#     for start in range(0, len(items), chosen_per_row):
#         chunk = items[start:start + chosen_per_row]
#         line_parts = []
#         for j, (label, value) in enumerate(chunk):
#             key_w = chosen_col_widths[j]
#             line_parts.append(pad_by_visual(label, key_w))
#             line_parts.append(pad_by_visual(value, VAL_WIDTH))
#         lines.append(''.join(line_parts).rstrip())
#
#     return '\n'.join(lines)
#
#
#
#
# def xinzang_zhibiao33(ai_indicator, max_width=110):
#     """
#     心脏超声指标排版输出（自动列数 + 自动列宽 + 值列强制分隔）。
#
#     规则：
#       · 自动读取 ai_indicator 中所有「有值」的指标，按出现顺序排版；
#       · 优先每行 4 组；若总宽 > max_width，降为 3 组；仍超宽再降为 2 组；
#       · 名称列最小宽度 18，数值列固定宽度 8；
#       · 数值列之后强制保留 1 个空格（VAL_GAP），避免值正好占满 8 宽时与下一列粘连；
#       · 名称列超过最小宽度时自动加宽，保证同行对齐。
#     """
#     KEY_WIDTH = 18       # 名称列最小宽度
#     VAL_WIDTH = 8        # 数值列固定宽度
#     VAL_GAP   = 1        # 数值列与下一名称列之间的强制分隔空格
#     PER_ROW_MAX = 4
#     PER_ROW_MIN = 2
#
#     LABELS = {
#         '左房前后径':     '左房前后径[25-40]',
#         '右室前后径':     '右室前后径[16-30]',
#         '主肺动脉径':     '主肺动脉径[16-30]',
#         '室间隔厚度':     '室间隔厚度[8-12]',
#         '左室射血分数':   '左室射血分数[50-60]',
#         '二尖瓣环间隔测': '二尖瓣环间隔侧',
#         '二尖瓣环侧隔测': '二尖瓣环侧隔侧',
#     }
#
#     def visual_len(text):
#         return len(str(text).encode('gbk', errors='ignore'))
#
#     def pad_by_visual(text, width):
#         text = str(text)
#         gap = width - visual_len(text)
#         return text + ' ' * gap if gap > 0 else text
#
#     # ---------- 1. 解析数据 ----------
#     data = {}
#     try:
#         for item in ai_indicator:
#             name = (item.get('name') or '').strip()
#             value = item.get('value')
#             if not name or not value:
#                 continue
#             unit = item.get('unit') or ''
#             abnormal = item.get('abnormal')
#             text = f"{value}{unit}"
#             if abnormal and str(abnormal) not in ('null', 'None'):
#                 text += f" {abnormal}"
#             data[LABELS.get(name, name)] = text.strip()
#     except Exception:
#         print("指标数据解析异常")
#         return ''
#
#     if not data:
#         return ''
#
#     items = list(data.items())
#     val_slot = VAL_WIDTH + VAL_GAP   # 值列实际占位
#
#     # ---------- 2. 按每行数计算列宽与总宽 ----------
#     def try_layout(per_row):
#         cols = min(per_row, len(items))
#         col_widths = [KEY_WIDTH] * cols
#         for idx, (label, _) in enumerate(items):
#             col = idx % per_row
#             if col < cols:
#                 col_widths[col] = max(col_widths[col], visual_len(label))
#         total_width = sum(w + val_slot for w in col_widths)
#         return col_widths, total_width
#
#     # ---------- 3. 选择每行数：4 -> 3 -> 2 ----------
#     chosen_per_row = PER_ROW_MIN
#     chosen_col_widths = None
#     for pr in range(PER_ROW_MAX, PER_ROW_MIN - 1, -1):
#         col_widths, total_width = try_layout(pr)
#         if total_width <= max_width:
#             chosen_per_row = pr
#             chosen_col_widths = col_widths
#             break
#     else:
#         chosen_col_widths, _ = try_layout(PER_ROW_MIN)
#
#     # ---------- 4. 逐行拼接 ----------
#     lines = []
#     for start in range(0, len(items), chosen_per_row):
#         chunk = items[start:start + chosen_per_row]
#         parts = []
#         for j, (label, value) in enumerate(chunk):
#             parts.append(pad_by_visual(label, chosen_col_widths[j]))
#             # 值列填充到 VAL_WIDTH，再强制追加 VAL_GAP 个空格
#             v = pad_by_visual(value, VAL_WIDTH)
#             if visual_len(v) <= VAL_WIDTH:
#                 v += ' ' * VAL_GAP
#             else:
#                 # 值本身已超过 8 宽，也至少补 1 个分隔空格
#                 v += ' ' * VAL_GAP
#             parts.append(v)
#         lines.append(''.join(parts).rstrip())
#
#     return '\n'.join(lines)
#
#
#
#
#
# def xinzang_zhibiao(ai_indicator):
#     try:
#         str_d = {}
#         for item in ai_indicator:
#             if item.get('value'):
#                 str_d[item.get('name')] = f"{item.get('value')} {item.get('unit')} {item.get('abnormal')}" if item.get('abnormal') and item.get('abnormal', '') not in ['null', "None"] else f"{item.get('value')} {item.get('unit')}"
#
#         str_f = f"""
# 二维及M型超声测量值:
# 左房前后径[25-40]: {str_d.get('左房前后径')}  左房容积: {str_d.get('左房容积')}  主动脉瓣环: {str_d.get('主动脉瓣环')}  升主动脉: {str_d.get('升主动脉内径')}
# 右室前后径[16-30]: {str_d.get('右室前后径')}  主肺动脉径[16-30]: {str_d.get('主肺动脉径')}
# 室间隔厚度[8-12]: {str_d.get('室间隔厚度')}  运动幅度：{str_d.get('运动幅度-室间隔')}  左室后壁厚度: {str_d.get('左室后壁厚度')}  运动幅度：{str_d.get('运动幅度-左室后壁')}
# 左室舒张期内径[20-50(女)/55（男）]: {str_d.get('左室舒张期内径')}  左室收缩期内径: {str_d.get('左室收缩期内径')}
# 频谱多普勒:
# 主动脉流速: {str_d.get('主动脉流速')}  肺动脉流速: {str_d.get('肺动脉流速')}  二尖瓣: E {str_d.get('二尖瓣E峰')}  A {str_d.get('二尖瓣A峰')}
# 组织多普勒： 二尖瓣环间隔侧e': {str_d.get('二尖瓣环间隔测')}  二尖瓣环侧隔侧e': {str_d.get('二尖瓣环侧隔测')}  E/e: {str_d.get('E/e')}
# 三尖瓣反流流速: {str_d.get('三尖瓣反流流速')}  压力阶差: {str_d.get('压力阶差')}  估测肺动脉压约: {str_d.get('估测肺动脉压约')}
# 左心收缩功能测定:
# 左室舒张期容积: {str_d.get('左室舒张期容积')}  左室收缩期容积: {str_d.get('左室收缩期容积')}  左室射血分数[50-80]: {str_d.get('左室射血分数')}  左室短轴缩短率: {str_d.get('左室短轴缩短率')}
# 每搏输出量: {str_d.get('每搏输出量')}  每分输出量: {str_d.get('每分钟输出量')}  即时心率: {str_d.get('即时心率')}
#                     """
#     except Exception:
#         print("指标数据解析异常")
#         pass
#     return str_f.replace('None', ' ')
#
#
#
# sql = "select * from V_XT_BG_TESTRESULT@xuetang where 住院号 = '163298' Order By 记录时间"
# patient_info = global_tools.call_new_his(sql, sys='nshis')
#
# for item in patient_info:
#     print(item)

# auto dip
API_KEY1 = "sk-34e7c54119f847258d43f40bc24111bd"

# pacs
API_KEY2 = "sk-f4e288071c6647d3976067bb48b3133f"


def query_balance():
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY2}'}
    response = requests.request("GET", "https://api.deepseek.com/user/balance", headers=headers, data={})
    print(f" {datetime.now()} 查询余额结果：{response.text}")
    if response:
        response = response.json()
        if Decimal(response['balance_infos'][0]['total_balance']) < Decimal('1'):
            return False
        return True
    return False


query_balance()


#  2026-10-16 10:11:03.974197 查询余额结果：{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"457.25","granted_balance":"401.71","topped_up_balance":"55.53"}]}
#  2026-10-16 10:18:13.014760 查询余额结果：{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"456.63","granted_balance":"401.10","topped_up_balance":"55.53"}]}
#  2026-10-16 14:46:37.659281 查询余额结果：{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"454.89","granted_balance":"399.36","topped_up_balance":"55.53"}]}




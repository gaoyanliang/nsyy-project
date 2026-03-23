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
from itertools import groupby
from operator import itemgetter
from typing import Dict, List
from urllib.parse import quote, unquote
from uuid import uuid4

import numpy as np
import pandas as pd
import pytesseract
import redis
import requests
import xlrd

from gylmodules import global_config, global_tools
from gylmodules.composite_appointment import ca_server
from gylmodules.composite_appointment.appt_config import APPT_ROOMS_KEY
from gylmodules.critical_value import cv_config, critical_value
from gylmodules.parking import parking_server
from gylmodules.shift_change import shift_change_config, shift_change_server
from gylmodules.shift_change.shift_change_server import get_complete_time_slot
from gylmodules.utils import queue_utils
# from gylmodules import global_tools, global_config
# from gylmodules.critical_value import critical_value
# from gylmodules.global_tools import fetch_yun_sign_img, upload_sign_file, encrypt_data
# from gylmodules.questionnaire.sq_server import query_test_result
# from gylmodules.shift_change import shift_change_config
# from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER
# from gylmodules.shift_change.shift_change_server import merge_patient_records, timed_execution
from gylmodules.utils.db_utils import DbUtil

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
#
#
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
# # start_time = time.time()
# # data = call_new_his(sql)
# # # data = query_menzhen(sql)
# # # print(data)
# # for d in data:
# #     print(d)
# # print('耗时：', time.time() - start_time, '数量: ', len(data))
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


# # ================================================
# # 综合预约排班数据生成
# # 将 nsyy_gyl.appt_schedules 中的排班数据插入到
# # nsyy_gyl.appt_schedules_doctor 中（需要确定构造哪一周的数据）
# # ================================================
#
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# # query_sql = f"select * from nsyy_gyl.appt_doctor where his_status = 1 "
# # doctors = db.query_all(query_sql)
#
# doctors = [{"id": 684}, {"id": 685}, {"id": 686}]
# doc_s_data = []
# for doctor in doctors:
#     # doc_s_data.append((doctor.get('id'), '2025-07-14', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-14', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-15', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-15', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-16', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-16', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-17', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-17', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-18', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-18', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-19', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-19', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-20', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-20', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-21', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-21', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-22', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-22', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-23', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-23', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-24', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-24', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-25', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-25', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-26', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-26', 2, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-27', 1, 1))
#     # doc_s_data.append((doctor.get('id'), '2025-07-27', 2, 1))
#
#
# # insert_sql = """INSERT IGNORE INTO nsyy_gyl.appt_schedules (did, shift_date, shift_type, status)
# #                                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
# # db.execute_many(insert_sql, doc_s_data, need_commit=True)
# # del db
# #


#
# #
# # print(f"{date.today()}")
# #
# #
# # message_server.push({"type": 100, "data": {"title": "title", "context": "context", "message": {}}}, 110100)
#
#
# data = (
#     'BG2025010800431F',
#     'BG2025011100195B',
#     'BG2025011600322F',
#     'BG2025060700164B'
# )
#
# # # # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# # #             global_config.DB_DATABASE_GYL)
# # db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# #
# # query_sql = f"select * from nsyy_gyl.cv_info where cv_id in {data} "
# # records = db.query_all(query_sql)
# #
# # print(len(records))
# #
# # for record in records:
# #     # critical_value.send_to_his(record)
# #     print(f"患者 {record.get('patient_name')} 危机值id {record.get('cv_id')} 报告id {record.get('report_id')}  上报时间 {record.get('alertdt').strftime('%Y-%m-%d %H:%M:%S')}")
# #
# # del db
#
#
# # sql_str = """INSERT INTO nsyy_gyl.sq_surveys_question_association (su_id, qu_id, order_by_id, qu_default_value, qu_units, step_size, ans_prefix, ans_suffix, visibility) VALUES (15, {qu_id}, {order_by_id}, None, None, None, None, None, 1);"""
# #
# # order_id = 1
# #
# # for i in range(1456, 1621):
# #     ret_st = sql_str.replace('{qu_id}', str(i))
# #     ret_st = ret_st.replace('{order_by_id}', f"{order_id:.2f}")
# #     print(ret_st)
# #     order_id = order_id + 1
#
#
# # # 查询 his 中 回传过的 pacs 危机值列表
# # query_sql = f"""
# # select weijizhiid from df_cdr.jyjc_weijizhi where weijizhiid like '%BG%' and fasongsj > '2025-01-01 00:00:00'
# # """
# #
# # pacs_cvs = global_tools.call_new_his_pg(query_sql)
# # print(pacs_cvs)
# #
# # pacs_cv_ids = [pacs_cv.get('weijizhiid') for pacs_cv in pacs_cvs]
# #
# # quoted_ids = [f"'{id}'" for id in pacs_cv_ids]
#
#
# data = (
#     'BG2025060700164B',
#     'BG2025060300660B',
#     'BG2025032400455B',
#     'BG2025032300027B',
#     'BG20250122J0007J',
#     'BG20250122J0008J'
# )
#
# # 检查结果字段长度超了，需要重新传
# data = ('BG2025051900741F')
#
# # # # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# # #             global_config.DB_DATABASE_GYL)
# # db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
# #
# # query_sql = f"select * from nsyy_gyl.cv_info where cv_id in {data} "
# # records = db.query_all(query_sql)
# #
# # print(len(records))
# #
# # for record in records:
# #     critical_value.send_to_his(record)
# #     # print(f"患者 {record.get('patient_name')} 危机值id {record.get('cv_id')} 报告id {record.get('report_id')}  上报时间 {record.get('alertdt').strftime('%Y-%m-%d %H:%M:%S')}")
# #     # sqd_data = critical_value.query_shenqingdan_info(record)
# #     # if sqd_data:
# #     #     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息 {sqd_data} ")
# #     # else:
# #     #     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息未查询到")
# #
# # del db
#
#


# # =============================================================================================
# # 向his上报危急值 start
# # =============================================================================================
#
# source_2_cv = global_tools.call_new_his_pg("select weijizhiid from df_cdr.jyjc_weijizhi where leixing = 1 and fasongsj >= '2025-08-01 00:00:00'")
#
# # print(source_2_cv)
#
# source_2_cv_ids = [cv.get('weijizhiid') for cv in source_2_cv]
# #
# #
# # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
#
# query_sql = f"select * from nsyy_gyl.cv_info where cv_source = 2 and cv_id not in {tuple(source_2_cv_ids)} and alertdt >= '2025-08-01 00:00:00' "
# query_sql = f"select * from nsyy_gyl.cv_info where cv_source = 2 and cv_id = '40214' "
# records = db.query_all(query_sql)
# del db
#
# print(len(records))
#
# for record in records:
#     record['cv_id'] = '40214-2'
#     critical_value.send_to_his(record)
#
# print(f"{record.get('alertdt')}  {record.get('cv_name')} 危机值ID {record.get('cv_id')} 患者姓名 {record.get('patient_name')} zhuyuanhao {record.get('patient_treat_id')}  {record.get('report_id')}", critical_value.query_shenqingdan_info(record))
# print(f"患者 {record.get('patient_name')} 危机值id {record.get('cv_id')} 报告id {record.get('report_id')} 危机值内容 {record.get('cv_name')}  上报时间 {record.get('alertdt').strftime('%Y-%m-%d %H:%M:%S')}")
# sqd_data = critical_value.query_shenqingdan_info(record)
# if sqd_data:
#     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息 {sqd_data} ")
# else:
#     print(f"患者 {record.get('patient_name')} 报告id {record.get('report_id')} 申请单信息未查询到")
#
#
# # =============================================================================================
# # 向his上报危急值 end
# # =============================================================================================














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


# import imaplib
# import email
# from email import policy
# from email.parser import BytesParser
#
# # IMAP server configuration
# IMAP_SERVER = '192.168.3.92'  # Replace with your IMAP server address
# EMAIL_ACCOUNT = 'admin@nsyy.com'  # Replace with your email address
# EMAIL_PASSWORD = 'nsyy0601'  # Replace with your email password
#
#
# import imaplib
# import email
# from email import policy
# from email.parser import BytesParser
# import html
# import re
#
# # IMAP 配置（请替换为你的实际信息）
# IMAP_SERVER = '192.168.3.92'      # 通常 iRedMail 是 imap.yourdomain.com
# EMAIL_ACCOUNT = 'admin@nsyy.com'     # 你的邮箱地址
# EMAIL_PASSWORD = 'nsyy0601'  # 你的密码（建议使用应用专用密码）
#
# def connect_to_mailbox():
#     mail = imaplib.IMAP4_SSL(IMAP_SERVER)
#     mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
#     mail.select('Sent')
#     return mail
#
# def extract_text_from_part(part):
#     """从单个邮件部件中提取文本内容"""
#     content_type = part.get_content_type()
#     charset = part.get_content_charset() or 'utf-8'
#
#     if content_type == 'text/plain':
#         payload = part.get_payload(decode=True)
#         try:
#             text = payload.decode(charset, errors='replace')
#             return text.strip(), 'plain'
#         except Exception as e:
#             print(f"[ERROR] 解码 plain 文本失败: {e}")
#             return "", 'plain'
#
#     elif content_type == 'text/html':
#         payload = part.get_payload(decode=True)
#         try:
#             html_content = payload.decode(charset, errors='replace')
#             # 可选：转义 HTML 标签为纯文本（便于阅读）
#             # 如果你想保留结构，可以保留原样
#             # text = html.unescape(html_content)  # 去除 HTML 实体
#             # 使用正则去除标签（简单处理）
#             text = re.sub(r'<[^>]+>', '', html_content)
#             text = re.sub(r'\s+', ' ', text).strip()
#             return text, 'html'
#         except Exception as e:
#             print(f"[ERROR] 解码 HTML 内容失败: {e}")
#             return "", 'html'
#
#     else:
#         return None, content_type  # 不处理其他类型
#
# def parse_email_body(msg):
#     """递归解析邮件正文，支持 multipart"""
#     body_parts = []
#
#     if msg.is_multipart():
#         for part in msg.walk():
#             content_disposition = part.get("Content-Disposition", "").lower()
#             # 跳过附件（除非你想保存）
#             if "attachment" in content_disposition:
#                 continue
#
#             text, ctype = extract_text_from_part(part)
#             if text is not None:
#                 body_parts.append({
#                     'type': ctype,
#                     'content': text
#                 })
#     else:
#         # 单部分邮件
#         text, ctype = extract_text_from_part(msg)
#         if text is not None:
#             body_parts.append({
#                 'type': ctype,
#                 'content': text
#             })
#
#     return body_parts
#
# def fetch_emails(mail):
#     status, messages = mail.search(None, 'ALL')
#     if status != 'OK':
#         print("未找到邮件！")
#         return
#
#     email_ids = messages[0].split()
#
#     for e_id in email_ids:
#         print("=" * 80)
#         print(f"正在处理邮件 ID: {e_id.decode()}")
#
#         status, msg_data = mail.fetch(e_id, '(RFC822)')
#         for response_part in msg_data:
#             if isinstance(response_part, tuple):
#                 msg = BytesParser(policy=policy.default).parsebytes(response_part[1])
#
#                 subject = msg.get('subject', '').strip()
#                 from_ = msg.get('from', '').strip()
#                 to = msg.get('to', '').strip()
#                 date = msg.get('date', '').strip()
#
#                 print(f"主题: {subject}")
#                 print(f"发件人: {from_}")
#                 print(f"收件人: {to}")
#                 print(f"日期: {date}")
#
#                 # 解析正文
#                 body_parts = parse_email_body(msg)
#
#                 for idx, part in enumerate(body_parts):
#                     print(f"\n--- 正文部分 {idx+1} ({part['type']}) ---")
#                     print(part['content'])
#
#                 print("\n" + "=" * 80)
#
# def main():
#     mail = connect_to_mailbox()
#     try:
#         fetch_emails(mail)
#     finally:
#         mail.logout()
#
# if __name__ == "__main__":
#     main()







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






# import pandas as pd
# from pypinyin import lazy_pinyin
# from collections import defaultdict
#
# # ===== 配置 =====
# excel_path = "/Users/gaoyanliang/Downloads/邮箱账号.xls"
# output_path = excel_path  # 写回同一个文件
# sheet_index = 0  # 第一个工作表
# name_column = "姓名"  # 表格中的列名
# domain = "nsyy.com"   # 邮箱域名，如需要拼邮箱完整地址可接上
#
# # ===== 工具函数：将中文姓名转为拼音账号 =====
# def name_to_pinyin(name: str) -> str:
#     """
#     把中文名字转成 pinyin，姓和名之间加点：
#     李献哲  → li.xianzhe
#     马某某  → ma.moumou
#     """
#     if not isinstance(name, str):
#         return ""
#
#     pinyin_list = lazy_pinyin(name)
#     if len(pinyin_list) == 1:
#         # 单字名
#         return pinyin_list[0]
#     else:
#         # 第一个字：姓
#         last_name = pinyin_list[0]
#         # 剩下部分：名
#         first_name = "".join(pinyin_list[1:])
#         return f"{last_name}.{first_name}"
#
# # ===== 主流程 =====
# df = pd.read_excel(excel_path, sheet_name=sheet_index)
#
# if name_column not in df.columns:
#     raise ValueError(f"找不到列名：{name_column}")
#
# # 创建一个计数字典，用于处理重名
# account_counter = defaultdict(int)
# accounts = []
#
# for name in df[name_column]:
#     base = name_to_pinyin(str(name))
#
#     # 避免空名
#     if base == "":
#         accounts.append("unknown")
#         continue
#
#     # 检查重复
#     if account_counter[base] == 0:
#         account = base
#     else:
#         account = f"{base}{account_counter[base]}"
#
#     account_counter[base] += 1
#     accounts.append(account)
#
# # 写入新列
# df["邮箱账号"] = [f"{acc}" for acc in accounts]
# df["邮箱账号-完整"] = [f"{acc}@{domain}" for acc in accounts]
#
#
# # 保存
# df.to_excel(output_path, index=False, engine="openpyxl")
#
# print(f"生成完成！共生成 {len(df)} 个邮箱账号 → {output_path}")




# import pandas as pd
# from pypinyin import lazy_pinyin
# from collections import defaultdict
#
# # ===== 配置 =====
# excel_path = "/Users/gaoyanliang/Downloads/邮箱账号.xls"
# output_path = excel_path  # 写回同一个文件
# sheet_index = 0  # 第一个工作表
# name_column = "邮箱账号"  # 表格中的列名
# domain = "nsyy.com"   # 邮箱域名，如需要拼邮箱完整地址可接上
#
# # ===== 主流程 =====
# df = pd.read_excel(excel_path, sheet_name=sheet_index)
#
# # if name_column not in df.columns:
# #     raise ValueError(f"找不到列名：{name_column}")
#
# # 创建一个计数字典，用于处理重名
# account_counter = defaultdict(int)
# accounts = []
#
# for index, row in df.iterrows():
#     accounts.append({
#         "name": row[3],
#         "dept": row[2],
#         "account": row[65],
#         "emp_num": row[64]
#     })
#
# emp_map = {}
# for item in accounts:
#     # print(item)
#     emp_map[item.get("emp_num")] = item
#
# print(emp_map)

# print(', '.join(f'"{item.get("account")}"' for item in accounts))

# groups = defaultdict(list)
#
# for item in accounts:
#     groups[item["dept"]].append(item)
#
# result = []
# for dept, users in groups.items():
#     group_obj = {
#         "user_account": users[0].get('account'),  # 你没指定谁是群组所有者，我先用 dept，如果不对改成固定 admin
#         "user_name": users[0].get('name'),
#         "mail_group_name": dept,
#         "mail_group_description": f"{dept} 部门邮箱群组",
#         "user_list": [
#             {"user_account": u["account"], "user_name": u["name"]}
#             for u in users
#         ],
#         "is_public": 0
#     }
#     result.append(group_obj)
#
# for item in result:
#     print(item)





#
#
# # # db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
# #             global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")
#
# query_sql = f"select * from nsyy_gyl.ehp_reports where patient_id is not null "
# records = db.query_all(query_sql)
#
# sql = """SELECT a.id 挂号id, a.病人id, a.门诊号, a.姓名 AS 患者姓名, a.性别, a.年龄, b.名称 AS 就诊科室,
#         a.执行人 AS 医生姓名, a.发生时间 as 就诊日期, TO_CHAR(c.出生日期, 'YYYY/MM/DD') as 出生日期, c.家庭电话 联系电话, c.身份证号, c.家庭地址 现住址
#         FROM 病人挂号记录 a LEFT JOIN 部门表 b ON a.执行部门id = b.id
#         join 病人信息 c on a.病人id = c.病人id WHERE a.记录状态 = 1
#         and TRUNC(a.发生时间) = TO_DATE('{date_str}', 'YYYY-MM-DD')
#         and a.门诊号 = '{register_id}' order by a.发生时间 desc """
#
# for item in records:
#     patient_id = item.get("patient_id")
#     if patient_id and len(patient_id) == 10:
#         report_date = item.get("report_time").strftime("%Y-%m-%d")
#         data = call_new_his_local(sql.replace('{register_id}', patient_id).replace('{date_str}', report_date))
#         if not data:
#             print("没有数据", item)
#             continue
#         print(item.get('report_id'), data)
#         update_sql = """update nsyy_gyl.ehp_reports set patient_id = %s where report_id = %s"""
#         db.execute(update_sql, args=(data.get('病人id'), item.get('report_id')), need_commit=True)
#
# del db



# import top.api
#
# '''
# 这边可以设置一个默认的appkey和secret，当然也可以不设置
# 注意：默认的只需要设置一次就可以了
#
# '''
# top.setDefaultAppInfo("35075242", "284fcbdb6bfde85e1ae69f301559db95")
#
# '''
# 使用自定义的域名和端口（测试沙箱环境使用）
# a = top.api.UserGetRequest("gw.api.tbsandbox.com",80)
#
# 使用自定义的域名（测试沙箱环境使用）
# a = top.api.UserGetRequest("gw.api.tbsandbox.com")
#
# 使用默认的配置（调用线上环境）
# a = top.api.UserGetRequest()
#
# '''
# # a = top.api.UserGetRequest()
# a = top.api.AppipGetRequest()
#
# '''
# 可以在运行期替换掉默认的appkey和secret的设置
# a.set_app_info(top.appinfo("appkey","*******"))
# '''
#
# a.fields = "nick"
#
# try:
#     f = a.getResponse()
#     print(f)
# except Exception as e:
#     print(e)



# # 读取表中的追溯码数据
#
# def get_zhuisu_dict(file_path):
#     ret_data = []
#     # 将 excel 中的数据写入数据库
#     df = pd.read_excel(file_path)
#     # 获取文档的长度
#     length = len(df)
#     for i in range(0, length):
#         # 数据转字符类型
#         record = df.loc[i].values
#         ret_data.append({
#             "his-jiageid": record[0],
#             "his药品名称": record[1],
#             "his批准文号": record[3],
#             "his-guojiaypmc": record[4],
#             "追溯码": record[5],
#         })
#     return ret_data
#
#
# from topsdk.ability2940.request.alibaba_alihealth_drugtrace_top_yljg_query_codedetail_request import *
# # 根据追溯码查询药品信息
# def get_yaopin_info_from_ali(codes):
#     import urllib3
#     from urllib3.exceptions import InsecureRequestWarning
#     urllib3.disable_warnings(InsecureRequestWarning)
#
#     from topsdk.client import TopApiClient,TopException
#     from topsdk.ability2940.ability2940 import Ability2940
#
#     # create Client
#     client = TopApiClient(appkey='35075242', app_sercet='284fcbdb6bfde85e1ae69f301559db95', top_gateway_url='https://eco.taobao.com/router/rest',verify_ssl=False)
#     ability = Ability2940(client=client)
#
#     # create request
#     request = AlibabaAlihealthDrugtraceTopYljgQueryCodedetailRequest()
#     request.ref_ent_id = '2c9194c61f491ebc011f6420d3cc51c3'
#     request.codes = codes
#     try:
#         response = ability.alibaba_alihealth_drugtrace_top_yljg_query_codedetail(request)
#         return response.get('result', {}).get('models', [])
#     except TopException as e:
#         print("查询异常", codes, e)
#         return []
#
#
# # 将查询到的药品信息整理好写入表格
# def export_drugtrace_to_excel(models, file_path):
#     from openpyxl import Workbook
#     wb = Workbook()
#     ws = wb.active
#     ws.title = "药品追溯结果"
#
#     # 表头
#     headers = [
#         "his价格id", "追溯码", "his批准文号", "his药品名称", "医保药品名称", "药品名称",
#          "码状态", "码等级(3大码 2中码 1小码)",
#         "药品类型描述", "包装规格", "制剂规格", "剂型描述", "有效期", "批准文号", "药品id",
#         "企业名称", "企业id",
#         "批次号", "生产日期", "原始生产日期", "有效期至", "原始有效期", "最小包装数量"
#     ]
#     ws.append(headers)
#
#     for m in models:
#         produce = m.get("code_produce_info_d_t_o", {}).get("produce_info_list", [{}])[0]
#         drug = m.get("drug_ent_base_d_t_o", {})
#         ent = m.get("p_user_ent_d_t_o", {})
#         status = m.get("code_status_type_d_t_o", {})
#
#         ws.append([
#             m.get("his-jiageid"),
#             m.get("code"),
#             m.get("his批准文号"),
#             m.get("his药品名称"),
#             m.get("his-guojiaypmc"),
#             drug.get("physic_name"),
#
#             status.get("code_status"),
#             m.get("package_level"),
#
#             drug.get("prepn_type_desc"),
#             drug.get("pkg_spec_crit"),
#             drug.get("prepn_spec"),
#             drug.get("prepn_type_desc"),
#             drug.get("exprie"),
#             drug.get("approval_licence_no"),
#             drug.get("drug_ent_base_info_id"),
#             ent.get("ent_name"),
#             ent.get("ref_ent_id"),
#             produce.get("batch_no"),
#             produce.get("produce_date_str"),
#             produce.get("original_produce_date"),
#             produce.get("expire_date"),
#             produce.get("original_expire_date"),
#             produce.get("pkg_amount"),
#         ])
#
#     wb.save(file_path)


# # ============ 批量跑，每次跑 5000条左右
#
# zhuisu_data = get_zhuisu_dict("/Users/gaoyanliang/Downloads/output_part_10.xlsx")
#
# models = []
# for item in zhuisu_data:
#     code = str(item.get("追溯码"))
#     if code.__contains__(","):
#         codes = code.split(",")
#         # codes = [codes[0]]
#     elif code.__contains__("|"):
#         codes = code.split("|")
#         # codes = [codes[0]]
#     else:
#         codes = [code]
#
#     if not codes or not codes[0]:
#         print(item)
#         continue
#
#     code_dict = {}
#     for cd in codes:
#         raw = cd.strip()
#         m = re.search(r"\d+", raw)
#         if m:
#             code_dict[str(m.group())] = {}
#
#     if not code_dict:
#         print("无法提取追溯码：", item)
#         continue
#
#     rets = get_yaopin_info_from_ali(list(code_dict.keys()))
#
#     if not rets:
#         models.append({
#             "his-jiageid": item.get("his-jiageid"),
#             "his批准文号": item.get("his批准文号"),
#             "his-guojiaypmc": item.get("his-guojiaypmc"),
#             "his药品名称": item.get("his药品名称"),
#             "追溯码": item.get("追溯码"),
#             "code": code,
#         })
#     else:
#         ret = {}
#         ret['his-jiageid'] = item.get("his-jiageid")
#         ret['his批准文号'] = item.get("his批准文号")
#         ret['his-guojiaypmc'] = item.get("his-guojiaypmc")
#         ret['his药品名称'] = item.get("his药品名称")
#         ret['追溯码'] = item.get("追溯码")
#         for r in rets:
#             code_dict[r.get("code")] = r
#
#         for k, v in code_dict.items():
#             if not v:
#                 ret['code'] = k
#                 models.append(ret)
#             else:
#                 models.append({**ret, **v})
#
# export_drugtrace_to_excel(models, f"/Users/gaoyanliang/Downloads/his药品名称对应关系_10.xlsx")









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








# import pandas as pd
#
# df = pd.read_excel("/Users/gaoyanliang/Downloads/病案质控列表.xlsx")
#
# def safe_filename(name: str) -> str:
#     return name.replace("/", "_").replace("\\", "_").strip()
#
# for dept, sub_df in df.groupby("出院科室"):
#     filename = safe_filename(dept)
#     sub_df.to_excel(f"{filename}.xlsx", index=False)








# import openpyxl
#
# excel_path = '/Users/gaoyanliang/Downloads/dat_202603031602.xlsx'
# num = 0  # 工作表索引，openpyxl从0开始计数
#
# # 打开工作簿
# wbook = openpyxl.load_workbook(excel_path, data_only=True)  # data_only获取计算后的值
#
# # 获取工作表
# sheet_names = wbook.sheetnames
# sheet = wbook[sheet_names[num]]  # 通过索引获取工作表
#
# # 获取所有行数据
# data_list = []
# for row in sheet.iter_rows(min_row=3, values_only=True):  # 从第3行开始
#     if row[6]:
#         print({"dept_id": row[4], "user_id": row[1], "key": row[6]})
#         data_list.append({"dept_id": row[4], "user_id": row[1], "key": row[6]})
#
#
# print(f"总共 {len(data_list)} 行数据")
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# values1 = []
# values2 = []
# for item in data_list:
#     values1.append((item.get('dept_id'), item.get('user_id'), item.get('key')))
#     values2.append((item.get('dept_id'), item.get('user_id')))
#
# insert_sql = """INSERT INTO nsyy_gyl.file_dept_permission (dept_id, user_id) VALUES (%s, %s)
#                ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)"""
# db.execute_many(insert_sql, args=values2, need_commit=True)
#
# del db






import json
import time
from datetime import datetime, date
import os
import requests
import base64
from itertools import groupby

import redis
import netifaces as ni
import xlrd

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.critical_value.critical_value import call_third_systems_obtain_data
from gylmodules.critical_value import cv_config
from gylmodules.utils.db_utils import DbUtil
from suds.client import Client

from zeep import Client
from zeep.exceptions import Fault
from zeep.transports import Transport
import logging
import requests

# data = {'msg_list': [{'socket_data': {
#     "type": 400,
#     "data": {
#         "title": "危急值上报反馈",
#         "context": "test"
#     }},
#     'pers_id': int(9797)}]}
# headers = {'Content-Type': 'application/json'}
# response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
# print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", data, "user_id: ")

# data = call_third_systems_obtain_data('send_wx_msg', {
#     "type": "send_wx_msg",
#     "key_d": {"type": 71, "process_id": 11527, "action": 4, "title": "危急值上报反馈", "content": "msg"},
#     "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#     "pers_id": 110100,
#     "force_notice": 1})
#
# print(data)




# json_data =  {'pat_no': '398709', 'pat_type': 3, 'record': {'id': 3271, 'cv_id': '8807', 'alertdt': datetime(2024, 7, 1, 14, 29, 29), 'state': 7, 'cv_source': 2, 'alertman': '2795', 'alertman_name': '张萌萌', 'alertman_pers_id': '110229', 'alert_dept_id': 144, 'alert_dept_name': '医学检验科', 'patient_type': 3, 'patient_treat_id': '398709', 'patient_name': '谢春香', 'patient_gender': '2', 'patient_age': '74岁', 'patient_phone': None, 'patient_bed_num': '65', 'req_docno': '袁苗', 'ward_id': 1001000, 'ward_name': '神经外科五病区护理单元', 'dept_id': 94143, 'dept_name': '神经外科五病区', 'cv_type': None, 'cv_name': '*钾（离子选择性电极）', 'cv_result': '2.7', 'cv_unit': 'mmol/L', 'cv_ref': '3.5-5.3', 'cv_flag': 'L', 'redo_flag': '2', 'alertrules': '<2.8000', 'handle_doctor_id': None, 'handle_doctor_name': None, 'handle_time': None, 'analysis': None, 'method': None, 'time': datetime(2024, 7, 1, 14, 29, 43), 'nurse_recv_id': None, 'nurse_recv_name': None, 'nurse_recv_time': None, 'nurse_recv_info': None, 'nurse_send_time': None, 'nursing_record': None, 'nursing_record_time': None, 'doctor_recv_id': 1034, 'doctor_recv_name': '乔路宽', 'doctor_recv_time': datetime(2024, 7, 1, 18, 11, 4), 'is_nurse_recv_timeout': 1, 'is_nurse_send_timeout': 0, 'is_doctor_recv_timeout': 1, 'is_doctor_handle_timeout': 0, 'is_timeout': 0, 'nurse_recv_timeout': 420, 'nurse_send_timeout': 60, 'doctor_recv_timeout': 300, 'doctor_handle_timeout': 120, 'total_timeout': 600}, 'handler_name': '乔路宽', 'timer': '2024-07-01 18:11:28', 'method': '补钾治疗', 'analysis': '低钾'}


json_data =  {'pat_no': '394955', 'pat_type': 3, 'record': {'id': 3303, 'cv_id': '8824', 'alertdt': datetime(2024, 7, 2, 7, 3, 31), 'state': 7, 'cv_source': 2, 'alertman': '0601', 'alertman_name': '杨瀚', 'alertman_pers_id': '10323', 'alert_dept_id': 144, 'alert_dept_name': '医学检验科', 'patient_type': 3, 'patient_treat_id': '394955', 'patient_name': '聂子政', 'patient_gender': '1', 'patient_age': '73岁', 'patient_phone': None, 'patient_bed_num': '4', 'req_docno': '刘军', 'ward_id': 1001120, 'ward_name': 'CCU护理单元', 'dept_id': 1000421, 'dept_name': '麻醉重症监护病房(AICU)', 'cv_type': None, 'cv_name': '*钠（离子选择性电极）', 'cv_result': '161', 'cv_unit': 'mmol/L', 'cv_ref': '137-147', 'cv_flag': 'H', 'redo_flag': '2', 'alertrules': '>160.0000', 'handle_doctor_id': None, 'handle_doctor_name': None, 'handle_time': None, 'analysis': None, 'method': None, 'time': datetime(2024, 7, 2, 7, 4, 13), 'nurse_recv_id': None, 'nurse_recv_name': None, 'nurse_recv_time': None, 'nurse_recv_info': None, 'nurse_send_time': None, 'nursing_record': None, 'nursing_record_time': None, 'doctor_recv_id': 740, 'doctor_recv_name': '刘军', 'doctor_recv_time': datetime(2024, 7, 2, 7, 52, 21), 'is_nurse_recv_timeout': 1, 'is_nurse_send_timeout': 0, 'is_doctor_recv_timeout': 1, 'is_doctor_handle_timeout': 0, 'is_timeout': 0, 'nurse_recv_timeout': 420, 'nurse_send_timeout': 60, 'doctor_recv_timeout': 300, 'doctor_handle_timeout': 120, 'total_timeout': 600}, 'handler_name': '刘军', 'timer': '2024-07-02 07:54:16', 'method': '加强鼻饲温开水 200ml q4h', 'analysis': '患者食管癌术后，禁食水'}



def medical_record_writing_back(json_data):
    try:
        sql = ''
        pat_type = int(json_data.get('pat_type'))
        pat_no = int(json_data.get('pat_no'))
        if pat_type in (1, 2):
            # 门诊/急诊
            sql = f'select 病人ID as pid, NO as hid from 病人挂号记录 where 门诊号 = \'{pat_no}\' order by 登记时间 desc'
        elif pat_type == 3:
            # 住院
            sql = f'select 病人id as pid, 主页id as hid from 病案主页 where 住院号 = \'{pat_no}\' order by 主页id desc '

        param = {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": sql
        }
        data = call_third_systems_obtain_data('orcl_db_read', param)
        if data:
            record = json_data.get('record')
            body = ''
            recv_time = record.get('time').strftime("%Y-%m-%d %H:%M:%S")
            body = body + "于 " + recv_time + "接收到 " + str(record.get('alert_dept_name')) \
                   + " 推送的危机值: [" + str(record.get('cv_name')) + "]"
            body = body + " " + str(record.get('cv_result'))
            if record.get('cv_unit'):
                body = body + " " + record.get('cv_unit')

            body = body + "医生 " + json_data.get('handler_name') + " " + json_data.get('timer') + "处理了该危机值"
            if json_data.get('analysis'):
                body = body + " 原因分析: " + json_data.get('analysis')
            if json_data.get('method'):
                body = body + " 处理方法: " + json_data.get('method')
            pid = data[0].get('PID', 0)
            hid = data[0].get('HID', 0)
            param = {
                "type": "his_procedure",
                "procedure": "jk_p_Pat_List",
                "病人id": pid,
                "主页id": hid,
                "内容": body,
                "分类": "3",
                "记录人": json_data.get('handler_name'),
                "审核时间": json_data.get('timer'),
                "医嘱名称": record.get('cv_name'),
                "分类名": "危机值记录",
                "标签说明": record.get('cv_name')
            }
            data = call_third_systems_obtain_data('his_procedure', param)
            print(data)
    except Exception as e:
        print('病历回写异常：param = ', param, " json_data = ", json_data, " 异常信息 = ", e)


medical_record_writing_back(json_data)











#
# data = {'msg_list': [{'socket_data': {
#     "type": 400,
#     "data": {
#         "title": "危急值上报反馈",
#         "context": "患者 xxx 的危急值，已通知相关科室"
#     }},
#     'pers_id': 10013}]}
#
#
# headers = {'Content-Type': 'application/json'}
# response = requests.post(global_config.socket_push_url, data=json.dumps(data), headers=headers)
# print("Socket Push Status: ", response.status_code, "Response: ", response.text, "socket_data: ", data,
#       "user_id: ", 110100)
#







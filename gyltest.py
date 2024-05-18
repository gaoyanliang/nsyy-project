import json
import time
from datetime import datetime, timedelta, date
import os, requests
import base64

import redis
import netifaces as ni
import xlrd

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.composite_appointment.appt_config import APPT_DOCTOR_ADVICE_KEY
from gylmodules.utils.db_utils import DbUtil





data = [
        {
            "NO": "Y0483973",
            "医嘱内容": "颅内多普勒血流图(TCD)",
            "医嘱序号": 123550820,
            "发生时间": "Sat, 18 May 2024 08:42:39 GMT",
            "姓名": "陈建敏",
            "实收金额": 100.0,
            "执行科室": "彩超室",
            "执行部门ID": 241,
            "收费唯一标识": 257152006,
            "检查明细项": "颅内多普勒血流图(TCD)",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485240",
            "医嘱内容": "经颅多普勒超声发泡试验",
            "医嘱序号": 123561026,
            "发生时间": "Sat, 18 May 2024 10:22:17 GMT",
            "姓名": "陈建敏",
            "实收金额": 50.0,
            "执行科室": "彩超室",
            "执行部门ID": 241,
            "收费唯一标识": 257162277,
            "检查明细项": "经颅多普勒超声发泡试验",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485240",
            "医嘱内容": "右心声学造影",
            "医嘱序号": 123561029,
            "发生时间": "Sat, 18 May 2024 10:22:17 GMT",
            "姓名": "陈建敏",
            "实收金额": 48.0,
            "执行科室": "彩超室",
            "执行部门ID": 241,
            "收费唯一标识": 257162275,
            "检查明细项": "右心声学造影",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485243",
            "医嘱内容": "静脉穿刺置管术",
            "医嘱序号": 123561030,
            "发生时间": "Sat, 18 May 2024 10:23:01 GMT",
            "姓名": "陈建敏",
            "实收金额": 13.92,
            "执行科室": "彩超室",
            "执行部门ID": 241,
            "收费唯一标识": 257162274,
            "检查明细项": "静脉穿刺置管术",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485244",
            "医嘱内容": "一次性静脉留置针 0.7×19mm（24G×0.75IN",
            "医嘱序号": 123561031,
            "发生时间": "Sat, 18 May 2024 10:23:01 GMT",
            "姓名": "陈建敏",
            "实收金额": 2.45,
            "执行科室": "彩超室",
            "执行部门ID": 241,
            "收费唯一标识": 257162276,
            "检查明细项": "一次性静脉留置针",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485241",
            "医嘱内容": "0.9%氯化钠注射液(集采)(双阀)(50ml:0.45g)",
            "医嘱序号": 123561027,
            "发生时间": "Sat, 18 May 2024 10:25:24 GMT",
            "姓名": "陈建敏",
            "实收金额": 1.12,
            "执行科室": "门诊药房",
            "执行部门ID": 245,
            "收费唯一标识": 257162278,
            "检查明细项": "0.9%氯化钠注射液(集采)(双阀)",
            "病人ID": 3513702
        },
        {
            "NO": "Y0486248",
            "医嘱内容": "阿司匹林肠溶片(100mg*30)",
            "医嘱序号": 123568640,
            "发生时间": "Sat, 18 May 2024 23:00:00 GMT",
            "姓名": "陈建敏",
            "实收金额": 15.05,
            "执行科室": "门诊药房",
            "执行部门ID": 245,
            "收费唯一标识": 257191997,
            "检查明细项": "阿司匹林肠溶片",
            "病人ID": 3513702
        },
        {
            "NO": "Y0486248",
            "医嘱内容": "(京新)瑞舒伐他汀钙片(10mg*28片(集采))",
            "医嘱序号": 123568642,
            "发生时间": "Sat, 18 May 2024 23:00:00 GMT",
            "姓名": "陈建敏",
            "实收金额": 11.0,
            "执行科室": "门诊药房",
            "执行部门ID": 245,
            "收费唯一标识": 257191998,
            "检查明细项": "(京新)瑞舒伐他汀钙片",
            "病人ID": 3513702
        },
        {
            "NO": "Y0486248",
            "医嘱内容": "银杏蜜环口服溶液(10ml*12支/盒)",
            "医嘱序号": 123568644,
            "发生时间": "Sat, 18 May 2024 12:00:00 GMT",
            "姓名": "陈建敏",
            "实收金额": 128.1,
            "执行科室": "门诊药房",
            "执行部门ID": 245,
            "收费唯一标识": 257191999,
            "检查明细项": "银杏蜜环口服溶液",
            "病人ID": 3513702
        },
        {
            "NO": "Y0485242",
            "医嘱内容": "静脉注射",
            "医嘱序号": 123561028,
            "发生时间": "Sat, 18 May 2024 17:00:00 GMT",
            "姓名": "陈建敏",
            "实收金额": 11.2,
            "执行科室": "急诊内科",
            "执行部门ID": 1000680,
            "收费唯一标识": 257162273,
            "检查明细项": "静脉注射(或静脉采血)",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肾功能3项（BUN、Cr、UA）",
            "医嘱序号": 123546388,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 4.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149172,
            "检查明细项": "尿素测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肾功能3项（BUN、Cr、UA）",
            "医嘱序号": 123546388,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 13.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149173,
            "检查明细项": "肌酐测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肾功能3项（BUN、Cr、UA）",
            "医嘱序号": 123546388,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 6.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149174,
            "检查明细项": "血清尿酸测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483613",
            "医嘱内容": "肾功能3项（BUN、Cr、UA）(血清)",
            "医嘱序号": 123546389,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.6,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149153,
            "检查明细项": "静脉注射(或静脉采血)",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483613",
            "医嘱内容": "肾功能3项（BUN、Cr、UA）(血清)",
            "医嘱序号": 123546389,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 1.2,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149175,
            "检查明细项": "真空采血管(特殊采血管）",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血常规(机器法五类)",
            "医嘱序号": 123546390,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 20.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149154,
            "检查明细项": "血细胞分析或血常规(机器法五类)",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483613",
            "医嘱内容": "血常规(机器法五类)(抗凝血EDTA)",
            "医嘱序号": 123546391,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 1.2,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149176,
            "检查明细项": "真空采血管(特殊采血管）",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 7.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149157,
            "检查明细项": "葡萄糖测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149158,
            "检查明细项": "血清总胆固醇测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149159,
            "检查明细项": "血清甘油三酯测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 9.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149160,
            "检查明细项": "血清高密度脂蛋白胆固醇测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 9.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149161,
            "检查明细项": "血清低密度脂蛋白胆固醇测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 8.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149162,
            "检查明细项": "血清载脂蛋白AⅠ测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "血脂血糖7项",
            "医嘱序号": 123546392,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 8.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149163,
            "检查明细项": "血清载脂蛋白B测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "同型半胱氨酸(酶法)",
            "医嘱序号": 123546394,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 96.9,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149171,
            "检查明细项": "血同型半胱氨酸测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149155,
            "检查明细项": "血清总蛋白测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149156,
            "检查明细项": "血清白蛋白测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149164,
            "检查明细项": "血清总胆红素测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149165,
            "检查明细项": "血清直接胆红素测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149166,
            "检查明细项": "血清丙氨酸氨基转移酶测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 5.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149167,
            "检查明细项": "血清天门冬氨酸氨基转移酶测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 7.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149168,
            "检查明细项": "血清γ-谷氨酰基转移酶测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 7.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149169,
            "检查明细项": "血清碱性磷酸酶测定",
            "病人ID": 3513702
        },
        {
            "NO": "Y0483612",
            "医嘱内容": "肝功能9项",
            "医嘱序号": 123546396,
            "发生时间": "Sat, 18 May 2024 07:39:46 GMT",
            "姓名": "陈建敏",
            "实收金额": 4.0,
            "执行科室": "医学检验科",
            "执行部门ID": 144,
            "收费唯一标识": 257149170,
            "检查明细项": "乳酸脱氢酶测定",
            "病人ID": 3513702
        }
    ]

deptd = {}
for d in data:
    if d.get('执行部门ID') not in deptd:
        deptd[d.get('执行部门ID')] = []
    deptd[d.get('执行部门ID')].append(d)

for k, v in deptd.items():
    print(k)
    for vv in v:
        print(vv)



print('----------------------')


from itertools import groupby
from decimal import Decimal


data = [
    {'id': 137, 'appt_id': 19, 'pay_id': 'Y0483973', 'advice_info': '颅内多普勒血流图(TCD)', 'advice_desc': '颅内多普勒血流图(TCD)', 'dept_id': 241, 'dept_name': '彩超室', 'price': Decimal('100.0000'), 'state': 0},
    {'id': 138, 'appt_id': 19, 'pay_id': 'Y0485240', 'advice_info': '经颅多普勒超声发泡试验', 'advice_desc': '经颅多普勒超声发泡试验', 'dept_id': 241, 'dept_name': '彩超室', 'price': Decimal('50.0000'), 'state': 0}
]

# 按 pay_id 排序
data.sort(key=lambda x: x['pay_id'])

# 根据 pay_id 分组并计算每个分组的 price 总和
grouped_data = {}
for key, group in groupby(data, key=lambda x: x['pay_id']):
    group_list = list(group)
    total_price = sum(item['price'] for item in group_list)
    grouped_data[key] = {
        'items': group_list,
        'total_price': total_price
    }

# 输出结果
print(grouped_data)
# pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
#                             db=appt_config.APPT_REDIS_DB, decode_responses=True)
#
# redis_client = redis.Redis(connection_pool=pool)
#
# ret = redis_client.hget(APPT_DOCTOR_ADVICE_KEY, "dfasdfa")
#
#
# print(ret)
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# query_sql = f'select pay_id from nsyy_gyl.appt_doctor_advice where appt_id = 22'
# advicel = db.query_all(query_sql)
#
# print(advicel)
#
#
#
# # 2. Load the Excel file file_path为文件绝对路径, num为sheet序号（从0算起）
# excel_path = '/Users/gaoyanliang/Downloads/检验检查3.xls'
# num = 0
#
# wbook = xlrd.open_workbook(excel_path)
# sheet = wbook.sheet_by_index(num)
#
# # 获取表格内容
# rows = sheet.nrows  # 获取表格的行数
# data_list = []  # 获取每行数据, 组成一个list
# for n in range(1, rows):
#     values = sheet.row_values(n)
#     data = {
#     "收费唯一标识": int(values[1]),
#     "NO": values[2],
#     "病人ID": int(values[3]),
#     "医嘱序号": int(values[5]),
#     "姓名": values[4],
#     "医嘱内容": values[6],
#     "检查明细项": values[7],
#     "执行科室": values[8],
#     "执行部门ID": values[9],
#     "实收金额": values[10]
#     }
#     data_list.append(data)
#     if n > 26:
#         break
#
# print('total: ', len(data_list))
# # for d in retl:
# #     print(d)


#
# sdfadfa = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
# print(max(1,2))
#
# num = 9
#
# while num > 2:
#     print('-2')
#     num -= 2
#
# print(num)
#
# merged_list_1 = []
# list1 = [1, 2, 3]
# list2 = [4, 5, 6]
# list3 = [7, 8, 9]
#
# string_list = [f"'{item}'" for item in list2]
#
# print(','.join(string_list))
#
# # 方法1: 使用 + 操作符
# merged_list_1 = merged_list_1 + list1
# merged_list_1 = merged_list_1 + list2
# merged_list_1 = merged_list_1 + list3
# print(f"使用 + 操作符合并: {merged_list_1}")
#
#
#
# # data = [{"cv_source": 4}, {"cv_source": 4}]
# data = [{'CV_SOURCE': 4}, {'CV_SOURCE': 4}]
#
# # 使用列表推导式和字典推导式将键转换为大写
# converted_data = [{k.upper(): v for k, v in item.items()} for item in data]
#
# # 打印结果
# print(converted_data)
#
#
# data = [{"cv_source": 4, "other_field": "value1"}, {"cv_source": 4, "other_field": "value2"}]
#
# # 使用列表推导式和条件语句进行选择性转换
# converted_data = [
#     {("CV_SOURCE" if k == "cv_source" else k): v for k, v in item.items()}
#     for item in data
# ]
#
# # 打印结果
# print(converted_data)
#
#
#
# print(time.time()*1000)
#
# print( datetime.now().strftime("%Y%m%d%H%M%S%f"))
#
# data = [{'price': '0.9'}, {'price': '0.8'}, {'price': '0.7'}]
#
# price = max(data, key=lambda x: float(x['price']))['price']
#
# print(price)

#
# main_dir = '/Users/gaoyanliang/nsyy/综合预约/坐诊医生'
#
# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# json_datal = []
# for root, dirs, files in os.walk(main_dir):
#     # root 是当前目录路径
#     # dirs 是当前目录下的子目录列表
#     # files 是当前目录下的文件列表
#
#     # 我们只关心第一层子目录，因此直接跳过 root 本身
#     if root == main_dir:
#         continue
#
#     # 从当前目录路径中提取子目录名
#     subdir_name = os.path.basename(root)
#
#     for file in files:
#         # 获取文件名，不包含扩展名
#         file_name = os.path.splitext(file)[0]
#
#         server_path = '/home/cc/att/public/坐诊医生/' + subdir_name + '/' + file
#
#         # 将字符串转换为字节
#         byte_data = server_path.encode('utf-8')
#         # 对字节进行Base64编码
#         base64_encoded = base64.b64encode(byte_data)
#         # 将Base64编码的字节转换回字符串
#         encoded_string = base64_encoded.decode('utf-8')
#
#         json_datal.append({
#             'room': str(subdir_name),
#             'name': file_name,
#             'photo': encoded_string
#         })
#         print(subdir_name, file_name, server_path, encoded_string)
#
# for json_data in json_datal:
#     fileds = ','.join(json_data.keys())
#     args = str(tuple(json_data.values()))
#     insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_info ({fileds}) VALUES {args}"
#     last_rowid = db.execute(sql=insert_sql, need_commit=True)
#     if last_rowid == -1:
#         del db
#         raise Exception("入库失败! sql = " + insert_sql)





#
#
# def async_alert(type, id, msg):
#     def alert(type, id, msg):
#         key = cv_config.CV_SITES_REDIS_KEY[type] + str(id)
#         payload = {'type': 'popup', 'wiki_info': msg}
#         redis_client = redis.Redis(connection_pool=pool)
#         sites = redis_client.smembers(key)
#
#         records = []
#         if sites:
#             for ip in sites:
#                 auto_start_state = True
#                 url = f'http://{ip}:8085/opera_wiki'
#                 try:
#                     ret = requests.post(url, json=payload)
#                     if ret and 'code' in ret and '20000' in str(ret.get('code')):
#                         continue
#                 except Exception as e:
#                     print(f'向 {ip} 发送危机值弹框通知失败，准备远程启动危机值程序, ip 信息： ', '病区 ' if int(type) == 1 else '科室 ', id)
#
#                 url = f'http://{ip}:8091/push?r=D:/Softwares/WeiJiZhi/start.bat'
#                 try:
#                     ret = requests.post(url)
#                     if ret and 'code' in ret and '20000' not in str(ret.get('code')):
#                         auto_start_state = False
#                         print(f'{ip} 危机值程序远程启动失败 ret = {ret}')
#                 except Exception as e:
#                     auto_start_state = False
#                     print(f'{ip} 危机值程序远程启动失败')
#
#                 if not auto_start_state:
#                     records.append({'ip': ip, 'type': type, 'type_id': id, 'time': str(datetime.now())[:19]})
#
#     thread_b = threading.Thread(target=alert, args=(type, id, msg))
#     thread_b.start()



doctor_advice = [{'收费唯一标识': 256478851, 'NO': 'Y0456192', '病人ID': 3556547, '医嘱序号': 123200053, '姓名': '王俊一', '医嘱内容': '彩超检查(门诊)', '检查明细项': '彩色多普勒超声常规检查', '执行科室': '彩超室', '执行部门ID': 241.0, '实收金额': 80.0}, {'收费唯一标识': 256478852, 'NO': 'Y0456192', '病人ID': 3556547, '医嘱序号': 123200054, '姓名': '王俊一', '医嘱内容': '彩色多普勒超声常规检查:胃肠道(常规)', '检查明细项': '彩色多普勒超声常规检查', '执行科室': '彩超室', '执行部门ID': 241.0, '实收金额': 80.0}]





import json
import time
from itertools import groupby
from datetime import datetime

import requests
import xmltodict
from flask import request
from ping3 import ping
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from gylmodules import global_config
from gylmodules.critical_value import cv_config, cv_manage
import asyncio
import xml.etree.ElementTree as ET
import re
import redis
from openpyxl import Workbook

import random
import string

from gylmodules.medical_record_analysis.record_parse import death_record_parse, progress_note_parse
from gylmodules.medical_record_analysis.record_parse.admission_record_parse import clean_dict
from gylmodules.utils.db_utils import DbUtil


ans_list = [
    {
        "checked": 0,
        "exten_data": [
            {
                "type": 2,
                "exten_name": "病史年限",
                "exten_option": ["24小时内", "三天左右", "半个月左右", "一个月左右", "一个月以上"],
                "exten_unit": "",
                "exten_value": [],
                "exten_prefix": "",
                "exten_result": [],
                "exten_suffix": ""
            }
        ],
        "option_name": "脑血管疾病",
        "sub_options": [
        ]
    },
    {
        "checked": 0,
        "exten_data": [],
        "option_name": "无",
        "sub_options": [
        ]
    },
    {
        "checked": 0,
        "exten_data": [
        ],
        "option_name": "其他",
        "sub_options": [

        ]
    }
]

# ans_list = ["无", "其他"]

# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# json_data = {
#     'description': '是否有其他病史',
#     'sort_num': 11,
#     'type': 3,
#     'tpl_type': 2,
#     'tpl_type_detail': 5,
#     'ans_type': 7,
#     'ans_list': json.dumps(ans_list, ensure_ascii=False, default=str),
#     'medical_record_field': '其他病史',
# }
#
# fileds, args = ','.join(json_data.keys()), str(tuple(json_data.values()))
# insert_sql = f"INSERT INTO nsyy_gyl.question_list ({fileds}) VALUES {args}"
# last_rowid = db.execute(insert_sql, need_commit=True)
#
# if last_rowid == -1:
#     print('插入失败')
# del db



ans_list = [
    {
        "checked": 0,
        "exten_data": [
            {
                "type": 1,
                "step_size": 1,
                "exten_name": "服药频次(次/天)",
                "exten_unit": "",
                "exten_value": 2,
                "exten_prefix": "频次",
                "exten_result": "",
                "exten_suffix": "次/天"
            },
            {
                "type": 1,
                "step_size": 0.5,
                "exten_name": "药量(粒/次)",
                "exten_unit": "",
                "exten_value": 1,
                "exten_prefix": "药量",
                "exten_result": "",
                "exten_suffix": "粒/次"
            },
            {
                "type": 2,
                "step_size": 0.5,
                "exten_name": "药物不良反应",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "皮肤潮红",
                    "发痒",
                    "心悸",
                    "皮疹",
                    "呼吸困难",
                    "无"
                ],
                "exten_prefix": "不良反应",
                "exten_result": [

                ],
                "exten_suffix": ""
            },
            {
                "type": 3,
                "step_size": 0,
                "exten_name": "服药后头痛是否缓解？",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "缓解",
                    "未缓解"
                ],
                "exten_prefix": "服药后",
                "exten_result": [

                ],
                "exten_suffix": ""
            },
            {
                "type": 3,
                "step_size": 0,
                "exten_name": "您对该药物的满意度",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "明显好转",
                    "好转",
                    "稍好转",
                    "无变化",
                    "稍差",
                    "差",
                    "非常差"
                ],
                "exten_prefix": "服药后",
                "exten_result": [

                ],
                "exten_suffix": ""
            }
        ],
        "option_name": "酚咖片",
        "sub_options": [

        ]
    },
    {
        "checked": 0,
        "exten_data": [

        ],
        "option_name": "无",
        "sub_options": [

        ]
    },
    {
        "checked": 0,
        "exten_data": [
            {
                "type": 1,
                "step_size": 1,
                "exten_name": "服药频次(次/天)",
                "exten_unit": "",
                "exten_value": 2,
                "exten_prefix": "频次",
                "exten_result": "",
                "exten_suffix": "次/天"
            },
            {
                "type": 1,
                "step_size": 0.5,
                "exten_name": "药量(粒/次)",
                "exten_unit": "",
                "exten_value": 1,
                "exten_prefix": "药量",
                "exten_result": "",
                "exten_suffix": "粒/次"
            },
            {
                "type": 2,
                "step_size": 0.5,
                "exten_name": "药物不良反应",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "皮肤潮红",
                    "发痒",
                    "心悸",
                    "皮疹",
                    "呼吸困难",
                    "无"
                ],
                "exten_prefix": "不良反应",
                "exten_result": [

                ],
                "exten_suffix": ""
            },
            {
                "type": 3,
                "step_size": 0,
                "exten_name": "服药后头痛是否缓解？",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "缓解",
                    "未缓解"
                ],
                "exten_prefix": "服药后",
                "exten_result": [

                ],
                "exten_suffix": ""
            },
            {
                "type": 3,
                "step_size": 0,
                "exten_name": "您对该药物的满意度",
                "exten_unit": "",
                "exten_value": [

                ],
                "exten_option": [
                    "明显好转",
                    "好转",
                    "稍好转",
                    "无变化",
                    "稍差",
                    "差",
                    "非常差"
                ],
                "exten_prefix": "服药后",
                "exten_result": [

                ],
                "exten_suffix": ""
            }
        ],
        "option_name": "其他",
        "sub_options": [

        ]
    }
]

# db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#             global_config.DB_DATABASE_GYL)
#
# update_sql = f"update nsyy_gyl.question_list set ans_list = '{json.dumps(ans_list, ensure_ascii=False, default=str)}' where id = 72"
#
# db.execute(update_sql, need_commit=True)
#
# del db


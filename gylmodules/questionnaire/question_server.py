import redis
import json
import requests

from itertools import groupby
from datetime import datetime
from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.questionnaire import question_config


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", json=param)
            data = json.loads(response.text)
            if type != 'his_pers_reg':
                data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
            from tools import orcl_db_read
            data = orcl_db_read(param)
        elif type == 'his_pers_reg':
            from tools import his_pers_reg
            data = his_pers_reg(param)
        else:
            print('call_third_systems_obtain_data 不支持 ', type)
    return data


"""
根据患者就诊卡号 / 身份证号 查询患者信息
查询出来的科室是 id， 需要依赖 危急值系统缓存的科室信息查询 科室名字
"""


def query_patient_info(card_no):
    patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select * from 病人信息 where 就诊卡号 like '%{card_no}%' or 身份证号 like '%{card_no}%'"
    })

    # patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
    #     "type": "orcl_db_read",
    #     "db_source": "nshis",
    #     "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
    #     "sql": f'select a.*, b.身份证号, b.当前科室ID, b.当前床号, b.联系人电话, b.出生日期, '
    #            f'b.婚姻状况, b.职业, b.家庭地址, b.工作单位, b.民族, b.就诊时间 '
    #            f'from 病人挂号记录 a left join 病人信息 b on a.病人id=b.病人id '
    #            f"where ( b.就诊卡号 like '%{card_no}%' or b.身份证号 like '%{card_no}%' ) "
    #            f" order by a.登记时间 desc "
    # })
    if not patient_infos:
        raise Exception('未找到该患者挂号信息，请仔细核对 就诊卡号/身份证号 是否正确')
    data = {
        "sick_id": patient_infos[0].get('病人ID'), "patient_name": patient_infos[0].get('姓名'),
        "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_infos[0].get('年龄'),
        "patient_phone": patient_infos[0].get('联系人电话'), "birth_day": patient_infos[0].get('出生日期'),
        "marital_status": patient_infos[0].get('婚姻状况'), "occupation": patient_infos[0].get('职业'),
        "home_address": patient_infos[0].get('家庭地址'), "work_unit": patient_infos[0].get('工作单位'),
        "nation": patient_infos[0].get('民族'), "visit_time": datetime.now(), "card_no": card_no,
        "medical_card_no": patient_infos[0].get('就诊卡号'), "id_card_no": patient_infos[0].get('身份证号')
    }
    if data['patient_age']:
        data['patient_age'] = data['patient_age'].replace('岁', '')
    return data


def create_patient_info(json_data):
    # 创建患者信息
    create_ret = call_third_systems_obtain_data('his_socket', 'his_pers_reg', {
        "type": "his_pers_reg", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "pers_name": json_data.get('pers_name'), "pers_mobile": json_data.get('pers_mobile'),
        "pers_id_no": json_data.get('pers_id_no'), "pers_id_type": 1})

    if 'PatientID' not in create_ret or not create_ret.get('PatientID'):
        raise Exception('创建患者信息失败, 请稍后重试')

    return query_patient_info(json_data.get('pers_id_no'))


"""
查询问题模版列表
"""


def query_tpl_list():
    return {'tpl_type': question_config.tpl_type, 'tpl_type_detail': question_config.tpl_type_detail}


"""
查询问题列表
"""


def query_question_list(json_data):
    tpl_type = json_data.get('tpl_type')
    tpl_type_detail = json_data.get('tpl_type_detail')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.question_list where tpl_type = {question_config.tpl_type['通用']} " \
                f"or (tpl_type = {tpl_type} and tpl_type_detail = {tpl_type_detail}) "
    question_list = db.query_all(query_sql)
    del db

    for d in question_list:
        if d['ans_list']:
            d['ans_list'] = json.loads(d['ans_list'])
    return question_list


"""
问卷调查记录
"""


def question_survey_ans(json_data):
    # 提取病历所需数据， 提取出 主诉/现病史/既往史 然后把所有数据拼起来
    ans_data = []
    data = json_data['ans_list']
    # 先按 'type' 值排序
    data.sort(key=lambda x: x['type'])
    # 使用 groupby 按 'type' 分组
    for key, group in groupby(data, key=lambda x: x['type']):
        title = '未知'
        if int(key) == 1:
            title = '主诉'
        elif int(key) == 2:
            title = '现病史'
        elif int(key) == 3:
            title = '既往史'
        elif int(key) == 4:
            title = '体格检查'
        ans_data.append({'sort_num': int(key), 'title': title, 'content': assembly_data(group)})

    json_data['medical_card_no'] = json_data['patient_info'].get('medical_card_no', "0")
    json_data['id_card_no'] = json_data['patient_info'].get('id_card_no', "0")
    json_data['patient_info'] = json.dumps(json_data['patient_info'], default=str)
    json_data['ans_list'] = json.dumps(json_data['ans_list'], default=str)
    json_data['create_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    json_data['ans_data'] = json.dumps(ans_data, default=str)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.question_survey_list ({fileds}) VALUES {args}"
    last_rowid = db.execute(insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷调查记录入库失败! ", insert_sql, str(args))
    del db


def update_question_survey_ans(json_data):
    # 提取病历所需数据， 提取出 主诉/现病史/既往史 然后把所有数据拼起来
    ans_data = []
    data = json_data['ans_list']
    # 先按 'type' 值排序
    data.sort(key=lambda x: x['type'])
    # 使用 groupby 按 'type' 分组
    for key, group in groupby(data, key=lambda x: x['type']):
        title = '未知'
        if int(key) == 1:
            title = '主诉'
        elif int(key) == 2:
            title = '现病史'
        elif int(key) == 3:
            title = '既往史'
        elif int(key) == 4:
            title = '体格检查'
        ans_data.append({'sort_num': int(key), 'title': title, 'content': assembly_data(group)})

    qs_id = json_data.get('id')
    ans_data = json.dumps(ans_data, default=str)
    ans_list = json.dumps(json_data['ans_list'], default=str)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    update_sql = f"update nsyy_gyl.question_survey_list set ans_list = '{ans_list}', ans_data = '{ans_data}' " \
                 f"where id = {qs_id} "
    db.execute(update_sql, need_commit=True)
    del db


"""
组装数据
"""


def assembly_data(data):
    content = ''
    for x in data:
        if int(x['ans_type']) == question_config.ans_type['填空']:
            ans = x['question_answer'] if x['question_answer'] else '/'
        else:
            ans = '、'.join(x['question_answer']) if x['question_answer'] else '/'
        prefix = x['ans_prefix'] if x['ans_prefix'] else ''
        suffix = x['ans_suffix'] if x['ans_suffix'] else ''
        content += f"{x['medical_record_field']}：{prefix} {ans} {suffix}；"
    return content


"""
查询问卷调查
如果使用问卷调查 id ，查询详情包括题目 & 答案
如果根据用户信息查询，仅查询问卷调查列表，不包括题目 & 答案
"""


def query_question_survey(json_data):
    question_id = json_data.get('question_id')
    patient_name = json_data.get('patient_name')
    card_no = json_data.get('card_no')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if question_id:
        # todo 查询问题详情
        query_sql = f"select * from nsyy_gyl.question_survey_list where id = {question_id}"
    else:
        condition_sql = ""
        condition_sql = f" patient_name = '{patient_name}'" if patient_name else ""
        if card_no:
            condition_sql = f"{condition_sql} or card_no = '{card_no}'" if condition_sql else f"card_no = '{card_no}'"

        if not condition_sql:
            raise Exception("查询条件不足")
        query_sql = f"select * from nsyy_gyl.question_survey_list where {condition_sql}"

    data = db.query_all(query_sql)
    for d in data:
        d['patient_info'] = json.loads(d['patient_info'])
        d['ans_list'] = json.loads(d['ans_list'])
    return data


"""
根据 病人 id 查询历史问卷
"""


def query_question_survey_by_patient_id(patient_id):
    # 根据 病人 id 查询病人信息
    patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select * from 病人信息 where 病人ID = '{patient_id}' "
    })
    medical_card_no = patient_infos[0].get('就诊卡号')
    id_card_no = patient_infos[0].get('身份证号')
    if medical_card_no == 0 and id_card_no == 0:
        raise Exception("未查询到病人信息, 病人 ID = ", patient_id)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.question_survey_list where medical_card_no = '{medical_card_no}' " \
                f"or id_card_no = '{id_card_no}' order by create_time desc limit 1"
    survives = db.query_one(query_sql)
    survives['patient_info'] = json.loads(survives['patient_info']) if survives['patient_info'] else {}
    survives['ans_list'] = json.loads(survives['ans_list']) if survives['ans_list'] else {}
    return survives


def view_medical_records(qid):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.question_survey_list where id = {qid}"
    record = db.query_one(query_sql)
    del db

    if not record:
        raise Exception("未查找到病历")

    ans_data = json.loads(record['ans_data']) if record['ans_data'] else []
    patient_info = json.loads(record['patient_info']) if record['patient_info'] else []
    return {"patient_info": patient_info, "ans_data": ans_data}

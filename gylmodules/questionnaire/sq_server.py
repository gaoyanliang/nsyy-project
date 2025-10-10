import json
import logging
import re
import threading
import time
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor

import requests

from itertools import groupby
from datetime import datetime, timedelta
from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils import DbUtil

logger = logging.getLogger(__name__)


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    """
    调用第三方系统查询数据
    :param url:
    :param type:
    :param param:
    :return:
    """
    data = []
    try:
        req_url = f"http://127.0.0.1:6080/{url}"
        if global_config.run_in_local:
            req_url = f"http://192.168.124.53:6080/{url}"
        response = requests.post(req_url, timeout=20, json=param)
        data = json.loads(response.text)
        if type != 'his_pers_reg':
            data = data.get('data')
    except Exception as e:
        logger.error(f'向 HIS 注册患者信息异常：type = {type}, param = {param}, {e}')
    return data


def query_patient_info(card_no):
    """
    根据患者就诊卡号 / 身份证号 查询患者信息
    :param card_no:
    :return:
    """
    data = {}
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.sq_surveys_record where id_card_no = '{card_no}' " \
                f"or card_no = '{card_no}' order by visit_time desc limit 1"
    history_record = db.query_one(query_sql)
    if history_record:
        history_record.pop('id')
        history_record['visit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        age = calculate_age_from_id(history_record.get('id_card_no'), history_record.get('birth_day'))
        if age != '未知':
            history_record['patient_age'] = age
        if history_record.get('id_card_no') and len(history_record.get('id_card_no')) == 18:
            id_card_no = history_record.get('id_card_no')
            history_record['birth_day'] = f"{id_card_no[6:10]}-{id_card_no[10:12]}-{id_card_no[12:14]}"
        if history_record.get('nation', 0) == 0:
            history_record['nation'] = '汉族'
        data = history_record
    else:
        sql = f"""
           SELECT brxx.SHENFENZH 身份证号, brxx.JIUZHENKH 就诊卡号, brxx.CHUSHENGRQ 出生日期, brxx.LIANXIRDH 联系人电话, brxx.LIANXIREN 联系人,
    brxx.XIANZHUZHIDH 现住址电话, brxx.BINGRENID 病人ID, brxx.XINGMING 姓名, brxx.XINGBIEMC 性别, brxx.XINGBIEDM 性别代码, 
    brxx.HUNYINMC 婚姻, brxx.ZHIYEMC 职业, brxx.HUKOUDZ 户口地址, brxx.XIANZHUZHI 现住址, brxx.GONGZUODW 工作单位, 
    brxx.MINZUMC 民族 FROM df_bingrenzsy.gy_bingrenxx brxx WHERE brxx.JIUZHENKH = '{card_no}'  
    OR brxx.SHENFENZH = '{card_no}' ORDER BY brxx.JIANDANGRQ DESC
        """
        patient_infos = global_tools.call_new_his_pg(sql)
        if not patient_infos:
            raise Exception('未找到该患者信息，请仔细核对 就诊卡号/身份证号 是否正确')
        patient_age = calculate_age_from_id(patient_infos[0].get('身份证号'), patient_infos[0].get('出生日期'))
        if patient_infos[0].get('现住址电话') and len(patient_infos[0].get('现住址电话')) > 1:
            patient_phone = patient_infos[0].get('现住址电话')
        else:
            patient_phone = patient_infos[0].get('联系人电话')
        data = {
            "sick_id": patient_infos[0].get('病人id'), "patient_name": patient_infos[0].get('姓名'),
            "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_age,
            "patient_phone": patient_phone, "birth_day": patient_infos[0].get('出生日期'),
            "marital_status": patient_infos[0].get('婚姻'), "occupation": patient_infos[0].get('职业'),
            "home_address": patient_infos[0].get('现住址'), "work_unit": patient_infos[0].get('工作单位'),
            "nation": patient_infos[0].get('民族'), "visit_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "card_no": card_no, "allergy_history": "", "contact_name": patient_infos[0].get('联系人'),
            "contact_phone": patient_infos[0].get('联系人电话'),
            "medical_card_no": patient_infos[0].get('就诊卡号'), "id_card_no": patient_infos[0].get('身份证号')
        }
        if data.get('id_card_no') and len(data.get('id_card_no')) == 18:
            id_card_no = data.get('id_card_no')
            data['birth_day'] = f"{id_card_no[6:10]}-{id_card_no[10:12]}-{id_card_no[12:14]}"
        if data.get('nation', 0) == 0:
            data['nation'] = '汉族'

    # 查询挂号医生信息
    patient_name = data.get('patient_name')
    sql = f"""
        SELECT gh.bingrenxm 姓名, gh.guahaoysxm 执行人, gh.guahaoks 执行部门ID, gh.guahaoksmc 部门名称, 
        gh.guahaorq 发生时间, gh.guahaoys 执行人ID FROM df_jj_menzhen.mz_guahao gh WHERE gh.zuofeibz = 0 
        AND TRUNC(gh.guahaorq) = TRUNC(SYSDATE) AND gh.bingrenxm = '{patient_name}' ORDER BY gh.guahaorq DESC
    """
    register_infos = global_tools.call_new_his(sql)
    if register_infos:
        data['doctor_id'] = register_infos[0].get('执行人ID', "")
        data['doctor_name'] = register_infos[0].get('执行人', "")
        data['dept_id'] = register_infos[0].get('执行部门ID', "")
        data['dept_name'] = register_infos[0].get('部门名称', "")

    return data


def calculate_age_from_id(card_no, birth_date):
    """
    根据出生日期/身份证号 计算年龄 支持小于2岁展示 'X岁Y月'
    :param card_no:
    :param birth_date:
    :return:
    """
    try:
        if type(birth_date) != str:
            birth_date_str = birth_date.strftime("%Y%m%d")
        else:
            if card_no:
                # 从身份证中提取出生日期（第7到14位）
                birth_date_str = card_no[6:14]
            else:
                # 解析日期字符串为 datetime 对象
                parsed_date = datetime.strptime(birth_date, "%a, %d %b %Y %H:%M:%S %Z")
                birth_date_str = parsed_date.strftime("%Y%m%d")
        birth_date = datetime.strptime(birth_date_str, "%Y%m%d")
        today = datetime.today()

        # 计算年龄的年份和月份差
        years, months, days = today.year - birth_date.year, today.month - birth_date.month, today.day - birth_date.day
        # 调整月份和年份
        if days < 0:  # 当前日期比出生月的日子小，月份需要减1
            months -= 1
        if months < 0:  # 如果月份小于0，年份需要减1，月份加12
            years -= 1
            months += 12

        # 判断是否小于2岁
        if years < 2:
            if years == 0:
                return f"{months}月"
            else:
                return f"{years}岁{months}月"
        else:
            return f"{years}岁"
    except (ValueError, IndexError):
        return "未知"


def create_patient_info(json_data):
    """
    创建患者信息
    :param json_data:
    :return:
    """
    create_ret = call_third_systems_obtain_data('his_socket', 'his_pers_reg', {
        "type": "his_pers_reg", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "pers_name": json_data.get('pers_name'),
        "pers_mobile": json_data.get('pers_mobile'), "pers_id_no": json_data.get('pers_id_no'), "pers_id_type": 1})

    if 'PatientID' not in create_ret or not create_ret.get('PatientID'):
        raise Exception('创建患者信息失败, 请稍后重试', create_ret if create_ret else "")

    return query_patient_info(json_data.get('pers_id_no'))


def query_tpl_list():
    """
    查询问卷列表
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    surveys = db.query_all(f"select * from nsyy_gyl.sq_surveys")
    sorted_data = sorted(surveys, key=lambda x: (x['type'], x['id']))
    del db
    return sorted_data


def query_question_list(su_id, card_no):
    """
    根据问卷 id 查询问题列表
    :param su_id:
    :param card_no:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select a.id, a.su_id, a.qu_id, a.order_by_id,a.visibility, b.qu_title, b.qu_note, b.qu_tag, " \
                f"b.qu_tag_name, b.qu_type, b.qu_answer, b.pre_qu_id,b.pre_qu_answer, b.medical_record_field, " \
                f"b.keywords, b.create_date, coalesce(a.qu_default_value, b.qu_default_value) qu_default_value, " \
                f"coalesce(a.qu_units, b.qu_units) qu_units, coalesce(a.step_size, b.step_size) step_size, " \
                f"coalesce(a.ans_prefix, b.ans_prefix) ans_prefix, coalesce(a.ans_suffix, b.ans_suffix) ans_suffix, b.other_hint " \
                f"from nsyy_gyl.sq_surveys_question_association a join nsyy_gyl.sq_questions b on a.qu_id = b.id " \
                f"where a.su_id = {int(su_id)} and a.visibility = 1 order by a.order_by_id"
    question_list = db.query_all(query_sql)

    # 如果是数组字符串，先解析成数组
    qu_id_list = []
    for question in question_list:
        qu_id_list.append(str(question.get('id')))
        if question.get('qu_answer'):
            question["qu_answer"] = json.loads(question["qu_answer"])
        if question.get('qu_units'):
            question["qu_units"] = json.loads(question["qu_units"]) \
                if '[' in question['qu_units'] else question['qu_units']

    # 获取患者历史问卷的答案
    query_sql = f"select id from nsyy_gyl.sq_surveys_record" \
                f" where card_no = '{card_no}' or id_card_no = '{card_no}' or medical_card_no = '{card_no}'"
    hist_records = db.query_all(query_sql)

    hist_answer_list = []
    if hist_records:
        hist_re_id_list = [str(hist_record.get('id')) for hist_record in hist_records]
        query_sql = f"select * from (select *, ROW_NUMBER() over(PARTITION by qu_id order by re_id desc) rn " \
                    f"from nsyy_gyl.sq_surveys_answer where re_id in ({', '.join(hist_re_id_list)}) " \
                    f"and qu_id in ({', '.join(qu_id_list)})) v where rn = 1"
        hist_answer_list = db.query_all(query_sql)
        for answer in hist_answer_list:
            answer["answer"] = json.loads(answer["answer"])
            # answer["other_answer"] = json.loads(answer["other_answer"]) if answer.get('other_answer') else ""
    del db
    return question_list, hist_answer_list


def submit_survey_record(json_data):
    """
    提交问卷记录
    :param json_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 1. 根据患者信息生成问卷记录
    surveys_record = json_data.get('surveys_record')
    if 'id' in surveys_record:
        # 如果存在 id 说明是基于历史问卷提交成为新问卷
        surveys_record.pop('id')
        surveys_record['visit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not surveys_record.get('doctor_id') or not surveys_record.get('doctor_name'):
        surveys_record.pop('doctor_id') if 'doctor_id' in surveys_record else None
        surveys_record.pop('doctor_name') if 'doctor_name' in surveys_record else None
        surveys_record.pop('dept_id') if 'dept_id' in surveys_record else None
        surveys_record.pop('dept_name') if 'dept_name' in surveys_record else None
    surveys_record['treatment_advice'] = ''
    surveys_record['initial_impression'] = ''
    surveys_record['status'] = 1

    surveys_record = {k: v for k, v in surveys_record.items() if v is not None}
    fileds = ','.join(surveys_record.keys())
    args = str(tuple(surveys_record.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.sq_surveys_record ({fileds}) VALUES {args}"
    re_id = db.execute(insert_sql, need_commit=True)
    if re_id == -1:
        del db
        raise Exception("问卷记录入库失败! ", surveys_record, insert_sql)

    # 2. 插入答案
    question_list = json_data['question_list']

    answer_list = [
        (re_id, item['qu_id'], json.dumps(item['answer'], default=str, ensure_ascii=False), item.get('qu_unit', ''),
         item.get('other_answer') if item.get('other_answer') else "", item.get('need_confirm', 0))
        for item in question_list if item.get('answer')
    ]

    # 生成插入的 SQL
    placeholders = ', '.join(['%s'] * len(answer_list[0]))
    insert_sql = f"INSERT INTO nsyy_gyl.sq_surveys_answer (re_id, qu_id, answer, qu_unit, other_answer, need_confirm) VALUES ({placeholders})"
    last_rowid = db.execute_many(insert_sql, answer_list, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷记录答案列表入库失败! ", insert_sql, str(args))
    del db
    return re_id


def update_survey_record(json_data):
    """
    更新历史问卷
    :param json_data:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 1. 更新患者信息生成问卷记录
    surveys_record = json_data.get('surveys_record')
    re_id = surveys_record.get('id')
    surveys_record.pop('id')
    surveys_record['treatment_advice'] = ''
    surveys_record['initial_impression'] = ''
    surveys_record['status'] = 1

    set_clause = ", ".join([f"{key} = %s" for key in surveys_record.keys()])
    update_sql = f"UPDATE nsyy_gyl.sq_surveys_record SET {set_clause} WHERE id = %s"
    args = list(surveys_record.values()) + [re_id]
    db.execute(update_sql, args, need_commit=True)

    # 2. 更新答案
    question_list = json_data['question_list']
    answer_list = [
        (re_id, item['qu_id'], json.dumps(item['answer'], default=str, ensure_ascii=False), item.get('qu_unit', ''),
         item.get('other_answer') if item.get('other_answer') else "", item.get('need_confirm', 0))
        for item in question_list if item.get('answer')
    ]

    insert_sql = """
            INSERT INTO nsyy_gyl.sq_surveys_answer (re_id, qu_id, answer, qu_unit, other_answer, need_confirm) 
            VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE re_id = VALUES(re_id), qu_id = VALUES(qu_id), 
            answer = VALUES(answer), qu_unit = VALUES(qu_unit), 
            other_answer = VALUES(other_answer), need_confirm = VALUES(need_confirm) 
    """
    last_rowid = db.execute_many(insert_sql, answer_list, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷记录答案列表入库失败! ", insert_sql)
    del db


def delete_question_survey(re_id):
    """
    删除问卷记录
    :param re_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f"update nsyy_gyl.sq_surveys_record set status = 0 where id = {int(re_id)}"
    record = db.execute(update_sql, need_commit=True)
    del db


def query_hist_questionnaires_list(json_data):
    """
    条件查询历史问卷记录列表，支持查询条件有：患者姓名 身份证号 就诊卡号 操作人
    :param json_data:
    :return:
    """
    patient_name = json_data.get('patient_name')
    card_no = json_data.get('card_no')
    doctor_name = json_data.get('doctor')
    operator = json_data.get('operator')
    start_time = json_data.get('start_time')
    end_time = json_data.get('end_time')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    condition_sql = ""
    condition_sql = f" patient_name like '%{patient_name}%'" if patient_name else ""
    if operator:
        condition_sql = f"{condition_sql} or operator like '%{operator}%'" if condition_sql \
            else f" operator like '%{operator}%'"
    if card_no:
        condition_sql = f"{condition_sql} or card_no = '{card_no}' or medical_card_no = '{card_no}' " \
                        f"or id_card_no = '{card_no}'" if condition_sql \
            else f"card_no = '{card_no}' or medical_card_no = '{card_no}' or id_card_no = '{card_no}' "
    if doctor_name:
        condition_sql = f"{condition_sql} or doctor_name like '%{doctor_name}%'" if condition_sql \
            else f"doctor_name like '%{doctor_name}%'"
    if start_time and end_time:
        condition_sql = f"{condition_sql} and (visit_time between '{start_time}' and '{end_time}') " \
            if condition_sql else f"visit_time between '{start_time}' and '{end_time}'"

    if not condition_sql:
        raise Exception("查询条件不足")

    query_sql = f"select * from nsyy_gyl.sq_surveys_record where status = 1 and ({condition_sql})"
    survey_record = db.query_all(query_sql)
    del db

    for record in survey_record:
        record['visit_time'] = record['visit_time'].strftime('%Y-%m-%d %H:%M:%S')
    return survey_record


def query_hist_questionnaires_details(json_data):
    """
    精确查询历史问卷记录详情
    :param json_data:
    :return:
    """
    # 问卷记录 id
    re_id = json_data.get('re_id')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.sq_surveys_record where id = {int(re_id)}"
    survey_record = db.query_one(query_sql)
    if not survey_record:
        raise Exception(f'问卷记录 id {re_id} 不存在，请检查入参.')
    survey_record['visit_time'] = survey_record['visit_time'].strftime('%Y-%m-%d %H:%M:%S')

    # 前端直接根据 su-id 查询问卷问题列表，后端仅查询返回答案列表
    query_sql = f"select * from nsyy_gyl.sq_surveys_answer where re_id = {int(re_id)} "
    answer_list = db.query_all(query_sql)
    for answer in answer_list:
        answer["answer"] = json.loads(answer["answer"])
        # answer["other_answer"] = json.loads(answer["other_answer"]) if answer.get('other_answer') else ""
    del db

    # 查询 检查/检验 结果
    visit_time = datetime.strptime(survey_record.get('visit_time'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    test_results, examination_result, zhenduan = \
        query_data(survey_record.get('sick_id'), visit_time)
    return survey_record, answer_list, test_results, examination_result


def query_question_survey_by_patient_id(patient_id):
    """
    his 系统 根据 病人 id 查询问卷记录
    :param patient_id:
    :return:
    """
    # 根据 病人 id 查询病人信息
    patient_infos = global_tools.call_new_his(
        f"SELECT brxx.SHENFENZH, brxx.JIUZHENKH FROM df_bingrenzsy.gy_bingrenxx brxx "
        f"WHERE brxx.bingrenid = '{patient_id}'")
    medical_card_no, id_card_no = patient_infos[0].get('JIUZHENKH'), patient_infos[0].get('SHENFENZH')
    query_sql = ""
    if medical_card_no == 0 and id_card_no == 0:
        raise Exception("未查询到病人信息, 病人 ID = ", patient_id)
    elif medical_card_no != 0 and id_card_no != 0:
        query_sql = f"select * from nsyy_gyl.sq_surveys_record where status = 1 and " \
                    f"(medical_card_no = '{medical_card_no}' " \
                    f"or id_card_no = '{id_card_no}') order by visit_time desc"
    elif medical_card_no != 0:
        query_sql = f"select * from nsyy_gyl.sq_surveys_record where status = 1 and" \
                    f" medical_card_no = '{medical_card_no}' order by visit_time desc"
    elif id_card_no != 0:
        query_sql = f"select * from nsyy_gyl.sq_surveys_record where status = 1 and " \
                    f" id_card_no = '{id_card_no}' order by visit_time desc"
    if not query_sql:
        raise Exception("未查询到病人问卷记录, 病人 ID = ", patient_id)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    hist_records = db.query_all(query_sql)
    del db

    for record in hist_records:
        record['visit_time'] = record['visit_time'].strftime('%Y-%m-%d %H:%M:%S')
    return hist_records


def query_test_result(card_no, visit_date):
    """
    查询检查项目结果
    :param card_no:
    :param visit_date:
    :return:
    """
    sql = f"""
        SELECT jc.jiluid "jiluid", yj.yizhubh "doc_advice_id", jc.yizhuid "unique_key", yj.yizhumc "item_name", 
        jc.zhenduan "item_result", jc.jianchasuojian "img_result", jc.yinxiangurl "img_url", 
        jc.yingxiangbgurl "report_url" FROM df_shenqingdan.yj_jianchasqd yj 
        LEFT JOIN df_cdr.yj_jianchabg jc on yj.jianchasqdid =jc.shenqingdanid AND  jc.zuofeibz = 0 
        and jc.bingrenid = '{card_no}' WHERE yj.bingrenid = '{card_no}' 
        AND yj.kaidanrq  >= to_date('{visit_date}','yyyy-mm-dd')  and yj.zuofeibz=0
    """
    test_results = global_tools.call_new_his(sql=sql, sys='newzt', clobl=['img_result'])
    return test_results


def query_examination_result(patient_id, visit_date):
    """
    查询检验项目结果
    :param patient_id:
    :param visit_date:
    :return:
    """
    sql = f"""
     select t.jiluid AS "jiluid", t.yzid AS "doc_advice_id", t.jianchamd AS "item_name", jymx.zhongwenmc AS "item_sub_name",
        jymx.jianyanjg AS "item_sub_result", jymx.cankaofw AS "item_sub_refer", jymx.dangwei AS "item_sub_unit",
        jymx.yichangbz, jymx.jianyanxmid AS "item_sub_id",
        CASE
            WHEN jymx.yichangbz = 'L' THEN '低'
            WHEN jymx.yichangbz = 'H' THEN '高'
            WHEN jymx.yichangbz = 'E' THEN '阳性'
            WHEN jymx.yichangbz = 'D' THEN '阴性'  
            ELSE '正常' END AS "item_sub_flag" 
 from (select  LISTAGG(sqd.yizhubh, '+') WITHIN GROUP (ORDER BY sqd.yizhubh) as yzid,jy2.jianchamd,jy2.jiluid
       from  df_shenqingdan.yj_jianyansqd sqd left  join df_cdr.yj_jianyanbg jy2 on jy2.bingrenid=sqd.bingrenid and  
       instr(jy2.shenqingdid,sqd.jianyansqdid)>0  and jy2.jianyanzt=1 where sqd.bingrenid='{patient_id}'   
       and sqd.zuofeibz = 0  and sqd.kaidanrq >= to_date('{visit_date}','yyyy-mm-dd')      
group by jy2.jiluid,jy2.jianchamd) t left join df_cdr.yj_jianyanbgmx jymx ON t.jiluid = jymx.jiluid   
    """
    examination_results = global_tools.call_new_his(sql)
    return examination_results


def query_zhen_duan(sick_id, visit_date):
    if not sick_id:
        return ""
    sql = f"""
        SELECT brxx.zhenduanmc 名称 FROM df_lc_menzhen.zj_zhenduan brxx WHERE brxx.bingrenid = '{sick_id}' and 
        brxx.zuofeibz = 0 and TRUNC(brxx.chuangjiansj) >= to_date('{visit_date}', 'yyyy-mm-dd') 
        and TRUNC(brxx.chuangjiansj) < to_date('{visit_date}', 'yyyy-mm-dd') + 1 order by brxx.chuangjiansj desc
    """
    zhenduans = global_tools.call_new_his(sql)
    if not zhenduans:
        return ""

    return ", ".join([i.get('名称') for i in zhenduans])


def query_report(json_data):
    """
    统计数据 暂时仅统计了数量
    :param json_data:
    :return:
    """
    start_time, end_time, query_type = json_data.get('start_time'), json_data.get('end_time'), json_data.get(
        'query_type')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    time_sql = ""
    if start_time and end_time:
        time_sql = f" where visit_time BETWEEN '{start_time}' AND '{end_time}' and status != 0"

    if query_type == 'question':
        # 统计问卷报表
        query_sql = f"select count(*) count, su_id from nsyy_gyl.sq_surveys_record {time_sql} group by su_id"
    elif query_type == 'medical_guide':
        # 统计导医报表
        query_sql = f"select count(*) count, operator from nsyy_gyl.sq_surveys_record {time_sql} group by operator"
    elif query_type == 'patient':
        query_sql = f"select su_id, patient_name, patient_age, patient_sex, visit_time, doctor_name, dept_name, operator" \
                    f" from nsyy_gyl.sq_surveys_record {time_sql}"
    else:
        raise Exception('query_type 参数错误')
    operator_report = db.query_all(query_sql)
    del db
    return operator_report


def query_outpatient_medical_record(re_id):
    """
    查询门诊病历
    :param re_id:
    :return:
    """
    start_time = time.time()
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 1. 查询问卷记录 & 患者信息
    query_sql = f"select * from nsyy_gyl.sq_surveys_record WHERE id = {int(re_id)}"
    survey_record = db.query_one(query_sql)
    if not survey_record:
        raise Exception('问卷记录不存在')
    survey_record['visit_time'] = survey_record['visit_time'].strftime('%Y-%m-%d %H:%M:%S')

    # 查询问卷问题 & 答案， 然后组装数据
    query_sql = f"select a.id, a.su_id, a.qu_id, a.order_by_id,a.visibility, b.qu_title, b.qu_note, b.qu_tag, " \
                f"b.qu_tag_name, b.qu_type, b.qu_answer, b.pre_qu_id,b.pre_qu_answer, b.medical_record_field, " \
                f"b.keywords, b.create_date, coalesce(a.qu_default_value, b.qu_default_value) qu_default_value, " \
                f"coalesce(a.qu_units, b.qu_units) qu_units, coalesce(a.step_size, b.step_size) step_size, " \
                f"coalesce(a.ans_prefix, b.ans_prefix) ans_prefix, coalesce(a.ans_suffix, b.ans_suffix) ans_suffix, " \
                f"c.re_id, c.answer, c.qu_unit, c.other_answer, c.need_confirm from nsyy_gyl.sq_surveys_question_association a " \
                f"join nsyy_gyl.sq_questions b on a.qu_id = b.id left join nsyy_gyl.sq_surveys_answer c " \
                f"on c.qu_id = b.id where a.su_id = {int(survey_record.get('su_id'))} " \
                f"and a.visibility = 1 and c.re_id = {int(re_id)} order by a.order_by_id"
    answer_list = db.query_all(query_sql)

    query_sql = f"select * from nsyy_gyl.sq_surveys_detail where re_id = {int(re_id)} "
    survey_detail = db.query_one(query_sql)

    for item in answer_list:
        item['answer'] = json.loads(item.get('answer'))
        item['qu_answer'] = json.loads(item.get('qu_answer')) \
            if item.get('qu_answer') and item.get('qu_answer').__contains__('[') else item.get('qu_answer')
        item['qu_units'] = json.loads(item.get('qu_units')) \
            if item.get('qu_units') and item.get('qu_units').__contains__('[') else item.get('qu_units')
    del db

    # 查询 检查/检验 结果，拼装辅助检查, 辅助检查结果
    visit_time = datetime.strptime(survey_record.get('visit_time'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    test_results, examination_result, zhenduan = \
        query_data(survey_record.get('sick_id'), visit_time)
    # print(datetime.now(), '检验结果耗时：', time.time() - start_time)

    if not survey_detail:
        survey_detail = {}
    survey_detail['test_results'] = test_results
    survey_detail['examination_result'] = examination_result

    # todo 初步印象 治疗意见 应该是医生自己写的？？
    # 查询诊断（初步印象）
    survey_detail['his_zhenduan'] = zhenduan
    return survey_record, survey_detail, answer_list


def assembly_data(question_list, answer_dict):
    """
    组装患者门诊病历数据
    :param question_list:
    :param answer_dict:
    :return:
    """
    # 将问卷问题列表 构造成 树形结构
    tree = build_tree(question_list)

    # 遍历树形结构 拼接问题答案
    answer_data = {}
    for node in tree:
        ans_ret = collect_answer(node, answer_dict)
        if node.get('qu_tag') not in answer_data:
            answer_data[node.get('qu_tag')] = ""
        answer_data[node.get('qu_tag')] = answer_data[node.get('qu_tag')] + ans_ret + ", "

    for key, value in answer_data.items():
        if value.endswith(","):
            answer_data[key] = value[:-1]

    return answer_data


def build_tree(records):
    """
    将问题列表构造成树状结构
    :param records:
    :return:
    """
    # 创建一个字典来存储节点及其子节点
    nodes = {record['qu_id']: {**record, 'children': []} for record in records}

    # 遍历记录来填充每个节点的子节点列表
    for record in records:
        if record['pre_qu_id'] is not None:
            nodes[record['pre_qu_id']]['children'].append(nodes[record['qu_id']])

    # 提取根节点（pre_qu_id为None的节点）
    root_nodes = [nodes[record['qu_id']] for record in records if record['pre_qu_id'] is None]

    return root_nodes


def collect_answer(node, ans_dict):
    """
    递归遍历父节点问题，拼接问题答案
    :param node:
    :param ans_dict:
    :return:
    """
    answer = ans_dict.get(node['qu_id'], {}).get('answer', "/")
    if type(answer) == list:
        # 血压特殊处理
        answer = '/'.join(answer) if int(node['qu_id']) == 195 else ','.join(answer)
    answer = answer + ans_dict.get(node['qu_id'], {}).get('qu_unit', "")

    # 拼接问题在病历中展示字段
    if node.get('medical_record_field', "") and node.get('qu_id') not in (6, 7, 8, 9, 10):
        # 持续时间病历中不拼病历字段
        ans_ret = node.get('medical_record_field', "") + ": "
    else:
        ans_ret = ""
    if node.get('ans_prefix'):
        ans_ret = ans_ret + node.get('ans_prefix', "")

    # 如果当前问题存在子问题，递归拼接子问题
    if 'children' in node and node['children']:
        option = []
        if node.get('qu_type') in (2, 3):
            option = ans_dict.get(node['qu_id'], {}).get('answer', "")

        # 同一个选项 可能绑定多个子问题。 同一个选项的子问题拼接在一起
        checked_qu_list = []
        for child in node['children']:
            if child.get('pre_qu_answer') in option:
                checked_qu_list.append(child)

        if checked_qu_list:
            checked_qu_list.sort(key=itemgetter('pre_qu_answer'))
            for key, group in groupby(checked_qu_list, key=lambda x: x['pre_qu_answer']):
                ans_ret = ans_ret + key
                for item in group:
                    ans_ret = ans_ret + collect_answer(item, ans_dict) + ","
                if ans_ret.endswith(","):
                    ans_ret = ans_ret[:-1]
                ans_ret = ans_ret + "、"
        else:
            ans_ret = ans_ret + answer if not answer.__contains__("其他") else ans_ret

        if ans_ret.endswith("、"):
            ans_ret = ans_ret[:-1]
    else:
        # 如果不存在子问题，直接拼接当前问题答案
        ans_ret = ans_ret + answer if not answer.__contains__("其他") else ans_ret

    ans_ret = ans_ret + ans_dict.get(node['qu_id'], {}).get('other_answer', "")

    # 拼接问题后缀
    if node.get('ans_suffix'):
        ans_ret = ans_ret + node.get('ans_suffix', "")

    return ans_ret


def submit_medical_record(json_data):
    """
    提交（新增/更新）门诊病历
    :param json_data:
    :return:
    """
    re_id = json_data.get('re_id')
    sick_id = json_data.get('sick_id')
    visit_date = json_data.get('visit_date')
    ques_title = json_data.get('ques_title', "")
    visit_time = json_data.get('visit_time', "")
    zhusu = json_data.get('zhusu', '')
    zhusu_remark = json_data.get('zhusu_remark', '')
    xianbingshi = json_data.get('xianbingshi', '')
    xianbingshi_remark = json_data.get('xianbingshi_remark', '')
    jiwangshi = json_data.get('jiwangshi', '')
    jiwangshi_remark = json_data.get('jiwangshi_remark', '')
    tigejiancha = json_data.get('tigejiancha', '')
    tigejiancha_remark = json_data.get('tigejiancha_remark', '')
    zhuankejiancha = json_data.get('zhuankejiancha', '')
    zhuankejiancha_remark = json_data.get('zhuankejiancha_remark', '')
    test_results = json_data.get('fuzhujiancha', '') if json_data.get('fuzhujiancha') else ""
    fuzhujiancha_remark = json_data.get('fuzhujiancha_remark', '')
    examination_result = json_data.get('fuzhujiancha_ret', '') if json_data.get('fuzhujiancha_ret') else ""
    fuzhujiancha_ret_remark = json_data.get('fuzhujiancha_ret_remark', '')
    chubuzhenduan = json_data.get('chubuzhenduan', '')
    yijian = json_data.get('yijian', '')

    fuzhujiancha = test_results
    if test_results and type(test_results) == list:
        fuzhujiancha = ""
        for d in test_results:
            fuzhujiancha += f"{d['item_name']}：{d['item_result']} \n"
    fuzhujiancha_ret = examination_result
    if examination_result and type(examination_result) == list:
        fuzhujiancha_ret = ""
        for d in examination_result:
            fuzhujiancha_ret += f"{d['item_sub_name']}：{d['item_sub_result']} {d['item_sub_unit']} {d['item_sub_flag']} \n"

    args = (re_id, sick_id, ques_title, visit_date, zhusu, zhusu_remark, xianbingshi, xianbingshi_remark, jiwangshi,
            jiwangshi_remark, tigejiancha, tigejiancha_remark, zhuankejiancha, zhuankejiancha_remark, fuzhujiancha,
            fuzhujiancha_remark, fuzhujiancha_ret, fuzhujiancha_ret_remark, chubuzhenduan, yijian, visit_time)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = """
            INSERT INTO nsyy_gyl.sq_surveys_detail (re_id, sick_id, ques_title, visit_date, zhusu, zhusu_remark,
            xianbingshi, xianbingshi_remark, jiwangshi, jiwangshi_remark, tigejiancha, tigejiancha_remark,
            zhuankejiancha, zhuankejiancha_remark, fuzhujiancha, fuzhujiancha_remark, fuzhujiancha_ret, 
            fuzhujiancha_ret_remark, chubuzhenduan, yijian, visit_time) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            ON DUPLICATE KEY UPDATE re_id = VALUES(re_id), sick_id = VALUES(sick_id), ques_title = VALUES(ques_title), 
            visit_date = VALUES(visit_date), zhusu = VALUES(zhusu), zhusu_remark = VALUES(zhusu_remark), 
            xianbingshi = VALUES(xianbingshi), xianbingshi_remark = VALUES(xianbingshi_remark), 
            jiwangshi = VALUES(jiwangshi), jiwangshi_remark = VALUES(jiwangshi_remark), 
            tigejiancha = VALUES(tigejiancha), tigejiancha_remark = VALUES(tigejiancha_remark), 
            zhuankejiancha = VALUES(zhuankejiancha), zhuankejiancha_remark = VALUES(zhuankejiancha_remark), 
            fuzhujiancha = VALUES(fuzhujiancha), fuzhujiancha_remark = VALUES(fuzhujiancha_remark), 
            fuzhujiancha_ret = VALUES(fuzhujiancha_ret), fuzhujiancha_ret_remark = VALUES(fuzhujiancha_ret_remark), 
            chubuzhenduan = VALUES(chubuzhenduan), yijian = VALUES(yijian), visit_time = VALUES(visit_time) 
    """
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷记录详情入库失败! ", insert_sql)
    del db
    # 第一次调用 ai
    global_tools.start_thread(call_aichat, (last_rowid, zhusu, xianbingshi, jiwangshi, tigejiancha))


def patient_quest_details(json_data):
    """
    查询患者门诊问卷详情（根据病人 ID + 就诊日期（yyyy-mm-dd）查询）
    这个接口就是在挂号初次接诊时会把问卷接口里面的主诉 病史 辅助检查  体温  体重 身高 血压 脉搏信息回传（his主动调用）到门诊病历里面
    :param json_data:
    :return:
    """
    start_time = time.time()
    patient_id = json_data.get('patient_id')
    ques_date = json_data.get('ques_date')

    query_sql = f"select b.title, a.* from nsyy_gyl.sq_surveys_record a join nsyy_gyl.sq_surveys b on a.su_id = b.id " \
                f"WHERE sick_id = '{patient_id}' and DATE(visit_time) = '{ques_date}'"
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    records = db.query_all(query_sql)

    if not records:
        del db
        return {"patient_id": patient_id, "ques_date": ques_date, "ReturnCode": 1,
                "ReturnMessage": "未查询到患者当天的问卷记录", "ques_dtl": []}

    query_sql = f"select * from nsyy_gyl.sq_surveys_detail WHERE sick_id = '{patient_id}' " \
                f"and visit_date = '{ques_date}'"
    surveys_details = db.query_all(query_sql)
    del db

    ques_dtl = []
    if surveys_details:
        for d in surveys_details:
            health_data = extract_health_data(d.get('tigejiancha', ''))
            ques = {"ques_time": d.get('visit_time').strftime('%Y-%m-%d %H:%M:%S'),
                    'ques_title': d.get('ques_title', '未知') + '问卷',
                    'ZhuSu': d.get("zhusu", "") + d.get("zhusu_remark", ""),
                    'XianBingShi': d.get("xianbingshi", "") + d.get("xianbingshi_remark", ""),
                    'JiWangShi': d.get("jiwangshi", "") + d.get("jiwangshi_remark", ""),
                    'FuZhuJianCha': d.get('fuzhujiancha', ""), 'FuZhuJianChaJieGuo': d.get('fuzhujiancha_ret', ""),
                    'ZhuanKeJianCha': d.get('ai_result1', ""), 'ZhenDuan': d.get('chubuzhenduan', ''),
                    'TiGe_JianCha': [health_data]}

            if not ques.get('FuZhuJianCha') or not ques.get('FuZhuJianChaJieGuo') or not ques.get('ZhenDuan'):
                test_results, examination_result, zhenduan = \
                    query_data(d.get('sick_id'), d.get('visit_date'))
                test_data = ""
                if test_results:
                    for t in test_results:
                        if not t.get('item_name'):
                            return
                        test_data += f"{t['item_name']}：{t['item_result']} \n"
                exam_data = ""
                if examination_result:
                    for e in examination_result:
                        if not e.get('item_name'):
                            return
                        exam_data += f"{e['item_sub_name']}：{e['item_sub_result']} " \
                                     f"{e['item_sub_unit']} {e['item_sub_flag']} \n"

                # update_sql = f"UPDATE nsyy_gyl.sq_surveys_detail SET fuzhujiancha = '{test_data}',  " \
                #              f"fuzhujiancha_ret = '{exam_data}', chubuzhenduan = '{zhenduan}' WHERE id = {d.get('id')}"
                # db.execute(update_sql, need_commit=True)
                ques['FuZhuJianCha'] = test_data
                ques['FuZhuJianChaJieGuo'] = exam_data
                ques['ZhenDuan'] = zhenduan

            ques_dtl.append(ques)
    else:
        for record in records:
            medical_data, answer_dict = query_and_assembly_data(record.get('id'))
            ques = {"ques_time": record.get('visit_time').strftime('%Y-%m-%d %H:%M:%S'),
                    'ques_title': record.get('title', '未知') + '问卷', 'ZhuSu': medical_data.get(1, ""),
                    'XianBingShi': medical_data.get(2, ""), 'JiWangShi': medical_data.get(3, ""),
                    'FuZhuJianCha': medical_data.get(5, ""), 'FuZhuJianChaJieGuo': medical_data.get(6, ""),
                    'ZhuanKeJianCha': '', 'ZhenDuan': medical_data.get('zhenduan', ''), 'TiGe_JianCha': [{
                    'TiWen': answer_dict.get(192).get('answer') if answer_dict.get(192) else 0,
                    'XinLv': answer_dict.get(193).get('answer') if answer_dict.get(193) else 0,
                    'HuXi': answer_dict.get(194).get('answer') if answer_dict.get(194) else 0,
                    'GaoYa': answer_dict.get(195).get('answer')[0] if answer_dict.get(195) else 0,
                    'DiYa': answer_dict.get(195).get('answer')[1] if answer_dict.get(195) else 0,
                    'ShenGao': answer_dict.get(196).get('answer') if answer_dict.get(196) else 0,
                    'TiZhong': answer_dict.get(197).get('answer') if answer_dict.get(197) else 0,
                }]}
            ques_dtl.append(ques)

    return {
        "patient_id": patient_id,
        "ques_date": ques_date,
        "ReturnCode": 1,
        "ReturnMessage": "",
        "ques_dtl": ques_dtl
    }


def query_and_assembly_data(re_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 1. 查询问卷记录 & 患者信息
    query_sql = f"select * from nsyy_gyl.sq_surveys_record WHERE id = {int(re_id)}"
    survey_record = db.query_one(query_sql)
    if not survey_record:
        raise Exception('问卷记录不存在')
    survey_record['visit_time'] = survey_record['visit_time'].strftime('%Y-%m-%d %H:%M:%S')

    # 查询问卷问题 & 答案， 然后组装数据
    query_sql = f"select a.id, a.su_id, a.qu_id, a.order_by_id,a.visibility, b.qu_title, b.qu_note, b.qu_tag, " \
                f"b.qu_tag_name, b.qu_type, b.qu_answer, b.pre_qu_id,b.pre_qu_answer, b.medical_record_field, " \
                f"b.keywords, b.create_date, coalesce(a.qu_default_value, b.qu_default_value) qu_default_value, " \
                f"coalesce(a.qu_units, b.qu_units) qu_units, coalesce(a.step_size, b.step_size) step_size, " \
                f"coalesce(a.ans_prefix, b.ans_prefix) ans_prefix, coalesce(a.ans_suffix, b.ans_suffix) ans_suffix " \
                f"from nsyy_gyl.sq_surveys_question_association a join nsyy_gyl.sq_questions b on a.qu_id = b.id  " \
                f"where a.su_id = {int(survey_record.get('su_id'))} and a.visibility = 1 order by a.order_by_id"
    question_list = db.query_all(query_sql)

    query_sql = f"select a.*, b.* from nsyy_gyl.sq_surveys_answer a join nsyy_gyl.sq_questions b " \
                f"on a.qu_id = b.id where a.re_id = {int(re_id)} "
    answer_list = db.query_all(query_sql)
    for item in answer_list:
        item['answer'] = json.loads(item.get('answer'))
    del db
    answer_dict = {item['qu_id']: item for item in answer_list}
    medical_data = assembly_data(question_list, answer_dict)
    # 查询 检查/检验 结果，拼装辅助检查, 辅助检查结果
    visit_time = datetime.strptime(survey_record.get('visit_time'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    test_results, examination_result, zhenduan = \
        query_data(survey_record.get('sick_id'), visit_time)
    auxiliary_examination, auxiliary_examination_result = [], []
    # 检验需要根据 检验项目名称 进行分组
    examination_result.sort(key=itemgetter('item_name'))
    for key, group in groupby(examination_result, key=lambda x: x['item_name']):
        auxiliary_examination.append(key)
        ret = []
        for item in group:
            ret.append(f"{item.get('item_sub_name')} {item.get('item_sub_result')} ({item.get('item_sub_unit')})")
        ret = key + ": " + ", ".join(ret)
        auxiliary_examination_result.append(ret)

    for item in test_results:
        if item.get('item_name') and type(item['item_name']) == str:
            auxiliary_examination.append(item['item_name'])
        if item.get('item_result') and type(item['item_result']) == str:
            auxiliary_examination_result.append(item.get('item_result'))
    medical_data[5] = '、'.join(auxiliary_examination)
    medical_data[6] = '、'.join(auxiliary_examination_result)

    # 查询诊断（初步印象）
    medical_data['zhenduan'] = zhenduan
    return medical_data, answer_dict


def extract_health_data(text):
    # 定义正则表达式来匹配各项数据
    # "体温36.2°C，脉搏85次/分，呼吸20次/分，血压124/77mmHg，身高165CM，体重80公斤，神志清醒，步态正常，自动体位，精神正常。"
    patterns = {
        "TiWen": r"体温([\d.]+)°C",  # 匹配体温
        "XinLv": r"脉搏([\d]+)次/分",  # 匹配心率
        "HuXi": r"呼吸([\d]+)次/分",  # 匹配呼吸
        "XueYa": r"(\d{2,3})/(\d{2,3})mmHg",  # 匹配血压，提取高压
        'ShenGao': r"身高([\d]+)CM",
        'TiZhong': r"体重([\d]+)公斤"
    }

    # 创建一个字典来存储提取的数据， 默认值 -1
    data = {"TiWen": "-1", "XinLv": "-1", "HuXi": "-1", "GaoYa": "-1", "DiYa": "-1", "ShenGao": -1, "TiZhong": -1}
    # 使用正则表达式提取数据
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1)  # 其他项直接提取第一组匹配
            if key == "XueYa":
                data["GaoYa"] = match.group(1)  # 提取高压
                data["DiYa"] = match.group(2)  # 提取低压

    return data


def query_data(sick_id, visit_date):
    """
    使用并发查询测试结果、检查结果和诊断结果
    :param visit_date: 就诊时间
    :param sick_id: 病人 ID
    :return: 测试结果、检查结果和诊断结果
    """
    # 使用线程池并发查询
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(query_test_result, sick_id, visit_date),
            executor.submit(query_examination_result, sick_id, visit_date),
            executor.submit(query_zhen_duan, sick_id, visit_date)
        ]

        # 获取查询结果
        test_results = futures[0].result() or []
        examination_result = futures[1].result() or []
        zhenduan = futures[2].result() or ""
    return test_results, examination_result, zhenduan


def call_ai_api(param: dict):
    data = None
    url = f"http://192.168.9.35:6063/aichat/api_aichat"
    if global_config.run_in_local:
        url = f"http://192.168.124.53:6080/aichat/api_aichat"

    max_retries = 3
    delay = 1
    for attempt in range(max_retries + 1):  # +1 包括首次尝试
        try:
            # 发送 POST 请求
            response = requests.post(url, timeout=200, json=param)
            response.raise_for_status()  # 检查状态码，非 2xx 会抛出异常
            data = response.text
            data = json.loads(data)  # 成功时返回解析后的数据
            return data
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.warning(f"尝试 {attempt + 1}/{max_retries + 1} 调用 {url} 失败: {e}")
            if attempt < max_retries:  # 如果不是最后一次尝试
                time.sleep(delay)  # 等待后重试
            else:
                # 所有尝试失败，返回错误信息
                return data
    return data


def call_aichat(id, zhusu, xianbingshi, jiwangshi, tigejiancha):
    start_time = time.time()
    medical_data = ""
    medical_data = medical_data + "主诉：" + zhusu + "; "
    medical_data = medical_data + "现病史：" + xianbingshi + "; "
    medical_data = medical_data + "既往史：" + jiwangshi + "; "
    medical_data = medical_data + "体格检查：" + tigejiancha + "; "
    medical_data = medical_data + "以上为患者基本信息，请根据该患者病历信息，给出初步诊断和推荐做的检查检验项目。"

    data = None
    try:
        data = call_ai_api({"message": medical_data})
    except Exception as e:
        logger.error(f'调用 ai api 失败： {e}')

    if not data:
        return

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f"UPDATE nsyy_gyl.sq_surveys_detail set ai_result1 = '{data.get('data')}' where id = {id}"
    db.execute(update_sql, need_commit=True)
    del db
    logger.info(f'调用 ai api 耗时：{time.time() - start_time} s {id}')


def fetch_ai_result():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # visit_date = datetime.now().date() - timedelta(days=1)
    visit_date = datetime.now().date()
    query_sql = f"""
        select r.card_no, r.patient_name, r.patient_age, r.patient_sex, d.* 
        from nsyy_gyl.sq_surveys_detail d join nsyy_gyl.sq_surveys_record r 
        on d.re_id = r.id where d.ai_result2 is null and d.visit_date >= '{visit_date}' 
        and r.status = 1 order by d.visit_time
    """
    all_survey = db.query_all(query_sql)
    del db
    for survey in all_survey:
        # 第二次调用 ai
        global_tools.start_thread(fetch_patient_test_result, (survey,))


def fetch_patient_test_result(survey_record):
    test_results, examination_result, _ = query_data(survey_record.get('sick_id'),
                                                     survey_record.get('visit_date'))
    # 判断检查检验结果是否全部有结果了
    if len(test_results) == 0 and len(examination_result) == 0:
        # 没有开检查检验结果
        return

    test_data = ""
    if test_results:
        for t in test_results:
            if not t.get('jiluid'):
                return
            test_data = test_data + f"检查项目：{t.get('item_name')}, 检查结果：{t.get('item_result', '')} " \
                                    f"影像结果：{t.get('img_result', '')}; "

    examination_data = ""
    if examination_result:
        sorted_data = sorted(examination_result, key=lambda x: (str(x['item_name'])))
        for key, group in groupby(sorted_data, key=lambda x: (str(x["item_name"]))):
            # examination_data = examination_data + key
            for t in group:
                if not t.get('jiluid'):
                    return
                examination_data += f"{t['item_sub_name']}：{t['item_sub_result']} {t['item_sub_unit']} {t['item_sub_flag']}; "

    medical_data = f"患者 {survey_record.get('patient_name')}, 性别 {survey_record.get('patient_sex')}, " \
                   f"年龄 {survey_record.get('patient_age')} 岁 "
    medical_data = medical_data + "主诉：" + survey_record.get('zhusu') + "; "
    medical_data = medical_data + "现病史：" + survey_record.get('xianbingshi') + "; "
    medical_data = medical_data + "既往史：" + survey_record.get('jiwangshi') + "; "
    medical_data = medical_data + "体格检查：" + survey_record.get('tigejiancha') + "; "
    medical_data = medical_data + "检查检验结果：" + test_data + examination_data + "; "
    medical_data = medical_data + "以上为患者基本信息以及检查检验结果，请根据该患者，给出用药建议和治疗建议"

    data = None
    try:
        data = call_ai_api({"message": medical_data})
    except Exception as e:
        logger.error(f'调用 ai api 失败： {e}')

    if not data:
        return
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f"UPDATE nsyy_gyl.sq_surveys_detail set ai_result2 = '{data.get('data')}', " \
                 f"fuzhujiancha = '{test_data}', fuzhujiancha_ret = '{examination_data}' " \
                 f"where id = {survey_record.get('id')}"
    db.execute(update_sql, need_commit=True)
    del db

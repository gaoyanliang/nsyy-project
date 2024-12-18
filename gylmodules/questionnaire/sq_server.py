import json
from operator import itemgetter

import requests

from itertools import groupby
from datetime import datetime
from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    """
    调用第三方系统查询数据
    :param url:
    :param type:
    :param param:
    :return:
    """
    data = []
    if global_config.run_in_local:
        try:
            response = requests.post(f"http://192.168.3.12:6080/{url}", timeout=3, json=param)
            # response = requests.post(f"http://192.168.124.53:6080/{url}", timeout=3, json=param)
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


def query_patient_register_info(patient_id):
    register_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select t.姓名 姓名, t.执行人 执行人, t.执行部门ID 执行部门ID, bm.名称 部门名称, t.发生时间 发生时间, "
               f"ry.ID 执行人ID from 病人挂号记录 t join 部门表 bm on t.执行部门ID = bm.id left join 人员表 ry on "
               f"t.执行人 = ry.姓名 WHERE t.病人ID = {patient_id} "
               f"and TRUNC(t.发生时间) = TRUNC(SYSDATE) order by t.发生时间 desc"
    })


def query_patient_info(card_no):
    """
    根据患者就诊卡号 / 身份证号 查询患者信息
    :param card_no:
    :return:
    """
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
        return history_record

    patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select * from 病人信息 where 就诊卡号 = '{card_no}' or 身份证号 = '{card_no}' order by 就诊时间 desc"
    })
    if not patient_infos:
        raise Exception('未找到该患者信息，请仔细核对 就诊卡号/身份证号 是否正确')
    patient_age = calculate_age_from_id(patient_infos[0].get('身份证号'), patient_infos[0].get('出生日期'))
    if patient_infos[0].get('手机号') and len(patient_infos[0].get('手机号')) > 1:
        patient_phone = patient_infos[0].get('手机号')
    else:
        patient_phone = patient_infos[0].get('联系人电话')
    data = {
        "sick_id": patient_infos[0].get('病人ID'), "patient_name": patient_infos[0].get('姓名'),
        "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_age,
        "patient_phone": patient_phone, "birth_day": patient_infos[0].get('出生日期'),
        "marital_status": patient_infos[0].get('婚姻状况'), "occupation": patient_infos[0].get('职业'),
        "home_address": patient_infos[0].get('家庭地址'), "work_unit": patient_infos[0].get('工作单位'),
        "nation": patient_infos[0].get('民族'), "visit_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "card_no": card_no, "allergy_history": "",
        "medical_card_no": patient_infos[0].get('就诊卡号'), "id_card_no": patient_infos[0].get('身份证号')
    }

    # 查询挂号医生信息
    patient_name = data.get('patient_name')
    register_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select t.姓名 姓名, t.执行人 执行人, t.执行部门ID 执行部门ID, bm.名称 部门名称, t.发生时间 发生时间, "
               f"ry.ID 执行人ID from 病人挂号记录 t join 部门表 bm on t.执行部门ID = bm.id left join 人员表 ry on "
               f"t.执行人 = ry.姓名 WHERE t.姓名 = '{patient_name}' and t.记录状态=1 and t.执行状态!=-1 "
               f"and TRUNC(t.发生时间) = TRUNC(SYSDATE) order by t.发生时间 desc"
    })
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
    del db
    return surveys


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
                f"where a.su_id = {int(su_id)} order by a.order_by_id"
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
        surveys_record.pop('doctor_id')
        surveys_record.pop('doctor_name')
        surveys_record.pop('dept_id')
        surveys_record.pop('dept_name')
    surveys_record['treatment_advice'] = ''
    surveys_record['initial_impression'] = ''
    surveys_record['status'] = 1

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
         item.get('other_answer') if item.get('other_answer') else "")
        for item in question_list if item.get('answer')
    ]

    # 生成插入的 SQL
    placeholders = ', '.join(['%s'] * len(answer_list[0]))
    insert_sql = f"INSERT INTO nsyy_gyl.sq_surveys_answer (re_id, qu_id, answer, qu_unit, other_answer) VALUES ({placeholders})"
    last_rowid = db.execute_many(insert_sql, answer_list, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷记录答案列表入库失败! ", insert_sql, str(args))
    del db


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
         item.get('other_answer') if item.get('other_answer') else "")
        for item in question_list if item.get('answer')
    ]

    insert_sql = """
            INSERT INTO nsyy_gyl.sq_surveys_answer (re_id, qu_id, answer, qu_unit, other_answer) 
            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE re_id = VALUES(re_id), qu_id = VALUES(qu_id), 
            answer = VALUES(answer), qu_unit = VALUES(qu_unit), other_answer = VALUES(other_answer) 
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
    test_results = query_test_result(survey_record.get('card_no'), visit_time)
    examination_result = query_examination_result(survey_record.get('card_no'), visit_time)
    return survey_record, answer_list, test_results, examination_result


def query_question_survey_by_patient_id(patient_id):
    """
    his 系统 根据 病人 id 查询问卷记录
    :param patient_id:
    :return:
    """
    # 根据 病人 id 查询病人信息
    patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select * from 病人信息 where 病人ID = '{patient_id}' "})
    medical_card_no, id_card_no = patient_infos[0].get('就诊卡号'), patient_infos[0].get('身份证号')
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
    检查项目 涉及到两个数据库，其中有一个字段（影像所见）在两个数据库中定义的类型不同，导致关联查询出错，所以拆分成两个 sql
    :param card_no:
    :param visit_date:
    :return:
    """

    sql = f"""
        select gh.门诊号, xx.就诊卡号, xx.身份证号, gh.id 挂号ID, yz.id 医嘱ID 
          from 病人挂号记录 gh join 病人信息 xx on gh.病人id = xx.病人id
          join 病人医嘱记录 yz on gh.病人id = yz.病人id and gh.no = yz.挂号单
          where gh.登记时间 >= to_date('{visit_date}', 'yyyy-mm-dd') 
          and gh.登记时间 < to_date('{visit_date}', 'yyyy-mm-dd') + 1
          and (xx.就诊卡号 = '{card_no}' or xx.身份证号 = '{card_no}')
    """
    data = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})
    if not data:
        return []

    doc_advice_ids = []
    for d in data:
        doc_advice_ids.append(str(d.get('医嘱ID')))

    # 根据医嘱 id 列表 查询 检查项目结果
    ids = ', '.join(f"'{item}'" for item in doc_advice_ids)
    sql = f"""
            select a.医嘱ID "doc_advice_id", a.医嘱ID "unique_key", a.检查名称 "item_name", a.诊断印象 "item_result", a.影响所见 "img_result", 
            a.图像地址 "img_url", a.报告地址 "report_url" from V_tuxiangdizhi@pacslink a where 医嘱ID in ({ids})
        """
    examination_results = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})

    return examination_results


def query_examination_result(card_no, visit_date):
    """
    查询检验项目结果
    :param card_no:
    :param visit_date:
    :return:
    """
    sql = f"""
            select gh.门诊号 "outpatient_num", xx.身份证号 "id_card_no", gh.id 挂号ID, yz.id "doc_advice_id", 
                   d.名称 "item_name", c.中文名 "item_sub_name", b.检验结果 "item_sub_result",
                   b.结果参考 "item_sub_refer", b.单位 "item_sub_unit",
                   b.结果标志, b.项目ID "item_sub_id", yz.id||b.项目ID "unique_key",
                   case
                     when b.结果标志 = '1' then
                      '正常'
                     when b.结果标志 = '2' then
                      '偏低'
                     when b.结果标志 = '3' then
                      '偏高'
                     when b.结果标志 = '4' then
                      '阳性(异常)'
                     when b.结果标志 = '5' then
                      '警戒下限'
                     when b.结果标志 = '6' then
                      '警戒上限'
                     else
                      null
                   end "item_sub_flag"
              from 病人挂号记录 gh join 病人信息 xx on gh.病人id = xx.病人id join 病人医嘱记录 yz on gh.病人id = yz.病人id
              and gh.no = yz.挂号单 join 检验申请组合 e on yz.id = e.医嘱id join 检验组合项目 d on d.id = e.组合id 
              join 检验报告明细 b on b.组合id = d.id and b.标本id = e.标本id join 检验指标 c on b.项目id = c.id
             where gh.登记时间 >= to_date('{visit_date}', 'yyyy-mm-dd') 
             and gh.登记时间 < to_date('{visit_date}', 'yyyy-mm-dd') + 1
             and (xx.就诊卡号 = '{card_no}' or xx.身份证号 = '{card_no}')
        """

    test_results = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})
    return test_results


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
        time_sql = f" where visit_time BETWEEN '{start_time}' AND '{end_time}' "

    if query_type == 'question':
        # 统计问卷报表
        query_sql = f"select count(*) count, su_id from nsyy_gyl.sq_surveys_record {time_sql} group by su_id"
    elif query_type == 'medical_guide':
        # 统计导医报表
        query_sql = f"select count(*) count, operator from nsyy_gyl.sq_surveys_record {time_sql} group by operator"
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
                f"from nsyy_gyl.sq_surveys_question_association a join nsyy_gyl.sq_questions b on a.qu_id = b.id " \
                f"where a.su_id = {int(survey_record.get('su_id'))} order by a.order_by_id"
    question_list = db.query_all(query_sql)

    query_sql = f"select * from nsyy_gyl.sq_surveys_answer where re_id = {int(re_id)} "
    answer_list = db.query_all(query_sql)
    for item in answer_list:
        item['answer'] = json.loads(item.get('answer'))
    answer_dict = {item['qu_id']: item for item in answer_list}
    del db

    medical_data = assembly_data(question_list, answer_dict)

    # 查询 检查/检验 结果

    visit_time = datetime.strptime(survey_record.get('visit_time'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    test_results = query_test_result(survey_record.get('card_no'), visit_time)
    examination_result = query_examination_result(survey_record.get('card_no'), visit_time)

    # 收集辅助检查, 收集辅助检查结果
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
        auxiliary_examination.append(item['item_name'])
        auxiliary_examination_result.append(item.get('item_result'))

    medical_data[5] = '、'.join(auxiliary_examination)
    medical_data[6] = '、'.join(auxiliary_examination_result)

    # todo 初步印象 治疗意见 应该是医生自己写的？？
    # 查询诊断（初步印象）
    medical_data[7] = query_zhen_duan(survey_record.get('patient_name'), visit_time)
    medical_data[8] = survey_record.get('treatment_advice', '')

    return survey_record, medical_data


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


def submit_treatment_advice(json_data):
    """
    提交治疗意见 & 初步诊断
    :param json_data:
    :return:
    """
    re_id = json_data.get('re_id')
    initial_impression = json_data.get('initial_impression', "")
    treatment_advice = json_data.get('treatment_advice', "")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f"UPDATE nsyy_gyl.sq_surveys_record SET initial_impression = '{initial_impression}', " \
                 f"treatment_advice = '{treatment_advice}' WHERE id = {int(re_id)}"
    db.execute(update_sql, need_commit=True)
    del db


def query_zhen_duan(patient_name, visit_time):
    sql = f"select t.姓名 姓名, t.病人ID, t.ID, t.执行人 执行人, t.执行部门ID 执行部门ID, bm.名称 部门名称, t.发生时间 发生时间, " \
            f"ry.ID 执行人ID from 病人挂号记录 t join 部门表 bm on t.执行部门ID = bm.id left join 人员表 ry on " \
            f"t.执行人 = ry.姓名 WHERE t.姓名 = '{patient_name}' and t.记录状态=1 and t.执行状态!=-1 " \
            f"and TRUNC(t.发生时间) >= to_date('{visit_time}', 'yyyy-mm-dd') " \
          f"and TRUNC(t.发生时间) < to_date('{visit_time}', 'yyyy-mm-dd') + 1 order by t.发生时间 desc"

    register_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": sql
    })
    if not register_infos:
        return ""

    patient_id = register_infos[0].get('病人ID')
    homepage_id = register_infos[0].get('ID')
    zhenduans = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
        "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"select t2.编码,t2.名称,t.* from 病人诊断记录 t join 疾病编码目录 t2 on t.疾病id=t2.id "
               f"where 病人ID={patient_id} and 主页ID={homepage_id}"
    })
    if not zhenduans:
        return ""

    return ", ".join([i.get('名称') for i in zhenduans])

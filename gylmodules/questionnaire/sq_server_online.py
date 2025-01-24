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
            # response = requests.post(f"http://192.168.3.12:6080/{url}", timeout=3, json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", timeout=3, json=param)
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


def call_new_his(sql: str, clobl: list = None):
    """
    调用新 his 查询数据
    :param sql:
    :return:
    """
    param = {"key": "o4YSo4nmde9HbeUPWY_FTp38mB1c", "sys": "newzt", "sql": sql}
    if clobl:
        param['clobl'] = clobl
    query_oracle_url = "http://192.168.3.12:6080/oracle_sql"
    if global_config.run_in_local:
        query_oracle_url = "http://192.168.124.53:6080/oracle_sql"

    data = []
    try:
        response = requests.post(query_oracle_url, json=param)
        data = json.loads(response.text)
        data = data.get('data')
    except Exception as e:
        print(datetime.now(), '问卷调查 调用新 HIS 查询数据失败：' + str(param) + e.__str__())

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
           SELECT brxx.SHENFENZH 身份证号, brxx.JIUZHENKH 就诊卡号, brxx.CHUSHENGRQ 出生日期, brxx.LIANXIRDH 联系人电话, 
    brxx.XIANZHUZHIDH 现住址电话, brxx.BINGRENID 病人ID, brxx.XINGMING 姓名, brxx.XINGBIEMC 性别, brxx.XINGBIEDM 性别代码, 
    brxx.HUNYINMC 婚姻, brxx.ZHIYEMC 职业, brxx.HUKOUDZ 户口地址, brxx.XIANZHUZHI 现住址, brxx.GONGZUODW 工作单位, 
    brxx.MINZUMC 民族 FROM df_bingrenzsy.gy_bingrenxx brxx WHERE brxx.JIUZHENKH = '{card_no}'  
    OR brxx.SHENFENZH = '{card_no}' ORDER BY brxx.JIANDANGRQ DESC
        """
        patient_infos = call_new_his(sql)
        if not patient_infos:
            raise Exception('未找到该患者信息，请仔细核对 就诊卡号/身份证号 是否正确')
        patient_age = calculate_age_from_id(patient_infos[0].get('身份证号'), patient_infos[0].get('出生日期'))
        if patient_infos[0].get('现住址电话') and len(patient_infos[0].get('现住址电话')) > 1:
            patient_phone = patient_infos[0].get('现住址电话')
        else:
            patient_phone = patient_infos[0].get('联系人电话')
        data = {
            "sick_id": patient_infos[0].get('病人ID'), "patient_name": patient_infos[0].get('姓名'),
            "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_age,
            "patient_phone": patient_phone, "birth_day": patient_infos[0].get('出生日期'),
            "marital_status": patient_infos[0].get('婚姻'), "occupation": patient_infos[0].get('职业'),
            "home_address": patient_infos[0].get('现住址'), "work_unit": patient_infos[0].get('工作单位'),
            "nation": patient_infos[0].get('民族'), "visit_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "card_no": card_no, "allergy_history": "",
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
    register_infos = call_new_his(sql)
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
        surveys_record.pop('doctor_id')
        surveys_record.pop('doctor_name')
        surveys_record.pop('dept_id')
        surveys_record.pop('dept_name')
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
    patient_infos = call_new_his(f"SELECT brxx.SHENFENZH, brxx.JIUZHENKH FROM df_bingrenzsy.gy_bingrenxx brxx "
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
    检查项目 涉及到两个数据库，其中有一个字段（影像所见）在两个数据库中定义的类型不同，导致关联查询出错，所以拆分成两个 sql
    :param card_no:
    :param visit_date:
    :return:
    """
    sql = f"""
        SELECT jz.guahaoid 挂号ID, brxx.jiuzhenkh 就诊卡号, brxx.shenfenzh 身份证号, mzyz.yizhuid "doc_advice_id", 
        jc.yizhuid "unique_key", jc.jianchaxmmc "item_name", jc.zhenduan "item_result", jc.jianchasuojian "img_result", 
        jc.yinxiangurl "img_url", jc.yingxiangbgurl "report_url" FROM df_lc_menzhen.mz_yizhu mzyz 
        JOIN df_lc_menzhen.zj_jiuzhenxx jz ON mzyz.jiuzhenid = jz.jiuzhenid
        JOIN df_bingrenzsy.gy_bingrenxx brxx ON mzyz.bingrenid = brxx.bingrenid
        JOIN df_cdr.yj_jianchabg jc ON mzyz.yizhuid = jc.yizhuid
        WHERE (brxx.shenfenzh = '{card_no}' OR brxx.jiuzhenkh = '{card_no}') 
        AND jz.xitongsj >= to_date('{visit_date}','yyyy-mm-dd')
    """
    test_results = call_new_his(sql, ['img_result'])
    return test_results


def query_examination_result(card_no, visit_date):
    """
    查询检验项目结果
    :param card_no:
    :param visit_date:
    :return:
    """
    sql = f"""
               SELECT 
                   NULL AS outpatient_num,
                   brxx.shenfenzh AS "id_card_no",
                   jz.guahaoid AS 挂号ID,
                   mzyz.yizhuid AS "doc_advice_id",
                   jy.jianchamd AS "item_name",
                   jymx.zhongwenmc AS "item_sub_name",
                   jymx.jianyanjg AS "item_sub_result",
                   jymx.cankaofw AS "item_sub_refer",
                   jymx.dangwei AS "item_sub_unit",
                   jymx.yichangbz,
                   jymx.jianyanxmid AS "item_sub_id",
                   mzyz.yizhuid || jymx.shiyanxmid AS "unique_key",
                   CASE
                       WHEN jymx.yichangbz = 'L' THEN '低'
                       WHEN jymx.yichangbz = 'H' THEN '高'
                       WHEN jymx.yichangbz = 'E' THEN '阳性'
                       WHEN jymx.yichangbz = 'D' THEN '阴性'  
                       ELSE '正常'
                   END AS "item_sub_flag"
               FROM df_lc_menzhen.mz_yizhu mzyz
               JOIN df_lc_menzhen.zj_jiuzhenxx jz ON mzyz.jiuzhenid = jz.jiuzhenid
               JOIN df_bingrenzsy.gy_bingrenxx brxx ON mzyz.bingrenid = brxx.bingrenid
               JOIN df_shenqingdan.yj_jianyansqd jysqd ON mzyz.yizhuid = jysqd.yizhubh
               JOIN (
                   SELECT 
                       jiluid,
                       jianyanzt,
                       REGEXP_SUBSTR(shenqingdid, '[^,]+', 1, LEVEL) AS shenqingdanid,
                       REGEXP_SUBSTR(jianyanxmid, '[^+]+', 1, LEVEL) AS jianyanxmid,
                       jianchamd
                   FROM df_cdr.yj_jianyanbg 
                   WHERE menzhenzybz = '1' 
                   CONNECT BY LEVEL <= REGEXP_COUNT(shenqingdid, ',') + 1 AND PRIOR jiluid = jiluid AND PRIOR DBMS_RANDOM.VALUE IS NOT NULL
               ) jy ON jysqd.jianyansqdid = jy.shenqingdanid 
               LEFT JOIN df_cdr.yj_jianyanbgmx jymx ON jy.jiluid = jymx.jiluid  AND jy.jianyanxmid = jymx.jianyanxmid
               WHERE  jy.jianyanzt = 1 AND jz.xitongsj >= to_date('{visit_date}','yyyy-mm-dd') 
               and (jz.jiuzhenkh = '{card_no}' or brxx.shenfenzh = '{card_no}')           
           """

    examination_results = call_new_his(sql)
    return examination_results


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
    qanswer_list = db.query_all(query_sql)
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
    medical_data[7] = query_zhen_duan(survey_record.get('sick_id'), visit_time)
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


def submit_medical_record(json_data):
    """
    提交（新增/更新）门诊病历
    :param json_data:
    :return:
    """
    re_id = json_data.get('re_id')
    sick_id = json_data.get('sick_id')
    visit_date = json_data.get('visit_date')
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
    fuzhujiancha = json_data.get('fuzhujiancha', '')
    fuzhujiancha_remark = json_data.get('fuzhujiancha_remark', '')
    fuzhujiancha_ret = json_data.get('fuzhujiancha_ret', '')
    fuzhujiancha_ret_remark = json_data.get('fuzhujiancha_ret_remark', '')
    chubuzhenduan = json_data.get('chubuzhenduan', '')
    yijian = json_data.get('yijian', '')

    args = (re_id, sick_id, visit_date, zhusu, zhusu_remark, xianbingshi, xianbingshi_remark, jiwangshi,
            jiwangshi_remark, tigejiancha, tigejiancha_remark, zhuankejiancha, zhuankejiancha_remark,
            fuzhujiancha, fuzhujiancha_remark, fuzhujiancha_ret, fuzhujiancha_ret_remark, chubuzhenduan, yijian)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = """
            INSERT INTO nsyy_gyl.sq_surveys_detail (re_id, sick_id, visit_date, zhusu, zhusu_remark,
            xianbingshi, xianbingshi_remark, jiwangshi, jiwangshi_remark, tigejiancha, tigejiancha_remark,
            zhuankejiancha, zhuankejiancha_remark, fuzhujiancha, fuzhujiancha_remark, fuzhujiancha_ret, 
            fuzhujiancha_ret_remark, chubuzhenduan, yijian) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            ON DUPLICATE KEY UPDATE re_id = VALUES(re_id), sick_id = VALUES(sick_id), 
            visit_date = VALUES(visit_date), zhusu = VALUES(zhusu), zhusu_remark = VALUES(zhusu_remark), 
            xianbingshi = VALUES(xianbingshi), xianbingshi_remark = VALUES(xianbingshi_remark), 
            jiwangshi = VALUES(jiwangshi), jiwangshi_remark = VALUES(jiwangshi_remark), 
            tigejiancha = VALUES(tigejiancha), tigejiancha_remark = VALUES(tigejiancha_remark), 
            zhuankejiancha = VALUES(zhuankejiancha), zhuankejiancha_remark = VALUES(zhuankejiancha_remark), 
            fuzhujiancha = VALUES(fuzhujiancha), fuzhujiancha_remark = VALUES(fuzhujiancha_remark), 
            fuzhujiancha_ret = VALUES(fuzhujiancha_ret), fuzhujiancha_ret_remark = VALUES(fuzhujiancha_ret_remark), 
            chubuzhenduan = VALUES(chubuzhenduan), yijian = VALUES(yijian) 
    """
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("问卷记录详情入库失败! ", insert_sql)
    del db


def query_zhen_duan(sick_id, visit_time):
    sql = f"""
    SELECT brxx.zhenduanmc 名称 FROM df_lc_menzhen.zj_zhenduan brxx WHERE brxx.bingrenid = '{sick_id}' and
    TRUNC(brxx.chuangjiansj) >= to_date('{visit_time}', 'yyyy-mm-dd') 
    and TRUNC(brxx.chuangjiansj) < to_date('{visit_time}', 'yyyy-mm-dd') + 1 order by brxx.chuangjiansj desc
    """
    zhenduans = call_new_his(sql)
    if not zhenduans:
        return ""

    return ", ".join([i.get('名称') for i in zhenduans])


def patient_quest_details(json_data):
    """
    查询患者门诊问卷详情（根据病人 ID + 就诊日期（yyyy-mm-dd）查询）
    :param json_data:
    :return:
    """
    patient_id = json_data.get('patient_id')
    ques_date = json_data.get('ques_date')

    query_sql = f"select b.title, a.* from nsyy_gyl.sq_surveys_record a join nsyy_gyl.sq_surveys b on a.su_id = b.id " \
                f"WHERE sick_id = '{patient_id}' and DATE(visit_time) = '{ques_date}'"
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    records = db.query_all(query_sql)
    del db

    if not records:
        return {
            "patient_id": patient_id,
            "ques_date": ques_date,
            "ReturnCode": 1,
            "ReturnMessage": "未查询到患者当天的问卷记录",
            "ques_dtl": []
        }

    ques_dtl = []
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
        "ReturnMessage": "未查询到患者当天的问卷记录",
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
    test_results = query_test_result(survey_record.get('card_no'), visit_time)
    examination_result = query_examination_result(survey_record.get('card_no'), visit_time)
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

    # 查询诊断（初步印象）
    medical_data['zhenduan'] = query_zhen_duan(survey_record.get('sick_id'), visit_time)
    return medical_data, answer_dict

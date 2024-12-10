# import redis
# import json
# import requests
#
# from itertools import groupby
# from datetime import datetime
# from gylmodules import global_config
# from gylmodules.critical_value import cv_config
# from gylmodules.utils.db_utils import DbUtil
# from gylmodules.questionnaire import question_config
#
#
# def call_third_systems_obtain_data(url: str, type: str, param: dict):
#     data = []
#     if global_config.run_in_local:
#         try:
#             # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
#             response = requests.post(f"http://192.168.124.53:6080/{url}", timeout=3, json=param)
#             data = json.loads(response.text)
#             if type != 'his_pers_reg':
#                 data = data.get('data')
#         except Exception as e:
#             print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
#     else:
#         if type == 'orcl_db_read':
#             from tools import orcl_db_read
#             data = orcl_db_read(param)
#         elif type == 'his_pers_reg':
#             from tools import his_pers_reg
#             data = his_pers_reg(param)
#         else:
#             print('call_third_systems_obtain_data 不支持 ', type)
#     return data
#
#
# """
# 根据患者就诊卡号 / 身份证号 查询患者信息
# 查询出来的科室是 id， 需要依赖 危急值系统缓存的科室信息查询 科室名字
# """
#
#
# def query_patient_info(card_no):
#     patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
#         "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#         "sql": f"select * from 病人信息 where 就诊卡号 = '{card_no}' or 身份证号 = '{card_no}' order by 就诊时间 desc"
#     })
#     if not patient_infos:
#         raise Exception('未找到该患者挂号信息，请仔细核对 就诊卡号/身份证号 是否正确')
#     data = {
#         "sick_id": patient_infos[0].get('病人ID'), "patient_name": patient_infos[0].get('姓名'),
#         "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_infos[0].get('年龄'),
#         "patient_phone": patient_infos[0].get('联系人电话'), "birth_day": patient_infos[0].get('出生日期'),
#         "marital_status": patient_infos[0].get('婚姻状况'), "occupation": patient_infos[0].get('职业'),
#         "home_address": patient_infos[0].get('家庭地址'), "work_unit": patient_infos[0].get('工作单位'),
#         "nation": patient_infos[0].get('民族'), "visit_time": datetime.now(), "card_no": card_no, "allergy_history": "",
#         "medical_card_no": patient_infos[0].get('就诊卡号'), "id_card_no": patient_infos[0].get('身份证号')
#     }
#     return data
#
#
# def create_patient_info(json_data):
#     # 创建患者信息
#     create_ret = call_third_systems_obtain_data('his_socket', 'his_pers_reg', {
#         "type": "his_pers_reg", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#         "pers_name": json_data.get('pers_name'), "pers_mobile": json_data.get('pers_mobile'),
#         "pers_id_no": json_data.get('pers_id_no'), "pers_id_type": 1})
#
#     if 'PatientID' not in create_ret or not create_ret.get('PatientID'):
#         raise Exception('创建患者信息失败, 请稍后重试')
#
#     return query_patient_info(json_data.get('pers_id_no'))
#
#
# # """
# # 查询问题模版列表
# # """
# #
# #
# # def query_tpl_list():
# #     return {'tpl_type': question_config.tpl_type, 'tpl_type_detail': question_config.tpl_type_detail}
#
#
# """
# 查询问题列表
# """
#
#
# def query_question_list(json_data):
#     tpl_type = json_data.get('tpl_type')
#     tpl_type_detail = json_data.get('tpl_type_detail')
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = f"select * from nsyy_gyl.question_list where tpl_type = {question_config.tpl_type['通用']} " \
#                 f"or (tpl_type = {tpl_type} and tpl_type_detail = {tpl_type_detail}) "
#     question_list = db.query_all(query_sql)
#     del db
#
#     sorted_data = sorted(question_list, key=lambda x: (x['type'], x['sort_num']))
#     for d in sorted_data:
#         if d['ans_list']:
#             d['ans_list'] = json.loads(d['ans_list'])
#             if type(d['ans_list']) == dict:
#                 d['ans_list'] = d['ans_list'].get(f"{tpl_type}-{tpl_type_detail}", ["其他"])
#                 # d['ans_list'] = json.loads(d['ans_list'])
#     return sorted_data
#
#
# """
# 问卷调查记录
# """
#
#
# def question_survey_ans(json_data):
#     # 提取病历所需数据， 提取出 主诉/现病史/既往史 然后把所有数据拼起来
#     ans_data = []
#     data = json_data['ans_list']
#     # 先按 'type' 值排序
#     data.sort(key=lambda x: x['type'])
#     # 使用 groupby 按 'type' 分组
#     for key, group in groupby(data, key=lambda x: x['type']):
#         title = '未知'
#         if int(key) == 1:
#             title = '主诉'
#         elif int(key) == 2:
#             title = '现病史'
#         elif int(key) == 3:
#             title = '既往史'
#         elif int(key) == 4:
#             title = '体格检查'
#         ans_data.append({'sort_num': int(key), 'title': title, 'content': assembly_data(group)})
#
#     json_data['medical_card_no'] = json_data['patient_info'].get('medical_card_no', "0")
#     json_data['id_card_no'] = json_data['patient_info'].get('id_card_no', "0")
#     json_data['patient_info'] = json.dumps(json_data['patient_info'], default=str, ensure_ascii=False)
#     json_data['ans_list'] = json.dumps(json_data['ans_list'], default=str, ensure_ascii=False)
#     json_data['create_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     json_data['ans_data'] = json.dumps(ans_data, default=str, ensure_ascii=False)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     fileds = ','.join(json_data.keys())
#     args = str(tuple(json_data.values()))
#     insert_sql = f"INSERT INTO nsyy_gyl.question_survey_list ({fileds}) VALUES {args}"
#     last_rowid = db.execute(insert_sql, need_commit=True)
#     if last_rowid == -1:
#         del db
#         raise Exception("问卷调查记录入库失败! ", insert_sql, str(args))
#     del db
#
#
# def update_question_survey_ans(json_data):
#     # 提取病历所需数据， 提取出 主诉/现病史/既往史 然后把所有数据拼起来
#     ans_data = []
#     data = json_data['ans_list']
#     # 先按 'type' 值排序
#     data.sort(key=lambda x: x['type'])
#     # 使用 groupby 按 'type' 分组
#     for key, group in groupby(data, key=lambda x: x['type']):
#         title = '未知'
#         if int(key) == 1:
#             title = '主诉'
#         elif int(key) == 2:
#             title = '现病史'
#         elif int(key) == 3:
#             title = '既往史'
#         elif int(key) == 4:
#             title = '体格检查'
#         ans_data.append({'sort_num': int(key), 'title': title, 'content': assembly_data(group)})
#
#     qs_id = json_data.get('id')
#     ans_data = json.dumps(ans_data, default=str, ensure_ascii=False)
#     ans_list = json.dumps(json_data['ans_list'], default=str, ensure_ascii=False)
#     ans_list = ans_list.replace('\r', '\\r')
#     ans_list = ans_list.replace('\n', '\\n')
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     update_sql = f"update nsyy_gyl.question_survey_list set ans_list = '{ans_list}', ans_data = '{ans_data}' " \
#                  f"where id = {qs_id} "
#     db.execute(update_sql, need_commit=True)
#     del db
#
#
# """
# 组装数据
# """
#
#
# def assembly_data(data):
#     content = []
#     for x in data:
#         if int(x['ans_type']) in (1, 2, 4, 6):
#             # 1=填空 2=单选
#             if type(x['question_answer']) == str:
#                 ans = x['question_answer'] if x['question_answer'] else '/'
#             elif type(x['question_answer']) == list:
#                 ans = str(x['question_answer'][0]) if x['question_answer'] else '/'
#         elif int(x['ans_type']) == 3:
#             # 多选
#             ans = '、'.join(x['question_answer']) if x['question_answer'] else '/'
#         elif int(x['ans_type']) == 5:
#             # 双步进器（血压）
#             ans = '/'.join(x['question_answer']) if x['question_answer'] else '/'
#         elif int(x['ans_type']) in (7, 8):
#             # 扩展 选择 类型
#             ans = []
#             for item in x.get('ans_list'):
#                 if int(item.get('checked')) == 1:
#                     # 选中
#                     option_name = item['option_name']
#                     exten_data = item.get('exten_data')
#                     if exten_data:
#                         for exten in exten_data:
#                             exten_result = exten.get('exten_result') \
#                                 if type(exten.get('exten_result')) == str else ', '.join(exten.get('exten_result'))
#                             option_name = option_name + f" {exten.get('exten_prefix', '')} " \
#                                                         f"{exten_result} " \
#                                                         f"{exten.get('exten_suffix', '')} 、"
#                     if option_name.endswith("、"):
#                         option_name = option_name[:-1]
#                     ans.append(option_name)
#             ans = '、'.join(ans)
#         else:
#             print('未处理类型', x)
#
#         ans = ans + "   " + str(x.get('other_answer', ''))
#         prefix = x['ans_prefix'] if x['ans_prefix'] else ''
#         suffix = x['ans_suffix'] if x['ans_suffix'] else ''
#
#         content.append({'question_name': x['medical_record_field'], 'question_answer': f"{prefix} {ans} {suffix}"})
#     return content
#
#
# """
# 查询问卷调查
# 如果使用问卷调查 id ，查询详情包括题目 & 答案
# 如果根据用户信息查询，仅查询问卷调查列表，不包括题目 & 答案
# """
#
#
# def query_question_survey(json_data):
#     question_id = json_data.get('question_id')
#     patient_name = json_data.get('patient_name')
#     card_no = json_data.get('card_no')
#     doctor = json_data.get('doctor')
#     operator = json_data.get('operator')
#     start_time = json_data.get('start_time')
#     end_time = json_data.get('end_time')
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     if question_id:
#         query_sql = f"select * from nsyy_gyl.question_survey_list where id = {question_id}"
#     else:
#         condition_sql = ""
#         condition_sql = f" patient_name like '%{patient_name}%'" if patient_name else ""
#         if operator:
#             condition_sql = f"{condition_sql} or operator like '%{operator}%'" if condition_sql \
#                 else f" operator like '%{operator}%'"
#         if card_no:
#             condition_sql = f"{condition_sql} or card_no = '{card_no}'" if condition_sql else f"card_no = '{card_no}'"
#         if doctor:
#             condition_sql = f"{condition_sql} or doctor like '%{doctor}%'" if condition_sql \
#                 else f"doctor like '%{doctor}%'"
#         if start_time and end_time:
#             condition_sql = f"{condition_sql} and (create_time between '{start_time}' and '{end_time}') " \
#                 if condition_sql else f"create_time between '{start_time}' and '{end_time}'"
#
#         if not condition_sql:
#             raise Exception("查询条件不足")
#         query_sql = f"select * from nsyy_gyl.question_survey_list where status = 1 and ({condition_sql})"
#
#     test_results, examination_result = [], []
#     if question_id:
#         # 查询问卷详情时 同时查询 检查和检验结果
#         test_results = db.query_all(f'select * from nsyy_gyl.question_test_result where question_id = {question_id}')
#         examination_result = db.query_all(f'select * from nsyy_gyl.question_examination_result where question_id = {question_id}')
#
#     data = db.query_all(query_sql)
#     del db
#     for d in data:
#         d['patient_info'] = json.loads(d['patient_info'])
#         d['ans_list'] = json.loads(d['ans_list'])
#     return data, test_results, examination_result
#
#
# """
# 根据 病人 id 查询历史问卷
# """
#
#
# def query_question_survey_by_patient_id(patient_id):
#     # 根据 病人 id 查询病人信息
#     patient_infos = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
#         "type": "orcl_db_read", "db_source": "nshis",
#         "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
#         "sql": f"select * from 病人信息 where 病人ID = '{patient_id}' "
#     })
#     medical_card_no = patient_infos[0].get('就诊卡号')
#     id_card_no = patient_infos[0].get('身份证号')
#     query_sql = ""
#     if medical_card_no == 0 and id_card_no == 0:
#         raise Exception("未查询到病人信息, 病人 ID = ", patient_id)
#     elif medical_card_no != 0 and id_card_no != 0:
#         query_sql = f"select * from nsyy_gyl.question_survey_list where status = 1 and " \
#                     f"(medical_card_no = '{medical_card_no}' " \
#                     f"or id_card_no = '{id_card_no}') order by create_time desc limit 1"
#     elif medical_card_no != 0:
#         query_sql = f"select * from nsyy_gyl.question_survey_list where status = 1 and" \
#                     f" medical_card_no = '{medical_card_no}' order by create_time desc limit 1"
#     elif id_card_no != 0:
#         query_sql = f"select * from nsyy_gyl.question_survey_list where status = 1 and " \
#                     f" id_card_no = '{id_card_no}' order by create_time desc limit 1"
#     if not query_sql:
#         raise Exception("未查询到病人信息, 病人 ID = ", patient_id)
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     survives = db.query_one(query_sql)
#     del db
#     if survives:
#         survives['patient_info'] = json.loads(survives['patient_info']) if survives['patient_info'] else {}
#         survives['ans_list'] = json.loads(survives['ans_list']) if survives['ans_list'] else {}
#     return survives
#
#
# """
# 查看病历
# """
#
#
# def view_medical_records(qid):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     query_sql = f"select * from nsyy_gyl.question_survey_list where id = {qid}"
#     record = db.query_one(query_sql)
#     del db
#
#     if not record:
#         raise Exception("未查找到病历")
#     ans_data = json.loads(record['ans_data']) if record['ans_data'] else []
#     patient_info = json.loads(record['patient_info']) if record['patient_info'] else []
#     return {"patient_info": patient_info, "ans_data": ans_data}
#
#
# """
# 删除问卷
# """
#
#
# def delete_question_survey(qid):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     delete_sql = f"update nsyy_gyl.question_survey_list set status = 0 where id = {qid}"
#     record = db.execute(delete_sql, need_commit=True)
#     del db
#
#
# # 查询检查项目结果
#
#
# def query_test_result(card_no, visit_date):
#     # 检查项目 涉及到两个数据库，其中有一个字段（影像所见）在两个数据库中定义的类型不同，导致关联查询出错，所以拆分成两个 sql
#     sql = f"""
#         select gh.门诊号, xx.身份证号, gh.id 挂号ID, yz.id 医嘱ID
#           from 病人挂号记录 gh join 病人信息 xx on gh.病人id = xx.病人id
#           join 病人医嘱记录 yz on gh.病人id = yz.病人id and gh.no = yz.挂号单
#           where gh.登记时间 >= to_date('{visit_date}', 'yyyy-mm-dd')
#           and gh.登记时间 < to_date('{visit_date}', 'yyyy-mm-dd') + 1
#           and (gh.门诊号 = '{card_no}' or xx.身份证号 = '{card_no}')
#     """
#     data = medical_order_list = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
#         "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})
#     if not data:
#         return []
#
#     doc_advice_ids = []
#     for d in data:
#         doc_advice_ids.append(str(d.get('医嘱ID')))
#
#     # 根据医嘱 id 列表 查询 检查项目结果
#     ids = ', '.join(f"'{item}'" for item in doc_advice_ids)
#     sql = f"""
#     select a.医嘱ID "doc_advice_id", a.检查名称 "item_name", a.诊断印象 "item_result", a.影响所见 "img_result",
#     a.图像地址 "img_url", a.报告地址 "report_url" from V_tuxiangdizhi@pacslink a where 医嘱ID in ({ids})
#     """
#     examination_results = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
#         "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})
#     return examination_results
#
#
# # 查询检验项目结果
#
# def query_examination_result(card_no, visit_date):
#     sql = f"""
#             select gh.门诊号 "outpatient_num", xx.身份证号 "id_card_no", gh.id 挂号ID, yz.id "doc_advice_id",
#                     d.名称 "item_name", c.中文名 "item_sub_name", b.检验结果 "item_sub_result",
#                    b.结果参考 "item_sub_refer", b.单位 "item_sub_unit", b.结果标志, b.项目ID "item_sub_id",
#                    case
#                      when b.结果标志 = '1' then
#                       '正常'
#                      when b.结果标志 = '2' then
#                       '偏低'
#                      when b.结果标志 = '3' then
#                       '偏高'
#                      when b.结果标志 = '4' then
#                       '阳性(异常)'
#                      when b.结果标志 = '5' then
#                       '警戒下限'
#                      when b.结果标志 = '6' then
#                       '警戒上限'
#                      else
#                       null
#                    end "item_sub_flag"
#               from 病人挂号记录 gh join 病人信息 xx on gh.病人id = xx.病人id join 病人医嘱记录 yz on gh.病人id = yz.病人id
#               and gh.no = yz.挂号单 join 检验申请组合 e on yz.id = e.医嘱id join 检验组合项目 d on d.id = e.组合id
#               join 检验报告明细 b on b.组合id = d.id and b.标本id = e.标本id join 检验指标 c on b.项目id = c.id
#              where gh.登记时间 >= to_date('{visit_date}', 'yyyy-mm-dd')
#              and gh.登记时间 < to_date('{visit_date}', 'yyyy-mm-dd') + 1
#              and (gh.门诊号 = '{card_no}' or xx.身份证号 = '{card_no}')
#         """
#
#     test_results = call_third_systems_obtain_data('int_api', 'orcl_db_read', {
#         "type": "orcl_db_read", "db_source": "nshis", "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql})
#
#     return test_results
#
#
# def bind_result(json_data):
#     question_id = json_data.get('question_id')
#     data = json_data.get('data')
#     bind_type = int(json_data.get('bind_type'))
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     if bind_type == 1:
#         for d in data:
#             d.pop('挂号ID')
#             d.pop('结果标志')
#             d['question_id'] = question_id
#             fileds = ','.join(d.keys())
#             args = str(tuple(d.values()))
#             insert_sql = f"INSERT INTO nsyy_gyl.question_examination_result ({fileds}) VALUES {args}"
#             db.execute(insert_sql, need_commit=True)
#     elif bind_type == 2:
#         for d in data:
#             d['question_id'] = question_id
#             fileds = ','.join(d.keys())
#             args = str(tuple(d.values()))
#             insert_sql = f"INSERT INTO nsyy_gyl.question_test_result ({fileds}) VALUES {args}"
#             db.execute(insert_sql, need_commit=True)
#     del db
#
#
#
#

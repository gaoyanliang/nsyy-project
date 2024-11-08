import uuid
import json
import requests
import redis

from itertools import groupby
from datetime import datetime, timedelta
from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.hyperbaric_oxygen_therapy import hbot_config
from gylmodules.utils.db_utils import DbUtil

pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                            db=cv_config.CV_REDIS_DB, decode_responses=True)


def call_third_systems_obtain_data(type: str, sql: str, db_source: str):
    param = {"type": type, "db_source": db_source, "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql}
    data = []
    if global_config.run_in_local:
        try:
            # response = requests.post(f"http://192.168.3.12:6080/int_api", json=param)
            response = requests.post(f"http://192.168.124.53:6080/int_api", json=param)
            data = json.loads(response.text)
            data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
            from tools import orcl_db_read
            try:
                data = orcl_db_read(param)
            except Exception as e:
                print('orcl_db_read 查询数据失败：', param, e.__str__())
    return data


"""
根据住院号和登记时间，查询病人高压氧医嘱信息
"""


def query_medical_order(patient_id, register_time, db_source):
    data = None
    sql = "select a.*, bm.编码 开嘱科室编码, b.住院号 from 病人医嘱记录 a, 病案主页 b, 部门表 bm " \
          f"where a.病人id=b.病人id and a.主页id=b.主页id and a.开嘱科室id = bm.id and b.住院号='{patient_id}' " \
          f"and a.开嘱时间 >= to_date('{register_time}', 'yyyy-mm-dd') - 5 " \
          f"and a.医嘱内容 like '%高压氧%' and a.执行标记 != -1 and a.医嘱状态 not in (-1, 2, 4)"
    medical_order_list = call_third_systems_obtain_data('orcl_db_read', sql, db_source)
    if medical_order_list:
        data = {
            "homepage_id": medical_order_list[0].get('主页ID'), "doc_advice_id": medical_order_list[0].get('ID'),
            "doc_advice_content": medical_order_list[0].get('医嘱内容'),
            "doc_advice_info": medical_order_list[0].get('医生嘱托'),
            "doc_advice_doc": medical_order_list[0].get('开嘱医生'),
            "start_time": medical_order_list[0].get('开始执行时间'), "patient_id": medical_order_list[0].get('病人ID'),
            "doc_advice_order_num": medical_order_list[0].get('序号'),
            "bill_dept_id": medical_order_list[0].get('开嘱科室ID'),
            "bill_dept_code": medical_order_list[0].get('开嘱科室编码'),
            "execution_dept_id": medical_order_list[0].get('执行科室ID'),
            "bill_people": medical_order_list[0].get('开嘱医生'),
        }
    if len(medical_order_list) > 1:
        print(datetime.now(), 'DEBUG 查询出 ', len(medical_order_list), ' 条高压氧医嘱 住院号=', patient_id,
              register_time)
    return data


"""
根据患者住院号查询患者信息
⚠️ 注意： 查询门诊患者，需要根据 就诊卡号/身份证号 查询，
查询出来的科室是 id， 需要依赖 危急值系统缓存的科室信息查询 科室名字
"""


def query_patient_info(patient_type, patient_id, comp_type):
    db_source = "nshis" if int(comp_type) == 12 else "kfhis"
    data = {}
    if int(patient_type) == 3:
        # 住院
        sql = "select a.姓名,a.性别,a.年龄,a.住院号, a.出院科室id 科室ID, bm.名称 科室, bm.编码 科室编码, a.出院病床 床号, " \
              "a.联系人电话, a.住院医师, a.主页ID, a.病人ID, zd.名称 诊断 from 病案主页 a left join 部门表 bm " \
              "on a.出院科室id=bm.id left join (select distinct 病人ID, 主页ID, jb.名称 from 病人诊断记录 t " \
              "join 疾病编码目录 jb on t.疾病id = jb.id where t.记录来源 = 3 and t.诊断次序 = 1 and t.诊断类型 = 2) zd " \
              f"on a.病人id=zd.病人id and a.主页id=zd.主页id where a.住院号='{patient_id}' and a.出院日期 is null "
        patient_infos = call_third_systems_obtain_data('orcl_db_read', sql, db_source)
        if not patient_infos:
            raise Exception('未找到该住院号对应的患者信息，请仔细核对住院号是否正确')
        data = {
            "sick_id": patient_infos[0].get('病人ID'), "homepage_id": patient_infos[0].get('主页ID'),
            "doctor_name": patient_infos[0].get('住院医师'), "patient_name": patient_infos[0].get('姓名'),
            "patient_id": patient_id, "patient_sex": patient_infos[0].get('性别'),
            "patient_age": patient_infos[0].get('年龄'), "patient_dept": patient_infos[0].get('科室'),
            "patient_dept_id": patient_infos[0].get('科室ID'), "patient_dept_code": patient_infos[0].get('科室编码'),
            "diagnosis": patient_infos[0].get('诊断'), "patient_phone": patient_infos[0].get('联系人电话'),
            "course_of_treatment": "", "patient_bed": patient_infos[0].get('床号')
        }
    elif int(patient_type) == 1:
        # 门诊
        sql = 'select a.*, bm.编码 执行部门编码, bm.名称 执行部门名称, b.联系人电话 ' \
              'from 病人挂号记录 a left join 病人信息 b on a.病人id=b.病人id join 部门表 bm on a.执行部门id = bm.id ' \
              f"where ( b.就诊卡号 like '%{patient_id}%' or b.身份证号 like '%{patient_id}%' ) order by a.登记时间 desc "
        patient_infos = call_third_systems_obtain_data('orcl_db_read', sql, db_source)
        if not patient_infos:
            raise Exception('未找到该住院号对应的患者信息，请仔细核对住院号是否正确')
        data = {
            "sick_id": patient_infos[0].get('病人ID'), "patient_name": patient_infos[0].get('姓名'),
            "doctor_name": patient_infos[0].get('执行人'), "patient_id": patient_id,
            "patient_sex": patient_infos[0].get('性别'), "patient_age": patient_infos[0].get('年龄').replace('岁', ''),
            "patient_dept": patient_infos[0].get('执行部门名称'), "patient_dept_id": patient_infos[0].get('执行部门ID'),
            "patient_dept_code": patient_infos[0].get('执行部门编码'), "diagnosis": "",
            "patient_phone": patient_infos[0].get('联系人电话'), "course_of_treatment": ""
        }
    return data


"""
查询生命体征
"""


def query_vital_signs(sick_id, homepage_id, db_source):
    data = {}
    if db_source == 'nshis':
        sql = f"""
               select t.patient_id, t.visit_id, t.create_time, t.theme_code, t2.item_name, t2.item_value 
               from docs_eval_report_rec@YDHLCIS t join docs_eval_report_detail_rec@YDHLCIS t2 on t.report_id = t2.report_id
               and t2.item_name in ('呼吸', '体温', '脉搏', '血压') and t2.enabled_value = 'Y' and t.enabled_value = 'Y'
               and t.theme_code like '%首次护理评估单%' where patient_id = '{sick_id}' and visit_id = '{homepage_id}'
                """
    else:
        sql = f"""
                select 住院号, 项目名称 ITEM_NAME, 记录内容 ITEM_VALUE, 记录时间
                from (select 住院号, 项目名称, 记录内容, 记录时间,
                rank() over(partition by 住院号 order by 记录时间 desc) sn
                from (select g.住院号, t3.记录id, t3.记录时间, t3.项目名称, t3.记录内容,
                       count(1) over(partition by g.病人ID, g.主页ID, t3.记录id) cn
                  from 病案主页 g join 病人护理文件 t on g.病人id = t.病人id and g.主页id = t.主页id
                  join 病人护理数据 t2 on t.id = t2.文件id join 病人护理明细 t3 on t2.id = t3.记录id
                 where regexp_like(t3.项目名称, '(体温|呼吸|脉搏|舒张压|收缩压)')
                   and g.病人ID = '{sick_id}' and g.主页ID = '{homepage_id}')
                where cn = 5) where sn = 1
        """
    vital_signs = call_third_systems_obtain_data('orcl_db_read', sql, db_source)
    if not vital_signs:
        return data
    b = 'h/l'
    for d in vital_signs:
        data[d['ITEM_NAME']] = d['ITEM_VALUE']
        if d['ITEM_NAME'].__contains__('收缩压'):
            b = b.replace('h', d['ITEM_VALUE'])
        if d['ITEM_NAME'].__contains__('舒张压'):
            b = b.replace('l', d['ITEM_VALUE'])
    if '血压' not in data:
        data['血压'] = b
    return data


"""
高压氧治疗登记
"""


def register(json_data):
    date_to_compare = datetime.strptime(json_data.get('start_date'), '%Y-%m-%d')
    if date_to_compare.date() > datetime.now().date():
        json_data['execution_status'] = hbot_config.register_status['not_started']
    elif date_to_compare.date() == datetime.now().date():
        json_data['execution_status'] = hbot_config.register_status['in_progress']
    else:
        raise Exception('开始时间不能小于今天')

    patient_id = json_data.get('patient_id')
    json_data['register_id'] = str(uuid.uuid4())
    json_data['register_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    json_data['medical_order_status'] = hbot_config.medical_order_status['unordered']

    doc1 = {
        'b': '', 't': '', 'p': '', 'r': '',
        'map': '0.1', 'order': '1', 'method': 2, 'minute': '105', 'number': '1', 'disease': []
    }
    if int(json_data.get('patient_type')) == 3:
        db_source = 'nshis' if int(json_data.get('comp_type')) == 12 else 'kfhis'
        # 1. 根据住院号查询是否存在医嘱
        medical_order_info = query_medical_order(patient_id, datetime.today().strftime('%Y-%m-%d'), db_source)
        if medical_order_info and len(medical_order_info) > 1:
            json_data['medical_order_status'] = hbot_config.medical_order_status['ordered']
            json_data['medical_order_info'] = json.dumps(medical_order_info, default=str)
        # 2. 查询生命体征
        vital_signs = query_vital_signs(json_data['patient_info']['sick_id'], json_data['patient_info']['homepage_id'],
                                        db_source)
        doc1['b'] = vital_signs.get('血压') if vital_signs.get('血压') else ''
        doc1['t'] = vital_signs.get('体温') if vital_signs.get('体温') else ''
        doc1['p'] = vital_signs.get('脉搏') if vital_signs.get('脉搏') else ''
        doc1['r'] = vital_signs.get('呼吸') if vital_signs.get('呼吸') else ''

    json_data['doc1'] = json.dumps(doc1, default=str)
    json_data['patient_info'] = json.dumps(json_data['patient_info'], default=str)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    fileds, args = ','.join(json_data.keys()), str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.hbot_register_record ({fileds}) VALUES {args}"
    last_rowid = db.execute(insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("高压氧登记记录入库失败! ", insert_sql, str(args))
    del db


"""
查询登记记录 0=待执行 1=执行中 2=已完成/已取消
同时查询登记记录对应的当天的治疗记录的状态
"""


def query_register_record(json_data):
    query_type = json_data.get('query_type')
    key = json_data.get('key')
    if int(query_type) == 0:
        condition_sql = f"a.execution_status = {hbot_config.register_status['not_started']}"
    elif int(query_type) == 1:
        condition_sql = f"a.execution_status = {hbot_config.register_status['in_progress']}"
    elif int(query_type) == 2:
        condition_sql = f"a.execution_status >= {hbot_config.register_status['cancelled']}"
    else:
        raise Exception('参数错误, query_type = ', query_type, '(0=待执行 1=执行中 2=已完成/已取消)')

    if key:
        condition_sql = condition_sql + f" and (a.patient_id like '%{key}%' " \
                                        f"or JSON_CONTAINS(a.patient_info->'$.patient_name', '\"{key}\"') " \
                                        f"or JSON_CONTAINS(a.patient_info->'$.patient_dept', '\"{key}\"') " \
                                        f"or JSON_CONTAINS(a.patient_info->'$.diagnosis', '\"{key}\"') )"

    if json_data.get('start_date') and json_data.get('end_date'):
        condition_sql = condition_sql + f" and a.start_date between '{json_data.get('start_date')}' " \
                                        f"and '{json_data.get('end_date')}'"

    today_str = datetime.now().strftime('%Y-%m-%d')
    query_sql = f"select a.*, COALESCE( b.execution_status, 0) as today_status " \
                f"from nsyy_gyl.hbot_register_record a left join nsyy_gyl.hbot_treatment_record b " \
                f"on a.register_id = b.register_id and b.record_date = '{today_str}' where {condition_sql}"

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    data = db.query_all(query_sql)
    sorted_data = sorted(data, key=lambda x: (x['start_time'], x['id']))
    del db
    if sorted_data:
        for record in sorted_data:
            record.pop('medical_order_info')
            record.pop('doc1')
            record['patient_info'] = json.loads(record['patient_info']) if record.get('patient_info') else {}
            record['sign_info'] = json.loads(record['sign_info']) if record.get('sign_info') else {}

    return sorted_data


"""
更新登记记录开始时间
"""


def update_register_start_time(json_data):
    rid = json_data.get('id')
    start_time = json_data.get('start_time')
    if not start_time:
        raise Exception('更新开始时间，开始时间不能为空')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = f"update nsyy_gyl.hbot_register_record set start_time = '{start_time}' where id = {rid}"
    db.execute(update_sql, need_commit=True)
    del db


"""
查询治疗记录, 默认查询当天的治疗记录，还可以按照日期或者 住院号/门诊号 查询
query_type = 1 查询治疗记录
query_type = 2 查询知情同意书/仅查签名
"""


def query_treatment_record(json_data):
    register_id = json_data.get('register_id')
    query_type = json_data.get('query_type', 0)

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if int(query_type) == 1:
        query_sql = f"select * from nsyy_gyl.hbot_treatment_record WHERE register_id = '{register_id}'"
    elif int(query_type) == 2:
        query_sql = f"select comp_type, doc1, sign_info, patient_info " \
                    f"from nsyy_gyl.hbot_register_record WHERE register_id = '{register_id}'"
    elif int(query_type) == 3:
        query_sql = f"select sign_info from nsyy_gyl.hbot_register_record WHERE id = '{json_data['id']}' "
    elif int(query_type) == 4:
        query_sql = f"select sign_info from nsyy_gyl.hbot_treatment_record WHERE id = '{json_data['id']}' "
    else:
        raise Exception('参数错误, query_type = ', query_type, '(1=查询治疗记录 2=查询知情同意书&签名)')

    data = db.query_all(query_sql)
    if data:
        for record in data:
            record['record_info'] = json.loads(record['record_info']) if record.get('record_info') else {}
            record['sign_info'] = json.loads(record['sign_info']) if record.get('sign_info') else {}
            if record.get('doc1'):
                record['doc1'] = json.loads(record['doc1'])
            if record.get('patient_info'):
                record['patient_info'] = json.loads(record['patient_info'])
    if int(query_type) == 3 and not data[0].get('sign_info'):
        data[0]['sign_info'] = {"img1": hbot_config.sign_info.get(json_data.get('operator'), ""), "img2": "",
                                "img3": hbot_config.sign_info.get('刘春敏', ""), "img4": ""}
    if int(query_type) == 4 and not data[0].get('sign_info'):
        data[0]['sign_info'] = {"img5": hbot_config.sign_info.get(json_data.get('operator'), ""), "img6": ""}

    if int(query_type) == 2 and 'id' not in json_data:
        # 如果登记记录未录入生命体征，则查询，并更新登记记录
        doc1 = data[0].get('doc1')
        if not doc1.get('b') and not doc1.get('t'):
            patient_info = data[0].get('patient_info')
            db_source = "nshis" if int(data[0].get('comp_type')) == 12 else "kfhis"
            vital_signs = query_vital_signs(patient_info.get('sick_id'), patient_info.get('homepage_id'), db_source)
            if vital_signs:
                doc1['b'] = vital_signs.get('血压') if vital_signs.get('血压') else ''
                doc1['t'] = vital_signs.get('体温') if vital_signs.get('体温') else ''
                doc1['p'] = vital_signs.get('脉搏') if vital_signs.get('脉搏') else ''
                doc1['r'] = vital_signs.get('呼吸') if vital_signs.get('呼吸') else ''
                data[0]['doc1'] = doc1
                update_sql = f"update nsyy_gyl.hbot_register_record set doc1='{json.dumps(doc1)}' " \
                             f"where id={data[0].get('id')}"
                db.execute(update_sql, need_commit=True)
    del db
    return data


"""
更新登记信息
1. 签署执行同意书, 进行心理指导
2. 终止执行
3. 恢复已取消的登记记录
"""


def update_register_record(json_data):
    register_id = json_data.get('register_id')
    patient_id = json_data.get('patient_id')
    start_date = json_data.get('start_date')
    start_time = json_data.get('start_time')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 签署高压氧治疗知情同意书 & 进行高压氧患者入舱安全教育与心理指导
    doc1 = json_data.get('doc1')
    if doc1:
        # todo doc2 暂时没有意义，仅仅用来表示是否已经签署知情同意书
        set_sql = f"doc2 = '1', doc1 = '{json.dumps(doc1, default=str)}', operator = '{json_data.get('operator')}' "
        update_sql = f"update nsyy_gyl.hbot_register_record set {set_sql} where register_id = '{register_id}' "
        db.execute(update_sql, need_commit=True)
        write_new_treatment_record(register_id, patient_id, start_date, db)
        del db
        return

    # 恢复执行
    execution_status = json_data.get('execution_status')
    if execution_status and execution_status == hbot_config.register_status['in_progress']:
        query_sql = f"select * from nsyy_gyl.hbot_register_record where register_id = '{register_id}' "
        register_record = db.query_one(query_sql)
        if not register_record or register_record['execution_status'] == hbot_config.register_status['in_progress']:
            # 执行中的不需要恢复
            raise Exception('登记记录已处于执行中状态，不需要恢复')

        set_sql = ""
        start_date = json_data.get('start_date')
        if start_date:
            if datetime.strptime(start_date, '%Y-%m-%d').date() > datetime.now().date():
                set_sql += f"execution_status = {hbot_config.register_status['not_started']} "
            elif datetime.strptime(start_date, '%Y-%m-%d').date() == datetime.now().date():
                set_sql += f"execution_status = {hbot_config.register_status['in_progress']} "
            else:
                raise Exception('登记记录开始日期不能早于今天')
            set_sql += f", start_date = '{json_data.get('start_date')}' " if json_data.get('start_date') else ""

        set_sql += f", execution_days = {int(json_data.get('execution_days'))}" if json_data.get(
            'execution_days') else ""
        set_sql += f", start_time = '{json_data.get('start_time')}' " if json_data.get('start_time') else ""
        set_sql += f", execution_duration = {int(json_data.get('execution_duration'))}" \
            if json_data.get('execution_duration') else ""

        update_sql = f"update nsyy_gyl.hbot_register_record set {set_sql} where register_id = '{register_id}' "
        db.execute(update_sql, need_commit=True)
        write_new_treatment_record(register_id, patient_id, start_date, db)
        del db
        return

    # 终止执行
    if execution_status and execution_status == hbot_config.register_status['cancelled']:
        update_sql = f"update nsyy_gyl.hbot_register_record set execution_status = {hbot_config.register_status['cancelled']} " \
                     f"where register_id = '{register_id}' "
        db.execute(update_sql, need_commit=True)
        update_sql = f"update nsyy_gyl.hbot_treatment_record set execution_status = {hbot_config.treatment_record_status['cancel_all']} " \
                     f"where register_id = '{register_id}' and execution_status = {hbot_config.treatment_record_status['pending']} "
        db.execute(update_sql, need_commit=True)
        del db
        return


"""
更新治疗记录
"""


def update_treatment_record(json_data):
    tid = json_data.get('id')
    register_id = json_data.get('register_id')
    record_id = json_data.get('record_id')
    record_info = json_data.get('record_info')
    sign_info = json_data.get('sign_info')
    record_time = json_data.get('record_time')
    operator = json_data.get('operator')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.hbot_treatment_record where id = '{tid}' "
    treatment_record = db.query_one(query_sql)
    if not treatment_record:
        del db
        raise Exception("未找到该治疗记录！")

    # 更新治疗记录信息
    if record_info:
        set_info = f" record_info = '{json.dumps(record_info, default=str)}'"
        set_info += f", record_time = '{record_time}'" if record_time else ""
        update_sql = f"update nsyy_gyl.hbot_treatment_record set {set_info} where id = '{tid}' "
        db.execute(update_sql, need_commit=True)

    state = json_data.get('state')
    # 更新治疗记录状态
    if state:
        # 状态不变，不做任何修改
        if int(state) == int(treatment_record.get('execution_status')):
            del db
            return

        query_sql = f"select * from nsyy_gyl.hbot_register_record where register_id = '{register_id}'"
        register_record = db.query_one(query_sql)
        if int(state) == hbot_config.treatment_record_status['implement']:
            date_to_check = datetime.strptime(treatment_record.get('record_date'), '%Y-%m-%d')
            if date_to_check.date() > datetime.now().date():
                del db
                raise Exception('治疗时间还未到，不能提前执行')
            if int(treatment_record.get('execution_status')) >= hbot_config.treatment_record_status['cancel_this']:
                del db
                raise Exception('治疗记录已取消，无法再次执行')

            if int(register_record.get('execution_status')) >= hbot_config.register_status['cancelled']:
                del db
                raise Exception('本次治疗周期已被取消或已完成，如需继续治疗请重新登记')
            # 首次执行需要先签署心理指导/知情同意书
            if not register_record.get('sign_info'):
                del db
                raise Exception("更新HBOT治疗记录失败，未签署高压氧治疗知情同意书！")

        update_sql = f"update nsyy_gyl.hbot_treatment_record set execution_status = {state}, " \
                     f"operator = '{operator}' where id = '{tid}' "
        db.execute(update_sql, need_commit=True)

        # 本次执行完成，判断明天是否还需要执行
        if int(state) == hbot_config.treatment_record_status['cancel_all']:
            update_sql = f"update nsyy_gyl.hbot_register_record " \
                         f"set execution_status = {hbot_config.register_status['cancelled']} " \
                         f"where register_id = '{register_id}' "
            db.execute(update_sql, need_commit=True)
        else:
            tomorrow = datetime.strptime(treatment_record.get('record_date'), '%Y-%m-%d') + timedelta(days=1)
            last_day = datetime.strptime(register_record.get('start_date'), '%Y-%m-%d') + \
                       timedelta(days=int(register_record.get('execution_days')) - 1)
            if tomorrow.date() <= last_day.date():
                write_new_treatment_record(treatment_record.get('register_id'), treatment_record.get('patient_id'),
                                           tomorrow.strftime('%Y-%m-%d'), db)
            else:
                # 更新登录记录的状态
                update_sql = f"update nsyy_gyl.hbot_register_record set execution_status = {hbot_config.register_status['completed']} " \
                             f"where register_id = '{register_id}' "
                db.execute(update_sql, need_commit=True)
    del db


"""
更新签名信息
sign_type = 1 签署知情同意书 & 心理指导
sign_type = 2 治疗记录签名
"""


def update_sign_info(json_data):
    sign_id = json_data.get('sign_id')
    sign_type = json_data.get('sign_type')
    sign_info = json_data.get('sign_info')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    update_sql = ''
    if int(sign_type) == 1:
        # 登记记录签名
        update_sql = f"update nsyy_gyl.hbot_register_record set sign_info = '{json.dumps(sign_info, default=str)}' where id = {sign_id} "
    elif int(sign_type) == 2:
        # 治疗记录签名
        update_sql = f"update nsyy_gyl.hbot_treatment_record set sign_info = '{json.dumps(sign_info, default=str)}' where id = {sign_id} "
    else:
        raise Exception('未知的签名类型')
    db.execute(update_sql, need_commit=True)
    del db


"""
高压氧 扣款
高压氧坐97  躺145.5 急救单独开仓坐194+97  躺194+145.5

对应的扣费次数如下

高压氧坐  1
高压氧躺  1.5
急救单独开仓坐  3
急救单独开仓躺  3.5
"""


def hbot_charge(json_data):
    rid = json_data.get('rid')
    tid = json_data.get('tid')
    pay_num = json_data.get('pay_num')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.hbot_treatment_record where id = '{tid}' "
    treatment_record = db.query_one(query_sql)
    if not treatment_record:
        del db
        raise Exception("扣费失败，未找到治疗记录")
    if int(treatment_record.get('pay_status')) == 1:
        del db
        raise Exception("扣费失败：已付款，请勿重复操作")

    query_sql = f"select * from nsyy_gyl.hbot_register_record where id = '{rid}' "
    register_record = db.query_one(query_sql)
    if int(register_record.get('patient_type')) != 3:
        del db
        raise Exception("扣费失败：本系统暂时仅支持对住院患者进行扣款, 门诊患者请刷就诊卡。")

    patient_id, homepage_id, doc_advice_id, bill_dept_code, bill_people = '', '', '', '', ''
    if not register_record.get('medical_order_info'):
        # 如果不存在医嘱，查询患者信息（患者信息需要重新查，防止患者换科室）
        patient_info = query_patient_info(int(register_record.get('patient_type')),
                                          int(register_record.get('patient_id')),
                                          int(register_record.get('comp_type')))
        patient_id, homepage_id = patient_info.get('sick_id'), patient_info.get('homepage_id')
        bill_dept_code, bill_people = patient_info.get('patient_dept_code'), patient_info.get('doctor_name')
        doc_advice_id = 0
    else:
        medical_order_info = json.loads(register_record.get('medical_order_info'))
        patient_id, homepage_id = medical_order_info.get('patient_id'), medical_order_info.get('homepage_id')
        bill_dept_code, bill_people = medical_order_info.get('bill_dept_code'), medical_order_info.get('bill_people')
        doc_advice_id = medical_order_info.get('doc_advice_id')

    comp_id, executor, executor_code, execution_dept_code = 0, "刘春敏", "0392", "0421"
    if int(register_record.get('comp_type')) == 32:
        comp_id, executor, executor_code, execution_dept_code = 32, "崔世阳", "0408", "00049"
    pay_info = {
        "procedure": "瑞美血库费用", "comp_id": comp_id, "is_test": 1 if global_config.run_in_local else 0,
        # 0 为正式库 1 为测试库
        "病人id": patient_id, "主页id": homepage_id, "医嘱序号": doc_advice_id,
        "开单部门编码": bill_dept_code, "开单人": bill_people, "执行部门编码": execution_dept_code,
        "操作员编号": executor_code, "操作员姓名": executor, "data": [{"收费细目id": 18248, "数量": pay_num}]
    }
    param = f"""
                <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:hl7-org:v3">
                    <soapenv:Header> <soapenv:Body> <request> {json.dumps(pay_info, default=str)}
                    </request> </soapenv:Body> </soapenv:Header> </soapenv:Envelope>
            """
    response_data = ''
    try:
        if global_config.run_in_local:
            response = requests.post("http://192.168.124.53:6080/his_webservice", data=param)
        else:
            response = requests.post("http://192.168.3.12:6080/his_webservice", data=param)
        response_data = response.text
        print(datetime.now(), "高压氧扣费返回:", response_data, pay_info)

        start = response_data.find("<return>") + len("<return>")
        end = response_data.find("</return>")
        json_response = response_data[start:end].strip()
        data = json.loads(json_response)
        #  [{"状态": "0", "描述": "None", "his收费no": "YH095105", "收费细目id": "18248", "数量": "3.5"}]
        if data and data[0].get('状态') == '0':
            redis_client = redis.Redis(connection_pool=pool)
            # 尝试设置键，只有当键不存在时才设置成功, ex=600 表示过期时间 600 秒（10 分钟），nx=True 表示不存在时才设置
            if not redis_client.set(f"hbot:{rid}:{tid}", pay_num, ex=600, nx=True):
                raise Exception('扣费失败：当前患者今天的治疗，10分钟内已扣过一次费，请勿重复扣费')  # 已经在 10 分钟内执行过，不能重复执行

            update_sql = f"update nsyy_gyl.hbot_treatment_record " \
                         f"set pay_status = 1, pay_num = {pay_num}, pay_no = '{data[0].get('his收费no')}' " \
                         f"where id = '{tid}' "
            db.execute(update_sql, need_commit=True)
        else:
            if data:
                err_info = data[0].get('描述')
                if err_info.__contains__('没有找到患者信息'):
                    raise Exception("扣费失败：没有找到患者信息, 请确认患者是否已经出院")
                else:
                    raise Exception("扣费失败：", err_info)
            else:
                raise Exception("扣费失败：请联系技术人员处理！", data)
    except Exception as e:
        print(datetime.now(), f'高压氧扣费失败, pay_info', pay_info, " pay return : ", response_data, e)
        del db
        raise Exception("扣费失败：请联系技术人员处理！", e)
    del db


"""
定时任务
1. 如果到达执行时间，修改登记记录的状态
2. 刷新医嘱
"""


def hbot_run_everyday():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    states = (hbot_config.register_status['not_started'], hbot_config.register_status['in_progress'])
    query_sql = f"select * from nsyy_gyl.hbot_register_record where medical_order_status in {states}"
    register_records = db.query_all(query_sql)

    today = datetime.now().strftime('%Y-%m-%d')
    for register_record in register_records:
        # 更新医嘱 仅关注住院患者的医嘱状态
        if register_record.get('medical_order_status') == hbot_config.medical_order_status['unordered'] \
                and int(register_record.get('patient_type')) == 3:
            # 根据患者住院号，查询医嘱状态
            register_time = register_record.get('register_time').strftime('%Y-%m-%d')
            db_source = 'nshis' if int(register_record.get('comp_type')) == 12 else 'kfhis'
            medical_order_info = query_medical_order(register_record.get('patient_id'), register_time, db_source)
            if medical_order_info:
                update_sql = f"update nsyy_gyl.hbot_register_record " \
                             f"set medical_order_status = {hbot_config.medical_order_status['ordered']}, " \
                             f"medical_order_info = '{json.dumps(medical_order_info, default=str)}' " \
                             f"where id = {register_record.get('id')} "
                db.execute(update_sql, need_commit=True)

        if register_record['execution_status'] == hbot_config.register_status['not_started'] \
                and register_record['start_date'] == today:
            update_sql = f"update nsyy_gyl.hbot_register_record " \
                         f"set execution_status = {hbot_config.register_status['in_progress']} " \
                         f"where id = {register_record.get('id')} "
            db.execute(update_sql, need_commit=True)
    del db


def write_new_treatment_record(register_id, patient_id, record_date, db):
    query_sql = f"select * from nsyy_gyl.hbot_treatment_record where register_id = '{register_id}' " \
                f"and record_date = '{record_date}' and patient_id = '{patient_id}'"
    exist_record = db.query_one(query_sql)
    if exist_record:
        if exist_record['execution_status'] == hbot_config.treatment_record_status['pending']:
            return
        else:
            # 今天的已经创建了，创建明天的
            record_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d') + timedelta(days=1)
            record_date = record_date.strftime('%Y-%m-%d')

    query_sql = f"select * from nsyy_gyl.hbot_register_record where register_id = '{register_id}' " \
                f"and patient_id = '{patient_id}'"
    register_record = db.query_one(query_sql)
    if register_record['execution_status'] != hbot_config.register_status['in_progress']:
        return

    # 插入明天的执行记录
    treatment_record = {'register_id': register_id, 'record_id': datetime.now().strftime("%Y%m%d%H%M%S"),
                        'patient_id': patient_id, 'record_date': record_date,
                        'record_time': register_record.get('start_time'),
                        'execution_status': hbot_config.treatment_record_status['pending']}
    fileds = ','.join(treatment_record.keys())
    args = str(tuple(treatment_record.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.hbot_treatment_record ({fileds}) VALUES {args}"
    last_rowid = db.execute(insert_sql, need_commit=True)
    if last_rowid == -1:
        del db


"""
工作量统计
"""


def data_statistics(json_data):
    start_date = json_data.get('start_date')
    end_date = json_data.get('end_date')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"""
        select a.register_id, a.patient_id, a.execution_status, a.pay_status, a.pay_num, a.pay_no, 
        b.patient_info, b.comp_type from nsyy_gyl.hbot_treatment_record a join nsyy_gyl.hbot_register_record b 
        on a.register_id = b.register_id where a.record_date >= '{start_date}' and a.record_date <= '{end_date}' 
    """
    records = db.query_all(query_sql)
    del db
    for record in records:
        record['patient_info'] = json.loads(record['patient_info'])
        record['dept_name'] = record['patient_info'].get('patient_dept')

    data = []
    group_sorted = sorted(records, key=lambda x: x["dept_name"])
    for key, group in groupby(group_sorted, key=lambda x: x['dept_name']):
        group_list = list(group)
        num_of_people = sum(1 for item in group_list if item["pay_status"] == 1)
        amount_of_money = sum(
            item["pay_num"] * (97 if int(item["comp_type"]) == 12 else 92)
            for item in group_list
            if item["pay_status"] == 1
        )
        data.append({
            "dept_name": key,
            "num_of_people": num_of_people,
            "amount_of_money": amount_of_money
        })
    return data

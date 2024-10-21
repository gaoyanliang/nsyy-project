import uuid
import json
import requests
import redis

from datetime import datetime, timedelta
from gylmodules import global_config
from gylmodules.critical_value import cv_config
from gylmodules.hyperbaric_oxygen_therapy import hbot_config
from gylmodules.utils.db_utils import DbUtil


pool = redis.ConnectionPool(host=cv_config.CV_REDIS_HOST, port=cv_config.CV_REDIS_PORT,
                                        db=cv_config.CV_REDIS_DB, decode_responses=True)


def call_third_systems_obtain_data(type: str, param: dict):
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
            # 根据 sql 查询数据
            from tools import orcl_db_read
            try:
                data = orcl_db_read(param)
            except Exception as e:
                data = []
                print('orcl_db_read 查询数据失败：', param, e.__str__())
        else:
            print('call_third_systems_obtain_data 不支持 ', type)

    return data


"""
根据住院号和登记时间，查询病人高压氧医嘱信息
"""


def query_medical_order(patient_id, register_time):
    data = None
    medical_order_list = call_third_systems_obtain_data('orcl_db_read', {
        "type": "orcl_db_read",
        "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": "select a.* from 病人医嘱记录 a, 病案主页 b "
               f"where a.病人id=b.病人id and a.主页id=b.主页id and b.住院号='{patient_id}' "
               f"and a.开嘱时间 >= to_date('{register_time}', 'yyyy-mm-dd') "
               f"and a.医嘱内容 like '%高压氧%' and a.执行标记!='-1'"
    })
    if medical_order_list:
        redis_client = redis.Redis(connection_pool=pool)
        bill_dept_code = medical_order_list[0].get('开嘱科室ID')
        # dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, str(bill_dept_code))
        # dept_info = json.loads(dept_info) if dept_info else None
        # bill_dept_code = dept_info.get('dept_code') if dept_info else bill_dept_code

        execution_dept_code = medical_order_list[0].get('执行科室ID')
        # dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, str(execution_dept_code))
        # dept_info = json.loads(dept_info) if dept_info else None
        # execution_dept_code = dept_info.get('dept_code') if dept_info else execution_dept_code

        data = {
            "homepage_id": medical_order_list[0].get('主页ID'),
            "doc_advice_id": medical_order_list[0].get('ID'),
            "doc_advice_content": medical_order_list[0].get('医嘱内容'),
            "doc_advice_info": medical_order_list[0].get('医生嘱托'),
            "doc_advice_doc": medical_order_list[0].get('开嘱医生'),
            "start_time": medical_order_list[0].get('开始执行时间'),
            "patient_id": medical_order_list[0].get('病人ID'),
            "doc_advice_order_num": medical_order_list[0].get('序号'),
            "bill_dept_code": bill_dept_code,
            "execution_dept_code": execution_dept_code,
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


def query_patient_info(patient_type, patient_id):
    data = {}
    if int(patient_type) == 3:
        # 住院
        patient_infos = call_third_systems_obtain_data('orcl_db_read', {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": "select a.姓名,a.性别,a.年龄,a.住院号, bm.名称 科室, a.出院病床 床号,a.联系人电话, a.住院医师, a.主页ID, a.病人ID, zd.名称 诊断 "
                   "from 病案主页 a left join 部门表 bm on a.出院科室id=bm.id "
                   "left join (select distinct 病人ID, 主页ID, jb.名称 from 病人诊断记录 t "
                   "join 疾病编码目录 jb on t.疾病id = jb.id "
                   "where t.记录来源 = 3 and t.诊断次序 = 1 and t.诊断类型 = 2) zd on a.病人id=zd.病人id "
                   f"and a.主页id=zd.主页id where a.住院号='{patient_id}' and a.出院日期 is null "
        })
        if not patient_infos:
            raise Exception('未找到该住院号对应的患者信息，请仔细核对住院号是否正确')
        data = {
            "sick_id": patient_infos[0].get('病人ID'),
            "homepage_id": patient_infos[0].get('主页ID'),
            "doctor_name": patient_infos[0].get('住院医师'),
            "patient_name": patient_infos[0].get('姓名'),
            "patient_id": patient_id,
            "patient_sex": patient_infos[0].get('性别'),
            "patient_age": patient_infos[0].get('年龄'),
            "patient_dept": patient_infos[0].get('科室'),
            "patient_bed": patient_infos[0].get('床号'),
            "diagnosis": patient_infos[0].get('诊断'),
            "patient_phone": patient_infos[0].get('联系人电话'),
            "course_of_treatment": ""
        }
    elif int(patient_type) == 1:
        # 门诊
        patient_infos = call_third_systems_obtain_data('orcl_db_read', {
            "type": "orcl_db_read",
            "db_source": "nshis",
            "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
            "sql": f'select a.*, b.当前科室ID, b.当前床号, b.联系人电话 from 病人挂号记录 a left join 病人信息 b on a.病人id=b.病人id '
                   f"where ( b.就诊卡号 like '%{patient_id}%' or b.身份证号 like '%{patient_id}%' ) "
                   f" order by a.登记时间 desc "
        })
        if not patient_infos:
            raise Exception('未找到该住院号对应的患者信息，请仔细核对住院号是否正确')
        dept_name = patient_infos[0].get('当前科室ID')
        if int(dept_name) != 0:
            redis_client = redis.Redis(connection_pool=pool)
            dept_info = redis_client.hget(cv_config.DEPT_INFO_REDIS_KEY, str(dept_name))
            dept_info = json.loads(dept_info) if dept_info else str(dept_name) + '=未知科室'
            dept_name = dept_info.get('dept_name') if type(dept_info) == dict else dept_info
        data = {
            "sick_id": patient_infos[0].get('病人ID'),
            "homepage_id": "0",
            "doctor_name": patient_infos[0].get('执行人'),
            "patient_name": patient_infos[0].get('姓名'),
            "patient_id": patient_id,
            "patient_sex": patient_infos[0].get('性别'),
            "patient_age": patient_infos[0].get('年龄'),
            "patient_dept": dept_name,
            "patient_bed": patient_infos[0].get('当前床号'),
            "diagnosis": "",
            "patient_phone": patient_infos[0].get('联系人电话'),
            "course_of_treatment": ""
        }
        if data['patient_age']:
            data['patient_age'] = data['patient_age'].replace('岁', '')
    return data


"""
查询生命体征
"""


def query_vital_signs(sick_id, homepage_id):
    data = {}
    vital_signs = call_third_systems_obtain_data('orcl_db_read', {
        "type": "orcl_db_read",
        "db_source": "nshis",
        "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
        "sql": f"""
            select PATIENT_ID, VISIT_ID, TIME_POINT, THEME_CODE, ITEM_NAME, ITEM_VALUE
            from (select t.patient_id, t.visit_id, t.time_point, 
            rank() over(partition by t.patient_id, t.visit_id order by t.time_point) sn,
                   t.theme_code, t2.item_name, t2.item_value from DOCS_NORMAL_REPORT_REC@YDHLCIS t
              join DOCS_NORMAL_REPORT_DETAIL_REC@YDHLCIS t2 on t.report_id = t2.report_id
               and t2.item_name in ('呼吸', '体温', '脉搏', '血压')
               and t2.enabled_value = 'Y' and t.enabled_value = 'Y'
               and t.theme_code = '一般护理记录单(二)'
             where patient_id = '{sick_id}' and visit_id = '{homepage_id}') where sn = 1
        """
    })
    if not vital_signs:
        return data

    for d in vital_signs:
        data[d['ITEM_NAME']] = d['ITEM_VALUE']
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
        # 1. 根据住院号查询是否存在医嘱
        medical_order_info = query_medical_order(patient_id, datetime.today().strftime('%Y-%m-%d'))
        if medical_order_info:
            json_data['medical_order_status'] = hbot_config.medical_order_status['ordered']
            json_data['medical_order_info'] = json.dumps(medical_order_info, default=str)

        # 查询生命体征
        if not json_data.get('patient_info'):
            raise Exception('缺少病人信息 patient_info = ', json_data.get('patient_info'))
        vital_signs = query_vital_signs(json_data['patient_info']['sick_id'], json_data['patient_info']['homepage_id'])
        doc1['b'] = vital_signs.get('血压') if vital_signs.get('血压') else ''
        doc1['t'] = vital_signs.get('体温') if vital_signs.get('体温') else ''
        doc1['p'] = vital_signs.get('脉搏') if vital_signs.get('脉搏') else ''
        doc1['r'] = vital_signs.get('呼吸') if vital_signs.get('呼吸') else ''

    json_data['doc1'] = json.dumps(doc1, default=str)
    json_data['patient_info'] = json.dumps(json_data['patient_info'], default=str)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
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


def query_register_record(query_type, key):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
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

    today_str = datetime.now().strftime('%Y-%m-%d')
    query_sql = f"select a.*, COALESCE( b.execution_status, 0) as today_status " \
                f"from nsyy_gyl.hbot_register_record a left join nsyy_gyl.hbot_treatment_record b " \
                f"on a.register_id = b.register_id and b.record_date = '{today_str}' where {condition_sql}"
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
        query_sql = f"select doc1, sign_info from nsyy_gyl.hbot_register_record WHERE register_id = '{register_id}'"
        if json_data.get('id'):
            query_sql = f"select sign_info from nsyy_gyl.hbot_register_record WHERE id = '{json_data['id']}' "
    else:
        raise Exception('参数错误, query_type = ', query_type, '(1=查询治疗记录 2=查询知情同意书&签名)')

    data = db.query_all(query_sql)
    del db

    if data:
        for record in data:
            record['record_info'] = json.loads(record['record_info']) if record.get('record_info') else {}
            record['sign_info'] = json.loads(record['sign_info']) if record.get('sign_info') else {}
            record['doc1'] = json.loads(record['doc1']) if record.get('doc1') else {}
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
        set_sql = f"doc2 = '1', doc1 = '{json.dumps(doc1, default=str)}' "  # todo doc2 暂时没有意义，仅仅用来表示是否已经签署知情同意书
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

        update_sql = f"update nsyy_gyl.hbot_register_record set {set_sql} " \
                     f"where register_id = '{register_id}' "
        db.execute(update_sql, need_commit=True)
        write_new_treatment_record(register_id, patient_id, start_date, db)
        del db
        return

    # 终止执行
    if execution_status and execution_status == hbot_config.register_status['cancelled']:
        update_sql = f"update nsyy_gyl.hbot_register_record set execution_status = {hbot_config.register_status['cancelled']} " \
                     f"where register_id = '{register_id}' "
        db.execute(update_sql, need_commit=True)
        update_sql = f"update nsyy_gyl.hbot_treatment_record set execution_status = {hbot_config.treatment_record_status['cancel_this']} " \
                     f"where register_id = '{register_id}' and execution_status = {hbot_config.treatment_record_status['pending']} "
        db.execute(update_sql, need_commit=True)
        del db
        return


"""
更新治疗记录
"""


def update_treatment_record(json_data):
    register_id = json_data.get('register_id')
    record_id = json_data.get('record_id')
    record_info = json_data.get('record_info')
    sign_info = json_data.get('sign_info')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.hbot_treatment_record " \
                f"where register_id = '{register_id}' and record_id = '{record_id}'"
    treatment_record = db.query_one(query_sql)
    if not treatment_record:
        del db
        raise Exception("未找到该治疗记录！")

    # 更新治疗记录信息
    if record_info:
        set_info = f" record_info = '{json.dumps(record_info, default=str)}'"
        update_sql = f"update nsyy_gyl.hbot_treatment_record set {set_info} where id = '{treatment_record.get('id')}' "
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

        update_sql = f"update nsyy_gyl.hbot_treatment_record set execution_status = {state}  " \
                     f"where register_id = '{register_id}' and record_id = '{record_id}' "
        db.execute(update_sql, need_commit=True)

        # 本次执行完成，判断明天是否还需要执行
        if int(state) == hbot_config.treatment_record_status['cancel_all']:
            update_sql = f"update nsyy_gyl.hbot_register_record " \
                         f"set execution_status = {hbot_config.register_status['cancelled']} " \
                         f"where register_id = '{register_id}' "
            db.execute(update_sql, need_commit=True)
        else:
            tomorrow = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d') + timedelta(days=1)
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
        raise Exception("未找到治疗记录")
    if int(treatment_record.get('pay_status')) == 1:
        del db
        raise Exception("已付款，请勿重复操作")

    query_sql = f"select * from nsyy_gyl.hbot_register_record where id = '{rid}' "
    register_record = db.query_one(query_sql)
    if not register_record or not register_record.get('medical_order_info'):
        del db
        raise Exception("未找到该治疗记录的医嘱信息， 请联系医生先开医嘱")

    medical_order_info = json.loads(register_record.get('medical_order_info'))
    pay_info = {
        "procedure": "瑞美血库费用",
        "is_test": 1 if global_config.run_in_local else 0,  # 0 为正式库 1 为测试库
        "病人id": medical_order_info.get('patient_id'),
        "主页id": medical_order_info.get('homepage_id'),
        "医嘱序号": medical_order_info.get('doc_advice_id'),
        "开单部门编码": medical_order_info.get('bill_dept_code'),
        "开单人": medical_order_info.get('bill_people'),
        "执行部门编码": medical_order_info.get('execution_dept_code'),
        "操作员编号": "0392",
        "操作员姓名": "刘春敏",
        "data": [{"收费细目id": 18248, "数量": pay_num}]
    }
    # 构造 SOAP 请求
    param = f"""
                <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:hl7-org:v3">
                    <soapenv:Header>
                        <soapenv:Body>
                            <request>
                            {json.dumps(pay_info, default=str)}
                            </request>
                        </soapenv:Body>
                    </soapenv:Header>
                </soapenv:Envelope>
            """
    response_data = ''
    try:
        if global_config.run_in_local:
            response = requests.post("http://192.168.124.53:6080/his_webservice", data=param)
        else:
            response = requests.post("http://192.168.3.12:6080/his_webservice", data=param)
        response_data = response.text
        print("高压氧扣费返回:", response_data)

        start = response_data.find("<return>") + len("<return>")
        end = response_data.find("</return>")
        json_response = response_data[start:end].strip()
        data = json.loads(json_response)
        #  [{"状态": "0", "描述": "None", "his收费no": "YH095105", "收费细目id": "18248", "数量": "3.5"}]
        if data and data[0].get('状态') == '0':
            update_sql = f"update nsyy_gyl.hbot_treatment_record set pay_status = 1, pay_num = {pay_num}  " \
                         f"where id = '{tid}' "
            db.execute(update_sql, need_commit=True)
        else:
            del db
            raise Exception("高压氧扣费失败，请重试！", data)
    except Exception as e:
        del db
        print(datetime.now(), f'高压氧扣费失败, pay_info', pay_info, " pay return : ", response_data)
        raise Exception("高压氧扣费失败，请重试！", e)
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
            medical_order_info = query_medical_order(register_record.get('patient_id'), register_time)
            if medical_order_info or global_config.run_in_local:
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

    query_sql = f"select * from nsyy_gyl.hbot_register_record where register_id = '{register_id}' " \
                f"and patient_id = '{patient_id}'"
    register_record = db.query_one(query_sql)
    if register_record['execution_status'] !=  hbot_config.register_status['in_progress']:
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
        raise Exception("高压氧治疗记录入库失败! ", insert_sql, str(args))

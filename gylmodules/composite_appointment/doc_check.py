import json
import requests

from itertools import groupby
from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

"""
由于门诊医生的信息维护是在 HIS 中进行的，信息的改动不会自动同步到 综合预约系统中。
一下方法可以查询 HIS 中门诊医生的信息，然后和综合预约系统中维护的医生信息进行比对，同时更新不一致的信息
"""

def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", json=param)
            data = response.text
            data = json.loads(data)
            data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    return data


sql = """
select t.号类,
       t.号码,
       t.科室id,
       bm.名称    部门名称,
       t.医生id,
       t.医生姓名,
       ry.别名    真实姓名,
       t2.名称    挂号级别,
       t3.现价,
       t.项目id
  from 挂号安排 t
  join 收费项目目录 t2
    on t.项目id = t2.id
  join 收费价目 t3
    on t.项目id = t3.收费细目id
   and (t3.终止日期 is null or t3.终止日期 > sysdate)
  join 部门表 bm
    on t.科室id = bm.id
  left join 人员表 ry
    on t.医生ID = ry.id
 where (t.停用日期 is null or t.停用日期 > sysdate)
   and t2.名称 != '免费号'
   and t.医生id is not null
"""

param = {
    "type": "orcl_db_read",
    "db_source": "nshis",
    "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC",
    "sql": sql
}

data = call_third_systems_obtain_data('int_api', 'orcl_db_read', param)

# for d in data:
#     print(d)


doc_data = {}

group_sorted = sorted(data, key=lambda x: x["医生姓名"])
for key, group in groupby(group_sorted, key=lambda x: x['医生姓名']):
    group_list = list(group)
    doc_data[key] = group_list
    # print(group_list)

# 如果同一个医生，科室一样，挂号级别一样，打印日志
# 如果同一个医生，科室一样，挂号级别不一样，仅保留现价最高的那条记录
result = []
for doctor, records in doc_data.items():
    grouped = {}
    for record in records:
        key = (record['医生ID'], record['科室ID'])
        if key in grouped and grouped[key]['挂号级别'] == record['挂号级别']:
            print(
                f"医生 {record['医生姓名']} 在科室 {record['科室ID']} 存在相同挂号级别的记录：{record['挂号级别']}")
            continue
        elif key in grouped:
            if record['现价'] > grouped[key]['现价']:
                grouped[key] = record
        else:
            grouped[key] = record
    result.extend(grouped.values())

db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
# db = DbUtil("192.168.3.12", "gyl", "123456", "nsyy_gyl")

doc_in_db_list = db.query_all("select * from nsyy_gyl.appt_doctor")
doc_in_db_dict = {}
doc_in_db_sorted = sorted(doc_in_db_list, key=lambda x: x["his_name"])
for key, group in groupby(doc_in_db_sorted, key=lambda x: x['his_name']):
    doc_in_db_dict[key] = list(group)

result_sorted = sorted(result, key=lambda x: x["医生姓名"])
for key, group in groupby(result_sorted, key=lambda x: x['医生姓名']):
    group_list = list(group)
    doc_in_db = doc_in_db_dict.get(key)
    if not doc_in_db:
        print(f"医生 {key} 在数据库中不存在，请先添加医生信息", group_list)
        insert_sql = f"""
                insert into nsyy_gyl.appt_doctor(name, his_name, no, career, fee, appointment_id, dept_id, dept_name) 
                values ('{group_list[0].get('真实姓名')}', '{group_list[0].get('医生姓名')}', {group_list[0].get('医生ID')}, 
                '{group_list[0].get('挂号级别')}', '{group_list[0].get('现价')}', '{group_list[0].get('号码')}', 
                {group_list[0].get('科室ID')}, '{group_list[0].get('部门名称')}')
                """

        # todo 注释
        # db.execute(insert_sql, need_commit=True)
        print()
        continue

    if len(group_list) == 1 and len(doc_in_db) == 1:
        if int(group_list[0].get('号码')) != int(doc_in_db[0].get('appointment_id')) or \
                float(group_list[0].get('科室ID')) != float(doc_in_db[0].get('dept_id')) or \
                float(group_list[0].get('现价')) != float(doc_in_db[0].get('fee')):
            update_sql = f"""
                        update nsyy_gyl.appt_doctor set 
                          dept_id = {group_list[0].get('科室ID')}, dept_name = '{group_list[0].get('部门名称')}',
                          no = {group_list[0].get('医生ID')}, name = '{group_list[0].get('真实姓名')}',
                          career = '{group_list[0].get('挂号级别')}', fee = '{group_list[0].get('现价')}',
                          appointment_id = '{group_list[0].get('号码')}' where id = {doc_in_db[0].get('id')}
                        """

            # todo 注释
            # db.execute(update_sql, need_commit=True)
            print("===> 更新 ", key, group_list)
            print()
    elif len(group_list) >= len(doc_in_db):
        # print(f"医生：{key} 在数据库和新数据中存在多个记录，进一步检查科室")
        new_data_by_dept = {item['科室ID']: item for item in group_list}
        db_data_by_dept = {item['dept_id']: item for item in doc_in_db}

        for dept_id, new_data in new_data_by_dept.items():
            if dept_id in db_data_by_dept:
                db_data = db_data_by_dept[dept_id]
                if (int(new_data['号码']) != int(db_data['appointment_id']) or
                        float(new_data['现价']) != float(db_data['fee'])):
                    update_sql = f"""
                          UPDATE nsyy_gyl.appt_doctor SET 
                            dept_id = {new_data['科室ID']}, dept_name = '{new_data['部门名称']}',
                            no = {new_data['医生ID']}, name = '{new_data['真实姓名']}',
                            career = '{new_data['挂号级别']}', fee = '{new_data['现价']}',
                            appointment_id = '{new_data['号码']}' 
                          WHERE id = {db_data['id']}
                      """

                    # todo 注释
                    # db.execute(update_sql, need_commit=True)
                    print("---> 更新 ", key, new_data)
            else:
                print(f"---> 医生 {key} 的科室 {dept_id} 在数据库中不存在，请检查")
                print(group_list)
                print(doc_in_db)

        print()
    else:
        print("+++> 数据库中存在多余数据", key)
        print(group_list)
        print(doc_in_db)

del db

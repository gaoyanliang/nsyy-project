import json
import requests
import time
import concurrent.futures
from collections import defaultdict

import pandas as pd

from datetime import datetime, timedelta
from gylmodules import global_config


def call_third_systems_obtain_data(type: str, sql: str, db_source: str):
    param = {"type": type, "db_source": db_source, "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql}
    data = []
    if global_config.run_in_local:
        try:
            # 发送 POST 请求，将字符串数据传递给 data 参数
            # response = requests.post(f"http://192.168.3.12:6080/int_api", json=param)
            response = requests.post("http://192.168.124.53:6080/int_api", json=param, timeout=100)
            data = json.loads(response.text)
            data = data.get('data')
        except Exception as e:
            data = []
            print(datetime.now(), '调用第三方系统方法失败：type = orcl_db_read ' + ' param = ' + str(param) + "   " + e.__str__())
    else:
        # 根据住院号/门诊号查询 病人id 主页id
        from tools import orcl_db_read
        try:
            data = orcl_db_read(param)
        except Exception as e:
            data = []
            print(datetime.now(), '调用第三方系统方法失败：type = orcl_db_read ' + ' param = ' + str(param) + "   " + e.__str__())

    return data


def call_new_his(sql: str):
    param = {"key": "o4YSo4nmde9HbeUPWY_FTp38mB1c", "sys": "newzt", "sql": sql}

    query_oracle_url = "http://127.0.0.1:6080/oracle_sql"
    if global_config.run_in_local:
        query_oracle_url = "http://192.168.124.53:6080/oracle_sql"

    data = []
    try:
        response = requests.post(query_oracle_url, timeout=100, json=param)
        data = json.loads(response.text)
        data = data.get('data')
    except Exception as e:
        print(datetime.now(), '高压氧报表 调用新 HIS 查询数据失败：' + str(param) + e.__str__())

    return data


def sort_departments(departments):
    # Dictionary to convert Chinese numerals to Arabic
    chinese_to_arabic = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }

    def get_number_from_name(dept_name):
        words = dept_name.split()
        for word in words:
            for char in word:
                if char in chinese_to_arabic:
                    return chinese_to_arabic[char]
        # If no Chinese numeral found, try to find an Arabic number
        nums = [int(s) for s in dept_name.split() if s.isdigit()]
        return nums[0] if nums else 0

    # Custom sorting function
    def sort_key(dept):
        dept_name = dept['name']

        if '神经内科' in dept_name or '神内' in dept_name:
            return (0, get_number_from_name(dept_name))
        elif '康复院区' in dept_name:
            return (1, 0)
        elif '神经外科' in dept_name or '神外' in dept_name:
            return (2, get_number_from_name(dept_name))
        elif '烧伤科' in dept_name:
            return (3, get_number_from_name(dept_name))
        elif '肿瘤科' in dept_name:
            return (4, get_number_from_name(dept_name))
        elif '心血管内科' in dept_name:
            return (5, get_number_from_name(dept_name))
        elif '门诊' in dept_name:
            return (7, 0)  # Outpatient clinic
        elif dept_name == '总计':
            return (8, 0)  # Outpatient clinic
        else:
            return (6, dept_name)  # Other departments

    # Sort departments using the custom key
    sorted_depts = sorted(departments, key=sort_key)

    return sorted_depts


def get_next_day(end_date_str):
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    next_day = end_date + timedelta(days=1)
    return next_day.strftime('%Y-%m-%d')


def query_report(start_date, end_date):
    start_time = time.time()
    end_date = get_next_day(end_date)
    sql_zongyuan = f"""
        SELECT to_char(fashengrq,'yyyy-mm-dd') AS 计费日期, jifeiksmc AS 计费科室, bingrenid AS 病人ID,
        jiesuanje AS 结算金额 FROM df_jj_zhuyuan.zy_feiyong1
        WHERE jifeirq BETWEEN DATE '{start_date}' AND DATE'{end_date}' AND zhixingks = 281 
    """
    sql_kangfu = f"""
        SELECT to_char(发生时间, 'yyyy-mm-dd') as 计费日期, '康复院区' as 计费科室, 病人ID, 实收金额 as 结算金额 
        FROM 住院费用记录 WHERE 发生时间 BETWEEN TO_DATE('{start_date}', 'yyyy-mm-dd') 
        AND TO_DATE('{end_date}', 'yyyy-mm-dd') AND 执行部门ID = 342 
    """

    sql_menzhen = f"""
        SELECT to_char(COALESCE(t.zhixingrq, t1.shoufeirq2), 'yyyy-mm-dd') 计费日期,
               t.bingrenxm 姓名, t.kaidanksmc 开单科室名称,
               t.kaidanysxm 开单人, t.zhixingrxm 执行人姓名, 
               t.zhixingksmc 执行科室名称, t1.xiangmumc 项目名称, t1.shuliang 数量, t1.jiesuanje 结算金额, t.bingrenid 病人ID 
          FROM df_jj_menzhen.mz_feiyong1 t JOIN df_jj_menzhen.mz_feiyong2 t1 ON t.feiyongid = t1.feiyongid
          LEFT JOIN df_jj_menzhen.mz_shoufei t2 ON t.shoufeiid = t2.shoufeiid
         WHERE t.zhixingks = '281'
           and COALESCE(t.zhixingrq, t1.shoufeirq2) >= to_date('{start_date}', 'yyyy-mm-dd') and
         COALESCE(t.zhixingrq, t1.shoufeirq2) < to_date('{end_date}', 'yyyy-mm-dd') + 1
         order by t.bingrenxm, t.zhixingrq
        """

    # 并行查询
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_zongyuan = executor.submit(call_new_his, sql_zongyuan)
        future_kangfu = executor.submit(call_third_systems_obtain_data, 'orcl_db_read', sql_kangfu, "kfhis")
        future_menzhen = executor.submit(query_menzhen, sql_menzhen)

        try:
            zongyuan_data = future_zongyuan.result()
            kangfu_data = future_kangfu.result()
            menzhen_data = future_menzhen.result()
        except Exception as e:
            print(f"费用查询失败: {e}")
            # 可以在这里执行额外的清理操作，或者重新抛出异常

    zongyuan_new_data = []
    for d in zongyuan_data:
        if datetime.strptime(d.get('计费日期'), '%Y-%m-%d') < datetime.strptime(start_date, '%Y-%m-%d'):
            continue
        zongyuan_new_data.append(d)
    zongyuan_data = zongyuan_new_data
    print('查询耗时：', time.time() - start_time, '数量: ', len(kangfu_data), len(zongyuan_data))

    zongyuan_data = zongyuan_data if zongyuan_data is not None else []
    kangfu_data = kangfu_data if kangfu_data is not None else []
    all_data = zongyuan_data + kangfu_data
    if menzhen_data:
        for d in menzhen_data:
            all_data.append({
                '院区': '总院',
                '计费日期': d[0],
                '姓名': d[1],
                '住院号': "",
                '病人ID': d[9],
                '病人住院ID': "",
                '科室名称': d[2],
                '病区名称': d[2],
                '主治医生姓名': d[3],
                '计费人姓名': d[4],
                '计费科室': '门诊',
                '计费科室名称': '门诊',
                '执行科室名称': d[5],
                '项目名称': d[6],
                '数量': float(d[7]),
                '结算金额': float(d[8])
            })
    daily_stats = defaultdict(lambda: defaultdict(lambda: {'revenue': 0, 'patients': set()}))
    people_set = set()
    for record in all_data:
        people_set.add(record['病人ID'])
        date, department = record['计费日期'], record['计费科室']
        patient_id, amount = record['病人ID'], record['结算金额']

        daily_stats[department][date]['revenue'] += amount
        if patient_id not in daily_stats[department][date]['patients']:
            patient_charges = [r['结算金额'] for r in all_data
                               if
                               r['计费日期'] == date and r['计费科室'] == department and r['病人ID'] == patient_id]
            if sum(patient_charges) != 0:
                daily_stats[department][date]['patients'].add(patient_id)

    # Convert results to a more readable format
    people_total, price_total, total_people, total_price = [], [], {}, {}
    for departments, daily in daily_stats.items():
        people, price = {}, {}
        for date, data in daily.items():
            people[date] = len(data['patients'])
            price[date] = data['revenue']
            total_people[date] = len(data['patients']) + total_people.get(date, 0)
            total_price[date] = data['revenue'] + total_price.get(date, 0.0)
        people_total.append({"name": departments, **people})
        price_total.append({"name": departments, **price})


    total = {}
    t_people = 0
    t_price = 0.0
    for k, v in total_people.items():
        t_people += v
        total[k] = {'日期': k, '人数': v}

    for k, v in total_price.items():
        t_price += v
        total[k] = {"工作量": v, **total[k]}
    total = sorted(total.values(), key=lambda x: x['日期'])
    total.append({'日期': "汇总", '人数': t_people, '工作量': t_price})
    total.append({'日期': "人数汇总", '人数': len(people_set), '工作量': t_price})

    print(datetime.now(), '总耗时：', time.time() - start_time, start_date, end_date)
    return total, all_data


def query_menzhen(sql):
    results = []
    try:
        import psycopg2
        conn = psycopg2.connect(dbname="df_his", user="ogg", password="nyogg@2024", host="192.168.8.57", port="6000")
        cur = conn.cursor()
        cur.execute(sql)
        results = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print(datetime.now(), '高压氧门诊费用记录查询失败', e)
        results = []
    return results


def write_to_excel_with_sheets(data_sheets, file_name):
    from openpyxl import Workbook
    """
    将多组数据写入 Excel 文件的不同 Sheet 中。

    :param data_sheets: 数据列表，每个元素是一个字典，包含 "sheet_name" 和 "data" 信息
                        示例：[{"sheet_name": "Sheet1", "data": [...]}, {...}]
    :param file_name: 保存的 Excel 文件名
    """
    # 创建一个新的工作簿
    workbook = Workbook()

    # 遍历每个数据组，写入到对应的 Sheet 中
    for i, sheet_info in enumerate(data_sheets):
        sheet_name = sheet_info["sheet_name"]
        data = sheet_info["data"]
        column_order = sheet_info.get("column_order", [])

        # 创建新 Sheet（第一个 Sheet 保留为默认激活的 Sheet）
        if i == 0:
            sheet = workbook.active
            sheet.title = sheet_name
        else:
            sheet = workbook.create_sheet(title=sheet_name)

        # 写入表头
        if column_order:
            sheet.append(column_order)

        # 写入数据
        for row in data:
            sheet.append([row.get(col, '') for col in column_order])

    # 保存文件
    workbook.save(file_name)
    print(f"数据已保存到 {file_name}")


# query_report('2025-01-01', '2025-01-31')
ret_total, all_data = query_report('2025-02-01', '2025-02-28')


data_sheets = [
    {"sheet_name": "费用总计", "data": ret_total, "column_order": ["日期", "人数", "工作量"]},
    {"sheet_name": "治疗列表", "data": all_data, "column_order": ["计费日期", "病人ID", "计费科室", "结算金额"]},
]

# write_to_excel_with_sheets(data_sheets, '一月数据汇总.xlsx')



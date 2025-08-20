import json
import logging

import requests
import time
import concurrent.futures
import psycopg2
from collections import defaultdict

from datetime import datetime, timedelta
from gylmodules import global_config

DB_CONFIG = {
    "dbname": "df_his",
    "user": "ogg",
    "password": "nyogg@2024",
    "host": "192.168.8.57",
    "port": "6000"
}

logger = logging.getLogger(__name__)


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
            logger.error(f'高压氧查询失败: param={param}, e = {e.__str__()}')
    else:
        # 根据住院号/门诊号查询 病人id 主页id
        from tools import orcl_db_read
        try:
            data = orcl_db_read(param)
        except Exception as e:
            data = []
            logger.error(f'高压氧查询失败: param={param}, e = {e.__str__()}')

    return data


def sort_departments(departments):
    # 常量定义提高可读性
    SPECIAL_CATEGORIES = {
        '神经内科': {'keys': ['神经内科', '神内'], 'priority': 0},
        '康复院区': {'keys': ['康复院区'], 'priority': 1},
        '神经外科': {'keys': ['神经外科', '神外'], 'priority': 2},
        '烧伤科': {'keys': ['烧伤科'], 'priority': 3},
        '肿瘤科': {'keys': ['肿瘤科'], 'priority': 4},
        '心血管内科': {'keys': ['心血管内科'], 'priority': 5},
        '门诊': {'keys': ['门诊'], 'priority': 7},
        '总计': {'keys': ['总计'], 'priority': 8}
    }

    CHINESE_NUM_MAP = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }

    def parse_chinese_number(text):
        """解析中文数字字符串为阿拉伯数字"""
        result, temp = 0, 0
        for char in text:
            value = CHINESE_NUM_MAP.get(char, 0)
            if value >= 10:  # 处理单位字符
                result += temp * value
                temp = 0
            else:
                temp = temp * 10 + value
        return result + temp

    def extract_number(dept_name):
        """从科室名称中提取数字（支持中文数字和阿拉伯数字）"""
        import re
        # 同时匹配中文数字和阿拉伯数字
        match = re.search(r'(\d+|[一二三四五六七八九十]+)', dept_name)
        if not match:
            return 0  # 默认值

        num_str = match.group()
        if num_str.isdigit():
            return int(num_str)

        # 处理中文数字
        try:
            return parse_chinese_number(num_str)
        except:
            return 0

    def get_category_priority(dept_name):
        """获取科室分类优先级"""
        for category in SPECIAL_CATEGORIES.values():
            if any(key in dept_name for key in category['keys']):
                return (category['priority'], extract_number(dept_name))
        # 默认分类（其他科室按名称排序）
        return (6, dept_name)

    # 执行排序（保证稳定性）
    return sorted(departments,
                  key=lambda x: get_category_priority(x['name']),
                  reverse=False
                  )


def query_report(start_date, end_date):
    start_time = time.time()
    end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    # SQL 查询（使用 f-string 方式）
    sql_queries = {
        "zongyuan": f"""
            SELECT to_char(fashengrq, 'yyyy-mm-dd') AS 计费日期, jifeiksmc AS 计费科室, bingrenid AS 病人ID, 
                   jiesuanje AS 结算金额 
            FROM df_jj_zhuyuan.zy_feiyong1 
            WHERE jifeirq BETWEEN '{start_date}' AND '{end_date}' AND zhixingks = '281'
        """,
        "kangfu": f"""
            SELECT to_char(发生时间, 'yyyy-mm-dd') AS 计费日期, '康复院区' AS 计费科室, 病人ID, 实收金额 AS 结算金额
            FROM 住院费用记录 WHERE 发生时间 BETWEEN DATE '{start_date}' AND DATE '{end_date}' AND 执行部门ID = 342 
        """,
        "menzhen": f"""
            SELECT to_char(COALESCE(t.zhixingrq, t1.shoufeirq2), 'yyyy-mm-dd') AS 计费日期, 
                   t.bingrenxm AS 姓名, t.kaidanksmc AS 开单科室名称,
                   t.kaidanysxm AS 开单人, t.zhixingrxm AS 执行人姓名, 
                   t.zhixingksmc AS 执行科室名称, t1.xiangmumc AS 项目名称, 
                   t1.shuliang AS 数量, t1.jiesuanje AS 结算金额, t.bingrenid AS 病人ID 
            FROM df_jj_menzhen.mz_feiyong1 t
            JOIN df_jj_menzhen.mz_feiyong2 t1 ON t.feiyongid = t1.feiyongid
            WHERE t.zhixingks = '281'
              AND COALESCE(t.zhixingrq, t1.shoufeirq2) BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY t.bingrenxm, t.zhixingrq
        """
    }

    # 并行查询
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_zongyuan = executor.submit(safe_postgres_query, sql_queries["zongyuan"])
        future_menzhen = executor.submit(safe_postgres_query, sql_queries["menzhen"])
        future_kangfu = executor.submit(call_third_systems_obtain_data, 'orcl_db_read', sql_queries["kangfu"], "kfhis")

        try:
            zongyuan_data = future_zongyuan.result()
            menzhen_data = future_menzhen.result()
            kangfu_data = future_kangfu.result()
        except Exception as e:
            logger.error(f'高压氧费用查询失败: {e}')
            return [], []  # 查询失败时返回空数据
            # 可以在这里执行额外的清理操作，或者重新抛出异常

    def convert_data(todo_data):
        from decimal import Decimal
        return [
            {
                '病人ID': row[2],
                '结算金额': float(row[3]) if isinstance(row[3], Decimal) else row[3],
                '计费日期': row[0],
                '计费科室': row[1]
            }
            for row in todo_data if datetime.strptime(row[0], '%Y-%m-%d') >= datetime.strptime(start_date, '%Y-%m-%d')
        ]

    zongyuan_data = convert_data(zongyuan_data) if zongyuan_data else []
    zongyuan_new_data = []
    for d in zongyuan_data:
        if datetime.strptime(d.get('计费日期'), '%Y-%m-%d') < datetime.strptime(start_date, '%Y-%m-%d'):
            continue
        zongyuan_new_data.append(d)
    zongyuan_data = zongyuan_new_data
    zongyuan_data = zongyuan_data if zongyuan_data is not None else []
    kangfu_data = kangfu_data if kangfu_data is not None else []
    all_data = zongyuan_data + kangfu_data
    if menzhen_data:
        all_data += [
            {
                '院区': '总院',
                '计费日期': row[0],
                '姓名': row[1],
                '住院号': "",
                '病人ID': row[9],
                '病人住院ID': "",
                '科室名称': row[2],
                '病区名称': row[2],
                '主治医生姓名': row[3],
                '计费人姓名': row[4],
                '计费科室': '门诊',
                '计费科室名称': '门诊',
                '执行科室名称': row[5],
                '项目名称': row[6],
                '数量': float(row[7]),
                '结算金额': float(row[8])
            }
            for row in menzhen_data
        ]
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

    people_total.append({"name": "人次总计", **total_people})

    # 将最后一天改为人数统计
    last_day = max(total_people.keys())
    modified_data = {date: (len(people_set) if date == last_day else 0) for date, _ in total_people.items()}
    people_total.append({"name": "人数总计", **modified_data})

    price_total.append({"name": "总计", **total_price})
    people_total = sort_departments(people_total)
    price_total = sort_departments(price_total)
    i = 0
    for d in people_total:
        d['sort_num'] = i
        i = i + 1
    i = 0
    for d in price_total:
        d['sort_num'] = i
        i = i + 1

    logger.info(f'高压氧报表查询完成, 耗时: {time.time() - start_time}, {start_date} - {end_date}')
    return people_total, price_total


def safe_postgres_query(sql):
    results = []
    try:
        # 使用 `with` 语句确保自动关闭连接
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                results = cur.fetchall()

    except Exception as e:
        logger.error(f'高压氧门诊费用记录查询失败, {e.__str__()}')

    return results

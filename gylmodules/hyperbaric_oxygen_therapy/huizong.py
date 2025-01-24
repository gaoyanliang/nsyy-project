import json
import requests

import pandas as pd

from datetime import datetime, timedelta
from gylmodules import global_config


def call_third_systems_obtain_data(type: str, sql: str, db_source: str):
    param = {"type": type, "db_source": db_source, "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql}
    data = []
    try:
        response = requests.post(f"http://192.168.3.12:6080/int_api", json=param)
        # response = requests.post(f"http://192.168.124.53:6080/int_api", timeout=3, json=param)
        data = json.loads(response.text)
        data = data.get('data')
    except Exception as e:
        print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())

    return data


def call_new_his(sql: str):
    param = {"key": "o4YSo4nmde9HbeUPWY_FTp38mB1c", "sys": "newzt", "sql": sql}

    query_oracle_url = "http://192.168.3.12:6080/oracle_sql"
    # if global_config.run_in_local:
    #     query_oracle_url = "http://192.168.124.53:6080/oracle_sql"

    data = []
    try:
        response = requests.post(query_oracle_url, timeout=10, json=param)
        data = json.loads(response.text)
        data = data.get('data')
    except Exception as e:
        print('调用新 HIS 查询数据失败：' + str(param) + e.__str__())

    return data



def query_report(start_date, end_date):

    kangfu_sql = """
    SELECT a.*, b.名称 病人科室名称 FROM 住院费用记录 a join 部门表 b on a.病人科室ID = b.ID where 执行部门ID=342
    -- and TRUNC(发生时间) = TRUNC(SYSDATE)
    and 发生时间 >= to_date('{visit_date}','yyyy-mm-dd') and 发生时间 < to_date('{visit_date}','yyyy-mm-dd') + 1
    """


    sql = """
    SELECT jifeiks 计费科室, jifeiksmc 计费科室名称, COUNT(DISTINCT bingrenid) AS 病人数量,
    SUM(jiesuanje) AS 价格总数 FROM df_jj_zhuyuan.zy_feiyong1
    WHERE zhixingks = 281
    -- AND TRUNC(jifeirq) = TRUNC(SYSDATE)
    and jifeirq >= to_date('{visit_date}','yyyy-mm-dd') and jifeirq < to_date('{visit_date}','yyyy-mm-dd') + 1
    GROUP BY jifeiks, jifeiksmc ORDER BY 价格总数 DESC
    """

    yue_total = {}
    # 将字符串转换为日期格式
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    # 使用循环打印每一天的日期（仅年月日）
    current_date = start_date_obj
    while current_date <= end_date_obj:
        # print(current_date.strftime("%Y-%m-%d"))
        # current_date += timedelta(days=1)

        day = current_date.strftime("%Y-%m-%d")
        sheet2_data = call_new_his(sql.replace('{visit_date}', day))
        kangfu_data = call_third_systems_obtain_data('orcl_db_read', kangfu_sql.replace('{visit_date}', day), "kfhis")

        price_data = []
        for d in kangfu_data:
            price_data.append({'计费科室': d.get('病人科室ID'), '计费科室名称': d.get('病人科室名称'),
                '姓名': d.get('姓名'), '金额': d.get('实收金额')})

        result = {}
        for record in price_data:
            dept_id = record['计费科室']
            dept_name = record['计费科室名称']
            amount = record['金额']
            # 如果科室不存在，初始化
            if dept_id not in result:
                result[dept_id] = {'科室名称': dept_name, '人数': 0, '总金额': 0.0}
            # 更新科室统计
            result[dept_id]['人数'] += 1
            result[dept_id]['总金额'] += amount

        for dept_id, stats in result.items():
            sheet2_data.append({'计费科室': dept_id, '计费科室名称': stats['科室名称'],
                '病人数量': stats['人数'], '价格总数': stats['总金额']})

        total_price = 0.0
        total_patient = 0
        for d in sheet2_data:
            total_price += float(d.get('价格总数'))
            total_patient += int(d.get('病人数量'))

        sheet2_data.append({
            '计费科室': '总计',
            '计费科室名称': '总计',
            '病人数量': total_patient,
            '价格总数': total_price
        })

        yue_total[day] = sheet2_data

        current_date += timedelta(days=1)

    people_total = {}
    price_total = {}
    for k,v in yue_total.items():
        for i in v:
            if i['计费科室'] not in people_total:
                people_total[i['计费科室名称']] = {}
            if i['计费科室'] not in price_total:
                price_total[i['计费科室名称']] = {}

    for k,v in yue_total.items():
        for i in v:
            people_total[i['计费科室名称']][k] = people_total[i['计费科室名称']].get(k, 0) + i['病人数量']
            price_total[i['计费科室名称']][k] = price_total[i['计费科室名称']].get(k, 0) + i['价格总数']

    # for k, v in people_total.items():
    #     print(k, v)
    # print('-------------------')
    # for k, v in price_total.items():
    #     print(k, v)

    people_total = [{"name": key, **value} for key, value in people_total.items()]
    price_total = [{"name": key, **value} for key, value in price_total.items()]

    return people_total, price_total




# # 定义排序函数
# def sort_data(data):
#     sorted_keys = sorted(data.keys(), key=lambda x: (x == "总计", x))
#     sorted_data = {key: data[key] for key in sorted_keys}
#     return sorted_data
#
# # 对数据排序
# price_total = sort_data(price_total)
# people_total = sort_data(people_total)
#
#
# # 日期列
# dates = [f"第{i}天" for i in range(1, 32)]
#
# # 创建 DataFrame
# df1 = pd.DataFrame(price_total, index=dates).T
# df2 = pd.DataFrame(people_total, index=dates).T
#
# # 添加标题行
# df1_title_row = pd.DataFrame([["高压氧工作量"] + dates], columns=["类别"] + dates)  # 第一组类别为“人数”
# df2_title_row = pd.DataFrame([["高压氧人数"] + dates], columns=["类别"] + dates)  # 第二组类别为“价格”
#
# # 合并标题行与数据
# df1.reset_index(inplace=True)
# df1.columns = ["类别"] + dates
# df1_with_title = pd.concat([df1_title_row, df1], ignore_index=True)
#
# df2.reset_index(inplace=True)
# df2.columns = ["类别"] + dates
# df2_with_title = pd.concat([df2_title_row, df2], ignore_index=True)
#
# # 插入空行
# num_empty_rows = 5
# empty_rows = pd.DataFrame([[""] * len(df1_with_title.columns)] * num_empty_rows, columns=df1_with_title.columns)
#
# # 合并数据
# combined_df = pd.concat([df1_with_title, empty_rows, df2_with_title], ignore_index=True)
#
# # 写入到 Excel 文件
# output_file = "高压氧一月汇总.xlsx"
# combined_df.to_excel(output_file, sheet_name="日", index=False, header=False)
#
# print(f"两组数据已成功写入到 {output_file}，第一组类别为‘人数’，第二组类别为‘价格’。")



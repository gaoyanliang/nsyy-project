import json
import requests

from datetime import datetime
from gylmodules import global_config


from collections import defaultdict
from datetime import datetime
from decimal import Decimal


def call_third_systems_obtain_data(type: str, sql: str, db_source: str):
    param = {"type": type, "db_source": db_source, "randstr": "XPFDFZDF7193CIONS1PD7XCJ3AD4ORRC", "sql": sql}
    data = []
    try:
        # response = requests.post(f"http://192.168.3.12:6080/int_api", json=param)
        response = requests.post(f"http://192.168.124.53:6080/int_api", timeout=200, json=param)
        data = json.loads(response.text)
        data = data.get('data')
    except Exception as e:
        print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())

    return data


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

# ===========================================================================
# ================================== 日统计 ==================================
# ===========================================================================


visit_date = '2025-02-01'
visit_end_date = '2025-02-28'

"""
查询当天所有做高压氧治疗的患者收费信息
"""

sql = f"""
select to_char(feiyong.fashengrq,'yyyy-mm-dd') 计费日期, bingrenxx.xingming 姓名, bingrenxx.zhuyuanhao 住院号, bingrenxx.bingrenid 病人ID,
bingrenxx.bingrenzyid 病人住院ID, feiyong.keshimc 科室名称, feiyong.bingqumc 病区名称, feiyong.zhuzhiysxm 主治医生姓名,
feiyong.jifeirxm 计费人姓名, feiyong.jifeiks 计费科室, feiyong.jifeiksmc 计费科室名称, feiyong.zhixingksmc 执行科室名称,
feiyong.xiangmumc 项目名称, feiyong.shuliang 数量, feiyong.jiesuanje 结算金额 from df_jj_zhuyuan.zy_feiyong1 feiyong
join df_jj_zhuyuan.zy_bingrenxx bingrenxx on feiyong.bingrenid = bingrenxx.bingrenid
WHERE feiyong.zhixingks = '281'
-- and  TRUNC(jifeirq) = TRUNC(SYSDATE)
and feiyong.fashengrq >= to_date('{visit_date}','yyyy-mm-dd') and feiyong.fashengrq < to_date('{visit_end_date}','yyyy-mm-dd') + 1
order by bingrenxx.xingming, feiyong.jifeirq
"""

sheet1_data = query_menzhen(sql)
sheet1_data = [
        {
            '计费日期': row[0],
            '姓名': row[1],
            '住院号': row[2],
            '病人ID': row[3],
            '病人住院ID': row[4],
            '科室名称': row[5],
            '病区名称': row[6],
            '主治医生姓名': row[7],
            '计费人姓名': row[8],
            '计费科室': row[9],
            '计费科室名称': row[10],
            '执行科室名称': row[11],
            '项目名称': row[12],
            '数量': float(row[13]) if isinstance(row[13], Decimal) else row[13],
            '结算金额': float(row[14]) if isinstance(row[14], Decimal) else row[14],
        }
        for row in sheet1_data
    ]
print('总院人数:', len(sheet1_data))

for d in sheet1_data:
    d['院区'] = '总院'
if not sheet1_data:
    sheet1_data = []


"""
查询康复院区 当天所有做高压氧治疗的患者收费信息
"""

kangfu_sql = f"""
SELECT a.*, to_char(a.发生时间, 'yyyy-mm-dd') as 计费日期, b.名称 病人科室名称 FROM 住院费用记录 a join 部门表 b on a.病人科室ID = b.ID where 执行部门ID=342
-- and TRUNC(发生时间) = TRUNC(SYSDATE)
and a.发生时间 >= to_date('{visit_date}','yyyy-mm-dd') and a.发生时间 < to_date('{visit_end_date}','yyyy-mm-dd') + 1
"""

kangfu_data = call_third_systems_obtain_data('orcl_db_read', kangfu_sql, "kfhis")
for d in kangfu_data:
    sheet1_data.append({
        '院区': '康复院区',
        '计费日期': d.get('计费日期'),
        '姓名': d.get('姓名'),
        '住院号': "",
        '病人ID': d.get('病人ID'),
        '病人住院ID': "",
        '科室名称': d.get('病人科室名称'),
        '病区名称': d.get('病人科室名称'),
        '主治医生姓名': d.get('开单人'),
        '计费人姓名': d.get('操作员姓名'),
        '计费科室': d.get('执行部门ID'),
        '计费科室名称': d.get('执行部门ID'),
        '执行科室名称': d.get('执行部门ID'),
        '项目名称': '18248',
        '数量': d.get('数次'),
        '结算金额': d.get('实收金额')
    })

# print(sheet1_data)
print('康复人数: ', len(kangfu_data))

sql_menzhen = f"""
    SELECT to_char(COALESCE(t.zhixingrq, t1.shoufeirq2), 'yyyy-mm-dd') 计费日期,
           t.bingrenxm 姓名, t.kaidanksmc 开单科室名称,
           t.kaidanysxm 开单人, t.zhixingrxm 执行人姓名, 
           t.zhixingksmc 执行科室名称, t1.xiangmumc 项目名称, t1.shuliang 数量, t1.jiesuanje 结算金额, t.bingrenid 病人ID 
      FROM df_jj_menzhen.mz_feiyong1 t JOIN df_jj_menzhen.mz_feiyong2 t1 ON t.feiyongid = t1.feiyongid
      LEFT JOIN df_jj_menzhen.mz_shoufei t2 ON t.shoufeiid = t2.shoufeiid
     WHERE t.zhixingks = '281'
       and COALESCE(t.zhixingrq, t1.shoufeirq2) >= to_date('{visit_date}', 'yyyy-mm-dd') and
     COALESCE(t.zhixingrq, t1.shoufeirq2) < to_date('{visit_end_date}', 'yyyy-mm-dd') + 1
     order by t.bingrenxm, t.zhixingrq
    """

menzhen_data = query_menzhen(sql_menzhen)
for d in menzhen_data:
    sheet1_data.append({
        '院区': '门诊',
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


print('======================================')
people_set = set()
for d in sheet1_data:
    people_set.add(d.get('病人ID'))
    # print(d)


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


data_sheets = [
    {"sheet_name": "治疗列表", "data": sheet1_data, "column_order": ["院区", "计费日期", "姓名", "住院号", "病人ID", "病人住院ID", "科室名称", "病区名称",
                                                                     "主治医生姓名", "计费人姓名", "计费科室", "计费科室名称", "执行科室名称", "项目名称", "数量", "结算金额"]},
]


# 写入 Excel 文件
# file_name = datetime.now().strftime('%Y%m%d') + '工作量.xlsx'
# file_name = visit_date + '工作量.xlsx'
# write_to_excel_with_sheets(data_sheets, file_name)























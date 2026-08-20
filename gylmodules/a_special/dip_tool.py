
# ==============================================================================================
# ========================== 将治疗医嘱中对DIP入组没有帮助的标记 ====================================
# ==============================================================================================

# import pandas as pd
# from openpyxl.styles import PatternFill
#
# # ================== 可配置区域 ==================
# # 定义过滤关键词（根据常见无帮助医嘱命名）
# FILTER_KEYWORDS = [
#     # 基础生命体征与监护
#     '体温', '脉搏', '血压', '心电监护', '吸氧', '吸痰',
#     # 一般对症治疗
#     '物理降温', '冷热湿敷', '静脉输液', '皮下', '肌肉注射', '静脉注射',
#     # 常规换药/清创/拆线
#     '换药', '拆线', '清创',
#     # 常规检查
#     '血糖', '测定', '心电图', '胆红素',
#     # 口腔常规
#     '洁治', '充填', '牙髓', '调颌',
#     # 眼科常规
#     '泪道', '结膜', '角膜', '异物取出',
#     # 皮肤常规
#     '皮损', '皮肤活检',
#     # 康复理疗
#     '康复', '理疗', '训练',
#     #
#     '门诊', '转运费', '临床试验', '加收', '床位费', '卧气垫床', '电动气垫床', '产程管理', '少收', '减收', '急诊诊查费', '住院诊查费',
#     '中药贴敷'
# ]
#
# # 输入文件路径（请修改为实际路径）
# INPUT_FILE = '/Users/gaoyanliang/各个系统文档整理/ai-dip/治疗医嘱.xlsx'
# # 输出文件路径
# OUTPUT_FILE = '/Users/gaoyanliang/各个系统文档整理/ai-dip/治疗医嘱_标记.xlsx'
# # =============================================
#
# def is_filtered(text):
#     """判断医嘱名称是否包含任何过滤关键词"""
#     if pd.isna(text):
#         return False
#     name = str(text)
#     return any(kw in name for kw in FILTER_KEYWORDS)
#
# def main():
#     # 1. 读取Excel（默认第一个sheet）
#     df = pd.read_excel(INPUT_FILE, sheet_name=0)
#
#     # 2. 添加标记列
#     df['是否过滤'] = df['yizhuxmmc'].apply(is_filtered)
#
#     # 3. 保存为新文件，并用openpyxl对过滤行添加背景色
#     with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, sheet_name='Sheet1')
#         workbook = writer.book
#         worksheet = writer.sheets['Sheet1']
#
#         # 黄色填充
#         yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
#
#         # 获取“是否过滤”列的位置（从1开始）
#         col_idx = df.columns.get_loc('是否过滤') + 1
#
#         # 从第2行开始（表头为第1行）
#         for row_idx, filtered in enumerate(df['是否过滤'], start=2):
#             if filtered:
#                 # 标记整行背景色
#                 for col in range(1, len(df.columns) + 1):
#                     cell = worksheet.cell(row=row_idx, column=col)
#                     cell.fill = yellow_fill
#
#     print(f'✅ 处理完成！已生成标记文件：{OUTPUT_FILE}')
#
# if __name__ == '__main__':
#     main()








# ==============================================================================================
# ========================== 将手术清单中对DIP入组没有帮助的标记 ====================================
# ==============================================================================================


import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ================== 可配置区域 ==================
# 定义过滤关键词（根据手术名称判断）
FILTER_KEYWORDS = [
    # 检查/诊断类
    '造影', '超声', '检查', '活检', '探查', '测定', '测量', '监测',
    # 康复理疗类
    '康复', '理疗', '训练', '手法', '按摩', '推拿', '牵引',
    # 一般护理/小操作
    '换药', '拆线', '清创', '引流', '穿刺', '注射', '输液', '置管', '拔管',
    '石膏', '夹板', '外固定', '拔甲', '清创', '冲洗',
    # 眼科、口腔等常见小手术（非主要）
    '洁治', '充填', '拔牙', '调颌', '泪道', '结膜', '角膜',
    '睑板', '翼状胬肉', '眼睑', '耳廓', '外耳',
    '鼻甲', '鼻窦', '扁桃体', '腺样体',
    '包皮', '痔', '肛裂', '肛周',
    '皮肤', '痣', '瘢痕', '囊肿',
    # 其他辅助性操作
    '造影', 'X线', 'CT', 'MRI', '核磁', 'PET', 'ECT', '扫描', '照相'
]

# 输入文件路径（请修改为实际路径）
INPUT_FILE = '/Users/gaoyanliang/各个系统文档整理/ai-dip/手术清单.xlsx'
# 输出文件路径
OUTPUT_FILE = '/Users/gaoyanliang/各个系统文档整理/ai-dip/手术清单_标记.xlsx'
# =============================================

def is_filtered(text):
    """判断手术名称是否包含任何过滤关键词"""
    if pd.isna(text):
        return False
    name = str(text)
    return any(kw in name for kw in FILTER_KEYWORDS)

def main():
    # 1. 读取Excel（默认第一个sheet）
    df = pd.read_excel(INPUT_FILE, sheet_name=0)

    # 2. 确定手术名称列（根据列名，可能是'shoushumc'）
    # 如果找不到'shoushumc'，尝试使用'手术名称'
    name_col = None
    if 'shoushumc' in df.columns:
        name_col = 'shoushumc'
    elif '手术名称' in df.columns:
        name_col = '手术名称'
    else:
        raise ValueError("未找到手术名称列，请检查列名。")

    # 3. 添加标记列
    df['是否过滤'] = df[name_col].apply(is_filtered)

    # 4. 保存为新文件，并用openpyxl对过滤行添加背景色
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # 黄色填充
        yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

        # 获取“是否过滤”列的位置（从1开始）
        col_idx = df.columns.get_loc('是否过滤') + 1

        # 从第2行开始（表头为第1行）
        for row_idx, filtered in enumerate(df['是否过滤'], start=2):
            if filtered:
                # 标记整行背景色
                for col in range(1, len(df.columns) + 1):
                    cell = worksheet.cell(row=row_idx, column=col)
                    cell.fill = yellow_fill

    print(f'✅ 处理完成！已生成标记文件：{OUTPUT_FILE}')

if __name__ == '__main__':
    main()


    # # 读取之前生成的标记文件
    # df = pd.read_excel('/Users/gaoyanliang/各个系统文档整理/ai-dip/手术清单_标记.xlsx')
    # # 1. 查看所有被标记为“无帮助”的记录（需要过滤的）
    # filtered_records = df[df['是否过滤'] == True]
    # print(f"无帮助（需过滤）记录数：{len(filtered_records)}")
    # # 2. 查看所有未被标记的记录（有帮助的）
    # non_filtered_records = df[df['是否过滤'] == False]
    # print(f"\n有帮助（保留）记录数：{len(non_filtered_records)}")




















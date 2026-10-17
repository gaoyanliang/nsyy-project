#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/gyl/312')  # 就这一行！

import logging
import re
import sys
import time
import redis
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
from typing import Tuple, Dict, List
from datetime import datetime, timedelta

# 添加日志配置
# 配置日志系统
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # 输出到控制台
        logging.StreamHandler(sys.stdout),
        # 输出到同级目录的日志文件
        logging.FileHandler(f'shift_change_task.log')
    ]
)
# 设置第三方库日志级别为 WARNING
for lib in ['urllib3', 'requests', 'asyncio', 'httpx', 'selenium', 'paramiko']:
    logging.getLogger(lib).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from gylmodules import global_config, global_tools
from gylmodules.shift_change import shift_change_config
from gylmodules.shift_change.shift_change_config import PATIENT_TYPE_ORDER
from gylmodules.shift_change.shift_change_server import query_shift_config
from gylmodules.utils.db_utils_new import DbUtil

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True, protocol=2)


# ========================================================================
# ============================= 查询交接班数据 =============================
# ========================================================================


"""查询当前交班时间前一天的所有做手术的患者列表"""
def query_shoushu_patient_zhuyuanhao():
    start_time = time.time()
    cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pg_sql = """select zb.bingrenzyid as "bingrenzyid",zb.bingrenid 病人id,zb.zhuyuancs 主页id,zb.zhuyuanhao 住院号
                from df_jj_zhuyuan.zy_bingrenxx zb join (select distinct ss.bingrenzyid from df_shenqingdan.sm_shoushuxx ss 
                where ss.zuofeibz=0 and ss.zhuangtaibz=7 and ss.jieshusj between (timestamp'{end_time}'-interval '1' day) and 
                '{end_time}')ss on ss.bingrenzyid =zb.bingrenzyid where zb.quxiaorybz=0  and zb.yingerbz=0 
                and zb.rukebz=1 and zb.zaiyuanzt=0"""

    ydhl_sql = r"""with bingren as (select t.patient_id as 病人id, t.visit_id as 主页id,
                t.dept_name 所在病区 from kyeecis.v_his_pats_in_hospital t where t.dept_name in ('疼痛科护理单元')
                ) , ss as (select t2.patient_id as 病人id, t2.visit_id as 主页id, case 
                when regexp_like(t3.item_value, '^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}$') then 
                to_date(t3.item_value, 'yyyy/mm/dd hh24:mi:ss')
                when regexp_like(t3.item_value, '^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2} \d{1,2}:\d{1,2}$')
                then to_date(t3.item_value, 'yyyy-mm-dd hh24:mi:ss')
                when regexp_like(t3.item_value, '^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2} [^\d]+ [^\d]+ \d{1,2}:\d{1,2}:\d{1,2}$') then 
                to_date(regexp_replace(t3.item_value, '^(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}) [^\d]+ [^\d]+ (\d{1,2}:\d{1,2}:\d{1,2})$', '\1 \2'),
                                'yyyy/mm/dd hh24:mi:ss')
                else null 
                end as 手术结束时间
                from kyeecis.docs_eval_report_rec t2
                join kyeecis.docs_eval_report_detail_rec t3
                on t2.report_id = t3.report_id and t3.enabled_value = 'Y'
                where t2.theme_code = '介入手术护理单' and t2.enabled_value = 'Y' and t3.item_name = '手术结束时间'
                and t2.create_time between timestamp '{end_time}'-2 and timestamp '{end_time}'+1
                and (t2.patient_id,t2.visit_id) in (select 病人id,主页id from bingren)
                )
                select a.bingrenzyid as "bingrenzyid",ss.病人id as "病人id",ss.主页id as "主页id" ,a.inp_no 住院号,a.dept_name 所在病区
                from ss
                join kyeecis.v_his_pats_in_hospital a on a.patient_id=ss.病人id and a.visit_id = ss.主页id
                where ss.手术结束时间 between timestamp '{end_time}'-1 and timestamp '{end_time}' 
                """
    pg_shoushu, ydhl_shoushu = [], []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 查询医生交接班 患者数据
        tasks = {
            "pg_shoushu": executor.submit(timed_execution, "查询手术患者列表 pg ", global_tools.call_new_his_pg,
                                          pg_sql.replace("{end_time}", cur_time)),
            "ydhl_shoushu": executor.submit(timed_execution, "查询手术患者列表 ydhl ", global_tools.call_new_his,
                                            ydhl_sql.replace("{end_time}", cur_time), 'ydhl', None)
        }
        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        pg_shoushu = results["pg_shoushu"]
        ydhl_shoushu = results["ydhl_shoushu"]

    # 先从pg和ydhl查询上个班次中做手术的患者， 然后在查询这些患者的基本信息
    shoushu_set = set(item.get('bingrenzyid') for item in pg_shoushu + ydhl_shoushu)
    if not shoushu_set:
        return []

    # 查询所有手术患者的患者情况
    patient_info_sql = """select y.bingrenzyid, y.dangqiancwbm 床号, y.xingming 姓名, y.zhuyuanhao 住院号,
	y.bingrenid "病人id", y.xingbiemc 性别, y.nianling 年龄, y.dangqianbqmc 所在病区, y.dangqianbqid 所在病区id,
	y.zhuzhiysxm 主治医生姓名, coalesce(case
   		 when  (xpath('string(//node[@name="目前诊断"])', aa.wenjiannr::xml))[1]::text ~ '2[\.、]' 
  		  then regexp_replace((xpath('string(//node[@name="目前诊断"])', aa.wenjiannr::xml))[1]::text, '2[\.、].*$', '')
			else (xpath('string(//node[@name="目前诊断"])', aa.wenjiannr::xml))[1]::text
		end ,x.主要诊断,case
    		when  nullif((xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text,'')  is not null
    		then 
    			case when (xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text ~ '2[\.、]' 
    				 then regexp_replace((xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text, '2[\.、].*$', '')
					 else (xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text
				end
			when  nullif((xpath('string(//node[@name="入院诊断"])', wb2.wenjiannr::xml))[1]::text,'')  is not null
    		then 
    			case when (xpath('string(//node[@name="入院诊断"])', wb2.wenjiannr::xml))[1]::text ~ '2[\.、]' 
    				 then regexp_replace((xpath('string(//node[@name="入院诊断"])', wb2.wenjiannr::xml))[1]::text, '2[\.、].*$', '')
					 else (xpath('string(//node[@name="入院诊断"])', wb2.wenjiannr::xml))[1]::text
				end
			when nullif ((xpath('string(//node[@name="初步诊断_中医病名名称"])', wb2.wenjiannr::xml))[1]::text,'')  is not null
			then (xpath('string(//node[@name="初步诊断_中医病名名称"])', wb2.wenjiannr::xml))[1]::text || '(中医诊断)'|| 
				 (xpath('string(//node[@name="初步诊断_西医诊断名称"])', wb2.wenjiannr::xml))[1]::text || '(西医诊断)'
			else null
		end)
 as  主要诊断
from
	df_jj_zhuyuan.zy_bingrenxx y
left join df_bingli.ws_binglijl wb on wb.bingrenzyid =y.bingrenzyid and (wb.binglimc like '%入院记录%' or wb.binglimc='24小时入出院记录')  and wb.zuofeibz=0 and wb.wenshuzt=2
left join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid and xml_is_well_formed_document(coalesce(wb2.wenjiannr, ''))=True
left join (select wb.bingrenzyid,wb.jilusj,wb2.wenjiannr,row_number () over (partition by wb.bingrenzyid order by wb.jilusj desc) as rk
from df_bingli.ws_binglijl wb
join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid and xml_is_well_formed_document(coalesce(wb2.wenjiannr, ''))=True
where wb.binglimc ='转入记录'  and wb.zuofeibz=0 and wb.wenshuzt=2
)aa on aa.bingrenzyid =y.bingrenzyid and aa.rk=1
left join 
(select wb.bingrenzyid,
case
    		when  nullif((xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text,'')  is not null
    		then 
    			case when (xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text ~ '2[\.、]' 
    				 then regexp_replace((xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text, '2[\.、].*$', '')
					 else (xpath('string(//node[@name="初步诊断"])', wb2.wenjiannr::xml))[1]::text
				end
			when nullif ((xpath('string(//node[@name="初步诊断_中医病名名称"])', wb2.wenjiannr::xml))[1]::text,'')  is not null
			then (xpath('string(//node[@name="初步诊断_中医病名名称"])', wb2.wenjiannr::xml))[1]::text || '(中医诊断)'|| 
				 (xpath('string(//node[@name="初步诊断_西医诊断名称"])', wb2.wenjiannr::xml))[1]::text || '(西医诊断)'
			else null
		end as 主要诊断
from df_bingli.ws_binglijl wb
join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid and xml_is_well_formed_document(coalesce(wb2.wenjiannr, ''))=True
where wb.binglimc = '首次病程记录'  and wb.zuofeibz=0 and wb.wenshuzt=2
)x on x.bingrenzyid =y.bingrenzyid
where
	y.quxiaorybz = 0
	and y.yingerbz = 0
	and y.rukebz = 1
	and y.xingming not like '%测试%'
	and y.zaiyuanzt = 0
	and y.bingrenzyid in ({bingrenzyid})
    """
    patient_info_sql = patient_info_sql.replace('{bingrenzyid}', ','.join([f"'{item}'" for item in shoushu_set]))
    patient_info_list = global_tools.call_new_his_pg(patient_info_sql)

    shoushu_list = []
    if patient_info_list:
        for item in patient_info_list:
            item['patient_ward_id'] = shift_change_config.his_dept_dict.get(item.get('所在病区'))
            shoushu_list.append(item)

    logger.debug(f"查询手术患者列表耗时: {time.time() - start_time} , 数量 {len(shoushu_set)}")
    return patient_info_list


"""查询术后情况，仅晚班"""
def postoperative_situation(shift_classes, dept_list, zhuyuanhao_list):
    if int(shift_classes) != 3 or not zhuyuanhao_list:
        return []

    ydhl_dept_list = []
    for did in dept_list:
        if shift_change_config.ydhl_dept_dict.get(str(did)):
            ydhl_dept_list.append(shift_change_config.ydhl_dept_dict.get(str(did)))

    dept_str = ', '.join(f"'{item}'" for item in ydhl_dept_list)
    bingrenzyid_str = ', '.join(f"'{item}'" for item in zhuyuanhao_list)

    sql = """select zy.bingrenzyid "住院id",zy.bed_no 床号, zy.patient_id "病人id", zy.dept_name 所在病区,
    dnr.illness_measures 患者情况 from kyeecis.docs_normal_report_rec dnr join kyeecis.V_HIS_PATS_IN_HOSPITAL zy 
            on dnr.patient_id=zy.patient_id and dnr.visit_id=zy.visit_id and dept_code in ({dept_code}) 
            and bingrenzyid in ({bingrenzyid}) where dnr.time_point = trunc(sysdate)+ 7/24
            and dnr.theme_code like '%一般护理记录单%' and dnr.enabled_value = 'Y'
            """
    sql = sql.replace('{dept_code}', dept_str)
    sql = sql.replace('{bingrenzyid}', bingrenzyid_str)

    start_time = time.time()
    result = global_tools.call_new_his(sql=sql, sys='ydhl', clobl=None)
    logger.debug(f"术后信息查询: 术后数量 {len(result)} 执行时间: {time.time() - start_time} s")
    return result


"""查询住院患者的出院类型"""
def discharge_situation():
    sql = """select 住院号,疾病转归 from (select report_id,住院号,疾病转归 from (
    select t2.item_name, t2.item_value, t.report_id from kyeecis.docs_eval_report_rec t
    join kyeecis.docs_eval_report_detail_rec t2  on t.report_id = t2.report_id
    where t2.item_name in ('疾病转归', '住院号') and t2.enabled_value = 'Y' and t.theme_code = '出院小结'
    and t.create_time > sysdate - 1) pivot (max(item_value) 
    for item_name in ('疾病转归' as 疾病转归, '住院号' as 住院号))) where 疾病转归 is not null"""
    start_time = time.time()
    result = global_tools.call_new_his(sql=sql, sys='ydhl', clobl=None)
    logger.debug(f"出院信息查询：数量 {len(result)} 执行时间: {time.time() - start_time} s")
    if not result:
        return None
    result = {item.get('住院号'): '自动' if str(item.get('疾病转归', '')).strip() == '自动出院' else str(
        item.get('疾病转归', '')) for item in result}
    return result


"""医生交接班数据查询"""
def doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list, flush: bool = False, pid: str = None):
    start_time = time.time()
    shift_start, shift_end = get_complete_time_slot(time_slot)

    # 查询该班次是否有危急值
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                    f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and dept_id in ({','.join(dept_id_list)})"
        all_cvs = db.query_all(query_sql)

    patients, patient_count = [], []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 查询医生交接班 患者数据
        tasks = {
            "patients": executor.submit(timed_execution, "医生交接班(普通科室)患者数据查询 sql-1 sql_nhis ",
                                        global_tools.call_new_his_pg,
                                        reg_sqls.get(1).get('sql_nhis')
                                        .replace("--and", "and" if pid else "--and")
                                        .replace("{single_query}", pid if pid else "{single_query}")
                                        .replace("{科室id}", ', '.join(f"'{str(item)}'" for item in dept_id_list))
                                        .replace("{start_time}", shift_start)
                                        .replace("{end_time}", shift_end))
        }
        if not flush:
            tasks["patient_count"] = executor.submit(timed_execution, "医生交接班(普通科室)患者人数查询 sql-2 sql_nhis ",
                                                global_tools.call_new_his_pg,
                                                reg_sqls.get(2).get('sql_nhis')
                                                .replace("{科室id}",
                                                         ', '.join(f"'{str(item)}'" for item in dept_id_list))
                                                .replace("{start_time}", shift_start)
                                                .replace("{end_time}", shift_end))

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        patients = results["patients"]
        patient_count = results.get("patient_count", [])

    all_patients = merge_patient_cv_data(all_cvs, patients, 1, dept_id_list)
    # 将特殊科室合并
    for item in all_patients:
        if str(item.get('所在科室id')) not in shift_change_config.doc_teshu_dept_list:
            continue
        # 注意这两个顺序不能换
        item['所在科室id'] = shift_change_config.doc_teshu_dept_dict.get(item.get('所在科室'))
        item['所在科室'] = shift_change_config.doc_teshu_dept_id_dict.get(str(item.get('所在科室id')))

    # 合并特殊科室数量
    if patient_count:
        # 统计危急值数量
        cv_count = {}
        if all_cvs:
            for item in all_patients:
                if item.get('患者类别') and str(item.get('患者类别')).__contains__('危急值'):
                    key = str(item.get('所在科室id'))
                    if key not in cv_count:
                        cv_count[key] = set()
                    cv_count[key].add(item.get('病人id'))
        if cv_count:
            for item in patient_count:
                if item.get('患者类别') == '危急值':
                    item['人数'] = len(cv_count.get(item.get('所在科室id'))) if cv_count.get(item.get('所在科室id')) else 0

    for item in patient_count:
        if str(item.get('所在科室id')) not in shift_change_config.doc_teshu_dept_list:
            continue
        # 注意这两个顺序不能换
        item['所在科室id'] = shift_change_config.doc_teshu_dept_dict.get(item.get('所在科室'))
        item['所在科室'] = shift_change_config.doc_teshu_dept_id_dict.get(str(item.get('所在科室id')))

    merged_dict = {}
    for item in patient_count:
        dept_id = str(item["所在科室id"])
        if (dept_id, item["患者类别"]) not in merged_dict:
            # 第一次遇到该科室，创建副本并初始化count
            merged_dict[(dept_id, item["患者类别"])] = item.copy()
        else:
            # 已存在该科室，只累加count字段
            merged_dict[(dept_id, item["患者类别"])]["人数"] += item["人数"]
    patient_count = list(merged_dict.values())

    save_data(f"1-{shift_classes}", all_patients, patient_count, None, flush)
    logger.info(f"医生 {','.join(dept_id_list)} 交接班数据查询完成 ✅ 总耗时 {time.time() - start_time} 秒")


"""AICU 1000965 CCU 1001120  交班信息查询"""
def aicu_shift_change(reg_sqls, shift_classes, time_slot, dept_id, flush: bool = False, pid: str = None):
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    # 查询该班次是否有危急值
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                    f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id = {dept_id}"
        all_cvs = db.query_all(query_sql)

    dept_name = "'CCU护理单元'"
    if str(dept_id) == "1000965":
        dept_name = "'AICU护理单元'"
    patient_count, siwang_patients, chuangwei_info1, chuangwei_info2, pg_patients, \
        ydhl_patients, shuhou_patients, chuyuan_ydhl, teshu_patients, youchuang_pg, youchuang_ydhl = [], [], [], [], [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "AICU/CCU 患者人数统计 sql-5 sql_nhis ",
                                             global_tools.call_new_his_pg, reg_sqls.get(5).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)
                                             .replace("{病区名称}", dept_name)
                                             .replace("--and", "and" if pid else "--and")
                                             .replace("{single_query}", pid if pid else "{single_query}")),
            "siwang_patients": executor.submit(timed_execution, "AICU/CCU 出院转出死亡患者情况 sql-14 sql_nhis ",
                                               global_tools.call_new_his_pg, reg_sqls.get(14).get('sql_nhis')
                                               .replace("{start_time}", shift_start)
                                               .replace("{end_time}", shift_end)
                                               .replace("{病区名称}", dept_name)
                                               .replace("--and", "and" if pid else "--and")
                                               .replace("{single_query}", pid if pid else "{single_query}")),
            "pg_patients": executor.submit(timed_execution, "AICU/CCU 护理单元患者情况 pg sql-15 sql_base ",
                                           global_tools.call_new_his_pg, reg_sqls.get(15).get('sql_base')
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)
                                           .replace("{病区名称}", dept_name)
                                           .replace("--and", "and" if pid else "--and")
                                           .replace("{single_query}", pid if pid else "{single_query}")),
            "ydhl_patients": executor.submit(timed_execution, "AICU/CCU 护理单元患者情况 ydhl sql-15 sql_ydhl ",
                                             global_tools.call_new_his, reg_sqls.get(15).get('sql_ydhl')
                                             .replace("{start_time}", shift_start)
                                             .replace("{病区名称}", dept_name)
                                             .replace("{end_time}", shift_end).replace("--and",
                                                                                       "and" if pid else "--and")
                                             .replace("{single_query}", pid if pid else "{single_query}"), 'ydhl',
                                             None),
            "chuyuan_ydhl": executor.submit(discharge_situation),
            "teshu_patients": executor.submit(timed_execution, "AICU/CCU 护理单元特殊处理患者情况 sql-26 sql_ydhl ",
                                              global_tools.call_new_his, reg_sqls.get(26).get('sql_ydhl')
                                              .replace("{start_time}", shift_start)
                                              .replace("{病区名称}", dept_name)
                                              .replace("{end_time}", shift_end).replace("--and",
                                                                                        "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}"), 'ydhl',
                                              None),

            "youchuang_pg": executor.submit(timed_execution, "AICU/CCU 有创 pg sql-27 sql_nhis ",
                                            global_tools.call_new_his_pg, reg_sqls.get(27).get('sql_nhis')
                                            .replace("{start_time}", shift_start)
                                            .replace("{end_time}", shift_end)
                                            .replace("--and", "and" if pid else "--and")
                                            .replace("{single_query}", pid if pid else "{single_query}")
                                            .replace("{病区id}",
                                                     ', '.join(f"'{item}'" for item in [str(dept_id)]))),
            "youchuang_ydhl": executor.submit(timed_execution, "AICU/CCU 有创 ydhl sql-27 sql_ydhl",
                                              global_tools.call_new_his, reg_sqls.get(27).get('sql_ydhl')
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end).replace("--and",
                                                                                        "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}"), 'ydhl',
                                              None)

        }
        if int(shift_classes) == 3 and not flush:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "AICU/CCU 特殊患者床位信息 sql-8 sql_nhis ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(8).get('sql_nhis').replace("{病区名称}", dept_name))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "AICU/CCU 特殊患者床位信息 sql-8 sql_ydhl ",
                                                       global_tools.call_new_his, reg_sqls.get(8).get('sql_ydhl').replace("{病区名称}", dept_name),
                                                       'ydhl', None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        siwang_patients = results["siwang_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]
        chuyuan_ydhl = results.get("chuyuan_ydhl")
        teshu_patients = results["teshu_patients"]
        youchuang_pg = results["youchuang_pg"]
        youchuang_ydhl = results.get("youchuang_ydhl")

    # 查询预术手术患者
    yu_shoushus = handle_shoushu_and_yushu(reg_sqls, time_slot, [str(dept_id)], pid)
    if yu_shoushus:
        shoushu_count, yushu_count = 0, 0
        for item in yu_shoushus:
            if item.get('患者类别') == '手术':
                shoushu_count += 1
            else:
                yushu_count += 1
        patient_count.append({"患者类别": '预术', "人数": yushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": str(dept_id), "所在病区": dept_name.replace("'", "")})
        patient_count.append({"患者类别": '手术', "人数": shoushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": str(dept_id), "所在病区": dept_name.replace("'", "")})

    if chuyuan_ydhl:
        for patient in siwang_patients:
            if patient.get('患者类别') == '出院':
                patient['患者情况'] = patient['患者情况'].replace('###', chuyuan_ydhl.get(patient.get('住院号'), ''))

    start_time = time.time()
    all_patient_info = siwang_patients if siwang_patients else []
    all_patient_info = all_patient_info + handle_youchuang(youchuang_pg, youchuang_ydhl)
    all_patient_info = all_patient_info + yu_shoushus

    # 合并患者信息
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    merged_info = {}  # key = (病人id, 主页id)，value = （'患者类别'）}
    target_set = set()
    for patient in pg_patients:
        person_key = (patient.get("病人id"), str(patient.get("主页id")))
        if person_key not in merged_info:
            merged_info[person_key] = set()
        merged_info[person_key].add(patient.get("患者类别"))

    for person_key, types in merged_info.items():
        if '转入' in types and '手术' in types:
            target_set.add(person_key)

    # 如果转入和手术相同，仅需要一份患者情况
    merged_info = {}  # key = (病人id, 主页id)，value = '患者情况'}
    for patient in pg_patients:
        if patient.get("患者类别") in ['病危', '病重']:
            key = (patient.get("病人id"), str(patient.get("主页id")), '病危重')
        elif patient.get("患者类别") in ['入院', '转入']:
            key = (patient.get("病人id"), str(patient.get("主页id")), '新转入')
        else:
            key = (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '入院' or patient.get("患者类别") == '转入':
                    if ydhl_patient.get("转入时间") == patient.get("转入时间"):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    # 同一个人 如果同时存在 转入记录和手术记录， 则转入记录的患者情况需要清空
    surgery_patient_ids = set()
    for record in all_patient_info:
        if record.get('患者类别') == '手术':
            surgery_patient_ids.add(record.get('bingrenzyid'))
    processed_records = []
    for record in all_patient_info:
        # 如果是转入记录且该患者有手术记录，清空患者情况
        if (record.get('患者类别') == '转入' and
                record.get('bingrenzyid') in surgery_patient_ids):
            record['患者情况'] = ''

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": str(dept_id), "所在病区": dept_name.replace("'", "")})

    patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, [str(dept_id)], pid)

    # 合并特殊处理患者情况
    if teshu_patients:
        teshu_info = {}
        for patient in teshu_patients:
            if patient.get('bingrenzyid') not in teshu_info:
                teshu_info[patient.get('bingrenzyid')] = patient.get('患者情况')

        patient_set = set()
        for patient in all_patients:
            if patient.get('bingrenzyid') in teshu_info and patient.get('bingrenzyid') not in patient_set:
                patient_set.add(patient.get('bingrenzyid'))
                patient['患者情况'] = teshu_info.get(patient.get('bingrenzyid')) + patient['患者情况']
                patient['患者类别'] = patient.get('患者类别') + ', 特殊处理'

    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2, flush, pid)
    logger.info(f"AICU/CCU 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


"""妇产科 1000961 交班信息查询"""
def ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu, flush: bool = False, pid: str = None):
    if int(shift_classes) == 1:
        trunc = '17'
    elif int(shift_classes) == 2:
        trunc = '21.5'
    else:
        trunc = '7'
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                    f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id = 1000961"
        all_cvs = db.query_all(query_sql)

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, pg_patients, \
        ydhl_patients, shuhou_patients, chuyuan_ydhl, youchuang_pg, youchuang_ydhl = [], [], [], [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "妇产科患者人数统计 sql-7 sql_his ",
                                             global_tools.call_new_his_pg, reg_sqls.get(7).get('sql_nhis')
                                             .replace("--and", "and" if pid else "--and")
                                             .replace("{single_query}", pid if pid else "{single_query}")
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "teshu_patients": executor.submit(timed_execution, "妇产科 出院转出死亡患者情况 sql-16 sql_nhis ",
                                              global_tools.call_new_his_pg, reg_sqls.get(16).get('sql_nhis')
                                              .replace("--and", "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}")
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end)),
            "pg_patients": executor.submit(timed_execution, "妇产科 护理单元患者情况 pg sql-17 sql_base ",
                                           global_tools.call_new_his_pg, reg_sqls.get(17).get('sql_base')
                                           .replace("--and", "and" if pid else "--and")
                                           .replace("{single_query}", pid if pid else "{single_query}")
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)),
            "ydhl_patients": executor.submit(timed_execution, "妇产科 护理单元患者情况 ydhl sql-17 sql_ydhl ",
                                             global_tools.call_new_his, reg_sqls.get(17).get('sql_ydhl')
                                             .replace("--and", "and" if pid else "--and")
                                             .replace("{single_query}", pid if pid else "{single_query}")
                                             .replace("{trunc}", trunc)
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end), 'ydhl', None),
            "chuyuan_ydhl": executor.submit(discharge_situation),

            "youchuang_pg": executor.submit(timed_execution, "妇产科 有创 pg sql-27 sql_nhis ",
                                            global_tools.call_new_his_pg, reg_sqls.get(27).get('sql_nhis')
                                            .replace("--and", "and" if pid else "--and")
                                            .replace("{single_query}", pid if pid else "{single_query}")
                                            .replace("{start_time}", shift_start)
                                            .replace("{end_time}", shift_end)
                                            .replace("{病区id}",
                                                     ', '.join(f"'{item}'" for item in ['1000961']))),
            "youchuang_ydhl": executor.submit(timed_execution, "妇产科 有创 ydhl sql-27 sql_ydhl",
                                              global_tools.call_new_his, reg_sqls.get(27).get('sql_ydhl')
                                              .replace("--and", "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}")
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end), 'ydhl', None)
        }
        if int(shift_classes) == 3 and not flush:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "妇产科 特殊患者床位信息 sql-9 sql_nhis ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(9).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "妇产科 特殊患者床位信息 sql-9 sql_ydhl ",
                                                       global_tools.call_new_his, reg_sqls.get(9).get('sql_ydhl'),
                                                       'ydhl', None)
            if shoushu:
                tasks["shuhou_patients"] = executor.submit(postoperative_situation, 3, ['1000961'],
                                                           [item.get('bingrenzyid') for item in shoushu])

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        pg_patients = results["pg_patients"]
        ydhl_patients = results["ydhl_patients"]
        shuhou_patients = results.get("shuhou_patients", [])
        chuyuan_ydhl = results.get("chuyuan_ydhl")
        youchuang_pg = results["youchuang_pg"]
        youchuang_ydhl = results["youchuang_ydhl"]

    # 查询预术手术患者
    yu_shoushus = handle_shoushu_and_yushu(reg_sqls, time_slot, ['1000961'], pid)
    if yu_shoushus:
        shoushu_count, yushu_count = 0, 0
        for item in yu_shoushus:
            if item.get('患者类别') == '手术':
                shoushu_count += 1
            else:
                yushu_count += 1
        patient_count.append({"患者类别": '预术', "人数": yushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000961', "所在病区": '妇产科护理单元'})
        patient_count.append({"患者类别": '手术', "人数": shoushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000961', "所在病区": '妇产科护理单元'})

    if chuyuan_ydhl:
        for patient in teshu_patients:
            if patient.get('患者类别') == '出院':
                patient['患者情况'] = patient['患者情况'].replace('###', chuyuan_ydhl.get(patient.get('住院号'), ''))

    all_patient_info = teshu_patients if teshu_patients else []
    all_patient_info = all_patient_info + handle_youchuang(youchuang_pg, youchuang_ydhl)
    all_patient_info = all_patient_info + yu_shoushus

    # 合并患者情况
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    # 特需病区 ydhl和his中的名字不一致需要特殊处理
                    if ydhl_patient.get("所在病区") == patient.get("所在病区") or \
                            (ydhl_patient.get("所在病区", '').__contains__('特需病区护理单元')
                             and patient.get("所在病区", '').__contains__('特需病区护理单元')):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000961', "所在病区": '妇产科护理单元'})
    patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count + ['顺生'], 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000961"], pid)
    all_patients = merge_patient_shuhou_data(shuhou_patients, all_patients, shoushu, pid)
    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2, flush, pid)
    logger.info(f"妇产科 交接班数据查询完成 ✅ 总耗时: {time.time() - start}")


"""重症科室 1000962 交班信息查询"""
def icu_shift_change(reg_sqls, shift_classes, time_slot, flush: bool = False, pid: str = None, pzyid: str = None):
    if int(shift_classes) == 1:
        trunc = '1020'
    elif int(shift_classes) == 2:
        trunc = '1290'
    else:
        trunc = '420'
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                    f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}' and ward_id = 1000962"
        all_cvs = db.query_all(query_sql)

    patient_count, teshu_patients, chuangwei_info1, chuangwei_info2, temp_patients, chuyuan_ydhl, pg_patients, ydhl_patients, zz_data  = [], [], [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "patient_count": executor.submit(timed_execution, "ICU 护理单元 患者人数统计 sql-6 sql_nhis ",
                                             global_tools.call_new_his_pg, reg_sqls.get(6).get('sql_nhis')
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end)),
            "teshu_patients": executor.submit(timed_execution, "ICU 护理单元 出院转出死亡患者情况 sql-18 sql_nhis ",
                                              global_tools.call_new_his_pg, reg_sqls.get(18).get('sql_nhis')
                                              .replace("--and", "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}")
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end)),
            "chuyuan_ydhl": executor.submit(discharge_situation),

            "pg_patients": executor.submit(timed_execution, "ICU 护理单元患者情况 pg sql-20 sql_base ",
                                           global_tools.call_new_his_pg, reg_sqls.get(20).get('sql_base')
                                           .replace("--and", "and" if pid else "--and")
                                           .replace("{single_query}", pid if pid else "{single_query}")
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)),

            "ydhl_patients": executor.submit(timed_execution, "ICU 护理单元患者情况 ydhl sql-20 sql_ydhl ",
                                             global_tools.call_new_his, reg_sqls.get(20).get('sql_ydhl')
                                             .replace("--and", "and" if pid else "--and")
                                             .replace("{single_query}", pid if pid else "{single_query}")
                                             .replace("{start_time}", shift_start)
                                             .replace("{end_time}", shift_end), 'ydhl', None),

            "zz_data": executor.submit(timed_execution, "ICU 护理单元护理记录 sql-20 sql_zz",
                                       global_tools.call_query_sqlserver, reg_sqls.get(20).get('sql_zz')
                                       .replace("--and", "and" if pzyid else "--and")
                                       .replace("{single_query}", pzyid if pzyid else "{single_query}")
                                       .replace("{trunc}", trunc)
                                       .replace("{start_time}", shift_start)
                                       .replace("{end_time}", shift_end)),
        }
        if int(shift_classes) == 3 and not flush:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "ICU 护理单元 特殊患者床位信息 sql-10 sql_nhis ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(10).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "ICU 护理单元 特殊患者床位信息 sql-10 sql_ydhl ",
                                                       global_tools.call_new_his, reg_sqls.get(10).get('sql_ydhl'),
                                                       'ydhl',
                                                       None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results["patient_count"]
        teshu_patients = results["teshu_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        chuyuan_ydhl = results.get("chuyuan_ydhl", [])
        pg_patients = results.get("pg_patients", [])
        ydhl_patients = results.get("ydhl_patients", [])
        zz_data = results.get("zz_data", [])

    if chuyuan_ydhl:
        for patient in teshu_patients:
            if patient.get('患者类别') == '出院':
                patient['患者情况'] = patient['患者情况'].replace('###', chuyuan_ydhl.get(patient.get('住院号'), ''))

    all_patient_info = teshu_patients if teshu_patients else []

    # 合并患者情况
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key =  (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                tmp_info = tmp_info + (
                    str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    # 查询预术手术患者
    yu_shoushus = handle_shoushu_and_yushu(reg_sqls, time_slot, ['1000962'], pid)
    if yu_shoushus:
        shoushu_count, yushu_count = 0, 0
        for item in yu_shoushus:
            if item.get('患者类别') == '手术':
                shoushu_count += 1
            else:
                yushu_count += 1
        patient_count.append({"患者类别": '预术', "人数": yushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000962', "所在病区": 'ICU护理单元'})
        patient_count.append({"患者类别": '手术', "人数": shoushu_count, "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000962', "所在病区": 'ICU护理单元'})

    if all_cvs:
        patient_count.append({"患者类别": '危急值', "人数": len(all_cvs), "所在科室id": 0, "所在科室": '',
                              "所在病区id": '1000962', "所在病区": 'ICU护理单元'})
    patient_count = fill_missing_types(patient_count, shift_change_config.ward_people_count, 2)

    all_patients = merge_patient_cv_data(all_cvs, all_patient_info, 2, ["1000962"], pid)
    all_patients = all_patients + yu_shoushus

    zz_patients = {item.get('住院id'): item.get('记录内容') for item in zz_data}
    for item in all_patients:
        if item.get('bingrenzyid') in zz_patients:
            item['患者情况'] = item.get('患者情况', '') + zz_patients.get(item.get('bingrenzyid'), '')

    save_data(f"2-{shift_classes}", all_patients, patient_count, chuangwei_info1 + chuangwei_info2, flush, pid)
    logger.info(f"ICU 护理单元 交接班数据查询完成 ✅ 耗时: {time.time() - start}")


"""普通科室交接班数据查询"""
def general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list, shoushu, flush: bool = False,
                              pid: str = None):
    if int(shift_classes) == 1:
        trunc = '17'
    elif int(shift_classes) == 2:
        trunc = '21.5'
    else:
        trunc = '7'
    if not dept_list:
        return
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    ydhl_dept_list = [shift_change_config.ydhl_dept_dict.get(str(did)) for did in dept_list]
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        query_sql = f"select * from nsyy_gyl.cv_info where patient_type = 3 " \
                    f"and alertdt >= '{shift_start}' and alertdt <= '{shift_end}'"
        all_cvs = db.query_all(query_sql)


    non_teshu_sql = reg_sqls.get(12).get('sql_ydhl')
    teshu_sql = reg_sqls.get(13).get('sql_ydhl')
    if len(dept_list) == 1 and str(dept_list[0]) == '1001005':
        non_teshu_sql = reg_sqls.get(32).get('sql_ydhl')
        teshu_sql = reg_sqls.get(33).get('sql_ydhl')

    patient_count, siwang_patients, chuangwei_info1, chuangwei_info2, youchuang_pg, youchuang_ydhl, \
        teshu_ydhl_patients, teshu_pg_patients, ydhl_patients_other, pg_patients, \
        eye_pg_patients, eye_ydhl_patients, shuhou_patients, chuyuan_ydhl, zhongyi_pg_patients, zhongyi_ydhl_patients \
        = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []
    with ThreadPoolExecutor(max_workers=12) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "siwang_patients": executor.submit(timed_execution, "普通病区 出院转出死亡患者情况 sql-11 sql_nhis ",
                                               global_tools.call_new_his_pg, reg_sqls.get(11).get('sql_nhis')
                                               .replace("{特殊病区}",
                                                        """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元'""")
                                               .replace("--and", "and" if pid else "--and")
                                               .replace("{single_query}", pid if pid else "{single_query}")
                                               .replace("{start_time}", shift_start)
                                               .replace("{end_time}", shift_end)),
            "teshu_ydhl_patients": executor.submit(timed_execution, "普通病区 患者信息(特殊处理) ydhl sql-33 sql_ydhl ",
                                                   global_tools.call_new_his, teshu_sql
                                                   .replace("--and", "and" if pid else "--and")
                                                   .replace("{single_query}", pid if pid else "{single_query}")
                                                   .replace("{trunc}", trunc)
                                                   .replace("{病区id}",
                                                            ', '.join(f"'{item}'" for item in ydhl_dept_list))
                                                   .replace("{start_time}", shift_start)
                                                   .replace("{end_time}", shift_end),
                                                   'ydhl', ['患者情况']),
            "teshu_pg_patients": executor.submit(timed_execution, "普通病区 患者信息(特殊处理) pg sql-13 sql_nhis",
                                                 global_tools.call_new_his_pg, reg_sqls.get(13).get('sql_nhis')
                                                 .replace("--and", "and" if pid else "--and")
                                                 .replace("{single_query}", pid if pid else "{single_query}")
                                                 .replace("{start_time}", shift_start)
                                                 .replace("{end_time}", shift_end)
                                                 .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "pg_patients": executor.submit(timed_execution, "普通病区 患者信息 pg sql-12 sql_base",
                                           global_tools.call_new_his_pg, reg_sqls.get(12).get('sql_base')
                                           .replace("--and", "and" if pid else "--and")
                                           .replace("{single_query}", pid if pid else "{single_query}")
                                           .replace("{start_time}", shift_start)
                                           .replace("{end_time}", shift_end)
                                           .replace("{特殊病区}",
                                                    """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元','眼科护理单元','中医科/风湿免疫科护理单元'""")
                                           .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list))),
            "ydhl_patients_other": executor.submit(timed_execution, "普通病区 患者信息 ydhl sql-32 sql_ydhl 其他类型",
                                                   global_tools.call_new_his, non_teshu_sql
                                                   .replace("--and", "and" if pid else "--and")
                                                   .replace("{single_query}", pid if pid else "{single_query}")
                                                   .replace("{特殊病区}",
                                                            """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元','眼科护理单元','中医科/风湿免疫科护理单元'""")
                                                   .replace("{trunc}", trunc)
                                                   .replace("{病区id}",
                                                            ', '.join(f"'{item}'" for item in ydhl_dept_list))
                                                   .replace("{start_time}", shift_start)
                                                   .replace("{end_time}", shift_end)
                                                   , 'ydhl', None),
            "chuyuan_ydhl": executor.submit(discharge_situation),
            "youchuang_pg": executor.submit(timed_execution, "普通病区 有创 pg sql-27 sql_nhis ",
                                            global_tools.call_new_his_pg, reg_sqls.get(27).get('sql_nhis')
                                            .replace("--and", "and" if pid else "--and")
                                            .replace("{single_query}", pid if pid else "{single_query}")
                                            .replace("{start_time}", shift_start)
                                            .replace("{end_time}", shift_end)
                                            .replace("{病区id}",
                                                     ', '.join(f"'{item}'" for item in dept_list))),
            "youchuang_ydhl": executor.submit(timed_execution, "普通病区 有创 ydhl sql-27 sql_ydhl",
                                              global_tools.call_new_his, reg_sqls.get(27).get('sql_ydhl')
                                              .replace("--and", "and" if pid else "--and")
                                              .replace("{single_query}", pid if pid else "{single_query}")
                                              .replace("{start_time}", shift_start)
                                              .replace("{end_time}", shift_end), 'ydhl', None)

        }
        if not flush:
            tasks["patient_count"] = executor.submit(timed_execution, "普通病区 患者人数统计 sql-3 sql_nhis ",
                                                     global_tools.call_new_his_pg, reg_sqls.get(3).get('sql_nhis')
                                                     .replace("{特殊病区}",
                                                              """'ICU护理单元','CCU护理单元','AICU护理单元','妇产科护理单元'""")
                                                     .replace("{start_time}", shift_start)
                                                     .replace("{end_time}", shift_end)
                                                     .replace("{病区id}", ', '.join(f"'{item}'" for item in dept_list)))
        if int(shift_classes) == 3 and not flush:
            tasks["chuangwei_info1"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 sql-4 sql_nhis ",
                                                       global_tools.call_new_his_pg, reg_sqls.get(4).get('sql_nhis'))
            tasks["chuangwei_info2"] = executor.submit(timed_execution, "普通病区 特殊患者床位信息 sql-4 sql_ydhl ",
                                                       global_tools.call_new_his, reg_sqls.get(4).get('sql_ydhl'),
                                                       'ydhl', None)
            if shoushu:
                dept_set = set()
                for item in shoushu:
                    dept_set.add(item.get('patient_ward_id'))
                tasks["shuhou_patients"] = executor.submit(postoperative_situation, 3, list(dept_set),
                                                           [item.get('bingrenzyid') for item in shoushu])
        # 眼科特殊处理入院
        if '1000977' in dept_list:
            tasks["eye_pg_patients"] = executor.submit(timed_execution, "眼科病区 患者信息 pg sql-19 sql_base",
                                                       global_tools.call_new_his_pg, reg_sqls.get(19).get('sql_base')
                                                       .replace("--and", "and" if pid else "--and")
                                                       .replace("{single_query}", pid if pid else "{single_query}")
                                                       .replace("{start_time}", shift_start)
                                                       .replace("{end_time}", shift_end))
            tasks["eye_ydhl_patients"] = executor.submit(timed_execution, "眼科病区 患者信息 ydhl sql-19 sql_ydhl",
                                                         global_tools.call_new_his, reg_sqls.get(19).get('sql_ydhl')
                                                         .replace("--and", "and" if pid else "--and")
                                                         .replace("{single_query}", pid if pid else "{single_query}")
                                                         .replace("{trunc}", trunc)
                                                         .replace("{start_time}", shift_start).replace("{end_time}",
                                                                                                       shift_end)
                                                         , 'ydhl', None)

        # 中医科特殊处理入院 （和上面眼科逻辑一样）
        if '1001028' in dept_list:
            tasks["zhongyi_pg_patients"] = executor.submit(timed_execution, "中医科/风湿免疫科 患者信息 pg sql-25 sql_base",
                                                           global_tools.call_new_his_pg,
                                                           reg_sqls.get(25).get('sql_base')
                                                           .replace("--and", "and" if pid else "--and")
                                                           .replace("{single_query}", pid if pid else "{single_query}")
                                                           .replace("{start_time}", shift_start)
                                                           .replace("{end_time}", shift_end))
            tasks["zhongyi_ydhl_patients"] = executor.submit(timed_execution, "中医科/风湿免疫科 患者信息 ydhl sql-25 sql_ydhl",
                                                             global_tools.call_new_his, reg_sqls.get(25).get('sql_ydhl')
                                                             .replace("--and", "and" if pid else "--and")
                                                             .replace("{single_query}",
                                                                      pid if pid else "{single_query}")
                                                             .replace("{trunc}", trunc)
                                                             .replace("{start_time}", shift_start).replace("{end_time}",
                                                                                                           shift_end)
                                                             , 'ydhl', None)

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        patient_count = results.get("patient_count", [])
        siwang_patients = results["siwang_patients"]
        chuangwei_info1 = results.get("chuangwei_info1", [])
        chuangwei_info2 = results.get("chuangwei_info2", [])
        teshu_ydhl_patients = results["teshu_ydhl_patients"]
        teshu_pg_patients = results["teshu_pg_patients"]
        ydhl_patients_other = results["ydhl_patients_other"]
        pg_patients = results["pg_patients"]
        eye_pg_patients = results.get("eye_pg_patients", [])
        eye_ydhl_patients = results.get("eye_ydhl_patients", [])
        shuhou_patients = results.get("shuhou_patients", [])
        chuyuan_ydhl = results["chuyuan_ydhl"]
        zhongyi_pg_patients = results.get("zhongyi_pg_patients", [])
        zhongyi_ydhl_patients = results.get("zhongyi_ydhl_patients", [])
        youchuang_pg = results['youchuang_pg']
        youchuang_ydhl = results["youchuang_ydhl"]

    # 查询预术手术患者
    yu_shoushus = handle_shoushu_and_yushu(reg_sqls, time_slot, dept_list, pid)
    if yu_shoushus and not flush:
        yu_shoushus_group = defaultdict(list)
        for ite in yu_shoushus:
            yu_shoushus_group[ite.get('所在病区')].append(ite)

        for key, value in yu_shoushus_group.items():
            shoushu_count, yushu_count = 0, 0
            for it in list(value):
                if it.get('患者类别') == '手术':
                    shoushu_count += 1
                else:
                    yushu_count += 1
            patient_count.append({"患者类别": '预术', "人数": yushu_count, "所在科室id": 0, "所在科室": '',
                                  "所在病区id": str(shift_change_config.his_dept_dict.get(key)), "所在病区": key})
            patient_count.append({"患者类别": '手术', "人数": shoushu_count, "所在科室id": 0, "所在科室": '',
                                  "所在病区id": str(shift_change_config.his_dept_dict.get(key)), "所在病区": key})

    if chuyuan_ydhl:
        for patient in siwang_patients:
            if patient.get('患者类别') == '出院':
                patient['患者情况'] = patient['患者情况'].replace('###', chuyuan_ydhl.get(patient.get('住院号'), ''))

    all_patient_info = siwang_patients
    all_patient_info = all_patient_info + handle_youchuang(youchuang_pg, youchuang_ydhl)
    all_patient_info = all_patient_info + yu_shoushus
    teshu_pg_patient_dict = {}
    for patient in teshu_pg_patients:
        teshu_pg_patient_dict[patient['bingrenzyid']] = patient
    for item in teshu_ydhl_patients:
        p = teshu_pg_patient_dict.get(item.get('bingrenzyid'))
        if not p:
            continue
        p['患者情况'] = item.get('患者情况', '')
        all_patient_info.append(p)

    # 分组
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    ydhl_patients = ydhl_patients_other
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    # 特需病区 ydhl和his中的名字不一致需要特殊处理
                    if ydhl_patient.get("所在病区") == patient.get("所在病区") or \
                            (ydhl_patient.get("所在病区", '').__contains__('特需病区护理单元')
                             and patient.get("所在病区", '').__contains__('特需病区护理单元')):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        all_patient_info.append(patient)

    if eye_pg_patients:
        all_patient_info = all_patient_info + handle_ruyuan_patient(eye_ydhl_patients, eye_pg_patients)
    if zhongyi_pg_patients:
        all_patient_info = all_patient_info + handle_ruyuan_patient(zhongyi_ydhl_patients, zhongyi_pg_patients)

    patient_count_list = []
    if not flush:
        filtered_patient_count = [dept for dept in patient_count if dept['所在病区id'] in dept_list]
        patient_count_list = fill_missing_types(filtered_patient_count, shift_change_config.ward_people_count, 2)

    # 需要将移动护理id 转为his id
    for item in chuangwei_info2:
        item['所在病区id'] = str(shift_change_config.his_dept_id_dict.get(item['所在病区id'], ''))
    chuangwei_info_list = chuangwei_info1 + chuangwei_info2
    filtered_chuangwei_info = [dept for dept in chuangwei_info_list if dept['所在病区id'] in dept_list]

    filtered_patients = [dept for dept in all_patient_info if dept['所在病区id'] in dept_list]
    all_patients = merge_patient_cv_data(all_cvs, filtered_patients, 2, dept_list, pid)
    all_patients = merge_patient_shuhou_data(shuhou_patients, all_patients, shoushu, pid)
    save_data(f"2-{shift_classes}", all_patients, patient_count_list, filtered_chuangwei_info, flush, pid)
    logger.info(f"普通科室 {','.join(dept_list)} 通用交接班数据查询完成 ✅ 耗时: {time.time() - start}")


"""预术/手术统一处理逻辑 TODO sql 28 nhis base 待优化"""
def handle_shoushu_and_yushu(reg_sqls, time_slot, dept_list, pid: str = None):
    start_time = time.time()
    start = start_time
    shift_start, shift_end = get_complete_time_slot(time_slot)

    ydhl_dept_list = [shift_change_config.ydhl_dept_dict.get(str(did)) for did in dept_list]
    nhis_data, base_data, ydhl_data, zz_data = [], [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（添加时间统计）
        tasks = {
            "nhis_data": executor.submit(timed_execution, "预术及手术患者基本信息 sql-28 sql_nhis",
                                         global_tools.call_new_his_pg, reg_sqls.get(28).get('sql_nhis')
                                         .replace("--and", "and" if pid else "--and")
                                         .replace("{single_query}", pid if pid else "{single_query}")
                                         .replace("{start_time}", shift_start)
                                         .replace("{end_time}", shift_end).replace("{病区id}",
                                                                                   ', '.join(f"'{item}'" for item in
                                                                                             dept_list))),

            "base_data": executor.submit(timed_execution, "pg在院患者本班手术结束时间 sql-28 sql_base",
                                         global_tools.call_new_his_pg, reg_sqls.get(28).get('sql_base')
                                         .replace("--and", "and" if pid else "--and")
                                         .replace("{single_query}", pid if pid else "{single_query}")
                                         .replace("{start_time}", shift_start)
                                         .replace("{end_time}", shift_end).replace("{病区id}",
                                                                                   ', '.join(f"'{item}'" for item in
                                                                                             dept_list))),
            "ydhl_data": executor.submit(timed_execution, "ydhl本班手术结束时间 sql-28 sql_ydhl",
                                         global_tools.call_new_his, reg_sqls.get(28).get('sql_ydhl')
                                         .replace("--and", "and" if pid else "--and")
                                         .replace("{single_query}", pid if pid else "{single_query}")
                                         .replace("{start_time}", shift_start)
                                         .replace("{end_time}", shift_end).replace("{病区id}",
                                                                                   ', '.join(f"'{item}'" for item in
                                                                                             ydhl_dept_list)), 'ydhl',
                                         []),
            "zz_data": executor.submit(timed_execution, "手术患者情况 sql-28 sql_zz",
                                       global_tools.call_new_his, reg_sqls.get(28).get('sql_zz')
                                       .replace("--and", "and" if pid else "--and")
                                       .replace("{single_query}", pid if pid else "{single_query}")
                                       .replace("{start_time}", shift_start)
                                       .replace("{end_time}", shift_end), 'ydhl', []),
        }

        # 获取结果（会自动等待所有任务完成）
        results = {name: future.result() for name, future in tasks.items()}
        # 解包结果
        nhis_data = results["nhis_data"]
        base_data = results["base_data"]
        ydhl_data = results["ydhl_data"]
        zz_data = results["zz_data"]

    patient_infos = {}
    for item in nhis_data:
        patient_infos[(str(item.get('病人id')), str(item.get('主页id')))] = item

    # 按照患者病人id 主页id 手术结束时间排序 升序
    def sort_key(record):
        end_time = record['本班手术结束时间'] if record['本班手术结束时间'] else record['最大手术结束时间']
        time_key = end_time
        if end_time is None or end_time == '':
            time_key = ''
        return (str(record['病人id']), str(record['主页id']), time_key)

    shoushu_list = sorted(base_data + ydhl_data, key=sort_key)

    # 记录每位患者最晚的手术结束时间
    shoushu_dict = {}
    for item in shoushu_list:
        end_time = item['本班手术结束时间'] if item['本班手术结束时间'] else item['最大手术结束时间']
        shoushu_dict[(str(item.get('病人id')), str(item.get('主页id')))] = end_time

    def is_time1_before_time2(time_str1, time_str2):
        """
        判断第一个时间字符串是否早于第二个时间字符串

        参数:
            time_str1 (str): 第一个时间字符串，格式为 'YYYY-MM-DD HH:MM:SS'
            time_str2 (str): 第二个时间字符串，格式为 'YYYY-MM-DD HH:MM:SS'

        返回:
            bool: 如果 time_str1 < time_str2 返回 True，否则返回 False
            str: 错误信息（如果发生错误）
        """
        try:
            # 将时间字符串转换为 datetime 对象
            time1 = datetime.strptime(time_str1, '%Y-%m-%d %H:%M:%S')
            time2 = datetime.strptime(time_str2, '%Y-%m-%d %H:%M:%S')

            # 比较两个时间
            return time1 < time2
        except Exception as e:
            return False

    # 移除预术时间早于手术结束时间的预术记录
    yushus = []
    for item in nhis_data:
        # print(item)
        patient_id = item.get('病人id')
        main_id = item.get('主页id')
        if (str(patient_id), str(main_id)) in shoushu_dict \
                and is_time1_before_time2(item.get('预术时间'), shoushu_dict.get((str(patient_id), str(main_id)))) \
                and item.get('预术标志') == 1:
            continue

        item['患者情况'] = f"患者 {item.get('患者情况', '')} , 积极术前准备, 待术中。"
        yushus.append(item)

    # 补充手术患者信息
    shoushus = []
    for item in shoushu_list:
        if not item.get('本班手术结束时间'):
            continue
        p_info = patient_infos.get((str(item.get('病人id')), str(item.get('主页id'))))
        if not p_info:
            continue
        item['患者类别'] = "手术"
        item['bingrenzyid'] = p_info.get('bingrenzyid')
        item['床号'] = p_info.get('床号')
        item['姓名'] = p_info.get('姓名')
        item['住院号'] = p_info.get('住院号')
        item['性别'] = p_info.get('性别')
        item['年龄'] = p_info.get('年龄')
        item['所在病区'] = p_info.get('所在病区')
        item['所在病区id'] = p_info.get('所在病区id')
        item['主治医生姓名'] = p_info.get('主治医生姓名')
        item['患者情况'] = ''
        item['主要诊断'] = p_info.get('主要诊断')
        shoushus.append(item)

    # 合并同一个人的多个手术信息 赋值给第一个手术记录
    shoushu_info = sorted(zz_data, key=lambda x: (str(x["病人id"]), str(x["主页id"])))
    for key, group in groupby(shoushu_info, key=lambda x: (str(x["病人id"]), str(x["主页id"]))):
        infos = '; '.join(record['患者情况'] for record in list(group))
        for item in shoushus:
            if (str(item.get('病人id')), str(item.get('主页id'))) == key:
                item['患者情况'] = infos
                break

    records = yushus + shoushus
    # 合并相同患者类别和病人ID的记录，合并患者情况字段
    merged_records = {}
    for record in records:
        if '预术标志' in record and record['预术标志'] == 0:
            continue
        # 使用患者类别和病人ID作为合并的关键
        key = (record.get('患者类别', ''), record.get('bingrenzyid', ''))
        if key in merged_records:
            # 如果已存在相同患者类别和病人ID的记录，合并患者情况
            existing_record = merged_records[key]
            # 合并患者情况，用换行符分隔
            if record.get('患者情况'):
                if existing_record['患者情况']:
                    existing_record['患者情况'] += '\n\n' + record['患者情况']
                else:
                    existing_record['患者情况'] = record['患者情况']
        else:
            # 否则创建新记录（深拷贝避免修改原记录）
            merged_records[key] = record.copy()

    tmp_list = list(merged_records.values())
    finish_list = []
    for item in tmp_list:
        if item.get('预术标志', 1) == 0:
            continue
        finish_list.append(item)
    return finish_list


"""处理入院患者"""
def handle_ruyuan_patient(ydhl_patients, pg_patients):
    ret_data = []

    # 分组
    def key_func(x):
        return (x.get("病人id"), x.get("主页id"), x.get("标识"))

    groups = defaultdict(list)
    for patient in ydhl_patients:
        groups[key_func(patient)].append(patient)

    for patient in pg_patients:
        key = (patient.get("病人id"), str(patient.get("主页id")), '病危重') if patient.get("患者类别") in ['病危',
                                                                                                           '病重'] \
            else (patient.get("病人id"), str(patient.get("主页id")), patient.get("患者类别"))
        tmp_info = patient.get("患者情况", '') if patient.get("患者情况", '') else ''
        ydhl_list = groups.get(key)
        if ydhl_list:
            for ydhl_patient in ydhl_list:
                if patient.get("患者类别") == '转入':
                    if ydhl_patient.get("所在病区") == patient.get("所在病区") or \
                            (ydhl_patient.get("所在病区", '').__contains__('特需病区护理单元')
                             and patient.get("所在病区", '').__contains__('特需病区护理单元')):
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                        continue
                elif patient.get("患者类别") == '入院':
                    split_info = tmp_info.split('###')
                    if len(split_info) == 1:
                        tmp_info = tmp_info + (
                            str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
                    else:
                        tmp_info = split_info[0] + str(ydhl_patient.get("患者情况", '')).replace('***', split_info[1])
                else:
                    tmp_info = tmp_info + (
                        str(ydhl_patient.get("患者情况", '')) if ydhl_patient.get("患者情况", '') else '')
        patient['患者情况'] = tmp_info
        ret_data.append(patient)
    return ret_data


"""处理有创数据"""
def handle_youchuang(youchuang_pg, youchuang_ydhl):
    if not youchuang_pg:
        return []

    def key_func(x):
        return (str(x.get("病人id")), str(x.get("主页id")), x.get("时间"))

    groups = defaultdict()
    for patient in youchuang_ydhl:
        groups[key_func(patient)] = patient.get("患者情况", '')

    for patient in youchuang_pg:
        person_key = (str(patient.get("病人id")), str(patient.get("主页id")), patient.get('时间'))
        if person_key in groups:
            patient['患者情况'] = patient.get('患者情况') + groups.get(person_key, '')
    return youchuang_pg


def get_complete_time_slot(shift_slot: str) -> tuple:
    """根据输入的时间段返回完整的开始和结束时间"""
    start_str, end_str = shift_slot.split('-')
    start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
    end_time = datetime.strptime(end_str.strip(), '%H:%M').time()

    # 获取当前日期
    today = datetime.now().date()

    # 判断是否需要跨天
    if start_time < end_time:
        # 同一天内
        start_datetime = datetime.combine(today, start_time)
        end_datetime = datetime.combine(today, end_time)
    else:
        # 跨天情况（开始时间是前一天）
        start_datetime = datetime.combine(today - timedelta(days=1), start_time)
        end_datetime = datetime.combine(today, end_time)

    return f"{start_datetime.strftime('%Y-%m-%d %H:%M')}:01.000", f"{end_datetime.strftime('%Y-%m-%d %H:%M')}:00.999"


"""护理交接班数据 同一个人有多条记录时，合并为一条"""
def merge_patient_records(patient_list):
    """
    合并相同患者的记录（根据shift_date, shift_classes, zhuyuanhao, ward_id）
    合并规则：
    - patient_type 用逗号连接
    - patient_info 用换行符连接
    - 其他字段保留第一条记录的值
    """

    patient_list = sorted(patient_list, key=lambda x: PATIENT_TYPE_ORDER.get(x[9], float('inf')))

    # 使用复合键分组
    def key_func(x):
        # shift_date, shift_classes, zhuyuanhao, ward_id
        return (x[0], x[1], x[3], x[12])

    # 分组s
    groups = defaultdict(list)
    for patient in patient_list:
        groups[key_func(patient)].append(patient)

    merged_records = []
    # 合并每组记录
    for group_key, patients in groups.items():
        if len(patients) == 1:
            merged_records.append(patients[0])
            continue

        # 合并字段 如果有出院 诊断从出院中取
        base_patient = patients[0]
        bed = base_patient[4]
        for item in patients:
            if str(item[9]).__contains__('出院'):
                base_patient = item
            if str(item[9]).__contains__('转出'):
                bed = item[4]

        # 合并patient_type（去重）
        types = set()
        for p in patients:
            if p[9]:
                for type_part in p[9].split(','):
                    type_clean = type_part.strip()
                    if type_clean:
                        types.add(type_clean)
        # types = {p[9] for p in patients if p[9]}
        sorted_types = sorted(types, key=lambda x: PATIENT_TYPE_ORDER.get(x, float('inf')))
        merged_type = ', '.join(sorted_types) if sorted_types else base_patient[9]

        # 按时间排序后合并info
        try:
            sorted_patients = sorted(patients,
                                     key=lambda x: datetime.strptime(x[16], '%Y-%m-%d %H:%M:%S'))
            bingzhong_info, merged_info = '', ''
            for p in sorted_patients:
                if p[15]:
                    if p[9] and (p[9].__contains__('病重') or p[9].__contains__('病危') or p[9].__contains__('病危重')):
                        bingzhong_info = bingzhong_info + p[15]
                        continue
                    merged_info = merged_info + p[15] + '\n\n--------\n\n'
            merged_info = merged_info + bingzhong_info
            # merged_info = '\n\n--------\n\n'.join(f"{p[15]}" for p in sorted_patients if p[15])
            latest_time = sorted_patients[-1][16]
        except (IndexError, ValueError) as e:
            logger.warning(f"处理记录时出错: {e}")
            merged_info = "合并记录时发生错误"
            latest_time = base_patient[16]

        # 构建合并后的新元组（保持原始结构）
        base_patient = (
            base_patient[0],  # shift_date
            base_patient[1],  # shift_classes
            base_patient[2],  # bingrenzyid
            base_patient[3],  # zhuyuanhao
            bed,  # bed_no
            base_patient[5],  # patient_name
            base_patient[6],  # patient_sex
            base_patient[7],  # patient_age
            base_patient[8],  # zhenduan
            merged_type,  # patient_type (合并后)
            base_patient[10],  # patient_dept_id
            base_patient[11],  # patient_dept
            base_patient[12],  # patient_ward_id
            base_patient[13],  # patient_ward
            base_patient[14],  # doctor_name
            merged_info,  # patient_info (合并后)
            latest_time,  # create_at (取最新)
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # update_at
            base_patient[18],
        )
        merged_records.append(base_patient)

    return merged_records


"""查询危急值患者诊断"""
def query_cv_zhenduan(zhuyuanhao_list):
    start_time = time.time()
    id_list = ','.join(f"'{zhuyuanhao}'" for zhuyuanhao in zhuyuanhao_list)
    sql = f"""
            select zb.zhuyuanhao 住院号, zb.bingrenid "病人id", zb.bingrenzyid, case when (xpath('string(//node[@name="初步诊断"])', 
            wb2.wenjiannr::xml))[1]::text ~ '2[\.、]' then regexp_replace((xpath('string(//node[@name="初步诊断"])', 
            wb2.wenjiannr::xml))[1]::text, '2[\.、].*$', '\1') else (xpath('string(//node[@name="初步诊断"])', 
            wb2.wenjiannr::xml))[1]::text end as 主要诊断 from df_bingli.ws_binglijl wb 
            join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid
            join df_jj_zhuyuan.zy_bingrenxx zb on zb.bingrenzyid=wb.bingrenzyid and zb.zaiyuanzt=0 and zb.rukebz=1 
            and zb.yingerbz=0 and zb.quxiaorybz=0 where wb.binglimc = '首次病程记录'  and wb.zuofeibz=0 and wb.wenshuzt=2
            and zb.zhuyuanhao in ({id_list})
            """
    ret = global_tools.call_new_his_pg(sql)
    if not ret:
        return {}
    ret = {str(r.get("住院号")): r for r in ret}
    logger.debug(f"查询危机值数据完成耗时: {time.time() - start_time}")
    return ret


"""合并交接班危机值数据"""
def merge_patient_cv_data(cv_list, patient_list, shift_type, dept_list, pid: str = None):
    try:
        if not cv_list or not patient_list:
            return patient_list

        # 查询危机值患者诊断
        zhuyuanhao_list = [str(cv.get('patient_treat_id')) for cv in cv_list if cv.get('patient_treat_id')]
        cv_zhenduan = query_cv_zhenduan(zhuyuanhao_list)

        cv_dict = {}
        if int(shift_type) == 1:
            for cv in cv_list:
                if cv.get('dept_id') and cv.get('patient_treat_id'):
                    key = (str(cv['patient_treat_id']), str(cv['dept_id']))
                    if key not in cv_dict:
                        cv_dict[key] = []  # 初始化列表
                    cv_dict[key].append(cv)
        else:
            for cv in cv_list:
                if cv.get('ward_id') and cv.get('patient_treat_id'):
                    key = (str(cv['patient_treat_id']), str(cv['ward_id']))
                    if key not in cv_dict:
                        cv_dict[key] = []
                    cv_dict[key].append(cv)

        patient_dict = defaultdict(list)
        for patient in patient_list:
            if pid and str(pid) != str(patient.get('病人id')):
                continue
            key = (str(patient.get('住院号')), str(patient.get('所在病区id'))) if int(shift_type) == 2 \
                else (str(patient.get('住院号')), str(patient.get('所在科室id')))
            patient_dict[key].append(patient)

        for (zhuyuanhao, dpid), cvs in cv_dict.items():
            cv = cvs[0]
            if str(dpid) not in dept_list or not cv or not cv.get('patient_treat_id'):
                continue

            p_info = ''
            for item in cvs:
                p_info = p_info + f"  {item.get('alertdt')} 接危急值系统报 {item.get('cv_name')} " \
                                  f"{item['cv_result'] if item.get('cv_result') else ''} " \
                                  f"{item['cv_unit'] if item.get('cv_unit') else ''}, " \
                                  f" {item.get('method') if item.get('method') else ''} "
            if patient_dict.get((zhuyuanhao, dpid)):
                ps = patient_dict.get((zhuyuanhao, dpid))
                ps[0]['患者类别'] = (ps[0].get('患者类别', '') or '') + ', 危急值'
                ps[0]['患者情况'] = (ps[0].get('患者情况', '') or '') + p_info
            else:
                sex = '未知'
                if str(cv.get('patient_gender')) == '1':
                    sex = '男'
                if str(cv.get('patient_gender')) == '2':
                    sex = '女'

                cv_pg_info = cv_zhenduan.get(zhuyuanhao, {})
                if pid and str(pid) != str(cv_pg_info.get("病人id")):
                    continue
                p = {'bingrenzyid': cv_pg_info.get("bingrenzyid", ''), '病人id': cv_pg_info.get("病人id", ''),
                     '住院号': zhuyuanhao, '床号': cv.get('patient_bed_num'),
                     '姓名': cv.get('patient_name'), '性别': sex, '年龄': cv.get('patient_age'),
                     '主要诊断': cv_pg_info.get("主要诊断", ''), '患者类别': '危急值',
                     '主治医生姓名': cv.get('req_docno'),
                     '患者情况': p_info
                     }
                if int(shift_type) == 1:
                    p['所在科室id'] = cv.get('dept_id') if cv.get('dept_id') else ''
                    p['所在科室'] = cv.get('dept_name') if cv.get('dept_name') else ''
                else:
                    p['所在病区id'] = cv.get('ward_id') if cv.get('ward_id') else ''
                    p['所在病区'] = cv.get('ward_name') if cv.get('ward_name') else ''
                patient_dict[(zhuyuanhao, dpid)].append(p)

        ret_list = []
        for l in patient_dict.values():
            ret_list = ret_list + l
        return ret_list
    except Exception as e:
        logger.warning(f"合并危机值数据异常: {e}, dept = {dept_list}")
        return patient_list


"""合并交接班术后数据"""
def merge_patient_shuhou_data(shuhou_list, patient_list, shoushu_list, pid: str = None):
    try:
        if not shuhou_list or not shoushu_list:
            return patient_list

        shuhou_dict = defaultdict(list)
        for patient in shuhou_list:
            shuhou_dict[str(patient.get('住院id'))].append(patient)
        patient_dict = defaultdict(list)
        for patient in patient_list:
            if pid and pid != str(patient.get('病人id')):
                continue
            patient_dict[str(patient.get('bingrenzyid'))].append(patient)

        for patient in shoushu_list:
            if not patient.get('bingrenzyid'):
                continue
            if pid and str(pid) != str(patient.get('病人id')):
                continue

            if patient_dict.get(str(patient.get('bingrenzyid'))):
                ps = patient_dict.get(str(patient.get('bingrenzyid')))
                info = str(shuhou_dict.get(str(patient.get('bingrenzyid')), [{}])[0].get('患者情况', ''))
                if info and info != '0':
                    ps[0]['患者情况'] = str(ps[0]['患者情况']).replace(info, '')
                ps[0]['患者情况'] = str(ps[0]['患者情况']) + info
            else:
                p_shuhou = shuhou_dict.get(str(patient.get('bingrenzyid')), '')
                if not p_shuhou:
                    continue

                p_shuhou = p_shuhou[0]
                p = {'bingrenzyid': patient.get('bingrenzyid'), '住院号': patient.get('住院号'),
                     '床号': p_shuhou.get('床号', ''), '姓名': patient.get('姓名'),
                     '性别': patient.get('性别'), '年龄': patient.get('年龄'),
                     '主要诊断': patient.get('主要诊断'), '患者类别': '',
                     '主治医生姓名': patient.get('主治医生姓名'), '患者情况': p_shuhou.get('患者情况', '')
                     }

                dept_name = p_shuhou.get('所在病区', '')
                p['所在病区id'] = shift_change_config.his_dept_dict.get(dept_name, '0')
                p['所在病区'] = dept_name
                patient_dict[str(patient.get('bingrenzyid'))].append(p)

        ret_list = []
        for l in patient_dict.values():
            ret_list = ret_list + l
        return ret_list
    except Exception as e:
        logger.warning(f"合并术后数据异常: {e}")
        return patient_list


def timed_execution(log_info, func, *args):
    """带执行时间统计的函数包装器"""
    start_time = time.time()
    result = func(*args)
    logger.debug(f"{log_info} 执行时间: {time.time() - start_time} s")
    return result


"""持久化交接班数据"""
def save_data(shift_classes, patients, patient_count, patient_bed_info, flush: bool = False, pid: str = None):
    today_date = datetime.now().strftime("%Y-%m-%d")
    if pid:
        # 如果单独刷新某一个患者，不需要更新人数和床位信息
        patient_count = []
        patient_bed_info = []
    if str(shift_classes).endswith('-3'):
        # 晚班属于前一天的交班
        today_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if flush:
            patient_count = []
            # patient_bed_info = []
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if patients:
            for item in patients:
                if item.get('患者情况'):
                    item['患者情况'] = item.get('患者情况').replace(
                        ',瞳孔:,左侧形状:,直径:,对光反应:,边缘:,右侧形状:,直径:,对光反应:,边缘:', '')

            patient_list = [(today_date, shift_classes,
                             patient.get('bingrenzyid') if patient.get('bingrenzyid') else '0',
                             patient.get('住院号') if patient.get('住院号') else '0',
                             safe_bed_no(patient.get('床号')),
                             patient.get('姓名') if patient.get('姓名') else '0',
                             patient.get('性别') if patient.get('性别') else '0',
                             patient.get('年龄') if patient.get('年龄') else '0',
                             patient.get('主要诊断') if patient.get('主要诊断') else '',
                             patient.get('患者类别') if patient.get('患者类别') else '',
                             int(patient.get('所在科室id')) if patient.get('所在科室id') else 0,
                             patient.get('所在科室') if patient.get('所在科室') else '',
                             int(patient.get('所在病区id')) if patient.get('所在病区id') else 0,
                             patient.get('所在病区') if patient.get('所在病区') else '',
                             patient.get('主治医生姓名') if patient.get('主治医生姓名') else '',
                             patient.get('患者情况') if patient.get('患者情况') else '',
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             patient.get('病人id') if patient.get('病人id') else '') for patient in patients]

            if str(shift_classes).startswith('2-'):
                patient_list = merge_patient_records(patient_list)

            logger.debug(f"保存患者列表数据: patient_id = {pid}, 数量 = {len(patients)} 合并后 = {len(patient_list)}")
            # 生成插入的 SQL
            insert_sql = f"""INSERT INTO nsyy_gyl.scs_patients(shift_date, shift_classes, bingrenzyid, 
                            zhuyuanhao, bed_no, patient_name, patient_sex, patient_age, zhenduan, patient_type, 
                            patient_dept_id, patient_dept, patient_ward_id, patient_ward, doctor_name, patient_info, 
                            create_at, update_at, patient_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                            %s, %s, %s, %s) ON DUPLICATE KEY UPDATE zhuyuanhao = VALUES(zhuyuanhao), bed_no = VALUES(bed_no), 
                            patient_name = VALUES(patient_name), patient_sex = VALUES(patient_sex), 
                            patient_age = VALUES(patient_age), zhenduan = VALUES(zhenduan), 
                            patient_type = VALUES(patient_type), patient_dept_id = VALUES(patient_dept_id), 
                            patient_dept = VALUES(patient_dept), patient_ward_id = VALUES(patient_ward_id), 
                            patient_ward = VALUES(patient_ward), doctor_name = VALUES(doctor_name), 
                            patient_info = VALUES(patient_info), update_at = VALUES(update_at), patient_id = VALUES(patient_id)"""

            db.execute_many(insert_sql, args=patient_list, need_commit=True)

        if patient_count:
            count_list = [(today_date, shift_classes, item.get('患者类别'),
                           item.get('所在科室id') if item.get('所在科室id') else 0,
                           item.get('所在科室') if item.get('所在科室') else '0',
                           item.get('所在病区id') if item.get('所在病区id') else 0,
                           item.get('所在病区') if item.get('所在病区') else '0',
                           item.get('人数'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for item in patient_count]
            insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_count(shift_date, shift_classes, patient_type, 
                            patient_dept_id, patient_dept, patient_ward_id, patient_ward, count, create_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE count = VALUES(count)"""
            db.execute_many(insert_sql, count_list, need_commit=True)

        if patient_bed_info:
            for item in patient_bed_info:
                if item.get('患者信息'):
                    try:
                        beds = re.findall(r'\d+床', item.get('患者信息'))
                        item['患者信息'] = item.get('患者信息') + f"（共计 {len(beds)} 人）"
                    except Exception as e:
                        logger.warning(f"患者信息转换异常: {e}")

            bed_info_list = [
                (today_date, shift_classes, item.get('患者类别'),
                 shift_change_config.his_dept_dict.get(item.get('所在病区'), 0),
                 item.get('所在病区'), item.get('患者信息'),
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')) for item in patient_bed_info]
            insert_sql = f"""INSERT INTO nsyy_gyl.scs_patient_bed_info(shift_date, shift_classes, 
                            patient_type, patient_ward_id, patient_ward, patient_info, create_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s) 
                            ON DUPLICATE KEY UPDATE patient_info = VALUES(patient_info)"""
            db.execute_many(insert_sql, bed_info_list, need_commit=True)


def safe_bed_no(bed_no):
    try:
        if not bed_no:
            return '0'
        bed_no = str(bed_no).replace(' ', '')
        if not bed_no:
            return '0'
        numbers = re.findall(r'\d+', bed_no)
        return ''.join(numbers)
    except Exception as e:
        logger.error(f" 床号 {bed_no} 转换异常: {e}")
        return '0'


def check_shift_time(shift_slot: str) -> bool:
    """检查当前时间是否到交班时间了"""
    if not shift_slot:
        return False

    # 解析时间区间字符串
    start_str, end_str = shift_slot.split('-')
    start = datetime.strptime(start_str.strip(), '%H:%M').time()
    end = datetime.strptime(end_str.strip(), '%H:%M').time()
    if not start or not end:
        return False

    input_time = datetime.strptime(end_str, "%H:%M").time()
    now = datetime.now()
    current_time = now.time()

    # 创建时间范围（前后2分钟）
    time_min = (now - timedelta(minutes=5)).time()
    time_max = (now + timedelta(minutes=5)).time()

    # 处理跨日情况（如23:59-00:01）
    if time_min > time_max:
        # 当前时间接近午夜，范围跨越两天
        return input_time >= time_min or input_time <= time_max
    else:
        # 正常情况
        return time_min <= input_time <= time_max


def upcoming_shifts_grouped() -> Dict[Tuple[str, str], List[Dict]]:
    # return {('1', '07:30-17:00'): [{
    #     'dept_id': '1000982',
    #     'dept_name': '特需病区护理单元1',
    #     'shift_type': 2
    # }]}
    """获取按班次分组的即将交班的科室列表"""
    now = datetime.now().time()

    # 获取所有配置
    configs = query_shift_config()

    # 使用字典按班次类型和时间段分组
    shift_groups = defaultdict(list)

    for config in configs:
        if not config.get('shift_status'):
            continue
        # 检查早班
        if config['early_shift'] and config['early_shift_slot'] and check_shift_time(config['early_shift_slot']):
            shift_key = ('1', config['early_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

        # 检查中班
        if config['middle_shift'] and config['middle_shift_slot'] and check_shift_time(config['middle_shift_slot']):
            shift_key = ('2', config['middle_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

        # 检查晚班
        if config['night_shift'] and config['night_shift_slot'] and check_shift_time(config['night_shift_slot']):
            shift_key = ('3', config['night_shift_slot'])
            shift_groups[shift_key].append({
                'dept_id': config['dept_id'],
                'dept_name': config['dept_name'],
                'shift_type': config['shift_type']
            })

    return shift_groups


""" 定时执行交接班 """
def timed_shift_change():
    if datetime.now().hour in [0, 1, 2, 3, 4, 5, 23]:
        logging.info("当前时间段不执行定时任务")
        return

    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=600 表示过期时间 120 秒（2 分钟），nx=True 表示不存在时才设置
    redis_client.set(f"timed_shift_change", 1, ex=180, nx=True)

    shift_groups = []
    try:
        shift_groups = upcoming_shifts_grouped()
    except Exception as e:
        logger.error(f"获取即将交班科室列表失败：{e}")
        return

    if not shift_groups:
        logger.info(f"没有即将交班科室")
        redis_client.delete(f"timed_shift_change")
        return

    doctor_shift_groups = defaultdict(list)
    nursing_shift_groups = defaultdict(list)

    shift_classes = 1
    # 按班次类型和时间段排序输出
    for (shift_class, time_slot), departments in sorted(shift_groups.items()):
        shift_classes = shift_class
        for dept in departments:
            if int(dept['shift_type']) == 1:
                doctor_shift_groups[time_slot].append(dept['dept_id'])
            else:
                nursing_shift_groups[time_slot].append(dept['dept_id'])

    if not doctor_shift_groups and not nursing_shift_groups:
        return

    shoushu_patients = []
    if int(shift_classes) == 3:
        shoushu_patients = query_shoushu_patient_zhuyuanhao()

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
        reg_sqls = {item.get('sid'): item for item in all_sqls}

    # 抓取医生交接班数据
    if doctor_shift_groups:
        for time_slot, dept_list in doctor_shift_groups.items():
            try:
                doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list)
            except Exception as e:
                logger.warning(f"医生 {time_slot} 交班异常: {e}")

    if nursing_shift_groups:
        for time_slot, dept_list in nursing_shift_groups.items():
            if '1000961' in dept_list:
                # 妇产科
                try:
                    shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) == '1000961']
                    ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu)
                except Exception as e:
                    logger.warning(f"妇产科 {time_slot} 交接班异常: {e}")

            if '1000962' in dept_list:
                # ICU 重症
                try:
                    icu_shift_change(reg_sqls, shift_classes, time_slot)
                except Exception as e:
                    logger.warning(f"重症 ICU {time_slot} 交接班异常: {e}")

            if '1000965' in dept_list:
                # AICU
                try:
                    shoushu = []
                    aicu_shift_change(reg_sqls, shift_classes, time_slot, '1000965')
                except Exception as e:
                    logger.warning(f"AICU {time_slot} 交接班异常: {e}")

            if '1001120' in dept_list:
                # CCU
                try:
                    shoushu = []
                    aicu_shift_change(reg_sqls, shift_classes, time_slot, '1001120')
                except Exception as e:
                    logger.warning(f"CCU {time_slot} 交接班异常: {e}")


            if '1001005' in dept_list:
                # EICU 护理单元
                try:
                    shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) == '1001005']
                    general_dept_shift_change(reg_sqls, shift_classes, time_slot, ['1001005'], shoushu)
                except Exception as e:
                    logger.warning(f"EICU 护理单元 {time_slot} 交接班异常: {e}")

            # 排除特殊科室
            dept_id_list = [dept_id for dept_id in dept_list if
                            dept_id not in ['1000961', '1000962', '1000965', '1001120', '1001005']]
            try:
                shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) in dept_id_list]
                general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_id_list, shoushu)
            except Exception as e:
                logger.warning(f"护理 {time_slot} 交班异常: {e}")

    redis_client.delete(f"timed_shift_change")


"""单独执行某一个科室 某一个班次的交接班"""
def single_run_shift_change(json_data):
    if is_in_transition_period():
        raise Exception("请勿在日期切换窗口(23:40-00:19)刷新数据")

    dept_id = json_data.get('dept_id')
    if not dept_id:
        raise Exception("请先选择科室")

    shift_type = json_data.get('shift_type')
    shift_date = json_data.get('shift_date')
    shift_classes = json_data.get('shift_classes')
    time_slot = json_data.get('time_slot')
    dept_list = [str(dept_id)]
    patient_id = json_data.get('patient_id', '')
    bingrenzyid = json_data.get('bingrenzyid', '')

    input_date = datetime.strptime(shift_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    previous_day = today - timedelta(days=1)
    if input_date != previous_day and int(shift_classes) == 3:
        raise Exception("仅支持刷新前一天的晚班")
    if input_date != today and int(shift_classes) in [1, 2]:
        raise Exception("仅支持刷新当天的早班 和 中班")

    shift_start, shift_end = get_complete_time_slot(time_slot)
    if datetime.now().strftime("%Y-%m-%d %H:%M:%S.999") < shift_end and not global_config.run_in_local:
        raise Exception("请勿刷新未开始或未结束的班次")

    dshift_config = query_shift_config(dept_id=dept_id)
    if dshift_config and int(shift_type) != int(dshift_config.get('shift_type')):
        raise Exception("交班类型和科室不匹配，请选择正确的科室")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if db.query_one(f"select * from nsyy_gyl.scs_shift_info where shift_date = '{shift_date}' "
                        f"and dept_id = {dept_id} and shift_classes = '{shift_type}-{shift_classes}' and archived = 1"):
            raise Exception("该班次已归档无法再刷新数据，如需刷新数据请先取消归档。慎重操作")

        all_sqls = db.query_all("select * from nsyy_gyl.scs_reg_sql")
        reg_sqls = {item.get('sid'): item for item in all_sqls}

    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.set(f"timed_shift_change", 2, ex=90, nx=True):
        raise Exception("有正在执行的交接班任务，请稍后重试")

    # 尝试设置键，只有当键不存在时才设置成功.  ex=600 表示过期时间 600 秒（10 分钟），nx=True 表示不存在时才设置
    if not patient_id and not global_config.run_in_local and not redis_client.set(f"shift_change:{str(dept_id)}",
                                                                              dept_id, ex=130, nx=True):
        redis_client.delete(f"timed_shift_change")
        raise Exception('请先歇一歇，给系统一点反应时间（5分钟刷一次）')

    try:
        shoushu_patients = []
        if int(shift_classes) == 3 and len(dept_list) == 1 and (dept_list[0] not in ['1000965', '1001120', '1000962']):
            shoushu_patients = query_shoushu_patient_zhuyuanhao()

        if shift_type == 1:
            # 医生交接班
            # if str(dept_id) == '7903' or str(dept_id) == '94143':
            #     dept_list = ['7903', '94143']
            if str(dept_id) == '1000148' or str(dept_id) == '1000149':
                dept_list = ['1000148', '1000149']
            if str(dept_id) == '93163' or str(dept_id) == '1000701':
                dept_list = ['93163', '1000701']
            if str(dept_id) == '169' or str(dept_id) == '7905':
                dept_list = ['169', '7905']
            if str(dept_id) == '1000406' or str(dept_id) == '94103':
                dept_list = ['1000406', '94103']
            if str(dept_id) == '165' or str(dept_id) == '51227':
                dept_list = ['165', '51227']
            doctor_shift_change(reg_sqls, shift_classes, time_slot, dept_list, True)
        elif shift_type == 2:
            if len(dept_list) == 1 and ('1000965' in dept_list or '1001120' in dept_list):
                # AICU/CCU交接班
                aicu_shift_change(reg_sqls, shift_classes, time_slot, dept_list[0], True, patient_id)
                redis_client.delete(f"timed_shift_change")
                return
            if len(dept_list) == 1 and '1000961' in dept_list:
                # 妇产科交接班
                shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) == '1000961']
                ob_gyn_shift_change(reg_sqls, shift_classes, time_slot, shoushu, True, patient_id)
                redis_client.delete(f"timed_shift_change")
                return
            if len(dept_list) == 1 and '1000962' in dept_list:
                # 重症 ICU 交接班
                icu_shift_change(reg_sqls, shift_classes, time_slot, True, patient_id, bingrenzyid)
                redis_client.delete(f"timed_shift_change")
                return
            if len(dept_list) == 1 and '1001005' in dept_list:
                # EICU 护理单元
                shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) == '1001005']
                general_dept_shift_change(reg_sqls, shift_classes, time_slot, ['1001005'], shoushu, True, patient_id)
                redis_client.delete(f"timed_shift_change")
                return

            # 普通护理交接班
            shoushu = [item for item in shoushu_patients if str(item.get('所在病区id')) in dept_list]
            general_dept_shift_change(reg_sqls, shift_classes, time_slot, dept_list, shoushu, True, patient_id)
        else:
            raise Exception("未知的交接班类型")
    except Exception as e:
        logger.warning(f"{time_slot} 交班异常: {e}")
        redis_client.delete(f"shift_change:{dept_id}")
        redis_client.delete(f"timed_shift_change")
    redis_client.delete(f"timed_shift_change")


"""判断当前时间是否处于这两个过渡时间段内。"""
def is_in_transition_period():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    # 前一天最后20分钟 (23:40-23:59)
    if current_hour == 23 and current_minute >= 40:
        return True

    # 后一天前20分钟 (00:00-00:19)
    if current_hour == 0 and current_minute <= 19:
        return True

    return False


"""sql 没有统计的患者类别，人数默认为 0"""
def fill_missing_types(data, dept_people_count, shift_type):
    dept_map = defaultdict(dict)

    for item in data:
        key = (item['所在科室id'], item['所在科室']) if shift_type == 1 else (item['所在病区id'], item['所在病区'])
        dept_map[key][item['患者类别']] = item['人数']

    # 填充缺失的类型
    result = []
    for (dept_id, dept_name), type_count_map in dept_map.items():
        for t in dept_people_count:
            count = type_count_map.get(t, 0)
            result.append({
                "患者类别": t, "人数": count,
                "所在科室id": dept_id if shift_type == 1 else 0,
                "所在科室": dept_name if shift_type == 1 else '',
                "所在病区id": dept_id if shift_type == 2 else 0,
                "所在病区": dept_name if shift_type == 2 else '',
            })

    return result






if __name__ == '__main__':
    timed_shift_change()

    # single_run_shift_change({
    #     "shift_date": "2026-05-26",
    #     "shift_type": 2,
    #     "shift_classes": 3,
    #     "time_slot": "21:30-7:30",
    #     "dept_id": 1001120
    # })

# '1000965' AICU
#
# '1001120' CCU
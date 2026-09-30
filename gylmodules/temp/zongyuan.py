# from gylmodules import global_tools
# from gylmodules.utils.db_utils_new import DbUtil
#
# # 总院 DIP 患者数据更新
#
# with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
#     data = db.query_all("select 医保结算流水号 from nsyy_gyl.dip_patient where 用药医嘱 is null and 来源 = '南阳南石医院'")
#
# id_list = [item.get('医保结算流水号') for item in data]
#
# print(len(id_list))
# # print(id_list)
#
# batch_size = 50
# total = len(id_list)
# for i in range(0, total, batch_size):
#     batch = id_list[i:i + batch_size]
#     print(f"处理第 {i // batch_size + 1} 批，共 {len(batch)} 条记录")
#     # print(batch)
#     ids = ','.join([f"'{item}'" for item in batch])
#     # print(ids)
#
#     sql = f"""
#     with jy as
#     (
#     select bingrenzyid,string_agg(jg ,'、') as jg
#     from (
#     select yj.bingrenzyid,yj.shenhesj::varchar || string_agg(yj1.zhongwenmc || ':' ||yj1.jianyanjg || coalesce(yj1.dangwei,''),'、') as jg
#     from df_cdr.yj_jianyanbg yj
#     join df_cdr.yj_jianyanbgmx yj1 on yj.jiluid = yj1.jiluid
#     join df_jj_zhuyuan.zy_bingrenxx zb on yj.bingrenzyid=zb.bingrenzyid
#     join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
#     join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
#     group by yj.bingrenzyid,yj.shenhesj
#     order by yj.shenhesj
#     )v
#     group by bingrenzyid
#     ),
#     yz1 as
#     (
#     select  bingrenzyid,string_agg(治疗,'、') as 治疗
#     from
#     (
#     select bingrenzyid,
#     string_agg(  '诊疗：'
#     	|| yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
#     from(
#     select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
#     from df_lc_zhuyuan.yz_bingrenyz yb
#     join df_zhushuju.yz_yizhuxm yy on yb.yizhuxmid=yy.yizhuxmid and yy.yizhulxid='13'
#     join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
#     join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
#     join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
#     join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
#     where yb.yizhuzt in ('3', '4')
#     group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
#     )v
#     group by bingrenzyid
#     union all
#     select bingrenzyid,
#     string_agg(  '手术：'
#     	|| yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
#     from(
#     select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
#     from df_lc_zhuyuan.yz_bingrenyz yb
#     join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
#     join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
#     join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
#     join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
#     where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('25')
#     group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
#     )v
#     group by bingrenzyid
#     )z  group by bingrenzyid
#     ),
#     yz2 as
#     (
#     select bingrenzyid,
#     string_agg( '用药：'
#     	|| yizhumc || ':' || to_char(shuliang,'FM9999990.00') || coalesce(dw,'') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、') filter (where yizhufl in ('11','12','13')) as 用药
#     from(
#     select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
#     from df_lc_zhuyuan.yz_bingrenyz yb
#     join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
#     join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
#     join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
#     join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
#     where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('11','12','13')
#     group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
#     )v
#     group by bingrenzyid
#     )
#     select
#       zb.xingming ,
#       zb.zhuyuanhao ,
#       zb.zhuyuancs,
#       yz.yibaojyhm ,
#       (
#       select
#         string_agg(case
#           when zz.shunxuhao = 1 then '主要诊断：'
#           else '其他诊断：'
#         end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
#         '、'
#       order by
#         zz.shunxuhao)
#       from
#         df_jj_zhuyuan.zy_zhenduanzl zz
#       where
#         zz.bingrenzyid = zb.bingrenzyid
#         and zz.zhenduanlb like '19%'
#         and zz.zuofeibz = '0') 诊断,
#         (select
#       string_agg(case
#           when bbx.shunxuhao = 1 then '主要诊断：'
#           else '其他诊断：'
#         end || bbx.zhenduanmc || '(' || bbx.jibingbm  || ')' ,
#         '、'
#       order by
#         bbx.shunxuhao)
#     from
#       df_bingangl.ba_bingrenjbxx bb
#     join df_bingangl.ba_bingrenzd_xy bbx on
#       bb.binganbrxh = bbx.binganbrxh
#       and bbx.zuofeibz = '0'
#       and bbx.zhenduanlb like '19%'
#     where bb.hisbrzyid =zb.bingrenzyid) 病案诊断,
#     (
#     select string_agg(yj.baogaosj::varchar || yj.jianchaxmmc || ':' ||nullif(yj.jianchasuojian,''),'、' order by baogaosj asc)
#     from df_cdr.yj_jianchabg yj
#     where yj.bingrenzyid=zb.bingrenzyid and yj.zuofeibz=0
#     ) 检查,
#     jy.jg 检验,
#         (select
#       string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
#       '、'
#     order by
#       shunxuhao)
#     from
#       df_jj_zhuyuan.zy_ba_shoushuzl zbs
#     where
#       zbs.zuofeibz = '0'
#       and zbs.bingrenzyid = zb.bingrenzyid) 手术,
#       (
#       select
#         string_agg( (xpath ( 'string()' :: text,
#         wb2.wenjiannr :: xml ))[1]::text,
#         '
#     '
#       order by
#         wb.jilusj)
#       from
#         df_bingli.ws_binglijl wb
#       join df_bingli.ws_binglijlnr wb2 on
#         wb.binglijlid = wb2.binglijlid
#       where
#         wb.bingrenzyid = zb.bingrenzyid
#         and wb.zuofeibz = '0'
#         and wb.wenshuzt = 2
#         and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
#             (select
#      string_agg( (xpath ( 'string()' :: text,
#         wb2.wenjiannr :: xml ))[1]::text,
#         '
#     '
#       order by
#         wb.jilusj)
#     from
#       df_bingli.ws_binglijl wb
#     join df_bingli.ws_binglijlnr wb2 on
#       wb.binglijlid = wb2.binglijlid
#       where  wb.bingrenzyid = zb.bingrenzyid
#         and wb.zuofeibz = '0'
#       and wb.wenshuzt = 2
#        and fuleimblx ='RuYuanJLFL' )入院记录,
#         (select
#      string_agg( (xpath ( 'string()' :: text,
#         wb2.wenjiannr :: xml ))[1]::text,
#         '
#     '
#       order by wb.jilusj)
#     from df_bingli.ws_binglijl wb
#     join df_bingli.ws_binglijlnr wb2 on wb.binglijlid = wb2.binglijlid
#     where  wb.bingrenzyid = zb.bingrenzyid and wb.zuofeibz = '0' and wb.wenshuzt = 2 and fuleimblx ='ChuYuanJLFL' ) 出院记录 ,
#     yz1.治疗 治疗医嘱,yz2.用药 用药医嘱
#     from
#       df_jj_zhuyuan.zy_bingrenxx zb
#     join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
#     join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid
#     left join jy on jy.bingrenzyid=zb.bingrenzyid
#     left join yz1 on yz1.bingrenzyid=zb.bingrenzyid
#     left join yz2 on yz2.bingrenzyid=zb.bingrenzyid
#     where yz.yibaojyhm in ({ids})
#     """
#
#     data_list = global_tools.call_new_his_pg(sql)
#
#     if not data_list:
#         continue
#
#     # 在这里处理每一批数据
#     params = [
#         (r.get('诊断'), r.get('病案诊断'), r.get('手术'), r.get('手术记录'), r.get('出院记录'), r.get('入院记录'), r.get('检查'), r.get('检验'), r.get('治疗医嘱'), r.get('用药医嘱'), r.get('yibaojyhm'))
#         for r in data_list
#     ]
#
#     sql = """UPDATE nsyy_gyl.dip_patient SET 诊断 = %s, 病案诊断 = %s, 手术 = %s, 手术记录 = %s, 出院记录 = %s, 入院记录 = %s, 检查 = %s, 检验 = %s, 治疗医嘱 = %s, 用药医嘱 = %s WHERE 医保结算流水号 = %s"""
#
#     with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
#         db.execute_many(sql, params, need_commit=True)
#
#
#
from typing import List, Dict, Any

from gylmodules import global_tools
from gylmodules.utils.db_utils_new import DbUtil


# 从原始 INSERT 提取的所有字段名（按顺序）
FIELDS = [
    "医保结算流水号", "姓名", "患者费别", "总费用", "出院科室", "住院医师",
    "现DIP代码", "现DIP名称", "现DIP分值", "现DIP盈亏", "现DIP倍率",
    "住院号", "住院次数", "入院时间", "出院时间", "年龄", "性别",
     "诊断", "病案诊断", "手术", "医嘱", "出院记录",
    "手术记录", "入院记录", "来源", "检查", "检验", "治疗医嘱", "用药医嘱"
]

# 主键字段（用于冲突检测）
PRIMARY_KEY = "医保结算流水号"

def build_upsert_sql(fields: List[str], pk: str) -> str:
    """
    构建批量 upsert 的 SQL 模板（使用 %s 占位符）
    """
    placeholders = ", ".join(["%s"] * len(fields))
    field_names = ", ".join([f"`{f}`" for f in fields])

    # 更新部分：除主键外所有字段更新（也可只更新部分，但通常全部更新）
    update_parts = []
    for f in fields:
        if f != pk:
            update_parts.append(f"`{f}` = VALUES(`{f}`)")
    update_clause = ", ".join(update_parts)

    sql = f"""
        INSERT INTO dip_patient ({field_names})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_clause}
    """
    return sql


# 总院 DIP 患者数据更新

data = global_tools.excel_to_jsons('/Users/gaoyanliang/Downloads/清单质控列表__20260701_20260721.xlsx')

all_list = {item.get('医保结算流水号'): {
    "医保结算流水号": item.get('医保结算流水号'),
    "姓名": item.get('姓名'),
    "住院号": item.get('住院号'),
    "年龄": item.get('年龄'),
    "性别": item.get('性别'),
    "住院次数": item.get('住院次数'),
    "患者费别": item.get('患者费别'),
    "总费用": item.get('总费用'),
    "出院科室": item.get('出院科室'),
    "住院医师": item.get('住院医师'),
    "现DIP代码": item.get('DIP入组代码'),
    "现DIP名称": item.get('DIP入组名称'),
    "现DIP分值": item.get('DIP分值'),
    "现DIP盈亏": item.get('DIP结余预测'),
    "现DIP倍率": item.get('DIP倍率'),
    "入院时间": item.get('入院时间'),
    "出院时间": item.get('出院时间'),
    "来源": "南阳南石医院"
} for item in data if item.get('医保结算流水号')}

id_list = [item.get('医保结算流水号') for item in data if item.get('医保结算流水号')]

print(len(id_list))
# print(id_list)

batch_size = 100
total = len(id_list)
for i in range(0, total, batch_size):
    batch = id_list[i:i + batch_size]
    print(f"处理第 {i // batch_size + 1} 批，共 {len(batch)} 条记录")
    # print(batch)
    ids = ','.join([f"'{item}'" for item in batch])
    # print(ids)

    sql = f"""
    with jy as 
    (
    select bingrenzyid,string_agg(jg ,'、') as jg
    from (
    select yj.bingrenzyid,yj.shenhesj::varchar || string_agg(yj1.zhongwenmc || ':' ||yj1.jianyanjg || coalesce(yj1.dangwei,''),'、') as jg
    from df_cdr.yj_jianyanbg yj 
    join df_cdr.yj_jianyanbgmx yj1 on yj.jiluid = yj1.jiluid
    join df_jj_zhuyuan.zy_bingrenxx zb on yj.bingrenzyid=zb.bingrenzyid
    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
    group by yj.bingrenzyid,yj.shenhesj
    order by yj.shenhesj 
    )v
    group by bingrenzyid
    ),
    yz1 as 
    ( 
    select  bingrenzyid,string_agg(治疗,'、') as 治疗
    from 
    (
    select bingrenzyid,
    string_agg(  '诊疗：' 
    	|| yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
    from(
    select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
    from df_lc_zhuyuan.yz_bingrenyz yb
    join df_zhushuju.yz_yizhuxm yy on yb.yizhuxmid=yy.yizhuxmid and yy.yizhulxid='13'
    join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
    where yb.yizhuzt in ('3', '4') 
    group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
    )v 
    group by bingrenzyid
    union all 
    select bingrenzyid,
    string_agg(  '手术：' 
    	|| yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
    from(
    select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
    from df_lc_zhuyuan.yz_bingrenyz yb
    join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
    where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('25')
    group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
    )v 
    group by bingrenzyid
    )z  group by bingrenzyid
    ),
    yz2 as 
    ( 
    select bingrenzyid,
    string_agg( '用药：' 
    	|| yizhumc || ':' || to_char(shuliang,'FM9999990.00') || coalesce(dw,'') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、') filter (where yizhufl in ('11','12','13')) as 用药
    from(
    select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
    from df_lc_zhuyuan.yz_bingrenyz yb
    join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid and yz.yibaojyhm in ({ids})
    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
    where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('11','12','13')
    group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
    )v 
    group by bingrenzyid
    )
    select
      zb.xingming ,
      zb.zhuyuanhao ,
      zb.zhuyuancs,
      yz.yibaojyhm ,
      (
      select
        string_agg(case
          when zz.shunxuhao = 1 then '主要诊断：'
          else '其他诊断：'
        end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
        '、'
      order by
        zz.shunxuhao)
      from
        df_jj_zhuyuan.zy_zhenduanzl zz
      where
        zz.bingrenzyid = zb.bingrenzyid
        and zz.zhenduanlb like '19%'
        and zz.zuofeibz = '0') 诊断,
        (select
      string_agg(case
          when bbx.shunxuhao = 1 then '主要诊断：'
          else '其他诊断：'
        end || bbx.zhenduanmc || '(' || bbx.jibingbm  || ')' ,
        '、'
      order by
        bbx.shunxuhao)
    from
      df_bingangl.ba_bingrenjbxx bb
    join df_bingangl.ba_bingrenzd_xy bbx on
      bb.binganbrxh = bbx.binganbrxh
      and bbx.zuofeibz = '0'
      and bbx.zhenduanlb like '19%'
    where bb.hisbrzyid =zb.bingrenzyid) 病案诊断,
    (
    select string_agg(yj.baogaosj::varchar || yj.jianchaxmmc || ':' ||nullif(yj.jianchasuojian,''),'、' order by baogaosj asc)
    from df_cdr.yj_jianchabg yj 
    where yj.bingrenzyid=zb.bingrenzyid and yj.zuofeibz=0
    ) 检查,
    jy.jg 检验,
        (select
      string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
      '、'
    order by
      shunxuhao)
    from
      df_jj_zhuyuan.zy_ba_shoushuzl zbs
    where
      zbs.zuofeibz = '0'
      and zbs.bingrenzyid = zb.bingrenzyid) 手术,
      (
      select
        string_agg( (xpath ( 'string()' :: text,
        wb2.wenjiannr :: xml ))[1]::text,
        '
    '
      order by
        wb.jilusj)
      from
        df_bingli.ws_binglijl wb
      join df_bingli.ws_binglijlnr wb2 on
        wb.binglijlid = wb2.binglijlid
      where
        wb.bingrenzyid = zb.bingrenzyid
        and wb.zuofeibz = '0'
        and wb.wenshuzt = 2
        and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
            (select
     string_agg( (xpath ( 'string()' :: text,
        wb2.wenjiannr :: xml ))[1]::text,
        '
    '
      order by
        wb.jilusj)
    from
      df_bingli.ws_binglijl wb
    join df_bingli.ws_binglijlnr wb2 on
      wb.binglijlid = wb2.binglijlid
      where  wb.bingrenzyid = zb.bingrenzyid
        and wb.zuofeibz = '0'
      and wb.wenshuzt = 2
       and fuleimblx ='RuYuanJLFL' )入院记录,
        (select
     string_agg( (xpath ( 'string()' :: text,
        wb2.wenjiannr :: xml ))[1]::text,
        '
    '
      order by wb.jilusj)
    from df_bingli.ws_binglijl wb
    join df_bingli.ws_binglijlnr wb2 on wb.binglijlid = wb2.binglijlid
    where  wb.bingrenzyid = zb.bingrenzyid and wb.zuofeibz = '0' and wb.wenshuzt = 2 and fuleimblx ='ChuYuanJLFL' ) 出院记录 ,
    yz1.治疗 治疗医嘱,yz2.用药 用药医嘱
    from
      df_jj_zhuyuan.zy_bingrenxx zb
    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid
    left join jy on jy.bingrenzyid=zb.bingrenzyid
    left join yz1 on yz1.bingrenzyid=zb.bingrenzyid
    left join yz2 on yz2.bingrenzyid=zb.bingrenzyid
    where yz.yibaojyhm in ({ids})
    """

    data_list = global_tools.call_new_his_pg(sql)

    if not data_list:
        continue

    ret_list = []
    for item in data_list:
        yibaojyhm = item.get('yibaojyhm')
        patient = all_list.get(yibaojyhm)
        if not patient:
            continue
        patient['诊断'] = item.get('诊断')
        patient['病案诊断'] = item.get('病案诊断')
        patient['手术'] = item.get('手术')
        patient['检查'] = item.get('检查')
        patient['检验'] = item.get('检验')
        patient['手术记录'] = item.get('手术记录')
        patient['出院记录'] = item.get('出院记录')
        patient['入院记录'] = item.get('入院记录')
        patient['治疗医嘱'] = item.get('治疗医嘱')
        patient['用药医嘱'] = item.get('用药医嘱')
        ret_list.append(patient)

    # 在这里处理每一批数据
    sql = build_upsert_sql(FIELDS, PRIMARY_KEY)
    # print(sql)
    # 将字典转换为按 FIELDS 顺序的值元组列表
    rows = []
    for item in ret_list:
        row = tuple(item.get(f) for f in FIELDS)
        rows.append(row)
    print(f'更新 {len(rows)} 条数据')
    with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
        db.execute_many(sql, rows, need_commit=True)





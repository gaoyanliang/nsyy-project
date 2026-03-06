import pandas as pd
import cx_Oracle as orcl
import psycopg2
def yz():
    his_conn = psycopg2.connect(
        host="192.168.8.57",
        port=6000,
        user="ogg",
        password="nyogg@2024",
        dbname="df_his"
    )
    #his_conn = orcl.connect('system/NSpingtai!8166@192.168.8.84:1521/nsyypt')
    # his_conn = orcl.connect('zlhis/.1451534F81B@192.168.3.8:1521/orcl')
    # 建立连接
    start_time='2026-02-01'
    end_time='2026-03-01'
    month='2月挂号数据'
    sql ="""
select 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间::date 挂号时间 from (
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%神经内科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%妇产科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%全科医学科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%烧伤科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%皮肤科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%消化内科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%中医科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%耳鼻%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
union all 
SELECT 姓名, 身份证号, 联系电话, 性别, 挂号类别, 挂号科室, 挂号医生, 挂号时间
FROM (
    SELECT 
        bingrenxm 姓名,
        gb.shenfenzh 身份证号,
        gb.xianzhuzhidh 联系电话,
        gb.xingbiemc 性别,
        CASE mg.guahaolbgl 
            WHEN '1' THEN '普通'
            WHEN '2' THEN '急诊'
            WHEN '3' THEN '专科'
            WHEN '4' THEN '专家' 
            ELSE NULL 
        END AS 挂号类别,
        mg.guahaoksmc 挂号科室,
        mg.guahaoysxm 挂号医生,
        mg.zhidanrq 挂号时间,
        ROW_NUMBER() OVER (PARTITION BY TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD') oRDER BY RANDOM()) AS rn
    FROM df_jj_menzhen.mz_guahao mg 
    LEFT JOIN df_bingrenzsy.gy_bingrenxx gb ON mg.bingrenid = gb.bingrenid
    WHERE mg.jiaoyilx = 1 AND mg.zuofeibz = 0
    and mg.guahaoksmc like '%疼痛科%'
    and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')>='{start_time}' and TO_CHAR(mg.zhidanrq, 'YYYY-MM-DD')<'{end_time}'
) v
WHERE rn <= 100
--ORDER BY 挂号时间
)v 
order by 挂号时间, 身份证号

"""
    sql=sql.replace('{start_time}',start_time).replace('{end_time}',end_time)
    df = pd.read_sql(sql,his_conn)
    df.to_excel(f'{month}.xlsx', index=False)

if __name__ == "__main__":
    # 运行前修改如下数据
    #     start_time='2026-02-01'
    #     end_time='2026-03-01'
    #     month='2月挂号数据'
    yz()
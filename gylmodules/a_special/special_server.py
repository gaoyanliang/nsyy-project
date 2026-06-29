import json
import time
from datetime import datetime
from decimal import Decimal

import redis
import requests

from gylmodules import global_config, global_tools

import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gylmodules.utils.db_utils_new import DbUtil

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

"""查询DIP信息"""

def query_dip_patients():
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists('dip_patients'):
        query_medical_page_update_record()

    if not redis_client.exists('dip_patients'):
        return []

    data = []
    for item in redis_client.hscan_iter('dip_patients'):
        data.append(json.loads(item[1]))

    return data

def query_all_dip_patients():
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists('all_dip_patients'):
        return []

    data = []
    for item in redis_client.hscan_iter('all_dip_patients'):
        data.append(json.loads(item[1]))

    return data

def query_medical_page_update_record():
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置更新锁
    if not redis_client.set(f"patient_dip_query_lock", 1, ex=20*60, nx=True):
        raise Exception("正在获取数据，大概需要10-20分钟，请稍后重试")

    sql = """select zb.bingrenzyid, zb.xingming, zb.dangqianksmc, zb.zhuyuanysxm, zb.ruyuanrq ,
	(select string_agg(zz.zhenduanmc || '-' || zz.icd10 , '、' order by shunxuhao) from df_jj_zhuyuan.zy_zhenduanzl zz
	where zz.zuofeibz = '0'
		and zb.yiliaolbmc <> '生育住院'
		and zb.feiyongxzid in ('390_GuoJia', '310_GuoJia')
		and zb.yibaoqh ~ '^41'
		and zz.zhenduanlb like '13%'
		and zz.bingrenzyid = zb.bingrenzyid) zhenduan
from
	df_jj_zhuyuan.zy_bingrenxx zb
where
	zb.zaiyuanzt = '0'
	and zb.xingming not like '%测试%'
	and zb.dangqianksmc not like '%测试%'
	and zb.dangqianbqmc not like '%测试%'
	and zb.quxiaorybz = '0'
	and zb.rukebz = '1'
	and exists (
	select
		1
	from
		df_yiliaogl.gy_maidianrz gm
	where
		gm.mokuai = '病案首页'
		and gm.xingwei = '保存'
		and gm.chuangjiansj >= now()::date - interval '1 day'
		and gm.chuangjiansj < now()::date
		and gm.shujulyid = zb.bingrenzyid)"""

    data_list = global_tools.call_new_his_pg(sql)
    if not data_list:
        redis_client.delete('patient_dip_query_lock')
        return


    logger.debug(f'dip 一共查询到 {len(data_list)} 条修改记录')

    redis_client = redis.Redis(connection_pool=pool)
    # redis_client.delete('dip_patients')
    for item in data_list:
        if not item.get('bingrenzyid'):
            continue
        dip = get_dip(item.get('bingrenzyid'))
        if dip:
            dip_drg = dip.get('dipDrg') or {}
            # dip 分组
            item['groupName'] = "{} {}".format(dip_drg.get('dipRzmc') or '', dip_drg.get('dipRz') or '').strip()
            # dip 诊断
            item['dip_zhenduan'] = "{} {}".format(dip_drg.get('dipZdmc') or '', dip_drg.get('dipZd') or '').strip()
            # dip倍率
            item['dipRatio'] = dip_drg.get('dipJsFybl') or ''
            # 总费用
            item['totalCost'] = dip_drg.get('zfy') or ''
            # 盈亏
            item['profitLoss'] = dip_drg.get('dipJsJyyg') or ''
            # 标准分值
            item['score1'] = dip_drg.get('dipMlfz') or ''
            # 校正分值
            item['score2'] = dip_drg.get('dipJsJzfz') or ''

        item['patientId'] = item.get('bingrenzyid', '')
        item['patientName'] = item.get('xingming', '')
        item['patientDept'] = item.get('dangqianksmc', '')
        item['zhuyuanysxm'] = item.get('zhuyuanysxm', '')
        item['ruyuanrq'] = item.get('ruyuanrq')
        item['zhenduan'] = item.get('zhenduan', '')

        redis_client.hset('dip_patients', item.get('bingrenzyid'), json.dumps(item, ensure_ascii=False, default=str))
        redis_client.hset('all_dip_patients', item.get('bingrenzyid'), json.dumps(item, ensure_ascii=False, default=str))

    sql = """select zb.bingrenzyid from df_jj_zhuyuan.zy_bingrenxx zb where
            (( zb.zaiyuanzt = '0' and ( zb.yiliaolbmc = '生育住院'
                    or zb.feiyongxzid not in ('390_GuoJia', '310_GuoJia') or zb.yibaoqh !~ '^41')) or
            (zb.zaiyuanzt in ('1', '2') and zb.yuchuyrq > current_date - interval '2 days'))
            and zb.xingming not like '%测试%'
            and zb.dangqianksmc not like '%测试%'
            and zb.dangqianbqmc not like '%测试%'"""
    remove_data_list = global_tools.call_new_his_pg(sql)
    if not remove_data_list:
        redis_client.delete('patient_dip_query_lock')
        return
    for item in remove_data_list:
        redis_client.hdel('dip_patients', item.get('bingrenzyid'))

    redis_client.delete('patient_dip_query_lock')


def get_dip(bingrenzyid):
    url = f"http://192.168.9.26:9081/punuo/ba/ast/get/res-info?glwybs={bingrenzyid}&userId=DBA&source=doctor"
    retry_times = 3
    while retry_times > 0:
        try:
            with requests.Session() as session:
                r = session.get(url, timeout=5)
                r.raise_for_status()
                data = r.json()
            if data and (data.get('code', 1) == 0 or data.get('message', '') == "success"):
                return data.get('data')
        except Exception:
            pass
        retry_times -= 1
    return None


"""刷新患者DIP数据"""

def refresh_patient_dip_info(bingrenzyid):
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置更新锁
    if not redis_client.set(f"patient_dip_update_lock", 2, ex=90, nx=True):
        raise Exception("正在刷新，请稍后重试")

    patient_info = redis_client.hget('dip_patients', bingrenzyid)
    if not patient_info:
        redis_client.delete('patient_dip_update_lock')
        raise Exception('未找到患者信息')
    patient_info = json.loads(patient_info)
    dip = get_dip(bingrenzyid)
    if dip:
        dip_drg = dip.get('dipDrg') or {}
        # dip 分组
        patient_info['groupName'] = "{} {}".format(dip_drg.get('dipRzmc') or '', dip_drg.get('dipRz') or '').strip()
        # dip 诊断
        patient_info['zhenduan'] = "{} {}".format(dip_drg.get('dipZdmc') or '', dip_drg.get('dipZd') or '').strip()
        # dip倍率
        patient_info['dipRatio'] = dip_drg.get('dipJsFybl') or ''
        # 总费用
        patient_info['totalCost'] = dip_drg.get('zfy') or ''
        # 盈亏
        patient_info['profitLoss'] = dip_drg.get('dipJsJyyg') or ''
        # 标准分值
        patient_info['score1'] = dip_drg.get('dipMlfz') or ''
        # 校正分值
        patient_info['score2'] = dip_drg.get('dipJsJzfz') or ''

    redis_client.hset('dip_patients', bingrenzyid, json.dumps(patient_info, ensure_ascii=False, default=str))
    redis_client.hset('all_dip_patients', bingrenzyid, json.dumps(patient_info, ensure_ascii=False, default=str))
    redis_client.delete('patient_dip_update_lock')
    return patient_info



"""查询入院三天还未提交病案首页的患者列表"""


def query_unpage_patients():
    redis_client = redis.Redis(connection_pool=pool)
    if not redis_client.exists('dip_unpage_patients'):
        unmedical_page_list()

    if not redis_client.exists('dip_unpage_patients'):
        return []

    data = []
    for item in redis_client.hscan_iter('dip_unpage_patients'):
        data.append(json.loads(item[1]))

    return data


def unmedical_page_list():
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置更新锁
    if not redis_client.set(f"unpage_query_lock", 1, ex=20*60, nx=True):
        raise Exception("正在获取数据，大概需要10-20分钟，请稍后重试")

    sql = """select zb.bingrenzyid ,zb.xingming ,zb.zhuyuanhao ,zb.ruyuanrq ,zb.dangqianksmc ,zb.zhuyuanysxm,gz.dianhua 
            from df_jj_zhuyuan.zy_bingrenxx zb left join df_zhushuju.gy_zhigongda gz on zb.zhuyuanysid =gz.zhigongid 
            where
	zb.zaiyuanzt = '0'
	and zb.yiliaolbmc <> '生育住院'
	and zb.feiyongxzid in ('390_GuoJia', '310_GuoJia')
	and zb.yibaoqh ~ '^41'
	and zb.xingming not like '%测试%'
	and zb.dangqianksmc not like '%测试%'
	and zb.dangqianbqmc not like '%测试%'
	and zb.quxiaorybz = '0'
	and zb.rukebz = '1'
	and zb.ruyuanrq>=now()::date - interval '3 days'
	and not exists (
	select 1 from df_yiliaogl.gy_maidianrz gm where
		gm.mokuai = '病案首页'
		and gm.chuangjiansj>=current_date - 3
		and gm.xingwei = '保存'
		and gm.shujulyid = zb.bingrenzyid 
		 )"""

    data_list = global_tools.call_new_his_pg(sql)
    if not data_list:
        redis_client.delete('unpage_query_lock')
        return

    logger.debug(f'入院三天还未提交病案首页的患者列表 一共查询到 {len(data_list)} 条记录')

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.delete('dip_unpage_patients')
    for item in data_list:
        redis_client.hset('dip_unpage_patients', item.get('bingrenzyid'), json.dumps(item, ensure_ascii=False, default=str))

    redis_client.delete('unpage_query_lock')


def ocr_try_variants(img_b64):
    """利用眼科医院的ocr识别工具进行解析（带重试机制）"""

    # 可配置参数
    max_retries = 3
    timeout = 10
    retry_delay = 1  # 重试间隔（秒）

    # 设置重试策略
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=retry_delay,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    for attempt in range(1, max_retries + 1):
        try:
            payload = {"img_b64": img_b64}
            response = session.post(
                "http://192.168.190.252:8080/gyl/ehp/captcha",
                json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 20000:
                logger.debug(f"OCR 识别成功，第 {attempt} 次尝试")
                return data.get('data')
            else:
                logger.warning(
                    f"OCR 返回非成功码: code={data.get('code')}, "
                    f"msg={data.get('msg', 'N/A')}, 第 {attempt} 次尝试"
                )

        except requests.exceptions.Timeout:
            logger.error(f"OCR 请求超时，第 {attempt} 次尝试")
        except requests.exceptions.RequestException as e:
            logger.error(f"OCR 请求异常: {e}, 第 {attempt} 次尝试")
        except ValueError as e:
            logger.error(f"OCR 响应解析失败: {e}, 第 {attempt} 次尝试")

        # 最后一次不需要等待
        if attempt < max_retries:
            time.sleep(retry_delay * attempt)  # 指数退避

    session.close()
    raise Exception(f"OCR 识别失败，已重试 {max_retries} 次")


def query_all_dip_record():
    start_time = time.time()
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置更新锁
    if not redis_client.set(f"all_dip_query_lock", 1, ex=20*60, nx=True):
        raise Exception("正在获取数据，大概需要10-20分钟，请稍后重试")

    sql = """select zb.bingrenzyid, zb.xingming, zb.dangqianksmc, zb.zhuyuanysxm, zb.ruyuanrq ,
	(select string_agg(zz.zhenduanmc || '-' || zz.icd10 , '、' order by shunxuhao) from df_jj_zhuyuan.zy_zhenduanzl zz
	where zz.zuofeibz = '0'
		and zz.zhenduanlb like '13%'
		and zz.bingrenzyid = zb.bingrenzyid) zhenduan from df_jj_zhuyuan.zy_bingrenxx zb
        where
	zb.zaiyuanzt = '0'
	and zb.xingming not like '%测试%'
	and zb.dangqianksmc not like '%测试%'
	and zb.dangqianbqmc not like '%测试%'
	and zb.quxiaorybz = '0'"""

    data_list = global_tools.call_new_his_pg(sql)
    if not data_list:
        redis_client.delete('all_dip_query_lock')
        return


    logger.debug(f'dip 一共查询到 {len(data_list)} 条总记录')

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.delete('all_dip_patients')
    for item in data_list:
        if not item.get('bingrenzyid'):
            continue
        dip = get_dip(item.get('bingrenzyid'))
        if dip:
            dip_drg = dip.get('dipDrg') or {}
            # dip 分组
            item['groupName'] = "{} {}".format(dip_drg.get('dipRzmc') or '', dip_drg.get('dipRz') or '').strip()
            # dip 诊断
            item['dip_zhenduan'] = "{} {}".format(dip_drg.get('dipZdmc') or '', dip_drg.get('dipZd') or '').strip()
            # dip倍率
            item['dipRatio'] = dip_drg.get('dipJsFybl') or ''
            # 总费用
            item['totalCost'] = dip_drg.get('zfy') or ''
            # 盈亏
            item['profitLoss'] = dip_drg.get('dipJsJyyg') or ''
            # 标准分值
            item['score1'] = dip_drg.get('dipMlfz') or ''
            # 校正分值
            item['score2'] = dip_drg.get('dipJsJzfz') or ''

        item['patientId'] = item.get('bingrenzyid', '')
        item['patientName'] = item.get('xingming', '')
        item['patientDept'] = item.get('dangqianksmc', '')
        item['zhuyuanysxm'] = item.get('zhuyuanysxm', '')
        item['ruyuanrq'] = item.get('ruyuanrq')
        item['zhenduan'] = item.get('zhenduan', '')

        redis_client.hset('all_dip_patients', item.get('bingrenzyid'), json.dumps(item, ensure_ascii=False, default=str))

    logger.info(f'dip 一共处理了 {len(data_list)} 条总记录, 用时 {time.time() - start_time}秒')
    redis_client.delete('all_dip_query_lock')


def safe_value(val, numeric=False):
    """安全处理参数值，避免空字符串传入数值字段"""
    if val is None:
        return None
    if numeric:
        # 数值类型：空字符串转为 None，否则保持原值（Decimal/float/int）
        if val == '':
            return None
        return val
    else:
        # 字符串类型：去除换行符并转为字符串
        return str(val).replace('\n', '').replace('\r', '')

def handle_ai_dip(data):
    ai_dip_dict = {item.get('jiesuanid'): item for item in data}

    jiesuanids = ','.join([f"'{item}'" for item in ai_dip_dict.keys()])
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        patient_list = db.query_all(f"SELECT * FROM nsyy_gyl.dip_patient where 医保结算流水号 in ({jiesuanids})")

    for item in patient_list:
        jiesuanid = item.get('医保结算流水号')
        ai_dip_info = ai_dip_dict.get(jiesuanid)

        item['AI方案1DIP代码'] = ai_dip_info.get('recommendations', [])[0].get('dip_code') if len(ai_dip_info.get('recommendations', [])) > 0 else ''
        item['AI方案1DIP名称'] = ai_dip_info.get('recommendations', [])[0].get('dip_name') if len(ai_dip_info.get('recommendations', [])) > 0 else ''
        item['AI方案1DIP分值'] = ai_dip_info.get('recommendations', [])[0].get('score') if len(ai_dip_info.get('recommendations', [])) > 0 else ''
        item['AI方案1DIP倍率'] = ai_dip_info.get('recommendations', [])[0].get('dip_rate') if len(ai_dip_info.get('recommendations', [])) > 0 else ''
        item['AI方案1DIP入组类型'] = ai_dip_info.get('recommendations', [])[0].get('type') if len(ai_dip_info.get('recommendations', [])) > 0 else ''
        item['AI方案1DIP入组原因'] = ai_dip_info.get('recommendations', [])[0].get('reason') if len(ai_dip_info.get('recommendations', [])) > 0 else ''

        item['AI方案2DIP代码'] = ai_dip_info.get('recommendations', [])[1].get('dip_code') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''
        item['AI方案2DIP名称'] = ai_dip_info.get('recommendations', [])[1].get('dip_name') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''
        item['AI方案2DIP分值'] = ai_dip_info.get('recommendations', [])[1].get('score') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''
        item['AI方案2DIP倍率'] = ai_dip_info.get('recommendations', [])[1].get('dip_rate') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''
        item['AI方案2DIP入组类型'] = ai_dip_info.get('recommendations', [])[1].get('type') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''
        item['AI方案2DIP入组原因'] = ai_dip_info.get('recommendations', [])[1].get('reason') if len(
            ai_dip_info.get('recommendations', [])) > 1 else ''

        item['AI方案3DIP代码'] = ai_dip_info.get('recommendations', [])[2].get('dip_code') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''
        item['AI方案3DIP名称'] = ai_dip_info.get('recommendations', [])[2].get('dip_name') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''
        item['AI方案3DIP分值'] = ai_dip_info.get('recommendations', [])[2].get('score') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''
        item['AI方案3DIP倍率'] = ai_dip_info.get('recommendations', [])[2].get('dip_rate') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''
        item['AI方案3DIP入组类型'] = ai_dip_info.get('recommendations', [])[2].get('type') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''
        item['AI方案3DIP入组原因'] = ai_dip_info.get('recommendations', [])[2].get('reason') if len(
            ai_dip_info.get('recommendations', [])) > 2 else ''


        good_rate = item.get('现DIP倍率')
        good_score = item.get('现DIP分值')
        good_group = item.get('现DIP代码')
        good_group_name = item.get('现DIP名称')
        good_jieyu = Decimal(str(item.get('现DIP盈亏')))
        good_source = "科室"

        type = Decimal("4") if str(item.get('患者费别', '')).__contains__('居民') else Decimal("4.4")
        try:
            total_fee = Decimal(str(item.get('总费用', '0')))
        except:
            total_fee = Decimal("0")
        try:
            ai_score = Decimal(str(item.get('AI方案1DIP分值', '0')))
        except:
            ai_score = Decimal("0")

        try:
            ai_rate = total_fee / (ai_score * Decimal("5.72183"))
            item['AI方案1DIP倍率'] = ai_rate
        except:
            ai_rate = Decimal("0")

        if ai_rate <= Decimal("0.5"):
            # (病例校正分值＝基准分值*倍率)*点值-总费用
            item['AI方案1DIP盈亏'] = ai_score * ai_rate * type - total_fee
        elif ai_rate > Decimal("0.5") and ai_rate <= Decimal("2"):
            # (病例校正分值＝基准分值*倍率)*1.1217-总费用
            item['AI方案1DIP盈亏'] = ai_score * Decimal("1.1217") * type - total_fee
        elif ai_rate > Decimal("2"):
            # (病例校正分值＝基准分值*（倍率-2+1.1217）)*点值-总费用
            item['AI方案1DIP盈亏'] = ai_score * (ai_rate - Decimal("2") + Decimal("1.1217")) * type - total_fee
        else:
            logger.error(f"异常 {item}")

        if item.get('AI方案1DIP盈亏', 0) and item.get('AI方案1DIP盈亏', 0) > good_jieyu:
            good_rate = ai_rate
            good_score = ai_score
            good_group = item.get('AI方案1DIP代码', '')
            good_group_name = item.get('AI方案1DIP名称', '')
            good_jieyu = item.get('AI方案1DIP盈亏', 0)
            good_source = "AI方案一"

        if item.get('AI方案2DIP代码', ''):
            # J96.9-null && 未特指的呼吸衰竭:保守治疗 && 1099.64 && 0.59 && 核心病组
            try:
                # ai_rate = Decimal(str(item.get('AI方案2DIP倍率')))
                ai_score = Decimal(str(item.get('AI方案2DIP分值')))

                try:
                    ai_rate = total_fee / (ai_score * Decimal("5.72183"))
                    item['AI方案2DIP倍率'] = ai_rate
                except:
                    ai_rate = Decimal("0")

                if ai_rate <= Decimal("0.5"):
                    # (病例校正分值＝基准分值*倍率)*点值-总费用
                    item['AI方案2DIP盈亏'] = ai_score * ai_rate * type - total_fee
                elif ai_rate > Decimal("0.5") and ai_rate <= Decimal("2"):
                    # (病例校正分值＝基准分值*倍率)*1.1217-总费用
                    item['AI方案2DIP盈亏'] = ai_score * Decimal("1.1217") * type - total_fee
                elif ai_rate > Decimal("2"):
                    # (病例校正分值＝基准分值*（倍率-2+1.1217）)*点值-总费用
                    item['AI方案2DIP盈亏'] = ai_score * (ai_rate - Decimal("2") + Decimal("1.1217")) * type - total_fee
                else:
                    logger.error(f"2异常 {item}")

                if item.get('AI方案2DIP盈亏', 0) and item.get('AI方案2DIP盈亏', 0) > good_jieyu:
                    good_rate = ai_rate
                    good_score = ai_score
                    good_group = item.get('AI方案2DIP代码', '')
                    good_group_name = item.get('AI方案2DIP名称', '')
                    good_jieyu = item.get('AI方案2DIP盈亏', '')
                    good_source = "AI方案2"
            except Exception:
                logger.error(f"AI方案2DIP 数据异常 {item}")

        if item.get('AI方案3DIP代码', ''):
            # J96.9-null && 未特指的呼吸衰竭:保守治疗 && 1099.64 && 0.59 && 核心病组
            try:
                # ai_rate = Decimal(str(item.get('AI方案3DIP倍率')))
                ai_score = Decimal(str(item.get('AI方案3DIP分值')))
                try:
                    ai_rate = total_fee / (ai_score * Decimal("5.72183"))
                    item['AI方案3DIP倍率'] = ai_rate
                except:
                    ai_rate = Decimal("0")

                if ai_rate <= Decimal("0.5"):
                    # (病例校正分值＝基准分值*倍率)*点值-总费用
                    item['AI方案3DIP盈亏'] = ai_score * ai_rate * type - total_fee
                elif ai_rate > Decimal("0.5") and ai_rate <= Decimal("2"):
                    # (病例校正分值＝基准分值*倍率)*1.1217-总费用
                    item['AI方案3DIP盈亏'] = ai_score * Decimal("1.1217") * type - total_fee
                elif ai_rate > Decimal("2"):
                    # (病例校正分值＝基准分值*（倍率-2+1.1217）)*点值-总费用
                    item['AI方案3DIP盈亏'] = ai_score * (ai_rate - Decimal("2") + Decimal("1.1217")) * type - total_fee
                else:
                    print(f"3异常 {item}")

                if item.get('AI方案3DIP盈亏', 0) and item.get('AI方案3DIP盈亏', 0) > good_jieyu:
                    good_rate = ai_rate
                    good_score = ai_score
                    good_group = item.get('AI方案3DIP代码', '')
                    good_group_name = item.get('AI方案3DIP名称', '')
                    good_jieyu = item.get('AI方案3DIP盈亏', '')
                    good_source = "AI方案3"
            except Exception:
                logger.error(f"AI方案3DIP 数据异常 {item}")

        item['最终DIP代码'] = good_group
        item['最终DIP名称'] = good_group_name
        item['最终DIP分值'] = good_score
        item['最终DIP倍率'] = good_rate
        item['最终DIP盈亏'] = good_jieyu
        item['最终DIP来源'] = good_source

        update_sql = """
            UPDATE nsyy_gyl.dip_patient  SET 
                `AI方案1DIP代码` = %s,
                `AI方案1DIP名称` = %s,
                `AI方案1DIP分值` = %s,
                `AI方案1DIP盈亏` = %s,
                `AI方案1DIP倍率` = %s,
                `AI方案1DIP入组类型` = %s,
                `AI方案1DIP入组原因` = %s,
                `AI方案2DIP代码` = %s,
                `AI方案2DIP名称` = %s,
                `AI方案2DIP分值` = %s,
                `AI方案2DIP盈亏` = %s,
                `AI方案2DIP倍率` = %s,
                `AI方案2DIP入组类型` = %s,
                `AI方案2DIP入组原因` = %s,
                `AI方案3DIP代码` = %s,
                `AI方案3DIP名称` = %s,
                `AI方案3DIP分值` = %s,
                `AI方案3DIP盈亏` = %s,
                `AI方案3DIP倍率` = %s,
                `AI方案3DIP入组类型` = %s,
                `AI方案3DIP入组原因` = %s,
                `最终DIP代码` = %s,
                `最终DIP名称` = %s,
                `最终DIP分值` = %s,
                `最终DIP倍率` = %s,
                `最终DIP盈亏` = %s,
                `最终DIP来源` = %s
            WHERE 医保结算流水号 = %s
        """

        args = (
            safe_value(item.get('AI方案1DIP代码'), numeric=False),
            safe_value(item.get('AI方案1DIP名称'), numeric=False),
            safe_value(item.get('AI方案1DIP分值'), numeric=True),
            safe_value(item.get('AI方案1DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案1DIP倍率'), numeric=True),
            safe_value(item.get('AI方案1DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案1DIP入组原因'), numeric=False),

            safe_value(item.get('AI方案2DIP代码'), numeric=False),
            safe_value(item.get('AI方案2DIP名称'), numeric=False),
            safe_value(item.get('AI方案2DIP分值'), numeric=True),
            safe_value(item.get('AI方案2DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案2DIP倍率'), numeric=True),
            safe_value(item.get('AI方案2DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案2DIP入组原因'), numeric=False),

            safe_value(item.get('AI方案3DIP代码'), numeric=False),
            safe_value(item.get('AI方案3DIP名称'), numeric=False),
            safe_value(item.get('AI方案3DIP分值'), numeric=True),
            safe_value(item.get('AI方案3DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案3DIP倍率'), numeric=True),
            safe_value(item.get('AI方案3DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案3DIP入组原因'), numeric=False),

            safe_value(item.get('最终DIP代码'), numeric=False),
            safe_value(item.get('最终DIP名称'), numeric=False),
            safe_value(item.get('最终DIP分值'), numeric=True),
            safe_value(item.get('最终DIP倍率'), numeric=True),
            safe_value(item.get('最终DIP盈亏'), numeric=True),
            safe_value(item.get('最终DIP来源'), numeric=False),
                item.get('医保结算流水号')
            )

        try:
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                        global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                db.execute(update_sql, args, need_commit=True)
        except Exception:
            logger.error(f"更新数据异常 {item}")


def handle_ai_dip1(data):
    ai_dip_dict = {item.get('jiesuanid'): item for item in data}

    jiesuanids = ','.join([f"'{item}'" for item in ai_dip_dict.keys()])
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        patient_list = db.query_all(f"SELECT * FROM nsyy_gyl.dip_patient where 医保结算流水号 in ({jiesuanids})")

    for item in patient_list:
        jiesuanid = item.get('医保结算流水号')
        ai_dip_info = ai_dip_dict.get(jiesuanid)

        type = Decimal("4") if str(item.get('患者费别', '')).__contains__('居民') else Decimal("4.4")
        try:
            total_fee = Decimal(str(item.get('总费用', '0')))
        except:
            total_fee = Decimal("0")
        ai_sort = handle_recommendations(ai_dip_info.get('recommendations', []), total_fee, type, item.get('出院科室'))

        item['AI方案1DIP代码'] = ai_sort[0].get('dip_code') if len(ai_sort) > 0 else ''
        item['AI方案1DIP名称'] = ai_sort[0].get('dip_name') if len(ai_sort) > 0 else ''
        item['AI方案1DIP分值'] = ai_sort[0].get('score') if len(ai_sort) > 0 else ''
        item['AI方案1DIP倍率'] = ai_sort[0].get('dip_rate') if len(ai_sort) > 0 else ''
        item['AI方案1DIP盈亏'] = ai_sort[0].get('yk') if len(ai_sort) > 0 else ''
        item['AI方案1DIP入组类型'] = ai_sort[0].get('type') if len(ai_sort) > 0 else ''
        item['AI方案1DIP入组原因'] = ai_sort[0].get('reason') if len(ai_sort) > 0 else ''

        item['AI方案2DIP代码'] = ai_sort[1].get('dip_code') if len(ai_sort) > 1 else ''
        item['AI方案2DIP名称'] = ai_sort[1].get('dip_name') if len(ai_sort) > 1 else ''
        item['AI方案2DIP分值'] = ai_sort[1].get('score') if len(ai_sort) > 1 else ''
        item['AI方案2DIP倍率'] = ai_sort[1].get('dip_rate') if len(ai_sort) > 1 else ''
        item['AI方案2DIP盈亏'] = ai_sort[1].get('yk') if len(ai_sort) > 1 else ''
        item['AI方案2DIP入组类型'] = ai_sort[1].get('type') if len(ai_sort) > 1 else ''
        item['AI方案2DIP入组原因'] = ai_sort[1].get('reason') if len(ai_sort) > 1 else ''

        item['AI方案3DIP代码'] = ai_sort[2].get('dip_code') if len(ai_sort) > 2 else ''
        item['AI方案3DIP名称'] = ai_sort[2].get('dip_name') if len(ai_sort) > 2 else ''
        item['AI方案3DIP分值'] = ai_sort[2].get('score') if len(ai_sort) > 2 else ''
        item['AI方案3DIP倍率'] = ai_sort[2].get('dip_rate') if len(ai_sort) > 2 else ''
        item['AI方案3DIP盈亏'] = ai_sort[2].get('yk') if len(ai_sort) > 2 else ''
        item['AI方案3DIP入组类型'] = ai_sort[2].get('type') if len(ai_sort) > 2 else ''
        item['AI方案3DIP入组原因'] = ai_sort[2].get('reason') if len(ai_sort) > 2 else ''

        if len(ai_sort) > 0 and ai_sort[0].get('yk', 0) > Decimal(str(item.get('现DIP盈亏'))) :
            item['最终DIP代码'] = ai_sort[0].get('dip_code')
            item['最终DIP名称'] = ai_sort[0].get('dip_name')
            item['最终DIP分值'] = ai_sort[0].get('score')
            item['最终DIP倍率'] = ai_sort[0].get('dip_rate')
            item['最终DIP盈亏'] = ai_sort[0].get('yk')
            item['最终DIP来源'] = "AI方案一"
        else:
            good_rate = item.get('现DIP倍率')
            good_score = item.get('现DIP分值')
            good_group = item.get('现DIP代码')
            good_group_name = item.get('现DIP名称')
            good_jieyu = Decimal(str(item.get('现DIP盈亏')))
            good_source = "科室"
            item['最终DIP代码'] = item.get('现DIP代码')
            item['最终DIP名称'] = item.get('现DIP名称')
            item['最终DIP分值'] = item.get('现DIP分值')
            item['最终DIP倍率'] = item.get('现DIP倍率')
            item['最终DIP盈亏'] = item.get('现DIP盈亏')
            item['最终DIP来源'] = "科室"

        update_sql = """
            UPDATE nsyy_gyl.dip_patient  SET 
                `AI方案1DIP代码` = %s,
                `AI方案1DIP名称` = %s,
                `AI方案1DIP分值` = %s,
                `AI方案1DIP盈亏` = %s,
                `AI方案1DIP倍率` = %s,
                `AI方案1DIP入组类型` = %s,
                `AI方案1DIP入组原因` = %s,
                `AI方案2DIP代码` = %s,
                `AI方案2DIP名称` = %s,
                `AI方案2DIP分值` = %s,
                `AI方案2DIP盈亏` = %s,
                `AI方案2DIP倍率` = %s,
                `AI方案2DIP入组类型` = %s,
                `AI方案2DIP入组原因` = %s,
                `AI方案3DIP代码` = %s,
                `AI方案3DIP名称` = %s,
                `AI方案3DIP分值` = %s,
                `AI方案3DIP盈亏` = %s,
                `AI方案3DIP倍率` = %s,
                `AI方案3DIP入组类型` = %s,
                `AI方案3DIP入组原因` = %s,
                `最终DIP代码` = %s,
                `最终DIP名称` = %s,
                `最终DIP分值` = %s,
                `最终DIP倍率` = %s,
                `最终DIP盈亏` = %s,
                `最终DIP来源` = %s
            WHERE 医保结算流水号 = %s
        """

        args = (
            safe_value(item.get('AI方案1DIP代码'), numeric=False),
            safe_value(item.get('AI方案1DIP名称'), numeric=False),
            safe_value(item.get('AI方案1DIP分值'), numeric=True),
            safe_value(item.get('AI方案1DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案1DIP倍率'), numeric=True),
            safe_value(item.get('AI方案1DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案1DIP入组原因'), numeric=False),

            safe_value(item.get('AI方案2DIP代码'), numeric=False),
            safe_value(item.get('AI方案2DIP名称'), numeric=False),
            safe_value(item.get('AI方案2DIP分值'), numeric=True),
            safe_value(item.get('AI方案2DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案2DIP倍率'), numeric=True),
            safe_value(item.get('AI方案2DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案2DIP入组原因'), numeric=False),

            safe_value(item.get('AI方案3DIP代码'), numeric=False),
            safe_value(item.get('AI方案3DIP名称'), numeric=False),
            safe_value(item.get('AI方案3DIP分值'), numeric=True),
            safe_value(item.get('AI方案3DIP盈亏'), numeric=True),
            safe_value(item.get('AI方案3DIP倍率'), numeric=True),
            safe_value(item.get('AI方案3DIP入组类型'), numeric=False),
            safe_value(item.get('AI方案3DIP入组原因'), numeric=False),

            safe_value(item.get('最终DIP代码'), numeric=False),
            safe_value(item.get('最终DIP名称'), numeric=False),
            safe_value(item.get('最终DIP分值'), numeric=True),
            safe_value(item.get('最终DIP倍率'), numeric=True),
            safe_value(item.get('最终DIP盈亏'), numeric=True),
            safe_value(item.get('最终DIP来源'), numeric=False),
                item.get('医保结算流水号')
            )

        try:
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                        global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
                db.execute(update_sql, args, need_commit=True)

            logger.debug(f"更新数据成功 {jiesuanid}")
        except Exception:
            logger.error(f"更新数据异常 {item}")


def handle_recommendations(recommendations, total_fee, type_value, dept_name):
    results = []
    for item in recommendations:
        if not (item.get('dip_code') and item.get('dip_name')):
            continue

        if not is_number(item.get('dip_rate')) or not is_number(item.get('score')):
            continue

        ai_score = Decimal(str(item.get('score')))
        if ai_score == Decimal("0"):
            continue

        res = {
            "dip_code": item.get('dip_code'),
            "dip_name": item.get('dip_name'),
            "dip_rate": 0,
            "score": item.get('score'),
            "yk": 0,
            "type": item.get('type'),
            "reason": item.get('reason')
        }
        if item.get('dip_name').__contains__('床日病种'):
            res['yk'] = ai_score * type_value - total_fee
        else:
            ai_rate = total_fee / (ai_score * Decimal("5.72183"))
            res['dip_rate'] = ai_rate
            xishu = Decimal("1.1217")
            if dept_name in ['脑病康复科一区', '脑病康复科二区', '脑病康复科三区', '内科', '儿童康复科', '中医日间病房', '骨伤康复科/老年康复科']:
                xishu = Decimal("1.0620")
            if ai_rate <= Decimal("0.5"):
                # (病例校正分值＝基准分值*倍率)*点值-总费用
                res['yk'] = ai_score * ai_rate * type_value - total_fee
            elif ai_rate > Decimal("0.5") and ai_rate <= Decimal("2"):
                # (病例校正分值＝基准分值*倍率)*1.1217-总费用
                res['yk'] = ai_score * xishu * type_value - total_fee
            elif ai_rate > Decimal("2"):
                # (病例校正分值＝基准分值*（倍率-2+1.1217）)*点值-总费用
                res['yk'] = ai_score * (ai_rate - Decimal("2") + xishu) * type_value - total_fee
            else:
                logger.error(f"2异常 {item}")
        results.append(res)

    results = sorted(results, key=lambda x: x['yk'], reverse=True)
    return results


def is_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def query_dept_patients(dept_names, start_date, end_date):
    depts = ','.join([f"'{item}'" for item in dept_names])
    sql = f"""SELECT 住院医师, 住院号, 住院次数, 入院时间, 出院时间, 出院科室, 出院记录, 医保结算流水号, 
            医嘱, 年龄, 性别, 总费用, 患者费别, 手术, 手术记录, 病案诊断, 诊断, 现DIP代码 
            FROM nsyy_gyl.dip_patient where 出院科室 in ({depts}) and 
            出院时间 between '{start_date} 00:00:00' and '{end_date}  23:59:59' and 最终DIP代码 is null """
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        patient_list = db.query_all(sql)
    return patient_list



if __name__ == "__main__":
    start_time = time.time()

    # unmedical_page_list()
    # query_medical_page_update_record()
    #
    # print(datetime.now(), "dip 数据查询耗时", time.time() - start_time)
    #
    # data = {
    #     "jiesuanid": "20260301104741791070",
    #     "total_fee": "3798.17",
    #     "recommendations": [
    #         {
    #             "rank": 1,
    #             "dip_code": "O80.000-null",
    #             "dip_name": "头位顺产:保守治疗",
    #             "dip_rate": 0.67,
    #             "score": 990.00,
    #             "type": "核心病组",
    #             "reason": "顺产为主诊断，倍率优。"
    #         },
    #         {
    #             "rank": 2,
    #             "dip_code": "O99.005-null",
    #             "dip_name": "妊娠合并轻度贫血:保守治疗",
    #             "dip_rate": 0.74,
    #             "score": 900.00,
    #             "type": "核心病组",
    #             "reason": "贫血作为合并症，倍率接近0.79。"
    #         }
    #     ]
    # }
    # res = handle_recommendations(data.get('recommendations'), Decimal(data.get('total_fee')), Decimal("4"))
    # for item in res:
    #     print(item)
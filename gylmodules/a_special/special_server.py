import json
import time
from datetime import datetime

import redis
import requests

from gylmodules import global_config, global_tools

import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

        item['patientId'] = item.get('bingrenzyid', '')
        item['patientName'] = item.get('xingming', '')
        item['patientDept'] = item.get('dangqianksmc', '')
        item['zhuyuanysxm'] = item.get('zhuyuanysxm', '')
        item['ruyuanrq'] = item.get('ruyuanrq')
        item['zhenduan'] = item.get('zhenduan', '')

        redis_client.hset('dip_patients', item.get('bingrenzyid'), json.dumps(item, ensure_ascii=False, default=str))

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

    redis_client.hset('dip_patients', bingrenzyid, json.dumps(patient_info, ensure_ascii=False, default=str))
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
                logger.info(f"OCR 识别成功，第 {attempt} 次尝试")
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

if __name__ == "__main__":
    start_time = time.time()

    unmedical_page_list()
    query_medical_page_update_record()

    print(datetime.now(), "dip 数据查询耗时", time.time() - start_time)
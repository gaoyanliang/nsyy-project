import json
import logging
import time
import redis

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from topsdk.ability2940.request.alibaba_alihealth_drugtrace_top_yljg_query_codedetail_request import *

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

redis_key = "zhuisuma_redis_key"

def save_codes(codes):
    if not codes:
        return ''
    submit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    batch_id = datetime.now().strftime('%Y%m%d%H%M%S')
    code_list = [(code, batch_id, submit_time) for code in codes]

    insert_sql = f"""INSERT INTO zhuisuma_codes (code, batch_id, submit_time) VALUES (%s, %s, %s) 
                    ON DUPLICATE KEY UPDATE code = VALUES(code), batch_id = VALUES(batch_id), 
                      submit_time = VALUES(submit_time)"""

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 插入新批次
    db.execute_many(insert_sql, code_list, need_commit=True)
    del db

    redis_client = redis.Redis(connection_pool=pool)
    redis_client.delete(redis_key)

    return batch_id


# API: 获取历史数据
def get_history():
    query_sql = f"""select * from zhuisuma_codes """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # 插入新批次
    data = db.query_all(query_sql)
    del db

    return data



def auto_query_code():
    redis_client = redis.Redis(connection_pool=pool)
    if redis_client.exists(redis_key):
        return

    start_time = time.time()
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    zsm_codes = db.query_all(f"select * from nsyy_gyl.zhuisuma_codes where standard_name is null order by submit_time desc limit 10")

    if not zsm_codes:
        del db
        redis_client.set(redis_key, 1)
        return

    codes = [zsm_code.get("code") for zsm_code in zsm_codes]
    code_info = get_yaopin_info_from_ali(codes)
    code_dict = {str(info.get('追溯码')): info for info in code_info}

    update_data = []
    for zsm_code in zsm_codes:
        code = zsm_code.get("code")
        info = code_dict.get(code)
        if not info:
            continue
        update_data.append((code, zsm_code.get('batch_id'), zsm_code.get('submit_time'), info.get('药品名称'),
             json.dumps(info, ensure_ascii=False, default=str)))

    insert_sql = f"""INSERT INTO zhuisuma_codes (code, batch_id, submit_time, standard_name, code_info) VALUES (%s, %s, %s, %s, %s) 
                    ON DUPLICATE KEY UPDATE standard_name = VALUES(standard_name), code_info = VALUES(code_info) """
    # 插入新批次
    db.execute_many(insert_sql, update_data, need_commit=True)
    del db
    logger.info(f"更新数据完成 耗时 {time.time() - start_time}")


# 根据追溯码查询药品信息
def get_yaopin_info_from_ali(codes):
    from topsdk.client import TopApiClient, TopException
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        urllib3.disable_warnings(InsecureRequestWarning)

        from topsdk.ability2940.ability2940 import Ability2940
        # create Client
        # 码上放心： https://www.mashangfangxin.com/?spm=a21f6.8078396.0.0.7fc268578w8mnX
        # https://qg6r2i.yuque.com/qg6r2i/csvggm/ob21cg2o4e19k0gd?singleDoc#NpWeW
        # SDK： https://open.taobao.com/doc.htm?spm=a219a.15212433.0.0.40f5669a2Twqry&docId=101618&docType=1
        # 接口说明：https://open.taobao.com/api.htm?docId=52567&docType=2&scopeId=20981#scopes
        client = TopApiClient(appkey='35075242', app_sercet='284fcbdb6bfde85e1ae69f301559db95',
                              top_gateway_url='https://eco.taobao.com/router/rest', verify_ssl=False)
        ability = Ability2940(client=client)

        # create request
        request = AlibabaAlihealthDrugtraceTopYljgQueryCodedetailRequest()
        request.ref_ent_id = '2c9194c61f491ebc011f6420d3cc51c3'
        request.codes = codes

        response = ability.alibaba_alihealth_drugtrace_top_yljg_query_codedetail(request)
        data = response.get('result', {}).get('models', [])
        if not data:
            return []

        print(f"查询追溯码信息成功 {data}")
        ret = []
        for m in data:
            ret.append(organize_data(m))
        return ret
    except TopException as e:
        logger.error("查询追溯码信息异常", codes, e)
        return []


def organize_data(model):
    if not model:
        return {}
    produce = model.get("code_produce_info_d_t_o", {}).get("produce_info_list", [{}])[0]
    drug = model.get("drug_ent_base_d_t_o", {})
    ent = model.get("p_user_ent_d_t_o", {})
    status = model.get("code_status_type_d_t_o", {})
    return {
        "追溯码": model.get("code"),
        "药品名称": drug.get("physic_name") ,
        "码状态": status.get("code_status"),
        "码等级(3大码 2中码 1小码)": model.get("package_level"),
        "药品类型描述": drug.get("prepn_type_desc"),
        "包装规格": drug.get("pkg_spec_crit"),
        "制剂规格": drug.get("prepn_spec"),
        "剂型描述": drug.get("prepn_type_desc"),
        "有效期": drug.get("exprie"),
        "批准文号": drug.get("approval_licence_no"),
        "药品id": drug.get("drug_ent_base_info_id"),
        "企业名称": ent.get("ent_name"),
        "企业id": ent.get("ref_ent_id"),
        "批次号": produce.get("batch_no"),
        "生产日期": produce.get("produce_date_str"),
        "原始生产日期": produce.get("original_produce_date"),
        "有效期至": produce.get("expire_date"),
        "原始有效期": produce.get("original_expire_date"),
        "最小包装数量": produce.get("pkg_amount"),
    }



# data = get_yaopin_info_from_ali(['84556710735757958955'])
#
# print(data)


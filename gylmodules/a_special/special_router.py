import json
from datetime import datetime

from flask import Blueprint

from gylmodules import global_config, global_tools
from gylmodules.global_tools import api_response
from gylmodules.utils.db_utils import DbUtil

special_system = Blueprint('special system', __name__, url_prefix='/special')

# 手术流转接口 扫描患者腕带 查询患者信息
# 要求： 读取患者腕带或手术申请二维码，获取手术相关信息，包括手术部位，术式，麻醉方式等信息

@special_system.route('/surgical_transfer', methods=['POST', 'GET'])
@api_response
def surgical_transfer_query(json_data):
    data = surgical_transfer_data(json_data)
    return data


"""患者手术流转数据查询"""


def surgical_transfer_data(json_data):
    patient_id = json_data.get('patient_code')
    if not patient_id or not str(patient_id).startswith('BR'):
        raise Exception(f'患者腕带数据异常, 期望: BR|病人ID｜住院次数, 实际: {patient_id}')
    scan_timing = json_data.get('scan_timing')
    split_data = patient_id.split('|')
    patient_id, number = split_data[1], split_data[2]

    sql = f"""select ss.shoushudanid , zb.xingming 姓名, zb.dangqianksmc 科室, zb.zhuyuanhao 住院号,
	        zb.dangqiancwbm 床号, zb.nianling  年龄, ss.bingrenid , ss.shoushubw 手术部位,
	        ss.shoushumc || coalesce('+' || ss.shoushumc1, '')|| coalesce('+' || ss.shoushumc2,
	        '')|| coalesce('+' || ss.shoushumc3, '')|| coalesce('+' || ss.shoushumc4, 
            '')|| coalesce('+' || ss.shoushumc5, '') 手术名称, gd.daimamc || case when gd2.daimamc is not null
		and gd.daimamc <> gd2.daimamc then '+' || gd2.daimamc else ''
	    end 麻醉方式,
	to_char(ss.anpaisj, 'YYYY-MM-DD HH24:MI:SS') 手术安排时间, ss.zhenduanmc1 诊断 from df_jj_zhuyuan.zy_bingrenxx zb
    join df_shenqingdan.sm_shoushuxx ss on zb.bingrenzyid = ss.bingrenzyid and ss.zuofeibz = '0'
	and ss.zhuangtaibz in (6, 7) left join df_zhushuju.gy_daima gd on ss.mazuiff = gd.daimaid
	and gd.daimalb = '10078' left join df_zhushuju.gy_daima gd2 on ss.mazuiff1 = gd2.daimaid
	and gd2.daimalb = '10078' 
    where ss.anpaisj >= now()::date and ss.anpaisj < now()::date + interval '1 day' and ss.bingrenid = '{patient_id}'
    -- where ss.anpaisj >= '2025-12-16' and ss.anpaisj < '2025-12-17' and ss.bingrenid = '10190159'
    """
    data = global_tools.call_new_his_pg(sql)
    if not data:
        return {}

    shoushudanids = [str(item.get('shoushudanid')) for item in data]
    shoushudanids = ','.join([f"'{item}'" for item in shoushudanids])
    sql = f"""
        select t.sam_apply_id,
           t.in_oproom_date   入手术室时间,
           t.out_oproom_date  出手术室时间,
           t.oper_beging_date 手术开始时间,
           t.oper_end_date    手术结束时间
      from sam_anar t
     where t.sam_apply_id in ({shoushudanids})
    """
    shijian = global_tools.call_new_his(sql, 'nsshouma')
    shijian_dict = {}
    for item in shijian:
        shijian_dict[item.get('SAM_APPLY_ID')] = item

    for item in data:
        item.update(shijian_dict.get(item.get('shoushudanid'), {}))

    data = data[0]
    patient_name = data.get('姓名', '')
    data['record_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = """INSERT INTO nsyy_gyl.a_surgical_transfer (patient_id, number, patient_name, patient_info,
                                    timing, record_time) VALUES (%s, %s, %s, %s, %s, %s)"""
    args = (patient_id, number, patient_name, json.dumps(data, ensure_ascii=False, default=str),
            scan_timing, data['record_time'])
    db.execute(insert_sql, args, need_commit=True)
    del db
    return data


# json_data = {
#     "patient_code": "BR|10151903|1",
#     "scan_timing": 1
# }
#
# surgical_transfer_data(json_data)















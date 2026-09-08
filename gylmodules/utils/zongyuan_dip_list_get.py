import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests
from typing import List, Dict, Any

from gylmodules import global_tools, global_config
from gylmodules.utils.db_utils_new import DbUtil

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("zongyuan_dip_list_get.log")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# 每天定时从 365 清单指控中抓取数据 同步到 dip_patient 表中



class PunuoClient:
    """普诺系统API客户端，封装登录和患者数据查询"""

    BASE_URL = "http://192.168.9.26:9081"
    LOGIN_PATH = "/punuo/user/login"
    # 清单指控
    QUERY_PATH = "/punuo/pnQdlb/qdDataList"

    """
    初始化客户端并自动登录
    :param user_id: 登录用户名
    :param password: 登录密码
    :param keep_alive: 保持登录标志，默认1
    :param log_level: 日志级别，如 logging.DEBUG
    """
    def __init__(self, user_id: str = "", password: str = "", keep_alive: int = 1, log_level: int = logging.INFO):
        self.user_id = user_id
        self.password = password
        self.keep_alive = keep_alive
        self.token = None
        self.login_status = False
        # 从原始 INSERT 提取的所有字段名（按顺序）
        self.FIELDS = [
            "医保结算流水号", "姓名", "患者费别", "总费用", "出院科室", "住院医师",
            "现DIP代码", "现DIP名称", "现DIP分值", "现DIP盈亏", "现DIP倍率",
            "住院号", "住院次数", "入院时间", "出院时间", "年龄", "性别",
            "诊断", "病案诊断", "手术", "医嘱", "出院记录",
            "手术记录", "入院记录", "来源", "检查", "检验", "治疗医嘱", "用药医嘱"
        ]

        # 主键字段（用于冲突检测）
        self.PRIMARY_KEY = "医保结算流水号"
        logger.info("初始化 PunuoClient，用户: %s", user_id)
        self._login()


    """执行登录，获取token"""
    def _login(self):
        url = self.BASE_URL + self.LOGIN_PATH
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9", "Connection": "keep-alive",
            "Content-Type": "application/json", "Origin": "http://192.168.9.26", "Referer": "http://192.168.9.26/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        }
        payload = {"userId": self.user_id, "password": self.password, "keepAlive": self.keep_alive}
        logger.info("开始登录，URL: %s", url)

        max_retries, retry_count, retry_delay = 3, 0, 1
        while retry_count < max_retries:
            try:
                resp = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
                resp.raise_for_status()
                result = resp.json()
                logger.debug("登录响应: %s", result)
                # 根据实际响应结构提取token（这里假设 code=0 成功，data.token 存放token）
                if result.get("code") != 0:
                    raise Exception(f"登录失败: {result.get('message', '未知错误')}")
                token_data = result.get("data")
                if not token_data:
                    raise Exception("登录响应中无data字段")
                self.token = token_data.get("token")
                if not self.token:
                    raise Exception("登录响应中无token字段")
                logger.info(f"365登录成功，token: {self.token[:20]}...")
                self.login_status = True
                return
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    sleep_time = retry_delay * (2 ** (retry_count - 1))  # 指数退避
                    logging.warning(f"登录过程异常 {e}")
                    time.sleep(sleep_time)
                else:
                    logging.error(f"已达最大重试次数 {max_retries}。最后错误: {str(e)}")
                    return

    """构建查询请求头"""
    def _build_query_headers(self) -> Dict:
        if not self.token:
            raise RuntimeError("未获取到有效token，请先登录")
        return {
            "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive", "Content-Type": "application/json", "Origin": "http://192.168.9.26",
            "Referer": "http://192.168.9.26/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "token": self.token
        }

    """
    获取所有符合条件的患者数据（自动分页）
    :param query_type: 时间查询类型，4=按月，5=按时间段
    :param ratio_time: 时间值，按月如"2026-05"，按段如"2026-07-01,2026-07-17"
    :param department: 科室名称，默认为"呼吸与危重症医学科"
    :param page_size: 每页数量
    :param order_by: 排序字段
    :param is_asc: 是否升序，默认False（降序）
    :param hospital_zone_id: 院区ID
    :param extra_filters: 其他可选的过滤参数，如 requireMap 中的字段
    :return: 患者数据列表（每条记录为字典）
    """
    def get_patient_list(self, ratio_time: str = "2026-05",
            department: str = "", page_size: int = 200, **extra_filters) -> List[Dict[str, Any]]:
        # 构造基础查询参数（可扩展）
        base_payload = {
            "pageNo": 1, "pageSize": page_size, "timeModel": { "queryType": 5, "ratioTime": ratio_time},
            "requireMap": {"seachType": 1}, "requireList": {}, "basicMap": {}, "zk": {},
            "orderByColumn": "jssj", "isAsc": "desc", "hospitalZoneId": "B00001"
        }
        # 合并额外参数（支持覆盖）
        for key, value in extra_filters.items():
            if key not in ["requireMap", "requireList"]:
                base_payload[key] = value

        all_data = []
        page_no = 1
        while True:
            logger.debug(f"开始查询第 {page_no} 页")
            payload = base_payload.copy()
            payload["pageNo"] = page_no
            resp = requests.post(
                self.BASE_URL + self.QUERY_PATH,
                json=payload,
                headers=self._build_query_headers(),
                verify=False,
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            # 假设成功 code=0，数据在 data 中
            if result.get("code") != 0:
                raise Exception(f"查询失败: {result.get('message', '未知错误')}")

            data = result.get("data")
            if data is None:
                break

            # 常见分页结构：data.list 或 data.records 或 data 本身就是列表
            if isinstance(data, list):
                page_data = data
                total = len(data)  # 如果是列表，可能没有total，只能按长度判断
                # 此时无法准确知道总条数，只能假设本次返回数量小于page_size即结束
            elif isinstance(data, dict):
                page_data = data.get("list") or data.get("records") or data.get("rows") or []
                total = data.get("total", 0)
            else:
                page_data = []
                total = 0

            if not page_data:
                break

            all_data.extend(page_data)

            # 如果总条数已知，且已获取全部，则退出
            if total > 0 and len(all_data) >= total:
                break
            # 如果本次返回数量小于page_size，说明是最后一页
            if len(page_data) < page_size:
                break
            # 否则继续下一页
            page_no += 1

        if all_data:
            all_data = [self.map_patient_record_v2(item) for item in all_data]
            ret_d = []
            for item in all_data:
                try:
                    ret_d.append(self.map_patient_record_v2(item))
                except Exception as e:
                    logging.error(f"处理患者数据时出错: {str(e)}")
        logging.info(f"成功获取 {len(all_data)} 条患者数据")
        return all_data

    """将新查询接口返回的 JSON 记录映射为表头字段字典"""
    def map_patient_record_v2(self, record: dict) -> dict:
        # 性别映射
        gender_map = {'1': '男', '2': '女'}
        diprz = record.get('dipRz', '')
        diprzmc = record.get('dipRzdm', '').replace(f"{diprz}-", '')
        diprz = diprz.replace(':', '-')

        return {
            '病案号': record.get('bah', ''),
            '医保结算流水号': record.get('ybjslsh', ''),
            '患者费别': record.get('hzfb', ''),
            '住院号': record.get('zyh', ''),
            '住院次数': record.get('zycs', ''),
            'DIP倍率': record.get('dipJsFybl', ''),
            'DIP结余预测': record.get('dipJyyc', ''),
            '总费用': record.get('jehj', ''),
            'DIP入组代码': diprz,
            'DIP入组名称': diprzmc,
            '出院科室': record.get('cyks', ''),
            '住院医师': record.get('zyys') or record.get('zzys', ''),
            '入院时间': record.get('rysj', ''),
            '出院时间': record.get('cysj', ''),
            '姓名': record.get('xm', ''),
            '年龄': record.get('nl', ''),
            '性别': gender_map.get(record.get('xb', ''), '未知'),
            'DIP分值': record.get('dipFz', '') if not diprzmc.__contains__('康复病种') else str(record.get('dipJsJzfz', '')),
            '病种类别': record.get('dipBzlb', ''),
            'jssj': record.get('jssj', '')
        }

    """构建批量 upsert 的 SQL 模板（使用 %s 占位符） """
    def build_upsert_sql(self, fields: List[str], pk: str) -> str:
        placeholders = ", ".join(["%s"] * len(fields))
        field_names = ", ".join([f"`{f}`" for f in fields])

        # 更新部分：除主键外所有字段更新（也可只更新部分，但通常全部更新）
        update_parts = []
        for f in fields:
            if f != pk:
                update_parts.append(f"`{f}` = VALUES(`{f}`)")
        update_clause = ", ".join(update_parts)
        sql = f"""INSERT INTO dip_patient ({field_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"""
        return sql

    #
    def write_to_db(self, data):
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

        batch_size = 100
        total = len(id_list)
        for i in range(0, total, batch_size):
            batch = id_list[i:i + batch_size]
            logger.debug(f"处理第 {i // batch_size + 1} 批，共 {len(batch)} 条记录")
            ids = ','.join([f"'{item}'" for item in batch])

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
            sql = self.build_upsert_sql(self.FIELDS, self.PRIMARY_KEY)
            # 将字典转换为按 FIELDS 顺序的值元组列表
            rows = []
            for item in ret_list:
                # print(item)
                row = tuple(item.get(f) for f in self.FIELDS)
                rows.append(row)

            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL) as db:
            # with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
                db.execute_many(sql, rows, need_commit=True)
                logger.debug(f'写入 {len(rows)} 条数据')


def query_change_patients():
    sql = """
    select zb.bingrenzyid, zb.zhuyuanhao,zb.zhuyuancs ,null 病历名称,null 病历内容,'出院患者' as fl 
    from df_jj_zhuyuan.zy_bingrenxx zb 
    where zb.xingming not like '%测试%' 
    and zb.dangqianksmc not like '%测试%'
    and zb.dangqianbqmc not like '%测试%'
    and zb.quxiaorybz=0 and zb.yingerbz=0
    and zb.chuyuanrq>=now() -interval '1 day'
    and zb.feiyongxzmc <> '自费'
            union all 
    select zb.bingrenzyid, zb.zhuyuanhao,zb.zhuyuancs ,null 病历名称,null 病历内容,'清单变化患者' as fl 
    from df_jj_zhuyuan.zy_bingrenxx zb
    where
        (zb.chuyuanrq>=now()-interval '1 day') --在院或当前时间48小时内出院
        and zb.xingming not like '%测试%'
        and zb.dangqianksmc not like '%测试%'
        and zb.dangqianbqmc not like '%测试%'
        and zb.quxiaorybz = '0' and zb.yingerbz=0
         and zb.feiyongxzmc <> '自费'
        and exists  (
        select 1 from df_yiliaogl.gy_maidianrz gm where
            gm.mokuai = '病案首页'
            and gm.chuangjiansj>=now() - interval '1 day'
            and gm.xingwei = '保存'
            and gm.shujulyid = zb.bingrenzyid 
             )
            union all 	
    select zb.bingrenzyid, zb.zhuyuanhao ,zb.zhuyuancs,
    case wb.mobanlx when 'ChuYuanJL' then '出院记录' when 'RuYuanJL' then '入院记录' when 'SHOUSHUJL' then '手术记录' else null end as 病历名称,
    array_to_string(xpath('//*/text()', wb2.wenjiannr::xml), ' ') 病历内容,'病历修改患者' as fl 
    from df_bingli.ws_binglijl wb 
    join df_jj_zhuyuan.zy_bingrenxx zb on wb.bingrenzyid =zb.bingrenzyid   and zb.xingming not like '%测试%'
        and zb.dangqianksmc not like '%测试%'
        and zb.dangqianbqmc not like '%测试%'
        and zb.quxiaorybz = '0' and zb.yingerbz=0 and zb.chuyuanrq>=now() -interval '1 day'  and zb.feiyongxzmc <> '自费'
    join df_yiliaogl.gy_maidianrz gm on wb.binglijlid =gm.shujulyid and mokuai='病历文书' and gm.chuangjiansj>=now() - interval '1 day' and gm.xingwei = '保存'
    join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid 
    where wb.zuofeibz=0  and wb.mobanlx in ('ChuYuanJL','RuYuanJL','SHOUSHUJL')
    """
    data_list = global_tools.call_new_his_pg(sql)
    return data_list

"""单个查询函数，使用传入的 Session 复用连接"""
def get_dip_single(bingrenzyid: str, session: requests.Session):
    url = f"http://192.168.9.26:9081/punuo/ba/ast/get/res-info?glwybs={bingrenzyid}&userId=DBA&source=doctor"
    retry_times = 3
    while retry_times > 0:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data and (data.get('code', 1) == 0 or data.get('message', '') == "success"):
                return data.get('data')
            else:
                # 如果返回错误码，直接结束重试（可根据需要调整）
                return None
        except Exception as e:
            logger.error(f"请求失败 {e.__str__()}，重试次数：{retry_times}")
            retry_times -= 1
            if retry_times == 0:
                return None
            time.sleep(0.5)  # 重试前短暂等待
    return None

def get_dip_batch(id_list: List[str], max_workers: int = 10):
    """批量并发查询 DIP 信息"""
    if not id_list:
        return {}

    # 每个线程使用独立的 Session（requests.Session 非线程安全，建议每个线程新建）
    def worker(bingrenzyid: str) -> tuple:
        with requests.Session() as session:
            dip = get_dip_single(bingrenzyid, session)
            return bingrenzyid, dip

    result = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(worker, id_): id_ for id_ in id_list}
        for future in as_completed(future_to_id):
            id_ = future_to_id[future]
            try:
                _, dip = future.result()
                result[id_] = dip
            except Exception as e:
                logger.error(f"处理ID {id_} 时发生异常: {e}")
    return result



def handle_change_patients(change_patients, client):
    if not change_patients:
        return

    def handle_nianling(age):
        if str(age).__contains__('岁'):
            age = age.split('岁')[0]
        else:
            age = '1'
        return age

    ids = [item.get('bingrenzyid') for item in change_patients]
    ids = list(set(ids))
    logger.info(f"去重后一共得到 {len(ids)} 条需要更新的数据")
    ids = ','.join([f"'{item}'" for item in ids])
    sql = f"""
        with jy as (
        select
            bingrenzyid,
            string_agg(jg , '、') as jg
        from
            (
            select
                yj.bingrenzyid,
                yj.shenhesj::varchar || string_agg(yj1.zhongwenmc || ':' || yj1.jianyanjg || coalesce(yj1.dangwei, ''), '、') as jg
            from
                df_cdr.yj_jianyanbg yj
            join df_cdr.yj_jianyanbgmx yj1 on
                yj.jiluid = yj1.jiluid
            join df_jj_zhuyuan.zy_bingrenxx zb on
                yj.bingrenzyid = zb.bingrenzyid
            join df_jj_zhuyuan.zy_jiesuan1 zj on
                zb.bingrenzyid = zj.bingrenzyid
                and zb.jiesuanxh = zj.jiesuanxh
            join df_yibao.yb_zhuyuanjsxx yz on
                zj.yibaojsid = yz.zhuyuanjsid
                --and yz.yibaojyhm in ('20260302115236154400')
            where
                zb.bingrenzyid in ({ids})
            group by
                yj.bingrenzyid,
                yj.shenhesj
            order by
                yj.shenhesj )v
        group by
            bingrenzyid),
        yz1 as (
        select
            bingrenzyid,
            string_agg(治疗, '、') as 治疗
        from
            (
            select
                bingrenzyid,
                string_agg( '诊疗：' 
                    || yizhumc || ':' || to_char(shuliang, 'FM9999990') || coalesce(nullif(dw, ''), ' ') || ' 金额:' || to_char(je, 'FM9999990.00') , '、') as 治疗
            from
                ( select yb.bingrenzyid, yb.yizhuid, sum(zf.shuliang) shuliang, max(zf.jijiadw) dw, sum(zf.jiesuanje) je, yb.yizhufl, yb.yizhumc
                    from df_lc_zhuyuan.yz_bingrenyz yb
                    join df_zhushuju.yz_yizhuxm yy on yb.yizhuxmid = yy.yizhuxmid and yy.yizhulxid = '13'
                    join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid = zb.bingrenzyid
                    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
                    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
                    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid = zf.yizhuid
                    where yb.yizhuzt in ('3', '4') and zb.bingrenzyid in ({ids})
                    group by yb.bingrenzyid, yb.yizhuid having sum(zf.jiesuanje) >0
                    )v
            group by
                bingrenzyid
        union all
            select
                bingrenzyid,
                string_agg( '手术：' 
                        || yizhumc || ':' || to_char(shuliang, 'FM9999990') || coalesce(nullif(dw, ''), ' ') || ' 金额:' || to_char(je, 'FM9999990.00') , '、') as 治疗
            from
                ( select yb.bingrenzyid, yb.yizhuid, sum(zf.shuliang) shuliang, max(zf.jijiadw) dw, sum(zf.jiesuanje) je, yb.yizhufl, yb.yizhumc
                    from df_lc_zhuyuan.yz_bingrenyz yb join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid = zb.bingrenzyid
                    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
                    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
                    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid = zf.yizhuid
                    where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('25') and zb.bingrenzyid in ({ids})
                    group by yb.bingrenzyid, yb.yizhuid having sum(zf.jiesuanje) >0 )v
            group by
                bingrenzyid
                    )z
        group by
            bingrenzyid),
        yz2 as (
        select
            bingrenzyid,
            string_agg( '用药：' 
                        || yizhumc || ':' || to_char(shuliang, 'FM9999990.00') || coalesce(dw, '') || ' 金额:' || to_char(je, 'FM9999990.00') , '、') filter (
            where yizhufl in ('11', '12', '13')) as 用药
        from
            (select yb.bingrenzyid, yb.yizhuid, sum(zf.shuliang) shuliang, max(zf.jijiadw) dw, sum(zf.jiesuanje) je, yb.yizhufl, yb.yizhumc
                    from df_lc_zhuyuan.yz_bingrenyz yb
                    join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid = zb.bingrenzyid
                    join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
                    join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
                    join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid = zf.yizhuid
                    where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('11', '12', '13') and zb.bingrenzyid in ({ids})
                    group by yb.bingrenzyid, yb.yizhuid having sum(zf.jiesuanje) >0 )v
        group by
            bingrenzyid)
        select
            zb.xingming ,
            zb.bingrenzyid,
            zb.zhuyuanhao ,
            zb.zhuyuancs,zb.nianling,zb.xingbiemc,zb.feiyongxzmc,zj.feiyonghj+zj.yingerfyhj,zb.dangqianksmc,zb.zhuyuanysxm,zb.ruyuanrq,zb.chuyuanrq, yz.yibaojyhm 医保结算流水号,
            zb.zhuyuanhao || '_' || zb.zhuyuancs yibaojyhm ,
            (
            select
                string_agg(case when zz.shunxuhao = 1 then '主要诊断：' else '其他诊断：' end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
                        '、' order by zz.shunxuhao)
            from
                df_jj_zhuyuan.zy_zhenduanzl zz
            where
                zz.bingrenzyid = zb.bingrenzyid
                and zz.zhenduanlb like '19%'
                and zz.zuofeibz = '0') 诊断,
            (
            select
                string_agg(case when bbx.shunxuhao = 1 then '主要诊断：'
                          else '其他诊断：' end || bbx.zhenduanmc || '(' || bbx.jibingbm || ')' , '、' order by bbx.shunxuhao)
            from
                df_bingangl.ba_bingrenjbxx bb
            join df_bingangl.ba_bingrenzd_xy bbx on
                bb.binganbrxh = bbx.binganbrxh
                and bbx.zuofeibz = '0'
                and bbx.zhenduanlb like '19%'
            where
                bb.hisbrzyid = zb.bingrenzyid) 病案诊断,
            (
            select
                string_agg(yj.baogaosj::varchar || yj.jianchaxmmc || ':' || nullif(yj.jianchasuojian, ''), '、' order by baogaosj asc)
            from
                df_cdr.yj_jianchabg yj
            where
                yj.bingrenzyid = zb.bingrenzyid
                and yj.zuofeibz = 0
                    ) 检查,
            jy.jg 检验,
            (
            select
                string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
                      '、' order by shunxuhao)
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
                      order by wb.jilusj)
            from
                df_bingli.ws_binglijl wb
            join df_bingli.ws_binglijlnr wb2 on
                wb.binglijlid = wb2.binglijlid
            where
                wb.bingrenzyid = zb.bingrenzyid
                and wb.zuofeibz = '0'
                and wb.wenshuzt = 2
                and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
            (
            select
                string_agg( (xpath ( 'string()' :: text, wb2.wenjiannr :: xml ))[1]::text,
                        '
                    '
                      order by wb.jilusj)
            from
                df_bingli.ws_binglijl wb
            join df_bingli.ws_binglijlnr wb2 on
                wb.binglijlid = wb2.binglijlid
            where
                wb.bingrenzyid = zb.bingrenzyid
                and wb.zuofeibz = '0'
                and wb.wenshuzt = 2
                and fuleimblx = 'RuYuanJLFL' )入院记录,
            (
            select
                string_agg( (xpath ( 'string()' :: text,
                        wb2.wenjiannr :: xml ))[1]::text,
                        '
                    '
                      order by wb.jilusj)
            from
                df_bingli.ws_binglijl wb
            join df_bingli.ws_binglijlnr wb2 on
                wb.binglijlid = wb2.binglijlid
            where
                wb.bingrenzyid = zb.bingrenzyid
                and wb.zuofeibz = '0'
                and wb.wenshuzt = 2
                and fuleimblx = 'ChuYuanJLFL' ) 出院记录 ,
            yz1.治疗 治疗医嘱,
            yz2.用药 用药医嘱
        from
            df_jj_zhuyuan.zy_bingrenxx zb
        left join df_jj_zhuyuan.zy_jiesuan1 zj on
            zb.bingrenzyid = zj.bingrenzyid
            and zb.jiesuanxh = zj.jiesuanxh
        left join df_yibao.yb_zhuyuanjsxx yz on
            zj.yibaojsid = yz.zhuyuanjsid
        left join jy on
            jy.bingrenzyid = zb.bingrenzyid
        left join yz1 on
            yz1.bingrenzyid = zb.bingrenzyid
        left join yz2 on
            yz2.bingrenzyid = zb.bingrenzyid
        where
            zb.bingrenzyid in ({ids})
"""

    start_time = time.time()
    data = global_tools.call_new_his_pg(sql)
    logger.info(f"查询数据耗时 {time.time() - start_time} 秒, 共查询到 {len(data)} 条数据")

    # 收集所有住院 ID（去重）
    id_list = list({item.get('bingrenzyid') for item in data if item.get('bingrenzyid')})

    # 批量并发获取 DIP 信息
    batch_start = time.time()
    dip_map = get_dip_batch(id_list, max_workers=20)  # 可根据实际调整并发数
    logger.info(f"批量获取DIP信息耗时 {time.time() - batch_start} 秒，共处理 {len(id_list)} 个ID")

    d_list = []
    for item in data:
        # 根据病人住院id 查询dip信息
        # dip_data = get_dip(item.get('bingrenzyid'))
        bingrenzyid = item.get('bingrenzyid')
        dip_data = dip_map.get(bingrenzyid)
        if not dip_data:
            logger.error(f"未找到病人 {item.get('bingrenzyid')} 的dip信息")
            continue
        d_list.append({
            "医保结算流水号": item.get('医保结算流水号') if item.get('医保结算流水号') else item.get('yibaojyhm'),
            "姓名": item.get('xingming'),
            "住院号": item.get('zhuyuanhao'),
            "年龄": handle_nianling(item.get('nianling')),
            "性别": item.get('xingbiemc'),
            "住院次数": item.get('zhuyuancs'),
            "出院科室": item.get('dangqianksmc'),
            "住院医师": item.get('zhuyuanysxm'),
            "入院时间": item.get('ruyuanrq'),
            "出院时间": item.get('chuyuanrq'),
            "来源": "南阳南石医院",
            '诊断': item.get('诊断'),
            '病案诊断': item.get('病案诊断'),
            '手术': item.get('手术'),
            '检查': item.get('检查'),
            '检验': item.get('检验'),
            '手术记录': item.get('手术记录'),
            '出院记录': item.get('出院记录'),
            '入院记录': item.get('入院记录'),
            '治疗医嘱': item.get('治疗医嘱'),
            '用药医嘱': item.get('用药医嘱'),
            "患者费别": dip_data.get('ylfkfs', '居民'),
            "病种类别": dip_data.get('dipDrg', {}).get('dipBzlb', ''),
            "总费用": dip_data.get('dipDrg', {}).get('zfy', ''),
            "现DIP代码": dip_data.get('dipDrg', {}).get('dipRz', ''),
            "现DIP名称": dip_data.get('dipDrg', {}).get('dipRzmc', ''),
            "现DIP分值": dip_data.get('dipDrg', {}).get('dipMlfz', ''),
            "现DIP盈亏": dip_data.get('dipDrg', {}).get('dipJsJyyg', ''),
            "现DIP倍率": dip_data.get('dipDrg', {}).get('dipJsFybl', '')
        })

    # for item in d_list:
    #     print(item)

    # 在这里处理每一批数据
    sql = client.build_upsert_sql(client.FIELDS, client.PRIMARY_KEY)
    # 将字典转换为按 FIELDS 顺序的值元组列表
    rows = []
    for item in d_list:
        row = tuple(item.get(f) for f in client.FIELDS)
        rows.append(row)

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL) as db:
    # with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
        db.execute_many(sql, rows, need_commit=True)
        logger.info(f'写入 {len(rows)} 条出院但是还没有结算的患者数据')


# ---------- 使用示例 ----------
if __name__ == "__main__":
    # print(get_dip("6855491"))

    # 实例化客户端（若用户名密码为空则使用默认）
    start_time = time.time()
    client = PunuoClient(user_id="0105", password="liuyi2025")
    if not client.login_status:
        logger.error("登录异常, 无法查询数据，程序退出")
        exit(0)
    try:
        # 1. 每天更新前1天的出院患者（防止漏数据 更新三天的）
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=50)
        all_get_patients = client.get_patient_list(ratio_time=f"{start_date},{end_date}")
        logger.info(f"一共查询到 {len(all_get_patients)} 条记录，准备写入数据库")

        # 1.1 将 住院号_住院次数 的医保结算流水号更新为 真正的医保结算流水号
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL) as db:
        # with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
            need_update = db.query_all("SELECT 医保结算流水号 FROM nsyy_gyl.dip_patient "
                                       "where 医保结算流水号 = CONCAT(住院号, '_', 住院次数) and 来源 = '南阳南石医院'")
        if need_update:
            need_update = [item.get('医保结算流水号') for item in need_update]
            all_id = {f"{item.get('住院号')}_{item.get('住院次数')}": item.get('医保结算流水号') for item in all_get_patients if item.get('医保结算流水号')}
            sql = """ UPDATE IGNORE nsyy_gyl.dip_patient
                    SET 医保结算流水号 = CASE
                """
            count = 0
            for item in need_update:
                if item in all_id:
                    count += 1
                    id = all_id[item]
                    item = item.split('_')
                    sql += f"WHEN 住院号 = '{item[0]}' AND 住院次数 = {item[1]} THEN '{id}'\n"
            sql += "END WHERE 医保结算流水号 = CONCAT(住院号, '_', 住院次数) and 来源 = '南阳南石医院'"
            if count > 0:
                db.execute(sql, need_commit=True)
            logger.info(f"更新了 {count} 条医保结算流水号")

        # 1.2 过滤掉2天前结算的数据
        filtered = [
            item for item in all_get_patients
            if item.get('jssj') and
               datetime.strptime(item.pop('jssj'), '%Y-%m-%d %H:%M:%S') >= (datetime.now() - timedelta(days=2))
        ]
        logging.info(f"一共过滤到 {len(filtered)} 条记录，准备写入数据库")

        # for item in filtered:
        #     print(item)
        client.write_to_db(filtered)
        logger.info(f"{start_date} - {end_date} 数据导入完成, 耗时 {time.time() - start_time} s")

        # 2. 查询 前一天更新的患者（出院患者/清单变化患者/病历修改患者）
        change_patients = query_change_patients()
        if not change_patients:
            logger.info("没有找到前一天需要更新的患者（出院患者/清单变化患者/病历修改患者）")
            exit(0)
        logger.info(f"一共查询到 {len(change_patients)} 条前一天需要更新的患者（出院患者/清单变化患者/病历修改患者）")
        # 过滤掉今天从365中更新的患者
        filtered = [f"{item.get('住院号')}_{item.get('住院次数')}" for item in filtered]
        need_update_change_patients = [item for item in change_patients if f"{item.get('zhuyuanhao')}_{item.get('zhuyuancs')}" not in filtered]
        logger.info(f"一共过滤出 {len(need_update_change_patients)} 条前一天需要更新的患者（出院患者/清单变化患者/病历修改患者）")

        # 3. 处理已出院但是还没有结算的患者（已出院但是365清单指控中找不到的患者）, 更新的患者也需要更新数据所以可以用同一个处理逻辑，但是更新的患者还需要第四步
        handle_change_patients(need_update_change_patients, client)

        # 4. 剩下变化的患者（出院患者/清单变化患者/病历修改患者） 都已经在表中，需要将AI结果清空 重新跑
        if not change_patients:
            ids = ','.join([f"('{item.get('住院号')}', {item.get('住院次数')})" for item in change_patients])
            # 如果已经跑过AI 数据了，则清空重新跑
            with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL) as db:
            # with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
                sql = f"""UPDATE nsyy_gyl.dip_patient SET
                    最终DIP代码 = NULL, 最终DIP名称 = NULL, 最终DIP分值 = NULL,  最终DIP盈亏 = NULL, 最终DIP倍率 = NULl, 最终DIP来源 = NULL,
                    AI方案1DIP代码 = NULL, AI方案1DIP名称 = NULL, AI方案1DIP分值 = NULL, AI方案1DIP盈亏 = NULL, AI方案1DIP倍率 = NULL, AI方案1DIP入组类型 = NULL,
                    AI方案2DIP代码 = NULL, AI方案2DIP名称 = NULL, AI方案2DIP分值 = NULL, AI方案2DIP盈亏 = NULL, AI方案2DIP倍率 = NULL, AI方案2DIP入组类型 = NULL,
                    AI方案3DIP代码 = NULL, AI方案3DIP名称 = NULL, AI方案3DIP分值 = NULL, AI方案3DIP盈亏 = NULL, AI方案3DIP倍率 = NULL, AI方案3DIP入组类型 = NULL,
                    AI方案分析 = NULL, AI方案1DIP入组原因 = NULL, AI方案2DIP入组原因 = NULL, AI方案3DIP入组原因 = NULL,  is_completed = 0
                    WHERE (住院号, 住院次数) IN ({ids})
                """
                db.execute(sql, need_commit=True)

    except Exception as e:
        logger.info(f"异常 {e.__str__()}, {traceback.print_exc()}")










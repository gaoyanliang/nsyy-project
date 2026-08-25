import logging
import time
import traceback
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from typing import List, Dict, Optional, Any
import urllib3

from gylmodules import global_tools
from gylmodules.utils.db_utils_new import DbUtil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PunuoClient:
    """普诺系统API客户端，封装登录和患者数据查询"""

    BASE_URL = "http://192.168.9.26:9081"
    LOGIN_PATH = "/punuo/user/login"
    # QUERY_PATH = "/punuo/pnQdlb/qdDataList"
    QUERY_PATH = "/punuo/hmPgData/pageHmBaDataList"

    def __init__(self, user_id: str = "", password: str = "", keep_alive: int = 1, log_level: int = logging.INFO):
        """
        初始化客户端并自动登录
        :param user_id: 登录用户名
        :param password: 登录密码
        :param keep_alive: 保持登录标志，默认1
        :param log_level: 日志级别，如 logging.DEBUG
        """
        self.user_id = user_id
        self.password = password
        self.keep_alive = keep_alive
        self.token = None
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

        # ----- 配置日志器 -----
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)
        file_handler = logging.FileHandler("punuo.log")
        file_handler.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[file_handler, console_handler],
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        self.logger.info("初始化 PunuoClient，用户: %s", user_id)
        self._login()

    def _login(self):
        """执行登录，获取token"""
        url = self.BASE_URL + self.LOGIN_PATH
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9", "Connection": "keep-alive",
            "Content-Type": "application/json", "Origin": "http://192.168.9.26", "Referer": "http://192.168.9.26/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        }
        payload = {"userId": self.user_id, "password": self.password, "keepAlive": self.keep_alive}
        self.logger.info("开始登录，URL: %s", url)

        max_retries, retry_count, retry_delay = 3, 0, 1
        while retry_count < max_retries:
            try:
                resp = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
                resp.raise_for_status()
                result = resp.json()
                self.logger.debug("登录响应: %s", result)
                # 根据实际响应结构提取token（这里假设 code=0 成功，data.token 存放token）
                if result.get("code") != 0:
                    raise Exception(f"登录失败: {result.get('message', '未知错误')}")
                token_data = result.get("data")
                if not token_data:
                    raise Exception("登录响应中无data字段")
                self.token = token_data.get("token")
                if not self.token:
                    raise Exception("登录响应中无token字段")
                self.logger.info(f"365登录成功，token: {self.token[:20]}...")
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

    def _build_query_headers(self) -> Dict:
        """构建查询请求头"""
        if not self.token:
            raise RuntimeError("未获取到有效token，请先登录")
        return {
            "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive", "Content-Type": "application/json", "Origin": "http://192.168.9.26",
            "Referer": "http://192.168.9.26/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "token": self.token
        }

    def get_patient_list(self, ratio_time: str = "2026-05",
            department: str = "", page_size: int = 100, **extra_filters) -> List[Dict[str, Any]]:
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
        # 构造基础查询参数（可扩展）
        # base_payload = {
        #     "pageNo": 1, "pageSize": page_size, "timeModel": { "queryType": query_type, "ratioTime": ratio_time},
        #     "requireMap": { "seachType": 1, **extra_filters.get("requireMap", {}) },
        #     "requireList": { "cyks": [department] if department else [], **extra_filters.get("requireList", {}) },
        #     "orderByColumn": order_by, "isAsc": "asc" if is_asc else "desc",
        #     "zk": {"fileId": "", "conditionType": None }, "hospitalZoneId": hospital_zone_id
        # }
        base_payload = {
            "headFzq": 3, "headCyksbms": [department] if department else [],
            "isAsc": "desc", "queryType": 5, "ratioTime": ratio_time,
            "inquireNextType": "1", "pageNo": 1, "pageSize": 100, "hospitalZoneId": "B00001"
        }
        # 合并额外参数（支持覆盖）
        for key, value in extra_filters.items():
            if key not in ["requireMap", "requireList"]:
                base_payload[key] = value

        all_data = []
        page_no = 1
        while True:
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
        return all_data

    def map_patient_record_v2(self, record: dict) -> dict:
        """
        将新查询接口返回的 JSON 记录映射为表头字段字典
        """
        # 性别映射
        gender_map = {'1': '男', '2': '女'}
        ylfkfs = {
            "1.1": "本市城镇职工基本医疗保险", "1.2": "外埠城镇职工基本医疗保险",
            "2.1": "本市城乡居民基本医疗保险", "2.2": "外埠城镇居民基本医疗保险",
            "3.1": "本市新型农村合作医疗", "3.2": "外埠新型农村合作医疗",
            "4": "贫困救助", "5": "商业医疗保险", "6": "自公费", "7": "全自费", "8": "其他社会保险医保", "9": "其他",
        }

        diprz = record.get('dipRz', '')
        diprzmc = record.get('dipHbCode', '').replace(f"{diprz},", '')
        diprz = diprz.replace(':', '-')
        total_fee = Decimal(str(record.get('zfy', 0)))
        dip_rate = Decimal("0")
        yk = Decimal("0")
        dip_score = Decimal("0")
        bzlb = '基层病种' if record.get('dipJcbz', '否') == '是' else record.get('dipBzlb', '')
        ylfkfs = ylfkfs.get(record.get('ylfkfs'))
        if record.get('dipMlfz', 0):
            dip_score = Decimal(str(record.get('dipMlfz', 0)))
            dip_rate = total_fee / (dip_score * Decimal("5.72183"))
            xishu = Decimal("1.1217")
            if bzlb == '基层病种':
                xishu = Decimal("0.9579")

            if ylfkfs.__contains__('居民') or ylfkfs.__contains__('职工'):
                type_value = Decimal("4") if ylfkfs.__contains__('居民') else Decimal("4.4")

                if dip_rate <= Decimal("0.5"):
                    # (病例校正分值＝基准分值*倍率)*点值-总费用
                    yk = dip_score * dip_rate * type_value - total_fee
                elif dip_rate > Decimal("0.5") and dip_rate <= Decimal("2"):
                    # (病例校正分值＝基准分值*倍率)*1.1217-总费用
                    yk = dip_score * xishu * type_value - total_fee
                elif dip_rate > Decimal("2"):
                    # (病例校正分值＝基准分值*（倍率-2+1.1217）)*点值-总费用
                    yk = dip_score * (dip_rate - Decimal("2") + xishu) * type_value - total_fee

        return {
            '病案号': record.get('bah', ''),
            '医保结算流水号': f"{record.get('bah', '')}_{record.get('zycs', '')}",
            '患者费别': ylfkfs,
            '住院号': record.get('zyh', ''),
            '住院次数': record.get('zycs', ''),
            'DIP倍率': dip_rate.__str__(),
            'DIP结余预测': yk.__str__(),
            '总费用': total_fee.__str__(),
            'DIP入组代码': diprz,
            'DIP入组名称': diprzmc,
            '出院科室': record.get('cybf', ''),
            '住院医师': record.get('zyys') or record.get('zzys', ''),
            '入院时间': record.get('rysj', ''),
            '出院时间': record.get('cysj', ''),
            '姓名': record.get('xm', ''),
            '年龄': record.get('nl', ''),
            '性别': gender_map.get(record.get('xb', ''), '未知'),
            'DIP分值': dip_score.__str__(),
            '病种类别': bzlb
        }

    def build_upsert_sql(self, fields: List[str], pk: str) -> str:
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

        sql = f"""INSERT INTO dip_patient ({field_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"""
        return sql

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
            self.logger.info(f"处理第 {i // batch_size + 1} 批，共 {len(batch)} 条记录")
            ids = ','.join([f"'{item}'" for item in batch])

            sql = f"""with jy as (select bingrenzyid,string_agg(jg ,'、') as jg from (
            select yj.bingrenzyid,yj.shenhesj::varchar || string_agg(yj1.zhongwenmc || ':' ||yj1.jianyanjg || coalesce(yj1.dangwei,''),'、') as jg
            from df_cdr.yj_jianyanbg yj join df_cdr.yj_jianyanbgmx yj1 on yj.jiluid = yj1.jiluid
            join df_jj_zhuyuan.zy_bingrenxx zb on yj.bingrenzyid=zb.bingrenzyid
            join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
            join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid  --and yz.yibaojyhm in ('20260302115236154400')
            where zb.zhuyuanhao || '_' || zb.zhuyuancs in ({ids}) group by yj.bingrenzyid,yj.shenhesj order by yj.shenhesj )v
            group by bingrenzyid), yz1 as ( select  bingrenzyid,string_agg(治疗,'、') as 治疗 from (
            select bingrenzyid, string_agg(  '诊疗：' 
            || yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
            from( select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
            from df_lc_zhuyuan.yz_bingrenyz yb
            join df_zhushuju.yz_yizhuxm yy on yb.yizhuxmid=yy.yizhuxmid and yy.yizhulxid='13'
            join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
            join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
            join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
            join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
            where yb.yizhuzt in ('3', '4')  and zb.zhuyuanhao || '_' || zb.zhuyuancs in ({ids})
            group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0
            )v group by bingrenzyid union all  select bingrenzyid, string_agg(  '手术：' 
                || yizhumc || ':' || to_char(shuliang,'FM9999990') || coalesce(nullif(dw,''),' ') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、')  as 治疗
            from( select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
            from df_lc_zhuyuan.yz_bingrenyz yb join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
            join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
            join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
            join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
            where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('25')  and  zb.zhuyuanhao || '_' || zb.zhuyuancs in ({ids})
            group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0 )v  group by bingrenzyid
            )z  group by bingrenzyid), yz2 as  (  select bingrenzyid, string_agg( '用药：' 
                || yizhumc || ':' || to_char(shuliang,'FM9999990.00') || coalesce(dw,'') || ' 金额:' || to_char(je,'FM9999990.00')  ,'、') filter (where yizhufl in ('11','12','13')) as 用药
            from(select yb.bingrenzyid,yb.yizhuid,sum(zf.shuliang) shuliang,max(zf.jijiadw) dw,sum(zf.jiesuanje) je,yb.yizhufl,yb.yizhumc
            from df_lc_zhuyuan.yz_bingrenyz yb
            join df_jj_zhuyuan.zy_bingrenxx zb on yb.bingrenzyid=zb.bingrenzyid
            join df_jj_zhuyuan.zy_jiesuan1 zj on zb.bingrenzyid = zj.bingrenzyid and zb.jiesuanxh = zj.jiesuanxh
            join df_yibao.yb_zhuyuanjsxx yz on zj.yibaojsid = yz.zhuyuanjsid --and yz.yibaojyhm in ('20260302115236154400')
            join df_jj_zhuyuan.zy_feiyong1 zf on yb.yizhuid=zf.yizhuid
            where yb.yizhuzt in ('3', '4') and yb.yizhufl in ('11','12','13') and zb.zhuyuanhao || '_' || zb.zhuyuancs in ({ids})
            group by yb.bingrenzyid,yb.yizhuid having sum(zf.jiesuanje) >0 )v 
            group by bingrenzyid) select zb.xingming , zb.zhuyuanhao , zb.zhuyuancs, zb.zhuyuanhao || '_' || zb.zhuyuancs yibaojyhm ,
            (select string_agg(case when zz.shunxuhao = 1 then '主要诊断：' else '其他诊断：' end || zz.zhenduanmc || '(' || zz.icd10 || ')' ,
                '、' order by zz.shunxuhao) from df_jj_zhuyuan.zy_zhenduanzl zz where zz.bingrenzyid = zb.bingrenzyid
                and zz.zhenduanlb like '19%' and zz.zuofeibz = '0') 诊断,  (select string_agg(case when bbx.shunxuhao = 1 then '主要诊断：'
                  else '其他诊断：' end || bbx.zhenduanmc || '(' || bbx.jibingbm  || ')' ,  '、' order by bbx.shunxuhao)
            from df_bingangl.ba_bingrenjbxx bb join df_bingangl.ba_bingrenzd_xy bbx on
              bb.binganbrxh = bbx.binganbrxh and bbx.zuofeibz = '0' and bbx.zhenduanlb like '19%'
            where bb.hisbrzyid =zb.bingrenzyid) 病案诊断, (
            select string_agg(yj.baogaosj::varchar || yj.jianchaxmmc || ':' ||nullif(yj.jianchasuojian,''),'、' order by baogaosj asc)
            from df_cdr.yj_jianchabg yj  where yj.bingrenzyid=zb.bingrenzyid and yj.zuofeibz=0
            ) 检查, jy.jg 检验, (select string_agg(zbs.shoushumc || '(' || zbs.icdbm || ')',
              '、'  order by shunxuhao) from df_jj_zhuyuan.zy_ba_shoushuzl zbs where zbs.zuofeibz = '0'
              and zbs.bingrenzyid = zb.bingrenzyid) 手术, (
              select string_agg( (xpath ( 'string()' :: text,
                wb2.wenjiannr :: xml ))[1]::text,
                '
            '
              order by wb.jilusj) from df_bingli.ws_binglijl wb join df_bingli.ws_binglijlnr wb2 on wb.binglijlid = wb2.binglijlid
              where wb.bingrenzyid = zb.bingrenzyid  and wb.zuofeibz = '0' and wb.wenshuzt = 2  and wb.mobanlx = 'SHOUSHUJL' ) 手术记录,
            (select string_agg( (xpath ( 'string()' :: text,  wb2.wenjiannr :: xml ))[1]::text,
                '
            '
              order by wb.jilusj) from df_bingli.ws_binglijl wb
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
            where zb.zhuyuanhao || '_' || zb.zhuyuancs in ({ids})
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

            with DbUtil('192.168.3.12', 'gyl', '123456', 'nsyy_gyl') as db:
                db.execute_many(sql, rows, need_commit=True)
                self.logger.info(f'写入 {len(rows)} 条数据')


# ---------- 使用示例 ----------
if __name__ == "__main__":
    # 实例化客户端（若用户名密码为空则使用默认）
    start_time = time.time()
    client = PunuoClient(user_id="0105", password="liuyi2025")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        # patients2 = client.get_patient_list(ratio_time=f"{start_date},{end_date}", department='神经外科四病区/神经介入科二病区')
        patients2 = client.get_patient_list(ratio_time=f"{start_date},{end_date}")
        client.logger.info(f"一共查询到 {len(patients2)} 条记录，准备写入数据库")
        for item in patients2:
            print(item)
        # client.write_to_db(patients2)
        client.logger.info(f"{start_date} - {end_date} 数据导入完成, 耗时 {time.time() - start_time} s")
    except Exception as e:
        client.logger.info(f"异常 {e.__str__()}, {traceback.print_exc()}")


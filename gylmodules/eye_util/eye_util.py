import json
import logging
import operator
import re
import time
from datetime import datetime, timedelta

import redis
import requests

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

"""
定时获取眼科视光检查结果
部分数据依赖第三方系统 威萌和翻转拍 不连内网无法导出报告
"""


def auto_fetch_eye_data():
    if datetime.now().hour in [0, 1, 2, 3, 4, 5, 20, 21, 22, 23]:
        return
    start_time = (datetime.now() - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")
    end_of_day = datetime.now().replace(hour=23, minute=59, second=0, microsecond=0)
    end_time = end_of_day.strftime("%Y-%m-%d %H:%M:%S")
    # start_time = '2025-01-01 00:00:00'
    # end_time = '2025-05-01 00:00:00'
    fetch_data1(start_time, end_time)
    fetch_data2(start_time, end_time)


"""
查询视光报告
威萌：账号：18638818488 密码: Ks123456
网址：http://store.keash.cn/#/login/auto
"""


def fetch_data1(start_time, end_time):
    headers = {
        'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'zh-CN,zh;q=0.9',
        'Authorization': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpblR5cGUiOiJsb2dpbiIsImxvZ2luSWQiOiJzdG9yZTUyMiIsInJuU3RyIjoiYkc1a3RIVnFCbUtDTWYyaTA1MTVtN2gxeE9QcjRVSjAiLCJ1c2VySWQiOjUyMn0.vsjqNhJfBj0E3moyDVVFLslxomNdkNF3ZjgZ8mmq3MA',
        'Content-Type': 'application/json;charset=UTF-8', 'Origin': 'http://39.105.5.236:3100/',
        'Proxy-Connection': 'keep-alive', 'Referer': 'http://39.105.5.236:3100/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    url = f"http://39.105.5.236:29000/system-api/exam-record/page"
    # limit 最大不能超过 100
    payload = {"page": 1, "limit": 100, "startTime": start_time, "endTime": end_time}
    retry_times = 3
    while retry_times > 0:
        try:
            response = requests.Session().post(url=url, headers=headers, data=json.dumps(payload), verify=False)
            response.raise_for_status()
            ret = response.json()
            if ret.get("status") != 0:
                retry_times -= 1
                continue
            results = ret.get("data", {}).get('results', [])
            if not results:
                return

            record_list = []
            for patient in results:
                ret_data = {}
                recordList = patient.get('recordList', [])
                for item in recordList:
                    if item.get('type') == 'nr':
                        # NRA
                        ret_data['nra'] = item.get('result', '').replace('右眼', 'OD').replace('左眼', 'OS').replace(
                            '双眼', 'OU').replace('\n', ' ')
                    if item.get('type') == 'pr':
                        # PRA
                        ret_data['pra'] = item.get('result', '').replace('右眼', 'OD').replace('左眼', 'OS').replace(
                            '双眼', 'OU').replace('\n', ' ')
                    if item.get('type') == 'ac':
                        # AC/A
                        ret_data['aca'] = item.get('result', '').replace('右眼', 'OD').replace('左眼', 'OS').replace(
                            '双眼', 'OU').replace('\n', ' ')
                    if item.get('type') == 'ar':
                        # 调节幅度
                        matches = re.findall(r'(右眼|左眼|双眼)[:：]\s*([^\n\r]+)', item.get('result', ''))
                        tmp = {}
                        for eye, cpm in matches:
                            if eye == '右眼':
                                tmp['od'] = cpm
                            if eye == '左眼':
                                tmp['os'] = cpm
                            if eye == '双眼':
                                tmp['ou'] = cpm
                        ret_data['ar'] = tmp
                    if item.get('type') == 'af':
                        # 调节灵活度
                        matches = re.findall(r'(右眼|左眼|双眼)：(\d+)\s*cpm', item.get('result', ''))
                        tmp = {}
                        for eye, cpm in matches:
                            if eye == '右眼':
                                tmp['od'] = cpm
                            if eye == '左眼':
                                tmp['os'] = cpm
                            if eye == '双眼':
                                tmp['ou'] = cpm
                        ret_data['af'] = tmp
                    if item.get('type') == 'fv':
                        # 近水平聚散度
                        tmp = item.get('result', '')
                        tmp = tmp.replace('\n', ' ').replace('BI', '').replace('BO', '').replace('模糊点', '')\
                            .replace('分裂点', '').replace('回归点', '')
                        tmp = tmp.split('：')
                        ret_data['fv'] = {
                            "bim": tmp[1] if len(tmp) > 1 else '--',
                            "bif": tmp[2] if len(tmp) > 2 else '--',
                            "bih": tmp[3] if len(tmp) > 3 else '--',
                            "bom": tmp[4] if len(tmp) > 4 else '--',
                            "bof": tmp[5] if len(tmp) > 5 else '--',
                            "boh": tmp[6] if len(tmp) > 6 else '--'
                        }
                    if item.get('type') == 'vc':
                        # 近视力
                        ret_data['vc'] = item.get('result', '').replace('\n', ' ')\
                            .replace('OD', 'od').replace('OS', 'os').replace('OU', 'ou')
                    if item.get('type') == 'w4':
                        # 近worth-4dot
                        ret_data['w4'] = item.get('result', '').replace('\n', ' ')
                    if item.get('type') == 'ep':
                        # 眼位
                        ret_data['ep'] = item.get('result', '').replace('\n', ' ')
                    if item.get('type') == 'fu':
                        # 近融合范围
                        ret_data['fu'] = item.get('result', '').replace('\n', ' ')
                    if item.get('type') == 'sv':
                        # RDS立体视
                        ret_data['sv'] = item.get('result', '').replace('\n', ' ')

                record_list.append(("威萌", patient.get('id') if patient.get('id') else '0',
                                    patient.get('startTime') if patient.get('startTime') else '',
                                    patient.get('customerNickName') if patient.get('customerNickName') else '', 0,
                                    patient.get('customerMobile') if patient.get('customerMobile') else '',
                                    patient.get('sgsNickName') if patient.get('sgsNickName') else '',
                                    patient.get('record') if patient.get('record') else '',
                                    json.dumps(ret_data, ensure_ascii=False, default=str)))
            save_data(record_list)
            return
        except Exception:
            retry_times -= 1
            time.sleep(2)


"""
查询视光报告
翻转拍：账号1：nynsyk001  账号2：nynsyk003 密码:123456
网址：http://www.zhishixun.com/login?redirect=%2Findex
"""


def fetch_data2(start_time, end_time):
    redis_client = redis.Redis(connection_pool=pool)
    token = redis_client.get('eye-token')
    if not token:
        return

    retry_times = 3
    while retry_times > 0:
        try:
            params = {"checkType": "0", "pageNum": "1", "pageSize": "100",
                      "checkStartTime": start_time, "checkEndTime": end_time}
            headers = {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
                       "Authorization": f"Bearer {token}", "Referer": "http://www.zhishixun.com/iflip/check/checkList",
                       "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                       }
            resp = requests.get("http://www.zhishixun.com/api/management/check/queryPlatformCheckInfo",
                                headers=headers, params=params, verify=False)
            resp.raise_for_status()
            if resp.status_code != 200:
                retry_times -= 1
                continue
            data = resp.json()
            rows = data.get('rows')
            if not rows:
                retry_times -= 1
                continue

            record_list = []
            for patient in rows:
                value = {"od": '', "os": '', 'ou': ''}
                if patient.get('leftEye'):
                    match = re.search(r'\d+\.\d+cpm', patient.get('leftEye'))
                    if match:
                        value['os'] = match.group().replace('cpm', '')
                    if not value['os'] and patient.get('leftEye') and patient.get('leftEye').__contains__('cpm'):
                        value['os'] = '+不通过'
                if patient.get('rightEye'):
                    match = re.search(r'\d+\.\d+cpm', patient.get('rightEye'))
                    if match:
                        value['od'] = match.group().replace('cpm', '')
                    if not value['od'] and patient.get('rightEye') and patient.get('rightEye').__contains__('cpm'):
                        value['od'] = '+不通过'
                if patient.get('binoculus'):
                    match = re.search(r'\d+\.\d+cpm', patient.get('binoculus'))
                    if match:
                        value['ou'] = match.group().replace('cpm', '')
                    if not value['ou'] and patient.get('binoculus') and patient.get('binoculus').__contains__('cpm'):
                        value['ou'] = '+不通过'
                record_list.append(("翻转拍", patient.get('checkId') if patient.get('checkId') else '0',
                                    patient.get('checkStartTime') if patient.get('checkStartTime') else '',
                                    patient.get('checkUserName') if patient.get('checkUserName') else '',
                                    patient.get('checkUserGender') if patient.get('checkUserGender') else 0,
                                    patient.get('checkUserPhone') if patient.get('checkUserPhone') else '',
                                    patient.get('checkcompAName') if patient.get('checkcompAName') else '',
                                    json.dumps({"left": patient.get('leftEye') if patient.get('leftEye') else '',
                                                "right": patient.get('rightEye') if patient.get('rightEye') else '',
                                                "binoculus": patient.get('binoculus') if patient.get(
                                                    'binoculus') else ''
                                                }, ensure_ascii=False, default=str),
                                    json.dumps(value, ensure_ascii=False, default=str)
                                    ))
            save_data(record_list)
            return
        except Exception:
            pass
        retry_times -= 1


def save_data(records):
    if not records:
        return
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    insert_sql = f"""INSERT INTO nsyy_gyl.ehp_check_result(type, record_id, check_time, name, sex, phone, 
                    checker, value, value_well) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE 
                    type = VALUES(type), record_id = VALUES(record_id), sex = VALUES(sex), 
                    phone = VALUES(phone), checker = VALUES(checker), value = VALUES(value), 
                    value_well = VALUES(value_well)"""
    db.execute_many(insert_sql, records, need_commit=True)
    del db


"""获取 翻转拍 网站token"""

_ops = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "x": operator.mul, "X": operator.mul, "×": operator.mul,
    "/": operator.floordiv, "÷": operator.floordiv
}


def ocr_try_variants(img_b64):
    """利用眼科医院的ocr识别工具进行解析"""
    retry_times = 3
    while retry_times > 0:
        try:
            payload = {"img_b64": img_b64}
            with requests.Session() as session:
                r = session.post("http://192.168.190.252:8080/gyl/ehp/captcha", json=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
            if data["code"] == 20000:
                return data.get('data')
        except Exception:
            pass
        retry_times -= 1
    logger.warning("识别翻转拍验证码失败")
    return None


def smart_parse_compute(txt):
    """
    从 OCR 文本中尽量提取最可能的 a op b 并返回结果与解析表达式。
    规则与纠错策略：
     - 去除无关符号（除数字与 +-*/ 外）
     - 替换常见符号（× x X -> *，÷ -> /）
     - 如果数字粘连（如 327），默认只取前一位或两位（根据长度）
     - 如果解析失败返回 (None, reason)
    """
    if not txt:
        return None, "空 OCR 文本"
    s = txt.replace(" ", "")
    s = s.replace("—", "-").replace("–", "-")
    s = s.replace("×", "*").replace("x", "*").replace("X", "*")
    s = s.replace("÷", "/")
    # 仅保留数字和运算符
    s = re.sub(r"[^0-9+\-*/]", "", s)
    # 尝试 a op b 模式
    m = re.search(r"(\d+)([+\-*/])(\d+)", s)
    if not m:
        # 退而求其次：提取所有数字并猜测减法（常见）
        nums = re.findall(r"\d+", s)
        if len(nums) >= 2:
            a, b = nums[0], nums[1]
            # 限制为单/两位数，若多位取首位
            if len(a) > 2: a = a[0]
            if len(b) > 2: b = b[0]
            a, b = int(a), int(b)
            res = _ops.get("-", operator.sub)(a, b)
            return res, f"{a}-{b}={res}"
        return None, f"未能解析: {txt} -> {s}"
    a_raw, op, b_raw = m.groups()

    # 如果识别像 '327' 或 '32789' 等粘连，取前1位或前2位（如果验证码有时是两位数可取2位）
    def trim_num(x):
        if len(x) <= 2:
            return x
        # 优先保留 1 位（因为多数验证码是个位运算），若你确认会有两位可改逻辑
        return x[0]

    a_s = trim_num(a_raw)
    b_s = trim_num(b_raw)
    try:
        a, b = int(a_s), int(b_s)
    except:
        return None, f"数字转换失败: {a_s},{b_s}"
    if op not in _ops:
        return None, f"未知运算符: {op}"
    try:
        res = _ops[op](a, b)
    except Exception as e:
        return None, f"计算异常: {e}"
    return res, f"{a}{op}{b}={res}"


def do_login(code_value, uuid_value):
    retry_times = 3
    while retry_times > 0:
        try:
            payload = {"username": "nynsyk001", "password": "e10adc3949ba59abbe56e057f20f883e",
                       "code": str(code_value), "uuid": uuid_value, "loginType": "IFLIP"}
            headers = {"Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
                       "Referer": "http://www.zhishixun.com/login?redirect=%2Findex", "isToken": "false",
                       "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                       "Content-Type": "application/json;charset=UTF-8"}
            with requests.Session() as session:
                r = session.post("http://www.zhishixun.com/api/auth/admin/login_pwd_manage",
                                 headers=headers, json=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
            if data["code"] == 200:
                return data.get('data')
        except Exception:
            pass
        retry_times -= 1
    return None


def fetch_token():
    retry_times = 5
    while retry_times > 0:
        try:
            with requests.Session() as session:
                r = session.get("http://www.zhishixun.com/api/code", timeout=10)
                r.raise_for_status()
                data = r.json()

            if data["code"] != 200:
                logger.debug(f"获取验证码失败: {data}")
                retry_times -= 1
                continue

            img_b64 = data.get("img")
            uuid_val = data.get("uuid")
            if not img_b64 or not uuid_val:
                retry_times -= 1
                continue

            # 2) OCR 多策略识别
            cand = ocr_try_variants(img_b64)

            # 3) 对每个候选做智能解析与计算
            chosen = None
            res, expr = smart_parse_compute(cand)
            logger.debug(f"尝试解析: {cand} => {expr}")
            if not res:
                retry_times -= 1
                continue
            logger.info(f"最终识别/计算：{res} {expr}")

            # 登陆获取 token
            token = do_login(res, uuid_val)
            if token is None:
                logger.warning("翻转拍网站 token 获取失败 重试")
                retry_times -= 1
                continue

            return token
        except:
            pass
        retry_times -= 1
    return None


def flush_token():
    # token 存在不需要重新获取
    redis_client = redis.Redis(connection_pool=pool)
    if redis_client.exists('eye-token'):
        return

    start_time = time.time()
    token = fetch_token()
    logger.debug(f"token 获取耗时 {time.time() - start_time}, {token}")
    if not token:
        return
    # token 获取成功 更新token
    redis_client.set(f"eye-token", token.get('access_token'), ex=3 * 60 * 60, nx=True)
    redis_client.delete(f"eye-token-old")
    redis_client.set(f"eye-token-old", token.get('access_token'), ex=4 * 60 * 60, nx=True)

# flush_token()

# auto_fetch_eye_data()

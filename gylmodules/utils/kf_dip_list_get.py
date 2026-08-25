import logging

import requests
import time
from typing import Dict, List, Any, Optional
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PMSClient:
    """普美事（PMS）系统客户端，支持验证码登录及患者数据查询"""

    def __init__(self, base_url: str, username: str, password: str):
        """
        初始化客户端
        :param base_url: 基础地址，如 http://192.168.9.17
        :param ocr_func: 验证码识别函数，接受base64图片字符串，返回识别出的验证码字符串
        :param username: 登录用户名
        :param password: 登录密码（若前端有加密，请传入已加密的值；否则传明文）
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # 对应 --insecure
        self.token = None
        # 基础请求头（与浏览器一致）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Referer': f'{self.base_url}/',
            'Origin': self.base_url,
        })

    # 假设您已有的OCR识别函数（放在外部定义）
    def ocr_try_variants(self, img_b64):
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
        return None

    def smart_parse_compute(self, txt):
        """
        从 OCR 文本中尽量提取最可能的 a op b 并返回结果与解析表达式。
        规则与纠错策略：
         - 去除无关符号（除数字与 +-*/ 外）
         - 替换常见符号（× x X -> *，÷ -> /）
         - 如果数字粘连（如 327），默认只取前一位或两位（根据长度）
         - 如果解析失败返回 (None, reason)
        """
        import re, operator
        _ops = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "x": operator.mul, "X": operator.mul, "×": operator.mul,
            "/": operator.floordiv, "÷": operator.floordiv
        }
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

    def get_captcha(self, captcha_url: str) -> tuple:
        """
        获取验证码图片和uuid
        :param captcha_url: 验证码接口完整路径，如 /pms-service/captcha
        :return: (img_base64字符串, uuid)
        """
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Referer': f'{self.base_url}/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        }
        resp = self.session.get(self.base_url + captcha_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 200:
            raise Exception(f"获取验证码失败: {data.get('msg')}")
        return data['img'], data['uuid']

    def login(self, login_url: str, max_retries: int = 3) -> bool:
        """
        执行登录（自动识别验证码并重试）
        :param login_url: 登录接口路径，如 /pms-service/login
        :param max_retries: 识别失败时的最大重试次数
        :return: True 登录成功，False 登录失败
        """
        for attempt in range(max_retries):
            try:
                # 1. 获取验证码
                img_b64, uuid = self.get_captcha('/pms-service/captchaImage')  # 请根据实际路径调整
                # 2. 调用用户提供的OCR函数识别
                cand = self.ocr_try_variants(img_b64)
                if not cand:
                    print(f"第 {attempt+1} 次尝试：OCR 识别失败，重试...")
                    time.sleep(1)
                    continue
                print(f"第 {attempt+1} 次尝试：识别验证码为 {cand}")

                # 3) 对每个候选做智能解析与计算
                chosen = None
                code, expr = self.smart_parse_compute(cand)
                print(f"尝试解析: {cand} => {expr}")
                if not code:
                    print(f"第 {attempt+1} 次尝试：解析失败 ，重试...")
                    time.sleep(1)
                    continue
                print(f"最终识别/计算：{code} {expr}")

                # 3. 提交登录
                payload = {
                    "username": self.username,
                    "password": self.password,
                    "code": code,
                    "uuid": uuid
                }
                resp = self.session.post(self.base_url + login_url, json=payload, timeout=10)
                resp.raise_for_status()
                result = resp.json()
                if result.get('code') == 200:
                    # 提取token：优先从响应体获取，若没有则从cookie获取Admin-Token
                    self.token = result.get('data', {}).get('token') or result.get('token')
                    if not self.token:
                        # 尝试从Cookie中获取Admin-Token
                        self.token = self.session.cookies.get('Admin-Token')
                    if self.token:
                        print(f"获取到Token: {self.token[:20]}...")
                    else:
                        print("警告：未获取到Token，后续请求可能失败。")
                    return True
                else:
                    print(f"登录失败: {result.get('msg')}，重试...")
                    time.sleep(1)
            except Exception as e:
                print(f"第 {attempt+1} 次尝试异常: {e}")
                time.sleep(1)
        print("金豆登录失败，已达最大重试次数。")
        return False

    def _build_query_params(self, **kwargs) -> Dict[str, Any]:
        """
        构造查询参数（GET请求）
        默认参数覆盖了 curl 中的常用项，您可以根据需要传入覆盖。
        """
        params = {
            'current': 1,
            'size': 10,
            'type': 2,
            'cysjKs': '',
            'cysjJs': '',
            'setlId': '',
            'settleKssj': '',
            'settleJssj': '',
            'bahjhzxm': '',
            'listingStatus': '',
            'cyks': '',
            'zzys': '',
            'zyzd': '',
            'sscz': '',
            'rzfxlx': '',
            'fyfxlx': '',
            'swfxlx': '',
            'wrzyy': '',
            'ycyk': '',
            'fyjgfx': '',
            'ljfyfx': '',
            'jdbllx': '',
            'cczyts': '60',
            'gzlx': '',
            'yfzbmjmc': '',
            'qdRefSetleFlag': '',
            'deptGroup': '',
            'zylsh': '',
            'sftf': '',
            'gzfl': '0',
            'reportStatus': '',
            'lyfs': '',
            'outFlag': '',
            'insutype': '',
            'chargeType': '',
            'isDrg': '2'
        }
        # 用传入的kwargs覆盖默认值
        params.update(kwargs)
        # 删除空值参数（可选）
        return params

    def query_patients(self, query_url: str = '/mrqc-service/Qdquery/listpage', **kwargs) -> List[Dict]:
        """
        查询患者列表（自动分页，返回全部记录）
        :param query_url: 查询接口路径
        :param kwargs: 查询参数，可覆盖默认值，如 current=1, size=100, settleKssj='2026-07-01' 等
        :return: 患者记录列表（每条记录为字典）
        """
        if not self.token:
            raise Exception("未登录或Token无效，请先调用 login() 方法。")
        # 设置Authorization头
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

        all_data = []
        params = self._build_query_params(**kwargs)
        page = params.get('current', 1)
        size = params.get('size', 100)  # 每页条数，可调大
        params['size'] = size
        print(params)

        while True:
            params['current'] = page
            resp = self.session.get(self.base_url + query_url, params=params, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            # 假设返回格式为 { "code": 200, "data": { "records": [...], "total": 100 } }
            if result.get('code') != 200:
                raise Exception(f"查询失败: {result.get('msg')}")
            data = result.get('data', {})
            records = data.get('rows', [])
            if not records:
                break
            all_data.extend(records)
            total = data.get('total', 0)
            # 如果总数已知且已全部获取，退出
            if total > 0 and len(all_data) >= total:
                break
            # 如果本次返回数量小于size，说明是最后一页
            if len(records) < size:
                break
            page += 1

        if all_data:
            for item in all_data:
                item['病案号'] = item.pop('bah', '')
                item['结算ID'] = item.pop('setlId', '')
                item['患者姓名'] = item.pop('hzxm', '')
                item['预分组编码'] = item.pop('dipCode', '')
                item['预分组名称'] = item.pop('dipName', '')
                item['基准分值'] = item.pop('rwt', 0)
                item['病例分值'] = item.pop('baRwt', 0)
                item['入组类型'] = item.pop('groupWarning', '') # 10 核心病种 11 综合病种 99 基层病种 0未入组
                item['病例类型'] = item.pop('costWarning', '') # 5 床日付费 1 正常倍率  2高倍率 3 底倍率 4 未入组
                item['倍率'] = item.pop('bl', 0)
                item['预测盈亏'] = item.pop('ycyk', 0)
                item['医疗总费用'] = item.pop('zfy', 0)
                item['预测总费用'] = item.pop('zfbz', 0)
                item['医保基金'] = item.pop('tcjjzf', 0)
                item['DIP医保基金'] = item.pop('groupTczf', 0)
                item['基金结余'] = item.pop('jjjy', 0)
                item['个人负担总额'] = item.pop('grfdze', 0)
                item['地区均费'] = item.pop('avgCost', 0)
                item['同等级地区均费'] = item.pop('levelAvgCost', 0)
                item['住院天数'] = item.pop('sjzyts', 0)
                item['住院次数'] = item.pop('zycs', 0)
                item['药占比(%)'] = item.pop('yczbl', 0)
                item['药占比阈值(%)'] = item.pop('bzyczbl', 0)
                item['耗占比(%)'] = item.pop('hczbl', 0)
                item['耗占比阈值(%)'] = item.pop('bzhczbl', 0)
                item['检查费占比(%)'] = item.pop('jczbl', 0)
                item['检验费占比(%)'] = item.pop('jyzbl', 0)
                item['治疗费占比(%)'] = item.pop('zlzbl', 0)
                item['手术费占比(%)'] = item.pop('sszbl', 0)
                item['主要诊断编码'] = item.pop('zyzddmYb', '')
                item['主要诊断名称'] = item.pop('zyzdmcYb', '')
                item['主要手术及操作编码'] = item.pop('ssjczbmYb1', '')
                item['主要手术及操作名称'] = item.pop('ssjczmcYb1', '')
                item['性别'] = item.pop('xb', '') # 1→男，2→女，其他→未知
                item['院内出院科室'] = item.pop('yncyks', '')
                item['出院科室'] = item.pop('cyks', '')
                item['出院时间'] = item.pop('cysj', '')
                item['结算时间'] = item.pop('setlTime', '')
                item['住院医师'] = item.pop('zyys', '')
                item['上传时间'] = item.pop('scsj', '')
                item['险种类型'] = item.pop('insutype', '') # 职工基本医疗保险 310 公务员医疗补助 320  大额医疗费用补助 330  离休人员医疗保障 340  城乡居民基本医疗保险 390  城乡居民大病医疗保险 392 生育保险 510

        return all_data


# ---------- 使用示例 ----------
if __name__ == "__main__":

    # 1. 创建客户端
    # 康复
    # client = PMSClient(
    #     base_url="http://192.168.9.17",
    #     username="u3015",
    #     password="MTIzNDU2"   # 根据实际情况填写
    # )
    # 油田
    client = PMSClient(
        base_url="http://192.168.9.15",
        username="u0117",
        password="MTIzNDU2"   # 根据实际情况填写
    )

    # 2. 登录
    if client.login('/pms-service/login'):
        # 3. 查询患者列表（使用默认参数，可自定义日期等）
        patients = client.query_patients(
            size=50,                    # 每页50条
            settleKssj='2026-07-01',
            settleJssj='2026-07-17'
        )
        print(f"共获取 {len(patients)} 条患者记录")
        # 打印前3条示例
        for p in patients[:3]:
            print(p)
    else:
        print("登录失败，无法查询。")


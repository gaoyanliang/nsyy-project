import time
import json
import logging
from decimal import Decimal
from threading import Lock

import requests
from openai import OpenAI, RateLimitError, APIError
from functools import wraps

# ---------- 配置 ----------

API_KEY = "sk-f4e288071c6647d3976067bb48b3133f"  # 替换为实际key
BASE_URL = "https://api.deepseek.com/"
MODEL = "deepseek-v4-flash"  # 或 deepseek-chat
MAX_WORKERS = 20  # 并发线程数，根据API限制调整
MAX_RETRIES = 3  # 每个API请求最大重试次数
RETRY_DELAY = 2  # 初始重试延迟（秒），指数增长

logger = logging.getLogger(__name__)

# 全局锁
write_lock = Lock()


""" 打印AI 回答 """
def print_response_detail(res, haoshi):
    logger.info(f"====== 本次AI回答情况 ======")
    logger.debug(f"本次请求ID： {res.id}")
    logger.debug(f"本次AI回答： {res.choices[0].message.content}")

    # 安全获取 usage 相关信息
    usage = getattr(res, 'usage', None)
    if usage:
        logger.info(f"本次输入消耗的 token 数： {getattr(usage, 'prompt_tokens', 'N/A')}")
        logger.info(f"本次输出消耗的 token 数： {getattr(usage, 'completion_tokens', 'N/A')}")
        logger.info(f"本次消耗的总 token 数： {getattr(usage, 'total_tokens', 'N/A')}")

        # 思考消耗的 token 数（部分模型支持）
        completion_details = getattr(usage, 'completion_tokens_details', None)
        if completion_details and hasattr(completion_details, 'reasoning_tokens'):
            reasoning_tokens = completion_details.reasoning_tokens
        else:
            reasoning_tokens = 'N/A (not supported)'
        logger.info(f"本次思考消耗的 token 数： {reasoning_tokens}")

        # 缓存命中 token 数
        cache_hit = getattr(usage, 'prompt_cache_hit_tokens', None)
        if cache_hit is None:
            cache_hit = 'N/A (not supported)'
        logger.info(f"从缓存中命中的 token 数： {cache_hit}")
    else:
        logger.info("本次 token 消耗信息： N/A (usage missing)")

    logger.info(f"本次回答总耗时： {haoshi} 秒")
    logger.debug(f"本次AI返回： {res.choices[0].message}")
    logger.info('--' * 10)

# ---------- 辅助函数 ----------

"""装饰器：处理API限流和临时错误"""
def retry_on_rate_limit(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    wait = delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                except APIError as e:
                    if attempt < max_retries - 1:
                        wait = delay * (2 ** attempt)
                        logger.warning(f"API error: {e}, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unhandled error: {e}")
                    raise
            raise Exception(f"Failed after {max_retries} retries")

        return wrapper

    return decorator


# ---------- 核心API调用（改写为可重用，每个患者独立） ----------

def call_ai_for_patient(info, is_json: bool = False):
    if not query_balance():
        return None
    """ 处理单个患者的全部问题，返回结果字典。  内部包含重试和对话历史管理。 """
    info = info.replace("严格仅输出以下CSV格式表格", "严格仅输出以下CSV格式表格（不要markdown格式）")
    # 每个线程独立的OpenAI客户端（线程安全）
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    @retry_on_rate_limit()
    def ask_one():
        messages = [{"role": "user", "content": info}]
        return client.chat.completions.create(model=MODEL, messages=messages)

    start = time.time()
    response = ask_one()
    # safe_append_to_json(OUTPUT_FILE[2], extract_json_from_response(response.choices[0].message.content))
    print_response_detail(response, time.time() - start)

    return response.choices[0].message.content if not is_json else extract_json_from_response(response.choices[0].message.content)



"""查询余额"""
def query_balance():
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
    response = requests.request("GET", "https://api.deepseek.com/user/balance", headers=headers, data={})
    logger.info(f"查询余额结果：{response.text}")
    if response:
        response = response.json()
        if Decimal(response['balance_infos'][0]['total_balance']) < Decimal('1'):
            return False
        return True
    return False


def extract_json_from_response(response_text: str):
    """
    从 AI 响应中提取 JSON 内容
    支持 ```json ... ``` 或直接的 JSON 文本
    返回解析后的 JSON 对象（列表或字典）
    """
    # 去除可能的 Markdown 标记
    text = response_text.strip()
    import re
    # 尝试提取 ```json ... ``` 中的内容
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)

    # 尝试解析 JSON
    try:
        # 先尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 如果失败，尝试修复常见问题（如单引号替换为双引号）
        try:
            # 将 Python 风格的字典/列表转为 JSON（单引号 -> 双引号）
            fixed = text.replace("'", '"')
            return json.loads(fixed)
        except json.JSONDecodeError:
            # 如果还是失败，记录原始内容并返回 None
            logger.error(f"无法解析 JSON: {text[:200]}...")
            return None

def excel_to_jsons1(file_path, sheet_num: int = 0, header_line: int = 1, keys: list = None):
    """
    :param file_path: Excel 文件路径
    :param sheet_num: 工作表索引，从0开始
    :param header_line: 表头所在行号（从1开始）
    :param keys: 需要提取的列名列表，若为 None 则提取所有列
    :return: JSON 字符串列表
    """
    import openpyxl
    wbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wbook[wbook.sheetnames[sheet_num]]

    # 读取所有表头
    headers = [cell.value for cell in sheet[header_line]]

    # 如果指定了 keys，则只保留这些列；否则保留所有列
    if keys is not None:
        # 仅保留在 keys 中出现的列名（按 keys 的顺序保留，便于排序）
        # 如果某个 key 不在 headers 中，此处会被忽略（也可主动抛出异常）
        valid_keys = [k for k in keys if k in headers]
        # 构建列索引映射：列名 -> 列索引（0-based）
        col_indices = {name: idx for idx, name in enumerate(headers) if name in valid_keys}
        # 为了后续 zip 顺序一致，按 valid_keys 顺序取出列值
        # 由于 iter_rows 按列顺序返回，我们需要按索引提取，但更简单的是直接用行字典过滤
    else:
        valid_keys = headers

    results = []
    for row in sheet.iter_rows(min_row=header_line + 1, values_only=True):  # 从表头下一行开始
        # 将整行与所有表头组合成字典
        full_dict = dict(zip(headers, row))
        # 如果指定了 keys，则过滤字典
        if keys is not None:
            row_dict = {k: full_dict[k] for k in valid_keys if k in full_dict}
        else:
            row_dict = full_dict

        # 如果需要写入文件，需要将row_dict转为JSON字符串
        # row_json = json.dumps(row_dict, ensure_ascii=False, default=str)
        results.append(row_dict)

    return results




# ---------- 启动 ----------
if __name__ == "__main__":

    text = """
    
左房前后径为 32 毫米，主动脉根部瓣环内径为 21 毫米，升主动脉内径为 36 毫米，右室前后径为 20 毫米，肺动脉内径为 20 毫米。左心室舒张内径为 49 毫米，收缩内径为 33 毫米，室间隔厚度为 10.6 毫米，运动幅度为 9 毫米，左室后壁厚度为 10.2 毫米，运动幅度为 9 毫米。主动脉瓣瓣上流速为 1.06 米/秒，肺动脉瓣上流速为 1.14 米/秒。二尖瓣 E 峰流速为 0.90 米/秒，A 峰流速为 0.74 米/秒，二尖瓣 TVI 间隔侧为 8 厘米，侧壁侧为 1。三尖瓣反流速度为 2.5 米/秒，压差为 25 毫米汞柱，估测肺动脉瓣压力为 28 毫米汞柱。舒张期容积为 114 毫升，收缩期容积为 46 毫升，射血分数为 59%，短轴缩短率为 31%，每搏输出量为 67 毫升，每分输出量为 4.4 升，静息心率为 65 次/分。该患者主动脉瓣回声增强，舒张期可见少量反流，二尖瓣收缩期亦见少量反流。

    """

    start_time = time.time()
    ret = call_ai_for_patient(text)
    print(ret)
    print(json.loads(ret))

    print("耗时：", time.time() - start_time)

    # 查询余额
    query_balance()

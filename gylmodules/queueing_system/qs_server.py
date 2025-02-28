import requests
import json

from datetime import datetime, timedelta
from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil


def call_third_systems_obtain_data(url: str, type: str, param: dict):
    data = []
    if global_config.run_in_local:
        try:
            # response = requests.post(f"http://192.168.3.12:6080/{url}", json=param)
            response = requests.post(f"http://192.168.124.53:6080/{url}", timeout=3, json=param)
            data = json.loads(response.text)
            if type != 'his_pers_reg':
                data = data.get('data')
        except Exception as e:
            print('调用第三方系统方法失败：type = ' + type + ' param = ' + str(param) + "   " + e.__str__())
    else:
        if type == 'orcl_db_read':
            from tools import orcl_db_read
            data = orcl_db_read(param)
        else:
            print('call_third_systems_obtain_data 不支持 ', type)
    return data


"""
接口一： 读取患者当天的医嘱信息
1. window 客户端 调用读卡器读取卡片信息
2. 根据 身份证号/社保卡号/就诊卡号 查询患者当天医嘱信息 门诊的同时查询医嘱状态
"""


def query_patient_info(card_no, card_type):
    # card_type 1=身份证 2=社保卡 3=就诊卡 4=住院患者 住院号
    condition_sql = ""
    if int(card_type) in (1, 2):
        # 身份证 社保卡 都使用身份证号查询
        condition_sql = f"身份证号 = '{card_no}'"
    elif int(card_type) == 3:
        condition_sql = f"就诊卡号 = '{card_no}'"
    else:
        raise Exception("card_type 错误, 暂时仅支持 1=身份证 2=社保卡 3=就诊卡 4=住院患者 住院号")

    # 0. 选择卡片类型 读卡器 读取卡片信息
    # 1. 根据卡片类型 确定 card_no 匹配的字段
    # 2. 查询患者 当天的检查类医嘱
    print()


"""
接口二： 分配房间 
1. 门诊医嘱 检查缴费状态，没有缴费 先缴费
2. 医嘱执行   todo 医嘱执行接口
3. 在 pacs 中进行登记 （注意 不同的医嘱可能需要到不同的房间做）
4. 绑定房间
5. 加入队列
"""


def room_assignments(item_list):

    item_list = [{"医嘱信息:": "", "房间信息": ""}]
    # 0. 门诊患者的检查医嘱 未缴费 提醒缴费

    # 1. 医嘱执行 todo 需要 his 提供医嘱执行接口

    # 2. 在 pacs 中进行登记 todo 需要确定是否可以做到 一条医嘱 == 一个检查项目 == 一个检查房间，   登记完成之后 所有房间都可以看到 还是某一个房间可以看到
    # todo 需要 pacs 提供检查登记接口

    # 3. 绑定房间 插入排队信息

    print()


"""
接口三：房间列表查询
"""


def query_room_list():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    # queue_status = 0 等待中状态
    query_sql = """
        SELECT r.* , COUNT(q.queue_id) AS waitting_num
        FROM nsyy_gyl.qs_room_list r LEFT JOIN nsyy_gyl.qs_queue_list q
        ON r.room_id = q.room_id AND q.queue_status = 0
        GROUP BY r.room_id, r.room_name, r.room_type
        ORDER BY r.room_id;
    """

    # todo 同时查询每个房间的等待人数
    qs_room_list = db.query_all(f"select * from nsyy_gyl.qs_room_list")
    del db
    return qs_room_list


"""
接口四：查询房间排队情况
"""


def query_room_queue_situation(rid):
    # rid = 0 查询所有房间， 不等于 0 查询指定房间

    print()


"""
接口五： 更新患者排队状态
"""


def update_patient_queue_state(patient_id, room_no, state):
    print()


def find_median(num1: float, num2: float) -> float:
    """
    计算两个浮点数的中位数。

    :param num1: 第一个浮点数
    :param num2: 第二个浮点数
    :return: 两个浮点数的中位数
    """
    return (num1 + num2) / 2.0


def next_float(num: float) -> float:
    """
    输入一个保留两位小数的浮点数，输出比这个浮点数大的下一个浮点数。

    :param num: 输入的浮点数（保留两位小数）
    :return: 比输入浮点数大的下一个浮点数（小数点前加一，小数点后为0）
    """
    integer_part = int(num) + 1  # 小数点前部分加一
    return float(f"{integer_part}.00")  # 小数点后置为 0.00


def calculate_next_time(minutes_to_add: int) -> str:
    """
    计算当前时间点加上指定分钟数后的时间点。

    Args:
        base_time (str): 当前时间
        minutes_to_add (int): 要添加的分钟数。

    Returns:
        str: 加上分钟数后的新时间点，格式为 "%Y-%m-%d %H:%M:%S"。
    """
    try:
        # 将输入时间解析为 datetime 对象
        current_time = datetime.now()

        # 计算新时间点
        new_time = current_time + timedelta(minutes=minutes_to_add)

        # 格式化返回结果
        return new_time.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return f"输入的时间格式错误: {e}"


# 示例调用
minutes_to_add = 60
result = calculate_next_time(minutes_to_add)
print("新时间点:", result)











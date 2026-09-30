import time
import traceback
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException

# Chrome 无头模式配置
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # Chrome 114+推荐的无头模式
chrome_options.add_argument("--disable-gpu")  # 禁用GPU加速
chrome_options.add_argument("--no-sandbox")  # Linux系统需要
chrome_options.add_argument("--disable-dev-shm-usage")  # 防止内存不足
chrome_options.add_argument("--window-size=1920,1080")  # 设置窗口大小

# 强化配置（解决证书和资源加载问题）
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--ignore-ssl-errors")
chrome_options.add_argument("--disable-notifications")

# 屏蔽资源加载错误
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
chrome_options.add_argument("--disable-stylesheets")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

# 防止被检测为自动化工具
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("useAutomationExtension", False)

# 启动无头浏览器
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)
actions = ActionChains(driver)

# 隐藏WebDriver特征
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


"""登录函数"""


def login():
    try:
        # 访问登录页面
        driver.get("http://tingchechang.nsyy.com.cn/")
        print(datetime.now(), "✅ 已访问登录页面")

        # 输入用户名
        username = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']")))
        username.clear()
        username.send_keys("admin1")

        # 输入密码
        password = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入密码' and @type='password']")))
        password.clear()
        password.send_keys("Lg20252025")

        # 点击登录按钮
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'login-btn')]")))
        try:
            login_btn.click()
        except:
            driver.execute_script("arguments[0].click();", login_btn)

        # 验证登录成功
        wait.until(EC.text_to_be_present_in_element((By.XPATH, "//span[@class='username']"), "admin1"))
        print(datetime.now(), "✅ 登录成功")
        return True
    except Exception as e:
        print(datetime.now(), f"❌ 登录失败: {str(e)}")
        driver.save_screenshot("login_fail.png")
        return False


"""进入停车场出入口页面"""


def switch_to_parking_page():
    try:
        # 点击菜单
        parking_menu = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='sub-nav-title' and contains(text(), '停车场出入口')]")))

        # 滚动到视图中心
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parking_menu)
        time.sleep(0.5)

        # 点击菜单
        try:
            parking_menu.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", parking_menu)

        print(datetime.now(), "✅ 已进入停车场出入口页面")
        return True
    except Exception as e:
        print(datetime.now(), f"❌ 进入停车场页面失败: {str(e)}")
        driver.save_screenshot("parking_page_fail.png")
        return False


"""切换至信息查询菜单 获取指定cookie"""


def switch_to_info_query():
    """专为海康威视停车场系统设计的菜单切换方案"""
    try:
        # 确保在主文档中
        driver.switch_to.default_content()

        # 切换到内容iframe（根据图片中的iframe000505）
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))

        # 在iframe内查找菜单（关键步骤）
        menu_xpath = "//li[contains(@class,'el-menu-item') and contains(.,'信息查询')]"
        menu = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, menu_xpath))
        )

        # 高亮元素（调试用）
        driver.execute_script("""
            arguments[0].style.outline = '3px solid red';
            arguments[0].scrollIntoView({block: 'center'});
        """, menu)

        # 6. 特殊点击处理（海康系统需要）
        driver.execute_script("""
            // 先触发鼠标悬停
            arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));

            // 再触发点击
            const clickEvent = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true
            });
            arguments[0].dispatchEvent(clickEvent);

            // 兼容性处理
            if (arguments[0].querySelector('a')) {
                arguments[0].querySelector('a').click();
            }
        """, menu)

        # 7. 等待内容更新
        time.sleep(2)  # 必须等待
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                                                                        "//*[contains(text(), '过车记录查询')]")))

        print(datetime.now(), "✅ 成功切换到信息查询页面")
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        print(datetime.now(), cookies)
        return True

    except Exception as e:
        print(datetime.now(), f"❌ 切换失败: {str(e)}", e.__class__)

        # 获取诊断信息
        print(datetime.now(), "当前页面HTML:", driver.execute_script("return document.documentElement.outerHTML"))
        driver.save_screenshot("hik_fail.png")
        return False


"""获取所有超时车辆数据（停车时长超过 7 天）"""


def fetch_all_timeout_cars():
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token,
            "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleInParking/getVehicleInParkingPage"

    # 2. 获取第一页数据（确定总页数）
    first_page_params = {
        "plateNo": "",
        "parkDay": "7",  # 超过 7 天的数据
        "plateBelieve": 100,
        "pageNo": 1,
        "pageSize": 100,
        "time": int(time.time() * 1000)
    }

    first_page = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"],
                              params=first_page_params).json()

    if first_page.get("code") != "0":
        raise Exception(f"初始请求失败: {first_page.get('msg')}")

    all_data = first_page["data"]["rows"]
    total = first_page["data"]["total"]
    page_size = first_page["data"]["pageSize"]
    total_pages = (total + page_size - 1) // page_size  # 向上取整

    print(f"📊 共发现 {total} 条数据，需抓取 {total_pages} 页")

    for page in range(2, total_pages + 1):
        params = {
            "plateNo": "",
            "parkDay": "7",  # 超过 7 天的数据
            "plateBelieve": 100,
            "pageNo": page,
            "pageSize": page_size,
            "time": int(time.time() * 1000)
        }

        try:
            resp = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"], params=params)
            if resp.json().get("code") == "0":
                all_data.extend(resp.json()["data"]["rows"])
            else:
                print(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

        time.sleep(1)

    # 4. 数据清洗与导出
    df = pd.DataFrame(all_data)
    # 字段筛选（根据需求调整）
    selected_columns = {
        "车牌号": "plateNo",
        "入场时间": "inTimeFront",
        "停车库ID": "parkingId",
        "停车库": "parkingName",
        "识别准确度": "plateBelieveString",
        "放行结果": "releaseResultName",
        "停车时长": "parkTime",
        "车辆类型": "vehicleTypeString",
        "车牌类型": "plateTypeString",
        "车辆分类": "stopTypeName",
        "入口名称": "entranceName",
        "车辆图片": "carImageURL",
        "车牌图片": "plateImageURL",
    }

    # 创建新DataFrame（仅保留需要的字段）
    cleaned_df = pd.DataFrame()
    for new_name, old_name in selected_columns.items():
        if old_name in df.columns:
            cleaned_df[new_name] = df[old_name]

    cleaned_df.to_excel("库内车辆完整数据.xlsx", index=False)
    print(f"✅ 成功获取 {len(df)}/{total} 条数据")
    return df


"""获取会员车辆列表"""


def fetch_all_vip_cars():
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token,
            "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application/recharge"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/fetchBatchVehicleInfoPage"

    # 2. 获取第一页数据（确定总页数）
    first_page_params = {
        # 车主姓名
        "ownerName": "",
        "plateNo": "",
        "pageNo": 1,
        "pageSize": 100,
        "time": int(time.time() * 1000)
    }
    first_page = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"],
                              params=first_page_params).json()

    if first_page.get("code") != "0":
        raise Exception(f"初始请求失败: {first_page.get('msg')}")

    all_data = first_page["data"]["rows"]
    total = first_page["data"]["total"]
    page_size = first_page["data"]["pageSize"]
    total_pages = (total + page_size - 1) // page_size  # 向上取整

    print(f"📊 共发现 {total} 条数据，需抓取 {total_pages} 页")

    for page in range(2, total_pages + 1):
        params = {
            "ownerName": "",
            "plateNo": "",
            "pageNo": page,
            "pageSize": page_size,
            "time": int(time.time() * 1000)
        }

        try:
            resp = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"], params=params)
            if resp.json().get("code") == "0":
                all_data.extend(resp.json()["data"]["rows"])
            else:
                print(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

        time.sleep(1)

    def process_vehicle(vehicle):
        # 提取有效期信息
        validity = vehicle['validity'][0] if vehicle['validity'] else {}
        function_time = validity.get('functionTime', {}).get('defaultTime', {})

        # 计算剩余天数（如果已经过期则显示0）
        left_days = function_time.get('leftDays', 0)
        if left_days and left_days < 0:
            left_days = 0

        # 构建结果字典
        return {
            "车辆信息ID": vehicle['vehicleId'],
            "车牌号": vehicle['plateNo'],
            "人员ID": vehicle['personId'],
            "姓名": vehicle['personName'],
            "卡号": vehicle['cardNo'] or "",
            "车辆分组ID": vehicle['vehicleGroup'],
            "车辆分组": vehicle['vehicleGroupName'],
            "停车场": validity.get('parkName', ''),
            "有效期开始": function_time.get('startTime', ''),
            "有效期结束": function_time.get('endTime', ''),
            "剩余天数": left_days,
            "所属组织": vehicle.get('organizational', '')
        }

    # 4. 数据清洗与导出
    processed_data = [process_vehicle(item) for item in all_data]
    df = pd.DataFrame(processed_data)

    # 保存到Excel
    output_file = "会员车辆信息表.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"✅ 成功获取会员车辆信息 {len(df)}/{total} 条数据")
    return df


"""获取指定日期过往车辆记录 支持按车牌号查询"""


def fetch_all_car_past_records(begin_date, end_date, plateNo):
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token,
            "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application/record/pass"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleRecord/searchVehileRecordNum"

    # 2. 获取总数量
    first_page_params = {
        "beginTime": f"{begin_date}T00:00:00.000+08:00",
        "endTime": f"{end_date}T23:59:59.000+08:00",
        "plateNo": plateNo,
        "pageNo": 1,
        "pageSize": 100,
        "time": int(time.time() * 1000)
    }
    first_page = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"],
                              params=first_page_params).json()

    if first_page.get("code") != "0":
        raise Exception(f"初始请求失败: {first_page.get('msg')}")

    all_data = []
    total = first_page["data"]["total"]
    page_size = first_page["data"]["pageSize"]
    total_pages = (total + page_size - 1) // page_size  # 向上取整

    print(f"📊 共发现 {total} 条过往车辆数据，需抓取 {total_pages} 页")

    base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleRecord/searchVehileRecordData"
    for page in range(1, total_pages + 1):
        params = {
            "beginTime": f"{begin_date}T00:00:00.000+08:00",
            "endTime": f"{end_date}T23:59:59.000+08:00",
            "plateNo": plateNo,
            "pageNo": page,
            "pageSize": page_size,
            "time": int(time.time() * 1000)
        }

        try:
            resp = requests.get(base_url, headers=auth["headers"], cookies=auth["cookies"], params=params)
            if resp.json().get("code") == "0":
                all_data.extend(resp.json()["data"]["rows"])
            else:
                print(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

        time.sleep(1)

    def process_vehicle(vehicle):
        # 转换时间戳为可读格式（如需要）
        create_time = vehicle.get('createTime')
        if create_time:
            try:
                create_time = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                create_time = str(create_time)
        else:
            create_time = ""

        # 构建结果字典
        return {
            "车牌号": vehicle['plateNo'],
            "卡号": vehicle['cardNo'] or "",
            "进出方向": vehicle['carInOutString'],
            "通行时间": vehicle['crossDateFront'],
            "车牌照片": vehicle['plateNoPicUrl'],
            "车辆照片": vehicle['vehiclePicUrl'],
            "车辆类型": vehicle['vehicleTypeString'],
            "停车类型": vehicle['stopTypeName'],
            "车道名称": vehicle['roadwayName'],
            "停车场ID": vehicle['parkId'],
            "停车场": vehicle['parkName'],
            "出入口名称": vehicle['entranceName'],
            "车辆颜色": vehicle['vehicleColorString'],
            "车牌类型": vehicle['plateTypeString'],
            "放行结果": vehicle['releaseResultName'],
            "放行方式": vehicle['releaseWayName'],
            "放行原因": vehicle['releaseReasonName'],
            "车辆类别": vehicle['carCategoryName'],
            "记录时间": vehicle['createTime']
        }

    # 4. 数据清洗与导出
    processed_data = [process_vehicle(item) for item in all_data]
    df = pd.DataFrame(processed_data)

    # 保存到Excel
    output_file = f"{begin_date}-{end_date}过往车辆记录信息表.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"✅ 成功获取 {begin_date} - {end_date} 过往车辆信息 {len(df)}/{total} 条数据")
    return df


"""车辆包期充值"""


def save_vehicle_recharge():
    # 1. 准备认证信息（复用之前的逻辑）
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn",
        "REGION_ID": "root000000",
        "Referer": "http://tingchechang.nsyy.com.cn/pms/application/recharge/addContract/57ce44f14fd549a09fe5c4ffa8c9b13f",
        "X-Requested-With": "XMLHttpRequest",
        "X-Token": token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 准备POST数据（从curl命令中解析出的原始数据）
    post_params = {
        'accountId': '',
        'personId': '',
        'vehicleId': '9a6ae2b7c865437983a7a335b1eab849',
        'parkId': '36716d9a-e37a-11eb-a77d-bb0a9f242da1',
        'phaseRuleId': '47785fbc-ed03-11eb-ac31-8b3ffff81cd1',
        'num': '1',
        'prevTimeStr': '[]',
        'newTimeStr': '[{"startTime":"2025-08-06","endTime":"2025-08-29"}]',
        'accountFlag': '0',
        'money': '0',
        'chargeType': '1',
        'payment': '1',
        'chargeCode': ''
    }

    # 3. 发送POST请求
    url = "http://tingchechang.nsyy.com.cn/pms/action/vehicleCharge/saveVehicleRecharge"

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=post_params,  # 注意使用data而不是json
            verify=False  # 对应curl的--insecure参数
        )

        # 4. 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == "0":
                print("✅ 充值信息保存成功", result)
                return True
            else:
                print(f"❌ 保存失败: {result}")
                return False
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


"""车辆包期退款 - 删除包期"""


def save_vehicle_refund(plateNo, vehicleId, parkId):
    """

    :return: bool 是否成功
    """
    # 1. 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn",
        "Proxy-Connection": "keep-alive",
        "REGION_ID": "root000000",
        "REGION_NAME": quote("根节点"),  # URL编码中文
        "Referer": f"http://tingchechang.nsyy.com.cn/pms/application/recharge/vehicleRefund/{vehicleId}/{parkId}",
        "SCENE_HEADER": "default",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 构建表单数据（严格匹配cURL格式）
    form_data = {
        "vehicleId": vehicleId,
        "plateNo": quote(plateNo),  # 车牌号需要URL编码
        "cardNo": "",
        "parkId": parkId,
        "personId": "",
        "money": "0",
        "accountFlag": ""
    }

    # 3. 发送请求
    url = "http://tingchechang.nsyy.com.cn/pms/action/vehicleCharge/saveVehicleRefund"

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=form_data,  # 注意使用data而不是json
            verify=False,
            timeout=10
        )

        # 4. 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == "0":
                print(f"✅ 车辆[{plateNo}]退款申请成功", result)
                return True
            else:
                print(f"❌ 退款失败: {result}")
                return False
        else:
            print(f"❌ HTTP错误 [{response.status_code}]")
            return False

    except requests.exceptions.Timeout:
        print("⏰ 请求超时，请检查网络连接")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {type(e).__name__}: {str(e)}")
        return False


"""新增车辆记录(仅车辆信息 不包含人员信息)"""


def save_or_update_vehicle(plateNo):
    """
    保存或更新车辆信息（表单格式POST请求）
    :param plateNo: 车牌号
    :return: bool 是否成功
    """
    # 1. 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn",
        "REGION_ID": "root000000",
        "REGION_NAME": quote("根节点"),  # URL编码中文
        "Referer": "http://tingchechang.nsyy.com.cn/pms/application/vehicle/vehicle/create",
        "SCENE_HEADER": "default",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 构建表单数据（严格匹配cURL格式）
    form_data = {
        "plateNo": plateNo,  # 车牌号需要URL编码
        "vehicleGroup": "d4f655fe-63b7-11f0-a7b1-cf4bd39c4672",
        "plateType": "8", "plateColor": "0", "vehicleType": "0", "vehicleColor": "0", "isFreeScene": "false",
        "vehicleId": "", "personName": "", "personId": "", "orgIndexCode": "", "cardNo": "",
        "mark": "", "parkIds": "", "prevTimeStr": "[]", "newTimeStr": "[]"}

    # 3. 发送请求
    url = "http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/saveOrUpdateVehicleInfo"

    try:
        response = requests.post(url, headers=headers, cookies=cookies, data=form_data,  # 注意使用data而不是json
                                 verify=False, timeout=10)

        # 4. 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == "0":
                print(f"✅ 车辆[{plateNo}]信息保存成功")
                return True
            else:
                print(f"❌ 保存失败: {result.get('msg', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP错误 [{response.status_code}]")
            return False

    except requests.exceptions.Timeout:
        print("⏰ 请求超时，请检查网络连接")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {type(e).__name__}: {str(e)}")
        return False


# 抓取车辆数据
def fetch_data():
    try:
        if login():
            if switch_to_parking_page():
                if switch_to_info_query():
                    fetch_all_timeout_cars()
                    fetch_all_vip_cars()
                    fetch_all_car_past_records('2025-08-04', '2025-08-04', '')
    except Exception as e:
        print(datetime.now(), f"❌ 主流程错误: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()
        print(datetime.now(), "✅ 浏览器已关闭")


# 添加车辆信息
def add_new_car_info(car_no):
    """
    新增车辆信息
    :return:
    """
    try:
        if login():
            if switch_to_parking_page():
                if switch_to_info_query():
                    success = save_or_update_vehicle(car_no)
                    print("操作结果:", success)
    except Exception as e:
        print(datetime.now(), f"❌ 主流程错误: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()
        print(datetime.now(), "✅ 浏览器已关闭")


# 车辆充值
def vehicle_recharge():
    try:
        if login():
            if switch_to_parking_page():
                if switch_to_info_query():
                    save_vehicle_recharge()
    except Exception as e:
        print(datetime.now(), f"❌ 主流程错误: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()
        print(datetime.now(), "✅ 浏览器已关闭")


# 退费删除包期
def vehicle_refund(plateNo, vehicleId, parkId):
    try:
        if login():
            if switch_to_parking_page():
                if switch_to_info_query():
                    save_vehicle_refund(plateNo, vehicleId, parkId)
    except Exception as e:
        print(datetime.now(), f"❌ 主流程错误: {str(e)}")
        traceback.print_exc()
    finally:
        driver.quit()
        print(datetime.now(), "✅ 浏览器已关闭")


if __name__ == "__main__":
    start_time = time.time()
    fetch_data()
    # add_new_car_info('京CTEST1')
    # vehicle_recharge()
    # vehicle_refund("京CTEST1", "9a6ae2b7c865437983a7a335b1eab849", "36716d9a-e37a-11eb-a77d-bb0a9f242da1")
    print("总耗时: ", time.time() - start_time, " s")

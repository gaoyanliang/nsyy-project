# import time
# import traceback
# from asyncio import as_completed
# from concurrent.futures import ThreadPoolExecutor
#
# import pandas as pd
# import requests
# from selenium import webdriver
# from selenium.webdriver import ActionChains
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
# from tqdm import tqdm
#
# # Chrome 基础配置
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")   # 默认全屏
# chrome_options.add_argument("--disable-extensions")
# chrome_options.add_argument("--disable-popup-blocking")
#
# # 强化配置（解决证书和资源加载问题）
# chrome_options.add_argument("--ignore-certificate-errors")  # 忽略证书错误
# chrome_options.add_argument("--ignore-ssl-errors")         # 忽略SSL错误
# chrome_options.add_argument("--disable-notifications")     # 禁用通知
#
# # 屏蔽资源加载错误
# chrome_options.add_argument("--blink-settings=imagesEnabled=false")
# chrome_options.add_argument("--disable-stylesheets")
# chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 禁用控制台日志
#
# # 启动浏览器
# driver = webdriver.Chrome(options=chrome_options)
# wait = WebDriverWait(driver, 20)  # Firefox()  Chrome()
# actions = ActionChains(driver)
#
# # 备用全屏方案（如果最大化不够）
# try:
#     driver.maximize_window()  # 双重保障
# except:
#     driver.set_window_size(1920, 1080)
#
#
# def login():
#     """登录函数"""
#     # 等待并输入用户名
#     username = WebDriverWait(driver, 15).until(
#         EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']"))
#     )
#     username.clear()
#     username.send_keys("admin1")
#
#     # 等待并输入密码
#     password = WebDriverWait(driver, 15).until(
#         EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入密码' and @type='password']"))
#     )
#     password.clear()
#     password.send_keys("Lg20252025")
#
#     # 点击登录
#     login_btn = WebDriverWait(driver, 15).until(
#         EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'login-btn')]"))
#     )
#     try:
#         login_btn.click()
#     except:
#         driver.execute_script("arguments[0].click();", login_btn)  # JS点击
#
#     # 验证登录
#     WebDriverWait(driver, 20).until(EC.text_to_be_present_in_element((By.XPATH, "//span[@class='username']"), "admin1"))
#     print(datetime.now(), "✅ 登录成功")
#
#
# def switch_to_parking_page():
#     """进入停车场出入口页面"""
#
#     # 点击"停车场出入口"菜单
#     parking_menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
#         (By.XPATH, "//div[@class='sub-nav-title' and contains(text(), '停车场出入口')]")))
#
#     # 确保元素完全可见
#     driver.execute_script("""arguments[0].scrollIntoView({behavior: 'smooth',
#                        block: 'center', inline: 'center'});""", parking_menu)
#     # 等待动画效果完成
#     time.sleep(0.5)
#     try:
#         parking_menu.click()
#     except ElementClickInterceptedException:
#         # 处理可能的遮挡
#         driver.execute_script("arguments[0].click();", parking_menu)
#     except StaleElementReferenceException:
#         # 处理元素过期
#         parking_menu = wait.until(EC.element_to_be_clickable(
#             (By.XPATH, "//*[contains(@class, 'sub-nav') and contains(., '停车场出入口')]")))
#         parking_menu.click()
#
#     try:
#         iframes = driver.find_elements(By.TAG_NAME, "iframe")
#         for index, iframe in enumerate(iframes):
#             print(datetime.now(), f"iframe {index}: {iframe.get_attribute('outerHTML')}")
#         # 切换到iframe
#         WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))
#         # 尝试定位车辆管理元素
#         WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[@title='车辆管理']")))
#         print(datetime.now(), "✅ 成功进入停车场出入口页面")
#         driver.switch_to.default_content()  # 切换回主文档
#     except Exception as e:
#         print(datetime.now(), "❌ 未找到停车场出入口菜单", e.__class__)
#         driver.switch_to.default_content()  # 确保切换回主文档
#         # 检查整个DOM结构
#         # print(datetime.now(), driver.execute_script("return document.documentElement.outerHTML;"))
#
#
#     # 强制显示元素
#     driver.execute_script("""const items = document.querySelectorAll('li.el-menu-item');
#         items.forEach(item => item.style.display = 'block');""")
#     # 等待元素渲染
#     time.sleep(0.5)  # 必要等待
#     # print(datetime.now(), driver.execute_script("return document.documentElement.outerHTML;"))
#
#     # 打印所有菜单项的文本内容
#     all_items = driver.execute_script("""return Array.from(document.querySelectorAll('li.el-menu-item'))
#             .map(item => item.textContent.trim());""")
#     print(datetime.now(), "所有菜单项文本:", all_items)
#
#
# def switch_to_info_query():
#     """专为海康威视停车场系统设计的菜单切换方案"""
#     try:
#         # 确保在主文档中
#         driver.switch_to.default_content()
#
#         # 切换到内容iframe（根据图片中的iframe000505）
#         WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))
#
#         # 在iframe内查找菜单（关键步骤）
#         menu_xpath = "//li[contains(@class,'el-menu-item') and contains(.,'信息查询')]"
#         menu = WebDriverWait(driver, 20).until(
#             EC.element_to_be_clickable((By.XPATH, menu_xpath))
#         )
#
#         # 高亮元素（调试用）
#         driver.execute_script("""
#             arguments[0].style.outline = '3px solid red';
#             arguments[0].scrollIntoView({block: 'center'});
#         """, menu)
#
#         # 6. 特殊点击处理（海康系统需要）
#         driver.execute_script("""
#             // 先触发鼠标悬停
#             arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
#
#             // 再触发点击
#             const clickEvent = new MouseEvent('click', {
#                 view: window,
#                 bubbles: true,
#                 cancelable: true
#             });
#             arguments[0].dispatchEvent(clickEvent);
#
#             // 兼容性处理
#             if (arguments[0].querySelector('a')) {
#                 arguments[0].querySelector('a').click();
#             }
#         """, menu)
#
#         # 7. 等待内容更新
#         time.sleep(2)  # 必须等待
#         WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
#                                                                         "//*[contains(text(), '过车记录查询')]")))
#
#         print(datetime.now(), "✅ 成功切换到信息查询页面")
#         cookies = {c['name']: c['value'] for c in driver.get_cookies()}
#         print(datetime.now(), cookies)
#         return True
#
#     except Exception as e:
#         print(datetime.now(), f"❌ 切换失败: {str(e)}", e.__class__)
#
#         # 获取诊断信息
#         print(datetime.now(), "当前页面HTML:", driver.execute_script("return document.documentElement.outerHTML"))
#         driver.save_screenshot("hik_fail.png")
#         return False
#
#
# try:
#     # 访问网址
#     driver.get("http://tingchechang.nsyy.com.cn/")
#
#     # 登录
#     login()
#
#     # 切换到停车场出入口页面
#     switch_to_parking_page()
#
#     # 切换到信息查询页面
#     switch_to_info_query()
#
# except Exception as e:
#     print(datetime.now(), f"❌ 发生错误: {str(e)}", e.__class__, traceback.print_exc())
#     driver.save_screenshot("error.png")
# finally:
#     driver.quit()
#


import time
import traceback
from datetime import datetime

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException

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


def login():
    """登录函数"""
    try:
        # 访问登录页面
        driver.get("http://tingchechang.nsyy.com.cn/")
        print(datetime.now(), "✅ 已访问登录页面")

        # 输入用户名
        username = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']"))
        )
        username.clear()
        username.send_keys("admin1")

        # 输入密码
        password = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入密码' and @type='password']"))
        )
        password.clear()
        password.send_keys("Lg20252025")

        # 点击登录按钮
        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'login-btn')]"))
        )
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


def switch_to_parking_page():
    """进入停车场出入口页面"""
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


def switch_to_info_query1():
    """切换到信息查询页面"""
    try:
        # 确保在主文档
        driver.switch_to.default_content()

        # 切换到iframe
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))

        # 定位并点击信息查询菜单
        menu = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//li[contains(@class,'el-menu-item') and contains(.,'信息查询')]")))

        # 使用ActionChains模拟鼠标操作
        actions.move_to_element(menu).pause(0.5).click().perform()

        # 等待页面加载
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(), '过车记录查询')]")))

        print(datetime.now(), "✅ 已切换到信息查询页面")

        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        for c in cookies:
            print(datetime.now(), c)
        return True
    except Exception as e:
        print(datetime.now(), f"❌ 切换信息查询失败: {str(e)}")
        driver.save_screenshot("info_query_fail.png")
        return False


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


def fetch_all_timeout_cars():
    """自动分页获取所有超时车辆数据（带进度条和错误重试）"""
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


def fetch_all_vip_cars():
    """获取会员车辆列表"""
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
            "车牌号": vehicle['plateNo'],
            "人员ID": vehicle['personId'],
            "姓名": vehicle['personName'],
            "卡号": vehicle['cardNo'] or "",
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


def fetch_all_car_past_records(begin_date, end_date, plateNo):
    """获取指定日期过往车辆记录"""
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


def main():
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


if __name__ == "__main__":
    main()

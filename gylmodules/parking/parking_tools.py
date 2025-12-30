from datetime import datetime
import threading
import time
import logging
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException


logger = logging.getLogger(__name__)


# 线程局部存储
thread_local = threading.local()


def getDriver():
    """为每个线程创建独立的WebDriver实例，增强稳定性"""
    if not hasattr(thread_local, 'driver'):
        # Chrome 无头模式配置 - 增强稳定性版本
        chrome_options = Options()

        # 基本配置
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        # 稳定性增强配置
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        chrome_options.add_argument("--disable-cloud-import")
        chrome_options.add_argument("--dns-prefetch-disable")

        # 内存和性能优化
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")

        chrome_options.add_argument("--single-process")  # 单进程模式，显著加速启动
        chrome_options.add_argument("--no-zygote")  # 禁用zygote进程

        # 网络和SSL配置
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        # 日志和调试禁用
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        # 实验性选项 - 显著提升启动速度
        chrome_options.add_experimental_option("excludeSwitches",
                                               ["enable-logging", "enable-automation", "ignore-certificate-errors"])

        # 防止崩溃
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")

        # 功能禁用
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")

        # 用户代理
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            # 添加重试机制
            for attempt in range(3):
                try:
                    thread_local.driver = webdriver.Chrome(options=chrome_options)

                    # 隐藏WebDriver特征
                    thread_local.driver.execute_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    thread_local.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            })
                            window.chrome = {runtime: {}};
                        '''
                    })

                    # 设置超时时间
                    thread_local.driver.set_page_load_timeout(20)
                    thread_local.driver.set_script_timeout(20)
                    thread_local.driver.implicitly_wait(10)

                    logger.debug(f"✅ WebDriver 创建成功 (尝试 {attempt + 1})")
                    break

                except Exception as e:
                    if attempt == 2:
                        raise e
                    logger.warning(f"⚠️ WebDriver 创建失败，重试 {attempt + 1}/3: {e}")
                    time.sleep(2)

        except Exception as e:
            logger.error(f"❌ WebDriver 创建失败: {e}")
            raise

    return thread_local.driver


def cleanup_driver():
    """清理线程的driver"""
    if hasattr(thread_local, 'driver'):
        try:
            thread_local.driver.quit()
        except Exception as e:
            logger.debug(f"清理driver时发生错误: {e}")
        finally:
            if hasattr(thread_local, 'driver'):
                del thread_local.driver


"""登录函数"""


def login(driver):
    try:
        # 访问登录页面
        driver.get("http://tingchechang.nsyy.com.cn/")
        logger.debug("✅ 已访问登录页面")

        # 输入用户名
        username = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']")))
        username.clear()
        username.send_keys("admin1")

        # 输入密码
        password = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入密码' and @type='password']")))
        password.clear()
        password.send_keys("Lg20252025")

        # 点击登录按钮
        login_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'login-btn')]")))
        try:
            login_btn.click()
        except:
            driver.execute_script("arguments[0].click();", login_btn)

        # 验证登录成功
        WebDriverWait(driver, 30).until(EC.text_to_be_present_in_element((By.XPATH, "//span[@class='username']"), "admin1"))
        logger.debug("✅ 停车场系统登录成功")
    except Exception as e:
        logger.error(f"❌ 停车场系统登录失败: {str(e)}")
        raise Exception("停车场系统登录失败", e.__str__())


"""进入停车场出入口页面"""


def switch_to_parking_page(driver):
    try:
        # 点击菜单
        parking_menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='sub-nav-title' and contains(text(), '停车场出入口')]")))

        # 滚动到视图中心
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parking_menu)
        time.sleep(0.5)

        # 点击菜单
        try:
            parking_menu.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", parking_menu)
        logger.debug("✅ 已进入停车场出入口页面")
    except Exception as e:
        logger.error(f"❌ 进入停车场页面失败: {str(e)}")
        raise Exception("进入停车场页面失败", e.__str__())


"""切换至信息查询菜单 获取指定cookie"""


def switch_to_info_query(driver):
    """专为海康威视停车场系统设计的菜单切换方案"""
    try:
        # 确保在主文档中
        driver.switch_to.default_content()

        # 使用更快的iframe切换方式
        try:
            # 方法1：直接通过ID快速切换（最快）
            iframe = driver.find_element(By.ID, "iframe000505")
            driver.switch_to.frame(iframe)
        except:
            # 方法2：使用CSS选择器
            iframe = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[id='iframe000505']"))
            )
            driver.switch_to.frame(iframe)

        # # 切换到内容iframe（根据图片中的iframe000505）
        # WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))

        # 在iframe内查找菜单（关键步骤）
        menu_xpath = "//li[contains(@class,'el-menu-item') and contains(.,'信息查询')]"
        menu = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, menu_xpath))
        )

        # # 高亮元素（调试用）
        # driver.execute_script("""arguments[0].style.outline = '3px solid red';
        #     arguments[0].scrollIntoView({block: 'center'});""", menu)
        #
        # # 6. 特殊点击处理（海康系统需要）
        # driver.execute_script("""
        #     // 先触发鼠标悬停
        #     arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
        #
        #     // 再触发点击
        #     const clickEvent = new MouseEvent('click', {view: window, bubbles: true, cancelable: true});
        #     arguments[0].dispatchEvent(clickEvent);
        #
        #     // 兼容性处理
        #     if (arguments[0].querySelector('a')) {
        #         arguments[0].querySelector('a').click();
        #     }
        # """, menu)

        # 7. 等待内容更新
        time.sleep(2)  # 必须等待
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
        #                                                                 "//*[contains(text(), '过车记录查询')]")))

        logger.debug("✅ 成功切换到信息查询页面")
        # for c in driver.get_cookies():
        #     print(c)
    except Exception as e:
        logger.error(f"❌ 切换至信息查询页面异常: {str(e)}")
        raise Exception("切换至信息查询页面异常", e.__str__())
        # # 获取诊断信息
        # print(datetime.now(), "当前页面HTML:", driver.execute_script("return document.documentElement.outerHTML"))


def request_with_retry(url, headers, cookies, datas, is_get=False, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            if is_get:
                response = requests.get(url, headers=headers, cookies=cookies, params=datas)
            else:
                response = requests.post(url, headers=headers, cookies=cookies,
                                         data=datas, verify=False, timeout=10)

            # 检查HTTP状态码
            response.raise_for_status()
            # 检查响应内容是否有效
            if not response.text:
                raise ValueError("响应内容为空")
            # 尝试解析JSON响应
            try:
                result = response.json()
            except ValueError:
                raise ValueError("响应不是有效的JSON格式")

            if result.get("code") != "0":
                raise Exception(f"接口返回错误 重试: {result.get('msg')} {result.get('data')}")

            return result
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise Exception(f"达到最大重试次数 {max_retries} 次，最终失败: {str(e)}")


"""获取所有超时车辆数据（停车时长超过 7 天）"""


def fetch_all_timeout_cars(driver):
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token, "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleInParking/getVehicleInParkingPage"

    # 2. 获取第一页数据（确定总页数）
    first_page_params = {
        "time": int(time.time() * 1000), "plateNo": "", "parkDay": "3",  # 超过 7 天的数据
        "plateBelieve": 100, "pageNo": 1, "pageSize": 100
    }

    try:
        first_page = request_with_retry(base_url, auth["headers"], auth["cookies"], first_page_params, True)

        if first_page.get("code") != "0":
            raise Exception("初始请求失败")

        all_data = first_page["data"]["rows"]
        total = first_page["data"]["total"]
        page_size = first_page["data"]["pageSize"]
        total_pages = (total + page_size - 1) // page_size  # 向上取整
        logger.debug(f"📊 共发现 {total} 条数据，需抓取 {total_pages} 页")

        for page in range(2, total_pages + 1):
            params = {
                "time": int(time.time() * 1000), "plateNo": "", "parkDay": "3",  # 超过 7 天的数据
                "plateBelieve": 100, "pageNo": page, "pageSize": page_size
            }
            resp = request_with_retry(base_url, auth["headers"], auth["cookies"], params, True)
            if resp.get("code") == "0":
                all_data.extend(resp["data"]["rows"])
            else:
                logger.warning(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
    except:
        raise Exception("获取超时车辆数据失败")

    all_timeout_cars = []
    for car in all_data:
        all_timeout_cars.append({"plate_no": car.get('plateNo'), "park_time": car.get('parkTime')})

    logger.debug(f"✅ 成功获取 {len(all_timeout_cars)}/{total} 条超时车辆数据")
    return all_timeout_cars


"""获取会员车辆列表"""


def fetch_all_vip_cars(driver):
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token, "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application/recharge"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/fetchBatchVehicleInfoPage"

    # 2. 获取第一页数据（确定总页数）
    first_page_params = {
        "ownerName": "", "plateNo": "", "pageNo": 1, "pageSize": 100,
        "time": int(time.time() * 1000)
    }
    try:
        first_page = request_with_retry(base_url, auth["headers"], auth["cookies"], first_page_params, True)
        if first_page.get("code") != "0":
            raise Exception("会员车辆初始请求失败")

        all_data = first_page["data"]["rows"]
        total = first_page["data"]["total"]
        page_size = first_page["data"]["pageSize"]
        total_pages = (total + page_size - 1) // page_size  # 向上取整
        logger.debug(f"📊 共发现 {total} 条会员车辆数据，需抓取 {total_pages} 页")

        for page in range(2, total_pages + 1):
            params = {"ownerName": "", "plateNo": "", "pageNo": page, "pageSize": page_size,
                      "time": int(time.time() * 1000)}
            resp = request_with_retry(base_url, auth["headers"], auth["cookies"], params, True)
            if resp.get("code") == "0":
                all_data.extend(resp["data"]["rows"])
            else:
                logger.warning(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
    except:
        raise Exception("获取会员车辆列表失败")

    def process_vehicle(vehicle):
        # 提取有效期信息
        validity = vehicle['validity'][0] if vehicle['validity'] else {}
        function_time = validity.get('functionTime', {}).get('defaultTime', {})
        if validity.get('state', -1) != 0:
            try:
                function_time = validity.get('functionTime', {}).get('detailTimes', [])
                function_time = function_time[len(function_time) - 1]
            except:
                function_time = validity.get('functionTime', {}).get('defaultTime', {})

        # 计算剩余天数（如果已经过期则显示0）
        left_days = function_time.get('leftDays', 0)
        if left_days and left_days <= 0:
            left_days = 0

        # 构建结果字典
        return {
            "vehicle_id": vehicle['vehicleId'],
            "plate_no": vehicle['plateNo'],
            "person_name": vehicle['personName'],
            "vehicle_group": vehicle['vehicleGroupName'],
            "park_name": validity.get('parkName', ''),
            "start_date": function_time.get('startTime', ''),
            "end_date": function_time.get('endTime', ''),
            "vip_status": 1 if int(left_days) > 0 else 2,
            "left_days": int(left_days)
        }

    all_vip_cars = []
    for car in all_data:
        all_vip_cars.append(process_vehicle(car))

    logger.debug(f"✅ 获取会员车辆列表成功 {len(all_vip_cars)}/{total} 条数据")
    # # 4. 数据清洗与导出
    # processed_data = [process_vehicle(item) for item in all_data]
    # df = pd.DataFrame(processed_data)
    #
    # # 保存到Excel
    # output_file = "会员车辆信息表.xlsx"
    # df.to_excel(output_file, index=False, engine='openpyxl')
    # print(f"✅ 成功获取会员车辆信息 {len(df)}/{total} 条数据")
    return all_vip_cars


"""获取指定日期过往车辆记录 支持按车牌号查询"""


def fetch_all_car_past_records(driver, begin_date, end_date, plateNo):
    # 1. 获取实时认证
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")
    auth = {
        "headers": {
            "Cookie": f"JSESSIONID={cookies['JSESSIONID']}; CASTGC={cookies.get('CASTGC', '')}",
            "X-Token": token, "REGION_ID": "root000000",
            "Referer": "http://tingchechang.nsyy.com.cn/pms/application/record/pass"
        },
        "cookies": cookies
    }
    base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleRecord/searchVehileRecordNum"

    # 2. 获取总数量
    first_page_params = {
        "beginTime": f"{begin_date}T00:00:00.000+08:00",
        "endTime": f"{end_date}T23:59:59.000+08:00",
        "plateNo": plateNo, "pageNo": 1, "pageSize": 100, "time": int(time.time() * 1000)
    }

    try:
        first_page = request_with_retry(base_url, auth["headers"], auth["cookies"], first_page_params, True)
        if first_page.get("code") != "0":
            raise Exception(f"初始请求失败: {first_page.get('msg')}")

        all_data = []
        total = first_page["data"]["total"]
        page_size = first_page["data"]["pageSize"]
        total_pages = (total + page_size - 1) // page_size  # 向上取整
        logger.debug(f"📊 共发现 {total} 条过往车辆数据，需抓取 {total_pages} 页")

        base_url = "http://tingchechang.nsyy.com.cn/pms/action/queryVehicleRecord/searchVehileRecordData"
        for page in range(1, total_pages + 1):
            params = {
                "beginTime": f"{begin_date}T00:00:00.000+08:00",
                "endTime": f"{end_date}T23:59:59.000+08:00",
                "plateNo": plateNo, "pageNo": page, "pageSize": page_size, "time": int(time.time() * 1000)
            }

            resp = request_with_retry(base_url, auth["headers"], auth["cookies"], params, True)
            if resp.get("code") == "0":
                all_data.extend(resp["data"]["rows"])
            else:
                logger.warning(f"⚠️ 页面 {resp.url.split('pageNo=')[1].split('&')[0]} 数据异常")
    except Exception as e:
        raise Exception(f"获取过往车记录列表失败 {e}")

    all_records = []
    for vehicle in all_data:
        all_records.append({
            "plate_no": vehicle['plateNo'],
            "car_in_out": vehicle['carInOutString'],
            "cross_date": vehicle['crossDateFront'],
            "vehicle_pic": vehicle['vehiclePicUrl'],
            "park_name": vehicle['parkName'],
            "entrance_name": vehicle['entranceName'],
            "uuid": vehicle['uuid'],
        })
    logger.debug(f"✅ 获取过往车辆列表成功 {len(all_records)}/{total} 条数据")
    # # 4. 数据清洗与导出
    # processed_data = [process_vehicle(item) for item in all_data]
    # df = pd.DataFrame(processed_data)
    #
    # # 保存到Excel
    # output_file = f"{begin_date}-{end_date}过往车辆记录信息表.xlsx"
    # df.to_excel(output_file, index=False, engine='openpyxl')
    # print(f"✅ 成功获取 {begin_date} - {end_date} 过往车辆信息 {len(df)}/{total} 条数据")
    return all_records


"""车辆包期充值"""


def vehicle_recharge(driver, vehicle_id, park_id, start_date, end_date):
    # 1. 准备认证信息（复用之前的逻辑）
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    token = driver.execute_script("return localStorage.getItem('token')")

    headers = {
        "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn", "REGION_ID": "root000000",
        "Referer": "http://tingchechang.nsyy.com.cn/pms/application/recharge/addContract/57ce44f14fd549a09fe5c4ffa8c9b13f",
        "X-Requested-With": "XMLHttpRequest", "X-Token": token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 准备POST数据（从curl命令中解析出的原始数据）
    post_params = {
        'vehicleId': vehicle_id, 'parkId': park_id, 'phaseRuleId': '47785fbc-ed03-11eb-ac31-8b3ffff81cd1',
        'newTimeStr': '[{"startTime": "{1}", "endTime": "{2}"}]'.replace('{1}', start_date).replace('{2}', end_date),
        'num': '1', 'prevTimeStr': '[]', 'accountFlag': '0', 'money': '0', 'chargeType': '1',
        'payment': '1', 'chargeCode': '', 'accountId': '', 'personId': ''
    }

    # 3. 发送POST请求
    try:
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleCharge/saveVehicleRecharge",
                                    headers, cookies, post_params)

        if result.get("code") != "0":
            logger.error(f"❌ 会员充值失败: {result}, {post_params}")
            return False, ""

        logger.debug(f"✅ 充值信息保存成功 {result}")
        return True, result
    except Exception as e:
        logger.error(f"❌ 会员充值失败: {str(e)}, {post_params}")
        return False, ""


"""车辆包期退款 - 删除包期
需要执行两个操作 1 包期退款（退款之后 有效期截止到退款当日）， 2 包期删除
"""


def vehicle_refund(driver, plateNo, vehicleId, parkId):
    # 1. 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}

    headers = {
        "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn", "Proxy-Connection": "keep-alive",
        "REGION_ID": "root000000", "REGION_NAME": quote("根节点"),  # URL编码中文
        "Referer": f"http://tingchechang.nsyy.com.cn/pms/application/recharge/vehicleRefund/{vehicleId}/{parkId}",
        "SCENE_HEADER": "default", "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 构建表单数据（严格匹配cURL格式）
    form_data = {
        "vehicleId": vehicleId, "plateNo": quote(plateNo),  # 车牌号需要URL编码
        "parkId": parkId, "cardNo": "", "personId": "", "money": "0", "accountFlag": ""
    }

    # 3. 发送请求
    try:
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleCharge/saveVehicleRefund",
                                    headers, cookies, form_data)
        if result.get("code") != "0":
            logger.warning(f"❌ 车辆[{plateNo}]会员包期退款申请失败 {form_data}")
            return False, ""

        headers['Referer'] = f'http://tingchechang.nsyy.com.cn/pms/application/recharge/profile/{vehicleId}'
        form_data = {"vehicleId": vehicleId, "parkId": parkId}
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleCharge/deleteVehicleParkFunction",
                                    headers, cookies, form_data)
        logger.debug(f"✅ 车辆[{plateNo}]会员包期退款 删除申请成功, {result}")
        return True, result
    except Exception as e:
        logger.warning(f"❌ 车辆[{plateNo}]会员包期退款 删除申请失败 {form_data}, {e}")
        return False, ""


"""新增车辆记录(仅车辆信息 不包含人员信息)"""


def save_vehicle(driver, plateNo, vehicleGroup):
    """
    保存或更新车辆信息（表单格式POST请求）
    :param plateNo: 车牌号
    :return: bool 是否成功
    """
    # 1. 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    headers = {
        "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn", "REGION_ID": "root000000",
        "REGION_NAME": quote("根节点"),  # URL编码中文
        "Referer": "http://tingchechang.nsyy.com.cn/pms/application/vehicle/vehicle/create",
        "SCENE_HEADER": "default", "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 构建表单数据（严格匹配cURL格式）
    form_data = {
        "plateNo": plateNo, "vehicleGroup": vehicleGroup,
        "plateType": "8", "plateColor": "0", "vehicleType": "0", "vehicleColor": "0", "isFreeScene": "false",
        "vehicleId": "", "personName": "", "personId": "", "orgIndexCode": "", "cardNo": "",
        "mark": "", "parkIds": "", "prevTimeStr": "[]", "newTimeStr": "[]"}

    # 3. 发送请求
    try:
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/saveOrUpdateVehicleInfo",
                                    headers, cookies, form_data)
        if result.get("code") != "0":
            logger.warning(f"❌ 会员车辆添加失败: {result}")
            return False, ''

        logger.debug(f"✅ 会员车辆[{plateNo}]新增成功, {result}")
        return True, result
    except Exception as e:
        logger.warning(f"❌ 会员车辆添加失败: {e}")
        return False, ''


"""更新车辆车牌号"""


def update_vehicle(driver, plateNo, vehicleId, vehicleGroup):
    """
    :param plateNo: 车牌号
    :return: bool 是否成功
    """
    # 1. 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    headers = {
        "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "http://tingchechang.nsyy.com.cn", "REGION_ID": "root000000",
        "REGION_NAME": quote("根节点"),  # URL编码中文
        # "Referer": "http://tingchechang.nsyy.com.cn/pms/application/vehicle/vehicle/create",
        "SCENE_HEADER": "default", "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    # 2. 构建表单数据（严格匹配cURL格式）
    form_data = {"vehicleId": vehicleId, "plateNo": plateNo, "vehicleGroup": vehicleGroup}

    # 3. 发送请求
    try:
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/saveOrUpdateVehicleInfo",
                                    headers, cookies, form_data)
        if result.get("code") != "0":
            logger.warning(f"❌ 会员车辆车牌号更新失败: {result}")
            return False, ''

        logger.debug(f"✅ 会员车辆[{plateNo}]车牌号更新成功, {result}")
        return True, result
    except Exception as e:
        logger.warning(f"❌ 会员车辆车牌号更新失败: {e}")
        return False, ''


"""删除车辆记录"""


def delete_vehicle(driver, vehicleId):
    """
    保存或更新车辆信息（表单格式POST请求）
    :param plateNo: 车牌号
    :return: bool 是否成功
    """
    # 从浏览器获取认证信息
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    headers = {
        "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "REGION_ID": "root000000",
        "Origin": "http://tingchechang.nsyy.com.cn", "REGION_NAME": quote("根节点"),  # URL编码中文
        "Referer": "http://tingchechang.nsyy.com.cn/pms/application/vehicle/vehicle",
        "SCENE_HEADER": "default", "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    try:
        result = request_with_retry("http://tingchechang.nsyy.com.cn/pms/action/vehicleInfo/deleteVehicle",
                                    headers, cookies, {"ids": vehicleId})
        if result.get("code") != "0":
            logger.warning(f"❌ 会员车辆删除失败: {result}")
            return False, ''

        logger.debug(f"✅ 会员车辆删除成功, {result}")
        return True, result
    except Exception as e:
        logger.warning(f"❌ 会员车辆删除失败: {e}")
        return False, ''


# 抓取车辆数据
def fetch_data(start_date, end_date, is_fetch_vip):
    try:
        driver = getDriver()
        # 登陆系统 进入指定页面 获取cookie
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        vip_cars = []
        if is_fetch_vip:
            vip_cars = fetch_all_vip_cars(driver)
        # 抓取数据
        timeout_cars = fetch_all_timeout_cars(driver)
        past_records = fetch_all_car_past_records(driver, start_date, end_date, '')

        return timeout_cars, vip_cars, past_records
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 添加车辆信息 & 会员包期充值
def add_new_car_and_recharge(car_no, park_id, start_date, end_date, group):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        vehicle_group = "b67185ee-ebad-11eb-9892-8f05dd1cd40b"
        if group == 'VIP':
            vehicle_group = "ab3ccf1c-ebb2-11eb-9895-5f4afbf5c8f2"
        success, car_info = save_vehicle(driver, car_no, vehicle_group)
        if not success:
            return None

        vehicle_id = car_info['data'].get('vehicleId')
        try:
            success, result = vehicle_recharge(driver, vehicle_id, park_id, start_date, end_date)
            if success and result.get("code") != "0":
                # 充值失败，删除车辆信息
                delete_vehicle(driver, vehicle_id)

            return vehicle_id
        except:
            # 会员包期充值失败，删除车辆信息
            delete_vehicle(driver, vehicle_id)
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 添加会员包期
def add_vip_card(vehicle_id, park_id, start_date, end_date):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        success, result = vehicle_recharge(driver, vehicle_id, park_id, start_date, end_date)
        return success, result
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 移除会员包期
def remove_vip_card(plate_no, vehicle_id, park_id):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        success, result = vehicle_refund(driver, plate_no, vehicle_id, park_id)
        return success, result
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 重置会员包期
def reset_vip_card(plate_no, vehicle_id, park_id, start_date, end_date):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        success, result = vehicle_refund(driver, plate_no, vehicle_id, park_id)
        if not success:
            raise Exception("会员包期重置失败")

        success, result = vehicle_recharge(driver, vehicle_id, park_id, start_date, end_date)
        return success, result
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 删除会员车辆
def delete_vip_car(vehicle_id):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        success, result = delete_vehicle(driver, vehicle_id)
        return success, result
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


# 更新车牌号
def update_car_plate_no(vehicle_id, new_plate_no, group):
    try:
        driver = getDriver()
        login(driver)
        switch_to_parking_page(driver)
        switch_to_info_query(driver)

        vehicleGroup = "b67185ee-ebad-11eb-9892-8f05dd1cd40b"
        if group == 'VIP':
            vehicleGroup = "ab3ccf1c-ebb2-11eb-9895-5f4afbf5c8f2"
        success, result = update_vehicle(driver, new_plate_no, vehicle_id, vehicleGroup)
        return success, result
    finally:
        logger.debug("✅ 浏览器已关闭")
        cleanup_driver()


if __name__ == "__main__":
    start_t = time.time()
    driver = getDriver()
    # 登陆系统 进入指定页面 获取cookie
    login(driver)
    switch_to_parking_page(driver)
    switch_to_info_query(driver)

    # 抓取数据
    timeout_cars = fetch_all_timeout_cars(driver)
    for item in timeout_cars:
        print(item)

    # logger.debug("浏览器关闭耗时 ", time.time() - start_time)
    print("总耗时: ", time.time() - start_t, " s")

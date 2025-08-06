import random
import time
import traceback
from asyncio import as_completed
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
from tqdm import tqdm

# Chrome 基础配置
chrome_options = Options()
chrome_options.add_argument("--start-maximized")   # 默认全屏
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-popup-blocking")

# 强化配置（解决证书和资源加载问题）
chrome_options.add_argument("--ignore-certificate-errors")  # 忽略证书错误
chrome_options.add_argument("--ignore-ssl-errors")         # 忽略SSL错误
chrome_options.add_argument("--disable-notifications")     # 禁用通知

# 屏蔽资源加载错误
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
chrome_options.add_argument("--disable-stylesheets")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 禁用控制台日志

# 启动浏览器
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)  # Firefox()  Chrome()
actions = ActionChains(driver)

# 备用全屏方案（如果最大化不够）
try:
    driver.maximize_window()  # 双重保障
except:
    driver.set_window_size(1920, 1080)


def login():
    """登录函数"""
    # 等待并输入用户名
    username = WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入用户名']"))
    )
    username.clear()
    username.send_keys("admin1")

    # 等待并输入密码
    password = WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='请输入密码' and @type='password']"))
    )
    password.clear()
    password.send_keys("Lg20252025")

    # 点击登录
    login_btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'login-btn')]"))
    )
    try:
        login_btn.click()
    except:
        driver.execute_script("arguments[0].click();", login_btn)  # JS点击

    # 验证登录
    WebDriverWait(driver, 20).until(EC.text_to_be_present_in_element((By.XPATH, "//span[@class='username']"), "admin1"))
    print("✅ 登录成功")


def switch_to_parking_page():
    """进入停车场出入口页面"""

    # 点击"停车场出入口"菜单
    parking_menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
        (By.XPATH, "//div[@class='sub-nav-title' and contains(text(), '停车场出入口')]")))

    # 确保元素完全可见
    driver.execute_script("""arguments[0].scrollIntoView({behavior: 'smooth',
                       block: 'center', inline: 'center'});""", parking_menu)
    # 等待动画效果完成
    time.sleep(0.5)
    try:
        parking_menu.click()
    except ElementClickInterceptedException:
        # 处理可能的遮挡
        driver.execute_script("arguments[0].click();", parking_menu)
    except StaleElementReferenceException:
        # 处理元素过期
        parking_menu = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(@class, 'sub-nav') and contains(., '停车场出入口')]")))
        parking_menu.click()

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for index, iframe in enumerate(iframes):
            print(f"iframe {index}: {iframe.get_attribute('outerHTML')}")
        # 切换到iframe
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505")))
        # 尝试定位车辆管理元素
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[@title='车辆管理']")))
        print("✅ 成功进入停车场出入口页面")
        driver.switch_to.default_content()  # 切换回主文档
    except Exception as e:
        print("❌ 未找到停车场出入口菜单", e.__class__)
        driver.switch_to.default_content()  # 确保切换回主文档
        # 检查整个DOM结构
        # print(driver.execute_script("return document.documentElement.outerHTML;"))


    # 强制显示元素
    driver.execute_script("""const items = document.querySelectorAll('li.el-menu-item');
        items.forEach(item => item.style.display = 'block');""")
    # 等待元素渲染
    time.sleep(0.5)  # 必要等待
    # print(driver.execute_script("return document.documentElement.outerHTML;"))

    # 打印所有菜单项的文本内容
    all_items = driver.execute_script("""return Array.from(document.querySelectorAll('li.el-menu-item'))
            .map(item => item.textContent.trim());""")
    print("所有菜单项文本:", all_items)


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

        print("✅ 成功切换到信息查询页面")
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        print(cookies)
        return True

    except Exception as e:
        print(f"❌ 切换失败: {str(e)}", e.__class__)

        # 获取诊断信息
        print("当前页面HTML:", driver.execute_script("return document.documentElement.outerHTML"))
        driver.save_screenshot("hik_fail.png")
        return False


def export_parking_vehicles():
    """自动化获取库内所有车辆数据（支持分页/异常处理）"""
    try:
        # 1. 切换到内容iframe（关键步骤）
        driver.switch_to.default_content()
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe000505"))
        )

        # 2. 点击【库内车辆查询】子菜单（根据图片中的title属性）
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//li[@title='库内车辆查询']"))
        ).click()

    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        driver.save_screenshot("error.png")
        return []


def fetch_all_vehicles():
    """自动分页获取所有车辆数据（带进度条和错误重试）"""
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


def enter_system_management():
    """处理会新开标签页的系统管理菜单"""
    try:
        # 1. 确保在主文档中
        driver.switch_to.default_content()
        time.sleep(1)  # 等待页面稳定

        # 2. 获取当前窗口句柄（用于后续切换回来）
        main_window = driver.current_window_handle

        # 3. 定位菜单图标（根据图片中的三横线图标）
        menu_icon = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'h-icon-menu_leftbar')]"))
        )

        # 4. 点击展开菜单
        menu_icon.click()
        print("✅ 已展开主菜单")

        # 5. 定位系统管理菜单项
        system_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), '系统管理')]"))
        )

        # 6. 获取当前窗口数
        original_windows = driver.window_handles

        # 7. 点击系统管理（使用JS确保点击生效）
        driver.execute_script("arguments[0].click();", system_menu)
        print("✅ 已点击系统管理")

        # 8. 等待新标签页打开（关键修正）
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(original_windows))
        new_window = [window for window in driver.window_handles if window not in original_windows][0]

        # 9. 切换到新标签页
        driver.switch_to.window(new_window)
        print("✅ 已切换到新标签页")

        # 10. 验证是否进入系统管理
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), '用户管理') or contains(text(), '系统设置')]"))
        )
        print("✅ 成功进入系统管理页面")
        return True

    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        print("当前窗口数量:", len(driver.window_handles))
        print("当前URL:", driver.current_url)
        driver.save_screenshot("new_tab_fail.png")
        return False


def xitong_guanli():
    """
    登陆成功之后进入系统管理页面 维护人员信息
    :return:
    """
    try:
        # 访问网址
        driver.get("http://tingchechang.nsyy.com.cn/")

        # 登录
        login()

        # 进入系统管理
        enter_system_management()

    except Exception as e:
        print(f"❌ 发生错误: {str(e)}", e.__class__, traceback.print_exc())
        driver.save_screenshot("error.png")
    finally:
        driver.quit()




try:
    # 访问网址
    driver.get("http://tingchechang.nsyy.com.cn/")

    # 登录
    login()

    # 进入系统管理
    enter_system_management()

    # # 切换到停车场出入口页面
    # switch_to_parking_page()
    #
    # # 切换到信息查询页面
    # switch_to_info_query()
    #
    # # 进入 库内车辆查询
    # export_parking_vehicles()

    # data = fetch_all_vehicles()

except Exception as e:
    print(f"❌ 发生错误: {str(e)}", e.__class__, traceback.print_exc())
    driver.save_screenshot("error.png")
finally:
    driver.quit()


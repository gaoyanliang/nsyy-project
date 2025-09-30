import threading
import time
import logging

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

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
            print(datetime.now(), "✅ WebDriver 已正常关闭")
        except Exception as e:
            print(datetime.now(), f"❌ 清理driver时发生错误 {e}")
        finally:
            if hasattr(thread_local, 'driver'):
                del thread_local.driver


"""登录函数"""


def login(driver, url):
    try:
        driver.get(url)
        print(datetime.now(), "🚀 页面已打开，开始等待【获取数据】按钮出现...")

        # 等待页面DOM加载完成
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )

        # 等待加载遮罩消失
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "el-loading-mask"))
        )

        # 额外等待一下确保所有异步操作完成
        time.sleep(2)

        button = WebDriverWait(driver, 20).until(EC.visibility_of_element_located(
                (By.XPATH, "//button[.//span[contains(text(), '获取数据')]]")))
        print(datetime.now(), "🖱️ 已等待到【获取数据】按钮出现，准备点击")

        # 点击按钮
        button.click()

        # 等待包含指定文字的弹框出现
        WebDriverWait(driver, 60).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//div[contains(@class, 'el-message-box') or contains(@class, 'el-message')]"),
                "PDF报告上传成功！"
            )
        )

        print(datetime.now(), "🎉 检测到【PDF报告上传成功！】弹框，准备关闭")
    except Exception as e:
        raise Exception("进入检查报告单页面失败", e.__str__())


def process_report_item(item):
    """处理单个报告项 根据来源确定URL"""
    if global_config.run_in_local:
        url_map = {
            '油田': "http://192.168.124.14:8081/?id=10952757&str=pdf&type=15#/",
            '康复': "http://192.168.124.14:8081/?id=10952757&str=pdf&type=35#/",
            '其他': "http://192.168.124.14:8081/?id=10952757&str=pdf&type=15#/"
        }
    else:
        url_map = {
            '油田': "http://192.168.3.12:6060/index3.html?str=pdf&type=15#/",
            '康复': "http://192.168.3.12:6060/index3.html?str=pdf&type=35#/",
            '其他': "http://192.168.3.12:6060/index3.html?str=pdf&type=15#/"
        }

    source = item.get('来源', '其他')
    url = url_map.get(source, url_map['其他'])
    if not url.startswith('http'):
        print(datetime.now(), f"❌ 无效的URL: {url}")
        return False

    try:
        start_time = time.time()
        driver = getDriver()
        # print(datetime.now(), f"📊 正在处理报告: {item.get('id', '未知ID')}")

        success = login(driver, url)
        # print(datetime.now(), f"⏱️ 处理耗时: {time.time() - start_time:.2f}秒")
        return success

    except Exception as e:
        print(datetime.now(), f"❌ 处理报告时发生错误: {e}")
        return False
    finally:
        # 注意：不要在这里关闭driver，因为它是线程局部的
        pass


def auto_pacs():
    """主处理函数"""
    # print(datetime.now(), "🚀 开始自动PACS处理任务")

    try:
        while True:
            # 获取待处理的报告
            db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                        global_config.DB_DATABASE_GYL)
            records = db.query_all(
                "SELECT * FROM nsyy_gyl.medical_reports WHERE is_upload = 0"
            )
            del db

            if not records:
                logger.info("✅ 所有报告已处理完成")
                break

            # print(datetime.now(), f"📊 待处理报告: {records[0]['id']}")
            # 处理每个报告
            success_count = 0
            for item in records:
                if process_report_item(item):
                    success_count += 1
            # 短暂休息避免过度频繁查询
            time.sleep(1)
    except Exception as e:
        print(datetime.now(), f"❌ 自动PACS处理任务失败: {e}")
    finally:
        print(datetime.now(), "🛑 自动PACS处理任务结束")
        # 程序结束时清理所有线程的driver
        cleanup_driver()


if __name__ == "__main__":
    auto_pacs()


"""
pacs_router 随项目一起启动

yt_pacs_tools 单独执行， 通过接口调用 auto——pacs 会造成阻塞 无法生成pdf
/home/gyl/.conda/envs/gg/bin/python /home/gyl/gyl_server/gylmodules/pacs_pdf/yt_pacs_tools.py > /home/gyl/pacs_pdf.log 2>&1
"""

import threading
import time
import logging

from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

run_in_local = True

db_config = {
    'host': '127.0.0.1' if run_in_local else '192.168.3.12',
    'user': 'root' if run_in_local else 'gyl',
    'password': 'gyl.2015' if run_in_local else '123456',
}


# 线程局部存储
thread_local = threading.local()


def getDriver():
    """为每个线程创建独立的WebDriver实例"""
    if not hasattr(thread_local, 'driver'):
        chrome_options = Options()

        # 简化配置，减少可能的问题
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        # 移除可能引起问题的配置
        # chrome_options.add_argument("--single-process")  # 这个可能引起稳定性问题
        # chrome_options.add_argument("--no-zygote")       # 这个可能引起稳定性问题

        # 保留必要的配置
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")

        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            thread_local.driver = webdriver.Chrome(options=chrome_options)

            # 设置合理的超时时间
            thread_local.driver.set_page_load_timeout(30)
            thread_local.driver.set_script_timeout(20)
            thread_local.driver.implicitly_wait(10)

            logger.debug("✅ WebDriver 创建成功")

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
        # print(datetime.now(), "🚀 页面已打开，开始等待【获取数据】按钮出现...")

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
        # print(datetime.now(), "🖱️ 已等待到【获取数据】按钮出现，准备点击")

        # 点击按钮
        # button.click()

        # 使用JavaScript点击，避免元素被遮挡
        driver.execute_script("arguments[0].click();", button)
        # print(datetime.now(), "✅ 已点击获取数据按钮")

        # 短暂等待确保点击生效
        time.sleep(2)

        # 等待包含指定文字的弹框出现
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//div[contains(@class, 'el-message-box') or contains(@class, 'el-message')]"),
                "PDF报告上传成功！"
            )
        )
        print(datetime.now(), "🎉 检测到【PDF报告上传成功！】弹框，准备关闭")
        time.sleep(2)
    except Exception as e:
        # # 添加更详细的错误信息
        # print(datetime.now(), f"❌ 登录过程失败: {str(e)}")
        #
        # # 保存页面截图以便调试
        # try:
        #     driver.save_screenshot(f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        #     print(datetime.now(), "📸 已保存错误截图")
        # except:
        #     pass
        raise Exception(f"进入检查报告单页面失败: {str(e)}")
    # raise Exception("进入检查报告单页面失败", e.__str__())


def process_report_item(item):
    """处理单个报告项 根据来源确定URL"""
    if run_in_local:
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

        success = login(driver, url)
        return success
    except Exception as e:
        print(datetime.now(), f"❌ 处理报告时发生错误: {e}")
        return False
    finally:
        # 注意：不要在这里关闭driver，因为它是线程局部的
        pass


def auto_pacs():
    """主处理函数"""
    print(datetime.now(), "🚀 开始自动PACS处理任务")
    try:
        while True:
            # 获取待处理的报告
            query_sql = "SELECT * FROM nsyy_gyl.medical_reports WHERE is_upload = 0 limit 5"
            records = execute_safe_query(query_sql, None)
            if not records:
                logger.info("✅ 所有报告已处理完成")
                break

            # 处理每个报告
            success_count = 0
            for item in records:
                if process_report_item(item):
                    success_count += 1
            # 短暂休息避免过度频繁查询
            time.sleep(5)
    except Exception as e:
        print(datetime.now(), f"❌ 自动PACS处理任务失败: {e}")
    finally:
        print(datetime.now(), "🛑 自动PACS处理任务结束")
        # 程序结束时清理所有线程的driver
        cleanup_driver()


"""执行查询操作，自动管理连接资源"""


def execute_query(query: str, params):
    connection = None
    try:
        # 创建连接
        connection = pymysql.connect(host=db_config.get("host"), port=3306, user=db_config.get('user'),
                                     password=db_config.get('password'), database='nsyy_gyl')
        with connection.cursor(cursor=DictCursor) as cursor:
            # 执行查询
            if params:
                cursor.execute(query)
            else:
                cursor.execute(query)

            result = cursor.fetchall()
            logging.info(f"查询成功，返回 {len(result)} 条记录")
            return result
    except pymysql.Error as e:
        logging.error(f"MySQL 查询错误: {e}")
        return []

    finally:
        # 确保连接被关闭
        if connection:
            connection.close()
            logging.debug("数据库连接已关闭")


"""带重试机制的查询"""


def execute_safe_query(query: str, params):
    for attempt in range(3):
        try:
            return execute_query(query, params)
        except pymysql.OperationalError as e:
            if attempt == 3 - 1:
                logging.error(f"查询失败，已达到最大重试次数: {e}")
                raise
            logging.warning(f"查询失败，第 {attempt + 1} 次重试: {e}")
            time.sleep(2 ** attempt)  # 指数退避
    return []


if __name__ == "__main__":
    auto_pacs()


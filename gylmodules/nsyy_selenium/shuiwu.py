import logging
import os
import random
import threading
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from playwright.async_api import async_playwright, Page, expect, TimeoutError as PWTimeout
import asyncio

app = Flask(__name__)
CORS(app)

run_in_local = True

logger = logging.getLogger("shuiwu")
logger.setLevel(logging.DEBUG)
# 避免重复添加Handler（防止多次调用时重复日志）
if logger.handlers:
    logger.handlers.clear()

# 控制台Handler
if run_in_local:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
else:
    # 文件Handler（自动轮转）
    file_handler = RotatingFileHandler(filename='shuiwu.log', maxBytes=10 * 1024 * 1024, backupCount=5, delay=False)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # 添加Handler
    logger.addHandler(file_handler)


LOGIN_SESSIONS = {}
SESSION_LOCK = threading.Lock()

QR_TIMEOUT = 50
LOGIN_TIMEOUT = 180
DOWNLOAD_DIR = "./downloads"  # 与你的保存路径一致
URL = "https://etax.henan.chinatax.gov.cn:8443/"
WAIT_STRATEGY = "domcontentloaded"
timeout6 = 60000
timeout9 = 90000
min_wait: float = 0.8
max_wait: float = 2.3


async def playwright_login_worker_async(session_id: str):
    with SESSION_LOCK:
        session = LOGIN_SESSIONS.get(session_id)
        if not session:
            return
        logger.info(f" 登录任务开始: {session_id} {session}")

    try:
        async with async_playwright() as p:
            # browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled", "--start-maximized",])
            # context = await browser.new_context(viewport=None)
            # page = await context.new_page()
            browser = await p.chromium.launch(

                # headless=True,
                # args=[
                #     "--headless=new",  # 新版本Chrome的无头模式
                #     "--disable-blink-features=AutomationControlled",
                #     "--no-sandbox",
                #     "--disable-dev-shm-usage",
                #     "--disable-gpu",
                #     "--disable-web-security",  # 避免跨域问题
                #     "--disable-features=IsolateOrigins,site-per-process",  # 禁用沙箱特性
                #     "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                # ]

                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",  # 有时 GPU 加速反而引起检测
                    "--start-maximized",
                    "--disable-infobars",  # 隐藏“Chrome 正被自动化测试软件控制”提示
                    "--window-size=1920,1080",  # 固定窗口大小，模拟真实用户
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    # 真实 UA
                ]
            )
            context = await browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                # 关闭自动化痕迹
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                # 推荐：模拟真实设备
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                # 关键：禁用 Playwright 的自动化标记
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                }
            )
            # 在新页面创建时注入 JS 隐藏 webdriver
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;     // 清除部分检测
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)

            # 在页面中注入脚本，覆盖navigator.webdriver等属性
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            """)

            with SESSION_LOCK:
                session["status"] = "init"
                session["message"] = "打开登录页"

            await page.goto(URL, timeout=timeout6)
            await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
            logger.info(f" 进入网页 {URL}")

            ####  1️⃣ 处理可能的弹框
            await handle_bullet_box(page)
            await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

            #### 2️⃣  登陆
            async def login(login_page: Page):
                try:
                    login_btn = login_page.get_by_role("button", name="登录").or_(login_page.get_by_role("link", name="登录")
                                                                                  ).or_(login_page.locator("text=登录").locator("visible=true").first)
                    await expect(login_btn).to_be_visible(timeout=timeout6)
                    await expect(login_btn).to_be_enabled(timeout=timeout6)
                    await login_btn.click(delay=120, force=False)  # 不强制点击，更接近人类
                except Exception as e:
                    logger.error(f"点击登录按钮失败: {e}")
                    await login_page.screenshot(path=f"debug_login_fail_{session_id}.png", full_page=True)
                    raise
            await login(page)
            await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
            logger.info(" 找到登陆按钮并已点击登录按钮")

            #### 3️⃣  获取登陆二维码
            qr_img = await page.wait_for_selector("#qrcodeDiv img", timeout=timeout6)
            src = await qr_img.get_attribute("src")
            logger.info(" 获取到登陆二维码，待用户扫码登录")
            if not src or not src.startswith("data:image"):
                logger.warning("⚠️ 未获取到二维码")
                raise RuntimeError("未获取到二维码")

            with SESSION_LOCK:
                session["qrcode"] = src.split(",", 1)[1]
                session["status"] = "waiting"
                session["message"] = "请扫码"

            ####  4️⃣ 等待用户扫码登录
            async def wait_login(login_page: Page):
                start = datetime.now()
                logged_in = False
                while (datetime.now() - start).total_seconds() < 100:
                    current_url = login_page.url
                    logger.info(f" 当前URL: {current_url}")

                    # 条件1: URL 已不是登录页，且包含 logind 或 home/dashboard
                    if "login/" not in current_url.lower() and ("loginb" in current_url.lower() or "home" in current_url.lower()):
                        logged_in = True
                        logger.info(" 登录成功：URL 跳转到非登录页")
                        break

                    # 条件2: 出现首页标题 “我的待办”
                    try:
                        await login_page.wait_for_selector("//div[contains(@class, 'title')]//span[normalize-space(.)='我的待办']", timeout=5000)
                        logged_in = True
                        logger.info(" 登录成功：检测到 '我的待办' 标题")
                        break
                    except:
                        pass

                    # 条件3: “热门服务”
                    try:
                        await login_page.wait_for_selector("//div[contains(@class, 'tit-item')]//span[normalize-space(.)='热门服务']", timeout=5000)
                        logged_in = True
                        logger.info(" 登录成功：检测到 '热门服务'")
                        break
                    except:
                        pass

                    # 条件4: “税务数字账户” 卡片（首页常见入口）
                    try:
                        await login_page.wait_for_selector("//p[normalize-space(.)='发票业务']", timeout=5000)
                        logged_in = True
                        logger.info(" 登录成功：检测到 '发票业务' 入口")
                        break
                    except:
                        pass

                    if logged_in:
                        break

                    logger.info(" 还在等待登录成功...")

                if not logged_in:
                    logger.info(" 扫码登录超时，未检测到首页特征...")
                    await login_page.screenshot(path=f"login_timeout_{session_id}.png")
                    raise TimeoutError("扫码登录超时，未检测到首页特征")
            await wait_login(page)

            logger.info(" 用户登陆成功")
            with SESSION_LOCK:
                session["status"] = "downloading"
                session["message"] = "登录成功, 文件下载中... "

            human_pause = random.uniform(min_wait, max_wait)
            await asyncio.sleep(human_pause)

            # 点击头像获取当前 纳税人名称
            avatar_container = page.locator("#NavTopPopup").first
            await avatar_container.wait_for(state="visible", timeout=timeout6)
            await avatar_container.scroll_into_view_if_needed()
            await avatar_container.click(delay=400)
            await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
            human_pause = random.uniform(min_wait, max_wait)
            await asyncio.sleep(human_pause)

            menu_popup = page.locator(".nav-gr-popup, .t-popup, .grView").first
            await menu_popup.wait_for(state="visible", timeout=timeout6)
            # 假设弹窗已经弹出（menu_popup 或 type_dialog 是弹窗 locator）
            taxpayer_name_span = menu_popup.locator(
                "//div[contains(@class, 'grTitle') and .//span[contains(., '纳税人名称')]]"
                "//span[last()]").first
            taxpayer_name = await taxpayer_name_span.inner_text()
            cur_identity = taxpayer_name.strip()
            logger.info(f"当前纳税人名称: {cur_identity}")
            human_pause = random.uniform(min_wait, max_wait)
            await asyncio.sleep(human_pause)
            await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

            while True:
                # 如果当前纳税人身份已经下载过，则切换
                if cur_identity in session.get('identity', []):
                    identity_name = await switch_identity(page, session.get('identity', []))
                    if not identity_name:
                        logger.info(" 所有纳税人已下载完毕")
                        break
                    cur_identity = identity_name
                await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                logger.info(" 准备进入发票业务")
                ####  5️⃣ 进入发票业务（新 tab）
                async def into_tax_page(tax_page: Page):
                    try:
                        async with tax_page.expect_popup(timeout=timeout6) as popup_info:
                            tax_link = tax_page.locator("a:has(p[title='发票业务'])").first
                            await tax_link.scroll_into_view_if_needed()
                            await tax_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                            await tax_link.wait_for(state="visible", timeout=timeout6)
                            await tax_link.click(delay=400)
                            logger.info(" 已点击 '发票业务' 链接，等待新 tab")
                            await tax_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        new_page = await popup_info.value
                        logger.info(" 已捕获新 tab：发票业务 页面")
                    except Exception as e:
                        logger.error(f"进入发票业务页面异常 {e}")
                        new_page = tax_page

                    return new_page

                invoice_page = await into_tax_page(page)
                await invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                #### 6️⃣ 进入发票查询页面（SPA）   全量发票查询（SPA） - 类似优化
                async def query_stat(query_invoice_page: Page):
                    try:
                        # 关键：先滚动到元素可见
                        await query_invoice_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await query_invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                        logger.info(" 已强制滚动到发票查询页面底部")
                        human_pause = random.uniform(min_wait, max_wait)
                        await asyncio.sleep(human_pause)

                        # 或直接找 .page_app_item 内包含文本的
                        stat_item = query_invoice_page.locator(".page_app_item").filter(has_text="发票查询统计").first
                        await stat_item.wait_for(state="visible", timeout=timeout6)
                        await stat_item.scroll_into_view_if_needed()
                        await stat_item.click(delay=400)
                        await query_invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                        logger.info(" 已点击 '发票查询统计'")
                    except PWTimeout as te:
                        logger.error(f" 进入发票查询统计超时: {str(te)}")
                        await query_invoice_page.screenshot(path=f"query_stat_timeout.png")
                    except Exception as e:
                        logger.error(f" 发票查询统计异常: {str(e)}")
                        await query_invoice_page.screenshot(path=f"query_stat_error.png")

                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    #### 全量发票查询（SPA）
                    try:
                        full_query_item = query_invoice_page.locator(".g-card-menu-item__content").filter(has_text="全量发票查询").first
                        # 先检查元素是否存在
                        count = await full_query_item.count()
                        logger.info(f" 找到 {count} 个匹配 '全量发票查询' 的 .page_app_item")
                        if count == 0:
                            logger.warning(" 没有找到卡片，打印页面文本检查")
                            raise RuntimeError("未找到 '全量发票查询' 卡片")
                            # 等待元素 attached（存在于 DOM）
                        await full_query_item.wait_for(state="attached", timeout=timeout6)
                        await full_query_item.wait_for(state="visible", timeout=timeout6)
                        await query_invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        await full_query_item.scroll_into_view_if_needed()
                        await full_query_item.click(delay=400)
                        logger.info(" 已点击 '全量发票查询' 入口")

                    except PWTimeout as te:
                        logger.error(f" 进入全量发票查询超时: {str(te)}")
                        await query_invoice_page.screenshot(path=f"full_query_timeout.png")
                    except Exception as e:
                        logger.error(f" 全量发票查询异常: {str(e)}")
                        await query_invoice_page.screenshot(path=f"full_query_error.png")

                await query_stat(invoice_page)
                await invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                #### 8️⃣ 准备下载发票 开具发票/取得发票
                async def download_invoice(download_page: Page, query_type: str, identity: str):
                    # 选择 查询类型  开具发票/取得发票
                    await select_query_type(download_page, query_type)
                    await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                    # 先尝试关闭任何残留日历面板（关键！）
                    try:
                        old_panel = download_page.locator(
                            ".t-date-picker__panel:visible, .t-popup.t-date-picker__panel-container:visible").first
                        if await old_panel.count() > 0:
                            await download_page.mouse.click(10, 10)  # 点空白关闭
                            await old_panel.wait_for(state="hidden", timeout=5000)
                    except Exception as e:
                        logger.error(f"关闭任何残留日历面板遇到异常 {e}")
                        pass

                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    logger.info(f"查询日期为 {session['startDate']}    {session['endDate']} ")
                    # 第一个日期：正常点击输入框打开面板
                    await pick_date_async(download_page, "开票日期（起）", datetime.strptime(session['startDate'], "%Y-%m-%d"))
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    await pick_date_async(download_page, "开票日期（止）", datetime.strptime(session['endDate'], "%Y-%m-%d"))
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)
                    logger.info(" 两个日期已填写完成")

                    # 查询按钮（宽松匹配）
                    query_btn = download_page.locator("//button[contains(., '查询') or .//span[contains(., '查询')]]").first
                    await query_btn.wait_for(state="visible", timeout=timeout6)
                    await query_btn.scroll_into_view_if_needed()
                    await query_btn.click(delay=500)
                    logger.info(" 已点击 '查询' 按钮")
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    # 等待表格数据行
                    await download_page.wait_for_selector("//table//tr[position()>1]", timeout=timeout6)
                    logger.info(" 查询成功，表格出现")
                    # 检查结果（可选）
                    rows = await download_page.locator("//table//tr[position()>1]").count()
                    await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                    logger.info(f" 查询结果行数: {rows}")
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    # 在查询成功、表格出现之后执行导出全部
                    logger.info(" 准备导出全部数据")
                    # 定位“导出”按钮
                    export_btn = download_page.locator("//button[contains(., '导出') or .//span[contains(., '导出')]]").first
                    await export_btn.wait_for(state="visible", timeout=timeout6)
                    await export_btn.scroll_into_view_if_needed()
                    await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                    logger.info(" 已定位到 '导出' 按钮")

                    # 监听下载（提前设置）
                    async with download_page.expect_download(timeout=timeout9) as download_info:
                        # 点击“导出”按钮，弹出菜单
                        await export_btn.click(delay=400)
                        logger.info(" 已点击 '导出' 按钮，等待下拉菜单")

                        # 关键：定位当前弹出的菜单容器（用 .t-dropdown__menu + 包含选项文本）
                        dropdown_menu1 = download_page.locator(".t-dropdown__menu").filter(has_text="导出全部").first
                        if await dropdown_menu1.count() == 0:
                            dropdown_menu1 = download_page.locator(".t-popup__content.t-dropdown").filter(has_text="导出全部").first
                        await dropdown_menu1.wait_for(state="visible", timeout=timeout6)
                        logger.info(" 下拉菜单已弹出（已定位到菜单容器）")

                        # 点击“导出全部”选项（精确匹配 li 中的 span）
                        export_all_option = dropdown_menu1.locator(".t-dropdown__item-text:has-text('导出全部')").first.or_(
                            dropdown_menu1.locator("//span[normalize-space(.)='导出全部']").first)
                        await export_all_option.wait_for(state="visible", timeout=timeout6)
                        await export_all_option.click(delay=300)
                        logger.info(" 已点击 '导出全部' 选项")

                    # 保存下载文件
                    download = await download_info.value
                    suggested_filename = f"{identity}-{query_type}_{session['startDate']}-{session['endDate']}-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    logger.info(f" 浏览器开始下载文件 {suggested_filename}")
                    save_path = f"./downloads/{suggested_filename}"
                    os.makedirs("./downloads", exist_ok=True)

                    await download.save_as(save_path)
                    logger.info(f" 文件已保存到: {save_path}")
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)

                    # 提交对应pdf发票下载申请
                    try:
                        # 1. 全选表格数据（勾选表头全选 checkbox）
                        try:
                            select_all_checkbox = download_page.locator(
                                "//th[contains(@class, 't-table__cell-check')]"
                                "//input[@type='checkbox']").first
                            await select_all_checkbox.wait_for(state="attached", timeout=timeout6)
                            logger.info(" 已定位到表头全选 checkbox")

                            # 先滚动到表头位置（fixed-left 列可能需要）
                            await download_page.evaluate("window.scrollTo(0, 0)")  # 滚动到顶部
                            await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                            # 强制滚动 checkbox 可见（即使 fixed）
                            await select_all_checkbox.scroll_into_view_if_needed()
                            # 检查当前状态
                            is_checked = await select_all_checkbox.is_checked()
                            logger.info(f" 全选 checkbox 当前状态: {'已勾选' if is_checked else '未勾选'}")

                            if not is_checked:
                                checkbox_label = select_all_checkbox.locator(
                                    "xpath=ancestor::label[contains(@class, 't-checkbox')]").first
                                if await checkbox_label.count() > 0:
                                    await checkbox_label.click(delay=300)
                                    logger.info(" 已点击全选 label")
                                else:
                                    # 直接点击 input
                                    await select_all_checkbox.check()  # 用 check() 方法勾选
                                    logger.info(" 已用 check() 方法勾选全选框")

                                # 再次检查状态（防失败）
                                await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                                is_checked_after = await select_all_checkbox.is_checked()
                                if is_checked_after:
                                    logger.info(" 全选 checkbox 已成功勾选")
                                else:
                                    # 强制 dispatch change 事件
                                    await select_all_checkbox.evaluate("""
                                                                el => {
                                                                    el.checked = true;
                                                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                                                    el.dispatchEvent(new Event('input', {bubbles: true}));
                                                                }
                                                            """)
                                    logger.info(" 已强制 dispatch change 事件勾选全选")

                            else:
                                logger.info(" 全选 checkbox 已默认勾选，无需操作")
                        except Exception as e:
                            logger.error(f" 全选失败: {str(e)}")
                            await download_page.screenshot(
                                path=f"select_all_fail_{int(datetime.now().timestamp())}.png")
                            raise

                        # 2. 点击“下载”按钮，弹出下拉菜单
                        download_btn = download_page.locator("//button[contains(., '下载') or .//span[contains(., '下载')]]").first
                        await download_btn.wait_for(state="visible", timeout=timeout6)
                        await download_btn.scroll_into_view_if_needed()
                        await download_btn.click(delay=400)
                        logger.info(" 已点击 '下载' 按钮，等待下拉菜单")

                        # 等待下拉菜单（用包含“下载选中”的文本过滤，确保唯一）
                        download_menu = download_page.locator(".t-dropdown__menu").filter(has_text="下载选中").first
                        await download_menu.wait_for(state="visible", timeout=timeout6)
                        logger.info(" 下载下拉菜单已弹出")

                        # 点击“下载选中”
                        download_selected_option = download_menu.locator(".t-dropdown__item-text:has-text('下载选中')"
                                                                         ).first.or_(
                            download_menu.locator("//span[normalize-space(.)='下载选中']").first)
                        await download_selected_option.wait_for(state="visible", timeout=timeout6)
                        await download_selected_option.click(delay=300)
                        logger.info(" 已选择 '下载选中'")

                        # 3. 等待“文件下载类型”弹窗出现
                        download_type_dialog = download_page.locator(
                            "//div[contains(@class, 't-dialog') or contains(@class, 't-popup')][contains(., '文件下载类型')]"
                        ).first
                        await download_type_dialog.wait_for(state="visible", timeout=timeout6)
                        logger.info(" 文件下载类型弹窗已弹出")

                        # 4. 选中 “PDF文件” checkbox
                        # 选中 PDF 文件（点 label，而不是 input）
                        pdf_label = download_type_dialog.locator(
                            "//label[contains(@class,'t-checkbox') and .//span[normalize-space()='PDF文件']]").first
                        await pdf_label.wait_for(state="visible", timeout=timeout6)
                        await pdf_label.scroll_into_view_if_needed()

                        checkbox_input = pdf_label.locator("input[type='checkbox']").first
                        is_checked = await checkbox_input.is_checked()
                        if is_checked:
                            logger.info(" 'PDF文件' 已处于勾选状态，无需再次点击")
                        else:
                            await pdf_label.click(delay=200)
                            logger.info(" 已点击勾选 'PDF文件'")

                        # 等待确认按钮解锁
                        confirm_btn = download_type_dialog.locator("//button[.//span[normalize-space()='确认']]").first
                        await expect(confirm_btn).to_be_enabled(timeout=timeout6)
                        await confirm_btn.click(delay=200)
                        logger.info(" 已点击 '确认' 开始下载 PDF")
                        await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        # 处理弹框
                        await handle_bullet_box(download_page)
                        await download_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                    except Exception as e:
                        logger.error(f" pdf 发票申请提交失败 {e}")

                try:
                    await download_invoice(invoice_page, "开具发票", cur_identity)
                    await invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                except Exception as e:
                    logger.error(f" 开具发票失败 {e}")

                human_pause = random.uniform(min_wait, max_wait)
                await asyncio.sleep(human_pause)

                try:
                    await download_invoice(invoice_page, "取得发票", cur_identity)
                    await invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                except Exception as e:
                    logger.error(f" 开具发票失败 {e}")

                human_pause = random.uniform(min_wait, max_wait)
                await asyncio.sleep(human_pause)

                #### 9️⃣ 下载发票pdf
                async def download_pdf_invoice(download_pdf_page: Page, identity: str):
                    try:
                        logger.info(" 查询成功，开始导出 PDF 下载流程")
                        logger.info(" 返回上一页 去下载pdf发票")
                        # 定位返回箭头 SVG
                        back_arrow = download_pdf_page.locator(".t-icon.t-icon-arrow-left").first
                        await back_arrow.wait_for(state="attached", timeout=timeout6)  # 只等存在
                        logger.info(" 已定位到返回箭头 SVG")

                        # 滚动到顶部（fixed header 常见）
                        await download_pdf_page.evaluate("window.scrollTo(0, 0)")
                        await download_pdf_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        # 尝试滚动到图标
                        try:
                            await back_arrow.scroll_into_view_if_needed(timeout=timeout6)
                            logger.info(" 已滚动到返回箭头位置")
                        except:
                            logger.warning(" 滚动失败，继续强制点击")

                        # 强制点击 SVG
                        await back_arrow.click(force=True, delay=400)
                        logger.info(" 已点击返回箭头 SVG")

                        # 3. 等待页面返回完成（加载上一页）
                        await download_pdf_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                        logger.info(" 返回上一页验证完成，页面稳定")

                        full_query_item = download_pdf_page.locator(".g-card-menu-item__content").filter(
                            has_text="批量导入导出进度查询").first
                        # 先检查元素是否存在
                        count = await full_query_item.count()
                        logger.info(f" 找到 {count} 个匹配 '批量导入导出进度查询' 的 .page_app_item")
                        if count == 0:
                            logger.info(" 没有找到卡片，打印页面文本检查")
                            await download_pdf_page.screenshot(
                                path=f"no_card_{int(datetime.now().timestamp())}.png")
                            raise RuntimeError("未找到 '批量导入导出进度查询' 卡片")
                            # 等待元素 attached（存在于 DOM）
                        await full_query_item.wait_for(state="attached", timeout=timeout6)
                        await full_query_item.wait_for(state="visible", timeout=timeout6)

                        await full_query_item.scroll_into_view_if_needed()
                        await full_query_item.click(delay=400)
                        logger.info(" 已点击 '批量导入导出进度查询' 入口")

                        query_btn = download_pdf_page.locator(
                            "//button[contains(., '查询') or .//span[contains(., '查询')]]").first
                        await query_btn.wait_for(state="visible", timeout=timeout6)
                        await query_btn.scroll_into_view_if_needed()
                        await query_btn.click(delay=500)
                        logger.info(" 已点击 '查询' 按钮")

                        await download_pdf_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        # 1. 只等任意 tbody tr 存在（attached）
                        await download_pdf_page.wait_for_selector("tbody tr", state="attached", timeout=timeout9)

                        # 2. 打印 tr 数量确认
                        tr_count = await download_pdf_page.evaluate("document.querySelectorAll('tbody tr').length")
                        logger.info(f" 当前 tbody tr 数量: {tr_count}")

                        # 获取前两行
                        rows = (await download_pdf_page.locator("tbody tr").all())[:2]  # 只取前两行
                        if not rows:
                            logger.info(" 没有找到任何数据行")
                            return
                        for index, row in enumerate(rows, 1):
                            logger.info(f" 检查第 {index} 行")
                            # 定位该行最后一列的操作区域
                            op_cell = row.locator("td:last-child").first

                            # 尝试定位 “下载” 按钮（两种方式）
                            download_span = op_cell.locator("span.operate:has-text('下载')"
                            ).first.or_(op_cell.locator("span.operate")).first

                            # 判断是否是下载按钮
                            if await download_span.count() > 0:
                                btn_text = await download_span.inner_text()
                                btn_text = btn_text.strip()

                                if "下载" in btn_text:
                                    logger.info(f" 第 {index} 行找到下载按钮: {btn_text}")

                                    # 强制点击
                                    await download_span.click(force=True, delay=400)
                                    logger.info(f" 已点击第 {index} 行的 '下载' 按钮")

                                    # 监听下载（只监听一次，如果需要下载多个，可循环）
                                    async with download_pdf_page.expect_download(timeout=timeout6) as download_info:
                                        pass  # 点击已触发

                                    download = await download_info.value
                                    save_path = f"./downloads/{identity}_{session['startDate']}-{session['endDate']}-{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
                                    os.makedirs("./downloads", exist_ok=True)
                                    await download.save_as(save_path)
                                    logger.info(f" 第 {index} 行文件保存到: {save_path}")
                                else:
                                    logger.info(f" 第 {index} 行操作按钮不是下载: {btn_text}")
                            else:
                                logger.info(f" 第 {index} 行没有找到 '下载' 按钮")

                        await download_pdf_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

                        # # 3. 定位第一行最后一列的 span.operate 或包含“下载”的 span
                        # download_btn = download_pdf_page.locator("tbody tr:first-child td:last-child span.operate"
                        # ).first.or_(download_pdf_page.locator(
                        #         "tbody tr:first-child td:last-child span:has-text('下载')").first)
                        #
                        # # 只等 attached
                        # await download_btn.wait_for(state="attached", timeout=65000)
                        #
                        # # 4. 强制点击
                        # await download_btn.click(force=True, delay=400)
                        # logger.info(" 第一行 '下载' 按钮已 attached 点击第一行 '下载' 按钮")
                        #
                        # # 5. 监听下载
                        # async with download_pdf_page.expect_download(timeout=60000) as download_info:
                        #     logger.info(" 等待下载开始...")
                        #
                        # download = await download_info.value
                        # download_file_name = f"{identity}_{session['startDate']}-{session['endDate']}-{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
                        # save_path = f"./downloads/{download_file_name}"
                        # os.makedirs("./downloads", exist_ok=True)
                        # await download.save_as(save_path)
                        # logger.info(f" 文件保存到: {save_path}")

                        with SESSION_LOCK:
                            session["status"] = "success"
                            session["message"] = "文件下载成功"

                    except PWTimeout as te:
                        logger.error(f" 下载流程超时: {str(te)}")
                        await download_pdf_page.screenshot(path=f"download_timeout_{int(datetime.now().timestamp())}.png")

                        with SESSION_LOCK:
                            session["status"] = "fail"
                            session["message"] = "文件下载超时"
                    except Exception as e:
                        logger.error(f" 下载流程异常: {str(e)}")
                        await download_pdf_page.screenshot(path=f"download_error_{int(datetime.now().timestamp())}.png")
                        with SESSION_LOCK:
                            session["status"] = "fail"
                            session["message"] = "文件下载异常"
                await download_pdf_invoice(invoice_page, cur_identity)

                await invoice_page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
                logger.info(f" {cur_identity} 处理完成")
                with SESSION_LOCK:
                    session["identity"].append(cur_identity)

                # 2. 关闭 invoice_page 页面
                await invoice_page.close()
                logger.info(" 当前身份处理完成，关闭发票查询页面，切换回主页面")

                # 3. 切回原来的 page（主页面）
                await page.bring_to_front()
                logger.info(" 已切回主页面 page")
                await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

    except PWTimeout:
        with SESSION_LOCK:
            session["status"] = "failed"
            session["message"] = "页面操作超时"
        logger.error("❌ 页面操作超时")
    except asyncio.CancelledError as e:
        logger.error(f"❌ 协程被取消: {e}")
        raise
    except Exception as e:
        with SESSION_LOCK:
            session["status"] = "failed"
            session["message"] = str(e)
        logger.error(f"❌ 遇到异常: {e}")


"""身份切换 切换到还没处理过的身份 """

async def switch_identity(page: Page, identitys: list):
    # 登录成功后，右上角头像菜单 + 身份切换
    identity_name = ''
    try:
        logger.info(f" 准备开始身份切换")

        # 1. 定位头像区域（id="NavTopPopup" 最可靠）
        avatar_container = page.locator("#NavTopPopup").first
        await avatar_container.wait_for(state="visible", timeout=timeout6)
        await avatar_container.scroll_into_view_if_needed()
        # 2. 点击头像，弹出菜单
        await avatar_container.click(delay=400)
        logger.info(" 已点击头像，等待菜单弹出")

        # 加缓冲，确保选中状态生效
        await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

        # 3. 定位菜单（用 class 或文本过滤）
        menu_popup = page.locator(".nav-gr-popup, .t-popup, .grView").filter(has_text="身份切换").first
        await menu_popup.wait_for(state="visible", timeout=timeout6)

        # 4. 点击“身份切换”按钮（精确匹配 span.grBtnTitle）
        switch_identity_btn = menu_popup.locator(".grBtnTitle:has-text('身份切换')").first.or_(
            menu_popup.locator("//span[contains(@class, 'grBtnTitle') and normalize-space(.)='身份切换']").first)
        await switch_identity_btn.wait_for(state="visible", timeout=timeout6)
        await switch_identity_btn.scroll_into_view_if_needed()
        await switch_identity_btn.click(delay=300)
        logger.info(" 已点击 '身份切换' 按钮")

        await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
        logger.info(" 已进入身份切换页面，开始查找并切换身份")

        # 等待身份列表表格出现
        await page.wait_for_selector("//table//tr[position()>1]", timeout=timeout9)  # 数据行
        logger.info(" 身份列表表格已加载")

        await page.wait_for_selector(".el-table__body-wrapper table.el-table__body tbody tr", timeout=timeout6)
        # 2. 获取所有数据行（tbody 中的 tr）
        data_rows = await page.locator(".el-table__body-wrapper table.el-table__body tbody tr").all()

        if len(data_rows) == 0:
            logger.warning(" 无数据行（可能无身份或加载失败）")
            await page.screenshot(path=f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}-no_identity_rows.png")
        else:
            logger.info(f" 找到 {len(data_rows)} 行身份数据")
            # 3. 遍历每行，打印或处理
            for i, row in enumerate(data_rows, 1):
                cells = await row.locator("td").all_inner_texts()
                cleaned_cells = [cell.strip() for cell in cells if cell.strip()]
                if cleaned_cells[2] in identitys:
                    logger.info(f" {cleaned_cells[2]} 已处理， 跳过")
                    continue

                identity_name = cleaned_cells[2]
                # 4. 如果想点击某行的“切换”按钮
                switch_btn = row.locator("td:last-child button, td:last-child a, td:last-child [class*='switch']").first
                if await switch_btn.count() > 0:
                    logger.info(f" 已点击目标身份 {cleaned_cells[2]} 的切换按钮")
                    await switch_btn.click(delay=300)
                    break
        if not identity_name:
            logger.warning(" 未找到目标身份(有可能已经处理完了)")
            return identity_name

        # 4. 等待切换完成（页面刷新或提示）
        await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)
        # 1. 等待“身份切换”确认弹窗出现（警告：数据丢失）
        confirm_dialog = page.locator(
            "//div[contains(@class, 'el-message-box') or contains(@class, 'el-dialog')]"
            "[contains(., '身份切换') or contains(., '未保存数据丢失')]").first

        await confirm_dialog.wait_for(state="visible", timeout=timeout6)
        logger.info(" 身份切换确认弹窗已弹出")

        # 点击“确定”
        confirm_btn = confirm_dialog.locator("//button[contains(., '确定') or contains(., '确认')]").first
        await confirm_btn.wait_for(state="visible", timeout=timeout6)
        await confirm_btn.click(delay=300)
        logger.info(" 已点击确认弹窗的 '确定'")
        await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

        # 2. 等待“身份类型选择”弹窗出现
        type_dialog = page.locator(
            "//div[contains(@class, 'el-dialog') or contains(@class, 'el-message-box')]"
            "[contains(., '身份类型选择') or contains(., '办税员')]").first

        await type_dialog.wait_for(state="visible", timeout=timeout6)
        logger.info(" 身份类型选择弹窗已弹出")

        # 3. 选中“办税员”单选按钮
        tax_staff_radio = type_dialog.locator("//label[contains(., '办税员')]").first
        await tax_staff_radio.wait_for(state="visible", timeout=timeout6)
        await tax_staff_radio.scroll_into_view_if_needed()
        # 检查当前状态
        is_checked = await tax_staff_radio.locator("input[type='radio']").is_checked()
        if not is_checked:
            await tax_staff_radio.check()
            logger.info(" 已选中 '办税员'")
        else:
            logger.info(" '办税员' 已默认选中")

        await page.wait_for_load_state(WAIT_STRATEGY, timeout=timeout6)

        # 4. 点击弹窗的“确定”按钮（更宽松匹配）
        confirm_type_btn = type_dialog.locator(
            "//button[contains(translate(., '  ', ''), '确定') or contains(translate(., '  ', ''), '确认')]"
            "[contains(@class, 'el-button')]").first
        confirm_type_btn = type_dialog.get_by_role("button", name="确 定").first.or_(
            type_dialog.get_by_role("button", name="确定").first)
        await confirm_type_btn.wait_for(state="visible", timeout=timeout6)
        await confirm_type_btn.scroll_into_view_if_needed()
        await confirm_type_btn.click(delay=400)
        logger.info(" 已点击身份类型选择的 '确定' 按钮")

        # 5. 等待弹窗关闭 + 切换完成
        await type_dialog.wait_for(state="hidden", timeout=timeout6)
        logger.info(" 身份类型选择弹窗已关闭")
        logger.info(f" {identity_name} 身份切换完成，页面稳定")

        return identity_name
    except PWTimeout as te:
        logger.error(f" 身份切换超时: {str(te)}")
        await page.screenshot(path=f"identity_switch_timeout-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
        raise
    except Exception as e:
        logger.error(f" 身份切换异常: {str(e)}")
        await page.screenshot(path=f"identity_switch_error-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
        raise


"""处理页面中出现的弹框"""

async def handle_bullet_box(page: Page):
    try:
        # 更宽松地找所有可能的确认按钮，优先级从左到右
        possible_btn_texts = ["我知道了", "我已阅读", "继续访问", "确认", "同意", "关闭", "知道了"]
        for text in possible_btn_texts:
            btn = page.get_by_text(text, exact=False).first  # 放宽 exact=False 更稳
            try:
                if await btn.is_visible(timeout=6000):
                    logger.info(f" 找到弹窗按钮: {text} 并点击")
                    await btn.click(delay=150)  # 加一点模拟人类延迟
                    human_pause = random.uniform(min_wait, max_wait)
                    await asyncio.sleep(human_pause)
                    break
            except:
                continue

        # 额外等待，确保遮罩层消失（很多网站用 .mask / .dialog / .modal）
        await page.wait_for_function(
            """() => {
                const masks = document.querySelectorAll('.mask, .dialog, .modal, [role="dialog"]');
                return Array.from(masks).every(el => 
                    window.getComputedStyle(el).display === 'none' || 
                    el.offsetParent === null
                );
            }""", timeout=timeout6)
    except Exception as e:
        logger.error(f"处理弹窗时出错，但继续执行: {e}")
        raise


"""输入日期"""

async def pick_date_async(page: Page, label_text: str, target_date: datetime):
    try:
        logger.info(f" 开始选择日期 {label_text}: {target_date.strftime('%Y-%m-%d')}")

        # 直接进入点击日历逻辑（当前站点 force fill 无效）
        await fallback_click_calendar(page, label_text, target_date)

        # 可选：选完后验证 input 值（调试用）
        input_box = page.locator(
            f"//label[normalize-space(.)='{label_text}']/ancestor::div[contains(@class,'t-form__item')]//input"
        ).first
        final_value = await input_box.input_value()
        logger.info(f" 选择后输入框显示值: {final_value}")

    except Exception as e:
        logger.error(f" 日期选择异常 ({label_text}): {str(e)}")
        try:
            await page.screenshot(path=f"date_error_{label_text.replace(' ','_')}_{int(datetime.now().timestamp())}.png")
        except:
            pass
        raise


async def fallback_click_calendar(page: Page, label_text: str, target_date: datetime):
    day_str = str(target_date.day)

    input_box = page.locator(
        f"//label[normalize-space(.)='{label_text}']"
        f"/ancestor::div[contains(@class,'t-form__item')]//input"
    ).first

    logger.info(f"点击输入框打开面板: {label_text}")

    # ⭐ 关键 1：先点空白，确保前一个面板彻底关闭
    await page.mouse.click(10, 10)
    human_pause = random.uniform(min_wait, max_wait)
    await asyncio.sleep(human_pause)


    # ⭐ 关键 2：用“慢一点的 click”
    # await input_box.click(delay=600)
    await open_date_panel_like_human(page, input_box)

    panel = page.locator(".t-date-picker__panel:visible, .t-popup.t-date-picker__panel-container:visible").last
    await panel.wait_for(state="visible", timeout=timeout6)
    logger.info("面板打开成功（已锁定当前 panel）")

    # ⭐ 等日历格子渲染完成
    await panel.locator(".t-date-picker__cell-inner").first.wait_for(state="visible", timeout=timeout6)

    # 翻月 + 找日
    for _ in range(60):
        day_cell = panel.locator(
            f"xpath=.//td[not(contains(@class, 'additional')) "
            f"and not(contains(@class, 'disabled'))]"
            f"//div[contains(@class, 't-date-picker__cell-inner') "
            f"and normalize-space(text())='{day_str}']").first

        if await day_cell.count() > 0:
            await day_cell.first.click(delay=500)
            break

        await panel.locator(".t-pagination-mini__next").first.click(delay=500)
        human_pause = random.uniform(min_wait, max_wait)
        await asyncio.sleep(human_pause)

    # ⭐ 等面板真正关闭（模拟人）
    await panel.wait_for(state="hidden", timeout=timeout6)
    logger.info(f"{label_text} 日期选择完成")


async def open_date_panel_like_human(page: Page, input_box):
    # 1️⃣ 先点页面空白，彻底失焦
    await page.mouse.click(5, 5)
    human_pause = random.uniform(min_wait, max_wait)
    await asyncio.sleep(human_pause)

    # 2️⃣ 模拟鼠标移动到 input
    box = await input_box.bounding_box()
    if box:
        await page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
            steps=10
        )
        human_pause = random.uniform(min_wait, max_wait)
        await asyncio.sleep(human_pause)

    # 3️⃣ 再 click（慢）
    await input_box.click(delay=800)

    # 4️⃣ 再补一次 focus（非常关键）
    await input_box.focus()


"""选择【查询方式】，例如：'税（费）属期'"""

async def select_query_type(page: Page, option_text: str):
    logger.info(f" 开始选择查询类型: {option_text}")

    try:
        # 1. 输入框定位
        input_box = page.locator(
            "//label[normalize-space(.)='查询类型']"
            "/ancestor::div[contains(@class,'t-form__item')]"
            "//input"
        ).first

        await input_box.wait_for(state="visible", timeout=timeout6)
        logger.info(" 找到查询类型输入框")

        # 2. 点击后缀箭头（更可靠）
        suffix_icon = input_box.locator("xpath=ancestor::div[contains(@class, 't-input')]//span[contains(@class, 't-input__suffix')]").first
        if await suffix_icon.count() > 0:
            await suffix_icon.click(delay=300)
        else:
            await input_box.click(delay=500)

        # 3. 下拉浮层（用 filter(has_text) 唯一匹配）
        dropdown = page.locator(
            ".t-select__dropdown, .t-popup__content, .t-popup--content, [class*='select__dropdown'], [class*='popup__content']"
        ).filter(
            has_text=option_text  # 关键：必须包含目标选项文本
        ).last

        await dropdown.wait_for(state="visible", timeout=timeout6)
        logger.info(" 下拉浮层已弹出")

        # 4. 选项点击
        option = dropdown.locator(f"//*[normalize-space(.)='{option_text}']").first

        await option.wait_for(state="visible", timeout=timeout6)
        await option.click(delay=200)
        logger.info(f" 已点击选项 '{option_text}'")

        # 5. 等关闭
        await dropdown.wait_for(state="hidden", timeout=timeout6)
        logger.info(" 下拉关闭，选择完成")

    except PWTimeout as te:
        logger.error(f" 选择查询类型超时: {str(te)}")
        await page.screenshot(path=f"select_type_timeout_{int(datetime.now().timestamp())}.png")
        raise
    except Exception as e:
        logger.error(f" 选择查询类型异常: {str(e)}")
        await page.screenshot(path=f"select_type_error_{int(datetime.now().timestamp())}.png")
        raise

def playwright_thread_entry(session_id: str):
    asyncio.run(playwright_login_worker_async(session_id))


# ---------- API ----------

@app.route("/api/login/start", methods=["POST"])
def start_login():
    session_id = uuid.uuid4().hex
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")


    with SESSION_LOCK:
        LOGIN_SESSIONS[session_id] = {
            "status": "init",
            "message": "初始化中",
            "qrcode": "",
            "start_time": time.time(),
            "startDate": start_date,
            "endDate": end_date,
            'identity': []
        }
        logger.info(f"启动会话: {session_id} {LOGIN_SESSIONS[session_id]}")

    t = threading.Thread(
        target=playwright_thread_entry,
        args=(session_id,),
        daemon=True
    )
    t.start()

    return jsonify({"session_id": session_id})


@app.route("/api/login/qrcode")
def get_qrcode():
    session_id = request.args.get("session_id")

    with SESSION_LOCK:
        s = LOGIN_SESSIONS.get(session_id)
        if not s:
            return jsonify({"qrcode": ""})

        if time.time() - s["start_time"] > QR_TIMEOUT and not s["qrcode"]:
            s["status"] = "expired"
            s["message"] = "二维码超时"

        return jsonify({"qrcode": s["qrcode"]})


@app.route("/api/login/status")
def get_status():
    session_id = request.args.get("session_id")

    with SESSION_LOCK:
        s = LOGIN_SESSIONS.get(session_id)
        if not s:
            return jsonify({"status": "invalid", "message": "无效会话"})

        return jsonify({
            "status": s["status"],
            "message": s["message"]
        })

# 获取下载列表
@app.route('/api/download_list', methods=['GET'])
def download_list():
    files = []
    if os.path.exists(DOWNLOAD_DIR):
        for filename in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(filepath):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "size_str": f"{os.path.getsize(filepath) / 1024 / 1024:.2f} MB",
                    "modified_time": datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S"),
                    "url": f"/api/download_file/{filename}"
                })

    # 按修改时间倒序（最新下载的在最上面）
    files.sort(key=lambda x: x["modified_time"], reverse=True)

    return jsonify({
        "status": "success",
        "files": files
    })

# 下载单个文件
@app.route('/api/download_file/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
















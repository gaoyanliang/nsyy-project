import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import httpx

# =============================== iOS 推送（同步实现） ===============================

APNS_CLIENT = None
APNS_CLIENT_LOCK = threading.Lock()

def get_apns_client() -> httpx.Client:
    global APNS_CLIENT
    with APNS_CLIENT_LOCK:
        if APNS_CLIENT is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            pem_path = os.path.join(script_dir, "ck_nopass.pem")

            APNS_CLIENT = httpx.Client(
                http2=True,
                cert=pem_path,
                timeout=httpx.Timeout(10.0, connect=5.0),
                verify=True,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            )
        return APNS_CLIENT


def close_apns_client():
    """关闭客户端（程序退出或需要强制重连时调用）"""
    global APNS_CLIENT
    with APNS_CLIENT_LOCK:
        if APNS_CLIENT is not None:
            try:
                APNS_CLIENT.close()
            except Exception:
                pass
            APNS_CLIENT = None



def _send_single_apns(client: httpx.Client, token: str, title: str, body: str, sound: str) -> tuple[str, str]:
    """发送单条推送，返回 (token, status)。status == 'Success' 表示成功。"""
    # 默认使用 api.push.apple.com ，如果是本次测试通过电脑安装的 需要 api.sandbox.push.apple.com
    # url = f"https://api.sandbox.push.apple.com/3/device/{token}"
    url = f"https://api.push.apple.com/3/device/{token}"
    payload = {
        "aps": {
            "alert": {"title": title, "body": body},
            "sound": sound,          # "default" 或 "alert.wav"
            "badge": 1,
            "category": "MY_CATEGORY",
            "custom": {"type": "chat"},
        }
    }
    headers = {
        # 使用证书认证时 apns-topic 可省略；若你的 ck.pem 是多 App 共用，
        # 建议显式指定以防万一：
        "apns-topic": "com.nsyy.Nsyy",
        "apns-priority": "10",
        "apns-push-type": "alert",
        "apns-expiration": "0",
    }
    try:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return token, "Success"
        # APNs 错误响应体是 JSON，含 reason 字段，如 BadDeviceToken / Unregistered
        try:
            reason = resp.json().get("reason", f"HTTP_{resp.status_code}")
        except Exception:
            reason = f"HTTP_{resp.status_code}"
        return token, reason
    except Exception as e:
        return token, f"Exception:{type(e).__name__}"


def send_apns_batch(tokens, title, body, sound: str = "default"):
    """同步批量发送 APNs 推送"""
    if not tokens:
        return []

    start_time = time.time()
    client = get_apns_client()
    failed_tokens = []

    # 用线程池并发发送，兼顾速度与连接复用
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(_send_single_apns, client, token, title, body, sound)
            for token in tokens
        ]
        for future in futures:
            token, status = future.result()
            if status != "Success":
                failed_tokens.append(token)
                if status == "BadDeviceToken" or status == "Unregistered":
                    print(f"可清理无效 token: {token[:16]}... ({status})")
                else:
                    print(f"APNs 推送失败 token={token[:16]}... reason={status}")

    print(
        f"ios 推送：目标设备: {len(tokens)} | 失败: {len(failed_tokens)} | "
        f"耗时: {time.time() - start_time:.2f}s"
    )
    return failed_tokens

# send_apns_batch(['fb701c01d93fa074c4ff12bbddd3d3a5534b11c0a43382c151cd22d981cf7abb'], '危急值提醒', '发现新危急值，请及时处理[王世方-张彪-3078854-0]')



# 注意 ck_nopass.pem 有效期为一年，当前证书 2027-10-29 到期，到期后需要新证书
# https://developer.apple.com/account/resources/certificates/list
# 第一步：确认/创建 APNs 推送证书
# 点击 Certificates 右上角的 ➕ 号。
# 向下滚动到 Services 部分，找到 Apple Push Services。
# 点击继续，选择你的 App ID（com.nsyy.Nsyy），按提示生成 CSR 并上传。 （/Users/gaoyanliang/nsyy/ios/CertificateSigningRequest.certSigningRequest）
# 生成后，下载这个 Apple Push Services 的 .cer 文件（不要再下载 iOS Distribution 或 Development 来试了，它们不是干这个用的）。
#
# 第二步：在 Mac 上导出私钥
#
# 打开 钥匙串访问 (Keychain Access)。
# 在左侧选择 “登录” 或 “系统” 钥匙串，在类别中选择 “我的证书”。
# 找到你刚刚下载的、名字包含 Apple Push Services: com.nsyy.Nsyy 的证书。
# 展开它，确认下面有一个私钥。
# 右键点击这个证书，选择 “导出...”，保存为 ck.p12 文件，设置一个临时密码（比如 123456）。

# cd /Users/gaoyanliang/nsyy/nsyy-project/gylmodules/workstation/message/
#
# # 1. 下载的 .cer 转 .pem
# openssl x509 -inform der -in aps.cer -out aps_cert.pem
#
# # 2. 从 p12 提取私钥（会提示输入刚才设置的临时密码）
# openssl pkcs12 -in ck.p12 -nocerts -nodes -legacy -out ck_key.pem
#
# # 3. 合并证书和私钥
# cat aps_cert.pem ck_key.pem > ck_nopass.pem
#
# # 4. 清理临时文件
# rm aps_cert.pem ck_key.pem aps.cer ck.p12
# 验证新文件
# 检查证书主题和有效期，确保是新的
# openssl x509 -in ck_nopass.pem -noout -subject -dates
#
# # 检查私钥是否无密码
# openssl rsa -in ck_nopass.pem -check -noout
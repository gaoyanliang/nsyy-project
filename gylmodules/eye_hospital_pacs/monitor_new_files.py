import os
import time
import json
from datetime import datetime
from smb.SMBConnection import SMBConnection
import logging
import socket

# 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('monitor.log'),  # 保存日志到文件
#         logging.StreamHandler()  # 同时输出到控制台
#     ]
# )
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 共享文件夹配置
SHARE_SERVER = "192.168.124.5"  # Windows 电脑 IP
SHARE_NAME = "test_share"  # 共享文件夹名称
USERNAME = ""  # 匿名访问，无用户名
PASSWORD = ""  # 匿名访问，无密码
DOMAIN = ""  # 匿名访问，无域
CHECK_INTERVAL = 10  # 检查间隔（秒）
RECONNECT_INTERVAL = 30  # 重新连接间隔（秒）
LOCAL_DOWNLOAD_DIR = "downloaded_files"  # 本地下载目录
STATE_FILE = "file_state.json"  # 保存文件状态的文件

# 确保下载目录存在
if not os.path.exists(LOCAL_DOWNLOAD_DIR):
    os.makedirs(LOCAL_DOWNLOAD_DIR)

# 存储文件状态
last_file_list = set()


def load_file_state():
    """加载上次保存的文件状态"""
    global last_file_list
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                last_file_list = set(json.load(f))
            logger.info(f"从 {STATE_FILE} 加载文件状态，包含 {len(last_file_list)} 个文件")
        except Exception as e:
            logger.error(f"加载文件状态失败: {e}")
    else:
        logger.info("未找到状态文件，初始化为空")


def save_file_state():
    """保存当前文件状态"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(list(last_file_list), f)
        logger.info(f"文件状态已保存到 {STATE_FILE}")
    except Exception as e:
        logger.error(f"保存文件状态失败: {e}")


def connect_smb():
    """连接到 SMB 共享"""
    try:
        conn = SMBConnection(USERNAME, PASSWORD, "client_name", SHARE_SERVER, use_ntlm_v2=True, is_direct_tcp=True)
        if conn.connect(SHARE_SERVER, 445):
            logger.info(f"成功连接到 {SHARE_SERVER}")
            return conn
        else:
            logger.error("SMB 连接失败：无法建立连接")
            return None
    except socket.error as e:
        logger.error(f"连接 SMB 失败（网络错误）: {e}")
        return None
    except Exception as e:
        logger.error(f"连接 SMB 失败: {e}")
        return None


def get_file_list(conn, share_name, path=""):
    """获取共享文件夹中的文件列表"""
    file_set = set()
    try:
        files = conn.listPath(share_name, path)
        for file_info in files:
            if file_info.filename not in (".", ".."):
                file_path = os.path.join(path, file_info.filename).replace("\\", "/")
                if file_info.isDirectory:
                    file_set.update(get_file_list(conn, share_name, file_path))
                else:
                    file_set.add(file_path)
        return file_set
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return None  # 返回 None 表示获取失败


def download_file(conn, share_name, file_path):
    """下载文件到本地"""
    try:
        local_path = os.path.join(LOCAL_DOWNLOAD_DIR, file_path.replace("/", os.sep))
        local_dir = os.path.dirname(local_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        with open(local_path, 'wb') as f:
            conn.retrieveFile(share_name, file_path, f)
        logger.info(f"文件下载成功: {file_path} -> {local_path}")
    except Exception as e:
        logger.error(f"下载文件 {file_path} 失败: {e}")


def monitor_shared_folder():
    """监控共享文件夹"""
    global last_file_list
    # 加载上次文件状态
    load_file_state()

    conn = None
    while True:
        # 如果没有连接或连接已断开，尝试重新连接
        if not conn:
            logger.info(f"尝试连接到 {SHARE_SERVER}...")
            conn = connect_smb()
            if not conn:
                logger.warning(f"连接失败，将在 {RECONNECT_INTERVAL} 秒后重试")
                time.sleep(RECONNECT_INTERVAL)
                continue

        try:
            # 获取文件列表
            current_file_list = get_file_list(conn, SHARE_NAME)
            if current_file_list is None:
                logger.error("无法获取文件列表，可能是连接断开，尝试重新连接")
                conn.close()
                conn = None
                time.sleep(RECONNECT_INTERVAL)
                continue

            # 检测新文件
            files_changed = False
            new_files = current_file_list - last_file_list
            if new_files:
                files_changed = True
                logger.info("检测到新文件:")
                for file in new_files:
                    logger.info(f"  - {file}")
                    # 下载新文件
                    download_file(conn, SHARE_NAME, file)

            # 检测删除的文件
            deleted_files = last_file_list - current_file_list
            if deleted_files:
                files_changed = True
                logger.info("检测到文件被删除:")
                for file in deleted_files:
                    logger.info(f"  - {file}")

            # 仅在文件有变化时更新文件列表和保存状态
            if files_changed:
                last_file_list = current_file_list
                save_file_state()
            else:
                logger.debug("无文件变化，未保存状态")

            # 等待下一次检查
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("监控程序终止")
            # 确保程序终止时保存状态（如果有变化）
            if conn:
                current_file_list = get_file_list(conn, SHARE_NAME)
                if current_file_list is not None and last_file_list != current_file_list:
                    save_file_state()
            break
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
            # 关闭当前连接，准备重新连接
            if conn:
                conn.close()
                conn = None
            time.sleep(RECONNECT_INTERVAL)

    # 程序结束时关闭连接
    if conn:
        conn.close()


if __name__ == "__main__":
    logger.info("开始监控共享文件夹 test_share...")
    monitor_shared_folder()

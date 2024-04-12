import socket

"""
判断是否在本地运行 
"""


def run_in_local():
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到远程服务器（无需实际连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        ip_address = s.getsockname()[0]
        # '192.168.124.3' 为本地 ip
        if str(ip_address).startswith('192.168.124.'):
            print("本地运行" + ip_address)
            return True
        else:
            print("非本地运行" + ip_address)
            return False
    except Exception as e:
        print("Error:", e)
        return False


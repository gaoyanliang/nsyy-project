# 本地上传路径
upload_path_local = "/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/file_system/file_upload"

# 线上上传路径
upload_path_dev = f"/home/gyl/file_upload"


PERM_FIELDS = [
    "can_view",
    "can_edit",
    "can_delete",
    "can_download",
    "can_upload",
]

YUANJI_ALLOWED_USERS = ['110100', '100101']


# 远程文件服务器配置
SFTP_HOST = "192.168.9.75"
SFTP_USERNAME = "gyl"
SFTP_PASSWORD = "nsyy0601."
SFTP_PORT = 22
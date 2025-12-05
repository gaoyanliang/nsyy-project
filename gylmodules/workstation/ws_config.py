# ===========================================================
# =============         message         =====================
# ===========================================================
# 通知消息
NOTIFICATION_MESSAGE = 0
# 私聊
PRIVATE_CHAT = 1
# 群聊
GROUP_CHAT = 2


# msg cache redis key
msg_cache_key = {
    "group_member": "MESSAGE:GroupMember:{}",
    "group_info": "MESSAGE:GroupInfo:{}",
    "messages": "MESSAGE:Messages:{}",
}



# ===========================================================
# =============         fail            =====================
# ===========================================================

FILE_UPLOAD_FOLDER = '/uploads'
FILE_DOWNLOAD_FOLDER = '/downloads'
FILE_ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip'}

# sftp config
FILE_SFTP_HOST = '192.168.124.128'
FILE_SFTP_PORT = 22
FILE_SFTP_USERNAME = 'root'
FILE_SFTP_PASSWORD = '111111'
FILE_SFTP_REMOTE_FILES_PATH = '/home/yanliang/file-manager'

# SSH connection details
FILE_SSH_HOST = "192.168.124.128"
FILE_SSH_USERNAME = "root"
FILE_SSH_PASSWORD = "111111"

# file scope (全院，部门，项目，个人)
FILE_SCOPE = {1, 2, 3, 4}
FILE_SCOPE_ALL = 1
FILE_SCOPE_DEPT = 2
FILE_SCOPE_PROJECT = 3
FILE_SCOPE_PERSON = 4

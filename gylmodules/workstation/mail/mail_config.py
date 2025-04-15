
# ===========================================================
# =============         mail            =====================
# ===========================================================

# mail server db config
# MAIL_DB_HOST = '192.168.124.128'
# MAIL_DB_PORT = 3306
# MAIL_DB_USERNAME = 'root'
# MAIL_DB_PASSWORD = '111111'
# MAIL_DB_DATABASE = 'vmail'

MAIL_DB_HOST = '192.168.3.92'
MAIL_DB_PORT = 3306
MAIL_DB_USERNAME = 'root'
MAIL_DB_PASSWORD = 'NSYYnsyy@123'
MAIL_DB_DATABASE = 'vmail'

# 默认密码  nsyy0601
mail_default_passwd = "{SSHA512}w1gDN4y3uc/nyhuB+nMkbpd7c6yEB4/7DEoC6sIewkk9U9JvyGe498psVz92IfakT6ERsXzdNxoO23TKXi1+yN4UWjo="

MAIL_DOMAIN = '@nsyy.com'
MAIL_ACCOUNT_PASSWORD = 'nsyy0601'
MAIL_MAILBOX = 'INBOX'

# SSH connection details
# MAIL_SSH_HOST = "192.168.124.128"
# MAIL_SSH_USERNAME = "root"
# MAIL_SSH_PASSWORD = "111111"
MAIL_SSH_HOST = "192.168.3.92"
MAIL_SSH_USERNAME = "cc"
MAIL_SSH_PASSWORD = 'NSYYnsyy@123'
MAIL_SMTP_PORT = 587
MAIL_IMAP_PORT = 993

MAIL_OPERATE_UPDATE = 0
MAIL_OPERATE_ADD = 1
MAIL_OPERATE_REMOVE = 2
MAIL_OPERATE_PUBLIC = 3
MAIL_OPERATE_DELETE = 4

inline_attachments_dir_dev = "/Users/gaoyanliang/nsyy/nsyy-project/mail_inline_attachments"
inline_attachments_dir_prod = "/home/gyl/gyl_server/mail_inline_attachments"

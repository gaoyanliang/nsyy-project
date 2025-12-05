
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
# mail_default_passwd = "{SSHA512}w1gDN4y3uc/nyhuB+nMkbpd7c6yEB4/7DEoC6sIewkk9U9JvyGe498psVz92IfakT6ERsXzdNxoO23TKXi1+yN4UWjo="
# 默认密码  NSYYnsyy@123
mail_default_passwd = "{SSHA512}tuXy5LuK3F1NTLEOY1DuNIXco7OMzwHXcaN65HAYRgR6tJy6gRBicfuUEqjgsPJkj0RPTTrymi355w5Fvj97asxL+KY="

# MAIL_DOMAIN = '@nsyy.com'
MAIL_DOMAIN = ''
MAIL_ACCOUNT_PASSWORD = 'NSYYnsyy@123'
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


default_flags = []
default_folders = []

emp_map = {'U00351': {'name': '秦付绕', 'dept': '质量管理部', 'account': 'qin.furao', 'emp_num': 'U00351'}, 'U01315': {'name': '丁雪', 'dept': '质量管理部', 'account': 'ding.xue', 'emp_num': 'U01315'}, 'U01948': {'name': '孙丽娜', 'dept': '质量管理部', 'account': 'sun.lina', 'emp_num': 'U01948'}, 'U02192': {'name': '李黄', 'dept': '质量管理部', 'account': 'li.huang', 'emp_num': 'U02192'}, 'U02583': {'name': '王永慧', 'dept': '质量管理部', 'account': 'wang.yonghui', 'emp_num': 'U02583'}, 'U00201': {'name': '王芳', 'dept': '院感部', 'account': 'wang.fang', 'emp_num': 'U00201'}, 'U00309': {'name': '张理', 'dept': '院感部', 'account': 'zhang.li', 'emp_num': 'U00309'}, 'U01717': {'name': '王冬冬', 'dept': '院感部', 'account': 'wang.dongdong', 'emp_num': 'U01717'}, 'U01197': {'name': '张璇', 'dept': '院感部', 'account': 'zhang.xuan', 'emp_num': 'U01197'}, 'U00268': {'name': '祝明伟', 'dept': '医务部', 'account': 'zhu.mingwei', 'emp_num': 'U00268'}, 'U01831': {'name': '屈洋军', 'dept': '医务部', 'account': 'qu.yangjun', 'emp_num': 'U01831'}, 'U02964': {'name': '罗佳佳', 'dept': '医务部', 'account': 'luo.jiajia', 'emp_num': 'U02964'}, 'U02201': {'name': '吕婷婷', 'dept': '医务部', 'account': 'lv.tingting', 'emp_num': 'U02201'}, 'U02274': {'name': '胡鑫', 'dept': '医务部', 'account': 'hu.xin', 'emp_num': 'U02274'}, 'U02797': {'name': '李存', 'dept': '医务部', 'account': 'li.cun', 'emp_num': 'U02797'}, 'U00834': {'name': '李莉1', 'dept': '医务部', 'account': 'li.li1', 'emp_num': 'U00834'}, 'U02980': {'name': '赵淅鹏', 'dept': '医务部', 'account': 'zhao.xipeng', 'emp_num': 'U02980'}, 'U00701': {'name': '杨彩丽', 'dept': '护理部', 'account': 'yang.caili', 'emp_num': 'U00701'}, 'U00536': {'name': '杜蕾', 'dept': '护理部', 'account': 'du.lei', 'emp_num': 'U00536'}, 'U00446': {'name': '杨淑萍2', 'dept': '护理部', 'account': 'yang.shuping2', 'emp_num': 'U00446'}, 'U01877': {'name': '张淼', 'dept': '护理部', 'account': 'zhang.miao', 'emp_num': 'U01877'}, 'U00871': {'name': '房彩丽', 'dept': '护理部', 'account': 'fang.caili', 'emp_num': 'U00871'}, 'U01894': {'name': '胡弋璐', 'dept': '护理部', 'account': 'hu.yilu', 'emp_num': 'U01894'}, 'U01806': {'name': '王帅', 'dept': '护理部', 'account': 'wang.shuai', 'emp_num': 'U01806'}, 'U01797': {'name': '赵曼曼', 'dept': '护理部', 'account': 'zhao.manman', 'emp_num': 'U01797'}, 'U00001': {'name': '赵俊祥', 'dept': '行政办公室', 'account': 'zhao.junxiang', 'emp_num': 'U00001'}, 'U00002': {'name': '石军峰', 'dept': '行政办公室', 'account': 'shi.junfeng', 'emp_num': 'U00002'}, 'U04823': {'name': '赵博', 'dept': '行政办公室', 'account': 'zhao.bo', 'emp_num': 'U04823'}, 'U00006': {'name': '梁红春', 'dept': '行政办公室', 'account': 'liang.hongchun', 'emp_num': 'U00006'}, 'U10338': {'name': '周良', 'dept': '行政办公室', 'account': 'zhou.liang', 'emp_num': 'U10338'}, 'U00027': {'name': '时延龙', 'dept': '行政办公室', 'account': 'shi.yanlong', 'emp_num': 'U00027'}, 'U00009': {'name': '陆阳', 'dept': '行政办公室', 'account': 'lu.yang', 'emp_num': 'U00009'}, 'U01999': {'name': '陆月栈', 'dept': '行政办公室', 'account': 'lu.yuezhan', 'emp_num': 'U01999'}, 'U01832': {'name': '李雪', 'dept': '行政办公室', 'account': 'li.xue', 'emp_num': 'U01832'}, 'U02016': {'name': '李冰', 'dept': '行政办公室', 'account': 'li.bing', 'emp_num': 'U02016'}, 'u02614': {'name': '王菁菁', 'dept': '行政办公室', 'account': 'wang.jingjing', 'emp_num': 'u02614'}, 'U02876': {'name': '陈嘉钰', 'dept': '行政办公室', 'account': 'chen.jiayu', 'emp_num': 'U02876'}, 'U10001': {'name': '叶林峰', 'dept': '行政办公室', 'account': 'ye.linfeng', 'emp_num': 'U10001'},
           'U01283': {'name': '苏林', 'dept': '行政办公室', 'account': 'su.lin', 'emp_num': 'U01283'}, 'U00019': {'name': '禹丰', 'dept': '病案与信息管理部', 'account': 'yu.feng', 'emp_num': 'U00019'}, 'U01406': {'name': '王献峣', 'dept': '病案与信息管理部', 'account': 'wang.xianyao', 'emp_num': 'U01406'},
           'U00888': {'name': '崔光旭', 'dept': '病案与信息管理部', 'account': 'cui.guangxu', 'emp_num': 'U00888'},
           'U00080': {'name': '苏里', 'dept': '病案与信息管理部', 'account': 'su.li', 'emp_num': 'U00080'}, 'U00018': {'name': '任云鹤', 'dept': '病案与信息管理部', 'account': 'ren.yunhe', 'emp_num': 'U00018'}, 'U01420': {'name': '丁磊', 'dept': '病案与信息管理部', 'account': 'ding.lei', 'emp_num': 'U01420'}, 'U00011': {'name': '于闯', 'dept': '病案与信息管理部', 'account': 'yu.chuang', 'emp_num': 'U00011'}, 'U04824': {'name': '张世坦', 'dept': '病案与信息管理部', 'account': 'zhang.shitan', 'emp_num': 'U04824'}, 'U03378': {'name': '张竣', 'dept': '病案与信息管理部', 'account': 'zhang.jun', 'emp_num': 'U03378'}, 'U03472': {'name': '张榆', 'dept': '病案与信息管理部', 'account': 'zhang.yu', 'emp_num': 'U03472'}, 'admin': {'name': 'admin', 'dept': 'admin', 'account': 'admin', 'emp_num': 'admin'}}










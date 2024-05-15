#  === redis config ===

APPT_REDIS_HOST = '127.0.0.1'
APPT_REDIS_PORT = 6379
APPT_REDIS_DB = 2

# 预约类型
APPT_TYPE = {'online': 1, 'offline': 2}

# 预约紧急程度
APPT_URGENCY_LEVEL = {'green': 1, 'yellow': 2, 'red': 3}

# 0=保留 1=已预约 2=排队中 3=处理中 4=过号 5=已完成 6=已取消
APPT_STATE = {'new': 0, 'booked': 1, 'in_queue': 2, 'processing': 3, 'over_num': 4, 'completed': 5, 'canceled': 6}

# 测试环境推送地址
socket_push_url = 'http://192.168.124.53:6080/inter_socket_msg'

# 预约人紧急程度
APPT_URGENCY_LEVEL_KEY = 'APPT_URGENCY_LEVEL'
# 签到计数
APPT_SIGN_IN_NUM_KEY = 'APPT_SIGN_IN_NUM'
# 所有预约项目
APPT_PROJECTS_KEY = 'APPT_PROJECTS'
# 所有项目 按子类分组
APPT_PROJECTS_CATEGORY_KEY = 'APPT_PROJECTS_CATEGORY'
# 近7天所有项目剩余可预约数量
APPT_REMAINING_RESERVATION_QUANTITY_KEY = 'APPT_REMAINING_RESERVATION_QUANTITY'
# 坐诊医生
APPT_ATTENDING_DOCTOR_KEY = 'APPT_ATTENDING_DOCTOR'
# 医生图片
APPT_DOCTOR_INFO_KEY = 'APPT_DOCTOR_INFO'
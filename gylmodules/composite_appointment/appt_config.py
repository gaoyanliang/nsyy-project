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


#  === redis config ===

APPT_REDIS_HOST = '127.0.0.1'
APPT_REDIS_PORT = 6379
APPT_REDIS_DB = 2

# 预约类型 1=在线预约（小程序） 2=现场预约 3=自助挂号，手机查询时创建， 4=根据医嘱创建
APPT_TYPE = {'online': 1, 'offline': 2, 'auto_appt': 3, 'advice_appt': 4}

# 预约紧急程度
APPT_URGENCY_LEVEL = {'green': 1, 'yellow': 2, 'red': 3}

# 预约付款状态
# oa 和 his 均付款的情况下 oa付款支持退款
appt_pay_state = {'unpaid': 0, 'oa_pay': 1, 'his_pay': 2, 'oa_his_both_pay': 3}

# 0=保留 1=已预约 2=排队中 3=处理中 4=过号 5=已完成 6=已取消
APPT_STATE = {'new': 0, 'booked': 1, 'in_queue': 2, 'processing': 3, 'over_num': 4, 'completed': 5, 'canceled': 6}

# APPT_PERIOD_INFO = {1: '8:00-8:30', 2: '8:30-9:00', 3: '9:00-9:30', 4: '9:30-10:00', 5: '10:00-10:30', 6: '10:30-11:00', 7: '11:00-11:30', 8: '11:30-12:00'}
APPT_PERIOD_INFO = {1: '8:00-8:30', 2: '8:30-9:00', 3: '9:00-9:30', 4: '9:30-10:00', 5: '10:00-10:30', 6: '10:30-11:00',
                    7: '11:00-11:30', 8: '11:30-12:00', 9: '14:00-14:30', 10: '14:30-15:00', 11: '15:00-15:30',
                    12: '15:30-16:00', 13: '16:00-16:30', 14: '16:30-17:00', 15: '17:00-17:30', 16: '17:30-18:00'}

APPT_PERIOD_STR_INFO = {'8:00-8:30': 1,'8:30-9:00': 2, '9:00-9:30': 3, '9:30-10:00': 4, '10:00-10:30': 5, '10:30-11:00': 6,
                    '11:00-11:30': 7, '11:30-12:00': 8, '14:00-14:30': 9, '14:30-15:00': 10, '15:00-15:30': 11,
                    '15:30-16:00': 12, '16:00-16:30': 13, '16:30-17:00': 14, '17:00-17:30': 15, '17:30-18:00': 16}

# APPT_PERIOD_INFO = {1: '8:00-8:30', 2: '8:30-9:00', 3: '9:00-9:30', 4: '9:30-10:00', 5: '10:00-10:30', 6: '10:30-11:00', 7: '11:00-11:30', 8: '11:30-12:00', 9: '14:00-14:30', 10: '14:30-15:00', 11: '15:00-15:30', 12: '15:30-16:00', 13: '16:00-16:30', 14: '16:30-17:00', 15: '17:00-17:30', 16: '17:30-18:00',
#                     17: '18:00-18:30', 2: '18:30-19:00', 3: '19:00-19:30', 4: '19:30-20:00', 5: '20:00-20:30', 6: '20:30-21:00',
#                     7: '21:00-21:30', 8: '21:30-22:00', 9: '22:00-22:30', 10: '22:30-23:00', 11: '23:00-23:30',
#                     12: '23:30-00:00', 13: '00:00-00:30', 14: '00:30-1:30', 15: '1:30-2:00', 16: '2:30-3:00', 12: '3:30-4:00', 13: '4:00-4:30', 14: '4:30-5:00', 15: '5:00-5:30', 16: '5:30-6:00', 13: '6:00-6:30', 14: '6:30-7:00', 15: '7:00-7:30', 16: '7:30-8:00',
#                     }


appt_slot_dict = {
    0: 1,
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 1,
    6: 1,
    7: 1,
    8: 1,
    9: 3,
    10: 5,
    11: 7,
    12: 9,
    13: 9,
    14: 9,
    15: 11,
    16: 13,
    17: 15,
    18: 1,
    19: 1,
    20: 1,
    21: 1,
    22: 1,
    23: 1,
}

# socket 推送地址
socket_push_url = 'http://120.194.96.67:6066/inter_socket_msg'

default_photo = 'L2hvbWUvY2MvYXR0L3B1YmxpYy9kb2MvZGVmYXVsdC5wbmc='



# 所有项目 按子类分组
APPT_PROJECTS_CATEGORY_KEY = 'APPT_PROJECTS_CATEGORY'
# 近7天所有项目剩余可预约数量
APPT_REMAINING_RESERVATION_QUANTITY_KEY = 'APPT_REMAINING_RESERVATION_QUANTITY'
# 坐诊医生
APPT_ATTENDING_DOCTOR_KEY = 'APPT_ATTENDING_DOCTOR'

# 医生图片
APPT_DOCTOR_PHOTO_INFO_KEY = 'APPT_DOCTOR_PHOTO_INFO'

# 根据医生查找项目
APPT_DOCTOR_TO_PROJ_KEY = 'APPT_DOCTOR_TO_PROJ'



# 签到计数
APPT_SIGN_IN_NUM_KEY = 'APPT_SIGN_IN_NUM'
# 医生信息
APPT_DOCTORS_KEY = 'APPT_DOCTORS'
APPT_DOCTORS_BY_NAME_KEY = 'APPT_DOCTORS_BY_NAME'
# 所有预约项目
APPT_PROJECTS_KEY = 'APPT_PROJECTS'
# 执行科室信息
APPT_EXECUTION_DEPT_INFO_KEY = 'APPT_EXECUTION_DEPT_INFO'
# 所有房间
APPT_ROOMS_KEY = 'APPT_ROOMS'
APPT_ROOMS_BY_PROJ_KEY = 'APPT_ROOMS_BY_PROJ'
# 所有排班信息
APPT_SCHEDULING_KEY = 'APPT_SCHEDULING'
APPT_SCHEDULING_DAILY_KEY = 'APPT_SCHEDULING_DAILY'
# 当天自助挂号记录
APPT_DAILY_AUTO_REG_RECORD_KEY = 'APPT_DAILY_AUTO_REG_RECORD'

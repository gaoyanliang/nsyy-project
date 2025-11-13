# 预约类型 1=在线预约（小程序） 2=现场预约 3=自助挂号，手机查询时创建， 4=根据医嘱创建  6=挂号（自助机/诊间）后登记 排号  7=仅排号
APPT_TYPE = {'online': 1, 'offline': 2, 'auto_appt': 3, 'advice_appt': 4,
             'inpatient_advice': 5, "after_reg": 6, "numbering": 7}

# 预约紧急程度
APPT_URGENCY_LEVEL = {'green': 1, 'yellow': 2, 'red': 3}

# 预约付款状态
# oa 和 his 均付款的情况下 oa付款支持退款 4=oa已退款
appt_pay_state = {'unpaid': 0, 'oa_pay': 1, 'his_pay': 2, 'oa_his_both_pay': 3, 'oa_refunded': 4}

# 0=保留 1=已预约 2=排队中 3=处理中 4=过号 5=已完成 6=已取消（未签到前，小程序取消金额原路返回） 7=已退费（签到后，调用退费接口）
APPT_STATE = {'new': 0, 'booked': 1, 'in_queue': 2, 'processing': 3,
              'over_num': 4, 'completed': 5, 'canceled': 6, 'refund': 7}

# 时间段
APPT_PERIOD_INFO = {1: '8:00-9:00', 2: '9:00-10:00', 3: '10:00-11:00', 4: '11:00-12:00',
                    5: '14:00-15:00', 6: '15:00-16:00', 7: '16:00-17:00', 8: '17:00-18:00'}

APPT_PERIOD_STR_INFO = {'8:00-9:00': 1, '9:00-10:00': 2, '10:00-11:00': 3, '11:00-12:00': 4,
                        '14:00-15:00': 5, '15:00-16:00': 6, '16:00-17:00': 7, '17:00-18:00': 8}

appt_slot_dict = {
    0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 2, 10: 3, 11: 4, 12: 5,
    13: 5, 14: 5, 15: 6, 16: 7, 17: 7, 18: 5, 19: 5, 20: 5, 21: 5, 22: 5, 23: 5
}

default_photo = 'L2hvbWUvY2MvYXR0L3B1YmxpYy9kb2MvZGVmYXVsdC5wbmc='
default_sort_num = 9999

# 近7天所有项目剩余可预约数量
APPT_REMAINING_RESERVATION_QUANTITY_KEY = 'APPT_REMAINING_RESERVATION_QUANTITY'
# 签到计数
APPT_SIGN_IN_NUM_KEY = 'APPT_SIGN_IN_NUM'
# 医生信息
APPT_DOCTORS_KEY = 'APPT_DOCTORS'
APPT_DOCTORS_BY_NAME_KEY = 'APPT_DOCTORS_BY_NAME'
# 所有项目
APPT_PROJECTS_KEY = 'APPT_PROJECTS'
# 执行科室信息
APPT_EXECUTION_DEPT_INFO_KEY = 'APPT_EXECUTION_DEPT_INFO'
# 所有房间
APPT_ROOMS_KEY = 'APPT_ROOMS'
APPT_ROOMS_BY_PROJ_KEY = 'APPT_ROOMS_BY_PROJ'
# 当天自助挂号记录
APPT_DAILY_AUTO_REG_RECORD_KEY = 'APPT_DAILY_AUTO_REG_RECORD'

doctor_name_list = [
    "杨洪", "徐文举", "李翔", "王天才", "张继东",
    "朱新臣", "凌云", "郭俊范", "肖小华",
    "刘朝锋", "王相阁", "冯大磊", "朱帅", "吴广",
    "孙世辉", "杨荣刚", "杨越峰", "刘艳贞", "魏天",
    "乔煦", "陶江涛", "高改", "罗亚敏",
    "邹克勇", "靳峰", "张高峰", "徐锋", "金海明",
    "肖正红", "闻朋浩", "翟焕阁", "袁燕", "刘斌",
    "张晓奎", "钱俊甫", "师恒伟", "余德旺", "周理",
    "李森森", "王玉", "白石", "王桂安", "刘淑君", "李翔",
    "李风波", "李新旗", "杨寒", "姜飒", "吴云刚", "苏艳荣",
    "李雯洁", "熊飞", "刘正廷", "吕小洽", "屈新华", "贾新春",
    "侯海燕", "宋佳", "孙丽苏", "席三赢", "袁苗"]

# 医嘱状态
medical_order_status = {
    "unordered": 0,  # 未开医嘱
    "ordered": 1,    # 已开医嘱
 }

# 登记状态

register_status = {
    "not_started": 0,    # 未开始
    "in_progress": 1,    # 执行中
    "cancelled": 2,      # 已取消
    "completed": 3       # 已完成
}

# 治疗记录状态

treatment_record_status = {
    "pending": 0,      # 待执行
    "implement": 1,    # 执行
    "cancel_this": 2,  # 取消本执行
    "cancel_all": 3    # 取消全部
}

comp_type = {
    12: "南石医院总院",
    32: "康复中医院"
}

sign_info = {
    "刘春敏": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMS0wNS8xNzMwNzY2ODExLjc0NjgyMS5wbmc=",
    "付杰": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMS0wMS8xNzMwNDI3MjEyLjE3NzI4MTYucG5n",
    "陈安平": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMS0wNS8xNzMwNzY0NzY3LjQ1OTA5OS5wbmc=",
    "樊琳": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMS0wMy8xNzMwNTk4NjI0Ljc4MzI3OTcucG5n",
    "admin": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMi0xOC8xNzM0NDg0MzQ3LjUzNjkzNjMucG5n",
    "李璐": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0LzIwMjQvMjAyNC0xMi0yMy8xNzM0OTI1MjA4LjQzNDI2NzgucG5n"
}

sign_user_id = {
    "刘春敏": "U0392",
    "付杰": "U0397",
    "陈安平": "U0368",
    "樊琳": "U2144",
    "admin": "17382120012",
    "李璐": "U1136"
}

sign_file_path = '/home/gyl/hbot_sign_info/'

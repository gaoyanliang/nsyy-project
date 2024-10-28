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
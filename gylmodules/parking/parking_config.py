
park_id_dict = {
    "南石医院": "36716d9a-e37a-11eb-a77d-bb0a9f242da1",
    "南石医院南院区": "69389046-a0a0-11ef-9ac2-7715cd54bd16",
}

park_info = {
    "group_list": ['员工车辆', 'VIP'],
    "park_list": ['南石医院', '南石医院南院区']
}


# 预警时间
warning_day = 7 * 24 * 60

# 停用时间
shutdown_day = 9 * 24 * 60

enable_auto_freeze = True

redis_key = 'necessary_to_execute'

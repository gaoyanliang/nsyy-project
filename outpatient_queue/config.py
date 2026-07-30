# Redis配置
REDIS_CONFIG = {
    # 'host': '192.168.124.9',
    'host': '127.0.0.1',
    'port': 6379,
    'db': 9,
    'decode_responses': True
}


# 业务类型配置 - 使用字母前缀
BUSINESS_TYPES = {
    "1": {
        'name': '门诊取药',
        'type': 'medicine',
        'windows': [],
        'prefix': 'A',      # 使用A开头
        'color': '#e74c3c',
        'description': '含药品查询', # '含药品查询缴费',
        'icon': '💊',
        'voice': 'A'        # 语音播报用字母A
    },
    "2": {
        'name': '打印病历',
        'type': 'record',
        'windows': [],
        'prefix': 'B',      # 使用B开头
        'color': '#3498db',
        'description': '病历打印服务',
        'icon': '📄',
        'voice': 'B'
    },
    "3": {
        'name': '医院缴费',
        'type': 'payment',
        'windows': [],
        'prefix': 'C',      # 使用C开头
        'color': '#f39c12',
        'description': '医疗费用缴纳',
        'icon': '💰',
        'voice': 'C'
    },
    "4": {
        'name': '工伤结算/用血报销',
        'type': 'payment',
        'windows': ['8'],
        'prefix': 'C',  # 使用C开头
        'color': '#f39c12',
        'description': '工伤结算/用血减免报销业务处理，在3号缴费窗口独立办理',
        'icon': '💰',
        'voice': 'C'
    }
}

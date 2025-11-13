# 全局配置
# 线上环境使用 server db config ， 定时任务全部开启， run_in_local=False

# server db config
# DB_HOST = '192.168.3.12'
# DB_PORT = 3306
# DB_USERNAME = 'gyl'
# DB_PASSWORD = '123456'
# DB_DATABASE_GYL = 'nsyy_gyl'

# local db config
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USERNAME = 'root'
DB_PASSWORD = 'gyl.2015'
DB_DATABASE_GYL = 'nsyy_gyl'

db_config = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USERNAME,
    'password': DB_PASSWORD,
    'database': DB_DATABASE_GYL
}

# redis db config
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2

# 管理定时任务开启和关闭
schedule_task = {'cv_timeout': 1, 'cv_dept_update': 1, 'appt_daily': 1}

run_in_local = True

# socket_push_url = 'http://192.168.124.53:6080/inter_socket_msg'
socket_push_url = 'http://120.194.96.67:6066/inter_socket_msg'
# # 服务器使用内网地址
# socket_push_url = 'http://192.168.3.65:6066/inter_socket_msg'


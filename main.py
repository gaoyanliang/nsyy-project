# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

# -*- coding: utf-8 -*-
# 必须放在最前面，早于任何其他 import
from gevent import monkey
monkey.patch_all()

from gylmodules.composite_appointment import ca_server
from gylmodules.critical_value import critical_value

# 立即配置日志（放在最前面，确保其他模块导入前生效）
import logging
from gylmodules import global_config
from gylmodules.global_tools import setup_logging

if global_config.run_in_local:
    setup_logging(log_file='my_app.log', level=logging.DEBUG)
else:
    setup_logging(log_file='my_app.log', level=logging.INFO)

logger = logging.getLogger(__name__)
import time

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from gylmodules.app import gylroute
from gylmodules import gylschedule_task

server_app = Flask(__name__)
server_app.register_blueprint(gylroute, url_prefix='/gyl')

CORS(server_app, supports_credentials=True)
# 需要安装 eventlet， （pip3 install eventlet） 否则 ValueError: Invalid async_mode specified
# async_mode = "eventlet"
# socketio = SocketIO()
# socketio.init_app(server_app, cors_allowed_origins='*', async_mode=async_mode, subprocess=1000, threaded=True)

async_mode = "gevent"   # 改成 gevent
socketio = SocketIO()
socketio.init_app(server_app, cors_allowed_origins='*', async_mode=async_mode)

# ---------- 显式初始化缓存 ----------
# 注意：gevent 环境下，在 fork 之前调用，能保证所有 worker 进程都持有同一份初始缓存
# 但如果你用 gunicorn 多 worker，每个 worker 会各自 import main.py，
# 所以这段会被每个 worker 执行一次 —— 这是可以接受的，因为它是“读”操作，不会互相覆盖
ca_server.init_cache()

critical_value.pull_running_cv()
# -----------------------------------


def start_schedule_work():
    # 如需修改任务，需关闭程序再重新启动
    import atexit
    import fcntl
    f = open("scheduler.lock", "wb")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except:
        return

    def unlock():
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

    atexit.register(unlock)

    # gyl schedule
    logger.info('项目启动')
    # schedule_task()
    gylschedule_task.schedule_task()
    time.sleep(3)  # 至少3秒 确保aaa被占用


# if __name__ == '__main__':
#     import threading
#     t = threading.Thread(target=start_schedule_work)
#     # t.setDaemon
#     t.daemon = True  # Python 3 推荐
#     t.start()
#     socketio.run(server_app, host='0.0.0.0', port=8080, debug=False, use_reloader=True)


if __name__ == '__main__':
    import gevent
    gevent.spawn(start_schedule_work)   # 用 greenlet 而不是 Thread
    socketio.run(server_app, host='0.0.0.0', port=8080, debug=False, use_reloader=False)
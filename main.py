# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

# -*- coding: utf-8 -*-
import os
import time

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from gylmodules.app import gylroute
from gylmodules.workstation.schedule_task import schedule_task
from gylmodules import gylschedule_task

server_app = Flask(__name__)
server_app.register_blueprint(gylroute, url_prefix='/gyl')

CORS(server_app, supports_credentials=True)
async_mode = "eventlet"
socketio = SocketIO()
socketio.init_app(server_app, cors_allowed_origins='*', async_mode=async_mode, subprocess=1000, threaded=True)


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
    print('项目启动')
    # schedule_task()
    gylschedule_task.schedule_task().start()
    time.sleep(3)  # 至少3秒 确保aaa被占用


if __name__ == '__main__':
    import threading
    t = threading.Thread(target=start_schedule_work)
    t.setDaemon
    t.start()
    socketio.run(server_app, host='0.0.0.0', port=6080, debug=True, use_reloader=True)

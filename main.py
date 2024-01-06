# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

# -*- coding: utf-8 -*-
import eventlet
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from sport_mng.sport_mng import sport_mng

server_app = Flask(__name__)

# 注册医体融合项目路由
server_app.register_blueprint(sport_mng, url_prefix='/gyl/sport_mng')
# server_app.register_blueprint(sport_mng)

CORS(server_app, supports_credentials=True)
async_mode = "eventlet"
socketio = SocketIO()
socketio.init_app(server_app, cors_allowed_origins='*', async_mode=async_mode, subprocess=1000, threaded=True)

if __name__ == '__main__':
    socketio.run(server_app, host='0.0.0.0', port=8080, debug=True, use_reloader=True)

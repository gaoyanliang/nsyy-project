# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

# -*- coding: utf-8 -*-
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from gylmodules.app import gylroute

server_app = Flask(__name__)
server_app.register_blueprint(gylroute, url_prefix='/gyl')

CORS(server_app, supports_credentials=True)
async_mode = "eventlet"
socketio = SocketIO()
socketio.init_app(server_app, cors_allowed_origins='*', async_mode=async_mode, subprocess=1000, threaded=True)

if __name__ == '__main__':
    socketio.run(server_app, host='0.0.0.0', port=8080, debug=True, use_reloader=True)

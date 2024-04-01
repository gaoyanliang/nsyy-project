from flask import Blueprint

from gylmodules.app_version.app_version_router import app_version
from gylmodules.critical_value.critical_value_router import cv
from gylmodules.sport_mng.sport_mng import sport_mng
from gylmodules.workstation.message.message_router import message_router
from gylmodules.workstation.mail.mail_router import mail_router

gylroute = Blueprint('gyl', __name__)

# ============================
# === 1. 注册医体融合项目路由 ===
# ============================
gylroute.register_blueprint(sport_mng)


# # ============================
# # === 2. 注册工作站相关路由 ====
# # ============================
# workstation = Blueprint('workstation', __name__, url_prefix='/workstation')
# # 2.1 注册消息管理路由
# workstation.register_blueprint(message_router)
# # 2.2 注册邮箱管理路由
# workstation.register_blueprint(mail_router)
#
# gylroute.register_blueprint(workstation)


# ============================
# === 3. 注册 app 版本管理  ====
# ============================
gylroute.register_blueprint(app_version)


# ============================
# === 4. 注册危机值系统路由 ====
# ============================
gylroute.register_blueprint(cv)

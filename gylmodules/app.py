from flask import Blueprint

from gylmodules.app_version.app_version_router import app_version
from gylmodules.critical_value.critical_value_router import cv
from gylmodules.composite_appointment.composite_appointment_router import appt
from gylmodules.medical_record_analysis.parse_router import parse
from gylmodules.sport_mng.sport_mng import sport_mng
from gylmodules.workstation.message.message_router import message_router
from gylmodules.workstation.mail.mail_router import mail_router

gylroute = Blueprint('gyl', __name__)
print("=============== 开始注册路由 =====================")

# ============================
# === 1. 注册医体融合项目路由 ===
# ============================
# print('1. 注册医体融合项目路由')
# gylroute.register_blueprint(sport_mng)


# # ============================
# # === 2. 注册工作站相关路由 ====
# # ============================
# print('2. 注册工作站相关路由')
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
print('3. 注册 app 版本管理路由')
gylroute.register_blueprint(app_version)


# ============================
# === 4. 注册危机值系统路由 ====
# ============================
print('4. 注册危机值系统路由')
gylroute.register_blueprint(cv)


# ============================
# === 5. 注册综合预约系统路由 ====
# ============================
print('5. 注册综合预约系统路由')
gylroute.register_blueprint(appt)

# ============================
# === 6. 注册病历解析系统路由 ====
# ============================
print('6. 注册病历解析系统路由')
gylroute.register_blueprint(parse)

print("=============== 路由注册完成 =====================")

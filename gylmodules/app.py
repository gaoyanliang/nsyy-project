import logging

from flask import Blueprint

from gylmodules import global_config
from gylmodules.a_special.special_router import special_system
from gylmodules.app_version.app_version_router import app_version
from gylmodules.critical_value.critical_value_router import cv
from gylmodules.file_system.file_router import file_system
from gylmodules.global_tools import setup_logging
from gylmodules.hospital_class.hosp_class_router import hosp_class
from gylmodules.hyperbaric_oxygen_therapy.hbot_router import hbot
from gylmodules.pacs_pdf.pacs_router import pacs_system
from gylmodules.parking.parking_router import parking
from gylmodules.pre_hospital_system.phs_router import phs
from gylmodules.questionnaire.question_router import question
from gylmodules.composite_appointment.composite_appointment_router import appt
from gylmodules.medical_record_analysis.parse_router import parse
from gylmodules.shift_change.shift_change_router import shift_change
from gylmodules.workstation.message.message_router import message_router
from gylmodules.workstation.mail.mail_router import mail_router

# 初始化日志
if global_config.run_in_local:
    setup_logging(log_file='my_app.log', level=logging.DEBUG)  # 可按需调整参数
else:
    setup_logging(log_file='my_app.log', level=logging.INFO)  # 可按需调整参数
logger = logging.getLogger(__name__)
logger.info("==================== 应用启动 =========================")

gylroute = Blueprint('gyl', __name__)
logger.info("=============== Start 开始注册路由 =====================")

# ============================
# === 1. 注册医体融合项目路由 ===
# ============================
# print('1. 注册医体融合项目路由')
# gylroute.register_blueprint(sport_mng)


# ============================
# === 2. 注册工作站相关路由 ====
# ============================
logger.info('2. 注册工作站相关路由')
workstation = Blueprint('workstation', __name__, url_prefix='/workstation')
# 2.1 注册消息管理路由
logger.info('    2.1 注册消息管理路由')
workstation.register_blueprint(message_router)
# 2.2 注册邮箱管理路由
logger.info('    2.2 注册邮箱管理路由')
workstation.register_blueprint(mail_router)

gylroute.register_blueprint(workstation)


# ============================
# === 3. 注册 app 版本管理  ====
# ============================
logger.info('3. 注册 app 版本管理路由')
gylroute.register_blueprint(app_version)


# ============================
# === 4. 注册危机值系统路由 ====
# ============================
logger.info('4. 注册危机值系统路由')
gylroute.register_blueprint(cv)


# ============================
# === 5. 注册综合预约系统路由 ====
# ============================
logger.info('5. 注册综合预约系统路由')
gylroute.register_blueprint(appt)


# ============================
# === 6. 注册病历解析系统路由 ====
# ============================
logger.info('6. 注册病历解析系统路由')
gylroute.register_blueprint(parse)


# ============================
# === 7. 注册高压氧系统路由 ====
# ============================
logger.info('7. 注册高压氧系统路由')
gylroute.register_blueprint(hbot)


# ============================
# === 8. 注册问卷调查系统路由 ===
# ============================
logger.info('8. 注册问卷调查系统路由')
gylroute.register_blueprint(question)


# ============================
# === 9. 注册院前急救系统路由 ===
# ============================
logger.info('9. 注册院前急救系统路由')
gylroute.register_blueprint(phs)


# ============================
# === 10. 注册院内讲座系统路由 ===
# ============================
logger.info('10. 注册院内讲座系统路由')
gylroute.register_blueprint(hosp_class)


# ============================
# === 12. 交接班系统路由 ===
# ============================
logger.info('12. 交接班系统路由')
gylroute.register_blueprint(parking)


# ============================
# === 13. 停车场系统路由 ===
# ============================
logger.info('13. 停车场系统路由')
gylroute.register_blueprint(shift_change)


# ============================
# === 14. 文件系统路由 ===
# ============================
logger.info('14. 文件系统路由')
gylroute.register_blueprint(file_system)


# ============================
# === 15. pacs pdf系统路由 ===
# ============================
logger.info('15. pacs pdf')
gylroute.register_blueprint(pacs_system)


# ============================
# === 16. 特殊系统路由 ===
# ============================
logger.info('16. 特殊系统路由')
gylroute.register_blueprint(special_system)

logger.info("=============== End 路由注册完成 =====================")

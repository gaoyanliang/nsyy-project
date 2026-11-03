import os

# MYSQL_URL = os.getenv(
#     "MYSQL_URL",
#     "mysql+pymysql://root:gyl.2015@127.0.0.1:3306/nsyy_gyl?charset=utf8mb4",
# )

MYSQL_URL = os.getenv(
    "MYSQL_URL",
    "mysql+pymysql://gyl:123456@127.0.0.1:3306/nsyy_gyl?charset=utf8mb4",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/2")

SCORE_VERSION = "v1.1-20261028"

RED_DIRECT_FIELDS = ["abandon_treatment", "auto_discharge"]
RED_DIRECT_LEAVE_MODE = "非医嘱离院"
ORANGE_DIRECT_FIELDS = ["patient_request_discharge"]

RISK_LOW = "低风险"
RISK_MEDIUM = "中风险"
RISK_HIGH = "高风险"
RISK_CRITICAL = "极高风险"

RISK_COLOR = {
    RISK_LOW: "绿色",
    RISK_MEDIUM: "黄色",
    RISK_HIGH: "橙色",
    RISK_CRITICAL: "红色",
}
RISK_RANK = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}
RISK_KEY = {RISK_LOW: "low", RISK_MEDIUM: "medium", RISK_HIGH: "high", RISK_CRITICAL: "critical"}

# Flask 启动配置
# RUN_IN_LOCAL = os.getenv("RUN_IN_LOCAL", "1") == "1"
# PORT_LOCAL = int(os.getenv("PORT_LOCAL", "8081"))
# PORT_PROD = int(os.getenv("PORT_PROD", "6094"))
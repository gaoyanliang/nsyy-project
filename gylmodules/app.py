from flask import Blueprint
from gylmodules.sport_mng.sport_mng import sport_mng

gylroute = Blueprint('gyl', __name__)

# 注册医体融合项目路由
gylroute.register_blueprint(sport_mng)

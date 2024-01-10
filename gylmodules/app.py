from flask import Flask
from gylmodules.sport_mng.sport_mng import sport_mng

app = Flask(__name__)

# 注册医体融合项目路由
app.register_blueprint(sport_mng, url_prefix='/gyl/sport_mng')

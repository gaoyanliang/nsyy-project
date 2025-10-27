import traceback

from flask import Blueprint, jsonify

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

app_version = Blueprint('app version', __name__, url_prefix='/app_version')


#  查询 app 版本信息
@app_version.route('/query_app_version/<type>/<detail>', methods=['GET', 'POST'])
def query_app_version(type, detail):
    try:
        version_info = query_app_version_from_db(type, detail)
    except Exception as e:
        print(f"mail_router.delete_mail: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': 'app 版本信息查询失败' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': 'app 版本信息查询成功',
        'data': version_info
    })


def query_app_version_from_db(type, detail):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select * from nsyy_gyl.app_version " \
                f"where type = '{type}' and detail = '{detail}' order by update_time desc limit 1"
    version_info = db.query_one(query_sql)
    del db

    return version_info

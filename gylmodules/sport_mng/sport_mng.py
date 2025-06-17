import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from gylmodules import global_config
from gylmodules.sport_mng import elec_health_card
from gylmodules.utils.db_utils import DbUtil
import xmltodict
import json

sport_mng = Blueprint('sport_mng', __name__, url_prefix='/sport_mng')
logger = logging.getLogger(__name__)


#  获取电子健康卡信息
@sport_mng.route('/gov_id_check', methods=['POST'])
def gov_id_check():
    json_data = json.loads(request.get_data().decode('utf-8'))
    id_card_num = json_data.get("id_card_num")
    # test 110101199004076650 吕测试
    res = elec_health_card.get_info_by_id(id_card_num=id_card_num)

    # return code: 0-成功 1-失败 -1-异常
    if res is not None:
        # Convert XML to Python dictionary
        xml_dict = xmltodict.parse(res)
        # Convert dictionary to JSON
        json_data = json.dumps(xml_dict, indent=2)
        logger.debug(f"Return data: {json_data}")

        # Load JSON data into a Python dictionary
        data_dict = json.loads(json_data)
        # Access the 'returncode' value
        returncode_value = data_dict['Response']['returncode']
        output = data_dict['Response']['output']
        logger.debug(f"Return code: {returncode_value}")

        if int(returncode_value) == 0 and output is not None:
            user_info = {
                "currentAddress": data_dict['Response']['output']['Response']['currentAddress'],
                "domicileAddress": data_dict['Response']['output']['Response']['domicileAddress'],
                "ehcId": data_dict['Response']['output']['Response']['ehcId'],
                "idCardNum": data_dict['Response']['output']['Response']['idCardNum'],
                "idCardType": data_dict['Response']['output']['Response']['idCardType'],
                "mainIndexId": data_dict['Response']['output']['Response']['mainIndexId'],
                "status": data_dict['Response']['output']['Response']['status'],
                "telephone": data_dict['Response']['output']['Response']['telephone'],
                "userName": data_dict['Response']['output']['Response']['userName'],
                "userSex": data_dict['Response']['output']['Response']['userSex'],
                "birthday": data_dict['Response']['output']['Response']['birthday'],
            }
            return jsonify({
                'code': 20000,
                'res': '该用户已申领电子健康卡',
                'data': user_info
            })
        else:
            return jsonify({
                'code': 50000,
                'res': '该用户未申领电子健康卡',
                'data': json_data
            })

    return jsonify({
        'code': 50000,
        'res': '验证失败，请检查电子健康卡服务是否正常',
        'data': '验证失败，请检查服务是否正常'
    })


#  创建电子健康卡
@sport_mng.route('/gov_id_create', methods=['POST'])
def gov_id_create():
    json_data = json.loads(request.get_data().decode('utf-8'))
    apply_type = json_data.get("apply_type")
    user_name = json_data.get("user_name")
    telephone = json_data.get("telephone")
    id_card_num = json_data.get("id_card_num")
    current_address = json_data.get("current_address")
    domicile_address = json_data.get("domicile_address")

    if apply_type is None:
        apply_type = '1'
    if user_name is None or telephone is None or id_card_num is None \
            or current_address is None or domicile_address is None:
        return jsonify({
            'code': 50000,
            'res': '入参异常，参数不能为 None',
            'data': '电子健康卡申领失败，请检查参数是否填写无误。'
        })

    res = elec_health_card.gov_id_create(apply_type=apply_type,
                                         user_name=user_name,
                                         telephone=telephone,
                                         id_card_num=id_card_num,
                                         current_address=current_address,
                                         domicile_address=domicile_address)
    # return code: 0-成功 1-失败 -1-异常
    if res is not None:
        # Convert XML to Python dictionary
        xml_dict = xmltodict.parse(res)
        # Convert dictionary to JSON
        json_data = json.dumps(xml_dict, indent=2)
        logger.debug(f"Return data: {json_data}")

        # Load JSON data into a Python dictionary
        data_dict = json.loads(json_data)
        # Access the 'returncode' value
        returncode_value = data_dict['Response']['returncode']
        logger.debug(f"Return code: {returncode_value}")
        message = data_dict['Response']['message']
        logger.debug(f"Return Message: {message}")
        output = data_dict['Response']['output']

        if int(returncode_value) == 0 and output is not None:
            user_info = {
                "currentAddress": data_dict['Response']['output']['Response']['currentAddress'],
                "domicileAddress": data_dict['Response']['output']['Response']['domicileAddress'],
                "ehcId": data_dict['Response']['output']['Response']['ehcId'],
                "idCardNum": data_dict['Response']['output']['Response']['idCardNum'],
                "idCardType": data_dict['Response']['output']['Response']['idCardType'],
                "mainIndexId": data_dict['Response']['output']['Response']['mainIndexId'],
                "telephone": data_dict['Response']['output']['Response']['telephone'],
                "userName": data_dict['Response']['output']['Response']['userName'],
                "userSex": data_dict['Response']['output']['Response']['userSex'],
                "birthday": data_dict['Response']['output']['Response']['birthday'],
            }
            return jsonify({
                'code': 20000,
                'res': message,
                'data': user_info
            })
        else:
            return jsonify({
                'code': 50000,
                'res': message,
                'data': json_data
            })

    return jsonify({
        'code': 50000,
        'res': '电子健康卡申领失败，请检查服务是否正常',
        'data': '电子健康卡申领失败，请检查服务是否正常'
    })


# 获取膳食列表
@sport_mng.route('/meal_list', methods=['POST'])
def meal_list():
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = 'select * from menu'
        meal_list = db.query_all(query_sql)
        del db
    except Exception as e:
        del db
        logger.error(f"sport_list: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '获取膳食列表失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '获取膳食列表成功',
        'data': meal_list
    })


# 获取运动列表
@sport_mng.route('/sport_list', methods=['POST'])
def sport_list():
    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = 'select * from nsyy_general.sports_actions'
        sport_list = db.query_all(query_sql)
        del db
    except Exception as e:
        del db
        logger.error(f"sport_list: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '获取运动列表失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '获取运动列表成功',
        'data': sport_list
    })


# 创建套餐
@sport_mng.route('/create_package', methods=['POST'])
def create_package():
    json_data = json.loads(request.get_data().decode('utf-8'))
    name = json_data.get("name")
    type = json_data.get("type")
    creator = json_data.get("creator")
    list = json_data.get("list")

    if list is None or list == '':
        return jsonify({
            'code': 50000,
            'res': '套餐数据录入失败, 套餐内没有数据, 请挑选合适的运动或膳食组成套餐',
            'data': ""
        })

    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        args = (name, int(type), int(creator), list)
        insert_sql = "INSERT INTO package (name,type,creator,list) VALUES (%s,%s,%s,%s)"
        last_rowid = db.execute(insert_sql, args, need_commit=True)
        if last_rowid == -1:
            return jsonify({
                'code': 50000,
                'res': '套餐数据录入失败',
                'data': ""
            })
        del db
    except Exception as e:
        del db
        logger.error(f"sport_list: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '套餐数据录入失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '套餐数据录入成功',
        'data': last_rowid
    })


# 读取标准套餐（医生调用）
@sport_mng.route('/read_package', methods=['POST'])
def read_package():
    json_data = json.loads(request.get_data().decode('utf-8'))
    # 医生编号
    doctor_id = json_data.get("doctor_id")
    # 套餐类别 0-运动套餐 1-餐饮套餐
    type = json_data.get("type")
    if doctor_id is None:
        return jsonify({
            'code': 50000,
            'res': '标准套餐查询失败，请提供医生 ID',
            'data': ""
        })

    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = "SELECT * FROM package WHERE creator = {} and type = {}".format(int(doctor_id), int(type))
        package_list = db.query_all(query_sql)

        # 读取运动/膳食详情
        if int(type) == 0:
            for package in package_list:
                datas = []
                groups = str(package.get("list")).split(';')
                for group in groups:
                    query_sql = "SELECT * FROM nsyy_general.sports_actions WHERE action_id in ({})".format(group)
                    details = db.query_all(query_sql)
                    datas.append(details)
                package['list'] = datas
        else:
            for package in package_list:
                datas = []
                groups = str(package.get("list")).split(';')
                for group in groups:
                    query_sql = "SELECT * FROM nsyy_gyl.menu WHERE id in ({})".format(group)
                    details = db.query_all(query_sql)
                    datas.append(details)
                package['list'] = datas
        del db
    except Exception as e:
        del db
        logger.error(f"read_package: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '标准套餐数据查询失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '标准套餐数据查询成功',
        'data': package_list
    })


# 读取患者餐饮列表/运动列表
@sport_mng.route('/read_patient_package', methods=['POST'])
def read_patient_package():
    json_data = json.loads(request.get_data().decode('utf-8'))
    # 患者编号
    patient_id = json_data.get("patient_id")
    # 套餐类别 0-运动套餐 1-餐饮套餐
    type = json_data.get("type")
    if patient_id is None:
        return jsonify({
            'code': 50000,
            'res': '患者运动/饮食列表查询失败，请提供患者 ID',
            'data': ""
        })

    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = "SELECT * FROM patient_package WHERE patient_id = {} and type = {}".format(int(patient_id),
                                                                                               int(type))
        patient_list = db.query_all(query_sql)

        # 读取运动/膳食详情
        if int(type) == 0:
            for list in patient_list:
                datas = []
                groups = str(list.get("list")).split(';')
                for group in groups:
                    query_sql = "SELECT * FROM nsyy_general.sports_actions WHERE action_id in ({})".format(group)
                    details = db.query_all(query_sql)
                    datas.append(details)
                list['list'] = datas
                query_sql = "SELECT * FROM nsyy_gyl.package WHERE id = {}".format(int(list.get("from_package")))
                package = db.query_one(query_sql)
                list['name'] = package.get('name')
        else:
            for list in patient_list:
                datas = []
                groups = str(list.get("list")).split(';')
                for group in groups:
                    query_sql = "SELECT * FROM nsyy_gyl.menu WHERE id in ({})".format(group)
                    details = db.query_all(query_sql)
                    datas.append(details)
                list['list'] = datas
                query_sql = "SELECT * FROM nsyy_gyl.package WHERE id = {}".format(int(list.get("from_package")))
                package = db.query_one(query_sql)
                list['name'] = package.get('name')
        del db
    except Exception as e:
        del db
        logger.error(f"read_patient_package: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '患者运动/饮食列表查询失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '患者运动/饮食列表查询成功',
        'data': patient_list
    })


# 医生给患者分配套餐
@sport_mng.route('/allocation_package', methods=['POST'])
def allocation_package():
    json_data = json.loads(request.get_data().decode('utf-8'))
    # 套餐编号
    package_id = json_data.get("package_id")
    # 患者编号
    patient_id = json_data.get("patient_id")
    type = json_data.get("type")
    start_date = json_data.get("start_date")
    if start_date is None:
        start_date = datetime.date.today()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = "SELECT * FROM package WHERE id = {} ".format(int(package_id))
        package = db.query_all(query_sql)
        if package is None or len(package) == 0:
            return jsonify({
                'code': 50000,
                'res': '套餐分配失败, 所选套餐不存在',
                'data': ""
            })

        args = (int(patient_id), int(package_id), start_date, package[0].get("list"), int(type))
        insert_sql = "INSERT INTO patient_package (patient_id,from_package,start_date,list,type) VALUES (%s,%s,%s,%s,%s)"
        last_rowid = db.execute(insert_sql, args, need_commit=True)
        if last_rowid == -1:
            return jsonify({
                'code': 50000,
                'res': '套餐分配失败',
                'data': ""
            })

        del db
    except Exception as e:
        del db
        logger.error(f"allocation_package: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '套餐分配失败',
            'data': ""
        })

    return jsonify({
        'code': 20000,
        'res': '套餐分配成功',
        'data': last_rowid
    })


# 患者修改运动/膳食列表
@sport_mng.route('/update_patient_list', methods=['POST'])
def update_patient_list():
    json_data = json.loads(request.get_data().decode('utf-8'))
    # 列表编号
    list_id = json_data.get("list_id")
    # 患者编号
    patient_id = json_data.get("patient_id")
    list = json_data.get("list")
    start_date = json_data.get("start_date")

    if start_date is not None:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    try:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)

        query_sql = "SELECT * FROM nsyy_gyl.patient_package WHERE id = {} ".format(int(list_id))
        patient_list = db.query_one(query_sql)
        if patient_list is None:
            return jsonify({
                'code': 50000,
                'res': '患者列表修改失败，当前患者不存在该列表，请检查',
                'data': ""
            })
        if patient_list.get('patient_id') != int(patient_id):
            return jsonify({
                'code': 50000,
                'res': '患者列表修改失败，当前患者修改的不是本人的运动/饮食列表',
                'data': ""
            })

        if list is not None and start_date is not None:
            update_sql = "UPDATE nsyy_gyl.patient_package SET start_date = %s , list = %s WHERE id = %s"
            args = (start_date, list, list_id)
        elif list is None and start_date is None:
            return jsonify({
                'code': 50000,
                'res': '患者列表修改失败，请提供正确的参数（列表和开始时间必须提供一个）',
                'data': ''
            })
        elif start_date is None:
            update_sql = "UPDATE nsyy_gyl.patient_package SET list = %s WHERE id = %s"
            args = (list, list_id)
        else:
            update_sql = "UPDATE nsyy_gyl.patient_package SET start_date = %s WHERE id = %s"
            args = (start_date, list_id)

        db.execute(update_sql, args, need_commit=True)
        del db
    except Exception as e:
        del db
        logger.error(f"update_patient_list: An unexpected error occurred: {e}")
        return jsonify({
            'code': 50000,
            'res': '患者列表更新失败',
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '患者列表更新成功',
        'data': ''
    })


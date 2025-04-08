import json
from flask import jsonify

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from datetime import datetime, timedelta


def hosp_class(json_data):
    func_type = json_data.get('type')
    json_data.pop('type')
    if func_type == 'class_dtl':
        return class_dtl(int(json_data.get('class_id')), int(json_data.get('pers_id')))
    elif func_type == 'class_apply':
        return class_apply(json_data)
    elif func_type == 'class_apply_list':
        return class_apply_list()
    elif func_type == 'class_appr':
        return class_appr(json_data.get('class_id'))
    elif func_type == 'class_list':
        return class_list(json_data.get('date_str'), json_data.get('period'))
    elif func_type == 'class_join':
        return class_join(json_data.get('cp_key'), json_data.get('pers_id'), json_data.get('pers_name'),
                          json_data.get('pers_status'), json_data.get('class_id'))
    elif func_type == 'class_checkin':
        return class_checkin(json_data.get('cp_key'))
    elif func_type == 'class_comments':
        return class_comments(json_data.get('class_id'), json_data.get('pers_id'), json_data.get('rate'))
    elif func_type == 'class_his':
        return class_his(json_data.get('pers_id'), json_data.get('his_type'), json_data.get('page_no'),
                         json_data.get('page_size'), json_data.get('start_d'), json_data.get('end_d'))
    else:
        return jsonify({'code': 50000, 'res': 'type is illegal'})


def class_dtl(class_id, pers_id):
    """
    获取讲座明细
    :param class_id:
    :param pers_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    class_detail = db.query_one(f"""select c.*, coalesce(p.pers_id, 0) as pers_id, coalesce(p.pers_name, '') 
                            as pers_name, coalesce(p.pers_status, -1) as pers_status, coalesce(r.ques1_rate, -1) 
                            as ques1_rate from nsyy_gyl.hosp_class c 
                            left join nsyy_gyl.hosp_class_pers p on c.class_id = p.class_id and p.pers_id = {pers_id}
                            left join nsyy_gyl.hosp_class_rate r on c.class_id = r.class_id and r.pers_id = {pers_id}
                            where c.class_id = {class_id}
                            """)
    del db

    if class_detail and class_detail.get('class_att'):
        class_detail['class_att'] = json.loads(class_detail.get('class_att'))

    return jsonify({'code': 20000, 'res': '讲座明细查询成功', 'data': class_detail})


def class_apply(apply_data):
    """
    讲座申请/更新 申请无 class_id
    :param apply_data:
    :return:
    """
    class_id = apply_data.get('class_id')
    new_class_start = apply_data.get('class_start')
    new_class_end = apply_data.get('class_end')

    if apply_data.get('class_att'):
        apply_data['class_att'] = json.dumps(apply_data.get('class_att'))
    else:
        apply_data.pop('class_att')
    if 'class_status' not in apply_data:
        apply_data['class_status'] = 1

    # 验证输入时间格式
    try:
        new_start_dt = datetime.strptime(new_class_start, '%Y-%m-%d %H:%M:%S')
        new_end_dt = datetime.strptime(new_class_end, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({'code': 50000, 'res': '输入的时间格式不正确，应为 "YYYY-MM-DD HH:MM:SS"'})

    # 确保新课程的开始时间早于结束时间
    if new_start_dt >= new_end_dt:
        return jsonify({'code': 50000, 'res': '新课程的开始时间必须早于结束时间'})

    new_date = datetime.strptime(new_class_start, '%Y-%m-%d %H:%M:%S').date().__str__()

    # 构建查询语句，检查时间冲突和间隔不足30分钟的情况  -- 检查与已有课程的时间交叉
    check_query = f"""SELECT COUNT(*) > 0 AS has_conflict FROM nsyy_gyl.hosp_class WHERE class_status = 2 and 
            DATE(class_start) = '{new_date}' and ('{new_class_start}' < class_end AND '{new_class_end}' > class_start)
       """
    if class_id:
        apply_data.pop('class_id')
        check_query += f" AND class_id != {class_id}"
    if apply_data.get('class_addr'):
        check_query += f" AND class_addr = '{apply_data.get('class_addr')}'"

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    has_conflict = db.query_one(check_query)
    if has_conflict.get('has_conflict') > 0:
        del db
        return jsonify({'code': 50000, 'res': '新课程与已批复课程存在时间存在冲突或讲座地址冲突'})

    if class_id:
        # 生成 SET 部分的 SQL 语句
        set_clause = ', '.join([f"{key} = %s" for key in apply_data.keys()])
        apply_sql = f"UPDATE nsyy_gyl.hosp_class SET {set_clause} WHERE class_id = %s"
        params = tuple(apply_data.values()) + (int(class_id),)
        db.execute(apply_sql, params, need_commit=True)
    else:
        apply_sql = f"INSERT INTO nsyy_gyl.hosp_class ({','.join(apply_data.keys())}) " \
                    f"VALUES {str(tuple(apply_data.values()))}"
        last_row = db.execute(sql=apply_sql, need_commit=True)
        if last_row == -1:
            del db
            return jsonify({'code': 50000, 'res': '新增讲座申请失败'})
    del db

    return jsonify({'code': 20000, 'res': '讲座申请/更新成功'})


def class_apply_list():
    """
    获取待批复讲座清单 （仅 黄满利 可以看到这个列表，前端控制）
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    classes = db.query_all(f"select * from nsyy_gyl.hosp_class where class_status = 1")
    del db

    return jsonify({'code': 20000, 'res': '待批复讲座清单查询成功', 'data': classes})


def class_appr(class_id):
    """
    讲座批复
    :param class_id:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    class_data = db.query_one(f"select * from nsyy_gyl.hosp_class where class_id = {int(class_id)}")
    if not class_data:
        del db
        return jsonify({'code': 50000, 'res': '该讲座不存在'})

    class_date = class_data.get('class_start').strftime('%Y-%m-%d %H:%M:%S')
    # 构建查询语句，检查时间冲突和间隔不足30分钟的情况  -- 检查与已有课程的时间交叉
    check_query = f"""SELECT COUNT(*) > 0 AS has_conflict FROM nsyy_gyl.hosp_class WHERE class_status = 2 and 
            DATE(class_start) = '{class_date}' and ('{class_data.get('class_start').strftime('%Y-%m-%d %H:%M:%S')}' < 
            class_end AND '{class_data.get('class_end').strftime('%Y-%m-%d %H:%M:%S')}' > class_start)
       """
    if class_data.get('class_addr'):
        check_query += f" AND class_addr = '{class_data.get('class_addr')}'"

    has_conflict = db.query_one(check_query)
    if has_conflict.get('has_conflict') > 0:
        del db
        return jsonify({'code': 50000, 'res': '新课程与已批复课程存在时间存在冲突或讲座地址冲突'})

    db.execute(f"update nsyy_gyl.hosp_class set class_status = 2 "
               f"where class_id = {int(class_id)} and class_status = 1", need_commit=True)
    del db
    return jsonify({'code': 20000, 'res': '讲座批复成功'})


def class_list(date_str, period):
    """
    获取已批复讲座清单
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    end_date = start_date + timedelta(days=period)
    classes = db.query_all(f"select * from nsyy_gyl.hosp_class where class_status = 2 "
                           f"and class_start >= '{start_date}' and class_start < '{end_date}'")
    del db

    return jsonify({'code': 20000, 'res': '已批复讲座清单查询成功', 'data': classes})


def class_join(cp_key, pers_id, pers_name, pers_status, class_id):
    """
    参与/取消讲座
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    target_class = db.query_one(f"select * from nsyy_gyl.hosp_class where class_id = {int(class_id)}")
    if not target_class:
        del db
        return jsonify({'code': 50000, 'res': '该讲座不存在'})
    if target_class.get('class_end') < datetime.now():
        del db
        return jsonify({'code': 50000, 'res': '该讲座已结束'})

    insert_sql = """
            INSERT INTO nsyy_gyl.hosp_class_pers (cp_key, pers_id, pers_name, pers_status, class_id) 
            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE cp_key = VALUES(cp_key), pers_id = VALUES(pers_id), 
            pers_name = VALUES(pers_name), pers_status = VALUES(pers_status), class_id = VALUES(class_id)
    """
    args = (cp_key, pers_id, pers_name, pers_status, class_id)
    last_rows = db.execute(insert_sql, args, need_commit=True)
    del db

    if last_rows == -1:
        return jsonify({'code': 50000, 'res': '报名/取消异常'})

    return jsonify({'code': 20000, 'res': '报名/取消成功'})


def class_checkin(cp_key):
    """
    签到
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    old_checkin = db.query_one(f"select * from nsyy_gyl.hosp_class_pers where cp_key = '{cp_key}'")
    if not old_checkin:
        return jsonify({'code': 50000, 'res': '签到失败，请先报名'})
    if old_checkin.get('pers_status') == 2:
        return jsonify({'code': 50000, 'res': '签到失败，你已经签过到了'})

    affected_rows = db.execute(f"update nsyy_gyl.hosp_class_pers set pers_status = 2 where cp_key = '{cp_key}'",
                               need_commit=True)
    del db
    return jsonify({'code': 20000, 'res': '签到成功'})


def class_comments(class_id, pers_id, rate):
    """
    评价
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    cp_key = f"{class_id}_{pers_id}"
    old_checkin = db.query_one(f"select * from nsyy_gyl.hosp_class_pers where cp_key = '{cp_key}'")
    if not old_checkin:
        return jsonify({'code': 50000, 'res': '评价失败，请先报名'})
    if old_checkin.get('pers_status') < 3:
        return jsonify({'code': 50000, 'res': '评价失败，请先签过'})

    insert_sql = """
            INSERT INTO nsyy_gyl.hosp_class_rate (class_id, pers_id, ques1_rate) 
            VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE class_id = VALUES(class_id), pers_id = VALUES(pers_id), 
            ques1_rate = VALUES(ques1_rate)
    """
    last_row = db.execute(insert_sql, (class_id, pers_id, rate), need_commit=True)

    if last_row == -1:
        return jsonify({'code': 50000, 'res': '评价失败'})

    # 评价成功 修改状态
    affected_rows = db.execute(f"update nsyy_gyl.hosp_class_pers set pers_status = 3 where cp_key = '{cp_key}'",
                               need_commit=True)
    del db

    return jsonify({'code': 20000, 'res': '评价成功'})


def class_his(pers_id, his_type, page_no, page_size, start_d, end_d):
    """
    开讲记录 his_type: 1 主讲清单/ 2参与清单
    :return:
    """
    condition_sql = ''
    if start_d and end_d:
        condition_sql = f"and DATE(class_start) BETWEEN '{start_d}' AND '{end_d}' "

    if int(his_type) == 1:
        query_sql = f"select * from nsyy_gyl.hosp_class where owner = {pers_id} {condition_sql} order by class_id desc"
    elif int(his_type) == 2:
        query_sql = f"select * from nsyy_gyl.hosp_class where class_id in (select class_id " \
                    f"from hosp_class_pers where pers_id = {pers_id}) {condition_sql} order by class_id desc"
    else:
        return jsonify({'code': 50000, 'res': f'查询异常 his_type = {his_type} is illegal'})

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    classes = db.query_all(query_sql)
    del db

    total = len(classes)
    if page_no and page_size:
        start_index = (page_no - 1) * page_size
        end_index = start_index + page_size
        classes = classes[start_index:end_index]

    return jsonify({'code': 20000, 'res': '查询成功', 'data': classes, 'total': total})

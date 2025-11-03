import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from gylmodules import global_config
from gylmodules.file_system import file_config
from gylmodules.utils.db_utils import DbUtil

logger = logging.getLogger(__name__)


# ==================================================
# ================用户组 & 权限管理 ===================
# ==================================================


"""新建或更新群组"""


def create_or_update_group(json_data):
    group_id = json_data.get("group_id")
    user_id = json_data.get("user_id", 0)
    group_name = json_data.get("group_name", '')
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if group_id:
        if not db.query_one(f"select * from nsyy_gyl.file_user_permission "
                            f"where group_id = {group_id} and user_id = {user_id}"):
            del db
            raise Exception("您没有编辑当前群组的权限")

        # 更新群组 名称
        sql = f"""UPDATE nsyy_gyl.file_user_group SET group_name = '{group_name}' WHERE group_id = {group_id}"""
        db.execute(sql, need_commit=True)
    else:
        # 新增群组
        sql = """INSERT INTO nsyy_gyl.file_user_group (group_name, owner_id, owner, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s) """
        last_rowid = db.execute(sql, (json_data.get("group_name", ''), user_id, json_data.get("user_name", ''),
                                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                need_commit=True)
        if last_rowid == -1:
            del db
            raise Exception("群组添加失败，请稍后重试")
        # 同时添加权限
        db.execute(f"""INSERT INTO nsyy_gyl.file_user_permission (name, group_id, user_id, user_name) 
        VALUES (%s, %s, %s, %s)""", (group_name, last_rowid, user_id, json_data.get('user_name', '')), need_commit=True)
        db.execute(f"""INSERT INTO nsyy_gyl.file_user_group_membership (group_id, user_id, user_name) 
        VALUES (%s, %s, %s)""", (last_rowid, user_id, json_data.get('user_name', '')), need_commit=True)
    del db


"""添加/移除群组成员"""


def add_group_member(op_type, group_id, members, user_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if not db.query_one(f"select * from nsyy_gyl.file_user_permission "
                        f"where group_id = {group_id} and user_id = {user_id}"):
        del db
        raise Exception("您没有编辑当前群组的权限")

    if op_type == "add":
        # 添加群组成员
        args = [(group_id, item.get('user_id', 0), item.get('user_name', '')) for item in members]
        insert_sql = """INSERT INTO nsyy_gyl.file_user_group_membership (group_id, user_id, user_name) 
            VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE user_name = VALUES(user_name)"""
        db.execute_many(insert_sql, args, need_commit=True)
    elif op_type == "remove":
        # 移除群组成员
        args = [str(item.get('user_id', 0)) for item in members]
        delete_sql = f"""DELETE FROM nsyy_gyl.file_user_group_membership where group_id = {group_id} 
        and user_id in ({','.join(args)})"""
        db.execute(delete_sql, need_commit=True)
    else:
        raise Exception("操作类型错误")
    del db


"""查询加入的所有群组所有的群组"""


def query_group_list(user_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    groups = db.query_all(f"select * from nsyy_gyl.file_user_group where group_id in "
                          f"(select group_id from file_user_group_membership where user_id = '{user_id}')")
    del db
    return groups


"""查询群组成员"""


def query_group_member(group_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    members = db.query_all(f"select * from nsyy_gyl.file_user_group_membership where group_id = {group_id}")
    del db
    return members


"""给科室/群组添加管理员"""


def add_admin(json_data):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    p_type = json_data.get("p_type")
    p_id = json_data.get("p_id")
    p_name = json_data.get("p_name", '')
    user_id = json_data.get("user_id")
    condition_sql = f"and dept_id = {p_id}" if p_type == "dept" else f"and group_id = {p_id}"
    if not db.query_one(f"select * from nsyy_gyl.file_user_permission "
                        f"where user_id = {user_id} {condition_sql}"):
        del db
        raise Exception("权限不足，请联系科室/群组文档管理员操作")

    users = json_data.get("users", [])
    args = [(p_name, p_id, item.get('user_id', 0), item.get('user_name', '')) for item in users]
    if p_type == "dept":
        insert_sql = """INSERT INTO nsyy_gyl.file_user_permission (name, dept_id, user_id, user_name) 
            VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE user_name = VALUES(user_name),
             user_name = VALUES(user_name)"""
    elif p_type == "group":
        insert_sql = """INSERT INTO nsyy_gyl.file_user_permission (name, group_id, user_id, user_name) 
                VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE user_name = VALUES(user_name),
                 user_name = VALUES(user_name)"""
    else:
        raise Exception("操作类型错误")
    db.execute_many(insert_sql, args, need_commit=True)
    del db


"""查询科室文档管理配置列表"""


def dept_admin_list():
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    dept_admins = db.query_all("select * from nsyy_gyl.file_user_permission where dept_id is not null")
    del db
    return dept_admins


# ==================================================
# ================  目录 文件 管理 ===================
# ==================================================


"""查看文件历史版本"""


def query_file_history(document_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    documents = db.query_all(f"select * from nsyy_gyl.file_document_version "
                             f"where document_id = {document_id} and is_deleted = 0")
    del db
    return documents


"""新建文件夹"""


def new_folder(json_data):
    # 文件类型 1=个人 2=组别 3=科室 4=院级
    file_type = json_data.get("file_type")
    owner_id = json_data.get("owner_id")
    parent_id = json_data.get("parent_id")

    # 仅科室文档管理员/群组管理员 可创建文件夹
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if parent_id == -1:
        query_sql = f"select * from nsyy_gyl.file_user_permission where user_id = {owner_id}"
    else:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
        on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {parent_id}
        union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
        on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {parent_id}
        """
    permission = db.query_all(query_sql)
    if not permission:
        del db
        raise Exception("权限不足，无法新建目录")

    insert_sql = """INSERT INTO nsyy_gyl.file_folder (file_type, name, parent_id, root_id, owner_id, owner, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    db.execute(insert_sql, (file_type, json_data.get("name"), parent_id, json_data.get("root_id"), owner_id,
                            json_data.get("owner"), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)
    del db


"""根目录添加权限 / 更新文件夹名字 / 删除文件夹"""


def update_folder(json_data):
    folder_id = json_data.get("folder_id")
    owner_id = json_data.get("owner_id")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    folder = db.query_one(f"select * from nsyy_gyl.file_folder where folder_id = {folder_id}")
    if not folder or folder.get('is_deleted', 0):
        del db
        raise Exception("该目录已删除")
    if folder.get('owner_id', 0) != owner_id:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法新增权限")

    if json_data.get('folder_name', ''):
        db.execute(f"UPDATE nsyy_gyl.file_folder SET name = '{json_data.get('folder_name')}' "
                   f"WHERE folder_id = {folder_id}", need_commit=True)

    if int(json_data.get('is_deleted', 0)):
        db.execute(f"UPDATE nsyy_gyl.file_folder SET is_deleted = 1 WHERE folder_id = {folder_id}", need_commit=True)

    if json_data.get('groups', []):
        args = []
        for item in json_data.get('groups', []):
            args.append((folder_id, item.get('group_id', 0), 0, item.get('group_name', '')))
        insert_sql = """INSERT INTO nsyy_gyl.file_folder_permission (folder_id, group_id, dept_id, name) 
                    VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE name = VALUES(name)"""
        db.execute_many(insert_sql, args, need_commit=True)

    if json_data.get('depts', []):
        args = []
        for item in json_data.get('depts', []):
            args.append((folder_id, 0, item.get('dept_id', 0), item.get('dept_name', '')))
        insert_sql = """INSERT INTO nsyy_gyl.file_folder_permission (folder_id, group_id, dept_id, name) 
                    VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE name = VALUES(name)"""
        db.execute_many(insert_sql, args, need_commit=True)

    del db


"""移动文件夹"""


def move_folder(json_data):
    source_root_id = json_data.get("source_root_id")
    target_root_id = json_data.get("target_root_id")
    owner_id = json_data.get("owner_id")
    folder_id = json_data.get("folder_id")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    folder = db.query_one(f"select * from nsyy_gyl.file_folder where folder_id = {folder_id}")
    if not folder or folder.get('is_deleted', 0):
        del db
        raise Exception("该目录已删除")
    if folder.get('owner_id', 0) != owner_id:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {source_root_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {source_root_id}
                """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法移动目录")

    if source_root_id != target_root_id:
        # 如果当前根目录和目标根目录不一致，需要判断是否有目标根目录的操作权限
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                        on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {target_root_id}
                        union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                        on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {target_root_id}
                        """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法移动目录")

    db.execute(f"UPDATE nsyy_gyl.file_folder SET parent_id = {json_data.get('target_folder_id')}, "
               f"root_id = {target_root_id} WHERE folder_id = {folder_id}",
               need_commit=True)
    del db


"""上传文件 文件由前端调用老接口上传，这里仅保存上传后的路径 """


def upload_file(json_data):
    owner_id = json_data.get("owner_id")
    folder_id = json_data.get("folder_id")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    folder = db.query_one(f"select * from nsyy_gyl.file_folder where folder_id = {folder_id}")
    if not folder or folder.get('is_deleted', 0):
        del db
        raise Exception("该目录已删除")
    if folder.get('owner_id', 0) != owner_id:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法上传文件")

    # file_path = _upload_file(file)
    # if not file_path:
    #     del db
    #     raise Exception("文件上传失败")

    insert_sql = """INSERT INTO nsyy_gyl.file_document (type, name, folder_id, storage_path, owner_id, 
                    owner, is_publish, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    db.execute(insert_sql, (json_data.get('type'), json_data.get('name'), json_data.get('folder_id'),
                            json_data.get('storage_path'), owner_id, json_data.get('owner'),
                            json_data.get('is_publish'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)

    del db


"""更新文件名称/发布状态"""


def update_file(json_data):
    owner_id = json_data.get("owner_id")
    folder_id = json_data.get("folder_id")
    document_id = json_data.get("document_id")

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    document = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
    if not document or document.get('is_deleted', 0):
        del db
        raise Exception("该目录已删除")
    if not document or document.get('owner_id', 0) != owner_id:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {folder_id}
                """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法更新文件")

    condition_sql = ""
    if json_data.get('file_name', ''):
        condition_sql = f"name = '{json_data.get('file_name')}'"
    if 'is_publish' in json_data:
        condition_sql += f", is_publish = '{json_data.get('is_publish')}'" \
            if condition_sql else f"is_publish = '{json_data.get('is_publish')}'"
    db.execute(
        f"UPDATE nsyy_gyl.file_document SET {condition_sql} WHERE document_id = {document_id}",
        need_commit=True)

    del db


"""移动文件"""


def move_file(json_data):
    source_root_id = json_data.get("source_root_id")
    target_root_id = json_data.get("target_root_id")
    owner_id = json_data.get("owner_id")
    document_id = json_data.get("document_id")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    document = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
    if document and document.get('is_deleted', 0):
        del db
        raise Exception("该目录已删除")
    if not document or document.get('owner_id', 0) != owner_id:
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {source_root_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {source_root_id}
                """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法移动文件")

    if source_root_id != target_root_id:
        # 如果当前根目录和目标根目录不一致，需要判断是否有目标根目录的操作权限
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                        on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {target_root_id}
                        union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                        on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {target_root_id}
                        """
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法移动文件")

    db.execute(f"UPDATE nsyy_gyl.file_document SET folder_id = {json_data.get('target_folder_id')} "
               f" WHERE document_id = {document_id}",
               need_commit=True)
    del db


"""查询当前目录内容"""


def query_file_list(json_data):
    parent_id = json_data.get("folder_id", -1)
    owner_id = json_data.get("owner_id")
    dept_id = json_data.get("dept_id")
    file_type = json_data.get("file_type")
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    if parent_id == -1:
        # 没有父目录，则查询时需要选择一个文件类型
        query_sql = f"""
            select * from nsyy_gyl.file_folder where folder_id in (
            select a.folder_id from nsyy_gyl.file_folder_permission a join nsyy_gyl.file_user_permission b 
            on a.group_id = b.group_id where b.user_id = {owner_id}  union
            select a.folder_id from nsyy_gyl.file_folder_permission a join nsyy_gyl.file_user_permission b 
            on a.dept_id = b.dept_id where b.user_id = {owner_id}) and is_deleted = 0 and file_type = {file_type}
        """
        folders = db.query_all(query_sql)
        documents = []
    else:
        root_id = json_data.get("root_id")
        query_sql = f"""select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.group_id = b.group_id where a.user_id = {owner_id} and b.folder_id = {root_id}
                union select a.* from nsyy_gyl.file_user_permission a join nsyy_gyl.file_folder_permission b 
                on a.dept_id = b.dept_id where a.user_id = {owner_id} and b.folder_id = {root_id}"""
        permission = db.query_all(query_sql)
        if not permission:
            del db
            raise Exception("权限不足，无法访问当前目录")
        folders = db.query_all(f"select * from nsyy_gyl.file_folder where parent_id = {parent_id} and is_deleted = 0")
        documents = db.query_all(f"select * from nsyy_gyl.file_document "
                                 f"where folder_id = {json_data.get('folder_id')} and is_deleted = 0")

    del db
    return {"folders": folders, "documents": documents}


"""把平铺的目录列表转成树"""


def build_tree(type, root_id):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    folders = db.query_all(f"select * from nsyy_gyl.file_folder where file_type = {type} and is_deleted = 0")
    del db

    # 建立 parent_id -> children 的映射
    children_map: Dict[int, List[Dict[str, Any]]] = {}
    id_map: Dict[int, Dict[str, Any]] = {}

    for f in folders:
        id_map[f["folder_id"]] = f
        children_map.setdefault(f["parent_id"], []).append(f)

    # 递归构建
    def build_node(node: Dict[str, Any]) -> Dict:
        kids = [build_node(child) for child in children_map.get(node["folder_id"], [])]
        return {
            "folder_id": node['folder_id'], "name": node['name'],
            "parent_id": node['parent_id'], "children": kids
        }

    # 找出根节点
    roots = [build_node(node) for node in children_map.get(root_id, [])]
    return roots


def get_folder_tree(root_id):
    try:
        tree = build_tree(4, root_id)
        return tree
    except Exception as e:
        print(e)

# tree = get_folder_tree(1)

# print(tree)


def _upload_file(file):
    if not file:
        return ''
    try:
        path = "/Users/gaoyanliang/nsyy/nsyy-project/gylmodules/file_system/upload" \
            if global_config.run_in_local else f"/home/n/{datetime.now().strftime('%Y%m%d')}"
        import os
        # 确保上传目录存在
        path = file_config.upload_path if global_config.run_in_local else f"{file_config.upload_path}/{datetime.now().strftime('%Y%m%d')}"
        if not os.path.exists(path):
            os.makedirs(path)

        # 安全保存文件
        file_path = os.path.join(path, file.filename)
        file.save(file_path)
        return file_path
    except Exception as e:
        logger.error(f"文件上传失败 {e}")
    return ''

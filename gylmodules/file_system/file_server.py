import os
import paramiko
import json
import logging
from datetime import datetime

from gylmodules import global_config
from gylmodules.file_system import file_config
from gylmodules.file_system.file_config import PERM_FIELDS
from gylmodules.utils.db_utils_new import DbUtil

logger = logging.getLogger(__name__)

# 1.个人文档（file_type=1），所有人都可以在个人文档中创建文件夹&上传文件 且默认有所创建文件夹和上传文件的所有权限，同时也可以给其他人赋予权限
# 2.群组文档（file_type=2）,根目录只有群主和群管理员 可以创建文件夹和上传文件，创建的文件夹该群组的人默认有查看的权限，上传的文件该群组的人默认有查看和下载的权限，群主和群管理员可以给其他人赋予权限
# 3.科室文档（file_type=3）根目录只有科主任或科室文档管理员 可以创建文件夹和上传文件，创建的文件夹该科室的人默认有查看的权限，上传的文件该科室的人默认有查看和下载的权限科主任和科室文档管理员可以给其他人赋予权限
# 4.院级文档（file_type=4）院级文档只有指定的某些人可以创建文件夹和上传文件，这些人可以给其他人赋予权限



# ==================================================
# ================  科室权限管理 ===================
# ==================================================

"""给科室添加管理员"""


def op_admin(json_data):
    dept_id = json_data.get("dept_id")
    dept_name = json_data.get("dept_name", '')
    pers_id = json_data.get("user_id")
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        sql = f"select * from nsyy_gyl.file_dept_permission where pers_id = '{pers_id}' and dept_id = '{dept_id}'"
        if not db.query_one(sql):
            raise Exception("权限不足，请联系科室文档管理员操作")

        members = json_data.get("members", [])
        if json_data.get("op_type") == "remove":
            # 移除管理员
            user_ids = ','.join([f"'{str(item.get('pers_id'))}'" for item in members])
            delete_sql = f"""DELETE FROM nsyy_gyl.file_dept_permission where dept_id = '{dept_id}' and pers_id in ({user_ids})"""
            db.execute(delete_sql, need_commit=True)
        elif json_data.get("op_type") == "add":
            args = [(dept_id, dept_name, item.get('pers_id'), item.get('pers_name')) for item in members]
            insert_sql = """INSERT INTO nsyy_gyl.file_dept_permission (dept_id, dept_name, pers_id, pers_name) 
                                VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE pers_id = VALUES(pers_id),
                                 dept_id = VALUES(dept_id), dept_name = VALUES(dept_name), pers_name = VALUES(pers_name)"""
            db.execute_many(insert_sql, args, need_commit=True)
        else:
            raise Exception("操作类型错误")



"""查询科室文档管理配置列表"""


def dept_admin_list(dept_id):
    # dept_id = -1 查询院级
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        dept_admins = db.query_all(f""" select * from nsyy_gyl.file_dept_permission where dept_id = '{dept_id}' """)
        return dept_admins




# ==================================================
# ================  目录 文件 管理 ===================
# ==================================================


"""查看文件历史版本"""


def query_file_history(document_id):
    """这一步 不需要权限判断，由上一步判断"""
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        documents = db.query_all(f"select * from nsyy_gyl.file_document_version "
                                 f"where document_id = {document_id} and is_deleted = 0")
        return documents


"""新建文件夹"""


def new_folder(json_data):
    # 文件类型 1=个人 2=科室 3=群组
    file_type = json_data.get("file_type")
    owner_id = json_data.get("owner_id")
    parent_id = json_data.get("parent_id")
    owner_depts = json_data.get("owner_depts")
    group_id = json_data.get("group_id")  # 新增参数，用于群组文档

    # ---- 根目录权限检查 ----
    if parent_id == -1:
        if not check_root_permission(owner_id, file_type, owner_depts, group_id):
            raise Exception("您无权在此根目录下创建文件夹")
    else:
        # 非根目录：检查父文件夹的编辑权限
        permissions = get_effective_permission(owner_id, owner_depts, folder_id=parent_id)
        if not permissions.get("can_edit"):
            raise Exception("权限不足，无父目录的编辑权限")

    # 仅科室文档管理员/群组管理员 可创建文件夹
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if parent_id != -1:
            # 如果要创建子目录 判读是否有父目录的编辑权限
            permissions = get_effective_permission(owner_id, owner_depts, folder_id=parent_id)
            if not permissions["can_edit"]:
                raise Exception("权限不足，无父目录的编辑权限, 无法创建子文件夹")

        # 1. 插入文件夹
        insert_sql = """INSERT INTO nsyy_gyl.file_folder (file_type, name, parent_id, root_id, 
                        owner_id, owner, created_at, updated_at, group_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        folder_id = db.execute(insert_sql, (file_type, json_data.get("name"), parent_id, -1, owner_id,
                                json_data.get("owner"), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), group_id), need_commit=True)

        # 2. 获取刚插入的文件夹ID
        if folder_id == -1:
            raise Exception("文件夹插入失败")

        # 3. 给创建者赋予该文件夹的所有权限（can_manage 也加上，虽然业务未用，但保持完整）
        perm_sql = """INSERT INTO nsyy_gyl.file_folder_permission 
                      (folder_id, user_id, group_id, dept_id, can_view, can_edit, can_delete, can_upload, can_manage) 
                      VALUES (%s, %s, 0, 0, 1, 1, 1, 1, 1)"""
        db.execute(perm_sql, (folder_id, owner_id), need_commit=True)

        # ---- 根据文件类型添加默认权限 ----
        if parent_id == -1:
            if file_type == 2 and group_id:
                # 群组所有成员获得查看权限
                perm_sql = """INSERT INTO nsyy_gyl.file_folder_permission 
                                      (folder_id, group_id, can_view, can_upload, can_download) 
                                      VALUES (%s, %s, 1, 1, 1) ON DUPLICATE KEY UPDATE can_view=1, can_upload=1, can_download=1"""
                db.execute(perm_sql, (folder_id, group_id), need_commit=True)
            elif file_type == 3 and owner_depts:
                # 科室所有成员获得查看权限（可能多个科室，都给）
                for dept_id in owner_depts:
                    perm_sql = """INSERT INTO nsyy_gyl.file_folder_permission 
                                          (folder_id, dept_id, can_view, can_upload, can_download) 
                                          VALUES (%s, %s, 1, 1, 1) ON DUPLICATE KEY UPDATE can_view=1, can_upload=1, can_download=1"""
                    db.execute(perm_sql, (folder_id, dept_id), need_commit=True)

        # 可选：验证插入
        if global_config.run_in_local:
            check = db.query_one(f"SELECT can_upload FROM nsyy_gyl.file_folder_permission WHERE folder_id={folder_id} AND user_id={owner_id}")
            logger.debug(
                f"Folder {folder_id} permission for user {owner_id}: can_upload={check['can_upload'] if check else 'NO RECORD'}")


"""更新文件夹名字 / 删除文件夹"""


def update_folder(json_data):
    folder_id = json_data.get("folder_id")
    owner_id = json_data.get("owner_id")
    owner_depts = json_data.get("owner_depts")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        folder = db.query_one(f"select owner_id, is_deleted from nsyy_gyl.file_folder where folder_id = {folder_id}")
        if not folder or folder.get('is_deleted', 0):
            raise Exception("无效操作, 该目录已删除, 刷新页面")

        # 获取权限集
        permissions = get_effective_permission(owner_id, owner_depts, folder_id=folder_id)
        if int(json_data.get('is_deleted', 0)):
            if not permissions["can_delete"]:
                raise Exception("权限不足, 无权限删除文件夹")
            db.execute(f"UPDATE nsyy_gyl.file_folder SET is_deleted = 1 WHERE folder_id = {folder_id}", need_commit=True)

        if not permissions["can_edit"]:
            raise Exception("权限不足, 无权限修改文件夹名字/权限")

        if json_data.get('folder_name', ''):
            db.execute(f"UPDATE nsyy_gyl.file_folder SET name = '{json_data.get('folder_name')}' "
                       f"WHERE folder_id = {folder_id}", need_commit=True)



"""
批量添加 / 撤销 / 清除 权限
resource_type,  # "document" or "folder"
    resource_ids,   # [1,2,3]
    target_type,    # "user" | "group" | "dept"
    target_ids,     # [10,20]
    operation,      # "grant" | "revoke" | "clear"
    perm_fields     # ["can_view", "can_edit"]
    
operation:
    grant  -> 指定字段设为 True
    revoke -> 指定字段设为 False
    clear  -> 删除整条权限记录
"""


def grant_folder(resource_type, resource_ids, target_type, target_ids, operation, perm_fields):
    if not resource_ids or not target_ids:
        return

    if resource_type not in ("document", "folder"):
        raise ValueError("未知文件类型，仅支持 document/folder")
    if target_type not in ("user", "group", "dept"):
        raise ValueError("非法权限目标，仅支持 user/group/dept")

    if operation not in ("grant", "revoke", "clear"):
        raise ValueError("invalid operation")

    for f in perm_fields:
        if f not in PERM_FIELDS:
            raise ValueError(f"invalid permission field {f}")

    table = "nsyy_gyl.file_document_permission" if resource_type == "document" else "nsyy_gyl.file_folder_permission"
    resource_column = "document_id" if resource_type == "document" else "folder_id"
    target_column = f"{target_type}_id"

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        # CLEAR 操作（真正批量删除）
        if operation == "clear":
            # 生成 (rid, tid) 组合
            delete_pairs = [(rid, tid) for rid in resource_ids for tid in target_ids]
            placeholders = ",".join(["(%s,%s)"] * len(delete_pairs))

            flat_values = []
            for rid, tid in delete_pairs:
                flat_values.extend([rid, tid])

            db.execute(f"""DELETE FROM {table} WHERE ({resource_column}, {target_column}) IN ({placeholders})""",
                       flat_values, need_commit=True)
            return

        # GRANT / REVOKE 操作

        # 构造所有插入组合
        insert_pairs = [(rid, tid) for rid in resource_ids for tid in target_ids]
        # 每条记录字段值
        field_values = []
        for f in perm_fields:
            if operation == "grant":
                field_values.append(True)
            else:
                field_values.append(False)

        # 生成 VALUES 占位符
        single_row_placeholder = "(" + ",".join(["%s"] * (2 + len(perm_fields))) + ")"
        placeholders = ",".join([single_row_placeholder] * len(insert_pairs))

        # 拼接值
        flat_values = []
        for rid, tid in insert_pairs:
            flat_values.extend([rid, tid] + field_values)

        # UPDATE 部分
        update_clause = ", ".join([f"{f}=VALUES({f})" for f in perm_fields])

        sql = f""" INSERT INTO {table} ({resource_column}, {target_column}, {", ".join(perm_fields)})
            VALUES {placeholders} ON DUPLICATE KEY UPDATE {update_clause} """

        db.execute(sql, flat_values, need_commit=True)


"""移动文件夹/文件"""


def move_folder_or_document(json_data):
    owner_id = json_data.get("owner_id")
    owner_depts = json_data.get("owner_depts")
    resource_type = json_data.get("resource_type")  # "document" or "folder"
    resource_id = json_data.get("resource_id")
    target_folder_id = json_data.get("target_folder_id")

    if target_folder_id == -1:
        raise Exception("目标目录异常，无法移动至根目录，请重新选择目录")

    # 权限校验
    if resource_type == "folder":
        permissions = get_effective_permission(owner_id, owner_depts, folder_id=resource_id)
        if not permissions.get("can_edit"):
            raise Exception("权限不足，没有当前文件夹的编辑权限")
    elif resource_type == "document":
        permissions = get_effective_permission(owner_id, owner_depts, doc_id=resource_id)
        if not permissions.get("can_edit"):
            raise Exception("权限不足，没有当前文件的编辑权限")
    else:
        raise ValueError("未知资源类型，仅支持 document/folder")

    # 目标文件夹权限校验
    target_perms = get_effective_permission(owner_id, owner_depts, folder_id=target_folder_id)
    if not target_perms.get("can_edit"):
        raise Exception("权限不足，没有目标文件夹的编辑权限")

    # 数据库操作
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # ===== 检查资源是否存在且未删除 =====
        if resource_type == "folder":
            row = db.query_one(f"SELECT * FROM nsyy_gyl.file_folder WHERE folder_id = {resource_id}")
        else:
            row = db.query_one(f"SELECT * FROM nsyy_gyl.file_document WHERE document_id = {resource_id}")

        if not row:
            raise Exception(f"{resource_type}不存在")
        if row.get('is_deleted', 0) == 1:
            raise Exception(f"{resource_type}已被删除")

        # ===== 检查目标文件夹是否存在且未删除 =====
        target = db.query_one(f"SELECT * FROM nsyy_gyl.file_folder WHERE folder_id = {target_folder_id}")
        if not target:
            raise Exception("目标文件夹不存在")
        if target.get('is_deleted', 0) == 1:
            raise Exception("目标文件夹已被删除")

        # ===== 循环引用检查（仅对文件夹移动） =====
        if resource_type == "folder":
            # 检查目标文件夹是否是当前文件夹本身或其子文件夹
            if resource_id == target_folder_id:
                raise Exception("不能将文件夹移动到自己")
            # 检查 target_folder_id 是否在 resource_id 的子孙中
            current = target_folder_id
            while current != -1:
                if current == resource_id:
                    raise Exception("不能将文件夹移动到自己的子文件夹中")
                # 查询当前节点的父级
                parent_row = db.query_one(f"SELECT parent_id FROM nsyy_gyl.file_folder WHERE folder_id = {current}")
                if not parent_row:
                    break
                current = parent_row.get("parent_id", -1)

        # ===== 执行移动更新 =====
        if resource_type == "folder":
            # 更新 parent_id
            update_sql = "UPDATE nsyy_gyl.file_folder SET parent_id = %s WHERE folder_id = %s"
            db.execute(update_sql, (target_folder_id, resource_id), need_commit=True)
        else:  # document
            # 更新 folder_id
            update_sql = "UPDATE nsyy_gyl.file_document SET folder_id = %s WHERE document_id = %s"
            db.execute(update_sql, (target_folder_id, resource_id), need_commit=True)


"""上传文件"""


def upload_file(json_data, upload_files):
    owner = json_data.get("owner", '')
    owner_id = json_data.get("owner_id")
    owner_depts = json.loads(json_data.get("owner_depts"))
    folder_id = int(json_data.get("folder_id"))

    file_type = int(json_data.get("file_type"))  # 注意前端用 'type' 表示 file_type
    group_id = json_data.get("group_id")  # 新增
    group_name = json_data.get("group_name")  # 新增

    # ---- 根目录权限检查 ----
    if folder_id == -1:
        if not check_root_permission(owner_id, file_type, [str(item.get('dept_id')) for item in owner_depts], group_id):
            raise Exception("您无权在此根目录下上传文件")
    else:
        permissions = get_effective_permission(owner_id, [str(item.get('dept_id')) for item in owner_depts], folder_id=folder_id)
        if not permissions.get("can_upload"):
            raise Exception("权限不足，没有当前文件夹的上传权限")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if folder_id != -1:
            folder = db.query_one(f"select * from nsyy_gyl.file_folder where folder_id = {folder_id}")
            if not folder or folder.get('is_deleted', 0):
                raise Exception("目标文件夹已删除")

        # 上传文件到服务器
        file_paths = _upload_file(upload_files)
        if not file_paths:
            raise Exception("文件上传失败")

        for item in file_paths:
            # 1. 插入文件
            insert_sql = """INSERT INTO nsyy_gyl.file_document 
                            (file_type, name, folder_id, storage_path, owner_id, owner, is_publish, created_at, updated_at, group_id) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            doc_id = db.execute(insert_sql, (file_type, item.get('name'), folder_id, item.get('path'), owner_id,
                                    json_data.get('owner'), json_data.get('is_publish'),
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), group_id), need_commit=True)
            if doc_id != -1:
                # 3. 给创建者赋予该文档的所有权限（文档无 can_upload，故不包含）
                perm_sql = """INSERT INTO nsyy_gyl.file_document_permission 
                                (document_id, user_id, user_name, group_id, dept_id, can_view, can_edit, can_delete, can_download, can_manage) 
                                VALUES (%s, %s, %s, 0, 0, 1, 1, 1, 1, 1)"""
                db.execute(perm_sql, (doc_id, owner_id, owner), need_commit=True)

                # ---- 根目录下文件默认权限 ----
                if folder_id == -1:
                    if file_type == 2 and group_id:
                        # 群组成员获得查看+下载
                        perm_sql = """INSERT INTO nsyy_gyl.file_document_permission 
                                                      (document_id, group_id, group_name, can_view, can_download) 
                                                      VALUES (%s, %s, %s, 1, 1) ON DUPLICATE KEY UPDATE can_view=1, can_download=1"""
                        db.execute(perm_sql, (doc_id, group_id, group_name), need_commit=True)
                    elif file_type == 3 and owner_depts:
                        for item in owner_depts:
                            perm_sql = """INSERT INTO nsyy_gyl.file_document_permission 
                                                          (document_id, dept_id, dept_name, can_view, can_download) 
                                                          VALUES (%s, %s, %s, 1, 1) ON DUPLICATE KEY UPDATE can_view=1, can_download=1"""
                            db.execute(perm_sql, (doc_id, item.get('dept_id'), item.get('dept_name')), need_commit=True)


"""下载文件"""

def download_file(json_data):
    document_id = json_data.get('document_id')
    version = json_data.get('version')
    owner_id = json_data.get('owner_id')
    owner_depts = json_data.get('owner_depts')

    permissions = get_effective_permission(owner_id, owner_depts, doc_id=document_id)
    if not permissions["can_download"]:
        raise Exception("权限不足，没有当前文件的下载权限")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        file = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
        if not file or file.get('is_deleted', 0):
            raise Exception("文件不存在")

        if file.get('cur_version_id', 1) != int(version):
            his_file = db.query_one(f"select * from nsyy_gyl.file_document_version "
                                    f"where document_id = {document_id} and version_id = {int(version)}")
            if not his_file or his_file.get('is_deleted', 0):
                raise Exception("文件不存在")
            file['storage_path'] = his_file.get('storage_path', '')

        if file.get('is_publish') == 0 and file.get('owner_id', 0) != owner_id:
            raise Exception("文件未发布无法下载")
        return file


"""更新文件名称/发布状态"""


def update_file(json_data, new_files):
    owner_id = json_data.get("owner_id")
    owner_depts = json.loads(json_data.get("owner_depts"))
    document_id = json_data.get("document_id")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        document = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
        if not document or document.get('is_deleted', 0):
            raise Exception("该目录已删除")

        if not document or document.get('owner_id', 0) != owner_id:
            permissions = get_effective_permission(owner_id, owner_depts, doc_id=document_id)
            if not permissions["can_edit"]:
                raise Exception("权限不足，没有当前文件的编辑权限")
            if int(json_data.get('is_deleted', 0)):
                if not permissions["can_delete"]:
                    raise Exception("权限不足，没有当前文件的删除权限")

        if int(json_data.get('is_deleted', 0)):
            db.execute(f"UPDATE nsyy_gyl.file_document SET is_deleted = 1 WHERE document_id = {document_id}", need_commit=True)

        condition_sql = ""
        if json_data.get('file_name', ''):
            condition_sql = f"name = '{json_data.get('file_name')}'"
        if 'is_publish' in json_data:
            condition_sql += f", is_publish = '{json_data.get('is_publish')}'" \
                if condition_sql else f"is_publish = '{json_data.get('is_publish')}'"
        if condition_sql:
            db.execute(f"UPDATE nsyy_gyl.file_document SET {condition_sql} WHERE document_id = {document_id}",
                       need_commit=True)

        if new_files:
            if not check_root_permission(owner_id, document.get('file_type'), [str(item.get('dept_id')) for item in owner_depts],
                                         json_data.get('group_id', 0)):
                raise Exception("您无权在此根目录下上传文件")

            # 上传文件到服务器
            file_paths = _upload_file(new_files)
            if not file_paths:
                raise Exception("文件上传失败")

            # 将旧文件存入历史信息
            insert_sql = """INSERT INTO nsyy_gyl.file_document_version 
                                    (document_id, version_id, storage_path, owner_id, owner, comment, is_deleted, updated_at) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            db.execute(insert_sql, (document_id, document.get('cur_version_id'), document.get('storage_path'),
                                        document.get('owner_id'), document.get('owner'), json_data.get('comment', ''), 0,
                                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)

            version = document.get('cur_version_id', 1) + 1
            # 更新文件地址 和 版本
            db.execute(f"UPDATE nsyy_gyl.file_document SET storage_path = '{file_paths[0].get('path')}', "
                       f"cur_version_id = {version} WHERE document_id = {document_id}", need_commit=True)


"""查询当前目录内容"""

def merge_with_priority(layers):
    result = {f: None for f in PERM_FIELDS}

    for layer in layers:
        if not layer:
            continue
        for f in PERM_FIELDS:
            if result[f] is None:
                val = layer.get(f)
                if val is not None:
                    result[f] = bool(val)

    for f in PERM_FIELDS:
        if result[f] is None:
            result[f] = False

    return result

def merge_same_level(rows):
    if not rows:
        return None

    result = {f: None for f in PERM_FIELDS}

    for row in rows:
        for f in PERM_FIELDS:
            if row.get(f) is True:
                result[f] = True
            elif result[f] is None:
                result[f] = row.get(f)

    return result


"""查询目标文件夹的文件和文件夹"""

def query_file_list(json_data):
    parent_id = json_data.get("folder_id", -1)
    user_id = json_data.get("owner_id")
    depts = json_data.get("owner_depts")
    file_type = json_data.get("file_type")
    group_id = json_data.get("group_id", '')
    group_condition = f" and group_id = {group_id} " if group_id else ""
    depts = [str(d) for d in depts]
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        groups = db.query_all(f"select distinct group_id from nsyy_gyl.group_member where user_id = {user_id} and state = 1 ")
        groups = [g["group_id"] for g in groups]

        # ========= 1. 查询子文件夹 =========
        folders = db.query_all(f"select * from nsyy_gyl.file_folder where parent_id = {parent_id} "
                               f"and file_type = {file_type} and is_deleted = 0 {group_condition}")

        # ========= 2. 查询文件 =========
        documents = db.query_all(f"select * from nsyy_gyl.file_document where folder_id = {parent_id} "
                                 f"and file_type = {file_type} and is_deleted = 0 {group_condition}")

    folder_ids = [str(f["folder_id"]) for f in folders]
    # 关键：把当前目录也加入权限查询
    perm_folder_ids = set(folder_ids)
    if parent_id != -1:
        perm_folder_ids.add(str(parent_id))

    # 也可以把文件所在目录也加入，防止文件在其它目录
    for d in documents:
        if d.get("folder_id") is not None:
            perm_folder_ids.add(str(d["folder_id"]))

    doc_ids = []
    for d in documents:
        if d.get('is_publish', 0) == 1:
            doc_ids.append(str(d["document_id"]))
        else:
            if d.get('owner_id', 0) == user_id:
                doc_ids.append(str(d["document_id"]))

    # ========= 3. 批量加载权限 =========
    folder_perm_map = {}
    doc_perm_map = {}

    if perm_folder_ids:
        format_ids = ",".join(perm_folder_ids)
        folder_perm = db.query_all(
            f"select * from nsyy_gyl.file_folder_permission where folder_id in ({format_ids})"
        )
        for p in folder_perm:
            folder_perm_map.setdefault(p["folder_id"], []).append(p)

    if doc_ids:
        format_ids = ",".join(doc_ids)
        doc_perm = db.query_all(f"select * from nsyy_gyl.file_document_permission where document_id in ({format_ids})")
        for p in doc_perm:
            doc_perm_map.setdefault(p["document_id"], []).append(p)

    visible_folders = []
    visible_documents = []
    # ========= 4. 过滤文件夹 =========
    for f in folders:
        perms = folder_perm_map.get(f["folder_id"], [])

        layers = [
            next((p for p in perms if p.get("user_id") == user_id), None),
            merge_same_level([p for p in perms if p.get("group_id") in groups]),
            merge_same_level([p for p in perms if p.get("dept_id") in depts]),
        ]

        default_layer = {f: False for f in PERM_FIELDS}
        if f.get("file_type") == 4:  # 注意这里 f 是文件夹对象
            default_layer["can_view"] = True
            default_layer["can_download"] = True  # 如果也允许下载
        layers.append(default_layer)
        effective = merge_with_priority(layers)

        if effective["can_view"]:
            visible_folders.append(f)

    # ========= 5. 过滤文件 =========
    for d in documents:
        perms = doc_perm_map.get(d["document_id"], [])

        layers = [
            next((p for p in perms if p.get("user_id") == user_id), None),
            merge_same_level([p for p in perms if p.get("group_id") in groups]),
            merge_same_level([p for p in perms if p.get("dept_id") in depts]),
        ]

        # 如果文件没单独权限 → 回退当前文件夹权限
        if not any(layers):
            folder_perms = folder_perm_map.get(d["folder_id"], [])
            layers = [
                next((p for p in folder_perms if p.get("user_id") == user_id), None),
                merge_same_level([p for p in folder_perms if p.get("group_id") in groups]),
                merge_same_level([p for p in folder_perms if p.get("dept_id") in depts]),
            ]

        default_layer = {f: False for f in PERM_FIELDS}
        if d.get("file_type") == 4:  # 注意这里 f 是文件夹对象
            default_layer["can_view"] = True
            default_layer["can_download"] = True  # 如果也允许下载
        layers.append(default_layer)
        effective = merge_with_priority(layers)

        if effective["can_view"]:
            visible_documents.append(d)

    return {"folders": visible_folders, "documents": visible_documents}


"""查询删除的文件和文件夹"""

def query_deleted_list(json_data):
    user_id = json_data.get("owner_id")
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:

        # ========= 1. 查询子文件夹 =========
        folders = db.query_all(f"select * from nsyy_gyl.file_folder where is_deleted = 1 and owner_id = {user_id}")

        # ========= 2. 查询文件 =========
        documents = db.query_all(f"select * from nsyy_gyl.file_document where is_deleted = 1 and owner_id = {user_id}")

    return {"folders": folders, "documents": documents}


def _upload_file(files):
    if not files:
        return ''
    try:
        paths = []
        if global_config.run_in_local:
            import os
            # 确保上传目录存在
            path = f"{file_config.upload_path_local}/{datetime.now().strftime('%Y%m%d')}"
            if not os.path.exists(path):
                os.makedirs(path)

            for file in files:
                # 安全保存文件
                file_path = os.path.join(path, f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename}")
                file.save(file_path)
                paths.append({"name": file.filename, "path": file_path})
        else:
            remote_dir = f"{file_config.upload_path_dev}/{datetime.now().strftime('%Y%m%d')}"
            paths = _upload_file_to_remote(files, remote_dir)
        return paths
    except Exception as e:
        logger.error(f"文件上传失败 {e}")
    return []


def _upload_file_to_remote(files, remote_dir):
    if not files:
        return ''

    sftp = None
    ssh = None
    try:
        # 建立 SSH / SFTP 连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=file_config.SFTP_HOST,
            port=file_config.SFTP_PORT,
            username=file_config.SFTP_USERNAME,
            password=file_config.SFTP_PASSWORD,
            timeout=10,
        )
        sftp = ssh.open_sftp()

        # 递归创建远程目录
        _mkdir_p(sftp, remote_dir)

        paths = []
        for file in files:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename}"
            remote_path = f"{remote_dir}/{filename}".replace('\\', '/')

            # 上传文件（流式上传，避免落本地磁盘）
            file.stream.seek(0)
            sftp.putfo(file.stream, remote_path)

            paths.append({"name": file.filename, "path": remote_path})
        return paths
    except Exception as e:
        logger.error(f"文件上传失败 {e}")
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
    return []


def _mkdir_p(sftp, remote_dir):
    """在远程服务器上递归创建目录"""
    remote_dir = remote_dir.replace('\\', '/')
    dirs = []
    while remote_dir and remote_dir not in ('/', ''):
        dirs.append(remote_dir)
        remote_dir, _ = os.path.split(remote_dir)
    for d in reversed(dirs):
        try:
            sftp.stat(d)
        except IOError:
            sftp.mkdir(d)


"""文件/文件夹 权限查询 返回用户对 文档 或 文件夹 的最终权限"""


def empty_perm():
    return {f: False for f in PERM_FIELDS}


def merge_perm_rows(rows, result=None):
    """多条组权限 OR 合并"""
    result = empty_perm()
    for row in rows:
        for f in PERM_FIELDS:
            result[f] = result[f] or bool(row[f])
    return result


"""
检查用户是否允许在根目录（folder_id=-1）下创建文件夹或上传文件。
- file_type=1: 个人文档，所有人允许
- file_type=2: 群组文档，需用户为群主或管理员（需 group_id）
- file_type=3: 科室文档，需用户为科主任或科室文档管理员
- file_type=4: 院级文档，需用户在允许列表中（暂定读取配置）
"""
def check_root_permission(user_id, file_type, dept_list=None, group_id=None):
    if file_type == 1:
        return True

    if file_type == 2:
        if not group_id:
            # 群组 ID 必须提供，否则无法判断
            raise ValueError("群组文档操作必须提供 group_id")
        # 查询用户是否是该群组的群主或管理员
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            row = db.query_one(f"""
                SELECT allow_edit FROM nsyy_gyl.group_member
                WHERE group_id = {group_id} AND user_id = '{user_id}' AND state = 1
            """)
            # allow_edit=2 群主，1 管理员
            return row and row.get('allow_edit') in (1, 2)

    if file_type == 3:
        if not dept_list:
            return False
        # 用户必须是科室文档管理员（file_dept_permission 中有记录）
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            placeholders = ','.join([f"'{item}'" for item in dept_list])

            sql = f"SELECT 1 FROM nsyy_gyl.file_dept_permission WHERE pers_id = '{user_id}' AND dept_id IN ({placeholders})"
            row = db.query_one(sql)
            return row is not None

    if file_type == 4:
        # 院级文档从配置或环境变量读取允许的用户列表
        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            sql = f"SELECT pers_id FROM nsyy_gyl.file_dept_permission WHERE dept_id = '-1'"
            allowed_users = db.query_all(sql)
            allowed_users = [str(row["pers_id"]) for row in allowed_users]

        return allowed_users and str(user_id) in allowed_users

    return False


def get_effective_permission(user_id, dept_list, doc_id=None, folder_id=None, read_only=False):
    result = None
    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 查询用户所属群组（根据 read_only 决定是否限制 allow_edit）
        if read_only:
            groups = db.query_all(
                f"SELECT DISTINCT group_id FROM nsyy_gyl.group_member WHERE user_id = '{user_id}' AND state = 1")
            groups = [g["group_id"] for g in groups]
            depts = dept_list
        else:
            groups = db.query_all(
                f"SELECT DISTINCT group_id FROM nsyy_gyl.group_member WHERE user_id = '{user_id}' AND state = 1")
            groups = [g["group_id"] for g in groups]
            # 只取用户具有管理员身份的科室（限定在传入的科室列表中）
            dept_ids = ','.join([f"'{item}'" for item in dept_list])
            dept_records = db.query_all(
                f"SELECT DISTINCT dept_id FROM nsyy_gyl.file_dept_permission WHERE pers_id = '{user_id}' AND dept_id IN ({dept_ids})")
            depts = [str(d["dept_id"]) for d in dept_records]

        # 如果传入 doc_id，优先查文档权限
        if doc_id:
            # 文档用户权限（最高优先级）
            doc = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {doc_id}")
            if doc and doc.get('file_type') == 1 and str(doc.get('owner_id')) == str(user_id):
                return {f: True for f in ["can_view", "can_edit", "can_delete", "can_download"]}

            row = db.query_one(
                f"SELECT can_view, can_edit, can_delete, can_download FROM nsyy_gyl.file_document_permission "
                f"WHERE document_id = {doc_id} AND user_id = {user_id} LIMIT 1")
            if row:
                return {f: bool(row[f]) for f in ["can_view", "can_edit", "can_delete", "can_download"]}

            # 文档组/科室权限（次优先级）
            if groups or depts:
                sql = f"SELECT can_view, can_edit, can_delete, can_download FROM nsyy_gyl.file_document_permission WHERE document_id = {doc_id}"
                if groups and not depts:
                    groups = [str(item) for item in groups]
                    sql += f" AND group_id IN ({','.join(groups)})"
                if depts and not groups:
                    depts = [str(item) for item in depts]
                    sql += f" AND dept_id IN ({','.join(depts)})"
                if groups and depts:
                    groups = [str(item) for item in groups]
                    depts = [str(item) for item in depts]
                    sql += f" AND (group_id IN ({','.join(groups)}) OR dept_id IN ({','.join(depts)}))"

                rows = db.query_all(sql)
                if rows:
                    # 合并同层权限（OR）
                    perm = {f: False for f in ["can_view", "can_edit", "can_delete", "can_download"]}
                    for r in rows:
                        for f in perm:
                            perm[f] = perm[f] or bool(r[f])
                    return perm

            # 文档权限未命中，检查是否为院级文件
            if doc and doc.get("file_type") == 4:
                return {
                    "can_view": True,
                    "can_download": True,
                    "can_edit": False,
                    "can_delete": False,
                    "can_upload": False
                }

            # 文档权限未命中，回退到所在文件夹
            if not folder_id:
                doc = db.query_one(f"SELECT folder_id FROM nsyy_gyl.file_document WHERE document_id = {doc_id}")
                if not doc or not doc["folder_id"]:
                    return empty_perm()
                folder_id = doc["folder_id"]

        # 文件夹权限
        if folder_id:
            # 文件夹用户权限（最高）
            row = db.query_one(
                f"SELECT can_view, can_edit, can_delete, can_download, can_upload "
                f"FROM nsyy_gyl.file_folder_permission WHERE folder_id = {int(folder_id)} AND user_id = '{user_id}' LIMIT 1"
            )
            if row:
                return {f: bool(row[f]) for f in PERM_FIELDS}

                # 文件夹组/科室权限
            if groups or depts:
                sql = f"SELECT can_view, can_edit, can_delete, can_download, can_upload FROM nsyy_gyl.file_folder_permission WHERE folder_id = {folder_id}"
                if groups and not depts:
                    groups = [str(item) for item in groups]
                    sql += f" AND group_id IN ({','.join(groups)})"
                if depts and not groups:
                    depts = [str(item) for item in depts]
                    sql += f" AND dept_id IN ({','.join(depts)})"
                if groups and depts:
                    groups = [str(item) for item in groups]
                    depts = [str(item) for item in depts]
                    sql += f" AND (group_id IN ({','.join(groups)}) OR dept_id IN ({','.join(depts)}))"

                rows = db.query_all(sql)
                if rows:
                    perm = {f: False for f in PERM_FIELDS}
                    for r in rows:
                        for f in perm:
                            perm[f] = perm[f] or bool(r[f])
                    return perm

            # 如果都没命中，检查是否为院级文件夹
            folder_info = db.query_one(
                f"SELECT file_type FROM nsyy_gyl.file_folder WHERE folder_id = {int(folder_id)}"
            )
            if folder_info and folder_info.get("file_type") == 4:
                return {
                    "can_view": True,
                    "can_download": True,
                    "can_edit": False,
                    "can_delete": False,
                    "can_upload": False
                }
    # 默认无权限
    return empty_perm()


# ==================================================
# ================  资源详情与权限查询 ===================
# ==================================================

"""查询文件夹详情（包括当前权限）"""


def folder_detail(json_data):
    folder_id = json_data.get("folder_id")
    user_id = json_data.get("owner_id")
    user_depts = json_data.get("owner_depts", [])

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 查询文件夹信息
        folder = db.query_one(f"SELECT * FROM nsyy_gyl.file_folder WHERE folder_id = {folder_id}")
        if not folder or folder.get('is_deleted', 0):
            raise Exception("文件夹不存在或已删除")

        # 查询当前用户的权限
        permissions = get_effective_permission(user_id, user_depts, folder_id=folder_id)

        # 查询该文件夹的所有权限设置
        all_perms = db.query_all(f"""SELECT fp.*,
                                     CASE WHEN fp.user_id IS NOT NULL AND fp.user_id != '0' THEN 'user'
                                          WHEN fp.group_id IS NOT NULL AND fp.group_id != 0 THEN 'group'
                                          WHEN fp.dept_id IS NOT NULL AND fp.dept_id != '0' THEN 'dept'
                                          ELSE 'unknown' END as perm_type
                                     FROM nsyy_gyl.file_folder_permission fp
                                     WHERE fp.folder_id = {folder_id}""")

        return {
            "folder": folder,
            "permissions": permissions,
            "all_permissions": all_perms
        }



"""查询文档详情（包括当前权限）"""


def document_detail(json_data):
    document_id = json_data.get("document_id")
    user_id = json_data.get("owner_id")
    user_depts = json_data.get("owner_depts", [])

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        # 查询文档信息
        document = db.query_one(f"SELECT * FROM nsyy_gyl.file_document WHERE document_id = {document_id}")
        if not document or document.get('is_deleted', 0):
            raise Exception("文档不存在或已删除")

        # 查询当前用户的权限
        permissions = get_effective_permission(user_id, user_depts, doc_id=document_id)

        # 查询该文档的所有权限设置
        all_perms = db.query_all(f"""SELECT dp.*,
                                     CASE WHEN dp.user_id IS NOT NULL AND dp.user_id != '0' THEN 'user'
                                          WHEN dp.group_id IS NOT NULL AND dp.group_id != 0 THEN 'group'
                                          WHEN dp.dept_id IS NOT NULL AND dp.dept_id != '0' THEN 'dept'
                                          ELSE 'unknown' END as perm_type
                                     FROM nsyy_gyl.file_document_permission dp
                                     WHERE dp.document_id = {document_id}""")

        return {
            "document": document,
            "permissions": permissions,
            "all_permissions": all_perms
        }




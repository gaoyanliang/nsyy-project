# import logging
# from datetime import datetime
#
# from gylmodules import global_config
# from gylmodules.file_system import file_config
# from gylmodules.file_system.file_config import PERM_FIELDS
# from gylmodules.utils.db_utils import DbUtil
#
# logger = logging.getLogger(__name__)
#
# # ==================================================
# # ================用户组 & 权限管理(文件夹权限仅添加在根目录上) ===================
# # ==================================================
#
#
# """新建或更新群组"""
#
#
# def create_or_update_group(json_data):
#     group_id = json_data.get("group_id")
#     user_id = json_data.get("user_id", 0)
#     group_name = json_data.get("group_name", '')
#     members = json_data.get('members')
#     op_type = json_data.get("op_type")
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     if group_id:
#         if not db.query_one(f"select id from nsyy_gyl.file_user_permission "
#                             f"where group_id = {group_id} and user_id = {user_id}"):
#             del db
#             raise Exception("您没有编辑当前群组的权限,请联系群组管理员操作")
#
#         # 更新群组 名称
#         sql = f"""UPDATE nsyy_gyl.file_group SET group_name = '{group_name}',
#         updated_at = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' WHERE group_id = {group_id}"""
#         db.execute(sql, need_commit=True)
#     else:
#         # 新增群组
#         sql = """INSERT INTO nsyy_gyl.file_group (group_name, owner_id, owner, created_at, updated_at)
#             VALUES (%s, %s, %s, %s, %s) """
#         last_rowid = db.execute(sql, (json_data.get("group_name", ''), user_id, json_data.get("user_name", ''),
#                                       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                                       datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
#                                 need_commit=True)
#         if last_rowid == -1:
#             del db
#             raise Exception("群组添加失败，请稍后重试")
#         group_id = last_rowid
#         # 同时添加权限
#         db.execute(f"""INSERT INTO nsyy_gyl.file_user_permission (name, group_id, user_id, user_name)
#         VALUES (%s, %s, %s, %s)""", (group_name, last_rowid, user_id, json_data.get('user_name', '')), need_commit=True)
#         db.execute(f"""INSERT INTO nsyy_gyl.file_group_membership (group_id, user_id, user_name)
#         VALUES (%s, %s, %s)""", (last_rowid, user_id, json_data.get('user_name', '')), need_commit=True)
#
#     if members:
#         if op_type == "add":
#             # 添加群组成员
#             args = [(group_id, item.get('user_id', 0), item.get('user_name', '')) for item in members]
#             insert_sql = """INSERT INTO nsyy_gyl.file_group_membership (group_id, user_id, user_name)
#                 VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE user_name = VALUES(user_name)"""
#             db.execute_many(insert_sql, args, need_commit=True)
#         elif op_type == "remove":
#             # 移除群组成员
#             args = [str(item.get('user_id', 0)) for item in members]
#             delete_sql = f"""DELETE FROM nsyy_gyl.file_group_membership where group_id = {group_id}
#             and user_id in ({','.join(args)})"""
#             db.execute(delete_sql, need_commit=True)
#         else:
#             del db
#             raise Exception("群组成员操作类型错误")
#     del db
#
#
# """查询加入的所有群组"""
#
#
# def query_group_list(user_id):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     groups = db.query_all(f"select * from nsyy_gyl.file_group where group_id in "
#                           f"(select group_id from file_group_membership where user_id = '{user_id}')")
#     del db
#     return groups
#
#
# """查询群组成员"""
#
#
# def query_group_member(group_id):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     members = db.query_all(f"select * from nsyy_gyl.file_group_membership where group_id = {group_id}")
#     del db
#     return members
#
#
# """给科室/群组添加管理员"""
#
#
# def op_admin(json_data):
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     p_type = json_data.get("p_type")
#     p_id = json_data.get("p_id")
#     p_name = json_data.get("p_name", '')
#     user_id = json_data.get("user_id")
#     condition_sql = f"and dept_id = {p_id}" if p_type == "dept" else f"and group_id = {p_id}"
#     if not db.query_one(f"select * from nsyy_gyl.file_user_permission "
#                         f"where user_id = {user_id} {condition_sql}"):
#         del db
#         raise Exception("权限不足，请联系科室/群组文档管理员操作")
#
#     users = json_data.get("users", [])
#     if json_data.get("op_type") == "remove":
#         # 移除管理员
#         user_ids = ','.join([f"'{item['user_id']}'" for item in users])
#         args = [str(item.get('user_id', 0)) for item in users]
#         delete_sql = f"""DELETE FROM nsyy_gyl.file_user_permission where
#         {'dept_id' if p_type == "dept" else 'group_id'} = {p_id} and user_id in ({user_ids})"""
#         db.execute(delete_sql, need_commit=True)
#     elif json_data.get("op_type") == "add":
#         if p_type == "dept":
#             args = [(p_name, str(p_id), -1, str(item.get('user_id', 0)), item.get('user_name', '')) for item in users]
#         elif p_type == "group":
#             args = [(p_name, '', p_id, str(item.get('user_id', 0)), item.get('user_name', '')) for item in users]
#         else:
#             del db
#             raise Exception("操作类型错误 仅支持 dept/group")
#
#         insert_sql = """INSERT INTO nsyy_gyl.file_user_permission (name, dept_id, group_id, user_id, user_name)
#                             VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE user_id = VALUES(user_id),
#                              user_name = VALUES(user_name)"""
#         db.execute_many(insert_sql, args, need_commit=True)
#     else:
#         del db
#         raise Exception("操作类型错误")
#     del db
#
#
# """查询科室文档管理配置列表"""
#
#
# def dept_admin_list():
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     dept_admins = db.query_all(
#         "select * from nsyy_gyl.file_user_permission where dept_id is not null and dept_id != ''")
#     del db
#     return dept_admins
#
#
# # ==================================================
# # ================  目录 文件 管理 ===================
# # ==================================================
#
#
# """查看文件历史版本"""
#
#
# def query_file_history(document_id):
#     """这一步 不需要权限判断，由上一步判断"""
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     documents = db.query_all(f"select * from nsyy_gyl.file_document_version "
#                              f"where document_id = {document_id} and is_deleted = 0")
#     del db
#     return documents
#
#
# """新建文件夹"""
#
#
# def new_folder(json_data):
#     # 文件类型 1=个人 2=组别 3=科室 4=院级
#     file_type = json_data.get("file_type")
#     owner_id = json_data.get("owner_id")
#     parent_id = json_data.get("parent_id")
#     owner_depts = json_data.get("owner_depts")
#
#     # 仅科室文档管理员/群组管理员 可创建文件夹
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     if parent_id == -1:
#         # 根目录仅文档管理员有权限
#         query_sql = f"select * from nsyy_gyl.file_user_permission where user_id = {owner_id} " \
#                     f"and dept_id is not null and dept_id != ''"
#         permission = db.query_all(query_sql)
#         if not permission:
#             del db
#             raise Exception("权限不足，根目录仅文档管理员有权限")
#     else:
#         # 如果要创建子目录 判读是否有父目录的编辑权限
#         permissions = get_effective_permission(owner_id, owner_depts, folder_id=parent_id)
#         if not permissions["can_edit"]:
#             del db
#             raise Exception("权限不足，无父目录的编辑权限, 无法创建子文件夹")
#
#         insert_sql = """INSERT INTO nsyy_gyl.file_folder (file_type, name, parent_id, root_id,
#                         owner_id, owner, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
#         db.execute(insert_sql, (file_type, json_data.get("name"), parent_id, -1, owner_id,
#                                 json_data.get("owner"), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')), need_commit=True)
#     del db
#
#
# """更新文件夹名字 / 删除文件夹"""
#
#
# def update_folder(json_data):
#     folder_id = json_data.get("folder_id")
#     owner_id = json_data.get("owner_id")
#     owner_depts = json_data.get("owner_depts")
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     try:
#         folder = db.query_one(f"select owner_id, is_deleted from nsyy_gyl.file_folder where folder_id = {folder_id}")
#         if not folder or folder.get('is_deleted', 0):
#             del db
#             raise Exception("无效操作, 该目录已删除, 刷新页面")
#
#         # 获取权限集
#         permissions = get_effective_permission(owner_id, owner_depts, folder_id=folder_id)
#         if int(json_data.get('is_deleted', 0)):
#             if not permissions["can_delete"]:
#                 del db
#                 raise Exception("权限不足, 无权限删除文件夹")
#             db.execute(f"UPDATE nsyy_gyl.file_folder SET is_deleted = 1 WHERE folder_id = {folder_id}", need_commit=True)
#
#         if not permissions["can_edit"]:
#             del db
#             raise Exception("权限不足, 无权限修改文件夹名字/权限")
#
#         if json_data.get('folder_name', ''):
#             db.execute(f"UPDATE nsyy_gyl.file_folder SET name = '{json_data.get('folder_name')}' "
#                        f"WHERE folder_id = {folder_id}", need_commit=True)
#     except Exception as e:
#         del db
#         raise e
#
#     del db
#
#
# """
# 批量添加 / 撤销 / 清除 权限
# resource_type,  # "document" or "folder"
#     resource_ids,   # [1,2,3]
#     target_type,    # "user" | "group" | "dept"
#     target_ids,     # [10,20]
#     operation,      # "grant" | "revoke" | "clear"
#     perm_fields     # ["can_view", "can_edit"]
#
# operation:
#     grant  -> 指定字段设为 True
#     revoke -> 指定字段设为 False
#     clear  -> 删除整条权限记录
# """
#
#
# def grant_folder(resource_type, resource_ids, target_type, target_ids, operation, perm_fields):
#     if not resource_ids or not target_ids:
#         return
#
#     if resource_type not in ("document", "folder"):
#         raise ValueError("未知文件类型，仅支持 document/folder")
#     if target_type not in ("user", "group", "dept"):
#         raise ValueError("非法权限目标，仅支持 user/group/dept")
#
#     if operation not in ("grant", "revoke", "clear"):
#         raise ValueError("invalid operation")
#
#     for f in perm_fields:
#         if f not in PERM_FIELDS:
#             raise ValueError(f"invalid permission field {f}")
#
#     table = "nsyy_gyl.file_document_permission" if resource_type == "document" else "nsyy_gyl.file_folder_permission"
#     resource_column = "document_id" if resource_type == "document" else "folder_id"
#     target_column = f"{target_type}_id"
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     try:
#         # CLEAR 操作（真正批量删除）
#         if operation == "clear":
#             # 生成 (rid, tid) 组合
#             delete_pairs = [(rid, tid) for rid in resource_ids for tid in target_ids]
#             placeholders = ",".join(["(%s,%s)"] * len(delete_pairs))
#
#             flat_values = []
#             for rid, tid in delete_pairs:
#                 flat_values.extend([rid, tid])
#
#             db.execute(f"""DELETE FROM {table} WHERE ({resource_column}, {target_column}) IN ({placeholders})""",
#                        flat_values, need_commit=True)
#             return
#
#         # GRANT / REVOKE 操作
#
#         # 构造所有插入组合
#         insert_pairs = [(rid, tid) for rid in resource_ids for tid in target_ids]
#         # 每条记录字段值
#         field_values = []
#         for f in perm_fields:
#             if operation == "grant":
#                 field_values.append(True)
#             else:
#                 field_values.append(False)
#
#         # 生成 VALUES 占位符
#         single_row_placeholder = "(" + ",".join(["%s"] * (2 + len(perm_fields))) + ")"
#         placeholders = ",".join([single_row_placeholder] * len(insert_pairs))
#
#         # 拼接值
#         flat_values = []
#         for rid, tid in insert_pairs:
#             flat_values.extend([rid, tid] + field_values)
#
#         # UPDATE 部分
#         update_clause = ", ".join([f"{f}=VALUES({f})" for f in perm_fields])
#
#         sql = f""" INSERT INTO {table} ({resource_column}, {target_column}, {", ".join(perm_fields)})
#             VALUES {placeholders} ON DUPLICATE KEY UPDATE {update_clause} """
#
#         db.execute(sql, flat_values, need_commit=True)
#     except Exception as e:
#         del db
#         raise e
#     del db
#
#
# """移动文件夹/文件"""
#
#
# def move_folder_or_document(json_data):
#     owner_id = json_data.get("owner_id")
#     owner_depts = json_data.get("owner_depts")
#     resource_type = json_data.get("resource_type")  # "document" or "folder"
#     resource_id = json_data.get("resource_id")
#     target_folder_id = json_data.get("target_folder_id")
#
#     if target_folder_id == -1:
#         raise Exception("目标目录异常，无法移动至根目录，请重新选择目录")
#
#     permissions = empty_perm()
#     if resource_type == "folder":
#         permissions = get_effective_permission(owner_id, owner_depts, folder_id=resource_id)
#     elif resource_type == "document":
#         permissions = get_effective_permission(owner_id, owner_depts, doc_id=resource_id)
#     else:
#         raise ValueError("未知文件类型，仅支持 document/folder")
#
#     if not permissions["can_edit"]:
#         raise Exception("权限不足，没有当前文件夹/文件的编辑权限")
#
#     permissions = get_effective_permission(owner_id, owner_depts, folder_id=target_folder_id)
#     if not permissions["can_edit"]:
#         raise Exception("权限不足，没有目标文件夹的编辑权限")
#
#     table = "nsyy_gyl.file_document_permission" if resource_type == "document" else "nsyy_gyl.file_folder_permission"
#     resource_column = "document_id" if resource_type == "document" else "folder_id"
#     target_column = "folder_id" if resource_type == "document" else "parent_id"
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     folder = db.query_one(f"select * from {table} where {resource_column} = {resource_id}")
#     if not folder or folder.get('is_deleted', 0):
#         del db
#         raise Exception("当前文件夹/文件已被删除")
#     folder = db.query_one(f"select * from nsyy_gyl.file_folder_permission where folder_id = {target_folder_id}")
#     if not folder or folder.get('is_deleted', 0):
#         del db
#         raise Exception("目标文件夹已被删除")
#
#     db.execute(f"UPDATE {table} SET {target_column} = {target_folder_id} WHERE {resource_column} = {resource_id}",
#                need_commit=True)
#     del db
#
#
# """上传文件"""
#
#
# def upload_file(json_data, upload_files):
#     owner_id = json_data.get("owner_id")
#     owner_depts = json_data.get("owner_depts")
#     folder_id = json_data.get("folder_id")
#     permissions = get_effective_permission(owner_id, owner_depts, folder_id=folder_id)
#     if not permissions["can_upload"]:
#         raise Exception("权限不足，没有当前文件夹的上传权限")
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     folder = db.query_one(f"select * from nsyy_gyl.file_folder where folder_id = {folder_id}")
#     if not folder or folder.get('is_deleted', 0):
#         del db
#         raise Exception("目标文件夹已删除")
#
#     # 上传文件到服务器
#     file_paths = _upload_file(upload_files)
#     if not file_paths:
#         del db
#         raise Exception("文件上传失败")
#
#     args = []
#     for item in file_paths:
#         args.append((json_data.get('type'), item.get('name'), folder_id, item.get('path'), owner_id,
#                      json_data.get('owner'), json_data.get('is_publish'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
#
#     insert_sql = """INSERT INTO nsyy_gyl.file_document (file_type, name, folder_id, storage_path, owner_id,
#                     owner, is_publish, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
#     db.execute_many(insert_sql, args, need_commit=True)
#     del db
#
#
# """下载文件"""
#
# def download_file(json_data):
#     document_id = json_data.get('document_id')
#     version = json_data.get('version')
#     owner_id = json_data.get('owner_id')
#     owner_depts = json_data.get('owner_depts')
#
#     permissions = get_effective_permission(owner_id, owner_depts, doc_id=document_id)
#     if not permissions["can_download"]:
#         raise Exception("权限不足，没有当前文件的下载权限")
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     file = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
#     if not file or file.get('is_deleted', 0):
#         del db
#         raise Exception("文件不存在")
#
#     if file.get('cur_version_id', 1) != int(version):
#         his_file = db.query_one(f"select * from nsyy_gyl.file_document_version "
#                                 f"where document_id = {document_id} and version_id = {int(version)}")
#         if not his_file or his_file.get('is_deleted', 0):
#             del db
#             raise Exception("文件不存在")
#         file['storage_path'] = his_file.get('storage_path', '')
#
#     if file.get('is_publish') == 0 and file.get('owner_id', 0) != owner_id:
#         del db
#         raise Exception("文件未发布无法下载")
#     return file
#
#
# """更新文件名称/发布状态"""
#
#
# def update_file(json_data):
#     owner_id = json_data.get("owner_id")
#     owner_depts = json_data.get("owner_depts")
#     document_id = json_data.get("document_id")
#
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     document = db.query_one(f"select * from nsyy_gyl.file_document where document_id = {document_id}")
#     if not document or document.get('is_deleted', 0):
#         del db
#         raise Exception("该目录已删除")
#
#     if not document or document.get('owner_id', 0) != owner_id:
#         permissions = get_effective_permission(owner_id, owner_depts, doc_id=document_id)
#         if not permissions["can_edit"]:
#             raise Exception("权限不足，没有当前文件的编辑权限")
#
#     condition_sql = ""
#     if json_data.get('file_name', ''):
#         condition_sql = f"name = '{json_data.get('file_name')}'"
#     if 'is_publish' in json_data:
#         condition_sql += f", is_publish = '{json_data.get('is_publish')}'" \
#             if condition_sql else f"is_publish = '{json_data.get('is_publish')}'"
#     db.execute(f"UPDATE nsyy_gyl.file_document SET {condition_sql} WHERE document_id = {document_id}",
#                need_commit=True)
#     del db
#
#
# """查询当前目录内容"""
#
# def merge_with_priority(layers):
#     result = {f: None for f in PERM_FIELDS}
#
#     for layer in layers:
#         if not layer:
#             continue
#         for f in PERM_FIELDS:
#             if result[f] is None:
#                 val = layer.get(f)
#                 if val is not None:
#                     result[f] = bool(val)
#
#     for f in PERM_FIELDS:
#         if result[f] is None:
#             result[f] = False
#
#     return result
#
# def merge_same_level(rows):
#     if not rows:
#         return None
#
#     result = {f: None for f in PERM_FIELDS}
#
#     for row in rows:
#         for f in PERM_FIELDS:
#             if row.get(f) is True:
#                 result[f] = True
#             elif result[f] is None:
#                 result[f] = row.get(f)
#
#     return result
#
#
# """查询目标文件夹的文件和文件夹"""
#
# def query_file_list(json_data):
#     parent_id = json_data.get("folder_id", -1)
#     user_id = json_data.get("owner_id")
#     depts = json_data.get("owner_depts")
#     file_type = json_data.get("file_type")
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#
#     groups = db.query_all(f"select distinct group_id from nsyy_gyl.file_group_permission where user_id = {user_id} ")
#     groups = [g["group_id"] for g in groups]
#
#     # ========= 1. 查询子文件夹 =========
#     folders = db.query_all(f"select * from nsyy_gyl.file_folder where parent_id = {parent_id} "
#                            f"and file_type = {file_type} and is_deleted = 0")
#
#     # ========= 2. 查询文件 =========
#     documents = db.query_all(f"select * from nsyy_gyl.file_document where folder_id = {parent_id} "
#                              f"and file_type = {file_type} and is_deleted = 0")
#
#     folder_ids = [f["folder_id"] for f in folders]
#     doc_ids = []
#     for d in documents:
#         if d.get('is_publish', 0) == 1:
#             doc_ids.append(d["document_id"])
#         else:
#             if d.get('owner_id', 0) == user_id:
#                 doc_ids.append(d["document_id"])
#
#
#     # ========= 3. 批量加载权限 =========
#     folder_perm_map = {}
#     doc_perm_map = {}
#
#     if folder_ids:
#         format_ids = ",".join(folder_ids)
#         folder_perm = db.query_all(f"select * from nsyy_gyl.file_folder_permission where folder_id in ({format_ids})")
#         for p in folder_perm:
#             folder_perm_map.setdefault(p["folder_id"], []).append(p)
#
#     if doc_ids:
#         format_ids = ",".join(doc_ids)
#         doc_perm = db.query_all(f"select * from nsyy_gyl.file_document_permission where document_id in ({format_ids})")
#         for p in doc_perm:
#             doc_perm_map.setdefault(p["document_id"], []).append(p)
#
#     visible_folders = []
#     visible_documents = []
#     # ========= 4. 过滤文件夹 =========
#     for f in folders:
#         perms = folder_perm_map.get(f["id"], [])
#
#         layers = [
#             next((p for p in perms if p.get("user_id") == user_id), None),
#             merge_same_level([p for p in perms if p.get("group_id") in groups]),
#             merge_same_level([p for p in perms if p.get("dept_id") in depts]),
#         ]
#
#         effective = merge_with_priority(layers)
#
#         if effective["can_view"]:
#             visible_folders.append(f)
#
#     # ========= 5. 过滤文件 =========
#     for d in documents:
#         perms = doc_perm_map.get(d["id"], [])
#
#         layers = [
#             next((p for p in perms if p.get("user_id") == user_id), None),
#             merge_same_level([p for p in perms if p.get("group_id") in groups]),
#             merge_same_level([p for p in perms if p.get("dept_id") in depts]),
#         ]
#
#         # 如果文件没单独权限 → 回退当前文件夹权限
#         if not any(layers):
#             folder_perms = folder_perm_map.get(d["folder_id"], [])
#             layers = [
#                 next((p for p in folder_perms if p.get("user_id") == user_id), None),
#                 merge_same_level([p for p in folder_perms if p.get("group_id") in groups]),
#                 merge_same_level([p for p in folder_perms if p.get("dept_id") in depts]),
#             ]
#
#         effective = merge_with_priority(layers)
#
#         if effective["can_view"]:
#             visible_documents.append(d)
#
#     return {"folders": visible_folders, "documents": visible_documents}
#
#
# def _upload_file(files):
#     if not files:
#         return ''
#     try:
#         import os
#         # 确保上传目录存在
#         path = f"{file_config.upload_path}/{datetime.now().strftime('%Y%m%d')}"
#         if not os.path.exists(path):
#             os.makedirs(path)
#
#         paths = []
#         for file in files:
#             # 安全保存文件
#             file_path = os.path.join(path, f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename}")
#             file.save(file_path)
#             paths.append({"name": file.filename, "path": file_path})
#         return paths
#     except Exception as e:
#         logger.error(f"文件上传失败 {e}")
#     return []
#
#
#
# """文件/文件夹 权限查询 返回用户对 文档 或 文件夹 的最终权限"""
#
#
# def empty_perm():
#     return {f: False for f in PERM_FIELDS}
#
#
# def merge_perm_rows(rows, result=None):
#     """多条组权限 OR 合并"""
#     result = empty_perm()
#     for row in rows:
#         for f in PERM_FIELDS:
#             result[f] = result[f] or bool(row[f])
#     return result
#
#
# def get_effective_permission(user_id, depts, doc_id=None, folder_id=None):
#     result = None
#     db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
#                 global_config.DB_DATABASE_GYL)
#     # 查询用户所属科室/群组
#     groups = db.query_all(f"select distinct group_id from nsyy_gyl.file_group_membership where user_id = '{user_id}'")
#     # 1. 文档权限
#     if doc_id:
#         # 1.1 文档-组/科室权限
#         if groups or depts:
#             sql = """SELECT can_view, can_edit, can_delete, can_download
#             FROM nsyy_gyl.file_document_permission WHERE document_id=%s AND ("""
#             params = [doc_id]
#
#             conditions = []
#             if groups:
#                 conditions.append(f"group_id IN ({','.join(['%s'] * len(groups))})")
#                 params.extend(groups)
#
#             if depts:
#                 conditions.append(f"dept_id IN ({','.join(['%s'] * len(depts))})")
#                 params.extend(depts)
#
#             sql += " OR ".join(conditions) + ")"
#             rows = db.execute(sql, tuple(params))
#             if rows:
#                 result = merge_perm_rows(rows, result)
#
#         # 1.2 文档-用户权限
#         row = db.query_one(f"""SELECT can_view, can_edit, can_delete, can_download
#             FROM nsyy_gyl.file_document_permission WHERE document_id={doc_id} AND user_id='{user_id}' LIMIT 1""")
#         if row:
#             result = {f: bool(row[f]) or result[f] for f in PERM_FIELDS}
#
#
#         # 如果没命中文档权限 → 获取 folder_id
#         if not folder_id:
#             doc = db.query_one(f"SELECT folder_id FROM nsyy_gyl.file_document WHERE document_id={doc_id}")
#             if not doc or not doc["folder_id"]:
#                 return empty_perm()
#             folder_id = doc["folder_id"]
#
#     # 2. 文件夹权限
#     if folder_id:
#         # 2.1 文件夹-组/科室权限
#         if groups or depts:
#             sql = """SELECT can_view, can_edit, can_delete, can_download, can_upload
#             FROM nsyy_gyl.file_folder_permission WHERE folder_id=%s AND ( """
#             params = [folder_id]
#             conditions = []
#
#             if groups:
#                 conditions.append(f"group_id IN ({','.join(['%s'] * len(groups))})")
#                 params.extend(groups)
#
#             if depts:
#                 conditions.append(f"dept_id IN ({','.join(['%s'] * len(depts))})")
#                 params.extend(depts)
#
#             sql += " OR ".join(conditions) + ")"
#             rows = db.execute(sql, tuple(params))
#             if rows:
#                 result = merge_perm_rows(rows)
#
#         # 2.2 文件夹-用户权限
#
#         row = db.query_one(f"""SELECT can_view, can_edit, can_delete, can_download, can_upload
#             FROM nsyy_gyl.file_folder_permission WHERE folder_id={folder_id} AND user_id='{user_id}' LIMIT 1""")
#         if row:
#             result = {f: bool(row[f]) or result[f] for f in PERM_FIELDS}
#             return {f: bool(row[f]) for f in PERM_FIELDS}
#
#     del db
#     # 3. 默认 deny
#     return result if result else empty_perm()
#
#
#
#
#

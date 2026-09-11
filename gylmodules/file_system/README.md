
# 科室
```mysql-sql
-- ----------------------------
-- Table structure for file_dept
-- ----------------------------
DROP TABLE IF EXISTS `file_dept`;
CREATE TABLE `file_dept` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `keshibqbz` int DEFAULT NULL,
  `zhigongid` int DEFAULT NULL,
  `zhigongxm` varchar(255) DEFAULT NULL,
  `zhigonggh` varchar(10) DEFAULT NULL,
  `zuzhiid` int DEFAULT NULL,
  `zuzhimc` varchar(255) DEFAULT NULL,
  `zhigongdjmc` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_constraint` (`zhigongid`,`zuzhiid`)
) ENGINE=InnoDB AUTO_INCREMENT=9459 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for file_dept_permission
-- ----------------------------
DROP TABLE IF EXISTS `file_dept_permission`;
CREATE TABLE `file_dept_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dept_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '',
  `user_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `unique_constraint` (`user_id`,`dept_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1155 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

```

# 文件 & 版本

```mysql-sql

-- ----------------------------
-- Table structure for file_document_permission
-- ----------------------------
DROP TABLE IF EXISTS `file_document_permission`;
CREATE TABLE `file_document_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document_id` bigint DEFAULT NULL COMMENT '文件id',
  `user_id` varchar(10) DEFAULT NULL COMMENT '用户his id',
  `group_id` bigint DEFAULT NULL COMMENT '群组id',
  `dept_id` varchar(10) DEFAULT NULL COMMENT '科室id',
  `can_view` int DEFAULT '0' COMMENT '是否具有查看权限',
  `can_edit` int DEFAULT '0' COMMENT '是否具有编辑权限',
  `can_delete` int DEFAULT '0' COMMENT '是否具有删除权限',
  `can_download` int DEFAULT '0' COMMENT '是否具有下载权限',
  `can_manage` int DEFAULT '0' COMMENT '是否具有管理权限',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for file_document_version
-- ----------------------------
DROP TABLE IF EXISTS `file_document_version`;
CREATE TABLE `file_document_version` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document_id` bigint DEFAULT NULL,
  `version_id` int DEFAULT NULL,
  `storage_path` varchar(255) DEFAULT NULL,
  `owner_id` int DEFAULT NULL,
  `owner` varchar(50) DEFAULT NULL,
  `comment` text COMMENT '版本变更说明',
  `is_deleted` int DEFAULT '0',
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for file_document
-- ----------------------------
DROP TABLE IF EXISTS `file_document`;
CREATE TABLE `file_document` (
  `document_id` bigint NOT NULL AUTO_INCREMENT,
  `file_type` int DEFAULT NULL COMMENT '1=个人 2=组别 3=科室 4=院级',
  `name` varchar(255) DEFAULT NULL,
  `folder_id` bigint DEFAULT NULL,
  `cur_version_id` int NOT NULL DEFAULT '1',
  `storage_path` varchar(255) DEFAULT NULL,
  `owner_id` varchar(10) DEFAULT NULL,
  `owner` varchar(50) DEFAULT NULL,
  `sort_order` int DEFAULT '1',
  `is_deleted` int DEFAULT '0',
  `is_publish` int DEFAULT '0',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`document_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


```

## 文件夹 


```mysql-sql
-- ----------------------------
-- Table structure for file_folder_permission
-- ----------------------------
DROP TABLE IF EXISTS `file_folder_permission`;
CREATE TABLE `file_folder_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `folder_id` bigint DEFAULT NULL COMMENT '目录id',
  `user_id` varchar(10) DEFAULT NULL COMMENT '用户权限',
  `group_id` bigint DEFAULT '0' COMMENT '支持查看的群组',
  `dept_id` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '支持查看的科室',
  `can_view` int DEFAULT '0' COMMENT '是否具有查看权限',
  `can_edit` int DEFAULT '0' COMMENT '是否具有编辑权限',
  `can_delete` int DEFAULT '0' COMMENT '是否具有删除权限',
  `can_manage` int DEFAULT '0' COMMENT '是否具有管理权限',
  `can_upload` int DEFAULT NULL COMMENT '是否允许上传文件',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_constraint` (`folder_id`,`group_id`,`dept_id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ----------------------------
-- Table structure for file_folder
-- ----------------------------
DROP TABLE IF EXISTS `file_folder`;
CREATE TABLE `file_folder` (
  `folder_id` bigint NOT NULL AUTO_INCREMENT,
  `file_type` int DEFAULT NULL COMMENT '1=个人 2=组别 3=科室 4=院级',
  `name` varchar(255) DEFAULT NULL,
  `parent_id` bigint DEFAULT '0',
  `root_id` bigint DEFAULT NULL COMMENT '根目录id',
  `owner_id` varchar(10) DEFAULT NULL,
  `owner` varchar(50) DEFAULT NULL,
  `sort_order` int DEFAULT '1',
  `is_deleted` int DEFAULT '0',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`folder_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

权限优先级：文档用户权限 > 文档组/科室权限 > 文件夹用户权限 > 文件夹组/科室权限 > 默认 deny

如果文件没设置单独权限，就回退到它所在的文件夹权限。
```


# 群组

```mysql-sql
-- ----------------------------
-- Table structure for group
-- ----------------------------
DROP TABLE IF EXISTS `group`;
CREATE TABLE `group` (
  `group_id` bigint NOT NULL AUTO_INCREMENT COMMENT '群组id',
  `group_type` int DEFAULT '1' COMMENT '群类型[1:内部群;2:医患群;] 3 急诊白班 4 急诊夜班',
  `group_name` varchar(255) DEFAULT NULL COMMENT '群组名称',
  `owner_id` varchar(50) DEFAULT NULL COMMENT '群组创建者id',
  `owner_name` varchar(255) DEFAULT NULL COMMENT '群组创建者',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `description` varchar(255) DEFAULT NULL COMMENT '群组描述',
  `mail_account` varchar(255) DEFAULT NULL COMMENT '群组邮箱账号',
  `user_mail_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '群主邮箱账号',
  `is_public` int DEFAULT '1' COMMENT '是否公开可见[1:是;0:否;]',
  `group_state` int DEFAULT '1' COMMENT '1=正常 0=解散',
  `mail_account_state` int DEFAULT '0' COMMENT '0 待创建 1 已创建',
  `group_type_id` varchar(255) DEFAULT NULL COMMENT '外部群标识 医患群hash（p ID，doc id） 医生大群（doc id） ',
  `follower_id` varchar(255) DEFAULT NULL COMMENT '关注的医生id',
  PRIMARY KEY (`group_id`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for group_member
-- ----------------------------
DROP TABLE IF EXISTS `group_member`;
CREATE TABLE `group_member` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` bigint DEFAULT NULL COMMENT '群组id',
  `user_id` varchar(50) DEFAULT NULL COMMENT '成员id',
  `user_name` varchar(255) DEFAULT NULL COMMENT '成员名称',
  `user_mail_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用户邮箱账号',
  `join_type` int DEFAULT NULL COMMENT '入群方式（0 - 邀请/ 1-申请）',
  `state` int DEFAULT NULL COMMENT '0-申请中 1-加入群 2-移出群 3-拒绝加入',
  `is_reply` int DEFAULT '0' COMMENT '是否已响应 0 未响应 1 已响应',
  `allow_edit` int DEFAULT '0' COMMENT '0不允许 1=允许编辑群组 2=群主',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `mail_state` int DEFAULT '0' COMMENT '0=待加入群组 1=已加入群组',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_constraint` (`group_id`,`user_id`),
  UNIQUE KEY `unique_constraint1` (`user_id`,`group_id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


```





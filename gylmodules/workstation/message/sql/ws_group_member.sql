/*
 Navicat Premium Dump SQL

 Source Server         : yanliang
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : 127.0.0.1:3306
 Source Schema         : nsyy_gyl

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001

 Date: 18/09/2024 18:05:10
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_group_member
-- ----------------------------
DROP TABLE IF EXISTS `ws_group_member`;
CREATE TABLE `ws_group_member` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(50) DEFAULT NULL,
  `join_type` int DEFAULT NULL COMMENT '入群方式（0 - 邀请/ 1-申请）',
  `state` int DEFAULT NULL COMMENT '0-申请中 1-加入群 2-移出群 3-拒绝加入',
  `timer` datetime DEFAULT NULL,
  `is_reply` int DEFAULT '0' COMMENT '是否已响应 0 未响应 1 已响应',
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

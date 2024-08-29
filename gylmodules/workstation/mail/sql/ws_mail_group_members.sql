/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.3.12
 Source Server Type    : MySQL
 Source Server Version : 80039 (8.0.39-0ubuntu0.20.04.1)
 Source Host           : 192.168.3.12:3306
 Source Schema         : nsyy_gyl

 Target Server Type    : MySQL
 Target Server Version : 80039 (8.0.39-0ubuntu0.20.04.1)
 File Encoding         : 65001

 Date: 21/08/2024 08:59:34
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_mail_group_members
-- ----------------------------
DROP TABLE IF EXISTS `ws_mail_group_members`;
CREATE TABLE `ws_mail_group_members` (
  `id` int NOT NULL AUTO_INCREMENT,
  `mail_group_id` int NOT NULL COMMENT '群组 id',
  `user_account` varchar(100) DEFAULT NULL,
  `user_name` varchar(100) DEFAULT NULL,
  `is_show` int DEFAULT '1' COMMENT '是否展示（用户移除群组仅仅是不展示，但是群组还在）',
  `timer` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

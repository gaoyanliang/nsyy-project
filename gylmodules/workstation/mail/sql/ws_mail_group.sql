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

 Date: 18/09/2024 18:02:15
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_mail_group
-- ----------------------------
DROP TABLE IF EXISTS `ws_mail_group`;
CREATE TABLE `ws_mail_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL COMMENT '群组名称',
  `account` varchar(20) DEFAULT NULL COMMENT '群组邮箱账号',
  `description` varchar(100) DEFAULT NULL COMMENT '群组说明',
  `user_account` varchar(100) DEFAULT NULL COMMENT '创建者id',
  `user_name` varchar(100) DEFAULT NULL COMMENT '创建者名称',
  `timer` datetime DEFAULT NULL,
  `is_public` int DEFAULT NULL COMMENT '是否公开 0不公开 1公开',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

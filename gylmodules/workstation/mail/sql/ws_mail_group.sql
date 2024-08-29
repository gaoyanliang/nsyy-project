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

 Date: 21/08/2024 08:59:25
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
  `description` varchar(100) DEFAULT NULL COMMENT '群组说明',
  `user_account` varchar(100) DEFAULT NULL COMMENT '创建者id',
  `user_name` varchar(100) DEFAULT NULL COMMENT '创建者名称',
  `timer` datetime DEFAULT NULL,
  `is_public` int DEFAULT NULL COMMENT '是否公开 0不公开 1公开',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

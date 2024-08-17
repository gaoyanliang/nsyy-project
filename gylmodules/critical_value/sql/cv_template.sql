/*
 Navicat Premium Data Transfer

 Source Server         : 192.168.3.12
 Source Server Type    : MySQL
 Source Server Version : 80039 (8.0.39-0ubuntu0.20.04.1)
 Source Host           : 192.168.3.12:3306
 Source Schema         : nsyy_gyl

 Target Server Type    : MySQL
 Target Server Version : 80039 (8.0.39-0ubuntu0.20.04.1)
 File Encoding         : 65001

 Date: 17/08/2024 11:37:16
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cv_template
-- ----------------------------
DROP TABLE IF EXISTS `cv_template`;
CREATE TABLE `cv_template` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cv_name` varchar(255) DEFAULT NULL COMMENT '危机值名称',
  `cv_result` varchar(255) DEFAULT NULL COMMENT '危机值内容',
  `cv_result_abb` varchar(255) DEFAULT NULL COMMENT '危机值简写',
  `cv_result_pinyin_abb` varchar(255) DEFAULT NULL COMMENT '危机值拼音简写',
  `cv_source` int DEFAULT NULL COMMENT '危机值来源',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=60 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

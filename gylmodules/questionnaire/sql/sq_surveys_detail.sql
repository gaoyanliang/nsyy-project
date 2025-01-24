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

 Date: 24/12/2024 10:48:16
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for sq_surveys_detail
-- ----------------------------
DROP TABLE IF EXISTS `sq_surveys_detail`;
CREATE TABLE `sq_surveys_detail` (
  `id` int NOT NULL,
  `re_id` int DEFAULT NULL COMMENT '问卷记录 id',
  `sick_id` int DEFAULT NULL COMMENT '病人 id',
  `visit_date` varchar(12) DEFAULT NULL COMMENT '就诊日期',
  `zhusu` varchar(512) DEFAULT NULL,
  `zhusu_remark` varchar(512) DEFAULT NULL,
  `xianbingshi` varchar(1024) DEFAULT NULL,
  `xianbingshi_remark` varchar(1024) DEFAULT NULL,
  `jiwangshi` varchar(1024) DEFAULT NULL,
  `jiwangshi_remark` varchar(1024) DEFAULT NULL,
  `tigejiancha` varchar(1024) DEFAULT NULL,
  `tigejiancha_remark` varchar(1024) DEFAULT NULL,
  `zhuankejiancha` varchar(1024) DEFAULT NULL,
  `zhuankejiancha_remark` varchar(1024) DEFAULT NULL,
  `fuzhujiancha` varchar(1024) DEFAULT NULL,
  `fuzhujiancha_remark` varchar(1024) DEFAULT NULL,
  `fuzhujiancha_ret` varchar(1024) DEFAULT NULL,
  `fuzhujiancha_ret_remark` varchar(1024) DEFAULT NULL,
  `chubuzhenduan` varchar(512) DEFAULT NULL,
  `yijian` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

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

 Date: 17/08/2024 11:39:21
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for appt_scheduling
-- ----------------------------
DROP TABLE IF EXISTS `appt_scheduling`;
CREATE TABLE `appt_scheduling` (
  `id` int NOT NULL AUTO_INCREMENT,
  `did` int DEFAULT NULL COMMENT '医生id',
  `rid` int DEFAULT NULL COMMENT '坐诊房间',
  `pid` int DEFAULT NULL COMMENT '坐诊项目',
  `worktime` int DEFAULT NULL COMMENT '工作日，星期几',
  `ampm` int DEFAULT NULL COMMENT '上午下午',
  `state` int DEFAULT '1' COMMENT '状态：1=可预约，2=已满，3=停诊',
  `change_reason` varchar(512) DEFAULT NULL COMMENT '换班原因说明',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1499 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

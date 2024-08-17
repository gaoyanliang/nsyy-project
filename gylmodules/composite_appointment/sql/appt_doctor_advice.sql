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

 Date: 17/08/2024 11:38:14
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for appt_doctor_advice
-- ----------------------------
DROP TABLE IF EXISTS `appt_doctor_advice`;
CREATE TABLE `appt_doctor_advice` (
  `id` int NOT NULL AUTO_INCREMENT,
  `appt_id` int DEFAULT NULL,
  `pay_id` varchar(40) DEFAULT NULL,
  `advice_desc` varchar(510) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '医嘱明细',
  `dept_id` int DEFAULT NULL COMMENT '执行科室id',
  `dept_name` varchar(255) DEFAULT NULL,
  `price` decimal(10,4) DEFAULT NULL,
  `state` int DEFAULT '0' COMMENT '0未缴费 1 自主交费 2住院缴费',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=718 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

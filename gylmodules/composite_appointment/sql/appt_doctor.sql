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

 Date: 17/08/2024 11:38:03
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for appt_doctor
-- ----------------------------
DROP TABLE IF EXISTS `appt_doctor`;
CREATE TABLE `appt_doctor` (
  `id` int NOT NULL AUTO_INCREMENT,
  `dept_id` int DEFAULT NULL,
  `dept_name` varchar(50) DEFAULT NULL,
  `no` int DEFAULT NULL COMMENT '员工号',
  `name` varchar(50) DEFAULT NULL,
  `his_name` varchar(50) DEFAULT NULL,
  `career` varchar(50) DEFAULT NULL COMMENT '职称',
  `fee` decimal(10,4) DEFAULT NULL COMMENT '挂号费',
  `appointment_id` int DEFAULT NULL COMMENT '医生预约id',
  `photo` varchar(100) DEFAULT NULL COMMENT '医生图片',
  `desc` varchar(512) DEFAULT NULL COMMENT '医生简介',
  `phone` varchar(20) DEFAULT NULL COMMENT '医生联系方式',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=488 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

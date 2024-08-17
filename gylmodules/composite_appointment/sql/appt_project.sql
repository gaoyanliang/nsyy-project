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

 Date: 17/08/2024 11:38:50
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for appt_project
-- ----------------------------
DROP TABLE IF EXISTS `appt_project`;
CREATE TABLE `appt_project` (
  `id` int NOT NULL AUTO_INCREMENT,
  `proj_type` int DEFAULT NULL COMMENT '1 门诊项目 2 院内项目',
  `proj_name` varchar(255) DEFAULT NULL COMMENT '项目名称',
  `location_id` varchar(50) DEFAULT NULL COMMENT '位置码',
  `dept_id` int DEFAULT NULL,
  `dept_name` varchar(255) DEFAULT NULL,
  `is_group` int DEFAULT '0' COMMENT '是否分组',
  `nsnum` int DEFAULT NULL COMMENT '半天号源数量',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

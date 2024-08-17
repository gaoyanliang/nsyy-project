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

 Date: 17/08/2024 11:37:00
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cv_site
-- ----------------------------
DROP TABLE IF EXISTS `cv_site`;
CREATE TABLE `cv_site` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_dept` varchar(80) DEFAULT NULL,
  `site_dept_id` varchar(20) DEFAULT NULL,
  `site_ip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `site_ward` varchar(100) DEFAULT NULL,
  `site_ward_id` varchar(100) DEFAULT NULL,
  `time` datetime DEFAULT CURRENT_TIMESTAMP,
  `dept_phone` varchar(20) DEFAULT NULL COMMENT '科室主任电话',
  `ward_phone` varchar(20) DEFAULT NULL COMMENT '病区电话',
  `doctor_phone` varchar(20) DEFAULT NULL COMMENT '值班医生电话',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_ip` (`site_ip`)
) ENGINE=InnoDB AUTO_INCREMENT=650 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

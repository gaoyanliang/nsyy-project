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

 Date: 17/08/2024 11:36:36
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for alert_fail_log
-- ----------------------------
DROP TABLE IF EXISTS `alert_fail_log`;
CREATE TABLE `alert_fail_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip` varchar(20) DEFAULT NULL,
  `time` datetime DEFAULT NULL,
  `log` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ip` (`ip`)
) ENGINE=InnoDB AUTO_INCREMENT=565 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

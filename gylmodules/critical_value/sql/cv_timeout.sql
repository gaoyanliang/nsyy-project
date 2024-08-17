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

 Date: 17/08/2024 11:37:27
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cv_timeout
-- ----------------------------
DROP TABLE IF EXISTS `cv_timeout`;
CREATE TABLE `cv_timeout` (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` varchar(20) DEFAULT NULL,
  `nurse_recv_timeout` int DEFAULT NULL,
  `doctor_recv_timeout` int DEFAULT NULL,
  `total_timeout` int DEFAULT NULL,
  `nurse_send_timeout` int DEFAULT NULL,
  `doctor_handle_timeout` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_type` (`type`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

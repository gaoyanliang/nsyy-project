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

 Date: 05/11/2024 14:23:01
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for hbot_treatment_record
-- ----------------------------
DROP TABLE IF EXISTS `hbot_treatment_record`;
CREATE TABLE `hbot_treatment_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `register_id` varchar(50) NOT NULL,
  `record_id` varchar(30) NOT NULL,
  `patient_id` varchar(30) DEFAULT NULL,
  `execution_status` int DEFAULT NULL COMMENT '执行状态 0=待执行 1=执行 2=取消本次 3=取消所有',
  `record_date` varchar(11) DEFAULT NULL COMMENT '执行记录日期',
  `record_time` varchar(11) DEFAULT NULL,
  `record_info` json DEFAULT NULL,
  `sign_info` json DEFAULT NULL COMMENT '签名信息',
  `pay_status` int DEFAULT '0' COMMENT '付款状态',
  `pay_num` float DEFAULT NULL COMMENT '付款数量',
  `pay_no` varchar(20) DEFAULT NULL,
  `operator` varchar(50) DEFAULT NULL COMMENT '操作人',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_constraint` (`register_id`,`patient_id`,`record_date`),
  KEY `unique_tid` (`register_id`)
) ENGINE=InnoDB AUTO_INCREMENT=168 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

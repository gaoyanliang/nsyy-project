/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.3.12
 Source Server Type    : MySQL
 Source Server Version : 80040 (8.0.40-0ubuntu0.20.04.1)
 Source Host           : 192.168.3.12:3306
 Source Schema         : nsyy_gyl

 Target Server Type    : MySQL
 Target Server Version : 80040 (8.0.40-0ubuntu0.20.04.1)
 File Encoding         : 65001

 Date: 14/11/2024 10:13:35
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for question_survey_list
-- ----------------------------
DROP TABLE IF EXISTS `question_survey_list`;
CREATE TABLE `question_survey_list` (
  `id` int NOT NULL AUTO_INCREMENT,
  `patient_name` varchar(255) DEFAULT NULL COMMENT '患者名字',
  `card_no` varchar(50) DEFAULT NULL COMMENT '身份证号/就诊卡号',
  `tpl_type` int DEFAULT NULL COMMENT '问题类型',
  `tpl_type_detail` int DEFAULT NULL COMMENT '问题类别',
  `patient_info` json DEFAULT NULL COMMENT '患者信息',
  `ans_list` json DEFAULT NULL COMMENT '问题答案',
  `ans_data` json DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `medical_card_no` varchar(20) DEFAULT NULL COMMENT '就诊卡号',
  `id_card_no` varchar(20) DEFAULT NULL COMMENT '身份证号',
  `doctor` varchar(50) DEFAULT NULL COMMENT '医生名字',
  `operator` varchar(50) DEFAULT NULL COMMENT '操作人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=112 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

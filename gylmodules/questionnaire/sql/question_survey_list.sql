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

 Date: 31/10/2024 15:03:28
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

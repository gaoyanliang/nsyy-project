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

 Date: 05/11/2024 14:22:50
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for hbot_register_record
-- ----------------------------
DROP TABLE IF EXISTS `hbot_register_record`;
CREATE TABLE `hbot_register_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `register_id` varchar(50) NOT NULL COMMENT '登记号',
  `patient_type` int DEFAULT NULL COMMENT '患者类型',
  `patient_id` varchar(30) DEFAULT NULL COMMENT '住院号/门诊号',
  `comp_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '12=总院 32=康复中医院',
  `execution_status` int DEFAULT NULL COMMENT '0=未开始 1=执行中 2=已取消 3=已完成',
  `medical_order_status` int DEFAULT NULL COMMENT '0=未开医嘱 1=已开医嘱',
  `start_date` varchar(11) DEFAULT NULL COMMENT '开始日期',
  `execution_days` int DEFAULT NULL COMMENT '执行天数',
  `start_time` varchar(6) DEFAULT NULL COMMENT '开始时间',
  `execution_duration` int DEFAULT NULL COMMENT '执行时长（分钟）',
  `patient_info` json DEFAULT NULL COMMENT '患者信息：姓名/性别/年龄/住院号/科室/床号/诊断/疗程/联系电话',
  `doc1` json DEFAULT NULL COMMENT '高压氧治疗知情同意书',
  `doc2` json DEFAULT NULL COMMENT '高压氧患者入舱安全教育与心理指导',
  `medical_order_info` json DEFAULT NULL COMMENT '医嘱信息',
  `register_time` datetime DEFAULT NULL COMMENT '登记时间',
  `sign_info` json DEFAULT NULL COMMENT '签名信息',
  `registrant` varchar(50) DEFAULT NULL COMMENT '登记人',
  `operator` varchar(50) DEFAULT NULL COMMENT '操作人',
  PRIMARY KEY (`id`,`register_id`) USING BTREE,
  UNIQUE KEY `unique_rid` (`register_id`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

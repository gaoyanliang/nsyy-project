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

 Date: 17/08/2024 11:36:51
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cv_info
-- ----------------------------
DROP TABLE IF EXISTS `cv_info`;
CREATE TABLE `cv_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cv_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '危机值编号（系统中的上报id）',
  `alertdt` datetime DEFAULT NULL COMMENT '上报时间',
  `state` int DEFAULT NULL COMMENT '状态',
  `cv_source` int DEFAULT NULL COMMENT '0人工 1系统',
  `alertman` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '上报人',
  `alertman_name` varchar(64) DEFAULT NULL COMMENT '上报人',
  `alertman_pers_id` varchar(20) DEFAULT NULL,
  `alert_dept_id` int DEFAULT NULL COMMENT '上报科室id',
  `alert_dept_name` varchar(100) DEFAULT NULL COMMENT '上报科室名称',
  `patient_type` int DEFAULT NULL COMMENT '患者类型1=门诊,2=急诊,3=住院,4=体检',
  `patient_treat_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '门诊号/住院号',
  `patient_name` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者名字',
  `patient_gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者性别 1男2女',
  `patient_age` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者年龄',
  `patient_phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者联系方式',
  `patient_bed_num` varchar(10) DEFAULT NULL COMMENT '床号',
  `req_docno` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '开单医生',
  `ward_id` int DEFAULT NULL COMMENT '所属病区id',
  `ward_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '病区名称',
  `dept_id` int DEFAULT NULL COMMENT '所属科室 id',
  `dept_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '科室名称',
  `cv_type` varchar(100) DEFAULT NULL COMMENT '危机值类型',
  `cv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '危机值名称',
  `cv_result` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '危机值',
  `cv_unit` varchar(40) DEFAULT NULL COMMENT '危机值单位',
  `cv_ref` varchar(512) DEFAULT NULL COMMENT '参考值',
  `cv_flag` varchar(2) DEFAULT NULL COMMENT '结果状态标志  H偏高、HH偏高报警、L偏低、LL偏低报警、P阳性、E错误',
  `redo_flag` varchar(2) DEFAULT NULL COMMENT '复查标志  0＝无需复查，1＝需要复查，2＝已经复查',
  `alertrules` varchar(255) DEFAULT NULL COMMENT '危机值违反的规则',
  `handle_doctor_id` int DEFAULT NULL COMMENT '处理医生id',
  `handle_doctor_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '处理医生',
  `handle_time` datetime DEFAULT NULL COMMENT '医生处理时间',
  `analysis` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '原因分析',
  `method` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '处理办法',
  `time` datetime DEFAULT NULL COMMENT '创建时间',
  `nurse_recv_id` int DEFAULT NULL COMMENT '接收护士id',
  `nurse_recv_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '接收护士名字',
  `nurse_recv_time` datetime DEFAULT NULL COMMENT '护士接收时间',
  `nurse_recv_info` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '护士确认信息',
  `nurse_send_time` datetime DEFAULT NULL,
  `nursing_record` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '护理记录',
  `nursing_record_time` datetime DEFAULT NULL COMMENT '护理记录时间',
  `doctor_recv_id` int DEFAULT NULL COMMENT '接收医生id',
  `doctor_recv_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '接收医生名字',
  `doctor_recv_time` datetime DEFAULT NULL COMMENT '医生接收时间',
  `is_nurse_recv_timeout` int DEFAULT '0',
  `is_nurse_send_timeout` int DEFAULT '0',
  `is_doctor_recv_timeout` int DEFAULT '0',
  `is_doctor_handle_timeout` int DEFAULT '0' COMMENT '医生处理是否超时',
  `is_timeout` int DEFAULT '0',
  `nurse_recv_timeout` int DEFAULT NULL,
  `nurse_send_timeout` int DEFAULT NULL,
  `doctor_recv_timeout` int DEFAULT NULL,
  `doctor_handle_timeout` int DEFAULT '360' COMMENT '医生处理超时时间',
  `total_timeout` int DEFAULT '600' COMMENT '总超时时间',
  `instrna` varchar(100) DEFAULT NULL,
  `report_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_cv_id_cv_source` (`cv_id`,`cv_source`)
) ENGINE=InnoDB AUTO_INCREMENT=7953 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

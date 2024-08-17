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

 Date: 17/08/2024 11:38:58
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for appt_record
-- ----------------------------
DROP TABLE IF EXISTS `appt_record`;
CREATE TABLE `appt_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `father_id` int DEFAULT NULL,
  `type` int DEFAULT NULL COMMENT '预约类型 （1=微信小程序预约  2=现场预约）',
  `state` int DEFAULT '0' COMMENT '0=保留 1=已预约 2=排队中 3=处理中 4=过号 5=已完成 6=已取消',
  `id_card_no` varchar(20) DEFAULT NULL COMMENT '预约人身份证号',
  `openid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '微信号唯一标识（预约类型=1时，需要提供）',
  `patient_id` int DEFAULT NULL COMMENT '门诊号',
  `patient_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '预约人名称',
  `pid` int DEFAULT NULL COMMENT '预约项目id',
  `ptype` int DEFAULT NULL COMMENT '预约项目类型',
  `pname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '预约项目名称',
  `doc_id` int DEFAULT NULL,
  `doc_his_name` varchar(125) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '医生名字',
  `doc_dept_id` int DEFAULT NULL,
  `price` decimal(10,4) DEFAULT NULL,
  `rid` int DEFAULT NULL,
  `room` varchar(20) DEFAULT NULL COMMENT '房间号',
  `book_date` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '预约日期 (2024-04-13)',
  `book_period` int DEFAULT NULL COMMENT '预约时间段',
  `time_slot` int DEFAULT NULL COMMENT '预估时间段，每个小时为一个时间段',
  `level` int DEFAULT NULL COMMENT '预约紧急程度',
  `location_id` varchar(40) DEFAULT NULL COMMENT '位置id',
  `sign_in_num` int DEFAULT NULL COMMENT '签到号码',
  `sign_in_time` datetime DEFAULT NULL COMMENT '签到时间',
  `is_doc_change` int DEFAULT '0' COMMENT '医生是否改变',
  `create_time` datetime DEFAULT NULL,
  `cancel_time` datetime DEFAULT NULL COMMENT '取消预约时间',
  `pay_no` varchar(20) DEFAULT NULL,
  `pay_state` int DEFAULT '1' COMMENT '''unpaid'': 0, ''oa_pay'': 1, ''his_pay'': 2, ''oa_his_both_pay'': 3, ''oa_refunded'': 4',
  `sort_num` int DEFAULT '9999' COMMENT '排序字段',
  `sort_info` varchar(255) DEFAULT NULL COMMENT '调整顺序原因',
  `wait_num` int DEFAULT '0' COMMENT '等待人数',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1382 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

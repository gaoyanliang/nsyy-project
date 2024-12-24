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

 Date: 23/12/2024 09:08:09
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for hbot_sign_info
-- ----------------------------
DROP TABLE IF EXISTS `hbot_sign_info`;
CREATE TABLE `hbot_sign_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `register_id` varchar(50) DEFAULT NULL COMMENT '登记 id',
  `record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者住院号 治疗记录签名需要',
  `patient_name` varchar(50) DEFAULT NULL,
  `sign_type` int DEFAULT NULL COMMENT '签名类型 1=知情同意书 2=心理治疗 3=治疗记录',
  `user_id` varchar(20) DEFAULT NULL,
  `doctor_name` varchar(255) DEFAULT NULL COMMENT '签名医生名字',
  `doc_sign` json DEFAULT NULL COMMENT '知情同意书医生签名',
  `doc_ts_sign` json DEFAULT NULL COMMENT '医生时间戳签名',
  `pdf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'pdf 地址',
  `pat_hand_sign` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者手签图片',
  `pat_fingerprint` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者指纹图片',
  `pat_face_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '患者人脸图片',
  `sign_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_key_constraint` (`register_id`,`sign_type`)
) ENGINE=InnoDB AUTO_INCREMENT=68 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

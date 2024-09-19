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

 Date: 18/09/2024 18:05:30
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_historical_contacts
-- ----------------------------
DROP TABLE IF EXISTS `ws_historical_contacts`;
CREATE TABLE `ws_historical_contacts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(50) DEFAULT NULL,
  `chat_type` int DEFAULT NULL COMMENT '1-私聊 2-群聊',
  `chat_id` varchar(100) DEFAULT NULL COMMENT '聊天对象的id（user_id or group_id）',
  `chat_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `group_id` int DEFAULT NULL COMMENT '群聊 id',
  `last_msg_id` int DEFAULT NULL,
  `last_msg` varchar(16000) DEFAULT NULL COMMENT '最后一条聊天消息',
  `last_msg_time` datetime DEFAULT NULL COMMENT '最后一条消息发送时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='历史联系人\n';

SET FOREIGN_KEY_CHECKS = 1;

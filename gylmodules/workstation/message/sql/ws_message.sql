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

 Date: 18/09/2024 18:05:40
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_message
-- ----------------------------
DROP TABLE IF EXISTS `ws_message`;
CREATE TABLE `ws_message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_type` int DEFAULT NULL COMMENT '消息类型（0-通知消息， 1-聊天消息）',
  `context_type` int DEFAULT NULL COMMENT '消息体类型（text/image/video/audio/link）',
  `sender` int DEFAULT NULL COMMENT '发送者 userid',
  `sender_name` varchar(50) DEFAULT NULL COMMENT '发送者名字',
  `group_id` int DEFAULT NULL COMMENT '是否是群聊消息',
  `receiver` varchar(255) DEFAULT NULL COMMENT '通知消息存发送列表，私聊存userid，群聊存groupid',
  `receiver_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '存储私聊对象的名字',
  `context` varchar(16000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '消息体内容',
  `timer` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

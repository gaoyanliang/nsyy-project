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

 Date: 18/09/2024 18:05:49
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ws_message_read
-- ----------------------------
DROP TABLE IF EXISTS `ws_message_read`;
CREATE TABLE `ws_message_read` (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` int DEFAULT NULL COMMENT '0-通知消息 1-私聊消息 2-群聊消息',
  `sender` int DEFAULT NULL COMMENT '发送者userid ，或群成员',
  `receiver` int DEFAULT NULL COMMENT '接收者，或者group_id',
  `last_read` int DEFAULT NULL COMMENT 'last read msgid',
  `timer` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

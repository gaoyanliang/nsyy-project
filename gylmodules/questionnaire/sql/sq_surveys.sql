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

 Date: 10/12/2024 16:26:40
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for sq_surveys
-- ----------------------------
DROP TABLE IF EXISTS `sq_surveys`;
CREATE TABLE `sq_surveys` (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` int DEFAULT NULL COMMENT '问卷类型 1=通用, 2=专病, 3=专科',
  `type_name` varchar(255) DEFAULT NULL COMMENT '类型名称',
  `title` varchar(255) DEFAULT NULL COMMENT '问卷名称',
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `create_date` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of sq_surveys
-- ----------------------------
BEGIN;
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (1, 2, '专病', '胸痛', NULL, '2024-12-03 19:19:41');
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (2, 2, '专病', '痴呆', NULL, '2024-12-03 19:19:45');
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (3, 2, '专病', '脑血管', NULL, '2024-12-09 16:47:27');
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (4, 2, '专病', '头痛', NULL, '2024-12-09 16:47:29');
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (5, 2, '专病', '眩晕', NULL, '2024-12-09 16:47:31');
INSERT INTO `sq_surveys` (`id`, `type`, `type_name`, `title`, `description`, `create_date`) VALUES (7, 1, '通用', '通用', NULL, '2024-12-09 16:47:55');
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

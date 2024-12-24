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

 Date: 11/12/2024 14:56:39
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for app_version
-- ----------------------------
DROP TABLE IF EXISTS `app_version`;
CREATE TABLE `app_version` (
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '设备类型 区分 android 和 ios',
  `detail` varchar(255) DEFAULT NULL COMMENT '区分应用场景 pda 手机 医废 综合预约',
  `minimum_version` int DEFAULT NULL COMMENT '最低支持版本',
  `latest_version` int DEFAULT NULL,
  `upgrade_desc` varchar(255) DEFAULT NULL,
  `download_url` varchar(255) DEFAULT NULL,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of app_version
-- ----------------------------
BEGIN;
INSERT INTO `app_version` (`type`, `detail`, `minimum_version`, `latest_version`, `upgrade_desc`, `download_url`, `update_time`) VALUES ('ios', 'phone', 1, 2, '1. 更新项一, 2. 更新项二, 3.更新项三 ', 'https://apps.apple.com/us/app/%E5%8D%97%E7%9F%B3%E5%8C%BB%E9%99%A2%E7%BB%BC%E5%90%88%E7%AE%A1%E7%90%86%E5%B9%B3%E5%8F%B0/id6470251851', '2024-12-10 15:56:44');
INSERT INTO `app_version` (`type`, `detail`, `minimum_version`, `latest_version`, `upgrade_desc`, `download_url`, `update_time`) VALUES ('android', 'phone', 1, 1, '1. 更新项一, 2. 更新项二, 3.更新项三 ', 'http://120.194.96.67:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy9Oc3l5QVBLLmFwaw==', '2024-12-10 15:56:47');
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

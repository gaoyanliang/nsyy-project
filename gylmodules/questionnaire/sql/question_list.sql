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

 Date: 31/10/2024 15:03:38
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for question_list
-- ----------------------------
DROP TABLE IF EXISTS `question_list`;
CREATE TABLE `question_list` (
  `id` int NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL COMMENT '问题描述',
  `sort_num` int DEFAULT NULL COMMENT '排序字段',
  `type` int DEFAULT NULL COMMENT '问题类别',
  `tpl_type` int DEFAULT NULL COMMENT '模版分类 通用/专病/专科',
  `tpl_type_detail` int DEFAULT '0' COMMENT '模版类型明细',
  `ans_type` int DEFAULT NULL COMMENT '答案类型',
  `ans_list` varchar(255) DEFAULT NULL COMMENT '答案列表',
  `medical_record_field` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '病历字段',
  `ans_prefix` varchar(255) DEFAULT NULL COMMENT '问题前缀',
  `ans_suffix` varchar(255) DEFAULT NULL COMMENT '问题后缀',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of question_list
-- ----------------------------
BEGIN;
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (1, '本次就诊原因', 1, 1, 1, 0, 1, NULL, '主要症状', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (2, '症状持续时间', 2, 1, 1, 0, 1, NULL, '症状持续时间', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (3, '从什么时候开始不舒服', 1, 2, 1, 0, 1, NULL, '发病时间', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (4, '是否采用过药物，用药情况，治疗效果', 2, 2, 1, 0, 1, '', '用药情况', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (5, '是否在外院做过检查，检查结果情况', 3, 2, 1, 0, 1, NULL, '外院检查', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (6, '神志精神情况', 7, 2, 1, 0, 2, '[\"正常\", \"一般\", \"差\"]', '神志精神', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (7, '饮食情况', 8, 2, 1, 0, 2, '[\"正常\", \"良好\", \"一般\", \"较差\"]', '饮食', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (8, '睡眠情况', 9, 2, 1, 0, 2, '[\"正常\", \"一般\", \"差\"]', '睡眠', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (9, '大便情况', 10, 2, 1, 0, 2, '[\"正常\", \"失禁\", \"便结\"]', '大便', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (10, '小便情况', 11, 2, 1, 0, 2, '[\"正常\", \"增多\", \"减少\", \"潴留\", \"失禁\"]', '小便', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (11, '体力情况', 12, 2, 1, 0, 2, '[\"正常\", \"下降\"]', '体力', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (12, '体重情况', 13, 2, 1, 0, 2, '[\"无变化\", \"增加\", \"下降\"]', '体重', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (13, '胸痛症状', 14, 2, 2, 1, 2, '[\"间断\", \"持续\"]', '胸痛症状', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (14, '发病诱因是什么？', 3, 2, 1, 0, 3, '[\"剧烈运动\", \"劳累\", \"情绪激动\", \"餐后\"]', '发病诱因', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (15, '胸痛部位', 15, 2, 2, 1, 3, '[\"左侧\", \"右侧\", \"胸骨后\", \"上腹部\"]', '胸痛部位', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (16, '胸痛性质\r', 16, 2, 2, 1, 3, '[\"闷痛\", \"针刺样\", \"烧灼样\", \"撕裂样\", \"持续性隐痛\"]', '胸痛性质', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (18, '有什么伴随症状', 4, 2, 1, 0, 1, '', '伴随症状', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (19, '每次发作持续时间', 5, 2, 1, 0, 1, NULL, '每次发作持续时间', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (20, '有什么缓解因素', 6, 2, 1, 0, 3, '[\"休息后\", \"含化药物后\", \"进食后\"]', '缓解因素', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (22, '记忆是否受问题', 17, 2, 2, 2, 1, NULL, NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (23, '日常生活是否受影响', 18, 2, 2, 2, 1, NULL, NULL, '', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (24, '视空间能力如何', 19, 2, 2, 2, 1, NULL, NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (25, '精神行为如何', 20, 2, 2, 2, 1, NULL, NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (26, '平素身体', 1, 3, 1, 0, 2, '[\"良好\", \"一般\", \"差\"]', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (27, '有无高血压', 2, 3, 1, 0, 2, '[\"否认\", \"有\"]', '高血压病史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (28, '有无糖尿病', 3, 3, 1, 0, 2, '[\"否认\", \"有\"]', '糖尿病病史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (30, '有无心脏病', 5, 3, 1, 0, 2, '[\"否认\", \"有\"]', '心脏病病史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (31, '有无脑血管病', 6, 3, 1, 0, 2, '[\"否认\", \"有\"]', '脑血管病史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (32, '有无外伤手术史', 7, 3, 1, 0, 2, '[\"否认\", \"有\"]', '外伤手术史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (33, '有无家族史', 8, 3, 1, 0, 2, '[\"否认\", \"有\"]', '家族史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (34, '有无过敏史', 9, 3, 1, 0, 2, '[\"否认\", \"有\"]', '过敏史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (35, '有无传染病史', 10, 3, 1, 0, 2, '[\"否认\", \"有\"]', '传染病史', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (36, '其他病史，病史几年', 11, 3, 1, 0, 1, '', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (39, '体温', 1, 4, 1, 0, 1, NULL, '体温', NULL, 'C°');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (40, '脉搏', 2, 4, 1, 0, 1, NULL, '脉搏', NULL, '次/分');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (41, '呼吸', 3, 4, 1, 0, 1, NULL, '呼吸', NULL, '次/分');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (42, '血压', 4, 4, 1, 0, 1, NULL, '血压', NULL, 'mmHg');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (43, '神志精神情况', 5, 4, 1, 0, 2, '[\"清楚\", \"淡漠\", \"模糊\", \"昏睡\", \"谵妄\", \"昏迷\"]', '神志', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (44, '步态', 6, 4, 1, 0, 2, '[\"正常\", \"异常\", \"慌张\", \"醉汉\", \"拖曳\"]', '步态', NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`) VALUES (45, '体态 ', 7, 4, 1, 0, 2, '[\"自动体位\", \"被动体位\", \"强迫体位\"]', '体态', NULL, NULL);
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

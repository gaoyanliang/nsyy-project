/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.3.12
 Source Server Type    : MySQL
 Source Server Version : 80040 (8.0.40-0ubuntu0.20.04.1)
 Source Host           : 192.168.3.12:3306
 Source Schema         : nsyy_gyl

 Target Server Type    : MySQL
 Target Server Version : 80040 (8.0.40-0ubuntu0.20.04.1)
 File Encoding         : 65001

 Date: 14/11/2024 10:13:24
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
  `describe` varchar(255) DEFAULT NULL COMMENT '问题解释或说明',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of question_list
-- ----------------------------
BEGIN;
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (1, '本次就诊原因', 1, 1, 1, 0, 3, '{\"2-1\": [\"胸闷\", \"胸痛\", \"心慌\", \"呼吸困难\", \"上腹痛\", \"头疼头晕\", \"其他\"], \"2-2\": [\"记忆力下降\", \"视空间能力异常\", \"精神行为异常\", \"日常生活困难\", \"其他\"]}', '主要症状', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (2, '症状持续时间', 2, 1, 1, 0, 2, '{\"2-1\": [\"间断性（1分钟内）\", \"间断性（3分钟内）\", \"间断性（3-5分钟）\", \"间断性（十余分钟）\",\"间断性（十分钟以上）\", \"持续性（一天内）\", \"持续性（三天内）\", \"持续性（一周内）\", \"持续性（一周以上）\"], \"2-2\": [\"急性\", \"慢性\"]}', '症状持续时间', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (3, '从什么时候开始不舒服', 1, 2, 1, 0, 1, NULL, '发病时间', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (4, '是否采用过药物，用药情况，治疗效果', 10, 2, 1, 0, 1, '', '用药情况', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (5, '是否在外院做过检查，检查结果情况', 9, 2, 1, 0, 3, '{\"2-1\": [\"B 超\", \"静态心电图\", \"心脏彩超\", \"双源CT\", \"心脏造影\", \"动态心电图\", \"胸片\", \"CT\", \"核磁\", \"无\"], \"2-2\": [\"B 超\", \"静态心电图\", \"心脏彩超\", \"双源CT\", \"心脏造影\", \"动态心电图\", \"胸片\", \"CT\", \"核磁\", \"无\"]}', '外院检查', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (6, '神志精神情况', 11, 2, 1, 0, 2, '[\"正常\", \"一般\", \"差\"]', '神志精神', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (7, '饮食情况', 12, 2, 1, 0, 2, '[\"正常\", \"良好\", \"一般\", \"较差\"]', '饮食', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (8, '睡眠情况', 13, 2, 1, 0, 2, '[\"正常\", \"一般\", \"差\"]', '睡眠', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (9, '大便情况', 14, 2, 1, 0, 2, '[\"正常\", \"失禁\", \"便结\"]', '大便', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (10, '小便情况', 15, 2, 1, 0, 2, '[\"正常\", \"增多\", \"减少\", \"潴留\", \"失禁\"]', '小便', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (11, '体力情况', 16, 2, 1, 0, 2, '[\"正常\", \"下降\"]', '体力', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (12, '体重情况', 17, 2, 1, 0, 2, '[\"无变化\", \"增加\", \"下降\"]', '体重', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (13, '发病症状', 2, 2, 2, 1, 2, '[\"间断\", \"持续\"]', '胸痛症状', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (14, '发病诱因是什么？', 7, 2, 1, 0, 3, '[\"剧烈运动\", \"劳累\", \"情绪激动\", \"餐后\", \"天气因素\", \"其他\"]', '发病诱因', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (15, '胸痛部位', 4, 2, 2, 1, 3, '[\"左侧\", \"右侧\", \"胸骨后\", \"上腹部\", \"其他\"]', '胸痛部位', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (16, '胸痛性质\r', 5, 2, 2, 1, 3, '[\"闷痛\", \"针刺样\", \"烧灼样\", \"撕裂样\", \"持续性隐痛\", \"其他\"]', '胸痛性质', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (18, '有什么伴随症状', 7, 2, 1, 0, 3, '{\"2-1\": [\"胸闷\", \"憋气\", \"气短\", \"呼吸困难\", \"心慌\", \"出汗\", \"发热\", \"咳嗽\", \"反酸\", \"嗳气\", \"恶心\", \"呕吐\", \"无\", \"其他\"], \"2-2\": [\"精神行为异常\", \"记忆力减退\", \"幻觉\", \"无\", \"其他\"]}', '伴随症状', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (19, '每次发作持续时间', 7, 2, 1, 0, 2, '{\"2-1\": [\"24小时内\", \"三天左右\", \"一周左右\",\"一周以上\"], \"2-2\": [\"急性\", \"慢性\"]}', '每次发作持续时间', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (20, '有什么缓解因素', 8, 2, 1, 0, 3, '[\"休息后\", \"含化药物后\", \"进食后\", \"其他\"]', '缓解因素', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (22, '记忆是否受问题', 3, 2, 2, 2, 2, '[\"否认\", \"有\"]', NULL, NULL, NULL, '能不能记住交代的事情？有没有忘记反复买东西，比如每天都买香蕉，一问，忘记昨天买了了！ 炒菜时会不会忘记加盐或加多了？有没有烧水或熬中药糊了？今天几号？星期几？');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (23, '日常生活是否受影响', 4, 2, 2, 2, 2, '[\"否认\", \"有\"]', NULL, '', NULL, '能不能独立完成炒菜、买菜、管理财务等？');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (24, '视空间能力是否受影响', 5, 2, 2, 2, 2, '[\"否认\", \"有\"]', NULL, NULL, NULL, '能不能独立一个人出远门？怕迷路吗？衣服有没有穿反？等等。');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (25, '精神行为是否受影响', 6, 2, 2, 2, 2, '[\"否认\", \"有\"]', NULL, NULL, NULL, '能不能控制自己情绪？比如以前最亲爱的孙子一闹，就想打人或出去调整情绪？');
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (26, '平素身体', 1, 3, 1, 0, 2, '[\"良好\", \"一般\", \"差\"]', NULL, NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (27, '有无高血压', 2, 3, 1, 0, 2, '[\"否认\", \"有\"]', '高血压病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (28, '有无糖尿病', 3, 3, 1, 0, 2, '[\"否认\", \"有\"]', '糖尿病病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (30, '有无心脏病', 5, 3, 1, 0, 2, '[\"否认\", \"有\"]', '心脏病病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (31, '有无脑血管病', 6, 3, 1, 0, 2, '[\"否认\", \"有\"]', '脑血管病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (32, '有无外伤手术史', 7, 3, 1, 0, 2, '[\"否认\", \"有\"]', '外伤手术史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (33, '有无家族史', 8, 3, 1, 0, 2, '[\"否认\", \"有\"]', '家族史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (34, '有无过敏史', 9, 3, 1, 0, 2, '[\"否认\", \"有\"]', '过敏史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (35, '有无传染病史', 10, 3, 1, 0, 2, '[\"否认\", \"有\"]', '传染病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (36, '是否有其他病史', 11, 3, 1, 0, 3, '[\"脑血管疾病\", \"甲状腺疾病\", \"营养不良\",\"喝酒\", \"重金属中毒\", \"化工原料中毒\", \"吸毒史\",\"病毒感染史\", \"其他\"]', '其他病史', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (39, '体温', 1, 4, 1, 0, 4, NULL, '体温', NULL, 'C°', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (40, '脉搏', 2, 4, 1, 0, 4, NULL, '脉搏', NULL, '次/分', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (41, '呼吸', 3, 4, 1, 0, 4, NULL, '呼吸', NULL, '次/分', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (42, '血压', 4, 4, 1, 0, 5, NULL, '血压', NULL, 'mmHg', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (43, '神志精神情况', 8, 4, 1, 0, 2, '[\"清楚\", \"淡漠\", \"模糊\", \"昏睡\", \"谵妄\", \"昏迷\"]', '神志', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (44, '步态', 9, 4, 1, 0, 2, '[\"正常\", \"异常\", \"慌张\", \"醉汉\", \"拖曳\"]', '步态', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (45, '体态 ', 10, 4, 1, 0, 2, '[\"自动体位\", \"被动体位\", \"强迫体位\"]', '体态', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (46, '身高', 5, 4, 1, 0, 4, NULL, '身高', NULL, 'CM', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (47, '体重', 6, 4, 1, 0, 4, NULL, '体重', NULL, '斤', NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (48, '其他病史年限', 12, 3, 1, 0, 2, '[\"24小时内\", \"三天左右\", \"半个月\",\"一个月\", \"一个月以上\"]', '其他病史年限', NULL, NULL, NULL);
INSERT INTO `question_list` (`id`, `description`, `sort_num`, `type`, `tpl_type`, `tpl_type_detail`, `ans_type`, `ans_list`, `medical_record_field`, `ans_prefix`, `ans_suffix`, `describe`) VALUES (49, '那些情况下有可能加重胸痛', 17, 2, 2, 1, 3, '[\"活动时\", \"咳嗽或深吸气时\", \"某种体位\", \"局部按压时\", \"其他\"]', NULL, NULL, '加重胸痛', NULL);
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

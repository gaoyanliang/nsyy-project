#!/usr/bin/env python3
# 自动备份定时任务 每天 2/13点执行
# 脚本放在 /home/gyl/data_backup/table_auto_backup.py
# 使用crontab 来实现定时执行
# 0 2,13 * * * /home/cc/anaconda3/condabin/conda run -n gg python3 /home/gyl/data_backup/table_auto_backup.py

import os
import shutil
import subprocess
import gzip
import logging
from datetime import datetime, timedelta

# === 配置区域 ===
DB_HOST = "127.0.0.1"
# DB_USER = "root"
# DB_PASSWORD = "gyl.2015"
# DB_HOST = "192.168.3.12"
DB_USER = "gyl"
DB_PASSWORD = "123456"
DB_NAME = "nsyy_gyl"

BACKUP_DIR = "./backup"
DAYS_TO_KEEP = 7
COMPRESS = True
LOG_FILE = "./backup.log"
BACKUP_ROOT_DIR = "./backup"  # 备份根目录

TABLES_TO_BACKUP = ["app_token_info", "app_version",
                    # 危机值表
                    "alert_fail_log", "cv_info", "cv_site", "cv_template", "cv_timeout",
                    # 综合预约表
                    "appt_doctor", "appt_doctor_advice", "appt_project", "appt_record", "appt_room",
                    "appt_schedules", "appt_schedules_doctor", "appt_schedules_doctor",
                    # 眼科医院
                    "ehp_medical_record_detail", "ehp_medical_record_list", "ehp_reports",
                    # 高压氧
                    "hbot_register_record", "hbot_sign_info", "hbot_treatment_record",
                    # 院内讲座
                    "hosp_class", "hosp_class_pers", "hosp_class_rate", "hosp_class_rate_questions",
                    # 院前系统
                    "phs_patient_registration", "phs_record", "phs_record_data", "phs_record_sign",
                    # 文件调查
                    "sq_questions", "sq_surveys", "sq_surveys_answer", "sq_surveys_detail",
                    "sq_surveys_question_association", "sq_surveys_record",
                    # 邮箱系统
                    "ws_mail_custome", "ws_mail_group", "ws_mail_group_members", "ws_mail_group_permissions",
                    # 消息
                    "ws_group", "ws_group_member", "ws_historical_contacts"]

# === 初始化日志 ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

# === 新增配置 ===
BACKUP_TIMES = ["02", "13"]  # 每天备份的小时时间点（24小时制）
logger = logging.getLogger(__name__)


def get_backup_dir():
    """获取当天备份目录（按日期创建子目录）"""
    today = datetime.now().strftime("%Y%m%d")
    backup_dir = os.path.join(BACKUP_ROOT_DIR, today)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def should_run_backup():
    """检查当前时间是否在预设备份时段"""
    current_hour = datetime.now().strftime("%H")
    return current_hour in BACKUP_TIMES


def backup_tables():
    if not should_run_backup():
        logger.info("当前非预设备份时段，跳过执行")
    else:
        try:
            backup_dir = get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            logger.info(f"一共需要备份 {len(TABLES_TO_BACKUP)} 张表")
            index = 1
            for table in TABLES_TO_BACKUP:
                backup_file = os.path.join(backup_dir, f"{DB_NAME}_{table}_{timestamp}.sql")
                cmd = ["mysqldump", f"--host={DB_HOST}", f"--user={DB_USER}", f"--password={DB_PASSWORD}",
                       "--single-transaction", "--skip-lock-tables", DB_NAME, table]

                logger.info(f"开始备份表 [{index}]: {DB_NAME}.{table}")
                index = index + 1
                with open(backup_file, "wb") as f:
                    subprocess.run(cmd, stdout=f, check=True)

                if COMPRESS:
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                            f_out.writelines(f_in)
                    os.remove(backup_file)
                    logger.info(f"表备份已压缩: {backup_file}.gz")

            logger.info(f"开始清理旧备份")
            cleanup_old_backups()

        except Exception as e:
            logger.error(f"备份失败: {str(e)}", exc_info=True)
    logger.info(f"备份完成")


def cleanup_old_backups():
    cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    for dirname in os.listdir(BACKUP_ROOT_DIR):
        dirpath = os.path.join(BACKUP_ROOT_DIR, dirname)
        if os.path.isdir(dirpath):
            try:
                dir_date = datetime.strptime(dirname, "%Y%m%d")
                if dir_date < cutoff:
                    shutil.rmtree(dirpath)
                    logger.info(f"已清理旧备份目录: {dirname}")
            except ValueError:
                continue  # 忽略不符合日期格式的目录


if __name__ == "__main__":
    backup_tables()


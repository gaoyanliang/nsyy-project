#!/usr/bin/env python3
import imaplib
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import argparse
from typing import Tuple, List, Dict

import pymysql

run_in_local = False

# 数据库配置
db_config = {
    'host': '192.168.3.92' if run_in_local else '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'NSYYnsyy@123',
    'database': 'vmail',
    'charset': 'utf8mb4'
}

# 配置部分 - 根据实际情况修改
mail_config = {
    'MAIL_SSH_HOST': '192.168.3.92' if run_in_local else '127.0.0.1',  # 192.168.3.92
    'MAIL_IMAP_PORT': 993,
    'MAIL_DOMAIN': '@nsyy.com',
    'MAIL_ACCOUNT_PASSWORD': 'NSYYnsyy@123',  # 实际应用中应该从安全存储获取
    'BATCH_SIZE': 200,  # 每批处理的账户数量
    'MAX_WORKERS': 10,  # 并发线程数
    'RETENTION_DAYS': 30,  # 保留最近30天的邮件
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mail_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_user_accounts_from_mysql() -> List[str]:
    """从MySQL的mailbox表中获取用户账户列表"""
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT name FROM vmail.mailbox WHERE active = 1"  # 假设有active字段标识活跃账户
            cursor.execute(sql)
            accounts = [row[0] for row in cursor.fetchall()]
            logger.info(f"Fetched {len(accounts)} active accounts from database")
        return accounts
    except pymysql.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()


def connect_and_login(user_account: str) -> Tuple[str, imaplib.IMAP4_SSL]:
    """连接IMAP服务器并登录邮箱账户"""
    try:
        mail = imaplib.IMAP4_SSL(mail_config['MAIL_SSH_HOST'], mail_config['MAIL_IMAP_PORT'])
        mail_account = user_account + mail_config['MAIL_DOMAIN']
        status, _ = mail.login(mail_account, mail_config['MAIL_ACCOUNT_PASSWORD'])

        if status != "OK":
            logger.error(f"{mail_account} Login failed. Please check your credentials.")
            mail.logout()
            return "Fail", None

        return "OK", mail
    except Exception as e:
        logger.error(f"Error connecting to {user_account}: {str(e)}")
        return "Fail", None


def process_mailbox(mail: imaplib.IMAP4_SSL, mailbox: str) -> Tuple[str, str, int]:
    """处理单个邮箱文件夹"""
    try:
        # 选择邮箱
        status, _ = mail.select(mailbox)
        if status != "OK":
            return "Fail", f"Failed to select mailbox {mailbox}", 0

        # 计算删除日期阈值
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=mail_config['RETENTION_DAYS'])).strftime(
            "%d-%b-%Y")

        # 搜索旧邮件
        status, data = mail.search(None, f'(BEFORE "{cutoff_date}")')
        if status != "OK":
            return "Fail", f"Search failed in mailbox {mailbox}", 0

        # 获取邮件ID列表
        mail_ids = data[0].split()
        if not mail_ids:
            return "OK", f"No old emails in {mailbox}", 0

        # 标记删除旧邮件
        mail.store(b','.join(mail_ids), '+FLAGS', '\\Deleted')

        # 永久删除标记的邮件
        mail.expunge()

        return "OK", f"Deleted {len(mail_ids)} emails from {mailbox}", len(mail_ids)
    except Exception as e:
        return "Fail", f"Error processing mailbox {mailbox}: {str(e)}", 0


def process_user_account(user_account: str) -> Tuple[str, str, int]:
    """处理单个用户账户"""
    try:
        # 连接并登录
        status, mail = connect_and_login(user_account)
        if status != "OK":
            return "Fail", f"Login failed for {user_account}", 0

        # 获取邮箱列表
        status, data = mail.list()
        if status != "OK":
            mail.logout()
            return "Fail", f"Failed to get mail list for {user_account}", 0

        # 处理每个邮箱
        mailboxes = [item.split()[-1].decode('utf-8') for item in data]
        results = []
        total_deleted = 0

        has_email_been_deleted = False
        for mailbox in mailboxes:
            status, msg, deleted_count = process_mailbox(mail, mailbox)
            if status != "OK":
                mail.logout()
                return "Fail", msg, 0
            total_deleted += deleted_count
            results.append(msg)

        mail.logout()
        return "OK", f"Successfully processed {user_account}: {', '.join(results)}", total_deleted
    except Exception as e:
        return "Fail", f"Error processing account {user_account}: {str(e)}", 0


def process_accounts_batch(accounts_batch: List[str]) -> Dict[str, Tuple[str, str]]:
    """并发处理一批账户"""
    results = {}

    with ThreadPoolExecutor(max_workers=mail_config['MAX_WORKERS']) as executor:
        future_to_account = {executor.submit(process_user_account, account): account for account in accounts_batch}

        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                status, message, deleted_count = future.result()
                results[account] = (status, message, deleted_count)

                if status == "OK" and deleted_count > 0:
                    logger.info(f"{account}: {message}: Deleted {deleted_count} emails")
                elif status == "Fail":
                    logger.error(f"{account}: Failed - {message}")
            except Exception as e:
                error_msg = f"Unexpected error processing {account}: {str(e)}"
                results[account] = ("Fail", error_msg)
                logger.error(error_msg)

    return results


def main():
    """主处理函数"""
    start_time = time.time()
    user_accounts = get_user_accounts_from_mysql()
    if not user_accounts:
        logger.error("No active accounts found in database")
        return

    user_accounts.remove('postmaster')
    total_accounts = len(user_accounts)
    processed_accounts = 0
    failed_accounts = 0
    total_deleted = 0

    # 分批处理账户
    for i in range(0, total_accounts, mail_config['BATCH_SIZE']):
        batch = user_accounts[i:i + mail_config['BATCH_SIZE']]
        logger.info(f"Processing batch {i // mail_config['BATCH_SIZE'] + 1} with {len(batch)} accounts")

        batch_results = process_accounts_batch(batch)

        # 统计结果
        for account, (status, message, deleted_count) in batch_results.items():
            processed_accounts += 1
            total_deleted += deleted_count
            if status == "Fail":
                failed_accounts += 1

        # 如果有失败的账户，可以选择停止处理 (超过 10 个默认退出)
        if failed_accounts > 10:
            logger.warning(f"Stopping processing due to {failed_accounts} failed accounts in this batch")
            break

    # 输出摘要
    elapsed_time = time.time() - start_time
    logger.info("==========================================================")
    logger.info(f"=== Processing completed in {elapsed_time:.2f} seconds ===")
    logger.info("==========================================================")
    logger.info(f"Total accounts: {total_accounts}")
    logger.info(f"Total emails deleted: {total_deleted}")
    logger.info(f"Processed accounts: {processed_accounts}")
    logger.info(f"Successful accounts: {processed_accounts - failed_accounts}")
    logger.info(f"Failed accounts: {failed_accounts}")


if __name__ == "__main__":
    # user_accounts = ['T123445', 'U00019', 'U00888', 'U00018', 'U01420', 'U01406', 'U00080', 'U00011', 'U02430', 'U04824', 'admin1',
    #                  'admin', 'U10357', 'U03378', 'U03472', 'yanliang']

    main()



import hashlib
import json
import mimetypes

import string
import random
import base64
import os
import time
from datetime import datetime
from email.mime.image import MIMEImage
from pathlib import Path

import redis
import requests

from gylmodules import global_config
from gylmodules.composite_appointment import appt_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.utils.ssh_utils import SshUtil
from gylmodules.workstation.mail import mail_config

import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import re

pool = redis.ConnectionPool(host=appt_config.APPT_REDIS_HOST, port=appt_config.APPT_REDIS_PORT,
                            db=appt_config.APPT_REDIS_DB, decode_responses=True)


def send_email(json_data):
    """
    Send an email with the provided JSON data and save a copy to the Sent folder.
    Raises:
        Exception: If email sending fails
    """
    # Extract and validate required fields
    sender = json_data.get("sender")
    if not sender:
        raise ValueError("发送人不能为空")

    recipients = json_data.get("recipients", [])
    recipients_group = json_data.get("recipients_group", [])
    if not recipients and not recipients_group:
        raise ValueError("至少需要添加一位接收人或群组")

    # Process all recipient types
    ccs = json_data.get("ccs", [])
    bccs = json_data.get("bccs", [])
    subject = json_data.get("subject", "")
    body = json_data.get("body", "")
    attachments = json_data.get("attachments")
    names = json_data.get("names")

    # Create email message
    msg = MIMEMultipart()
    sender_email = f"{sender}{mail_config.MAIL_DOMAIN}".lower()
    msg["From"] = sender_email
    msg["Subject"] = subject
    msg["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Process all recipients and build To/Cc/Bcc headers   todo 校验群组是否存在
    def process_recipients(recipient_list):
        return [f"{r}{mail_config.MAIL_DOMAIN}".lower() for r in recipient_list]

    to_recipients = process_recipients(recipients + recipients_group)
    cc_recipients = process_recipients(ccs)
    bcc_recipients = process_recipients(bccs)

    msg["To"] = ", ".join(to_recipients)
    if cc_recipients:
        msg["Cc"] = ", ".join(cc_recipients)
    if bcc_recipients:
        msg["Bcc"] = ", ".join(bcc_recipients)

    # Add custom headers if present 附件&发送者信息
    if attachments is not None:
        msg['X-Attachments'] = json.dumps(attachments, default=str)
    if names is not None:
        msg['X-Names'] = json.dumps(names, default=str)

    # # Set the "Disposition-Notification-To" header  已读回执
    # msg["Disposition-Notification-To"] = sender_email

    # Add email body
    msg.attach(MIMEText(body, "plain"))

    # Process attachments
    temp_files = []
    if attachments:
        for attachment in attachments:
            filename = attachment.get('file_name')
            filepath = attachment.get('file_path')

            if not filename or not filepath:
                continue

            # Download attachment Add to email
            download_file(filepath, filename)
            with open(filename, "rb") as file:
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type and mime_type.startswith('image/'):
                    part = MIMEImage(file.read())
                    part.add_header("Content-ID", f"<{filename}>")
                else:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                    encoders.encode_base64(part)

                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

    try:
        # Send email via SMTP
        with smtplib.SMTP(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, mail_config.MAIL_ACCOUNT_PASSWORD)

            all_recipients = to_recipients + cc_recipients + bcc_recipients
            server.sendmail(sender_email, all_recipients, msg.as_string())

        # Save to Sent folder
        save_to_sent_folder(sender, msg.as_string())

    except smtplib.SMTPException as e:
        raise Exception(str(e))
    finally:
        # Clean up temporary files
        if attachments is not None:
            for attachment in attachments:
                try:
                    filename = attachment.get('file_name')
                    os.remove(filename)
                except OSError:
                    pass


def save_to_sent_folder(sender, email_text):
    """
    Save the sent email to the Sent folder using IMAP.
    """
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(mail_config.MAIL_SSH_HOST, mail_config.MAIL_IMAP_PORT)
        mail_account = f"{sender}{mail_config.MAIL_DOMAIN}"
        mail.login(mail_account, mail_config.MAIL_ACCOUNT_PASSWORD)
        mail.append("Sent", None, None, email_text.encode('utf-8'))
    except Exception as e:
        print(datetime.now(), f"Warning: Failed to save to Sent folder: {str(e)}")
    finally:
        if mail:
            mail.logout()


def download_file(url, filename):
    """
    下载文件并保存到本地
    :param url:
    :param filename:
    :return:
    """
    response = requests.get(url)
    with open(filename, "wb") as file:
        file.write(response.content)


def read_mail_list(user_account: str, page_size: int, page: int, mailbox: str, keyword: str = None):
    """ 高效分页读取邮件列表（仅获取邮件头、是否已读标识） """
    start_time = time.time()
    ret, mail = __login_mail_server(user_account, mailbox)
    if not ret:
        return []

    search_criteria = 'ALL'
    if keyword:
        search_criteria = '(OR (FROM \"' + keyword + '\") (SUBJECT \"' + keyword + '\"))'
        search_criteria = search_criteria.encode('utf-8')

    # **1️⃣ 获取所有邮件 UID**
    status, messages = mail.search(None, search_criteria)
    if status != "OK" or not messages[0]:
        return []

    # 倒序获取邮件 UID，最新邮件在前
    email_uids = messages[0].split()[::-1]
    total_emails = len(email_uids)
    if total_emails == 0:
        return []

    # **2️⃣ 计算分页范围**
    start = (page - 1) * page_size
    end = start + page_size
    selected_uids = email_uids[start:end]

    if not selected_uids:
        return []

    # **3️⃣ 批量获取邮件头 & FLAGS**
    uid_range = ",".join(uid.decode() for uid in selected_uids)
    status, msg_data = mail.fetch(uid_range,
                                  "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE X-Attachments X-Names)])")

    if status != "OK":
        return []

    email_list = []
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            raw_email = response_part[1]
            msg = email.message_from_bytes(raw_email)

            # **解析邮件 UID**
            uid = response_part[0].decode("utf-8").split()[0]  # 从 fetch 响应解析 UID

            # **解析邮件头**
            subject, encoding = decode_header(msg.get("Subject", ""))[0]
            subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject

            # **解析 FLAGS**
            flags_data = response_part[0].decode("utf-8") if isinstance(response_part[0], bytes) else ""
            is_unread = "\\Seen" not in flags_data

            email_list.append({
                'id': uid,  # 这里用 UID 而不是 Message-ID
                'Unread': is_unread,
                'Subject': subject or "(No Subject)",
                "From": msg.get("From", ""),
                'Date': convert_date_format(msg.get("Date", "")),
                'To': msg.get('To', ""),
                'CC': msg.get('CC', ""),
                "Bcc": msg.get("Bcc", ""),
                "ReplyToList": msg.get("Reply-To", ""),
                'attachments': json.loads(msg.get('X-Attachments', "[]")) if msg.get('X-Attachments') else [],
                'names': json.loads(msg.get('X-Names', "[]")) if msg.get('X-Names') else [],
            })

    __close_mail(mail)

    return email_list


def read_mail_detail(user_account: str, mail_id: str, mailbox: str):
    ret, mail = __login_mail_server(user_account, mailbox)
    ret, err = __read_mail_by_mail_id(mail, bytes(str(mail_id), 'utf-8'), True)
    __close_mail(mail)
    return ret


def delete_mail(user_account: str, mail_ids, mailbox: str):
    ret, mail = __login_mail_server(user_account, mailbox)

    # 标记为已删除
    for id in mail_ids:
        mail.store(bytes(str(id), 'utf-8'), '+FLAGS', '(\Deleted)')
    # 彻底删除
    mail.expunge()

    __close_mail(mail)


def fetch_attachment(user_account: str, mail_id: int, mailbox: str, file_name: str):
    ret, mail = __login_mail_server(user_account, mailbox)

    # Fetch the email based on the ID.  peek 防止修改邮件已读状态
    result, message_data = mail.fetch(bytes(str(mail_id), 'utf-8'), '(BODY.PEEK[])')
    if result == "OK":
        # Parse the email message
        msg = email.message_from_bytes(message_data[0][1])
        # Extract email details
        # subject, encoding = decode_header(msg.get("Subject"))[0]
        # subject = subject.decode(encoding) if encoding else subject
        # print("Subject              : {}".format(subject))

        for part in msg.walk():
            if part.get_content_maintype() == "multipart" or part.get("Content-Disposition") is None:
                continue
            filename = part.get_filename()
            if filename == file_name:
                return part.get_payload(decode=True)

    # Close the mailbox and log out
    __close_mail(mail)
    return None


def __read_mail_by_mail_id(mail, email_id, query_body: bool):
    # Fetch the email with peek to preserve read status
    result, message_data = mail.fetch(email_id, '(FLAGS BODY.PEEK[])')
    if result != "OK":
        return None, f"Failed to read email {email_id}"

    try:
        # Parse raw message
        raw_message = message_data[0][1]
        msg = email.message_from_bytes(raw_message)

        # Extract basic headers
        subject, encoding = decode_header(msg.get("Subject", ""))[0]
        subject = subject.decode(encoding) if encoding else subject

        # Process flags
        flags = message_data[0][0].decode("utf-8").split("FLAGS (")[1].split(")")[0]
        is_unread = "\\Seen" not in flags

        # Mark as read if needed
        if is_unread and query_body:
            mail.store(email_id, '+FLAGS', '\\Seen')

        # Process attachments and embedded content
        attachments = []
        cid_map = {}
        names = []

        # 正常附件 随邮件发送的
        if msg.get('X-Attachments'):
            try:
                attachments = json.loads(msg.get('X-Attachments'))
                for att in attachments:
                    original_str = f"{att['file_name']}#{att['file_path']}#{msg.get('Date')}"
                    att['url'] = compress_string(original_str)
            except json.JSONDecodeError:
                pass

        # 处理内联附件和嵌入式内容（在邮件内容中间的）
        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", "")
            content_id = part.get("Content-ID", "").strip("<>")

            # is_attachment = "attachment" in content_disposition.lower() # 普通附件
            is_inline = "inline" in content_disposition.lower()
            has_content_id = bool(content_id)

            if is_inline or has_content_id:
                # 获取附件内容
                file_data = part.get_payload(decode=True)
                content_hash = hashlib.sha256(file_data).hexdigest()[:16]  # 生成内容哈希
                content_type = part.get_content_type()

                # 获取原始文件名
                raw_filename = decode_filename(part.get_filename()) or f"inline_{content_hash}"
                safe_filename = sanitize_filename(raw_filename)

                # 生成最终文件名（哈希+原始名）
                final_name = f"{content_hash}_{safe_filename}"
                save_dir = mail_config.inline_attachments_dir_dev if global_config.run_in_local \
                    else mail_config.inline_attachments_dir_prod
                save_path = os.path.join(save_dir, final_name)

                try:
                    # 获取父目录
                    parent_dir = Path(save_path).parent
                    # 如果父目录不存在，则创建
                    if not parent_dir.exists():
                        os.makedirs(parent_dir, exist_ok=True)  # 自动创建嵌套目录
                    # 写入文件（原子操作）
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                except Exception as e:
                    print(f"文件保存失败: {str(e)}")

                # 添加到附件列表
                download_path = f"http://192.168.124.9:8080/gyl/workstation/mail/download/{final_name}" \
                    if global_config.run_in_local \
                    else f"http://192.168.3.12:6080/gyl/workstation/mail/download/{final_name}"
                if is_inline:
                    attachments.append({"file_name": safe_filename, "file_path": download_path, "url": download_path})

                if content_id:
                    cid_map[content_id] = download_path

        # Process names (custom header)
        if msg.get('X-Names'):
            try:
                names = json.loads(msg.get('X-Names'))
            except json.JSONDecodeError:
                names = []

        # Process email body
        body = None
        if query_body:
            html_body = None
            plain_body = None

            # Multipart processing
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue

                    content_type = part.get_content_type()
                    disposition = part.get("Content-Disposition", "")

                    # Skip attachments
                    if "attachment" in disposition.lower():
                        continue

                    # Process text content
                    if content_type in ["text/plain", "text/html"]:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'

                        try:
                            text = payload.decode(charset, 'ignore')
                        except (LookupError, UnicodeDecodeError):
                            text = payload.decode('utf-8', 'ignore')

                        if content_type == "text/html":
                            html_body = text
                        elif content_type == "text/plain":
                            plain_body = text
            else:
                # Handle non-multipart
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    body = payload.decode(charset, 'ignore')
                except (LookupError, UnicodeDecodeError):
                    body = payload.decode('utf-8', 'ignore')

            # Final body selection
            body = html_body or plain_body or body

            # Replace CID references
            # 替换CID为Data URI
            if body and cid_map:
                for cid, data in cid_map.items():
                    body = body.replace(f"cid:{cid}", data)

        # Build result
        return {
            "id": email_id.decode("utf-8"),
            "Unread": is_unread,
            "Subject": subject,
            "From": msg.get("From"),
            "To": msg.get("To"),
            "CC": msg.get("CC"),
            "Bcc": msg.get("Bcc"),
            "ReplyToList": msg.get("Reply-To"),
            "Date": convert_date_format(msg.get("Date")),
            "attachments": attachments,
            "names": names,
            "body": body,
        }, None

    except Exception as e:
        return None, f"Error processing email: {str(e)}"


def sanitize_filename(filename):
    """清理危险字符并截断超长文件名"""
    # 替换危险字符
    clean = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # 截断至 255 字符（文件系统限制）
    return clean[:255]


def decode_filename(encoded_name):
    """
    解码邮件附件文件名
    :param encoded_name: part.get_filename() 获取的原始值
    :return: 解码后的文件名
    """
    if not encoded_name:
        return None

    # 解码可能包含多个部分的头
    decoded_parts = decode_header(encoded_name)
    filename = []

    for content, charset in decoded_parts:
        try:
            # 处理字节类型内容
            if isinstance(content, bytes):
                # 使用指定的字符集解码，如果未知则尝试utf-8
                charset = charset or 'utf-8'
                filename_part = content.decode(charset, 'replace')  # 用替换字符处理错误
            else:
                filename_part = str(content)
            filename.append(filename_part)
        except LookupError:
            # 处理不存在的字符集
            filename_part = content.decode('utf-8', 'replace')
            filename.append(filename_part)
        except UnicodeDecodeError:
            # 双重保险解码失败处理
            filename_part = content.decode('latin-1', 'replace')
            filename.append(filename_part)

    # 拼接所有解码部分并清理特殊字符
    final_name = ''.join(filename)
    return final_name.replace('\n', '').replace('\r', '')


def compress_string(original_string):
    encoded_bytes = base64.b64encode(original_string.encode())
    encoded_string = encoded_bytes.decode()
    encoded_string_modified = encoded_string.replace('/', '&')
    return encoded_string_modified


"""登陆邮件服务器"""


def __login_mail_server(user_account: str, mailbox: str):
    # Connect to the IMAP server & Login to the email account
    mail = imaplib.IMAP4_SSL(mail_config.MAIL_SSH_HOST, mail_config.MAIL_IMAP_PORT)
    mail_account = user_account + mail_config.MAIL_DOMAIN
    status, _ = mail.login(mail_account, mail_config.MAIL_ACCOUNT_PASSWORD)
    if "OK" not in status:
        print(user_account + " Login failed. Please check your credentials.")
        mail.logout()
        return "Fail", f" {mail_account} Login failed. Please check your credentials."

    # list mailboxes
    status, data = mail.list()
    if status != "OK":
        mail.logout()
        return "Fail", "Failed to get mail list."

    # Select the mailbox you want to read, 使用 select() 方法选择要读取的邮件文件夹
    status, _ = mail.select(mailbox)
    if status != "OK":
        mail.logout()
        return "Fail", "Failed to select the mailbox {}".format(mailbox)

    return "OK", mail


def __close_mail(mail):
    # Close the mailbox and log out
    if mail:
        mail.close()
        mail.logout()


# ===========================================================
# =============  mail account manager   =====================
# ===========================================================


def create_mail_account(user_list):
    # 通过脚本创建邮箱账户
    ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
    is_first = True
    for mail_name in user_list:
        mail_name = mail_name + mail_config.MAIL_DOMAIN
        if is_first:
            ssh.execute_shell_command(
                f"bash /home/cc/iRedMail-1.7.2/tools/create_mail_user_SQL.sh "
                f"'{mail_name}' '{mail_config.MAIL_ACCOUNT_PASSWORD}' > "
                f"/tmp/create_multiple_mail_user.sql", sudo=True)
            is_first = False
            continue

        ssh.execute_shell_command(
            f"bash /home/cc/iRedMail-1.7.2/tools/create_mail_user_SQL.sh "
            f"'{mail_name}' '{mail_config.MAIL_ACCOUNT_PASSWORD}' >> "
            f"/tmp/create_multiple_mail_user.sql", sudo=True)

    ssh.execute_shell_command(f"mysql -u{mail_config.MAIL_DB_USERNAME} -p{mail_config.MAIL_DB_PASSWORD} "
                              f"vmail -e 'source /tmp/create_multiple_mail_user.sql'", sudo=True)
    ssh.execute_shell_command("rm /tmp/create_multiple_mail_user.sql", sudo=True)
    del ssh


def delete_mail_account(user_account):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)

    # 删除用户创建的群组
    query_sql = "select id, name from nsyy_gyl.ws_mail_group where user_account = '{}' ".format(user_account)
    mail_group_list = db.query_all(query_sql)
    for mail_group in mail_group_list:
        ssh.execute_shell_command(
            f"cd /opt/mlmmjadmin/tools; python3 maillist_admin.py delete"
            f" {mail_group.get('name') + mail_config.MAIL_DOMAIN}", sudo=True)

        args = (mail_group.get('id'))
        delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group " \
                     "WHERE id = %s "
        db.execute(delete_sql, args, need_commit=True)
        delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
                     "WHERE mail_group_id = %s "
        db.execute(delete_sql, args, need_commit=True)

    # 将用户从加入的群组中移除
    query_sql = "select id, account from nsyy_gyl.ws_mail_group where id in " \
                "(select mail_group_id from nsyy_gyl.ws_mail_group_members where user_account = '{}' ) " \
        .format(user_account)
    mail_group_list = db.query_all(query_sql)
    for mail_group in mail_group_list:
        ssh.execute_shell_command(
            f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c 'cd /opt/mlmmjadmin/tools; "
            f"python3 maillist_admin.py remove_subscribers"
            f" {mail_group.get('account') + mail_config.MAIL_DOMAIN} {user_account + mail_config.MAIL_DOMAIN}'")

    delete_sql = f"DELETE FROM nsyy_gyl.ws_mail_group_members WHERE user_account = '{user_account}' "
    db.execute(delete_sql, need_commit=True)

    del ssh
    del db


def reset_user_password(user_account, old_password, new_password, is_default):
    db = DbUtil(mail_config.MAIL_DB_HOST, mail_config.MAIL_DB_USERNAME, mail_config.MAIL_DB_PASSWORD,
                mail_config.MAIL_DB_DATABASE, mail_config.MAIL_DB_PORT)
    user_mail = user_account + mail_config.MAIL_DOMAIN
    user_mail = user_mail.lower()

    # 查询用户邮箱数据
    query_sql = f"select * from vmail.mailbox where username = '{user_mail}'"
    mailbox = db.query_one(query_sql)
    if not mailbox:
        raise Exception(f"用户 {user_account} 不存在")

    if int(is_default) == 0:
        ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
        # 校验旧密码
        # doveadm pw -t '{hashed_password}' -p '{plaintext_password}'
        ssh_ret = ssh.execute_shell_command(
            f"doveadm pw -t '{mailbox.get('password')}' -p '{old_password}'", sudo=True)
        if not (ssh_ret and ssh_ret.__contains__("verified")):
            raise Exception(f"旧密码错误")

        # 生成新密码，并替换
        # doveadm pw -s 'ssha512' -p '{plain_password}'
        new_password_hash = ssh.execute_shell_command(
            f"doveadm pw -s 'ssha512' -p '{new_password}'", sudo=True)
        del ssh
        new_password_hash = new_password_hash.replace("\n", "")
        if not new_password_hash:
            raise Exception(f"新密码不符合规范, 新密码必须包含：至少一个字母, 至少一个大写字母, 至少一个数字, 至少一个特殊字符")
    else:
        new_password_hash = mail_config.mail_default_passwd

    update_sql = f"UPDATE vmail.mailbox SET password='{new_password_hash}' WHERE username='{user_mail}'"
    db.execute(update_sql, need_commit=True)
    del db


# ===========================================================
# =============   mail group manager    =====================
# ===========================================================

"""
创建邮箱分组
"""


def create_mail_group(json_data):
    user_account = json_data.get("user_account")
    user_name = json_data.get("user_name")
    mail_group_name = json_data.get("mail_group_name")
    mail_group_description = json_data.get("mail_group_description")
    user_list = json_data.get("user_list")
    is_public = json_data.get("is_public")

    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=120 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(f"mail:create:{user_account}", 1, ex=60, nx=True):
        raise Exception('创建失败：请勿频繁创建群组，请于1分钟后再次尝试')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    # 随机生成群组账号
    mail_group_account = generate_random_string(5)

    query_sql = f"select id from nsyy_gyl.ws_mail_group where account = '{mail_group_account}' "
    mail_group = db.query_one(query_sql)
    if mail_group:
        # 随机生成的群账号重复，重新生成
        raise Exception(f"系统繁忙，请稍后再试")

    # 调用邮箱服务器群组管理脚本，创建新群组
    group_name = mail_group_account + mail_config.MAIL_DOMAIN
    group_name = group_name.lower()
    ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
    # 检查群组列表是否存在
    output = ssh.execute_shell_command(f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                       f"'cd /opt/mlmmjadmin/tools; python3 maillist_admin.py info {group_name}' ")
    if 'Error: NO_SUCH_ACCOUNT' not in output:
        raise Exception(f"系统繁忙，请稍后再试")
    # 创建群组
    only_subscriber_can_post = 'no'
    if int(is_public) == 0:
        only_subscriber_can_post = 'yes'
    output = ssh.execute_shell_command(f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                       f"'cd /opt/mlmmjadmin/tools; "
                                       f"python3 maillist_admin.py create {group_name}"
                                       f" only_subscriber_can_post={only_subscriber_can_post} "
                                       f"disable_archive=no disable_send_copy_to_sender=yes '")
    if 'Created.' not in output:
        raise Exception("邮箱群组群组" + mail_group_name + " 创建失败")

    timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args = (mail_group_name, mail_group_account, mail_group_description, user_account, user_name, timer, is_public)
    insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group (name, account, description, " \
                 "user_account, user_name, timer, is_public) " \
                 "VALUES (%s,%s,%s,%s,%s,%s,%s)"
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("新群组入库失败!")

    # 2. 组装用户邮箱账号 [用户账号]@邮箱后缀， 将用户邮箱加入到新群组中
    batch_insert_list = []
    failed_user_list = []
    user_dict = {}
    # 将创建者本人也加入
    user_list.append({"user_account": user_account, "user_name": user_name})
    for user in user_list:
        account = user.get('user_account')
        mail_account = account + mail_config.MAIL_DOMAIN
        mail_account = mail_account.lower()
        # 账号存在将账号加入到
        output = ssh.execute_shell_command(f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c 'cd /opt/mlmmjadmin/tools; "
                                           f"python3 maillist_admin.py add_subscribers {group_name} {mail_account} ' ")
        # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
        if 'Added.' not in output:
            failed_user_list.append(user)
        else:
            batch_insert_list.append(account)
            user_dict[account] = user

    query_sql = f"select user_account from nsyy_gyl.ws_mail_group_members where mail_group_id = {int(last_rowid)} "
    mem = db.query_all(query_sql)
    if mem:
        mem = [m.get('user_account') for m in mem]
        batch_insert_list = list(set(batch_insert_list) - set(mem))

    # 批量插入群组成员
    if batch_insert_list:
        args = []
        for account in batch_insert_list:
            user = user_dict.get(account)
            args.append((last_rowid, user.get('user_account'), user.get('user_name'), timer))
        insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group_members (mail_group_id, " \
                     "user_account, user_name, timer) VALUES (%s,%s,%s,%s)"
        db.execute_many(insert_sql, args, need_commit=True)

    del db
    del ssh
    return failed_user_list


"""
编辑群组
operate_type = 0 更新群组描述
operate_type = 1 向群组中新增用户
operate_type = 2 从群组中移除用户
operate_type = 3 修改群组公开性
operate_type = 4 删除群组 (对本人隐藏，但群组还在)
"""


def operate_mail_group(json_data):
    user_account = json_data.get("user_account")
    mail_group_id = json_data.get("mail_group_id")
    mail_group_name = json_data.get("mail_group_name")
    mail_group_account = json_data.get("mail_group_account", '')
    operate_type = json_data.get("operate_type")
    new_mail_group_desc = json_data.get("new_mail_group_desc")
    user_list = json_data.get("user_list")
    is_public = json_data.get("is_public")

    mail_group = mail_group_account + mail_config.MAIL_DOMAIN
    mail_group = mail_group.lower()

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if operate_type == mail_config.MAIL_OPERATE_UPDATE:
        # 更新群组描述
        update_sql = 'UPDATE nsyy_gyl.ws_mail_group SET description = %s, timer = %s WHERE id = %s'
        args = (new_mail_group_desc, timer, mail_group_id)
        db.execute(update_sql, args, need_commit=True)
        del db
        return
    elif operate_type == mail_config.MAIL_OPERATE_ADD:
        # 添加群组成员
        ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
        joined_user_list = []
        failed_user_list = []
        user_dict = {}
        for user in user_list:
            account = user.get('user_account')
            mail_account = account + mail_config.MAIL_DOMAIN
            mail_account = mail_account.lower()
            # 账号存在将账号加入到邮箱群组
            output = ssh.execute_shell_command(f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                               f"'cd /opt/mlmmjadmin/tools; "
                                               f"python3 maillist_admin.py add_subscribers"
                                               f" {mail_group} {mail_account}' ")
            # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
            if 'Added.' not in output:
                failed_user_list.append(user)
            else:
                joined_user_list.append(account)
                user_dict[account] = user
        del ssh

        query_sql = f"select user_account from nsyy_gyl.ws_mail_group_members where mail_group_id = {int(mail_group_id)} "
        mem = db.query_all(query_sql)
        if mem:
            mem = [m.get('user_account') for m in mem]
            joined_user_list = list(set(joined_user_list) - set(mem))

        # 批量插入群组成员
        if joined_user_list:
            args = []
            for account in joined_user_list:
                user = user_dict.get(account)
                args.append((mail_group_id, user.get('user_account'), user.get('user_name'), timer))
            insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group_members (mail_group_id, " \
                         "user_account, user_name, timer) VALUES (%s,%s,%s,%s)"
            db.execute_many(insert_sql, args, need_commit=True)

        del db
        return failed_user_list
    elif operate_type == mail_config.MAIL_OPERATE_REMOVE:
        # 移除群组成员
        ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
        removed_user_list = []
        failed_user_list = []
        for user in user_list:
            account = user.get('user_account')
            mail_account = account + mail_config.MAIL_DOMAIN
            mail_account = mail_account.lower()
            # 账号存在将账号加入到邮箱群组
            output = ssh.execute_shell_command(f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                               f"'cd /opt/mlmmjadmin/tools; "
                                               f"python3 maillist_admin.py remove_subscribers"
                                               f" {mail_group} {mail_account}' ")
            # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
            if 'Removed.' not in output:
                failed_user_list.append(user)
            else:
                removed_user_list.append(account)
        del ssh

        if removed_user_list:
            delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
                         f"WHERE mail_group_id = {mail_group_id} and user_account in " \
                         f"({', '.join([repr(item) for item in removed_user_list])})  "
            db.execute(delete_sql, need_commit=True)

        del db
        return failed_user_list
    elif operate_type == mail_config.MAIL_OPERATE_PUBLIC:
        query_sql = f"select * from nsyy_gyl.ws_mail_group where id = {int(mail_group_id)} "
        mail_group_record = db.query_one(query_sql)
        if int(mail_group_record.get('is_public')) == int(is_public):
            return

        # 只有创建者本人可以修改群组公开性
        if mail_group_record.get('user_account') != user_account:
            raise Exception("不可操作，只有创建者本人可以修改群组公开性")
        query_sql = "select * from nsyy_gyl.ws_mail_group_permissions where user_account = '{}' " \
            .format(str(user_account))
        user = db.query_one(query_sql)
        if user is None:
            raise Exception("当前用户没有创建公开群组的权限, ", user_account)

        update_sql = 'UPDATE nsyy_gyl.ws_mail_group SET is_public = %s, timer = %s WHERE id = %s'
        args = (is_public, timer, mail_group_id)
        db.execute(update_sql, args, need_commit=True)
        del db

        only_subscriber_can_post = 'no'
        if int(is_public) == 0:
            only_subscriber_can_post = 'yes'
        # 如果群组公开，则允许不在群组中的人向群组发送邮件
        ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
        ssh.execute_shell_command(f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c 'cd /opt/mlmmjadmin/tools; "
                                  f"python3 maillist_admin.py update {mail_group} "
                                  f"only_subscriber_can_post={only_subscriber_can_post} disable_subscription=yes'")
        del ssh

        return
    elif operate_type == mail_config.MAIL_OPERATE_DELETE:
        query_sql = f"select * from nsyy_gyl.ws_mail_group where id = {int(mail_group_id)} "
        mail_group = db.query_one(query_sql)
        if int(mail_group.get('is_public')) == 1:
            raise Exception("公开群组暂不支持删除，如果确定要删除，请先修改为私密群组")

        # 只有创建者本人可以修改群组公开性
        if mail_group.get('user_account') != user_account:
            raise Exception("不可操作，只有创建者本人可以删除当前群组")

        ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
        ssh.execute_shell_command(f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                  f"'cd /opt/mlmmjadmin/tools; python3 maillist_admin.py delete"
                                  f" {mail_group.get('account') + mail_config.MAIL_DOMAIN}'")
        del ssh

        db.execute(f"DELETE FROM nsyy_gyl.ws_mail_group WHERE id = {mail_group_id} ", need_commit=True)
        db.execute(f"DELETE FROM nsyy_gyl.ws_mail_group_members WHERE mail_group_id = {mail_group_id} ",
                   need_commit=True)
        del db


"""
查询当前用户可以看到的所有群组
1. 已加入的群组（包含本人创建的）
2. 公开的群组
"""


def query_mail_group_list(user_account: str):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = "select * from nsyy_gyl.ws_mail_group where id in ( " \
                "select mail_group_id from nsyy_gyl.ws_mail_group_members " \
                "where user_account = '{}' and is_show = 1 ) or is_public = 1 " \
        .format(user_account)
    mail_group_list = db.query_all(query_sql)

    for i in range(len(mail_group_list)):
        mail_group_id = mail_group_list[i].get('id')
        query_sql = "select * from nsyy_gyl.ws_mail_group_members where mail_group_id = {} " \
            .format(mail_group_id)
        members = db.query_all(query_sql)
        mail_group_list[i]["members"] = members

    del db
    return mail_group_list


# 生成指定长度的字符串
def generate_random_string(length):
    # 定义生成字符串的字符集
    characters = string.ascii_lowercase + string.digits
    # 使用random.choices从字符集中随机选择字符，形成指定长度的字符串
    random_string = ''.join(random.choices(characters, k=length))
    return 'maillist_' + random_string


def convert_date_format(date_str):
    try:
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return date_str

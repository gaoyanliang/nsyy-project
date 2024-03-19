import json

import os
from datetime import datetime

import requests

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil
from gylmodules.utils.ssh_utils import SshUtil
from gylmodules.workstation import ws_config

import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header


# ===========================================================
# =============     mail  manager       =====================
# ===========================================================


def send_email(sender: str, recipients: [str], ccs: [str],
               bccs: [str], subject: str, body: str, attachments, names):
    # Create a message container
    msg = MIMEMultipart()
    msg["From"] = sender + ws_config.MAIL_DOMAIN

    # 账户拼接 account【Domain】
    for i in range(len(recipients)):
        recipients[i] = recipients[i] + ws_config.MAIL_DOMAIN
    msg["To"] = ", ".join(recipients)

    if ccs is not None:
        for i in range(len(ccs)):
            ccs[i] = ccs[i] + ws_config.MAIL_DOMAIN
        msg["Cc"] = ", ".join(ccs)
        recipients = recipients + ccs
    if bccs is not None:
        for i in range(len(bccs)):
            bccs[i] = bccs[i] + ws_config.MAIL_DOMAIN
        msg["Bcc"] = ", ".join(bccs)
        recipients = recipients + bccs

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")
    msg["Subject"] = subject
    msg["Date"] = timer

    # 添加自定义内容 "Delivery-Data" header
    if attachments is not None:
        msg['X-Attachments'] = json.dumps(attachments, default=str)
    if names is not None:
        msg['X-Names'] = json.dumps(names, default=str)

    # # Set the "Disposition-Notification-To" header  已读回执
    # msg["Disposition-Notification-To"] = sender_email

    # Add the email body
    msg.attach(MIMEText(body, "plain"))

    if attachments is not None:
        for attachment in attachments:
            filename = attachment.get('file_name')
            filepath = attachment.get('file_path')

            download_file(filepath, filename)

            # 添加附件
            with open(filename, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)

            # # 获取上传文件的MIME类型
            # mime_type = attachment.mimetype
            # if mime_type.startswith('image/'):
            #     # 文件是图像
            #     image = MIMEImage(attachment.read())
            #     image.add_header("Content-ID", "<image1>")
            #     image.add_header('Content-Disposition', 'attachment', filename=filename)
            #     msg.attach(image)
            # else:
            #     # 文件是其他类型
            #     part = MIMEBase("application", "octet-stream")
            #     part.set_payload(attachment.read())
            #     encoders.encode_base64(part)
            #     part.add_header("Content-Disposition", 'attachment', filename=filename)
            #     msg.attach(part)

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SMTP_PORT)
        server.starttls()
        server.login(sender + ws_config.MAIL_DOMAIN, ws_config.MAIL_ACCOUNT_PASSWORD)

        # Send the email
        email_text = msg.as_string()
        server.sendmail(sender + ws_config.MAIL_DOMAIN, recipients, email_text)
        # Close the SMTP server connection
        server.quit()

        ret, mail = __login_mail_server(sender, "Sent")
        # Append the send email to the "Sent" folder
        email_bytes = email_text.encode('utf-8')
        mail.append("Sent", None, None, email_bytes)

        # Close the SMTP server connection
        __close_mail(mail)

        print("Email sent successfully")

        # 发送成功后删除附件文件
        if attachments is not None:
            for attachment in attachments:
                filename = attachment.get('file_name')
                print('准备删除文件 ' + filename)
                os.remove(filename)
    except smtplib.SMTPException as e:
        raise Exception("Failed to send the email: " + e.__str__())


# 下载文件并保存到本地
def download_file(url, filename):
    response = requests.get(url)
    with open(filename, "wb") as file:
        file.write(response.content)


def read_mail_list(user_account: str, page_size: int, page_number: int, mailbox: str):
    # Connect to the IMAP server
    ret, mail = __login_mail_server(user_account, mailbox)
    email_list = []

    # Search for all emails in the mailbox. use UNSEEN search unread mail
    status, email_ids = mail.search(None, "ALL")

    if status == "OK":
        email_id_list = email_ids[0].split()
        # Sort the email IDs in descending order (newest first)
        email_id_list.reverse()

        # Calculate the range of email IDs for the current page
        start_email_id = 1 + (page_size * (page_number - 1))
        end_email_id = page_size * page_number
        print("email count: " + str(len(email_id_list)) + " page_size: " + str(page_size)
              + " , page_number: " + str(page_number))

        # Limit the number of emails to retrieve to the latest 5
        email_id_list = email_id_list[start_email_id - 1:end_email_id]

        # Loop through the email IDs and fetch the email details
        for email_id in email_id_list:
            ret, err = __read_mail_by_mail_id(mail, email_id, False)
            if ret is not None:
                email_list.append(ret)

    # Close the mailbox and log out
    __close_mail(mail)

    return email_list


def read_mail_list_by_keyword(user_account: str, page_size: int, page_number: int, mailbox: str,
                              keyword: str):
    # Connect to the IMAP server
    ret, mail = __login_mail_server(user_account, mailbox)
    email_list = []

    search_criteria = '(OR (FROM \"' + keyword + '\") (SUBJECT \"' + keyword + '\"))'
    search_criteria = search_criteria.encode('utf-8')
    # search_criteria = '(SUBJECT "测试")'.encode('utf-8')
    # search_criteria = '(FROM "U111")'.encode('utf-8')
    # Search for all emails in the mailbox. use UNSEEN search unread mail
    status, email_ids = mail.search(None, search_criteria)

    if status == "OK":
        email_id_list = email_ids[0].split()
        # Sort the email IDs in descending order (newest first)
        email_id_list.reverse()

        # Calculate the range of email IDs for the current page
        start_email_id = 1 + (page_size * (page_number - 1))
        end_email_id = page_size * page_number
        print("email count: " + str(len(email_id_list)) + " page_size: " + str(page_size)
              + " , page_number: " + str(page_number))

        # Limit the number of emails to retrieve to the latest 5
        email_id_list = email_id_list[start_email_id - 1:end_email_id]

        # Loop through the email IDs and fetch the email details
        for email_id in email_id_list:
            ret, err = __read_mail_by_mail_id(mail, email_id, False)
            if ret is not None:
                email_list.append(ret)

    # Close the mailbox and log out
    __close_mail(mail)

    return email_list


def read_mail(user_account: str, mail_id: str, mailbox: str):
    # Connect to the IMAP server
    ret, mail = __login_mail_server(user_account, mailbox)

    ret, err = __read_mail_by_mail_id(mail, bytes(str(mail_id), 'utf-8'), True)
    # Close the mailbox and log out
    __close_mail(mail)

    return ret


def delete_mail(user_account: str, mail_ids, mailbox: str):
    # Connect to the IMAP server
    ret, mail = __login_mail_server(user_account, mailbox)

    # 标记为已删除
    for id in mail_ids:
        mail.store(bytes(str(id), 'utf-8'), '+FLAGS', '(\Deleted)')

    # 彻底删除
    mail.expunge()

    # Close the mailbox and log out
    __close_mail(mail)


def fetch_attachment(user_account: str, mail_id: int, mailbox: str, file_name: str):
    # Connect to the IMAP server
    ret, mail = __login_mail_server(user_account, mailbox)

    # Fetch the email based on the ID.  peek 防止修改邮件已读状态
    result, message_data = mail.fetch(bytes(str(mail_id), 'utf-8'), '(BODY.PEEK[])')
    if result == "OK":
        # Parse the email message
        msg = email.message_from_bytes(message_data[0][1])
        # Extract email details
        subject, encoding = decode_header(msg.get("Subject"))[0]
        subject = subject.decode(encoding) if encoding else subject
        print("Subject              : {}".format(subject))

        for part in msg.walk():
            if part.get_content_maintype() == "multipart" or part.get("Content-Disposition") is None:
                continue
            filename = part.get_filename()
            if filename == file_name:
                return part.get_payload(decode=True)

    # Close the mailbox and log out
    __close_mail(mail)
    return None


"""通过 email id 读取邮件"""


def __read_mail_by_mail_id(mail, email_id, query_body: bool):
    # Fetch the email based on the ID.  peek 防止修改邮件已读状态
    result, message_data = mail.fetch(email_id, '(FLAGS BODY.PEEK[])')
    if result == "OK":
        # Extract email flags and Check if the email is marked as unread
        flags = message_data[0][0].decode("utf-8").split("FLAGS (")[1].split(")")[0]
        is_unread = "\\Seen" not in flags

        # 将邮件标记为已读
        if is_unread and query_body:
            mail.store(email_id, '+FLAGS', '\Seen')

        # Parse the email message
        msg = email.message_from_bytes(message_data[0][1])
        # Extract email details
        subject, encoding = decode_header(msg.get("Subject"))[0]
        subject = subject.decode(encoding) if encoding else subject

        # Print the email details
        print(f"================== mail {email_id} ==================")
        print("Unread               : {}".format('Yes' if is_unread else 'No'))
        print("Email ID             : {}".format(email_id))
        print("Subject              : {}".format(subject))
        print("From                 : {}".format(msg.get("From")))
        print("To                   : {}".format(msg.get("To")))
        print("CC                   : {}".format(msg.get("CC")))
        print("Bcc                  : {}".format(msg.get("Bcc")))
        print("Priority             : {}".format(msg.get("Priority")))
        print("ReplyToList          : {}".format(msg.get("ReplyToList")))
        print("Date                 : {}".format(msg.get("Date")))
        print("X-Attachments        : {}".format(msg.get("X-Attachments")))
        print("X-Names              : {}".format(msg.get("X-Names")))

        # Extract attachments
        attachments = []
        if msg.get('X-Attachments') is not None:
            attachments = json.loads(msg.get('X-Attachments'))
        names = []
        if msg.get('X-Names') is not None:
            names = json.loads(msg.get('X-Names'))
        # for part in msg.walk():
        #     if part.get_content_maintype() == "multipart" or part.get("Content-Disposition") is None:
        #         continue
        #     filename = part.get_filename()
        #     if filename:
        #         attachments.append(filename)
        # print("Attachments count    : {}".format(len(attachments)))
        # for attachment in attachments:
        #     print(attachment)

        # Get the email content
        body = None
        if query_body:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type.__contains__('multipart/mixed'):
                        continue
                    if content_type.__contains__('application/octet-stream'):
                        continue

                    if "attachment" not in content_disposition:
                        body = part.get_payload(decode=True)

                        # Check for encoding and decode if necessary
                        charset = part.get_content_charset()
                        if charset:
                            body = body.decode(charset, 'ignore')

                        # print(body)
            else:
                body = msg.get_payload(decode=True)

                # Check for encoding and decode if necessary
                charset = msg.get_content_charset()
                if charset:
                    body = body.decode(charset, 'ignore')

                # print(body)
        # if msg.is_multipart():
        #     for part in msg.walk():
        #         if part.get_content_type() == "text/plain":
        #             body = part.get_payload(decode=True).decode()
        #             # log.debug("Message:")
        #             # print(body)
        # else:
        #     body = msg.get_payload(decode=True).decode()
        # log.debug("Message:")
        # print(body)
        if type(body) == bytes:
            # 将字节对象转换为字符串
            body = body.decode('utf-8')

        return {
            "id": email_id.decode("utf-8"),
            "Unread": True if is_unread else False,
            "Subject": subject,
            "From": msg.get("From"),
            "To": msg.get("To"),
            "CC": msg.get("CC"),
            "Bcc": msg.get("Bcc"),
            "ReplyToList": msg.get("ReplyToList"),
            "Date": msg.get("Date"),
            "attachments": attachments,
            "names": names,
            "body": body,
        }, None
    return None, f"read email {email_id} failed"


"""登陆邮件服务器"""


def __login_mail_server(user_account: str, mailbox: str):
    # Connect to the IMAP server
    mail = imaplib.IMAP4_SSL(ws_config.MAIL_SSH_HOST, ws_config.MAIL_IMAP_PORT)
    print("Successed to connect to the IMAP server " + ws_config.MAIL_SSH_HOST)

    # Login to the email account
    mail_account = user_account + ws_config.MAIL_DOMAIN
    status, _ = mail.login(mail_account, ws_config.MAIL_ACCOUNT_PASSWORD)
    if "OK" not in status:
        print(user_account + " Login failed. Please check your credentials.")
        mail.logout()
        return "Fail", f" {mail_account} Login failed. Please check your credentials."
    print(user_account + " Login successed. ")

    # list mailboxes
    status, data = mail.list()
    if status != "OK":
        print("Failed to get mail list.")
        mail.logout()
        return "Fail", "Failed to get mail list."
    print(f'mailboxes: {data}')

    # Select the mailbox you want to read, 使用 select() 方法选择要读取的邮件文件夹
    status, _ = mail.select(mailbox)
    if status != "OK":
        print("Failed to select the mailbox: " + mailbox)
        mail.logout()
        return "Fail", "Failed to select the mailbox."
    print(f"select {mailbox}")

    return "OK", mail


def __close_mail(mail):
    # Close the mailbox and log out
    print("Close the mailbox and log out")
    mail.close()
    mail.logout()


# ===========================================================
# =============  mail account manager   =====================
# ===========================================================


def create_mail_account(user_list):
    # 通过脚本创建邮箱账户
    ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
    is_first = True
    for mail_name in user_list:
        mail_name = mail_name + ws_config.MAIL_DOMAIN
        if is_first:
            ssh.execute_shell_command(
                f"bash /home/yanliang/iRedMail/tools/create_mail_user_SQL.sh "
                f"'{mail_name}' '{ws_config.MAIL_ACCOUNT_PASSWORD}' > "
                f"/tmp/create_multiple_mail_user.sql")
            is_first = False
            continue

        ssh.execute_shell_command(
            f"bash /home/yanliang/iRedMail/tools/create_mail_user_SQL.sh "
            f"'{mail_name}' '{ws_config.MAIL_ACCOUNT_PASSWORD}' >> "
            f"/tmp/create_multiple_mail_user.sql")

    ssh.execute_shell_command("mysql -uroot -p111111 vmail -e 'source /tmp/create_multiple_mail_user.sql'")
    ssh.execute_shell_command("rm /tmp/create_multiple_mail_user.sql")
    del ssh


def delete_mail_account(user_account):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)

    # 删除用户创建的群组
    query_sql = "select id, name from nsyy_gyl.ws_mail_group where user_account = '{}' ".format(user_account)
    mail_group_list = db.query_all(query_sql)
    for mail_group in mail_group_list:
        ssh.execute_shell_command(
            f"cd /opt/mlmmjadmin/tools; python3 maillist_admin.py delete"
            f" {mail_group.get('name') + ws_config.MAIL_DOMAIN}")

        args = (mail_group.get('id'))
        delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group " \
                     "WHERE id = %s "
        db.execute(delete_sql, args, need_commit=True)
        delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
                     "WHERE mail_group_id = %s "
        db.execute(delete_sql, args, need_commit=True)

    # 将用户从加入的群组中移除
    query_sql = "select id, name from nsyy_gyl.ws_mail_group where id in " \
                "(select mail_group_id from nsyy_gyl.ws_mail_group_members where user_account = '{}' ) " \
        .format(user_account)
    mail_group_list = db.query_all(query_sql)
    for mail_group in mail_group_list:
        ssh.execute_shell_command(
            f"cd /opt/mlmmjadmin/tools; python3 maillist_admin.py remove_subscribers"
            f" {mail_group.get('name') + ws_config.MAIL_DOMAIN} {user_account + ws_config.MAIL_DOMAIN}")

    args = (user_account)
    delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
                 "WHERE user_account = %s "
    db.execute(delete_sql, args, need_commit=True)


# ===========================================================
# =============   mail group manager    =====================
# ===========================================================


def create_mail_group(user_account: str, user_name: str, mail_group_name: str,
                      mail_group_description: str, user_list, is_public: int):
    """
    创建邮箱分组
    :param user_account:
    :param user_name:
    :param mail_group_name:
    :param mail_group_description:
    :param user_list:
    :param is_public:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    query_sql = "select id from nsyy_gyl.ws_mail_group where name = '{}' ".format(mail_group_name)
    mail_group = db.query_one(query_sql)
    if mail_group is not None:
        raise Exception("邮箱群组名已被占用，请输入新的名字（邮箱群组名仅支持字母数字组合）")

    # 1. 调用邮箱服务器群组管理脚本，创建新群组
    group_name = mail_group_name + ws_config.MAIL_DOMAIN
    # 通过脚本创建邮箱群组
    ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
    # 检查群组列表是否存在
    output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; python3 maillist_admin.py info {group_name}")
    if 'Error: NO_SUCH_ACCOUNT' not in output:
        raise Exception("邮箱群组群组" + mail_group_name + " 已存在")

    if is_public == 0:
        # 群组不公开
        output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                           f"python3 maillist_admin.py create {group_name}"
                                           f" only_subscriber_can_post=yes disable_archive=no ")
        if 'Created.' not in output:
            raise Exception("邮箱群组群组" + mail_group_name + " 创建失败")
    else:
        # 群组公开
        output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                           f"python3 maillist_admin.py create {group_name}"
                                           f" only_subscriber_can_post=no disable_archive=no ")
        if 'Created.' not in output:
            raise Exception("邮箱群组群组" + mail_group_name + " 创建失败")

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")
    args = (mail_group_name, mail_group_description, user_account, user_name, timer, is_public)
    insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group (name, description, " \
                 "user_account, user_name, timer, is_public) " \
                 "VALUES (%s,%s,%s,%s,%s,%s)"
    last_rowid = db.execute(insert_sql, args, need_commit=True)
    if last_rowid == -1:
        raise Exception("新群组入库失败!")

    # 2. 组装用户邮箱账号 [用户账号]@邮箱后缀， 将用户邮箱加入到新群组中
    joined_user_list = []
    failed_user_list = []
    # 将创建者本人也加入
    user_list.append({
        "user_account": user_account,
        "user_name": user_name
    })
    for user in user_list:
        account = user.get('user_account')
        mail_account = account + ws_config.MAIL_DOMAIN
        # 账号存在将账号加入到
        output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                           f"python3 maillist_admin.py add_subscribers {group_name} {mail_account} ")
        # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
        if 'Added.' not in output:
            failed_user_list.append(user)
        else:
            joined_user_list.append(user)
            query_sql = "select * from nsyy_gyl.ws_mail_group_members " \
                        "where mail_group_id = {} and user_account = '{}' " \
                .format(int(last_rowid), str(user.get('user_account')))
            mem = db.query_one(query_sql)
            if mem is None:
                args = (last_rowid, user.get('user_account'), user.get('user_name'), timer)
                insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group_members (mail_group_id, " \
                             "user_account, user_name, timer) " \
                             "VALUES (%s,%s,%s,%s)"
                db.execute(insert_sql, args, need_commit=True)

    del ssh
    return failed_user_list


def operate_mail_group(user_account: str, mail_group_id: int, mail_group_name: str, operate_type: int,
                       new_mail_group_desc: str, user_list, is_public: int):
    """
    编辑群组
    operate_type = 0 更新群组描述
    operate_type = 1 向群组中新增用户
    operate_type = 2 从群组中移除用户
    operate_type = 3 修改群组公开性
    operate_type = 4 删除群组 (对本人隐藏，但群组还在)
    :param user_account:
    :param mail_group_id:
    :param mail_group_name:
    :param operate_type:
    :param new_mail_group_desc:
    :param user_list:
    :param is_public:
    :return:
    """
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    timer = datetime.now()
    timer = timer.strftime("%Y-%m-%d %H:%M:%S")
    if operate_type == ws_config.MAIL_OPERATE_UPDATE:
        # 更新群组描述
        update_sql = 'UPDATE nsyy_gyl.ws_mail_group SET description = %s, timer = %s WHERE name = %s'
        args = (new_mail_group_desc, timer, mail_group_name)
        db.execute(update_sql, args, need_commit=True)
        return
    elif operate_type == ws_config.MAIL_OPERATE_ADD:
        # 添加群组成员
        ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
        joined_user_list = []
        failed_user_list = []
        for user in user_list:
            account = user.get('user_account')
            mail_account = account + ws_config.MAIL_DOMAIN
            # 账号存在将账号加入到邮箱群组
            output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                               f"python3 maillist_admin.py add_subscribers"
                                               f" {mail_group_name + ws_config.MAIL_DOMAIN} {mail_account} ")
            # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
            if 'Added.' not in output:
                failed_user_list.append(user)
            else:
                joined_user_list.append(user)
        del ssh

        for user in joined_user_list:
            query_sql = "select * from nsyy_gyl.ws_mail_group_members " \
                        "where mail_group_id = {} and user_account = '{}' " \
                .format(int(mail_group_id), str(user.get('user_account')))
            mem = db.query_one(query_sql)
            if mem is None:
                args = (mail_group_id, user.get('user_account'), user.get('user_name'), timer)
                insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group_members (mail_group_id, " \
                             "user_account, user_name, timer) " \
                             "VALUES (%s,%s,%s,%s)"
                db.execute(insert_sql, args, need_commit=True)

        return failed_user_list
    elif operate_type == ws_config.MAIL_OPERATE_REMOVE:
        # 移除群组成员
        ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
        removed_user_list = []
        failed_user_list = []
        for user in user_list:
            account = user.get('user_account')
            mail_account = account + ws_config.MAIL_DOMAIN
            # 账号存在将账号加入到邮箱群组
            output = ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                               f"python3 maillist_admin.py remove_subscribers"
                                               f" {mail_group_name + ws_config.MAIL_DOMAIN} {mail_account} ")
            # 将执行不成功的（账号不存在，添加失败） 移除列表，并想办法告知客户端
            if 'Removed.' not in output:
                failed_user_list.append(user)
            else:
                removed_user_list.append(user)
        del ssh

        for user in removed_user_list:
            args = (mail_group_id, user.get('user_account'), user.get('user_name'))
            delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
                         "WHERE mail_group_id = %s and user_account = %s and user_name = %s "
            db.execute(delete_sql, args, need_commit=True)
        return failed_user_list
    elif operate_type == ws_config.MAIL_OPERATE_PUBLIC:
        query_sql = "select * from nsyy_gyl.ws_mail_group " \
                    "where id = {} ".format(int(mail_group_id))
        mail_group = db.query_one(query_sql)
        if int(mail_group.get('is_public')) == int(is_public):
            return

        # 只有创建者本人可以修改群组公开性
        if mail_group.get('user_account') != user_account:
            raise Exception("不可操作，只有创建者本人可以修改群组公开性")
        query_sql = "select * from nsyy_gyl.ws_mail_group_permissions where user_account = '{}' " \
            .format(str(user_account))
        user = db.query_one(query_sql)
        if user is None:
            raise Exception("当前用户没有创建公开群组的权限")

        update_sql = 'UPDATE nsyy_gyl.ws_mail_group SET is_public = %s, timer = %s WHERE name = %s'
        args = (is_public, timer, mail_group_name)
        db.execute(update_sql, args, need_commit=True)

        if is_public == 1:
            # 如果群组公开，则允许不在群组中的人向群组发送邮件
            ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
            ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
                                      f"python3 maillist_admin.py update"
                                      f" {mail_group_name + ws_config.MAIL_DOMAIN} "
                                      f"only_moderator_can_post=yes disable_subscription=yes")
            del ssh

        return
    elif operate_type == ws_config.MAIL_OPERATE_DELETE:
        # 删除群组仅对本人隐藏该群组，但是群组依然存在，群组其他人依旧可以发送邮件
        update_sql = 'UPDATE nsyy_gyl.ws_mail_group_members SET is_show = 0, timer = %s ' \
                     'WHERE user_account = %s and mail_group_id = %s '
        args = (timer, user_account, mail_group_id)
        db.execute(update_sql, args, need_commit=True)
        # query_sql = "select * from nsyy_gyl.ws_mail_group " \
        #             "where id = {} ".format(int(mail_group_id))
        # mail_group = db.query_one(query_sql)
        # # 只有创建者本人可以删除
        # if mail_group.get('user_account') == user_account:
        #     ssh = SshUtil(ws_config.MAIL_SSH_HOST, ws_config.MAIL_SSH_USERNAME, ws_config.MAIL_SSH_PASSWORD)
        #     ssh.execute_shell_command(f"cd /opt/mlmmjadmin/tools; "
        #                               f"python3 maillist_admin.py delete"
        #                               f" {mail_group_name + ws_config.MAIL_DOMAIN} archive=yes ")
        #     del ssh
        #
        #     args = (mail_group_id)
        #     delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group " \
        #                  "WHERE id = %s "
        #     db.execute(delete_sql, args, need_commit=True)
        #
        #     delete_sql = "DELETE FROM nsyy_gyl.ws_mail_group_members " \
        #                  "WHERE mail_group_id = %s "
        #     db.execute(delete_sql, args, need_commit=True)
        # else:
        #     raise Exception("当前用户没有当前群组的权限，只有创建者本人可以删除")
    del db


def query_mail_group_list(user_account: str):
    """
    查询当前用户可以看到的所有群组
    1. 已加入的群组（包含本人创建的）
    2. 公开的群组
    :param user_account:
    :return:
    """
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

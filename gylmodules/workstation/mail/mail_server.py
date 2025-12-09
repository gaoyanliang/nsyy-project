import hashlib
import json
import logging
import mimetypes

import string
import random
import base64
import os
import time
import traceback
import uuid
from datetime import datetime
from email.mime.image import MIMEImage
from pathlib import Path
from threading import Lock
from typing import Dict, List

import redis
import requests

from gylmodules import global_config, global_tools
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

from gylmodules.workstation.message import msg_push_tool

pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)
logger = logging.getLogger(__name__)

# 全局预编译正则
_EMAIL_IN_BRACKETS = re.compile(r'<([^>@]+@[^>]+)>')  # 更精准，只匹配真实邮箱
_EMAIL_IN_BRACKETS_LOOSE = re.compile(r'<([^>]+)>')


# 全局连接池（进程内单例）
_IMAP_POOL: Dict[str, tuple] = {}  # key: user_account, value: (mail, last_used_time)
_POOL_LOCK = Lock()
_POOL_TIMEOUT = 10 * 60  # 10 分钟没用就关闭


"""获取或创建长连接"""


def get_imap_connection(user_account: str, mailbox: str = "INBOX"):
    user_account = user_account.strip()
    if not user_account:
        return None, None
    with _POOL_LOCK:
        # 1. 检查连接池里有没有这个用户的连接
        if user_account in _IMAP_POOL:
            mail, last_used = _IMAP_POOL[user_account]
            # 检查连接是否还活着
            try:
                mail.noop()  # 最轻量心跳
                select_status, _ = mail.select(mailbox)
                if select_status != "OK":
                    raise Exception(f"Select {mailbox} failed")
                _IMAP_POOL[user_account] = (mail, time.time())
                logger.debug(f"复用 IMAP 连接: {user_account}")
                return 'OK', mail
            except:
                # 连接死了，删掉重建
                logger.warning(f"IMAP 连接已失效，重新登录: {user_account}")
                try:
                    mail.logout()
                except:
                    pass
                del _IMAP_POOL[user_account]

        # 2. 没有就新建（只慢这一次）
        logger.debug(f"创建新的 IMAP 连接: {user_account}")
        ret, mail = __login_mail_server(user_account, mailbox)
        if ret:
            _IMAP_POOL[user_account] = (mail, time.time())
            return "OK", mail
        else:
            return None, None


def close_idle_connections():
    """后台定时清理空闲连接"""
    with _POOL_LOCK:
        now = time.time()
        to_remove = []
        for user, (mail, last_used) in _IMAP_POOL.items():
            if now - last_used > _POOL_TIMEOUT:
                try:
                    if mail:
                        mail.close()
                        mail.logout()
                except:
                    pass
                to_remove.append(user)
        for user in to_remove:
            del _IMAP_POOL[user]


"""登陆邮件服务器"""


def __login_mail_server(user_account: str, mailbox: str, retries=3):
    status, mail, mail_account = '', None, ''
    for i in range(retries):
        try:
            # Connect to the IMAP server & Login to the email account
            mail = imaplib.IMAP4_SSL(mail_config.MAIL_SSH_HOST, mail_config.MAIL_IMAP_PORT)
            mail_account = user_account + mail_config.MAIL_DOMAIN
            mail_account = mail_account.lower()
            status, _ = mail.login(mail_account, mail_config.MAIL_ACCOUNT_PASSWORD)
            break
        except Exception as e:
            logger.error(f"DEBUG  [Retry {i+1}] IMAP connection failed: {e}")
            time.sleep(1)

    if "OK" not in status:
        logger.warning(f"{user_account} Login failed. Please check your credentials.")
        mail.logout()
        return None, f" {mail_account} Login failed. Please check your credentials."

    # Select the mailbox you want to read, 使用 select() 方法选择要读取的邮件文件夹
    status, _ = mail.select(mailbox)
    if status != "OK":
        mail.logout()
        return None, "Failed to select the mailbox {}".format(mailbox)

    return "OK", mail



"""高可靠邮件发送函数（带重试、失败隔离、资源安全清理）"""

def send_email_robust(json_data, max_retries: int = 5) -> bool:
    start_time = time.time()
    sender = json_data.get("sender")
    if not sender:
        raise ValueError("发送人不能为空")

    subject = json_data.get("subject", "")
    body = json_data.get("body", "")
    attachments = json_data.get("attachments") or []
    names = json_data.get("names") or {}

    # 生成唯一 Message-ID（用于去重和追踪）
    message_id = f"<{uuid.uuid4()}@nsyy.com>"

    # 提前构建完整邮件对象（后面所有操作都用这个对象）
    msg, all_people, all_recipients = build_email_message(json_data, message_id)
    sender_email = f"{sender}{mail_config.MAIL_DOMAIN}".lower()

    # 临时文件列表，用于最后统一清理
    temp_files = []
    try:
        # Step 1: 下载附件到本地（带异常处理）
        for attachment in attachments:
            filename = attachment.get('file_name')
            filename = sanitize_filename(filename)
            filepath = attachment.get('file_path')
            if not filename or not filepath:
                continue

            try:
                local_path = download_file(filepath, filename)
                local_path = local_path or filename
            except Exception as e:
                logger.warning(f"附件下载失败 {filename}: {e}")
                raise Exception(f"附件下载失败 {filename}: {e}")
                local_path = filename if os.path.exists(filename) else None

            if local_path:
                temp_files.append(local_path)

        # 添加附件到邮件
        attach_files_to_message(msg, attachments, temp_files)

        # Step 2: 核心发送 + 重试机制
        success = False
        last_exception = None

        for attempt in range(max_retries):
            try:
                with smtplib.SMTP(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SMTP_PORT, timeout=30) as server:
                    server.starttls()
                    server.login(sender_email, mail_config.MAIL_ACCOUNT_PASSWORD)
                    server.send_message(msg, from_addr=sender_email, to_addrs=all_recipients)
                logger.debug(f"邮件发送成功 → {subject} | To: {len(all_recipients)} 人 | Message-ID: {message_id}")
                success = True
                break
            except (smtplib.SMTPServerDisconnected,
                    smtplib.SMTPConnectError,
                    smtplib.SMTPDataError,
                    OSError,
                    TimeoutError) as e:
                last_exception = e
                wait = (2 ** attempt) + random.uniform(0, 1)  # 指数退避 + 抖动
                logger.warning(f"邮件发送失败（第 {attempt + 1} 次），{wait:.1f}s 后重试: {e}")
                time.sleep(wait)

            except Exception as e:
                # 其他异常视为致命，不重试
                logger.error(f"邮件发送致命错误: {e}")
                last_exception = e
                break

        # Step 3: 只有真正发送成功，才执行后续操作
        if success:
            try:
                save_to_sent_folder(sender, msg.as_string())
            except Exception as e:
                logger.error(f"保存到发件箱失败（但邮件已发出）: {e}")

            try:
                rec_list, send = query_pers_ids(all_people, sender)
                global_tools.start_thread(msg_push_tool.push_msg_to_devices,
                                          (rec_list, "新邮件", f"来自 {names.get(sender.lower(), '')} 的新邮件 {subject}"))
                global_tools.socket_push("新邮件通知", {
                    "socketd": ["m_app"], "type": 400, 'pers_id': rec_list,
                    'timer': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "socket_data": {"chat_type": 0, "context_type": 11, "sender": 110100, "sender_name": "admin",
                                    "group_id": None, "receiver": send, "receiver_name": names.get(sender, ""),
                                    "context": {
                                        "type": 4, "title": "新邮件",
                                        "description": f"来自 {names.get(sender.lower(), '')} 的新邮件 {subject}",
                                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    },
                                    "timer": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }})
            except Exception as e:
                logger.error(f"推送通知失败（但邮件已发出）: {e}")

            return True
        else:
            logger.error(f"邮件发送最终失败（已重试 {max_retries} 次）: {last_exception}")
            raise smtplib.SMTPException(f"邮件发送失败，已重试 {max_retries} 次") from last_exception

    finally:
        logger.debug(f"邮件发送结束 耗时 {time.time() - start_time} s")
        # 无论成功失败，都彻底清理临时文件
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass


# ============================== 发送辅助函数 ==============================


def build_email_message(json_data: dict, message_id: str):
    all_people = []
    msg = MIMEMultipart()
    sender = json_data["sender"]
    sender_email = f"{sender}{mail_config.MAIL_DOMAIN}".lower()

    msg["From"] = sender_email
    msg["Subject"] = json_data.get("subject", "")
    msg["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg["Message-ID"] = message_id

    all_people.append(sender)
    recipients = json_data.get("recipients", [])
    all_people = all_people + recipients
    recipients_group = json_data.get("recipients_group", [])
    if not recipients and not recipients_group:
        raise ValueError("至少需要添加一位接收人或群组")
    ccs = json_data.get("ccs", [])
    all_people = all_people + ccs
    bccs = json_data.get("bccs", [])
    all_people = all_people + bccs
    # 如果收件人在群组中，则不单独给收件人发
    if recipients_group:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        group_list = ', '.join(f"'{item}'" for item in recipients_group)
        db_mail_group = db.query_all(f"SELECT id, account FROM nsyy_gyl.ws_mail_group WHERE account in ({group_list})")
        if db_mail_group:
            recipients_group = [item['account'] for item in db_mail_group]
            group_id_list = [item['id'] for item in db_mail_group]

            account_in_group_list = db.query_all(f"SELECT user_account FROM nsyy_gyl.ws_mail_group_members "
                                                 f"WHERE mail_group_id in ({','.join(str(i) for i in group_id_list)})")

            if account_in_group_list:
                account_in_group_list = [item['user_account'] for item in account_in_group_list]
                all_people = all_people + account_in_group_list
                recipients = [item for item in recipients if item not in account_in_group_list]
        del db

    def process_recipients(recipient_list):
        return [f"{r}{mail_config.MAIL_DOMAIN}".lower() for r in recipient_list]

    to_recipients = process_recipients(recipients + recipients_group)
    cc_recipients = process_recipients(ccs)
    bcc_recipients = process_recipients(bccs)

    all_recipients = to_recipients + cc_recipients + bcc_recipients
    # 处理收件人（包含群组展开）
    msg["To"] = ", ".join(to_recipients)
    if cc_recipients:
        msg["Cc"] = ", ".join(cc_recipients)
    if bcc_recipients:
        msg["Bcc"] = ", ".join(bcc_recipients)

    # 自定义头部
    if json_data.get("attachments"):
        msg['X-Attachments'] = json.dumps(json_data["attachments"], default=str)
    if json_data.get("names"):
        msg['X-Names'] = json.dumps(json_data["names"], default=str)

    # # Set the "Disposition-Notification-To" header  已读回执
    # msg["Disposition-Notification-To"] = sender_email

    # msg.attach(MIMEText(json_data.get("body", ""), "plain"))
    msg.attach(MIMEText(json_data.get("body", ""), "plain", "utf-8"))
    return msg, all_people, all_recipients


def attach_files_to_message(msg: MIMEMultipart, attachments: list, local_files: list):
    for attachment, local_path in zip(attachments, [f for f in local_files if f]):
        if not os.path.exists(local_path):
            continue
        with open(local_path, "rb") as f:
            mime_type, _ = mimetypes.guess_type(local_path)
            if mime_type and mime_type.startswith('image/'):
                part = MIMEImage(f.read())
                part.add_header("Content-ID", f"<{os.path.basename(local_path)}>")
            else:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=attachment.get('file_name'))
            msg.attach(part)


"""清理文件名：去掉所有控制字符、首尾空白、换行等"""


def sanitize_filename(filename: str) -> str:

    if not filename:
        return "unknown_attachment"
    # 移除所有 ASCII 控制字符（0-31 和 127）
    filename = ''.join(c for c in filename if ord(c) >= 32 and c not in '\r\n\t')
    # 去掉首尾空白和可能残留的奇怪字符
    filename = filename.strip()
    filename = filename.replace(' ', '_')
    # 可选：如果为空或太奇怪，给个默认名
    return filename or "attachment"


"""根据OA账号查询pers id"""


def query_pers_ids(oa_list, sender):
    if not oa_list:
        return []
    redis_client = redis.Redis(connection_pool=pool)
    rec_list, send = [], 0
    for item in oa_list:
        pers_id = redis_client.get(f"mail_emp_pers_id:{item.lower()}")
        if pers_id:
            rec_list.append(pers_id)
    send = redis_client.get(f"mail_emp_pers_id:{sender.lower()}")
    return rec_list, send


"""将邮件保存至已发送目录中"""

def save_to_sent_folder(sender, email_text):
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(mail_config.MAIL_SSH_HOST, mail_config.MAIL_IMAP_PORT)
        mail_account = f"{sender}{mail_config.MAIL_DOMAIN}"
        mail.login(mail_account, mail_config.MAIL_ACCOUNT_PASSWORD)
        mail.append("Sent", None, None, email_text.encode('utf-8'))
    except Exception as e:
        logger.error(f"Warning: Failed to save to Sent folder: {str(e)}")


"""下载文件并保存到本地， 服务器下载时，访问不到外网，需要将服务器地址改为本地"""

def download_file(url, filename):
    if not global_config.run_in_local:
        url = url.replace("oa.nsyy.com.cn", "127.0.0.1")
        url = url.replace("120.194.96.67", "127.0.0.1")
        url = url.replace("192.168.3.12", "127.0.0.1")
    response = requests.get(url)
    with open(filename, "wb") as file:
        file.write(response.content)


"""获取邮件的标志和标签"""


def get_email_flags(mail, uid):
    status, flags = mail.fetch(uid, '(FLAGS)')
    if status != 'OK' or not flags:
        return []

    flags_str = flags[0].decode('utf-8') if isinstance(flags[0], bytes) else str(flags[0])
    matches = re.findall(r'\\?\w+|\&\w+', flags_str)
    flag_code_list = [f for f in matches if f.startswith(('\\', '&'))]

    if flag_code_list:
        flag_list = []
        redis_client = redis.Redis(connection_pool=pool)
        for item in flag_code_list:
            flag = redis_client.get(f"mail_flag:{item}")
            if flag:
                flag_list.append(json.loads(flag))
        return flag_list
    return []


""" 分页读取邮件列表（仅获取邮件头、是否已读标识） """


def read_mail_list(user_account: str, page_size: int, page: int, mailbox: str, keyword: str = None):
    start_time = time.time()
    ret, mail = get_imap_connection(user_account, mailbox)
    if not ret:
        return [], 0

    try:
        # 1. 搜索
        # criteria = f'(OR SUBJECT "{keyword}" (OR FROM "{keyword}" (OR BODY "{keyword}" HEADER "X-Names" "{keyword}")))' if keyword else "ALL"
        criteria = f'(OR OR SUBJECT "{keyword}" FROM "{keyword}" HEADER "X-Names" "{keyword}")' if keyword else "ALL"
        # criteria = f'OR SUBJECT "{keyword}" FROM "{keyword}"' if keyword else "ALL"
        if isinstance(criteria, str):
            criteria_bytes = criteria.encode('utf-8')
        else:
            criteria_bytes = criteria
        # 用 UID search（更可靠）
        status, data = mail.uid('SEARCH', None, criteria_bytes)
        if status != "OK" or not data[0]:
            return [], 0

        uids = data[0].split()
        if not uids:
            return [], 0

        total = len(uids)
        # 倒序（最新在前）
        uids = uids[::-1]

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_uids = uids[start:end]
        if not page_uids:
            return [], total

        # 2. 一次 fetch 拿 UID + FLAGS + INTERNALDATE + 需要的头
        fetch_cmd = ("(UID FLAGS INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT "
                     "DATE MESSAGE-ID REPLY-TO X-Attachments X-Names)])")
        status, msg_data = mail.uid('FETCH', ','.join(u.decode() for u in page_uids), fetch_cmd)
        if status != "OK":
            return [], total

        results = []
        for item in msg_data:
            if len(item) != 2:
                continue
            header_part, body_part = item

            # 跳过非邮件响应（如 OK 状态）
            if not isinstance(header_part, bytes) or not isinstance(body_part, bytes):
                continue

            try:
                header_str = header_part.decode('utf-8', errors='ignore')
                uid_match = re.search(r'UID (\d+)', header_str)
                if not uid_match:
                    continue
                uid = uid_match.group(1)

                # 提取 FLAGS（关键！）
                flags_match = re.search(r'FLAGS \(([^)]*)\)', header_str)
                flags = []
                if flags_match:
                    raw_flags = flags_match.group(1)
                    flags = [f.strip() for f in raw_flags.split() if f.strip()]
                    if flags:
                        flag_list = []
                        redis_client = redis.Redis(connection_pool=pool)
                        for item in flags:
                            if redis_client.exists(f"mail_flag:{item}"):
                                flag = json.loads(redis_client.get(f"mail_flag:{item}"))
                                flag_list.append({"custome_name": flag.get('custome_name'),
                                                  "custome_code": flag.get('custome_code'), "status": flag.get('status')})
                        flags = flag_list

                is_unread = '\\Seen' not in header_str

                # 解析邮件头
                msg = email.message_from_bytes(body_part)

                names = {}
                if msg.get('X-Names'):
                    try:
                        names = json.loads(msg.get('X-Names'))
                    except json.JSONDecodeError:
                        names = {}

                x_attachments = msg.get('X-Attachments', '[]') or '[]'
                x_attachments = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', x_attachments)  # 移除所有控制字符
                cur_mail = {
                    "id": uid, "message_id": (msg.get("MESSAGE-ID") or ""),
                    "Unread": is_unread, "Subject": _fast_decode_header(msg.get("Subject", "")) or "(无主题)",
                    "From": _clean_address_field(msg.get("From", "")),
                    "To": _clean_address_field(msg.get("To", "")),
                    "CC": _clean_address_field(msg.get("CC", "")),
                    "Bcc": _clean_address_field(msg.get("Bcc", "")),
                    "Date": convert_date_format(msg.get("Date", "")),
                    "ReplyToList": msg.get("Reply-To", ""),
                    "flags": flags, "attachments": json.loads(x_attachments) or [], "names": names,
                }
                cur_mail['From_name'] = get_emp_name_group_name(cur_mail['From'])
                cur_mail['To_name'] = get_emp_name_group_name(cur_mail['To'])
                cur_mail['CC_name'] = get_emp_name_group_name(cur_mail['CC'])
                cur_mail['Bcc_name'] = get_emp_name_group_name(cur_mail['Bcc'])
                cur_mail['is_group_mail'] = True if cur_mail.get('To', '').__contains__('maillist') else False
                results.append(cur_mail)
            except Exception as e:
                logger.error(f"Failed to parse email: {e} {msg.get('MESSAGE-ID')} {traceback.print_exc()}")
                continue

        logger.debug(f"邮件列表查询耗时: {len(results)} emails in {time.time() - start_time:.2f}s")
        return results, total
    except Exception as e:
        raise


def _clean_address_field(field: str) -> str:
    """
    提取邮件地址中的纯邮箱部分
    输入: "张三 <zhangshan@example.com>", "LiSi <lisi@company.com>"
    输出: "zhangshan@example.com", "lisi@company.com"
    """
    if not field:
        return ""

    # 快速判断：如果没有 <，直接返回原内容（最常见情况）
    if '<' not in field:
        return field.strip()

    # 使用预编译的正则提取
    matches = _EMAIL_IN_BRACKETS.findall(field)
    if matches:
        return ', '.join(matches)

    # 如果没匹配到（极少见），尝试宽松正则
    matches = _EMAIL_IN_BRACKETS_LOOSE.findall(field)
    if matches:
        # 过滤掉明显不是邮箱的（比如 <12345> 这种）
        emails = [m for m in matches if '@' in m]
        if emails:
            return ', '.join(emails)

    # 最后兜底：返回原始内容（防止数据丢失）
    return field.strip()


def _fast_decode_header(value: str) -> str:
    """比 decode_header 快 10 倍的简版"""
    if not value:
        return ""
    decoded, charset = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(charset or 'utf-8', errors='replace')
    return decoded


"""查询邮件详情"""


def read_mail_detail(user_account: str, message_id, mailbox: str):
    start_time = time.time()
    ret, mail = get_imap_connection(user_account, mailbox)
    if not ret:
        raise Exception("连接邮箱服务器失败，请稍后重试")
    ret, err = __read_mail_by_mail_id(mail, message_id, True)
    if not ret:
        raise Exception(err)
    logger.debug(f"查询邮件详情耗时: {time.time() - start_time}")
    return ret


"""根据邮件id读取邮件详情"""


def __read_mail_by_mail_id(mail, message_id, query_body: bool):
    # 1️⃣ 包装 Message-ID，确保包含尖括号
    if not message_id.startswith("<"):
        message_id = f"<{message_id}>"

    # 2️⃣ 使用 HEADER 搜索
    status, data = mail.search(None, f'HEADER Message-ID "{message_id}"')
    if status != "OK" or not data or not data[0]:
        return None, "当前查询邮件不存在"

    # 可能有多个（理论上），取第一个
    email_id = data[0].split()[0]
    # fetch_parts = "(RFC822 FLAGS)"  # '(FLAGS BODY.PEEK[])'
    fetch_parts = '(FLAGS BODY.PEEK[])'  # '(FLAGS BODY.PEEK[])'
    if not query_body:
        fetch_parts = "(FLAGS BODY.PEEK[HEADER.FIELDS (Message-ID Subject From To CC Date)])"
    result, message_data = mail.fetch(email_id, fetch_parts)
    if result != "OK":
        return None, f"Failed to read email {email_id} {message_id}"

    try:
        raw_message = message_data[0][1] if query_body else message_data[0][0]  # RFC822 是完整邮件
        msg = email.message_from_bytes(raw_message)

        # Extract basic headers
        subject, encoding = decode_header(msg.get("Subject", ""))[0]
        subject = subject.decode(encoding) if encoding else subject

        # Process flags
        flags = message_data[0][0].decode("utf-8").split("FLAGS (")[1].split(")")[0]
        flags = flags.split(' ')
        is_unread = "\\Seen" not in flags

        if flags:
            flag_list = []
            redis_client = redis.Redis(connection_pool=pool)
            for item in flags:
                if redis_client.exists(f"mail_flag:{item}"):
                    flag = json.loads(redis_client.get(f"mail_flag:{item}"))
                    flag_list.append({"custome_name": flag.get('custome_name'),
                                      "custome_code": flag.get('custome_code'), "status": flag.get('status')})
            flags = flag_list

        # 标记邮件已读
        if is_unread and query_body:
            mail.store(email_id, '+FLAGS', '\\Seen')

        # Process attachments and embedded content
        attachments, cid_map, names = [], {}, []
        if msg.get('X-Attachments'):
            try:
                x_attachments = msg.get('X-Attachments', '[]') or '[]'
                x_attachments = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', x_attachments)  # 移除所有控制字符
                attachments = json.loads(x_attachments) or []
                for att in attachments:
                    original_str = f"{att['file_name']}#{att['file_path']}#{msg.get('Date')}"
                    att['url'] = compress_string(original_str)
            except json.JSONDecodeError:
                pass
        # Process names (custom header)
        if msg.get('X-Names'):
            try:
                names = json.loads(msg.get('X-Names'))
            except json.JSONDecodeError:
                names = {}

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

                if file_data is None:
                    logger.debug("跳过无内容的 inline part")
                    continue

                if not isinstance(file_data, (bytes, bytearray)):
                    logger.debug(f"跳过非二进制内容 inline part: {type(file_data)}")
                    continue

                content_hash = hashlib.sha256(file_data).hexdigest()[:16]  # 生成内容哈希
                content_type = part.get_content_type()

                # 获取原始文件名
                raw_filename = decode_filename(part.get_filename()) or f"inline_{content_hash}"
                # 替换危险字符 截断至 255 字符（文件系统限制）
                clean = re.sub(r'[\\/*?:"<>|]', "_", raw_filename)
                safe_filename = clean[:255]

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
                    logger.error(f"文件保存失败: {str(e)}")

                # 添加到附件列表
                download_path = f"http://192.168.124.9:8080/gyl/workstation/mail/download/{final_name}" \
                    if global_config.run_in_local \
                    else f"http://192.168.3.12:6080/gyl/workstation/mail/download/{final_name}"
                if is_inline:
                    attachments.append({"file_name": safe_filename, "file_path": download_path, "url": download_path})

                if content_id:
                    cid_map[content_id] = download_path

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
        cur_mail = {
            "id": email_id.decode("utf-8"), "message_id": msg.get("Message-ID"),
            "Unread": is_unread, "Subject": subject, "From": msg.get("From"),
            "To": msg.get("To"), "CC": msg.get("CC"), "Bcc": msg.get("Bcc"),
            "flags": flags, "ReplyToList": msg.get("Reply-To"),
            "Date": convert_date_format(msg.get("Date")),
            "attachments": attachments, "names": names, "body": body
        }
        cur_mail['From_name'] = get_emp_name_group_name(cur_mail['From'])
        cur_mail['To_name'] = get_emp_name_group_name(cur_mail['To'])
        cur_mail['CC_name'] = get_emp_name_group_name(cur_mail['CC'])
        cur_mail['Bcc_name'] = get_emp_name_group_name(cur_mail['Bcc'])
        cur_mail['is_group_mail'] = True if cur_mail.get('To', '').__contains__('maillist') else False
        return cur_mail, None

    except Exception as e:
        return None, f"Error processing email: {str(e)}"


"""删除邮件"""


def delete_mail(user_account: str, message_ids, mailbox: str):
    ret, mail = get_imap_connection(user_account, mailbox)
    if not ret:
        raise Exception("连接邮件服务器失败，请稍后重试")

    try:
        # 选择邮箱并使用 UID 模式
        mail.select(mailbox)

        deleted_count = 0

        for msg_id in message_ids:
            # 清理一下 Message-ID（去掉多余空格）
            msg_id_clean = msg_id.strip()
            if not msg_id_clean.startswith('<'):
                msg_id_clean = f"<{msg_id_clean}>"

            # 使用 HEADER 搜索 Message-ID（IMAP 标准字段）
            search_query = f'HEADER Message-ID "{msg_id_clean}"'
            status, data = mail.uid('search', None, search_query)

            if status != 'OK':
                logger.debug(f"搜索 Message-ID 失败: {msg_id_clean}")
                continue

            uid_list = data[0].split()
            if not uid_list:
                logger.debug(f"未找到邮件: {msg_id_clean}")
                continue

            # 可能有重复 Message-ID 的情况（极少），全部删除
            for uid in uid_list:
                # 标记为 \Deleted
                mail.uid('store', uid, '+FLAGS', '(\\Deleted)')
                deleted_count += 1

        # 彻底删除所有标记为 \Deleted 的邮件
        mail.expunge()
    except Exception as e:
        raise


def fetch_attachment(user_account: str, mail_id: int, mailbox: str, file_name: str):
    ret, mail = get_imap_connection(user_account, mailbox)

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

    return None


"""解码邮件附件文件名"""

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


"""邮件添加标记"""


def mark_email_flags(user_account: str, message_ids: List[str],
    mailbox: str, add_flag: bool = True, flags: List[str] = None) -> bool:
    if not flags:
        raise Exception("没有指定要操作的标签")

    ret, mail = get_imap_connection(user_account, mailbox)
    if not ret or not mail:
        raise Exception("连接邮箱服务器失败，请稍后重试")

    try:
        # 必须先 select 邮箱
        status, _ = mail.select(f'"{mailbox}"')
        if status != 'OK':
            raise Exception(f"无法选择邮箱文件夹: {mailbox}")

        action = '+FLAGS' if add_flag else '-FLAGS'
        success_count = 0
        for msg_id in message_ids:
            # 标准化 Message-ID 格式
            if not msg_id.startswith("<"):
                msg_id = f"<{msg_id}>"

            # 关键：使用 UID 搜索！
            search_cmd = f'HEADER Message-ID "{msg_id}"'
            status, data = mail.uid('SEARCH', None, search_cmd)

            if status != 'OK' or not data[0]:
                logger.warning(f"未找到邮件 Message-ID={msg_id}")
                continue

            uid_list = data[0].split()
            if not uid_list:
                logger.warning(f"Message-ID={msg_id} 搜索无结果")
                continue

            for uid in uid_list:
                uid = uid.decode('utf-8') if isinstance(uid, bytes) else uid

                # 正确方式：对每个 flag 分别 store
                for flag in flags:
                    # 自定义关键字不需要反斜杠，标准旗标需要
                    if flag.startswith('\\'):
                        flag_arg = flag  # 如 \\Seen
                    else:
                        flag_arg = flag   # 如 "MyTag" 或 "$Important"

                    status, resp = mail.uid('STORE', uid, action, flag_arg)

                    if status == 'OK':
                        logger.debug(f"{'添加' if add_flag else '移除'}标签成功 → UID={uid} "
                                    f"Message-ID={msg_id} Flag={flag}")
                        success_count += 1
                    else:
                        logger.error(f"操作标签失败 → UID={uid} Flag={flag} Response={resp}")

        logger.debug(f"本次共处理 {len(message_ids)} 封邮件，成功操作 {success_count} 次标签")
        return success_count > 0

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP 协议错误: {e}")
        return False
    except Exception as e:
        logger.exception(f"标记邮件标签时发生未知错误: {e}")
        return False


"""将邮件移动至指定目录"""

def move_email_to_folder(user_account: str, message_ids, mailbox, target_folder):
    ret, mail = get_imap_connection(user_account, mailbox)
    if not ret:
        raise Exception("连接邮箱服务器失败，请稍后重试")

    success = []
    failed = []
    try:
        # 关键修复点 2：必须先 SELECT 当前邮箱！！
        select_status, _ = mail.select(mailbox)
        if select_status != "OK":
            raise Exception(f"Failed to select mailbox: {mailbox})")

        if global_config.run_in_local:
            print("当前邮箱所有目录: ")
            status, existing_folders = mail.list()
            if status == "OK":
                for item in existing_folders:
                    print(item)

        # 1. 确保目标文件夹存在, 创建文件夹（如果不存在），支持嵌套文件夹如 "Archive/2025"
        try:
            status, _ = mail.create(target_folder)
        except Exception as e:
            print(f"Create folder {target_folder} error: {e}")
            # 已经存在会报错，属于正常情况，直接忽略
            if "exists" not in str(e).lower():
                logger.warning(f"Create folder {target_folder} warning: {e}")
                raise

        for msg_id in message_ids:
            msg_id = msg_id.strip()
            if not msg_id.startswith("<"):
                msg_id = f"<{msg_id}>"

            try:
                # 关键：用 HEADER Message-ID 搜索（极快，且不受 UID 变化影响）
                status, data = mail.search(None, f'HEADER Message-ID "{msg_id}"')
                if status != "OK" or not data[0]:
                    failed.append({"message_id": msg_id, "error": "Not found in current mailbox"})
                    continue

                uid_list = data[0].split()
                if not uid_list:
                    failed.append({"message_id": msg_id, "error": "Empty search result"})
                    continue

                # 理论上 Message-ID 是唯一的，取第一个
                uid = uid_list[0]

                # 执行 copy + delete（IMAP 标准移动方式）
                copy_status, _ = mail.uid('COPY', uid, target_folder)
                if copy_status != "OK":
                    failed.append({"message_id": msg_id, "error": f"Copy failed: {copy_status}"})
                    continue

                # 标记为已删除
                mail.uid('STORE', uid, '+FLAGS', '\\Deleted')
                success.append(msg_id)
            except Exception as e:
                logger.error(f"Move {msg_id} failed: {e}")
                failed.append({"message_id": msg_id, "error": str(e)})

        mail.expunge()  # 永久删除原邮件（完成移动）
    except Exception as e:
        logger.error(f"移动失败: {e}")
        raise

    return {"success": success, "failed": failed}


# ===========================================================
# =============   mail group manager    =====================
# ===========================================================

"""
创建邮箱分组
"""


def create_mail_group(json_data):
    start_time = time.time()
    user_account = json_data.get("user_account")
    user_name = json_data.get("user_name")
    mail_group_name = json_data.get("mail_group_name")
    mail_group_description = json_data.get("mail_group_description")
    user_list = json_data.get("user_list")
    is_public = json_data.get("is_public")
    if not all([user_account, user_name, mail_group_name]):
        raise ValueError("缺少必要参数")

    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=60 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(f"mail:create:{user_account}", 1, ex=60, nx=True):
        raise Exception('创建失败：请勿频繁创建群组，请于1分钟后再次尝试')

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL)
    ssh = SshUtil(mail_config.MAIL_SSH_HOST, mail_config.MAIL_SSH_USERNAME, mail_config.MAIL_SSH_PASSWORD)
    try:
        # 随机生成群组账号
        mail_group_account = generate_random_string(5)
        # 查询是否存在重复的id
        query_sql = f"select id from nsyy_gyl.ws_mail_group where account = '{mail_group_account}' "
        if db.query_one(query_sql):
            # 随机生成的群账号重复，重新生成
            raise Exception(f"系统繁忙，请稍后再试")

        # 调用邮箱服务器群组管理脚本，创建新群组
        group_name = mail_group_account + mail_config.MAIL_DOMAIN
        group_name = group_name.lower()

        # 检查群组列表是否存在
        output = ssh.execute_shell_command(f"echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                           f"'cd /opt/mlmmjadmin/tools; python3 maillist_admin.py info {group_name}' ")
        if 'Error: NO_SUCH_ACCOUNT' not in output:
            raise Exception(f"系统繁忙，请稍后再试")

        # 创建群组
        output = ssh.execute_shell_command(f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c "
                                           f"'cd /opt/mlmmjadmin/tools; python3 maillist_admin.py create {group_name}"
                                           f" only_subscriber_can_post={'yes' if int(is_public) == 0 else 'no'} "
                                           f"disable_archive=no disable_send_copy_to_sender=yes '")
        if 'Created.' not in output:
            raise Exception("邮箱群组群组" + mail_group_name + " 创建失败")

        timer = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        args = (mail_group_name, mail_group_account, mail_group_description, user_account, user_name, timer, is_public)
        insert_sql = "INSERT INTO nsyy_gyl.ws_mail_group (name, account, description, " \
                     "user_account, user_name, timer, is_public) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        last_rowid = db.execute(insert_sql, args, need_commit=True)
        if last_rowid == -1:
            raise Exception("新群组入库失败!")

        # 2. 组装用户邮箱账号 [用户账号]@邮箱后缀， 将用户邮箱加入到新群组中
        batch_insert_list, failed_user_list, user_dict = [], [], {}
        # 将创建者本人也加入
        user_list.append({"user_account": user_account, "user_name": user_name})
        for user in user_list:
            account = user.get('user_account')
            mail_account = account + mail_config.MAIL_DOMAIN
            mail_account = mail_account.lower()
            # 账号存在将账号加入到
            command = (f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c 'cd /opt/mlmmjadmin/tools; "
                       f"python3 maillist_admin.py add_subscribers {group_name} {mail_account} ' ")
            output = ssh.execute_shell_command(command)
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
                allow_edit = 1 if user.get('user_account') == user_account else 0
                args.append((last_rowid, user.get('user_account'), user.get('user_name'), timer, allow_edit))
            insert_sql = """INSERT INTO nsyy_gyl.ws_mail_group_members(mail_group_id, user_account, user_name,
                                                                       timer, allow_edit) \
                            VALUES (%s, %s, %s, %s, %s) \
                            ON DUPLICATE KEY UPDATE timer      = VALUES(timer), \
                                                    user_name  = VALUES(user_name), \
                                                    allow_edit = VALUES(allow_edit)"""
            db.execute_many(insert_sql, args, need_commit=True)

        logger.debug(f"群组创建成功，耗时 {time.time() - start_time}")
        return failed_user_list
    except Exception as e:
        logger.error(f"创建邮件群组失败: {e}", exc_info=True)
        raise
    finally:
        # 自动释放资源
        del db
        del ssh


"""
编辑群组
operate_type = 0 更新群组描述
operate_type = 1 向群组中新增用户
operate_type = 2 从群组中移除用户
operate_type = 3 修改群组公开性
operate_type = 4 删除群组 
"""


def operate_mail_group(json_data):
    # TODO 找时间优化
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
            command = f" echo {mail_config.MAIL_SSH_PASSWORD} | sudo -S bash -c 'cd /opt/mlmmjadmin/tools; python3 maillist_admin.py add_subscribers {mail_group} {mail_account} ' "
            output = ssh.execute_shell_command(command)
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
        if mail_group_record.get('user_account').lower() != user_account.lower():
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
        # 只有创建者本人可以修改群组公开性
        if mail_group.get('user_account').lower() != user_account.lower():
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
    sql = f"""SELECT g.*,
            m.id              AS member_id,
            m.user_account    AS member_user_account,
            m.user_name       AS member_user_name,
            m.allow_edit      AS member_allow_edit,
            m.timer           AS member_timer,
            m.is_show         AS member_is_show
        FROM nsyy_gyl.ws_mail_group g LEFT JOIN nsyy_gyl.ws_mail_group_members m ON g.id = m.mail_group_id
        WHERE g.is_public = 1 OR EXISTS (
            SELECT 1  FROM nsyy_gyl.ws_mail_group_members m2 WHERE m2.mail_group_id = g.id 
            AND m2.user_account = '{user_account}' AND m2.is_show = 1) ORDER BY g.id, m.id"""

    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    rows = db.query_all(sql)
    del db

    groups = {}
    for row in rows:
        gid = row['id']
        if gid not in groups:
            # 第一次见到这个组，构建组信息（去掉 member_ 开头的字段）
            group = {k: v for k, v in row.items() if not k.startswith('member_')}
            group['members'] = []
            groups[gid] = group

        # 如果有成员信息（LEFT JOIN 可能为 NULL）
        if row['member_id'] is not None:
            groups[gid]['members'].append({
                'id': row['member_id'],
                'user_account': row['member_user_account'],
                'user_name': row['member_user_name'],
                'is_show': row['member_is_show'],
                'allow_edit': row['member_allow_edit'],
                'timer': row['member_timer'],
                # 其他成员字段也加在这里
            })

    return list(groups.values())


"""生成指定长度的字符串 群组邮箱编号 固定以 maillist_ 为前缀  """


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


"""管理自定义标签和文件夹"""


def manager_custom_flags(json_data):
    pers_id, pers_name, pers_account = json_data.get('pers_id'), \
        json_data.get('pers_name'), json_data.get('pers_account')
    mail_custome_list = []
    redis_client = redis.Redis(connection_pool=pool)
    if json_data.get('flags'):
        for item in json_data.get('flags'):
            code = item.get('code') if item.get('code') else f"&{generate_secure_random_string()}"
            redis_client.set(f"mail_flag:{code}", json.dumps({"custome_name": item.get('name'),
                                                                                  "custome_code": code, "status": 1}))
            mail_custome_list.append((pers_id, pers_name, pers_account, 1, item.get('name'), code, item.get('status')))

    if json_data.get('folders'):
        for item in json_data.get('folders'):
            mail_custome_list.append((pers_id, pers_name, pers_account, 2, item.get('name'),
                                      item.get('code') if item.get('code') else generate_random_folder_name(),
                                      item.get('status')))
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    db.execute_many("""
        INSERT INTO nsyy_gyl.ws_mail_custome(pers_id, pers_name, pers_account, custome_type, 
        custome_name, custome_code, status) VALUES (%s, %s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE pers_id = VALUES(pers_id), pers_name = VALUES(pers_name), 
        pers_account = VALUES(pers_account), custome_type = VALUES(custome_type), 
        custome_name = VALUES(custome_name), custome_code = VALUES(custome_code), status = VALUES(status) 
    """, args=mail_custome_list, need_commit=True)
    del db


"""使用更安全的secrets模块生成随机字符串"""


def generate_secure_random_string():
    import secrets
    first_char = secrets.choice(string.ascii_uppercase)
    rest_chars = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(7))
    return first_char + rest_chars


"""生成一个绝对唯一的纯英文随机文件夹名"""


def generate_random_folder_name(prefix: str = "Folder") -> str:
    """
    规则：{prefix}_{时间戳}{4位随机字母}
    示例：
        Folder_20251127153028_ABCD
        Archive_20251127153029_XY9K
        Temp_20251127153030_P2mN
    """
    # 时间戳到秒（同一秒内也能区分）
    timestamp = int(time.time() * 1000)  # 毫秒级更保险

    # 4位随机大写字母（只用字母，清晰易读）
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    return f"{prefix}_{timestamp}_{letters}"


"""查询用户自定义标签"""


def query_mail_custome(pers_account):
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    query_sql = f"select custome_type, custome_name, custome_code, status " \
                f"from nsyy_gyl.ws_mail_custome where pers_account = '{pers_account}' "
    mail_custome_list = db.query_all(query_sql)
    del db

    flags_list, folder_list = mail_config.default_flags.copy(), mail_config.default_folders.copy()
    for item in mail_custome_list:
        if item.get('custome_type') == 1:
            flags_list.append({'name': item.get('custome_name'), "code": item.get('custome_code'),
                               "type": item.get('custome_type'), "status": item.get('status'), "is_custome": 1})
        elif item.get('custome_type') == 2:
            folder_list.append({'name': item.get('custome_name'), "code": item.get('custome_code'),
                               "type": item.get('custome_type'), "status": item.get('status'), "is_custome": 1})

    return flags_list, folder_list


"""根据邮箱账号获取对应的员工姓名"""


def get_emp_name_group_name(accouts: str):
    if not accouts:
        return ''
    account_list = accouts.split(',')
    ret = []
    redis_client = redis.Redis(connection_pool=pool)
    for item in account_list:
        item = item.strip()
        # item = item.replace('@nsyy.com', '').replace('@NSYY.COM', '')
        emp_name = redis_client.get(f"mail_group:{item}")
        if emp_name:
            ret.append(emp_name)
        else:
            emp_name = redis_client.get(f"mail_emp:{item.lower()}")
            if emp_name:
                ret.append(emp_name)
            else:
                ret.append(item)
    return ','.join(ret)


def cache_flags():
    redis_client = redis.Redis(connection_pool=pool)
    # 尝试设置键，只有当键不存在时才设置成功.  ex=60 表示过期时间 60 秒（1 分钟），nx=True 表示不存在时才设置
    if not redis_client.set(f"cache_mail_flags", 1, ex=3*60*60, nx=True):
        return

    start_time = time.time()
    db = DbUtil('192.168.3.12', 'root', '123123', "oa_test")
    flags = db.query_all(f"select * from nsyy_gyl.ws_mail_custome ")
    mail_groups = db.query_all(f"select account, name from nsyy_gyl.ws_mail_group")
    sql = """select a.pers_id, a.pers_name, a.emp_nub, b.dept_id, c.dept_name, b.dept_source, a.email 
        from oa_test.hr_pers_main a left join oa_test.hr_pers_dept b on a.pers_id = b.pers_id 
        left join oa_test.hr_dept c on b.dept_id = c.dept_id where a.email is not null"""
    emp_list = db.query_all(sql)
    del db
    if global_config.run_in_local:
        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        flags = db.query_all(f"select * from nsyy_gyl.ws_mail_custome ")
        mail_groups = db.query_all(f"select account, name from nsyy_gyl.ws_mail_group")
        del db

    if flags:
        redis_client.delete(f"mail_flag")
    if mail_groups:
        redis_client.delete(f"mail_group")
    if emp_list:
        redis_client.delete(f"mail_emp")
        redis_client.delete(f"mail_emp_pers_id")

    for item in flags:
        redis_client.set(f"mail_flag:{item.get('custome_code')}", json.dumps(item))
    for item in mail_groups:
        redis_client.set(f"mail_group:{item.get('account')}", item.get('name'))
    for item in emp_list:
        if not item.get('email', ''):
            continue
        redis_client.set(f"mail_emp:{item.get('email').lower()}",
                         f"{item.get('pers_name')}({item.get('dept_name')})")
        redis_client.set(f"mail_emp_pers_id:{item.get('email').lower()}", item.get('pers_id'))
    logger.info(f"缓存邮件标签/群组/成员信息成功，耗时：{time.time() - start_time}秒")


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

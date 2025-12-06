import os
import re

from flask import Blueprint, jsonify, request, send_file
from io import BytesIO

from gylmodules import global_config
from gylmodules.global_tools import api_response
from gylmodules.workstation.mail import mail_config
from gylmodules.workstation.mail import mail_server as mail

mail_router = Blueprint('mail router', __name__, url_prefix='/mail')


# ===========================================================
# =============  mail         manager   =====================
# ===========================================================


@mail_router.route('/send_mail', methods=['POST'])
@api_response
def send_email(json_data):
    mail.send_email_robust(json_data)


@mail_router.route('/query_mail_list', methods=['POST', 'GET'])
@api_response
def query_mail_list(json_data):
    user_account = json_data.get("user_account")
    page_size = json_data.get("page_size")
    page_number = json_data.get("page_number")
    mailbox = json_data.get('mailbox')
    mail_list, total_emails = mail.read_mail_list(user_account, page_size, page_number, mailbox)
    return {'list': mail_list, 'total': total_emails}


@mail_router.route('/query_mail_list_by_keyword', methods=['POST'])
@api_response
def query_mail_list_by_keyword(json_data):
    user_account = json_data.get("user_account")
    page_size = json_data.get("page_size")
    page_number = json_data.get("page_number")
    mailbox = json_data.get('mailbox')
    keyword = json_data.get('keyword')
    mail_list, total_emails = mail.read_mail_list(user_account, page_size, page_number, mailbox, keyword)
    return {'list': mail_list, 'total': total_emails}


@mail_router.route('/query_mail', methods=['POST'])
@api_response
def query_mail(json_data):
    user_account = json_data.get("user_account")
    mailbox = json_data.get('mailbox')
    message_id = json_data.get('message_id')

    email = mail.read_mail_detail(user_account, message_id, mailbox)
    if global_config.run_in_local and email and email.get('attachments'):
        origin = request.headers.get('Origin')
        if origin:
            try:
                from urllib.parse import urlparse
                host = urlparse(origin).hostname
                if host:
                    for attachment in email.get('attachments'):
                        if attachment.get('file_path'):
                            old_host = urlparse(attachment.get('file_path')).hostname
                            if old_host != host:
                                attachment['file_path'] = attachment['file_path'].replace(old_host, host)
            except:
                pass
    if email:
        if email.get('To') and email.get('To').__contains__('<'):
            email['To'] = ', '.join(re.findall(r'<([^>]+)>', email.get('To')))
        if email.get('From') and email.get('From').__contains__('<'):
            email['From'] = ', '.join(re.findall(r'<([^>]+)>', email.get('From')))
        if email.get('CC') and email.get('CC').__contains__('<'):
            email['CC'] = ', '.join(re.findall(r'<([^>]+)>', email.get('CC')))
        if email.get('Bcc') and email.get('Bcc').__contains__('<'):
            email['Bcc'] = ', '.join(re.findall(r'<([^>]+)>', email.get('Bcc')))
    return email


@mail_router.route('/delete_mail', methods=['POST'])
@api_response
def delete_mail(json_data):
    user_account = json_data.get("user_account")
    message_ids = json_data.get("message_ids")
    mailbox = json_data.get('mailbox')
    mail.delete_mail(user_account, message_ids, mailbox)


# ===========================================================
# =============   mail group manager    =====================
# ===========================================================


#  创建邮箱分组
@mail_router.route('/create_mail_group', methods=['POST'])
@api_response
def create_mail_group(json_data):
    failed_user_list = mail.create_mail_group(json_data)
    if len(failed_user_list) != 0:
        return '邮箱群组创建成功，但成员 ' + ' '.join(failed_user_list) + ' 加入群组失败，请检查以上用户是否拥有邮箱账户'
    return '邮箱群组创建成功'


#  编辑邮箱分组
@mail_router.route('/operate_mail_group', methods=['POST'])
@api_response
def operate_mail_group(json_data):
    operate_type = json_data.get("operate_type")
    mail_group_name = json_data.get("mail_group_name")

    failed_user_list = mail.operate_mail_group(json_data)
    if failed_user_list and len(failed_user_list) != 0:
        if operate_type == mail_config.MAIL_OPERATE_ADD:
            info = ' '.join(failed_user_list) + ': 以上用户订阅邮箱群组 ' + mail_group_name + ' 失败, 请联系管理员处理'
        elif operate_type == mail_config.MAIL_OPERATE_REMOVE:
            info = ' '.join(failed_user_list) + ': 以上用户取消订阅邮箱群组 ' + mail_group_name + ' 失败, 请联系管理员处理'
        else:
            info = ''
        return info
    return '邮箱群组操作成功'


@mail_router.route('/query_mail_group_list', methods=['POST'])
@api_response
def query_mail_group_list(json_data):
    user_account = json_data.get("user_account")
    return mail.query_mail_group_list(user_account)


@mail_router.route('/manager_custom_flags', methods=['POST'])
@api_response
def manager_custom_flags(json_data):
    mail.manager_custom_flags(json_data)


@mail_router.route('/query_mail_custome', methods=['POST'])
@api_response
def query_mail_custome(json_data):
    flags_list, folder_list = mail.query_mail_custome(json_data.get('pers_account'))
    return {"flags": flags_list, "folders": folder_list}


@mail_router.route('/mark_email_flags', methods=['POST'])
@api_response
def mark_email_flags(json_data):
    mail.mark_email_flags(json_data.get('user_account'), json_data.get('message_id'), json_data.get('mailbox'),
                          json_data.get('add_flag'), json_data.get('flag_code'))


@mail_router.route('/move_email_to_folder', methods=['POST'])
@api_response
def move_email_to_folder(json_data):
    mail.move_email_to_folder(json_data.get('user_account'), json_data.get('message_ids'), json_data.get('mailbox'),
                              json_data.get('target_folder'))


@mail_router.route('/mail_cache', methods=['POST'])
@api_response
def mail_cache():
    mail.cache_flags()



# ===========================================================
# =============  内部使用 mail account manager   =====================
# ===========================================================


@mail_router.route('/create_mail_account', methods=['POST'])
@api_response
def create_mail_account(json_data):
    user_list = json_data.get("user_list")
    mail.create_mail_account(user_list)


# todo 删除邮箱账户，这里只删除群组依赖，邮箱账户需要到 iRedMail 管理后台手动删除
@mail_router.route('/delete_mail_account', methods=['POST'])
@api_response
def delete_mail_account(json_data):
    user_account = json_data.get("user_account")
    mail.delete_mail_account(user_account)


@mail_router.route('/reset_user_password', methods=['POST'])
@api_response
def reset_user_password(json_data):
    user_account = json_data.get("user_account")
    old_password = json_data.get("old_password")
    new_password = json_data.get("new_password")
    is_default = json_data.get("is_default")
    mail.reset_user_password(user_account, old_password, new_password, is_default)


@mail_router.route('/download_attachment/<url>', methods=['POST'])
def download_attachment(url):
    return jsonify({
        'code': 20000,
        'res': url,
        'data': '下载成功'
    })


@mail_router.route('/download_attachment_test/<user_account>/<mailbox>/<mail_id>/<file_name>', methods=['GET'])
def download_attachment_test(user_account, mailbox, mail_id, file_name):
    attachment = mail.fetch_attachment(user_account, int(mail_id), mailbox, file_name)
    if attachment is not None:
        data_stream = BytesIO(attachment)
        return send_file(data_stream, as_attachment=True, download_name=file_name)

    return "Attachment not found", 404


@mail_router.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        save_dir = mail_config.inline_attachments_dir_dev if global_config.run_in_local else mail_config.inline_attachments_dir_prod
        save_path = os.path.join(save_dir, filename)

        # 检查文件是否已存在
        if not os.path.exists(save_path):
            return jsonify({
                'code': 50000,
                'res': f'文件不存在 {filename}',
                'data': f'文件不存在 {filename}'
            })

        # 4. 获取文件大小（用于日志或限速）
        file_size = os.path.getsize(save_path)

        # 5. 分块发送大文件（支持断点续传）
        return send_file(
            save_path,
            as_attachment=True,
            download_name=filename,  # 指定下载显示的文件名
            conditional=True,        # 支持 Range 请求
            etag=True,               # 启用 ETag 缓存
            max_age=3600             # 客户端缓存时间
        )

    except Exception as e:
        return jsonify({
                'code': 50000,
                'res': f'文件不存在 {filename}',
                'data': f'文件下载失败 {str(e)}'
            })

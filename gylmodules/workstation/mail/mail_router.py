import traceback

from flask import Blueprint, jsonify, request, send_file

from io import BytesIO
from gylmodules.workstation import ws_config
from gylmodules.workstation.mail import mail
import json

mail_router = Blueprint('mail router', __name__, url_prefix='/mail')


# ===========================================================
# =============  mail         manager   =====================
# ===========================================================


@mail_router.route('/send_mail', methods=['POST'])
def send_email():
    json_data = json.loads(request.get_data().decode('utf-8'))
    sender = json_data.get("sender")
    recipients = json_data.get("recipients")
    ccs = json_data.get("ccs")
    bccs = json_data.get("bccs")
    subject = json_data.get("subject")
    body = json_data.get("body")
    attachments = json_data.get("attachments")
    names = json_data.get("names")

    try:
        mail.send_email(sender, recipients, ccs, bccs, subject, body, attachments, names)
    except Exception as e:
        print(f"mail_router.send_email: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮件发送失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮件发送成功',
        'data': '邮件发送成功'
    })


@mail_router.route('/query_mail_list', methods=['POST'])
def query_mail_list():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    page_size = json_data.get("page_size")
    page_number = json_data.get("page_number")
    mailbox = json_data.get('mailbox')

    try:
        mail_list = mail.read_mail_list(user_account, page_size, page_number, mailbox)
    except Exception as e:
        print(f"mail_router.query_mail_list: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮件列表查询失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮件列表查询成功',
        'data': mail_list
    })


@mail_router.route('/query_mail_list_by_keyword', methods=['POST'])
def query_mail_list_by_keyword():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    page_size = json_data.get("page_size")
    page_number = json_data.get("page_number")
    mailbox = json_data.get('mailbox')
    keyword = json_data.get('keyword')

    try:
        mail_list = mail.read_mail_list_by_keyword(user_account, page_size, page_number, mailbox, keyword)
    except Exception as e:
        print(f"mail_router.query_mail_list: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮件列表查询失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮件列表查询成功',
        'data': mail_list
    })


@mail_router.route('/query_mail', methods=['POST'])
def query_mail():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    mail_id = json_data.get("mail_id")
    mailbox = json_data.get('mailbox')

    try:
        email = mail.read_mail(user_account, mail_id, mailbox)
    except Exception as e:
        print(f"mail_router.query_mail: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮件查询失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮件查询成功',
        'data': email
    })


@mail_router.route('/delete_mail', methods=['POST'])
def delete_mail():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    mail_ids = json_data.get("mail_ids")
    mailbox = json_data.get('mailbox')

    try:
        mail.delete_mail(user_account, mail_ids, mailbox)
    except Exception as e:
        print(f"mail_router.delete_mail: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮件删除失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮件删除成功',
        'data': ''
    })


@mail_router.route('/download_attachment/<url>', methods=['POST'])
def download_attachment(url):
    return jsonify({
        'code': 20000,
        'res': url,
        'data': '下载成功'
    })


# @mail_router.route('/download_attachment', methods=['POST'])
# def download_attachment():
#     json_data = json.loads(request.get_data().decode('utf-8'))
#     user_account = json_data.get("user_account")
#     mail_id = json_data.get("mail_id")
#     mailbox = json_data.get('mailbox')
#     file_name = json_data.get("file_name")
#
#     attachment = mail.fetch_attachment(user_account, int(mail_id), mailbox, file_name)
#     if attachment is not None:
#         data_stream = BytesIO(attachment)
#         return send_file(data_stream, as_attachment=True, download_name=file_name)
#
#     return "Attachment not found", 404


@mail_router.route('/download_attachment_test/<user_account>/<mailbox>/<mail_id>/<file_name>', methods=['GET'])
def download_attachment_test(user_account, mailbox, mail_id, file_name):
    attachment = mail.fetch_attachment(user_account, int(mail_id), mailbox, file_name)
    if attachment is not None:
        data_stream = BytesIO(attachment)
        return send_file(data_stream, as_attachment=True, download_name=file_name)

    return "Attachment not found", 404


# ===========================================================
# =============  mail account manager   =====================
# ===========================================================


@mail_router.route('/create_mail_account', methods=['POST'])
def create_mail_account():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_list = json_data.get("user_list")

    try:
        mail.create_mail_account(user_list)
    except Exception as e:
        print(f"mail_router.create_mail_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮箱账户创建失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮箱账户创建成功',
        'data': '邮箱账户创建成功'
    })


# 删除邮箱账户，这里只删除群组依赖，邮箱账户需要到 iRedMail 管理后台手动删除
@mail_router.route('/delete_mail_account', methods=['POST'])
def delete_mail_account():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    try:
        mail.delete_mail_account(user_account)
    except Exception as e:
        print(f"mail_router.delete_mail_account: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '删除邮箱账户失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '成功删除邮箱账户',
        'data': '成功删除邮箱账户'
    })


# ===========================================================
# =============   mail group manager    =====================
# ===========================================================


#  创建邮箱分组
@mail_router.route('/create_mail_group', methods=['POST'])
def create_mail_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    user_name = json_data.get("user_name")
    mail_group_name = json_data.get("mail_group_name")
    mail_group_description = json_data.get("mail_group_description")
    user_list = json_data.get("user_list")
    is_public = json_data.get("is_public")

    try:
        failed_user_list = mail.create_mail_group(user_account, user_name,
                                                  mail_group_name, mail_group_description, user_list, is_public)
        if len(failed_user_list) != 0:
            return jsonify({
                'code': 20000,
                'res': '邮箱群组创建成功，但成员 ' + ' '.join(failed_user_list) + ' 加入群组失败，请检查以上用户是否拥有邮箱账户',
                'data': '邮箱群组创建成功，但成员 ' + ' '.join(failed_user_list) + ' 加入群组失败，请检查以上用户是否拥有邮箱账户'
            })
    except Exception as e:
        print(f"mail_router.create_mail_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮箱群组创建失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮箱群组创建成功, 成员加入群组成功',
        'data': '邮箱群组创建成功, 成员加入群组成功'
    })


#  编辑邮箱分组
@mail_router.route('/operate_mail_group', methods=['POST'])
def operate_mail_group():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    mail_group_id = json_data.get("mail_group_id")
    mail_group_name = json_data.get("mail_group_name")
    operate_type = json_data.get("operate_type")
    new_mail_group_desc = json_data.get("new_mail_group_desc")
    user_list = json_data.get("user_list")
    is_public = json_data.get("is_public")

    try:
        failed_user_list = mail.operate_mail_group(user_account, mail_group_id, mail_group_name, operate_type,
                                                   new_mail_group_desc, user_list, is_public)
        if failed_user_list is not None and len(failed_user_list) != 0:
            if operate_type == ws_config.MAIL_OPERATE_ADD:
                info = ' '.join(failed_user_list) + ': 以上用户订阅邮箱群组 ' + mail_group_name + ' 失败, 请联系管理员处理'
                return jsonify({
                    'code': 20000,
                    'res': info,
                    'data': info
                })
            elif operate_type == ws_config.MAIL_OPERATE_REMOVE:
                info = ' '.join(failed_user_list) + ': 以上用户取消订阅邮箱群组 ' + mail_group_name + ' 失败, 请联系管理员处理'
                return jsonify({
                    'code': 20000,
                    'res': info,
                    'data': info
                })
    except Exception as e:
        print(f"mail_router.operate_mail_group: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮箱群组操作失败，请稍后重试' + e.__str__(),
            'data': ''
        })

    return jsonify({
        'code': 20000,
        'res': '邮箱群组操作成功',
        'data': '邮箱群组操作成功'
    })


@mail_router.route('/query_mail_group_list', methods=['POST'])
def query_mail_group_list():
    json_data = json.loads(request.get_data().decode('utf-8'))
    user_account = json_data.get("user_account")
    try:
        mail_group_list = mail.query_mail_group_list(user_account)
    except Exception as e:
        print(f"mail_router.query_mail_group_list: An unexpected error occurred: {e}")
        print(traceback.print_exc())
        return jsonify({
            'code': 50000,
            'res': '邮箱群组列表查询失败，请稍后重试',
            'data': '邮箱群组列表查询失败，请稍后重试'
        })

    return jsonify({
        'code': 20000,
        'res': '邮箱群组列表查询成功',
        'data': mail_group_list
    })


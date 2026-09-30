import os
from ftplib import FTP
from urllib.parse import urlparse

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from gylmodules.global_tools import api_response
from gylmodules import global_config
from gylmodules.pacs_pdf.pacs_server import query_and_save_report
from gylmodules.utils.db_utils_new import DbUtil

# 用于将油田/康复的检查报告生成pdf并上传至指定目录
pacs_system = Blueprint('pacs system', __name__, url_prefix='/pacs')


"""查询未上传pdf的报告"""


@pacs_system.route('/query_report_data', methods=['POST', 'GET'])
@api_response
def query_report_data(json_data):
    type = json_data.get('type', '0')
    if type == '15':
        sql = """select * from nsyy_gyl.medical_reports where 来源 = '油田' and is_upload = 0 ORDER BY RAND() limit 1"""
    elif type == '35':
        sql = """select * from nsyy_gyl.medical_reports where 来源 = '康复' and is_upload = 0 ORDER BY RAND() limit 1"""
    else:
        raise Exception(f"未定义的查询类型 {type}")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        data = db.query_one(sql)

    if data:
        if data.get('pdf路径') and data.get('pdf路径').__contains__('YXY_YT'):
            data['报告医生签名'] = yt_doc_sign_list_name.get(data.get('报告医生', ''), '')
            data['审核医生签名'] = yt_doc_sign_list_name.get(data.get('审核医生', ''), '')
        else:
            data['报告医生签名'] = yt_doc_sign_list_name.get(data.get('报告医生', ''), '')
            data['审核医生签名'] = yt_doc_sign_list_name.get(data.get('审核医生', ''), '')

    return data


"""上传pdf报告"""


@pacs_system.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return {"code": 50000, "data": '', "res": "没有文件"}

    file = request.files["file"]
    advice_id = request.form.get("advice_id")
    if not advice_id:
        return {"code": 50000, "data": '', "res": "没有医嘱id"}

    path = request.form.get("path")
    if not path:
        return {"code": 50000, "data": '', "res": "没有ftp路径"}

    if file.filename == "":
        return {"code": 50000, "data": '', "res": "文件名为空"}

    if file and ("." in file.filename and file.filename.rsplit(".", 1)[1].lower() == "pdf"):
        filename = secure_filename(file.filename)
        local_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(local_path)

        try:
            parsed = urlparse(path)
            filename = os.path.basename(parsed.path)
            upload_pdf_via_ftp(local_path, path, filename)
        except Exception as e:
            return {"code": 50000, "data": '', "res": f"FTP 上传失败: {e}"}
        finally:
            # 删除临时文件
            if os.path.exists(local_path):
                os.remove(local_path)

        with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                    global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
            sql = f"""UPDATE nsyy_gyl.medical_reports SET is_upload = 1 WHERE 医嘱ID = {advice_id}"""
            db.execute(sql, need_commit=True)

        return {"code": 20000, "data": f'PDF文件 {filename} 上传成功', "res": f"PDF文件 {filename} 上传成功"}
    else:
        return {"code": 50000, "data": '', "res": f"只允许上传 PDF 文件"}


"""查询并保存pacs 记录"""
@pacs_system.route('/query_and_save_report', methods=['POST', 'GET'])
def query_save_report():
    query_and_save_report()
    return {"code": 20000, "data": 'success', "res": f"success"}


yt_doc_sign_list_name = {
    "鲁璐": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTE4MjcuYm1w",
    "郑康": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTE4NjQuYm1w",
    "李洁1": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA3MzTvvIjmoLjno4HvvIkuYm1w",
    "李洁": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NzHvvIjmlL7lsITvvIkuYm1w",
    "师小坡": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTI1MjEuYm1w",
    "董亚楠": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTE3MDkuYm1w",
    "裴枫": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NzQuYm1w",
    "朱晓云": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjIuYm1w",
    "马小义": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjMuYm1w",
    "许多": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTE4NjYuYm1w",
    "张展英": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTMyODAuYm1w",
    "刘明": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjUuYm1w",
    "贾维维": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA3MzEuYm1w",
    "张志强": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjguYm1w",
    "李果": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTE1NzYuYm1w",
    "刘飞": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjAuYm1w",
    "杨明贵": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTA1NjEuYm1w",
    "袁庆辉": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTAyMzMuYm1w",
    "王颜辉": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcvVTI1MjIuYm1w",
    "杜凡": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv5p2c5YehLmJtcA==",
    "何洁": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv5L2V5rSBLmJtcA==",
    "王露": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv546L6ZyyLmJtcA==",
    "王明聪": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv546L5piO6IGqLmJtcA==",
    "王羽": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv546L5769LmJtcA==",
    "徐书渊": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv5b6Q5Lmm5riKLmJtcA==",
    "张冉": "http://192.168.3.12:6080/att_download?save_path=L2hvbWUvY2MvYXR0L3B1YmxpYy95dF9kb2Nfc2lnbl9pbWcv5byg5YaJLmJtcA=="
}


# 配置
UPLOAD_FOLDER = "/Users/gaoyanliang/nsyy/nsyy-project/pacs_pdf_temp_uploads" if global_config.run_in_local else '/home/gyl/gyl_server/pacs_pdf_temp_uploads'
# 确保本地临时目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_dir(path: str) -> str:
    from urllib.parse import urlparse
    import os
    # 解析 ftp URL
    parsed = urlparse(path)
    # 拿到路径部分
    full_path = parsed.path
    # 去掉文件名，只保留目录
    return os.path.dirname(full_path) + "/"


def upload_pdf_via_ftp(local_pdf, remote_path, remote_filename=None):
    """上传 PDF 到 FTP"""
    with FTP() as ftp:
        if remote_path and remote_path.__contains__("YXY_YT"):
            # 油田 pdf 保存地址
            ftp.connect("192.168.200.3", 21)
            ftp.login("pacs", "123456")
        else:
            # 康复中医院 pdf 保存地址
            ftp.connect("192.168.3.99", 21)
            ftp.login("zlpacs", "zlpacs")

        # 从ftp路径中获取目录
        remote_path = extract_dir(remote_path)
        for folder in remote_path.strip("/").split("/"):
            if folder not in ftp.nlst():
                try:
                    ftp.mkd(folder)
                except Exception:
                    pass
            ftp.cwd(folder)

        if not remote_filename:
            remote_filename = os.path.basename(local_pdf)

        with open(local_pdf, "rb") as f:
            ftp.storbinary(f"STOR " + remote_filename, f)


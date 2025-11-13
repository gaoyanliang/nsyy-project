import datetime
import os
from ftplib import FTP
from urllib.parse import urlparse
from datetime import datetime

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from gylmodules import global_tools
from gylmodules.global_tools import api_response
from gylmodules import global_config
from gylmodules.pacs_pdf import yt_pacs_tools
from gylmodules.utils.db_utils import DbUtil

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
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)

    data = db.query_one(sql)
    del db

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

        db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                    global_config.DB_DATABASE_GYL)
        sql = f"""UPDATE nsyy_gyl.medical_reports SET is_upload = 1 WHERE 医嘱ID = {advice_id}"""
        db.execute(sql, need_commit=True)
        del db

        return {"code": 20000, "data": f'PDF文件 {filename} 上传成功', "res": f"PDF文件 {filename} 上传成功"}
    else:
        return {"code": 50000, "data": '', "res": f"只允许上传 PDF 文件"}


"""查询并保存pacs 记录"""


def query_and_save_report():
    yt_sql = """
    select v.姓名,
       v.性别,
       v.年龄,
       v.检查号,
       v.科室,
       v.床号,
       v.检查日期,
       v.住院号,
       v.门诊号,
       v.检查项目,
       v.标本部位,
       v.检查所见,
       v.诊断意见,
       v.报告时间,
       v.报告医生,
       v.审核时间,
       v.审核医生,
       v.医嘱ID,
       v.PDF路径  "pdf路径",
       ry.编号    报告医生编号,
       ry2.编号   审核医生编号
  from (select brxx.姓名,
               brxx.性别,
               coalesce(gh.年龄, g.年龄, jc.年龄) 年龄,
               jc.检查号,
               bmb.名称 科室,
               bd.床号,
               yzfs.报到时间 检查日期,
               gh.门诊号,
               g.住院号,
               jc.影像类别 检查项目,
               bw.标本部位,
               nn.检查所见,
               mm.检查结论 诊断意见,
               bl.创建时间 报告时间,
               bl.创建人 报告医生,
               bl.完成时间 审核时间,
               decode(jc.影像类别,
                      'CT',
                      '刘飞',
                      'MR',
                      '杨明贵',
                      'DR',
                      '张志强',
                      bl.保存人) 审核医生,
               yz.id 医嘱ID,
               'ftp://192.168.200.3/YXY_YT/' || jc.影像类别 || '/' ||
               to_char(yz.开嘱时间, 'yyyymmdd') || '/' || yz.id || '/' || yz.id ||
               '.pdf' pdf路径
          from 病人医嘱记录 yz
          join 病人医嘱发送 yzfs
            on yz.id = yzfs.医嘱ID
          join 影像检查记录 jc
            on yz.id = jc.医嘱id
           and yzfs.发送号 = jc.发送号
           and jc.影像类别 <> 'US'
          join 病人医嘱报告 yzbg
            on yz.id = yzbg.医嘱id
          join 电子病历记录 bl
            on yzbg.病历id = bl.id
          join (Select 内容文本 As 检查结论, 文件id
                 From 电子病历内容 qq
                Where qq.终止版 = 0
                  And 对象属性 =
                      '0|0|1|1||9972|300|2|False|0|-1|0|1|False|True|宋体|11|False|False|False|False|400||0|0|False|'
                  and 内容文本 is not null) mm
            on bl.id = mm.文件id
          join (Select 内容文本 As 检查所见, 文件id
                 From 电子病历内容 qq
                Where qq.终止版 = 0
                  And 对象属性 =
                      '0|0|1|1||9763|2772|2|False|0|-1|0|1|False|True|宋体|11|False|False|False|False|400||0|0|False|'
                  and 内容文本 is not null) nn
            on bl.id = nn.文件id
          left join (select 相关id,
                           listagg(标本部位, '、') within group(order by id) as 标本部位
                      from 病人医嘱记录
                     group by 相关id) bw
            on yz.id = bw.相关id
          join 部门表 bmb
            on yz.开嘱科室id = bmb.id
          left join 病人挂号记录 gh
            on yz.病人id = gh.病人id
           and yz.挂号单 = gh.no
          left join 病案主页 g
            on yz.病人id = g.病人id
           and yz.主页id = g.主页id
          left join 病人变动记录 bd
            on bd.病人id = g.病人id
           and bd.主页id = g.主页id
           and bd.开始时间 <= yz.开嘱时间
           and bd.终止时间 > yz.开嘱时间
          join 病人信息 brxx
            on yz.病人id = brxx.病人id
            union 
            select brxx.姓名,
               brxx.性别,
               coalesce(gh.年龄, g.年龄, jc.年龄) 年龄,
               jc.检查号,
               bmb.名称 科室,
               bd.床号,
               yzfs.报到时间 检查日期,
               gh.门诊号,
               g.住院号,
               jc.影像类别 检查项目,
               bw.标本部位,
               nn.检查所见,
               mm.检查结论 诊断意见,
               bl.创建时间 报告时间,
               bl.创建人 报告医生,
               bl.完成时间 审核时间,
               decode(jc.影像类别,
                      'CT',
                      '刘飞',
                      'MR',
                      '杨明贵',
                      'DR',
                      '张志强',
                      bl.保存人) 审核医生,
               yz.id 医嘱ID,
               'ftp://192.168.200.3/YXY_YT/' || jc.影像类别 || '/' ||
               to_char(yz.开嘱时间, 'yyyymmdd') || '/' || yz.id || '/' || yz.id ||
               '.pdf' pdf路径
          from 病人医嘱记录 yz
          join 病人医嘱发送 yzfs
            on yz.id = yzfs.医嘱ID
          join 影像检查记录 jc
            on yz.id = jc.医嘱id
           and yzfs.发送号 = jc.发送号
           and jc.影像类别 <> 'US'
          join 病人医嘱报告 yzbg
            on yz.id = yzbg.医嘱id
          join 电子病历记录 bl
            on yzbg.病历id = bl.id
          join (Select 内容文本 As 检查结论, 文件id
                 From 电子病历内容 qq
                Where qq.终止版 = 0
                  And 对象属性 =
                      '0|0|1|1||8266|3373|2|False|0|-1|0|1|False|True|宋体|14|False|False|False|False|400||0|0|False|'
                  and 内容文本 is not null) mm
            on bl.id = mm.文件id
          join (Select 内容文本 As 检查所见, 文件id
                 From 电子病历内容 qq
                Where qq.终止版 = 0
                  And 对象属性 =
                      '0|0|1|1||7994|2387|2|False|0|-1|0|1|False|True|宋体|14|False|False|False|False|400||0|0|False|'
                  and 内容文本 is not null) nn
            on bl.id = nn.文件id
          left join (select 相关id,
                           listagg(标本部位, '、') within group(order by id) as 标本部位
                      from 病人医嘱记录
                     group by 相关id) bw
            on yz.id = bw.相关id
          join 部门表 bmb
            on yz.开嘱科室id = bmb.id
          left join 病人挂号记录 gh
            on yz.病人id = gh.病人id
           and yz.挂号单 = gh.no
          left join 病案主页 g
            on yz.病人id = g.病人id
           and yz.主页id = g.主页id
          left join 病人变动记录 bd
            on bd.病人id = g.病人id
           and bd.主页id = g.主页id
           and bd.开始时间 <= yz.开嘱时间
           and bd.终止时间 > yz.开嘱时间
          join 病人信息 brxx
            on yz.病人id = brxx.病人id
            ) v
  left join 人员表 ry
    on v.报告医生 = ry.姓名
  left join 人员表 ry2
    on v.审核医生 = ry2.姓名
 where v.审核时间 >= sysdate - 2/24 and v.审核时间 <= sysdate
    """

    kf_sql = """select v.姓名, v.性别, v.年龄, v.检查号, v.科室, v.床号, v.检查日期, v.住院号, v.门诊号, v.检查项目,
          v.标本部位, v.检查所见, v.诊断意见, v.报告时间, v.报告医生, v.审核时间, v.审核医生, v.医嘱ID, v.PDF路径 "pdf路径",
          ry.编号    报告医生编号, ry2.编号   审核医生编号 from (select brxx.姓名, brxx.性别,
           coalesce(gh.年龄, g.年龄, jc.年龄) 年龄, jc.检查号, bmb.名称 科室, bd.床号, yzfs.报到时间 检查日期, gh.门诊号,
                  g.住院号, jc.影像类别 检查项目, bw.标本部位, nn.检查所见, mm.检查结论 诊断意见, bl.创建时间 报告时间, 
                  bl.创建人 报告医生,  bl.完成时间 审核时间, bl.保存人 审核医生,
                  yz.id 医嘱ID, 'ftp://192.168.3.99/YXY_KF/' || jc.影像类别 || '/' ||
                  to_char(yz.开嘱时间, 'yyyymmdd') || '/' || yz.id || '/' || yz.id ||
                  '.pdf' pdf路径
             from 病人医嘱记录 yz join 病人医嘱发送 yzfs on yz.id = yzfs.医嘱ID
             join 影像检查记录 jc on yz.id = jc.医嘱id and yzfs.发送号 = jc.发送号 and jc.影像类别 <> 'US'
             join 病人医嘱报告 yzbg on yz.id = yzbg.医嘱id
             join 电子病历记录 bl on yzbg.病历id = bl.id
             join (Select 内容文本 As 检查结论, 文件id From 电子病历内容 qq Where qq.终止版 = 0 And 对象属性 =
                         '0|0|1|1||8237|3390|2|False|0|-1|0|1|False|True|宋体|14|False|False|False|False|400||0|0|False|'
                     and 内容文本 is not null) mm on bl.id = mm.文件id
             join (Select 内容文本 As 检查所见, 文件id From 电子病历内容 qq Where qq.终止版 = 0
                     And 对象属性 = '0|0|1|1||8957|658|2|False|0|-1|0|1|False|True|宋体|11|False|False|False|False|400||0|0|False|'
                     and 内容文本 is not null) nn on bl.id = nn.文件id
             left join (select 相关id, listagg(标本部位, '、') within group(order by id) as 标本部位 from 病人医嘱记录
                        group by 相关id) bw on yz.id = bw.相关id
             join 部门表 bmb on yz.开嘱科室id = bmb.id left join 病人挂号记录 gh on yz.病人id = gh.病人id
              and yz.挂号单 = gh.no left join 病案主页 g on yz.病人id = g.病人id and yz.主页id = g.主页id
             left join 病人变动记录 bd on bd.病人id = g.病人id and bd.主页id = g.主页id and bd.开始时间 <= yz.开嘱时间
              and bd.终止时间 > yz.开嘱时间 join 病人信息 brxx on yz.病人id = brxx.病人id) v
     left join 人员表 ry on v.报告医生 = ry.姓名 left join 人员表 ry2 on v.审核医生 = ry2.姓名
    where v.审核时间 >= sysdate - 2/24 and v.审核时间 <= sysdate"""

    yt_data = global_tools.call_new_his(sql=yt_sql, sys='ythis', clobl=[])
    kf_data = global_tools.call_new_his(sql=kf_sql, sys='kfhis', clobl=[])
    if yt_data:
        for item in yt_data:
            item["来源"] = "油田"
    if kf_data:
        for item in kf_data:
            item["来源"] = "康复"
    # print(data)
    db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
                global_config.DB_DATABASE_GYL)
    sql = """INSERT IGNORE INTO nsyy_gyl.medical_reports
    (医嘱ID, 姓名, 性别, 住院号, 年龄, 检查号, 科室, 床号, 检查日期, 门诊号, 检查项目, 报告时间, 标本部位, 检查所见, 
    诊断意见, 报告医生, 审核医生, pdf路径, 审核时间, 报告医生编号, 审核医生编号, 来源)
    VALUES (%(医嘱ID)s, %(姓名)s, %(性别)s, %(住院号)s, %(年龄)s, %(检查号)s, %(科室)s, %(床号)s, %(检查日期)s, 
    %(门诊号)s, %(检查项目)s, %(报告时间)s, %(标本部位)s, %(检查所见)s, %(诊断意见)s, %(报告医生)s, %(审核医生)s, 
    %(pdf路径)s, %(审核时间)s, %(报告医生编号)s, %(审核医生编号)s, %(来源)s)
    """
    if yt_data:
        db.execute_many(sql, yt_data, need_commit=True)
    if kf_data:
        db.execute_many(sql, kf_data, need_commit=True)
    del db


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


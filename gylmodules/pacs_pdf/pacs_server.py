#!/usr/bin/env python3
import logging
import sys
from datetime import datetime

sys.path.insert(0, '/home/gyl/gyl_server')  # 就这一行！

# 添加日志配置
# 配置日志系统
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # 输出到控制台
        logging.StreamHandler(sys.stdout),
        # 输出到同级目录的日志文件
        logging.FileHandler(f'pacs_server.log')
    ]
)
# 设置第三方库日志级别为 WARNING
for lib in ['urllib3', 'requests', 'asyncio', 'httpx', 'selenium', 'paramiko']:
    logging.getLogger(lib).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from gylmodules import global_config, global_tools
from gylmodules.utils.db_utils_new import DbUtil


def query_and_save_report():
    logger.info('开始查询 pacs pdf')
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
       v.检查所见 诊断意见,
       v.诊断意见 检查所见,
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
    sql = """INSERT IGNORE INTO nsyy_gyl.medical_reports
    (医嘱ID, 姓名, 性别, 住院号, 年龄, 检查号, 科室, 床号, 检查日期, 门诊号, 检查项目, 报告时间, 标本部位, 检查所见, 
    诊断意见, 报告医生, 审核医生, pdf路径, 审核时间, 报告医生编号, 审核医生编号, 来源)
    VALUES (%(医嘱ID)s, %(姓名)s, %(性别)s, %(住院号)s, %(年龄)s, %(检查号)s, %(科室)s, %(床号)s, %(检查日期)s, 
    %(门诊号)s, %(检查项目)s, %(报告时间)s, %(标本部位)s, %(检查所见)s, %(诊断意见)s, %(报告医生)s, %(审核医生)s, 
    %(pdf路径)s, %(审核时间)s, %(报告医生编号)s, %(审核医生编号)s, %(来源)s)
    """

    logger.info(f" 查询完成 开始插入数据 yt_data {len(yt_data)}  kf_data {len(kf_data)}")

    with DbUtil(global_config.DB_HOST, global_config.DB_USERNAME,
                global_config.DB_PASSWORD, global_config.DB_DATABASE_GYL) as db:
        if yt_data:
            db.execute_many(sql, yt_data, need_commit=True)
        if kf_data:
            db.execute_many(sql, kf_data, need_commit=True)


if __name__ == '__main__':
    query_and_save_report()
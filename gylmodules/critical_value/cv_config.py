#  === redis config ===

CV_REDIS_HOST = '127.0.0.1'
CV_REDIS_PORT = 6379
CV_REDIS_DB = 2

# 患者类型 1=门诊,2=急诊,3=住院,4=体检,5=手工临时上报

PATIENT_TYPE_OUTPATIENT_SERVICE = 1
PATIENT_TYPE_EMERGENCY_DEPARTMENT = 2
PATIENT_TYPE_HOSPITALIZATION = 3
PATIENT_TYPE_PHYSICAL_EXAMINATION = 4
PATIENT_TYPE_OTHER = 5


# 危机值来源 1=人工 2=检验系统 3=影像系统 4 心电图 5 床旁血糖 10 手工上报

CV_SOURCE_LABOR = 1
CV_SOURCE_INSPECTION_SYSTEM = 2
CV_SOURCE_IMAGING_SYSTEM = 3
CV_SOURCE_XINDIAN_SYSTEM = 4
CV_SOURCE_XUETANG_SYSTEM = 5
CV_SOURCE_MANUAL = 10

cv_manual_default_treat_id = "120"


# cv state 危机值状态
INVALID_STATE = 0  # 作废
CREATED_STATE = 1   # 新建
NOTIFICATION_NURSE_STATE = 2  # 已通知护理
NURSE_RECV_TIMEOUT_STATE = 3   # 护理接收超时
NURSE_RECV_STATE = 4  # 护理已接收
NOTIFICATION_DOCTOR_STATE = 5  # 已通知医生
DOCTOR_RECV_TIMEOUT_STATE = 6  # 医生接收超时
DOCTOR_RECV_STATE = 7  # 医生已接收
DOCTOR_HANDLE_TIMEOUT_STATE = 8  # 医生处理超时
DOCTOR_HANDLE_STATE = 9  # 医生已处理

# 超时时间 redis key
TIMEOUT_REDIS_KEY = {'nurse_recv': 'CV_TIMEOUT:CV_NURSE_RECV_TIMEOUT',
                     'nurse_send': 'CV_TIMEOUT:CV_NURSE_SEND_TIMEOUT',
                     'doctor_recv': 'CV_TIMEOUT:CV_DOCTOR_RECV_TIMEOUT',
                     'doctor_handle': 'CV_TIMEOUT:CV_DOCTOR_HANDLE_TIMEOUT',
                     'total': 'CV_TIMEOUT:CV_TOTAL_TIMEOUT'}

# 部门信息
DEPT_INFO_REDIS_KEY = 'CV_DEPT_INFO_REDIS_KEY'

# 运行中的危机值列表
RUNNING_CVS_REDIS_KEY = 'CV_RUNNING_CVS'

# 手工上报的危急值记录
MANUAL_CVS_REDIS_KEY = 'CV_MANUAL_CVS'

# 站点类型
CV_SITES_REDIS_KEY = {1: 'CV_SITES_WARD:{}', 2: 'CV_SITES_DEPT:{}'}

# 危急值模版
CV_TEMPLATE_REDIS_KEY = 'CV_TEMPLATE'

# ip站点 自动启动危急值程序失败
ALERT_FAIL_IPS_REDIS_KEY = 'CV_ALERT_FAIL_IPS'


patient_type_map = {
    1: '1',  # 门诊
    2: '0',  # 急诊
    3: '2',  # 住院
    4: '1',  # 体检（默认和门诊相同）
}

personnel_in_ultrasound2 = ["0577", "0735", "1569", "1711", "1863", "3258", "2935", "2983"]
# 超声二科的人员： 郑莉 0577 卢涛 0735 董娜 1569 朱慧慧 1711 朱刘欢 1863 闫炳仿 3258 范小华 2935 杨春燕 2983
personnel_in_ultrasound = ["1862"]
# 彩超室人员： 张琼月 1862



HIS_SYNCHRONIZE_DATA = """
<message>
    <request>
        <msg_id>{msg_id}</msg_id>
        <event_id>{event_id}</event_id>
        <creat_time>{creat_time}</creat_time>
        <sender>WEIJIZHI</sender>
        <receiver>HIS</receiver>
    </request>
    <body>
        <weijizhiwbid>{weijizhiwbid}</weijizhiwbid>
        <weijizhiid>{weijizhiid}</weijizhiid>
        <bingrenid>{bingrenid}</bingrenid>
        <leixing>{leixing}</leixing>
        <bingrenzyid>{bingrenzyid}</bingrenzyid>
        <menzhenzybz>{menzhenzybz}</menzhenzybz>
        <bingrenxm>{bingrenxm}</bingrenxm>
        <zhuyuanhao>{zhuyuanhao}</zhuyuanhao>
        <xingbie>{xingbie}</xingbie>
        <nianling>{nianling}</nianling>
        <bingqumc>{bingqumc}</bingqumc>
        <bingquid>{bingquid}</bingquid>
        <chuangweihao>{chuangweihao}</chuangweihao>
        <keshimc>{keshimc}</keshimc>
        <keshiid>{keshiid}</keshiid>
        <chuangjiansj>{chuangjiansj}</chuangjiansj>
        <weijizhinr>{weijizhinr}</weijizhinr>
        <jianyanjg>{jianyanjg}</jianyanjg>
        <dangwei>{dangwei}</dangwei>
        <cankaofw>{cankaofw}</cankaofw>
        <jianchaxmmc>{jianchaxmmc}</jianchaxmmc>
        <fasongsj>{fasongsj}</fasongsj>
        <fasongrenxm>{fasongrenxm}</fasongrenxm>
        <fasongren>{fasongren}</fasongren>
        <zuofeibz>{zuofeibz}</zuofeibz>
        <zuofeisj>{zuofeisj}</zuofeisj>
        <zuofeiren>{zuofeiren}</zuofeiren>
        <huifuysid>{huifuysid}</huifuysid>
        <huifuysxm>{huifuysxm}</huifuysxm>
        <yishenghfsj>{yishenghfsj}</yishenghfsj>
        <yishengclfs>1</yishengclfs>
        <yishengclnr>{yishengclnr}</yishengclnr>
        <huifuhsid>{huifuhsid}</huifuhsid>
        <huifuhsxm>{huifuhsxm}</huifuhsxm>
        <hushihfsj>{hushihfsj}</hushihfsj>
        <hushiclnr>{hushiclnr}</hushiclnr>
        <hushiclbz>1</hushiclbz>
        <jieshouhsid>{jieshouhsid}</jieshouhsid>
        <jieshouhsxm>{jieshouhsxm}</jieshouhsxm>
        <jieshousj>{jieshousj}</jieshousj>
        <tongzhiyssj>{tongzhiyssj}</tongzhiyssj>
        <tongzhiysxm>{tongzhiysxm}</tongzhiysxm>
        <tongzhiysid>{tongzhiysid}</tongzhiysid>
        <baogaodanid>{baogaodanid}</baogaodanid>
        <baogaosj>{baogaosj}</baogaosj>
        <jianyantmh>{jianyantmh}</jianyantmh>
        <zhixingsj>{zhixingsj}</zhixingsj>
        <shenqingdanid>{shenqingdanid}</shenqingdanid>
        <kaidanren>{kaidanren}</kaidanren>
        <kaidanksmc>{kaidanksmc}</kaidanksmc>
        <kaidanks>{kaidanks}</kaidanks>
        <kaidanrenxm>{kaidanrenxm}</kaidanrenxm>
        <kaidanrq>{kaidanrq}</kaidanrq>
        <yuanquid>1</yuanquid>
    </body>
</message>
"""








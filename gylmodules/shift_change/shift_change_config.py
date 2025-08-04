
doctor_shift_change_time = []


bed_info_list = [
    "管路滑脱高危患者",
    "防跌倒坠床患者",
    "压力性损伤高风险患者",
    "传染病患者",
    "VTE确诊患者",
    "VTE高危患者",
    "行为异常、有自杀倾向患者",
    "易走失的患者",
    "三日未排大便",
    "少数民族患者",
    "宗教信仰",
    "未结算人员",
    "多耐患者",
    "过敏史患者",
]

default_bed_info_list = {
    "管路滑脱高危患者": {"patient_type": "管路滑脱高危患者", "patient_info": ""},
    "防跌倒坠床患者": {"patient_type": "防跌倒坠床患者", "patient_info": ""},
    "压力性损伤高风险患者": {"patient_type": "压力性损伤高风险患者", "patient_info": ""},
    "传染病患者": {"patient_type": "传染病患者", "patient_info": ""},
    "VTE确诊患者": {"patient_type": "VTE确诊患者", "patient_info": ""},
    "VTE高危患者": {"patient_type": "VTE高危患者", "patient_info": ""},
    "行为异常、有自杀倾向患者": {"patient_type": "行为异常、有自杀倾向患者", "patient_info": ""},
    "易走失的患者": {"patient_type": "易走失的患者", "patient_info": ""},
    "三日未排大便": {"patient_type": "三日未排大便", "patient_info": ""},
    "少数民族患者": {"patient_type": "少数民族患者", "patient_info": ""},
    "宗教信仰": {"patient_type": "宗教信仰", "patient_info": ""},
    "未结算人员": {"patient_type": "未结算人员", "patient_info": ""},
    "多耐患者": {"patient_type": "多耐患者", "patient_info": ""},
    "过敏史患者": {"patient_type": "过敏史患者", "patient_info": ""},
}

patient_type_list = [
    '入院',
    '出院',
    '手术',
    '现有',
    '病危',
    '病重',
    '转入',
    '转出',
    '一级护理',
    '新生',
    '死亡',
    '特护',
    '顺生',
    '预术',
]

dept_people_count = ["原有", "现有", "入院", "手术", "出院", "病危", "病重", "转入", "转出", "死亡", "危机值"]
ward_people_count = ["现有", "入院", "出院", "病危", "病重", "转入", "转出", "死亡", "手术", "预术", "特护", "一级护理"]



import xml.etree.ElementTree as ET
import json
import os

from gylmodules.medical_record_analysis.record_parse.admission_record_parse import parse_hpi, clean_dict
from gylmodules.medical_record_analysis.build_cda.build_cda import assembling_cda_record

"""
====================================================================================================
============================================ 危急值报告处理记录(门诊)解析 ==============================
====================================================================================================
"""


# 从危急值报告处理记录(门诊) 解析危急值记录
def parse_cv_by_str(xml_str):
    try:
        root = ET.fromstring(xml_str)
        cv_info = {}
        document = root.find('document')

        element = document.find(".//element[@sid='CE6A04DE74264F938FC1A903103BFC5E']")
        record_time = ''
        if element is not None:
            record_time = element.get('value')
        cv_record = ''
        for utext in document.iter('utext'):
            if utext.text is not None and not utext.text.__contains__('南阳南石医院') \
                    and not utext.text.__contains__('危急值报告处理记录'):
                cv_record = cv_record + utext.text.strip() if utext.text else ''
        if record_time:
            cv_info[record_time] = cv_record
        return cv_info
    except Exception as e:
        return {}


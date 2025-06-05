import json
import xml.etree.ElementTree as ET
import re
import os
from collections import OrderedDict

"""
解析 cda xml 文件
"""


def parse_cda_xml_document_by_str(xml_str):
    root = ET.fromstring(xml_str)
    return parse_cda_xml_document(root)


def parse_cda_xml_document_by_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return parse_cda_xml_document(root)


def parse_cda_xml_document(root):
    # tree = ET.parse(xml_file)
    # root = tree.getroot()
    parse_data = OrderedDict()

    # 设置命名空间
    namespaces = {'hl7': 'urn:hl7-org:v3'}

    # ======================= 解析 header =======================

    # === 1. 文档信息
    file_info = {}
    file_info['标题'] = root.find('hl7:title', namespaces).text if root.find('hl7:title', namespaces) is not None else '/'
    file_info['文档流水号'] = root.find('hl7:id', namespaces).get('extension') if root.find('hl7:id',
                                                                                           namespaces) is not None else '/'
    file_info['文档生成时间'] = root.find('hl7:effectiveTime', namespaces).get('value')
    file_info['文档类型'] = root.find('hl7:code', namespaces).get('code')
    parse_data['文档信息'] = file_info

    # === 2. 文档记录对象
    patient_role = root.find('hl7:recordTarget/hl7:patientRole', namespaces)
    if patient_role:
        p_info = {}
        id_list = patient_role.findall('hl7:id', namespaces)
        for id in id_list:
            if id.get('root') is not None and id.get('root') == '2.16.156.10011.1.19':
                p_info['健康卡号'] = id.get('extension') if id.get('extension') else '/'
            elif id.get('root') is not None and id.get('root') == '2.16.156.10011.1.12':
                p_info['住院号'] = id.get('extension') if id.get('extension') else '/'
            elif id.get('root') is not None and id.get('root') == '2.16.156.10011.1.13':
                p_info['病案号'] = id.get('extension') if id.get('extension') else '/'

        # 病人住址
        if patient_role.find('hl7:addr', namespaces) is not None:
            p_info['现住址'] = patient_role.find('hl7:addr/hl7:houseNumber', namespaces).text if patient_role.find(
                'hl7:addr/hl7:houseNumber', namespaces) is not None else '/'
            p_info['现住址-省'] = patient_role.find('hl7:addr/hl7:state', namespaces).text if patient_role.find(
                'hl7:addr/hl7:state', namespaces) is not None else '/'
            p_info['现住址-市'] = patient_role.find('hl7:addr/hl7:city', namespaces).text if patient_role.find(
                'hl7:addr/hl7:city', namespaces) is not None else '/'
            p_info['现住址-县'] = patient_role.find('hl7:addr/hl7:county', namespaces).text if patient_role.find(
                'hl7:addr/hl7:county', namespaces) is not None else '/'
        p_info['患者联系电话'] = patient_role.find('hl7:telecom', namespaces).get(
            'value') if patient_role.find('hl7:telecom', namespaces) is not None else '/'

        p_info['患者身份证号'] = patient_role.find('hl7:patient/hl7:id', namespaces).get(
            'extension') if patient_role.find('hl7:patient/hl7:id', namespaces) is not None else '/'
        p_info['患者姓名'] = patient_role.find('hl7:patient/hl7:name', namespaces).text if patient_role.find(
            'hl7:patient/hl7:name', namespaces) is not None else '/'
        p_info['患者性别编码'] = patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces) is not None else '/'
        p_info['患者性别'] = patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:administrativeGenderCode',
                                                namespaces) is not None else '/'
        p_info['患者出生日期'] = patient_role.find('hl7:patient/hl7:birthTime', namespaces).get(
            'value') if patient_role.find('hl7:patient/hl7:birthTime', namespaces) is not None else '/'

        p_info['患者婚姻状况编码'] = patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces) is not None else '/'
        p_info['患者婚姻状况'] = patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces) is not None else '/'
        p_info['患者民族编码'] = patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces) is not None else '/'
        p_info['患者民族'] = patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces) is not None else '/'

        p_info['患者年龄'] = patient_role.find('hl7:patient/hl7:age', namespaces).get(
            'value') if patient_role.find('hl7:patient/hl7:age', namespaces) is not None else '/'
        p_info['患者职业编码'] = patient_role.find('hl7:patient/hl7:occupation/hl7:occupationCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:occupation', namespaces) is not None and patient_role.find(
            'hl7:patient/hl7:occupation/hl7:occupationCode', namespaces) is not None else '/'
        p_info['患者职业'] = patient_role.find('hl7:patient/hl7:occupation/hl7:occupationCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:occupation',
                                                namespaces) is not None and patient_role.find(
            'hl7:patient/hl7:occupation/hl7:occupationCode', namespaces) is not None else '/'

        p_info['出生地'] = patient_role.find('hl7:patient/hl7:birthplace/hl7:place/hl7:addr/hl7:county',
                                                      namespaces).text if patient_role.find(
            'hl7:patient/hl7:birthplace', namespaces) is not None else '/'
        p_info['出生地编码'] = patient_role.find('hl7:patient/hl7:birthplace/hl7:place/hl7:addr/hl7:postalCode',
                                                      namespaces).text if patient_role.find(
            'hl7:patient/hl7:birthplace', namespaces) is not None else '/'
        p_info['国籍'] = patient_role.find('hl7:patient/hl7:nationality',
                                                     namespaces).get('displayName') if patient_role.find(
            'hl7:patient/hl7:nationality', namespaces) is not None else '/'
        p_info['工作单位名称'] = patient_role.find('hl7:patient/hl7:employerOrganization/hl7:name',
                                                     namespaces).text if patient_role.find(
            'hl7:patient/hl7:employerOrganization', namespaces) is not None else '/'
        p_info['工作单位电话'] = patient_role.find('hl7:patient/hl7:employerOrganization/hl7:telecom',
                                                       namespaces).get('value') if patient_role.find(
            'hl7:patient/hl7:employerOrganization/hl7:telecom', namespaces) is not None else '/'
        p_info['工作单位邮编'] = patient_role.find('hl7:patient/hl7:employerOrganization/hl7:addr/hl7:postalCode',
                                                     namespaces).text if patient_role.find(
            'hl7:patient/hl7:employerOrganization', namespaces) is not None else '/'
        p_info['工作单位地址'] = patient_role.find('hl7:patient/hl7:employerOrganization/hl7:addr/hl7:houseNumber',
                                                       namespaces).text if patient_role.find(
            'hl7:patient/hl7:employerOrganization', namespaces) is not None else '/'

        p_info['户口地址'] = patient_role.find('hl7:patient/hl7:household/hl7:place/hl7:addr/hl7:houseNumber',
                                                       namespaces).text if patient_role.find(
            'hl7:patient/hl7:household', namespaces) is not None else '/'
        p_info['户口地邮编'] = patient_role.find('hl7:patient/hl7:household/hl7:place/hl7:addr/hl7:postalCode',
                                                   namespaces).text if patient_role.find(
            'hl7:patient/hl7:household', namespaces) is not None else '/'
        p_info['籍贯地址'] = patient_role.find('hl7:patient/hl7:nativePlace/hl7:place/hl7:addr/hl7:city',
                                                      namespaces).text if patient_role.find(
            'hl7:patient/hl7:nativePlace', namespaces) is not None else '/'

        parse_data['患者信息'] = p_info

    # 文档创作者
    author = root.find('hl7:author', namespaces)
    if author:
        author_info = {}
        author_info['文档创作时间'] = author.find('hl7:author/hl7:time', namespaces).get('value') if author.find(
            'hl7:author/hl7:time', namespaces) is not None else '/'
        author_info['文档创作者id'] = author.find('hl7:author/hl7:assignedAuthor/hl7:id', namespaces).get(
            'extension') if author.find('hl7:author/hl7:assignedAuthor/hl7:id', namespaces) is not None else '/'
        author_info['文档创作者'] = author.find('hl7:author/hl7:assignedAuthor/hl7:assignedAuthor/hl7:name',
                                                 namespaces).text if author.find(
            'hl7:author/hl7:assignedAuthor/hl7:assignedAuthor/hl7:name', namespaces) is not None else '/'
        parse_data['文档创作者信息'] = author_info

    # 病史陈述者
    informant = root.find('hl7:informant', namespaces)
    if informant:
        informant_info = {}
        informant_info['陈述者身份证号'] = informant.find('hl7:assignedEntity/hl7:id', namespaces).get(
            'extension') if informant.find('hl7:assignedEntity/hl7:id', namespaces) is not None else '/'
        informant_info['陈述者与患者关系代码'] = informant.find('hl7:assignedEntity/hl7:code', namespaces).get(
            'code') if informant.find('hl7:assignedEntity/hl7:code', namespaces) is not None else '/'
        informant_info['陈述者与患者关系'] = informant.find('hl7:assignedEntity/hl7:code', namespaces).get(
            'displayName') if informant.find('hl7:assignedEntity/hl7:code', namespaces) is not None else '/'
        informant_info['陈述者姓名'] = informant.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces).text \
            if informant.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces) is not None else '/'
        parse_data['病史陈述者信息'] = informant_info

    # 保管机构
    custodian = root.find('hl7:custodian', namespaces)
    if custodian:
        parse_data['保管机构编码'] = custodian.find('hl7:assignedCustodian/hl7:representedCustodianOrganization/hl7:id',
                                                    namespaces).get('extension') \
            if custodian.find('hl7:assignedCustodian/hl7:representedCustodianOrganization/hl7:id',
                              namespaces) is not None else '/'
        parse_data['保管机构名称'] = custodian.find(
            'hl7:assignedCustodian/hl7:representedCustodianOrganization/hl7:name', namespaces).text if custodian.find(
            'hl7:assignedCustodian/hl7:representedCustodianOrganization/hl7:name', namespaces) is not None else '/'

    # 最终审核者
    legal_authenticator = root.find('hl7:legalAuthenticator', namespaces)
    if legal_authenticator:
        parse_data['最终审核者编码'] = legal_authenticator.find('hl7:assignedEntity/hl7:id', namespaces).get(
            'extension') if legal_authenticator.find('hl7:assignedEntity/hl7:id', namespaces) is not None else '/'
        parse_data['最终审核者名称'] = legal_authenticator.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name',
                                                                namespaces).text if legal_authenticator.find(
            'hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces) is not None else '/'

    # 其他医师
    authenticators = root.findall('hl7:authenticator', namespaces)
    if authenticators:
        for au in authenticators:
            name = au.find('hl7:assignedEntity/hl7:code', namespaces).get('displayName')
            parse_data[name + '编码'] = au.find('hl7:assignedEntity/hl7:id', namespaces).get('extension')
            parse_data[name + '名称'] = au.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces).text \
                if au.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces) else '/'

    # 患者联系人
    participant = root.find('participant', namespaces)
    if participant is not None:
        parse_data['联系人与患者关系'] = participant.find('hl7:associatedEntity/hl7:code', namespaces).get('code')
        parse_data['联系人姓名'] = participant.find('hl7:associatedEntity/hl7:assignedPerson/hl7:name', namespaces).text
        parse_data['联系人住址'] = participant.find('hl7:associatedEntity/hl7:addr/hl7:houseNumber', namespaces).text
        parse_data['联系人电话'] = participant.find('hl7:associatedEntity/hl7:telecom', namespaces).get('value')

    # 病床号、病房、病区、科室和医院的关联
    component_of = root.find('hl7:componentOf', namespaces)
    if component_of:
        ee = component_of.find('hl7:encompassingEncounter', namespaces)
        parse_data['入院途径'] = ee.find('hl7:code', namespaces).get('displayName') if ee.find('hl7:code', namespaces) is not None else '/'

        if ee.find('hl7:effectiveTime', namespaces) is not None:
            parse_data['入院日期'] = ee.find('hl7:effectiveTime', namespaces).get('value', '/')
        if ee.find('hl7:effectiveTime/hl7:low', namespaces) is not None:
            parse_data['入院日期'] = ee.find('hl7:effectiveTime/hl7:low', namespaces).get('value')
            parse_data['出院日期'] = ee.find('hl7:effectiveTime/hl7:high', namespaces).get('value')

        parse_data['病床编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension') if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces) is not None else '/'
        parse_data['病床'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces) is not None else '/'
        parse_data['病房编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension') if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces) is not None else '/'
        parse_data['病房'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces) is not None else '/'
        parse_data['科室编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension') if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces) is not None else '/'
        parse_data['科室'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces) is not None else '/'
        parse_data['病区编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension') if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces) is not None else '/'
        parse_data['病区'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces) is not None else '/'
        parse_data['医院编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension') if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces) is not None else '/'
        parse_data['医院'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text if ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces) is not None else '/'

    # ======================= 解析 body =======================
    component = root.find('hl7:component', namespaces)
    if component:
        components = component.findall('hl7:structuredBody/hl7:component', namespaces)
        for item in components:
            com_dict = {}

            item_name = item.find('hl7:section/hl7:code', namespaces).get('displayName', './')
            code = item.find('hl7:section/hl7:code', namespaces).get('code', '/')

            key = code
            if key == '/':
                key = item_name

            text = item.find('hl7:section/hl7:text', namespaces).text if item.find('hl7:section/hl7:text', namespaces) is not None else '/'
            for entry in item.findall('hl7:section/hl7:entry', namespaces):
                entry_dict = {}
                if entry.find('hl7:organizer', namespaces) is not None:
                    coms = entry.findall('hl7:organizer/hl7:component', namespaces)
                    for com in coms:
                        observation = com.find('hl7:observation', namespaces)
                        name = observation.find('hl7:code', namespaces).get('displayName')
                        if name is None:
                            if observation.find('hl7:code', namespaces).get('code') == 'DE04.50.001.00':
                                name = 'ABO血型'
                            elif observation.find('hl7:code', namespaces).get('code') == 'DE04.50.010.00':
                                name = 'Rh血型'

                        entry_dict['time'] = observation.find('hl7:effectiveTime', namespaces).get(
                            'value') if observation.find(
                            'hl7:effectiveTime', namespaces) else '/'
                        value = observation.find('hl7:value', namespaces)
                        com_dict[name] = parse_value(value) if value is not None else '/'

                        entryships = observation.findall('hl7:entryRelationship', namespaces)
                        for er in entryships:
                            er_name = er.find('hl7:observation/hl7:code', namespaces).get('displayName')
                            er_value = er.find('hl7:observation/hl7:value', namespaces)
                            com_dict[er_name] = parse_value(er_value) if er_value is not None else '/'
                elif entry.find('hl7:act', namespaces) is not None:
                    if code == '8648-8':
                        # 住院过程章节
                        com_dict['出院病房'] = entry.find('hl7:act/hl7:author/hl7:assignedAuthor/hl7:representedOrganization/hl7:name', namespaces).text if entry.find('hl7:act/hl7:author/hl7:assignedAuthor/hl7:representedOrganization/hl7:name', namespaces) is not None else '/'
                        com_dict['出院科室'] = entry.find('hl7:act/hl7:author/hl7:assignedAuthor/hl7:representedOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name', namespaces).text if entry.find('hl7:act/hl7:author/hl7:assignedAuthor/hl7:representedOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name', namespaces) is not None else '/'
                    elif code == '48765-2':
                        # 过敏史
                        com_dict['过敏药物'] = entry.find(
                            'hl7:act/hl7:entryRelationship/hl7:observation/hl7:participant/hl7:participantRole/hl7:playingEntity/hl7:desc',
                            namespaces).text if entry.find(
                            'hl7:act/hl7:entryRelationship/hl7:observation/hl7:participant/hl7:participantRole/hl7:playingEntity/hl7:desc',
                            namespaces) is not None else '/'

                    # todo
                elif entry.find('hl7:procedure', namespaces) is not None:
                    procedure = entry.find('hl7:procedure', namespaces)
                    com_dict['时间'] = procedure.find('hl7:effectiveTime', namespaces).get('value') if procedure.find('hl7:effectiveTime', namespaces) is not None else '/'
                    com_dict['手术者编码'] = procedure.find('hl7:performer/hl7:assignedEntity/hl7:id', namespaces).get('extension') if procedure.find('hl7:performer/hl7:assignedEntity', namespaces) is not None else '/'
                    com_dict['手术者姓名'] = procedure.find('hl7:performer/hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces).text if procedure.find('hl7:performer/hl7:assignedEntity', namespaces) is not None else '/'

                    participants = procedure.findall('hl7:participant', namespaces)
                    for p in participants:
                        name = p.find('hl7:participantRole/hl7:playingEntity/hl7:name', namespaces).text
                        displayName = p.find('hl7:participantRole/hl7:code', namespaces).get('displayName')
                        if name is not None and displayName is not None:
                            com_dict[displayName] = name

                    entryRelationships = procedure.findall('hl7:entryRelationship', namespaces)
                    for e in entryRelationships:
                        e_name = e.find('hl7:observation/hl7:code', namespaces).get('displayName')
                        e_value = e.find('hl7:observation/hl7:value', namespaces)
                        com_dict[e_name] = parse_value(e_value) if e_value is not None else '/'
                else:
                    observation = entry.find('hl7:observation', namespaces)
                    if observation is None:
                        continue

                    # 转科科室特殊处理
                    if observation.find('hl7:author', namespaces) is not None and code == '42349-1':
                        com_dict['转科科室名'] = observation.find('hl7:author/hl7:assignedAuthor/hl7:representedOrqanization/hl7:name/', namespaces).text if observation.find(
                            'hl7:author/hl7:assignedAuthor/hl7:representedOrqanization/hl7:name/', namespaces) is not None else '/'
                        continue

                    name = observation.find('hl7:code', namespaces).get('displayName')
                    entry_dict['time'] = observation.find('hl7:effectiveTime', namespaces).get('value') if observation.find(
                        'hl7:effectiveTime', namespaces) else '/'
                    value = observation.find('hl7:value', namespaces)
                    com_dict[name] = parse_value(value) if value is not None else '/'

                    entryships = observation.findall('hl7:entryRelationship', namespaces)
                    for er in entryships:
                        er_name = er.find('hl7:observation/hl7:code', namespaces).get('displayName')
                        er_value = er.find('hl7:observation/hl7:value', namespaces)
                        com_dict[er_name] = parse_value(er_value) if er_value is not None else '/'

                    authors = observation.findall('hl7:author', namespaces)
                    for a in authors:
                        a_name = a.find('hl7:assignedAuthor/hl7:code', namespaces).get('displayName')
                        a_value = a.find('hl7:assignedAuthor/hl7:assignedPerson/hl7:name', namespaces).text
                        com_dict[a_name] = a_value

            parse_data[component_name.get(key, '/')] = com_dict
    return parse_data


def parse_value(value):
    ret = ''
    if value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ST':
        ret = value.text
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BL':
        ret = value.get('value')
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'PQ':
        ret = value.get('value') + ' ' + value.get('unit')
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'INT':
        ret = value.get('value')
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'CD':
        ret = value.get('code')
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'TS':
        ret = value.get('value')
    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'MO':
        ret = value.get('value') + ' ' + value.get('currency')
    else:
        print('===> 未知 value 类型', value.get('{http://www.w3.org/2001/XMLSchema-instance}type'))
    return ret


component_name = {
    '10154-3': '主诉',
    '10164-2': '现病史',
    '11348-0': '既往史',
    '11369-6': '预防接种史',
    '56836-0': '输血史',
    '29762-2': '个人史',
    '49033-4': '月经史',
    '10157-6': '家族史',
    '8716-3': '生命体征',
    '29545-1': '体格检査',
    '辅助检查': '辅助检查',
    '11450-4': '主要健康问题',
    '18776-5': '治疗计划',
    '29548-5': '诊断章节',
    '42349-1': '转科记录',
    '11535-2': '出院诊断',
    '48765-2': '过敏史',
    '30954-2': '实验室检查',
    '47519-4': '手术操作',
    '11336-5': '住院史',
    '8648-8': '住院过程',
    '48768-6': '费用章节',
    '行政管理': '行政管理',
    '46241-6': '入院诊断',
    '46209-3': '医嘱(用药)章节',

}


if __name__ == '__main__':
    # parse_data = parse_cda_xml_document_by_file('/Users/gaoyanliang/nsyy/病历解析/住院病案首页.xml')
    # parse_data = parse_cda_xml_document_by_file('/Users/gaoyanliang/nsyy/病历解析/病程记录/首次病程记录.xml')
    # parse_data = parse_cda_xml_document_by_file('/Users/gaoyanliang/nsyy/病历解析/出院记录/出院记录文档示例.xml')
    parse_data = parse_cda_xml_document_by_file('/Users/gaoyanliang/nsyy/病历解析/入院记录/入院记录文档示例.xml')

    # 将 Python 对象转换为格式化的 JSON 字符串
    formatted_json = json.dumps(parse_data, indent=4, ensure_ascii=False)
    print(formatted_json)















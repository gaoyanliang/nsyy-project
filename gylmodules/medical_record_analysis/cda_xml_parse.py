import json
import xml.etree.ElementTree as ET
import re
import os

"""
解析 cda xml 文件
"""


def parse_cda_xml_document(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    parse_data = {}

    # 设置命名空间
    namespaces = {'hl7': 'urn:hl7-org:v3'}
    schema = {'schema': '{http://www.w3.org/2001/XMLSchema-instance}'}

    # ======================= 解析 header =======================
    parse_data['title'] = root.find('hl7:title', namespaces).text if root.find('hl7:title',
                                                                               namespaces) is not None else '/'
    parse_data['文档编码'] = root.find('hl7:id', namespaces).get('extension') if root.find('hl7:id',
                                                                                           namespaces) is not None else '/'
    parse_data['文档生成时间'] = root.find('hl7:effectiveTime', namespaces).get('value')

    # 文档记录对象
    patient_role = root.find('hl7:recordTarget/hl7:patientRole', namespaces)
    if patient_role:
        parse_data['住院号'] = patient_role.find('hl7:id', namespaces).get('extension') if patient_role.find('hl7:id',
                                                                                                             namespaces) is not None else '/'
        parse_data['addr_house'] = patient_role.find('hl7:addr/hl7:houseNumber', namespaces).text if patient_role.find(
            'hl7:addr/hl7:houseNumber', namespaces) is not None else '/'
        parse_data['addr_street'] = patient_role.find('hl7:addr/hl7:streetName', namespaces).text if patient_role.find(
            'hl7:addr/hl7:streetName', namespaces) is not None else '/'
        parse_data['addr_town'] = patient_role.find('hl7:addr/hl7:township', namespaces).text if patient_role.find(
            'hl7:addr/hl7:township', namespaces) is not None else '/'
        parse_data['addr_county'] = patient_role.find('hl7:addr/hl7:county', namespaces).text if patient_role.find(
            'hl7:addr/hl7:county', namespaces) is not None else '/'
        parse_data['addr_city'] = patient_role.find('hl7:addr/hl7:city', namespaces).text if patient_role.find(
            'hl7:addr/hl7:city', namespaces) is not None else '/'
        parse_data['addr_state'] = patient_role.find('hl7:addr/hl7:state', namespaces).text if patient_role.find(
            'hl7:addr/hl7:state', namespaces) is not None else '/'

        parse_data['患者身份证号'] = patient_role.find('hl7:patient/hl7:id', namespaces).get(
            'extension') if patient_role.find('hl7:patient/hl7:id', namespaces) is not None else '/'
        parse_data['患者姓名'] = patient_role.find('hl7:patient/hl7:name', namespaces).text if patient_role.find(
            'hl7:patient/hl7:name', namespaces) is not None else '/'
        parse_data['患者性别编码'] = patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces) is not None else '/'
        parse_data['患者性别'] = patient_role.find('hl7:patient/hl7:administrativeGenderCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:administrativeGenderCode',
                                                namespaces) is not None else '/'

        parse_data['患者婚姻状况编码'] = patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces) is not None else '/'
        parse_data['患者婚姻状况'] = patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:maritalStatusCode', namespaces) is not None else '/'
        parse_data['患者民族编码'] = patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces) is not None else '/'
        parse_data['患者民族'] = patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:ethnicGroupCode', namespaces) is not None else '/'

        parse_data['患者年龄'] = patient_role.find('hl7:patient/hl7:age', namespaces).get(
            'value') if patient_role.find('hl7:patient/hl7:age', namespaces) is not None else '/'
        parse_data['患者职业编码'] = patient_role.find('hl7:patient/hl7:occupation/hl7:occupationCode', namespaces).get(
            'code') if patient_role.find('hl7:patient/hl7:occupation', namespaces) is not None and patient_role.find(
            'hl7:patient/hl7:occupation/hl7:occupationCode', namespaces) is not None else '/'
        parse_data['患者职业'] = patient_role.find('hl7:patient/hl7:occupation/hl7:occupationCode', namespaces).get(
            'displayName') if patient_role.find('hl7:patient/hl7:occupation',
                                                namespaces) is not None and patient_role.find(
            'hl7:patient/hl7:occupation/hl7:occupationCode', namespaces) is not None else '/'

    # 文档创作者
    author = root.find('hl7:author', namespaces)
    if author:
        parse_data['文档创作时间'] = author.find('hl7:author/hl7:time', namespaces).get('value') if author.find(
            'hl7:author/hl7:time', namespaces) is not None else '/'
        parse_data['文档创作者id'] = author.find('hl7:author/hl7:assignedAuthor/hl7:id', namespaces).get(
            'extension') if author.find('hl7:author/hl7:assignedAuthor/hl7:id', namespaces) is not None else '/'
        parse_data['文档创作者id'] = author.find('hl7:author/hl7:assignedAuthor/hl7:assignedAuthor/hl7:name',
                                                 namespaces).text if author.find(
            'hl7:author/hl7:assignedAuthor/hl7:assignedAuthor/hl7:name', namespaces) is not None else '/'

    # 病史陈述者
    informant = root.find('hl7:informant', namespaces)
    if informant:
        parse_data['陈述者身份证号'] = informant.find('hl7:assignedEntity/hl7:id', namespaces).get(
            'extension') if informant.find('hl7:assignedEntity/hl7:id', namespaces) is not None else '/'
        parse_data['陈述者与患者关系代码'] = informant.find('hl7:assignedEntity/hl7:code', namespaces).get(
            'code') if informant.find('hl7:assignedEntity/hl7:code', namespaces) is not None else '/'
        parse_data['陈述者与患者关系'] = informant.find('hl7:assignedEntity/hl7:code', namespaces).get(
            'displayName') if informant.find('hl7:assignedEntity/hl7:code', namespaces) is not None else '/'
        parse_data['陈述者姓名'] = informant.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces).text \
            if informant.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces) is not None else '/'

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
            parse_data[name + '名称'] = au.find('hl7:assignedEntity/hl7:assignedPerson/hl7:name', namespaces).text

    # 病床号、病房、病区、科室和医院的关联
    component_of = root.find('hl7:componentOf', namespaces)
    if component_of:
        ee = component_of.find('hl7:encompassingEncounter', namespaces)
        parse_data['入院时间'] = ee.find('hl7:effectiveTime', namespaces).get('value')
        parse_data['病床编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension')
        parse_data['病床'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text
        parse_data['病房编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension')
        parse_data['病房'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text
        parse_data['科室编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension')
        parse_data['科室'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text
        parse_data['病区编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension')
        parse_data['病区'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text
        parse_data['医院编码'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:id',
            namespaces).get('extension')
        parse_data['医院'] = ee.find(
            'hl7:location/hl7:healthCareFacility/hl7:serviceProviderOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:asOrganizationPartOf/hl7:wholeOrganization/hl7:name',
            namespaces).text

    # ======================= 解析 body =======================
    component = root.find('hl7:component', namespaces)
    if component:
        components = component.findall('hl7:structuredBody/hl7:component', namespaces)
        for item in components:
            code = item.find('hl7:section/hl7:code', namespaces)
            # 主诉
            if code.get('code') in ('10154-3', '10164-2', '11369-6', '56836-0', '29762-2', '49033-4', '10157-6') or name == '辅助检查':
                name = item.find('hl7:section/hl7:entry/hl7:observation/hl7:code', namespaces).get('displayName')
                parse_data[name + 'text'] = item.find('hl7:section/hl7:text', namespaces).text if item.find('hl7:section/hl7:text', namespaces).text else '/'
                value = item.find('hl7:section/hl7:entry/hl7:observation/hl7:value', namespaces)
                if value is not None:
                    if value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ST':
                        parse_data[name + 'value'] = value.text
                    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BL':
                        parse_data[name + 'value'] = value.get('value')
                    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'PQ':
                        parse_data[name + 'value'] = value.get('value') + ' ' + value.get('unit')
                    elif value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'INT':
                        parse_data[name + 'value'] = value.get('value')
                    else:
                        print('===> 未知 value 类型')
            elif code.get('code') in ('8716-3', '29545-1', '11348-0', '11450-4'):
                if code.get('code') == '8716-3':
                    # 生命体征
                    parse_data['生命体征text'] = item.find('hl7:section/hl7:text', namespaces).text if item.find(
                        'hl7:section/hl7:text', namespaces).text else '/'
                elif code.get('code') == '29545-1':
                    # 体格检查
                    parse_data['体格检查text'] = item.find('hl7:section/hl7:text', namespaces).text if item.find(
                        'hl7:section/hl7:text', namespaces).text else '/'
                elif code.get('code') == '11348-0':
                    # 既往史
                    parse_data['既往史text'] = item.find('hl7:section/hl7:text', namespaces).text if item.find(
                        'hl7:section/hl7:text', namespaces).text else '/'
                elif code.get('code') == '11450-4':
                    # 主要健康问题
                    parse_data['主要健康问题text'] = item.find('hl7:section/hl7:text', namespaces).text if item.find(
                        'hl7:section/hl7:text', namespaces).text else '/'

                entrys = item.findall('hl7:section/hl7:entry', namespaces)
                for entry in entrys:
                    observation = entry.find('hl7:observation', namespaces)
                    if observation is not None:
                        code = observation.find('hl7:code', namespaces).get('code')
                        if code == 'DE05.01.025.00':
                            parse_data['西医诊断时间'] = observation.find('hl7:effectiveTime', namespaces).get('value')
                        elif code == 'DE05.10.172.00':
                            parse_data['中医诊断时间'] = observation.find('hl7:effectiveTime', namespaces).get('value')

                        entry_key = observation.find('hl7:code', namespaces).get('displayName')
                        entry_value = observation.find('hl7:value', namespaces)
                        if entry_value is not None and entry_key is not None:
                            if entry_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ST':
                                parse_data[entry_key] = entry_value.text
                            elif entry_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BL':
                                parse_data[entry_key] = entry_value.get('value')
                            elif entry_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'PQ':
                                parse_data[entry_key] = entry_value.get('value') + ' ' + entry_value.get('unit')
                            elif entry_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'INT':
                                parse_data[entry_key] = entry_value.get('value')
                            elif entry_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'CD':
                                parse_data[entry_key] = entry_value.get('code')
                            else:
                                print('===> 未知 value 类型')

                        ships = observation.findall('hl7:entryRelationship', namespaces)
                        if ships is not None:
                            for ship in ships:
                                ship_key = ship.find('hl7:observation/hl7:code', namespaces).get('displayName')
                                ship_value = ship.find('hl7:observation/hl7:value', namespaces)
                                if ship_value is not None and ship_key is not None:
                                    if ship_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ST':
                                        parse_data[ship_key] = ship_value.text
                                    elif ship_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BL':
                                        parse_data[ship_key] = ship_value.get('value')
                                    elif ship_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'PQ':
                                        parse_data[ship_key] = ship_value.get('value') + ' ' + ship_value.get('unit')
                                    elif ship_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'INT':
                                        parse_data[ship_key] = ship_value.get('value')
                                    elif ship_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'CD':
                                        parse_data[ship_key] = ship_value.get('code')
                                    else:
                                        print('===> 未知 value 类型')
                    else:
                        organizer = entry.find('hl7:organizer', namespaces)
                        if organizer is not None:
                            components = organizer.findall('hl7:component', namespaces)
                            for component in components:
                                component_key = component.find('hl7:observation/hl7:code', namespaces).get('displayName')
                                component_value = component.find('hl7:observation/hl7:value', namespaces)
                                if component_value is not None and component_key is not None:
                                    if component_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ST':
                                        parse_data[component_key] = component_value.text
                                    elif component_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BL':
                                        parse_data[component_key] = component_value.get('value')
                                    elif component_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'PQ':
                                        parse_data[component_key] = component_value.get('value') + ' ' + component_value.get('unit')
                                    elif component_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'INT':
                                        parse_data[component_key] = component_value.get('value')
                                    elif component_value.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'CD':
                                        parse_data[component_key] = component_value.get('code')
                                    else:
                                        print('===> 未知 value 类型')

    return parse_data


if __name__ == '__main__':
    parse_data = parse_cda_xml_document('/Users/gaoyanliang/nsyy/病历解析/入院记录/入院记录文档示例.xml')

    # 将 Python 对象转换为格式化的 JSON 字符串
    formatted_json = json.dumps(parse_data, indent=4, ensure_ascii=False)
    print(formatted_json)

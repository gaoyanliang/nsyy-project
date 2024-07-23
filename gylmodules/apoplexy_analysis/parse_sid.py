import xml.etree.ElementTree as ET
import os


section_info = {}
sid_info = {}
exception_sid = {}
all_sid_dict = {}
sid_set = set()
# 验证 document - element 中的 sid 是否统一
def document_section(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    header = root.find('./document')

    for section in header.findall('section'):
        section_sid = section.get('sid') if section.get('sid') else section.get('iid')
        title = section.get('title').replace(' ', '')

        section_info[title] = section_sid
        sid_info[section_sid] = title

        section_sid_set = set()
        if section_sid in all_sid_dict:
            sid_dict = all_sid_dict[section_sid]
        else:
            sid_dict = {'sid': section_sid, 'title': title, 'child': {}}

        for item in section:
            if ('sid' in item.attrib or 'iid' in item.attrib) and 'title' in item.attrib:
                sid = item.get('sid') if item.get('sid') else item.get('iid')
                title = item.get('title').replace(' ', '')

                if sid is None or title.__contains__('单击这里选择职称') or title.__contains__('报告卡编码') or item.tag == 'patisign' or title.__contains__('输入内容'):
                    continue

                if sid in sid_info and sid_info[sid] != title:
                    exception_sid[sid] = { "sid": sid, "title1": title, "title2": sid_info[sid]}

                if sid in section_sid_set:
                    continue
                section_sid_set.add(sid)
                section_info[title] = sid
                sid_info[sid] = title
                sid_dict['child'][sid] = {'sid': sid, 'title': title, 'child': {}}

                if item.tag == 'group':
                    for group in item.findall('group'):
                        for ite in group:
                            if ite.tag == 'e_enum':
                                group_sid = ite.get('sid') if ite.get('sid') else ite.get('iid')
                                group_title = ite.get('title').replace(' ', '')

                                if group_sid is None or group_title.__contains__('单击这里选择职称') or group_title.__contains__(
                                        '报告卡编码') or ite.tag == 'patisign':
                                    continue

                                if group_sid in sid_info and sid_info[group_sid] != group_title:
                                    exception_sid[group_sid] = {"sid": group_sid, "title1": group_title, "title2": sid_info[group_sid]}

                                if group_sid in section_sid_set:
                                    continue
                                section_sid_set.add(group_sid)
                                section_info[group_title] = group_sid
                                sid_info[group_sid] = group_title
                                sid_dict['child'][sid]['child'][group_sid] = {'sid': group_sid, 'title': group_title}

        all_sid_dict[section_sid] = sid_dict


if __name__ == '__main__':
    directory = '/Users/gaoyanliang/nsyy/病历解析/入院记录/bingli/'
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".xml"):
                document_section(os.path.join(root, file))

    # sid 列表
    # index = 1
    # for key, value in section_info.items():
    #     print(index, key, value)
    #     index += 1

    # index = 1
    # for key, value in sid_info.items():
    #     print(index, key, value)
    #     index += 1
    print(sid_info)


    # 有层次机构的 sid 列表
    # for _, item in all_sid_dict.items():
    #     print(item)

    # 异常 sid (sid 相同 title 不同)
    print('---------------------------------')
    for _, value in exception_sid.items():
        print(value)


import xml.etree.ElementTree as ET
from datetime import datetime

from gylmodules import global_tools


def simplify_node(node):
    children = list(node)

    # 没有子节点
    if not children:
        text = (node.text or '').strip()
        return text if text else None

    # 有子节点
    simplified = {}
    value_parts = []

    if node.text and node.text.strip():
        value_parts.append(node.text.strip())

    for child in children:
        child_name = child.get('name')
        simplified[child_name] = simplify_node(child)
        if isinstance(simplified[child_name], str) and simplified[child_name].strip():
            value_parts.append(f"{child_name} {simplified[child_name].strip()}")

        if child.tail and child.tail.strip():
            value_parts.append(child.tail.strip())

    simplified['value'] = ' '.join(value_parts).strip()
    return simplified


def main_parse_func(xml_string, to_print: bool = True):
    root = ET.fromstring(xml_string)
    result = {}

    for node in root:
        if node.tag != "node":
            continue
        name = node.get("name")
        simplified = simplify_node(node)
        result[name] = simplified

    if to_print:
        # 打印结果
        import json
        print(json.dumps(result, ensure_ascii=False, indent=4))

    return result


if __name__ == "__main__":
    sql = """
            select wb2.wenjiannr ,wb.binglimc, wb.binglijlid from df_bingli.ws_binglijl wb
        join df_bingli.ws_binglijlnr wb2 on wb.binglijlid =wb2.binglijlid
        and wb.zuofeibz ='0' where wb.binglimc like '%入院记录%'and jilusj > '2025-01-01 00:00:00'  LIMIT 300
    """
    record_data = global_tools.call_new_his_pg(sql)
    print('病历数量： ', len(record_data))

    key_set = set()
    for data in record_data:
        try:
            result = main_parse_func(data.get('wenjiannr'), False)
            for k, _ in result.items():
                key_set.add(k)
        except Exception as e:
            print(data, e)

    for k in key_set:
        print(k)




import xml.etree.ElementTree as ET

from gylmodules import global_config
from gylmodules.utils.db_utils import DbUtil

# Open the XML file with the appropriate encoding
# with open('/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/101.xml', 'r', encoding='gb2312') as file:

file_list = ['/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/1.xml',
             '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/101.xml',
             '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/201.xml',
             '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/301.xml',
             '/Users/gaoyanliang/nsyy/综合预约/门诊医生挂号费用/401.xml']

db = DbUtil(global_config.DB_HOST, global_config.DB_USERNAME, global_config.DB_PASSWORD,
            global_config.DB_DATABASE_GYL)

my_set = set()
my_set1 = set()
items = {}
for file_path in file_list:

    with open(file_path, 'r', encoding='gb2312', errors='ignore') as file:
        xml_data = file.read()
    root = ET.fromstring(xml_data)

    for item in root.findall('.//Item'):
        price = "%.4f" % float(item.find('Price').text)
        json_data = {
            'appointment_id': int(item.find('AsRowid').text),
            'dept_id': int(item.find('DepID').text),
            'dept_name': item.find('DepName').text.strip(),
            'doctor_id': int(item.find('MarkId').text),
            'doctor_name': item.find('MarkDesc').text.strip(),
            'doctor_type': item.find('SessionType').text.strip(),
            'price': price,
        }
        # print(json_data)
        set_data = tuple(json_data.items())
        if set_data in my_set:
            continue
        my_set.add(set_data)

        copy_data = json_data.copy()
        copy_data.pop('price')
        copy_data.pop('doctor_type')
        copy_data.pop('appointment_id')
        copy_data = tuple(copy_data.items())

        if copy_data in my_set1:
            val = items[copy_data]
            if price > val.get('price'):
                items[copy_data] = json_data
        else:
            items[copy_data] = json_data
            my_set1.add(copy_data)


for _, json_data in items.items():
    fileds = ','.join(json_data.keys())
    args = str(tuple(json_data.values()))
    insert_sql = f"INSERT INTO nsyy_gyl.appt_doctor_info ({fileds}) VALUES {args}"
    last_rowid = db.execute(sql=insert_sql, need_commit=True)
    if last_rowid == -1:
        del db
        raise Exception("入库失败! sql = " + insert_sql)




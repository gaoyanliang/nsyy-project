"""
电子健康卡 接口入参
"""

# 电子健康卡服务地址
ehc_url = 'http://192.168.3.105:9001/ErhcService.asmx?wsdl'
# 组织机构代码
organizationNumber = '524113004190430778'
# 终端类型
platformType = '4'
# 终端编号 - 正式环境
equipmentNumber_prod = 'NY_NSYY_HIS'
# 终端编号 - 测试环境
equipmentNumber_test = 'nsyy0001'
# debug 模式（true 使用测试环境/ false 使用正式环境）
is_debug = False


# 申领前验证用户是否存在1001 根据身份证号查询
check_ehc_by_id = "<Request>" \
        "<tranCode>1001</tranCode>" \
        "<equipmentNumber>{equipmentNumber}</equipmentNumber>" \
        "<platformType>{platformType}</platformType>" \
        "<organizationNumber>{organizationNumber}</organizationNumber>" \
        "<ehcId/>" \
        "<idCardType>01</idCardType>" \
        "<idCardNum>{idCardNum}</idCardNum>" \
        "</Request>"

# 申领前验证用户是否存在1001 根据电子健康卡号查询
check_ehc_by_ehcId = "<Request>" \
        "<tranCode>1001</tranCode>" \
        "<equipmentNumber>{equipmentNumber}</equipmentNumber>" \
        "<platformType>{platformType}</platformType>" \
        "<organizationNumber>{organizationNumber}</organizationNumber>" \
        "<ehcId>{ehcId}</ehcId>" \
        "</Request>"

# 测试 - 申领电子健康卡 1002
create_ehc = "<Request> " \
        "<tranCode>1002</tranCode>" \
        "<equipmentNumber>{equipmentNumber}</equipmentNumber>" \
        "<platformType>{platformType}</platformType>" \
        "<organizationNumber>{organizationNumber}</organizationNumber>" \
        "<apply_type>{apply_type}</apply_type>" \
        "<userName>{userName}</userName>" \
        "<telephone>{telephone}</telephone>" \
        "<idCardType>01</idCardType>" \
        "<idCardNum>{idCardNum}</idCardNum>" \
        "<currentAddress>{currentAddress}</currentAddress>" \
        "<domicileAddress>{domicileAddress}</domicileAddress>" \
        "</Request>"

# 测试 - 修改用户信息1003
param3 = "<Request>" \
        "<tranCode>1003</tranCode>" \
        "<equipmentNumber>NY_NSYY_HIS</equipmentNumber>" \
        "<platformType>4</platformType>" \
        "<organizationNumber>524113004190430778</organizationNumber>" \
        "<ehcId>3DF32E3F25B54C48115D36A035927A5A37943FCB759E180F1379927013615A21</ehcId>" \
        "<cellphone>13027751873</cellphone>" \
        "<telephone>13027751873</telephone>" \
        "<currentAddress>河南南阳</currentAddress>" \
        "<domicileAddress>河南省南阳市镇平县</domicileAddress>" \
        "</Request>"

# 测试 - 用户注销1004
param4 = "<Request>" \
        "<tranCode>1005</tranCode>" \
        "<equipmentNumber>NY_NSYY_HIS</equipmentNumber>" \
        "<platformType>4</platformType>" \
        "<organizationNumber>524113004190430778</organizationNumber>" \
        "<ehcId>3DF32E3F25B54C48115D36A035927A5A37943FCB759E180F1379927013615A21</ehcId>" \
        "</Request>"

# 测试 - 二维码获取用户信息1005
param5 = "<Request>" \
        "<tranCode>1005</tranCode>" \
        "<equipmentNumber>NY_NSYY_HIS</equipmentNumber>" \
        "<platformType>4</platformType>" \
        "<organizationNumber>524113004190430778</organizationNumber>" \
        "<qrCode>3DF32E3F25B54C48115D36A035927A5A37943FCB759E180F1379927013615A21:0:09EB2883E5D4599F07E8BF5B49AD7D38:NY_NSYY_HIS</qrCode>" \
        "</Request>"

# 测试 - 申领二维码1006
param6 = "<Request>" \
        "<tranCode>1006</tranCode>" \
        "<equipmentNumber>NY_NSYY_HIS</equipmentNumber>" \
        "<platformType>4</platformType>" \
        "<organizationNumber>524113004190430778</organizationNumber>" \
        "<ehcId>3DF32E3F25B54C48115D36A035927A5A37943FCB759E180F1379927013615A21</ehcId>" \
        "<qrCodeType>2</qrCodeType>" \
        "<idCardType>01</idCardType>" \
        "<idCardNum>411324199605164530</idCardNum>" \
        "</Request>"

# 测试 - 动态二维码校验1007
param7 = "<Request>" \
        "<tranCode>1007</tranCode>" \
        "<equipmentNumber>NY_NSYY_HIS</equipmentNumber>" \
        "<platformType>4</platformType>" \
        "<organizationNumber>524113004190430778</organizationNumber>" \
        "<qrCode>3DF32E3F25B54C48115D36A035927A5A37943FCB759E180F1379927013615A21:0:2005AA7F6B9A9DC87586BB02F25FA299:NY_NSYY_HIS</qrCode>" \
        "<usecardScene>010401</usecardScene>" \
        "<userName>高彦良</userName>" \
        "<idCardType>01</idCardType>" \
        "<idCardNum>411324199605164530</idCardNum>" \
        "<payChannel>10000106</payChannel>" \
        "</Request>"

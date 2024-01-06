from utils.unified_logger import UnifiedLogger
from suds.client import Client
import sport_mng.ehc_config as ehc_config

log = UnifiedLogger()

"""
电子健康卡信息管理
"""


class ElecHealthCard:
    def __init__(self):
        log.info("初始化电子健康卡管理服务")
        self.client = Client(ehc_config.ehc_url)
        print(self.client)

    def get_info_by_id(self, id_card_num):
        """
        根据身份证号查询电子健康卡信息
        :param id_card_num: 身份证号
        :return:
        """
        param = ''
        if ehc_config.is_debug:
            param = ehc_config.check_ehc_by_id.format(equipmentNumber=ehc_config.equipmentNumber_test,
                                                      platformType=ehc_config.platformType,
                                                      organizationNumber=ehc_config.organizationNumber,
                                                      idCardNum=id_card_num)
        else:
            param = ehc_config.check_ehc_by_id.format(equipmentNumber=ehc_config.equipmentNumber_prod,
                                                      platformType=ehc_config.platformType,
                                                      organizationNumber=ehc_config.organizationNumber,
                                                      idCardNum=id_card_num)
        try:
            res = self.client.service.CallService(param)
            log.debug("根据 id_card_num: " + id_card_num + " 查询电子健康卡信息结果为: " + res)
            return res
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return None

    def get_info_by_ehc_id(self, ehc_id):
        """
        根据电子健康卡号查询电子健康卡信息
        :param ehc_id: 电子健康卡号
        :return:
        """
        param = ''
        if ehc_config.is_debug:
            param = ehc_config.check_ehc_by_ehcId.format(equipmentNumber=ehc_config.equipmentNumber_test,
                                                         platformType=ehc_config.platformType,
                                                         organizationNumber=ehc_config.organizationNumber,
                                                         idCardNum=ehc_id)
        else:
            param = ehc_config.check_ehc_by_ehcId.format(equipmentNumber=ehc_config.equipmentNumber_prod,
                                                         platformType=ehc_config.platformType,
                                                         organizationNumber=ehc_config.organizationNumber,
                                                         ehcId=ehc_id)
        try:
            res = self.client.service.CallService(param)
            log.debug("根据 ehc_id: " + ehc_id + " 查询电子健康卡信息结果为: " + res)
            return res
        except Exception as e:
            print(f"电子健康卡验证失败, An unexpected error occurred: {e}")
        return None

    def gov_id_create(self, apply_type, user_name, telephone, id_card_num, current_address, domicile_address):
        """
        创建电子健康卡
        :param apply_type: 申请方式
        :param user_name: 用户名
        :param telephone: 联系电话
        :param id_card_num: 身份证号
        :param current_address: 现住址
        :param domicile_address: 户籍住址
        :return:
        """
        param = ''
        if ehc_config.is_debug:
            param = ehc_config.create_ehc.format(equipmentNumber=ehc_config.equipmentNumber_test,
                                                 platformType=ehc_config.platformType,
                                                 organizationNumber=ehc_config.organizationNumber,
                                                 apply_type=apply_type,
                                                 userName=user_name,
                                                 telephone=telephone,
                                                 idCardNum=id_card_num,
                                                 currentAddress=current_address,
                                                 domicileAddress=domicile_address)
        else:
            param = ehc_config.create_ehc.format(equipmentNumber=ehc_config.equipmentNumber_prod,
                                                 platformType=ehc_config.platformType,
                                                 organizationNumber=ehc_config.organizationNumber,
                                                 apply_type=apply_type,
                                                 userName=user_name,
                                                 telephone=telephone,
                                                 idCardNum=id_card_num,
                                                 currentAddress=current_address,
                                                 domicileAddress=domicile_address)
        try:
            res = self.client.service.CallService(param)
            log.debug("电子健康卡申领结果为: " + res)
            return res
        except Exception as e:
            print(f"电子健康卡申领异常, An unexpected error occurred: {e}")
        return None

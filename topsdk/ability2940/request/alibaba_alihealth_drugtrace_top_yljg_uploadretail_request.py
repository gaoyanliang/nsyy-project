from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgUploadretailRequest(BaseRequest):

    def __init__(
        self,
        bill_code: str = None,
        bill_time: datetime = None,
        bill_type: int = None,
        physic_type: int = None,
        ref_user_id: str = None,
        from_user_id: str = None,
        oper_ic_code: str = None,
        oper_ic_name: str = None,
        trace_codes: list = None,
        customer_id_type: str = None,
        customer_id: str = None,
        user_tel: str = None,
        network_bill_flag: str = None,
        medic_doctor: str = None,
        medic_dispenser: str = None,
        user_name: str = None,
        user_agent: str = None,
        remarks: str = None,
        ignore_part_success_flag: str = None
    ):
        """
            单据编号（唯一）
        """
        self._bill_code = bill_code
        """
            单据时间（一般为药品入出库时间）
        """
        self._bill_time = bill_time
        """
            单据类型[323,零售出库(后修改为使用出库)][322,疫苗接种][116,消费者退货入库]
        """
        self._bill_type = bill_type
        """
            药品类型[2,特药，3,普药]【可以随便填写，单据上传后会以实际为准】
        """
        self._physic_type = physic_type
        """
            上传单据的医疗机构在码上放心平台的ref_ent_id，可通过“通过企业名得到唯一标识”接口获取
        """
        self._ref_user_id = ref_user_id
        """
            发货企业(可为空)
        """
        self._from_user_id = from_user_id
        """
            单据提交者(appkey编号、可为空)
        """
        self._oper_ic_code = oper_ic_code
        """
            单据提交者姓名（可为空）
        """
        self._oper_ic_name = oper_ic_name
        """
            追溯码【多个码时用逗号拼接的字符串。要求数量在3500个码以下，但一般不要传这么多，如果网络不好很容易传输一半报错】；注意：在同一张单据里，不能有重复的码；在同一张单据中不能同时上传有关联关系的大、小码；
        """
        self._trace_codes = trace_codes
        """
            购买人证件类型【1身份证2护照3 军官证4 医保卡5接种卡6学生证9其它】
        """
        self._customer_id_type = customer_id_type
        """
            购买人证件编号
        """
        self._customer_id = customer_id
        """
            用药人电话
        """
        self._user_tel = user_tel
        """
            互联标识 1是  0否
        """
        self._network_bill_flag = network_bill_flag
        """
            处方医师
        """
        self._medic_doctor = medic_doctor
        """
            发药人
        """
        self._medic_dispenser = medic_dispenser
        """
            患者（姓名、院内患者ID均可）
        """
        self._user_name = user_name
        """
            代理领药人
        """
        self._user_agent = user_agent
        """
            备注
        """
        self._remarks = remarks
        """
            码解析策略,1代表整单解析成功(任一码解析失败，上传时整单返回错误),传其他值或者不传代表部分解析成功(跳过无法解析的码，其余正常处理并上传)
        """
        self._ignore_part_success_flag = ignore_part_success_flag

    @property
    def bill_code(self):
        return self._bill_code

    @bill_code.setter
    def bill_code(self, bill_code):
        if isinstance(bill_code, str):
            self._bill_code = bill_code
        else:
            raise TypeError("bill_code must be str")
    @property
    def bill_time(self):
        return self._bill_time

    @bill_time.setter
    def bill_time(self, bill_time):
        if isinstance(bill_time, datetime):
            self._bill_time = bill_time
        else:
            raise TypeError("bill_time must be datetime")
    @property
    def bill_type(self):
        return self._bill_type

    @bill_type.setter
    def bill_type(self, bill_type):
        if isinstance(bill_type, int):
            self._bill_type = bill_type
        else:
            raise TypeError("bill_type must be int")
    @property
    def physic_type(self):
        return self._physic_type

    @physic_type.setter
    def physic_type(self, physic_type):
        if isinstance(physic_type, int):
            self._physic_type = physic_type
        else:
            raise TypeError("physic_type must be int")
    @property
    def ref_user_id(self):
        return self._ref_user_id

    @ref_user_id.setter
    def ref_user_id(self, ref_user_id):
        if isinstance(ref_user_id, str):
            self._ref_user_id = ref_user_id
        else:
            raise TypeError("ref_user_id must be str")
    @property
    def from_user_id(self):
        return self._from_user_id

    @from_user_id.setter
    def from_user_id(self, from_user_id):
        if isinstance(from_user_id, str):
            self._from_user_id = from_user_id
        else:
            raise TypeError("from_user_id must be str")
    @property
    def oper_ic_code(self):
        return self._oper_ic_code

    @oper_ic_code.setter
    def oper_ic_code(self, oper_ic_code):
        if isinstance(oper_ic_code, str):
            self._oper_ic_code = oper_ic_code
        else:
            raise TypeError("oper_ic_code must be str")
    @property
    def oper_ic_name(self):
        return self._oper_ic_name

    @oper_ic_name.setter
    def oper_ic_name(self, oper_ic_name):
        if isinstance(oper_ic_name, str):
            self._oper_ic_name = oper_ic_name
        else:
            raise TypeError("oper_ic_name must be str")
    @property
    def trace_codes(self):
        return self._trace_codes

    @trace_codes.setter
    def trace_codes(self, trace_codes):
        if isinstance(trace_codes, list):
            self._trace_codes = trace_codes
        else:
            raise TypeError("trace_codes must be list")
    @property
    def customer_id_type(self):
        return self._customer_id_type

    @customer_id_type.setter
    def customer_id_type(self, customer_id_type):
        if isinstance(customer_id_type, str):
            self._customer_id_type = customer_id_type
        else:
            raise TypeError("customer_id_type must be str")
    @property
    def customer_id(self):
        return self._customer_id

    @customer_id.setter
    def customer_id(self, customer_id):
        if isinstance(customer_id, str):
            self._customer_id = customer_id
        else:
            raise TypeError("customer_id must be str")
    @property
    def user_tel(self):
        return self._user_tel

    @user_tel.setter
    def user_tel(self, user_tel):
        if isinstance(user_tel, str):
            self._user_tel = user_tel
        else:
            raise TypeError("user_tel must be str")
    @property
    def network_bill_flag(self):
        return self._network_bill_flag

    @network_bill_flag.setter
    def network_bill_flag(self, network_bill_flag):
        if isinstance(network_bill_flag, str):
            self._network_bill_flag = network_bill_flag
        else:
            raise TypeError("network_bill_flag must be str")
    @property
    def medic_doctor(self):
        return self._medic_doctor

    @medic_doctor.setter
    def medic_doctor(self, medic_doctor):
        if isinstance(medic_doctor, str):
            self._medic_doctor = medic_doctor
        else:
            raise TypeError("medic_doctor must be str")
    @property
    def medic_dispenser(self):
        return self._medic_dispenser

    @medic_dispenser.setter
    def medic_dispenser(self, medic_dispenser):
        if isinstance(medic_dispenser, str):
            self._medic_dispenser = medic_dispenser
        else:
            raise TypeError("medic_dispenser must be str")
    @property
    def user_name(self):
        return self._user_name

    @user_name.setter
    def user_name(self, user_name):
        if isinstance(user_name, str):
            self._user_name = user_name
        else:
            raise TypeError("user_name must be str")
    @property
    def user_agent(self):
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent):
        if isinstance(user_agent, str):
            self._user_agent = user_agent
        else:
            raise TypeError("user_agent must be str")
    @property
    def remarks(self):
        return self._remarks

    @remarks.setter
    def remarks(self, remarks):
        if isinstance(remarks, str):
            self._remarks = remarks
        else:
            raise TypeError("remarks must be str")
    @property
    def ignore_part_success_flag(self):
        return self._ignore_part_success_flag

    @ignore_part_success_flag.setter
    def ignore_part_success_flag(self, ignore_part_success_flag):
        if isinstance(ignore_part_success_flag, str):
            self._ignore_part_success_flag = ignore_part_success_flag
        else:
            raise TypeError("ignore_part_success_flag must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.uploadretail"

    def to_dict(self):
        request_dict = {}
        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._bill_time is not None:
            request_dict["bill_time"] = convert_basic(self._bill_time)

        if self._bill_type is not None:
            request_dict["bill_type"] = convert_basic(self._bill_type)

        if self._physic_type is not None:
            request_dict["physic_type"] = convert_basic(self._physic_type)

        if self._ref_user_id is not None:
            request_dict["ref_user_id"] = convert_basic(self._ref_user_id)

        if self._from_user_id is not None:
            request_dict["from_user_id"] = convert_basic(self._from_user_id)

        if self._oper_ic_code is not None:
            request_dict["oper_ic_code"] = convert_basic(self._oper_ic_code)

        if self._oper_ic_name is not None:
            request_dict["oper_ic_name"] = convert_basic(self._oper_ic_name)

        if self._trace_codes is not None:
            request_dict["trace_codes"] = convert_basic_list(self._trace_codes)

        if self._customer_id_type is not None:
            request_dict["customer_id_type"] = convert_basic(self._customer_id_type)

        if self._customer_id is not None:
            request_dict["customer_id"] = convert_basic(self._customer_id)

        if self._user_tel is not None:
            request_dict["user_tel"] = convert_basic(self._user_tel)

        if self._network_bill_flag is not None:
            request_dict["network_bill_flag"] = convert_basic(self._network_bill_flag)

        if self._medic_doctor is not None:
            request_dict["medic_doctor"] = convert_basic(self._medic_doctor)

        if self._medic_dispenser is not None:
            request_dict["medic_dispenser"] = convert_basic(self._medic_dispenser)

        if self._user_name is not None:
            request_dict["user_name"] = convert_basic(self._user_name)

        if self._user_agent is not None:
            request_dict["user_agent"] = convert_basic(self._user_agent)

        if self._remarks is not None:
            request_dict["remarks"] = convert_basic(self._remarks)

        if self._ignore_part_success_flag is not None:
            request_dict["ignore_part_success_flag"] = convert_basic(self._ignore_part_success_flag)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


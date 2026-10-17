from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgUploadinoutbillRequest(BaseRequest):

    def __init__(
        self,
        bill_code: str = None,
        bill_time: datetime = None,
        bill_type: int = None,
        physic_type: int = None,
        ref_user_id: str = None,
        agent_ref_user_id: str = None,
        from_user_id: str = None,
        to_user_id: str = None,
        dest_user_id: str = None,
        oper_ic_code: str = None,
        oper_ic_name: str = None,
        warehouse_id: str = None,
        drug_id: str = None,
        trace_codes: list = None,
        client_type: str = None,
        return_reason_code: str = None,
        return_reason_des: str = None,
        cancel_reason_code: str = None,
        cancel_reason_des: str = None,
        executer_name: str = None,
        executer_code: str = None,
        superviser_name: str = None,
        superviser_code: str = None,
        from_address: str = None,
        to_address: str = None,
        from_bill_code: str = None,
        order_code: str = None,
        from_person: str = None,
        to_person: str = None,
        dis_ref_ent_id: str = None,
        dis_ent_id: str = None,
        qu_receivable: int = None,
        xt_is_check: str = None,
        xt_check_code: str = None,
        xt_check_code_desc: str = None,
        drug_list_json: str = None,
        ass_ref_ent_id: str = None,
        ass_ent_id: str = None,
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
            单据类型：102代表采购入库、202代表退货出库、205代表销毁出库
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
            代理企业REF标识
        """
        self._agent_ref_user_id = agent_ref_user_id
        """
            发货企业ent_id，可通过“通过企业名得到唯一标识”接口获取；（102采购入库填药品供应商id、202退货出库填医院id、205销毁出库填医院id）
        """
        self._from_user_id = from_user_id
        """
            收货企业ent_id，可通过“通过企业名得到唯一标识”接口获取；（102采购入库填医院id、202退货出库填药品供应商id、205销毁出库填医院id）
        """
        self._to_user_id = to_user_id
        """
            直调企业标识
        """
        self._dest_user_id = dest_user_id
        """
            单据提交者(appkey编号、可为空)  
        """
        self._oper_ic_code = oper_ic_code
        """
            单据提交者姓名（可为空）
        """
        self._oper_ic_name = oper_ic_name
        """
            仓号
        """
        self._warehouse_id = warehouse_id
        """
            已经废弃
        """
        self._drug_id = drug_id
        """
            追溯码【多个码时用逗号拼接的字符串。要求数量在1万个码以下，允许多个药品的追溯码混合上传】注意：在同一张单据里，不能有重复的码；在同一张单据中不能同时上传有关联关系的大、小码
        """
        self._trace_codes = trace_codes
        """
            客户端类型[必须填2]
        """
        self._client_type = client_type
        """
            已废弃，无需填写
        """
        self._return_reason_code = return_reason_code
        """
            已废弃，无需填写
        """
        self._return_reason_des = return_reason_des
        """
            已废弃，无需填写
        """
        self._cancel_reason_code = cancel_reason_code
        """
            已废弃，无需填写
        """
        self._cancel_reason_des = cancel_reason_des
        """
            已废弃，无需填写
        """
        self._executer_name = executer_name
        """
            已废弃，无需填写
        """
        self._executer_code = executer_code
        """
            已废弃，无需填写
        """
        self._superviser_name = superviser_name
        """
            已废弃，无需填写
        """
        self._superviser_code = superviser_code
        """
            （协同平台数据合规）发货地址（可为空）
        """
        self._from_address = from_address
        """
            （协同平台数据合规）收货地址（可为空）
        """
        self._to_address = to_address
        """
            （协同平台数据合规）发货单编号（可为空）
        """
        self._from_bill_code = from_bill_code
        """
            （协同平台数据合规）订货单编号（可为空）
        """
        self._order_code = order_code
        """
            （协同平台数据合规）发货人（可为空）
        """
        self._from_person = from_person
        """
            （协同平台数据合规）收货人（可为空）
        """
        self._to_person = to_person
        """
            （协同平台数据合规）药品配送企业【添写ref_ent_id】
        """
        self._dis_ref_ent_id = dis_ref_ent_id
        """
            （协同平台数据合规）药品配送企业entId【添写ent_id】
        """
        self._dis_ent_id = dis_ent_id
        """
            （协同平台数据合规）应收货总数量（可为空）
        """
        self._qu_receivable = qu_receivable
        """
            （协同平台数据合规）是否验证，0：未通过验证，1：已验证
        """
        self._xt_is_check = xt_is_check
        """
            （协同平台数据合规）未验证通过原因【验证未通过时填写】
        """
        self._xt_check_code = xt_check_code
        """
            （协同平台数据合规）未验证通过原因描述【验证未通过时填写】
        """
        self._xt_check_code_desc = xt_check_code_desc
        """
            （协同平台数据合规）药品列表Json[可不填写]
        """
        self._drug_list_json = drug_list_json
        """
            （协同平台数据合规）单据委托企业refEntId【疫苗药品出库单填写】
        """
        self._ass_ref_ent_id = ass_ref_ent_id
        """
            （协同平台数据合规）单据委托企业entId【疫苗药品出库单填写】
        """
        self._ass_ent_id = ass_ent_id
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
    def agent_ref_user_id(self):
        return self._agent_ref_user_id

    @agent_ref_user_id.setter
    def agent_ref_user_id(self, agent_ref_user_id):
        if isinstance(agent_ref_user_id, str):
            self._agent_ref_user_id = agent_ref_user_id
        else:
            raise TypeError("agent_ref_user_id must be str")
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
    def to_user_id(self):
        return self._to_user_id

    @to_user_id.setter
    def to_user_id(self, to_user_id):
        if isinstance(to_user_id, str):
            self._to_user_id = to_user_id
        else:
            raise TypeError("to_user_id must be str")
    @property
    def dest_user_id(self):
        return self._dest_user_id

    @dest_user_id.setter
    def dest_user_id(self, dest_user_id):
        if isinstance(dest_user_id, str):
            self._dest_user_id = dest_user_id
        else:
            raise TypeError("dest_user_id must be str")
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
    def warehouse_id(self):
        return self._warehouse_id

    @warehouse_id.setter
    def warehouse_id(self, warehouse_id):
        if isinstance(warehouse_id, str):
            self._warehouse_id = warehouse_id
        else:
            raise TypeError("warehouse_id must be str")
    @property
    def drug_id(self):
        return self._drug_id

    @drug_id.setter
    def drug_id(self, drug_id):
        if isinstance(drug_id, str):
            self._drug_id = drug_id
        else:
            raise TypeError("drug_id must be str")
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
    def client_type(self):
        return self._client_type

    @client_type.setter
    def client_type(self, client_type):
        if isinstance(client_type, str):
            self._client_type = client_type
        else:
            raise TypeError("client_type must be str")
    @property
    def return_reason_code(self):
        return self._return_reason_code

    @return_reason_code.setter
    def return_reason_code(self, return_reason_code):
        if isinstance(return_reason_code, str):
            self._return_reason_code = return_reason_code
        else:
            raise TypeError("return_reason_code must be str")
    @property
    def return_reason_des(self):
        return self._return_reason_des

    @return_reason_des.setter
    def return_reason_des(self, return_reason_des):
        if isinstance(return_reason_des, str):
            self._return_reason_des = return_reason_des
        else:
            raise TypeError("return_reason_des must be str")
    @property
    def cancel_reason_code(self):
        return self._cancel_reason_code

    @cancel_reason_code.setter
    def cancel_reason_code(self, cancel_reason_code):
        if isinstance(cancel_reason_code, str):
            self._cancel_reason_code = cancel_reason_code
        else:
            raise TypeError("cancel_reason_code must be str")
    @property
    def cancel_reason_des(self):
        return self._cancel_reason_des

    @cancel_reason_des.setter
    def cancel_reason_des(self, cancel_reason_des):
        if isinstance(cancel_reason_des, str):
            self._cancel_reason_des = cancel_reason_des
        else:
            raise TypeError("cancel_reason_des must be str")
    @property
    def executer_name(self):
        return self._executer_name

    @executer_name.setter
    def executer_name(self, executer_name):
        if isinstance(executer_name, str):
            self._executer_name = executer_name
        else:
            raise TypeError("executer_name must be str")
    @property
    def executer_code(self):
        return self._executer_code

    @executer_code.setter
    def executer_code(self, executer_code):
        if isinstance(executer_code, str):
            self._executer_code = executer_code
        else:
            raise TypeError("executer_code must be str")
    @property
    def superviser_name(self):
        return self._superviser_name

    @superviser_name.setter
    def superviser_name(self, superviser_name):
        if isinstance(superviser_name, str):
            self._superviser_name = superviser_name
        else:
            raise TypeError("superviser_name must be str")
    @property
    def superviser_code(self):
        return self._superviser_code

    @superviser_code.setter
    def superviser_code(self, superviser_code):
        if isinstance(superviser_code, str):
            self._superviser_code = superviser_code
        else:
            raise TypeError("superviser_code must be str")
    @property
    def from_address(self):
        return self._from_address

    @from_address.setter
    def from_address(self, from_address):
        if isinstance(from_address, str):
            self._from_address = from_address
        else:
            raise TypeError("from_address must be str")
    @property
    def to_address(self):
        return self._to_address

    @to_address.setter
    def to_address(self, to_address):
        if isinstance(to_address, str):
            self._to_address = to_address
        else:
            raise TypeError("to_address must be str")
    @property
    def from_bill_code(self):
        return self._from_bill_code

    @from_bill_code.setter
    def from_bill_code(self, from_bill_code):
        if isinstance(from_bill_code, str):
            self._from_bill_code = from_bill_code
        else:
            raise TypeError("from_bill_code must be str")
    @property
    def order_code(self):
        return self._order_code

    @order_code.setter
    def order_code(self, order_code):
        if isinstance(order_code, str):
            self._order_code = order_code
        else:
            raise TypeError("order_code must be str")
    @property
    def from_person(self):
        return self._from_person

    @from_person.setter
    def from_person(self, from_person):
        if isinstance(from_person, str):
            self._from_person = from_person
        else:
            raise TypeError("from_person must be str")
    @property
    def to_person(self):
        return self._to_person

    @to_person.setter
    def to_person(self, to_person):
        if isinstance(to_person, str):
            self._to_person = to_person
        else:
            raise TypeError("to_person must be str")
    @property
    def dis_ref_ent_id(self):
        return self._dis_ref_ent_id

    @dis_ref_ent_id.setter
    def dis_ref_ent_id(self, dis_ref_ent_id):
        if isinstance(dis_ref_ent_id, str):
            self._dis_ref_ent_id = dis_ref_ent_id
        else:
            raise TypeError("dis_ref_ent_id must be str")
    @property
    def dis_ent_id(self):
        return self._dis_ent_id

    @dis_ent_id.setter
    def dis_ent_id(self, dis_ent_id):
        if isinstance(dis_ent_id, str):
            self._dis_ent_id = dis_ent_id
        else:
            raise TypeError("dis_ent_id must be str")
    @property
    def qu_receivable(self):
        return self._qu_receivable

    @qu_receivable.setter
    def qu_receivable(self, qu_receivable):
        if isinstance(qu_receivable, int):
            self._qu_receivable = qu_receivable
        else:
            raise TypeError("qu_receivable must be int")
    @property
    def xt_is_check(self):
        return self._xt_is_check

    @xt_is_check.setter
    def xt_is_check(self, xt_is_check):
        if isinstance(xt_is_check, str):
            self._xt_is_check = xt_is_check
        else:
            raise TypeError("xt_is_check must be str")
    @property
    def xt_check_code(self):
        return self._xt_check_code

    @xt_check_code.setter
    def xt_check_code(self, xt_check_code):
        if isinstance(xt_check_code, str):
            self._xt_check_code = xt_check_code
        else:
            raise TypeError("xt_check_code must be str")
    @property
    def xt_check_code_desc(self):
        return self._xt_check_code_desc

    @xt_check_code_desc.setter
    def xt_check_code_desc(self, xt_check_code_desc):
        if isinstance(xt_check_code_desc, str):
            self._xt_check_code_desc = xt_check_code_desc
        else:
            raise TypeError("xt_check_code_desc must be str")
    @property
    def drug_list_json(self):
        return self._drug_list_json

    @drug_list_json.setter
    def drug_list_json(self, drug_list_json):
        if isinstance(drug_list_json, str):
            self._drug_list_json = drug_list_json
        else:
            raise TypeError("drug_list_json must be str")
    @property
    def ass_ref_ent_id(self):
        return self._ass_ref_ent_id

    @ass_ref_ent_id.setter
    def ass_ref_ent_id(self, ass_ref_ent_id):
        if isinstance(ass_ref_ent_id, str):
            self._ass_ref_ent_id = ass_ref_ent_id
        else:
            raise TypeError("ass_ref_ent_id must be str")
    @property
    def ass_ent_id(self):
        return self._ass_ent_id

    @ass_ent_id.setter
    def ass_ent_id(self, ass_ent_id):
        if isinstance(ass_ent_id, str):
            self._ass_ent_id = ass_ent_id
        else:
            raise TypeError("ass_ent_id must be str")
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
        return "alibaba.alihealth.drugtrace.top.yljg.uploadinoutbill"

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

        if self._agent_ref_user_id is not None:
            request_dict["agent_ref_user_id"] = convert_basic(self._agent_ref_user_id)

        if self._from_user_id is not None:
            request_dict["from_user_id"] = convert_basic(self._from_user_id)

        if self._to_user_id is not None:
            request_dict["to_user_id"] = convert_basic(self._to_user_id)

        if self._dest_user_id is not None:
            request_dict["dest_user_id"] = convert_basic(self._dest_user_id)

        if self._oper_ic_code is not None:
            request_dict["oper_ic_code"] = convert_basic(self._oper_ic_code)

        if self._oper_ic_name is not None:
            request_dict["oper_ic_name"] = convert_basic(self._oper_ic_name)

        if self._warehouse_id is not None:
            request_dict["warehouse_id"] = convert_basic(self._warehouse_id)

        if self._drug_id is not None:
            request_dict["drug_id"] = convert_basic(self._drug_id)

        if self._trace_codes is not None:
            request_dict["trace_codes"] = convert_basic_list(self._trace_codes)

        if self._client_type is not None:
            request_dict["client_type"] = convert_basic(self._client_type)

        if self._return_reason_code is not None:
            request_dict["return_reason_code"] = convert_basic(self._return_reason_code)

        if self._return_reason_des is not None:
            request_dict["return_reason_des"] = convert_basic(self._return_reason_des)

        if self._cancel_reason_code is not None:
            request_dict["cancel_reason_code"] = convert_basic(self._cancel_reason_code)

        if self._cancel_reason_des is not None:
            request_dict["cancel_reason_des"] = convert_basic(self._cancel_reason_des)

        if self._executer_name is not None:
            request_dict["executer_name"] = convert_basic(self._executer_name)

        if self._executer_code is not None:
            request_dict["executer_code"] = convert_basic(self._executer_code)

        if self._superviser_name is not None:
            request_dict["superviser_name"] = convert_basic(self._superviser_name)

        if self._superviser_code is not None:
            request_dict["superviser_code"] = convert_basic(self._superviser_code)

        if self._from_address is not None:
            request_dict["from_address"] = convert_basic(self._from_address)

        if self._to_address is not None:
            request_dict["to_address"] = convert_basic(self._to_address)

        if self._from_bill_code is not None:
            request_dict["from_bill_code"] = convert_basic(self._from_bill_code)

        if self._order_code is not None:
            request_dict["order_code"] = convert_basic(self._order_code)

        if self._from_person is not None:
            request_dict["from_person"] = convert_basic(self._from_person)

        if self._to_person is not None:
            request_dict["to_person"] = convert_basic(self._to_person)

        if self._dis_ref_ent_id is not None:
            request_dict["dis_ref_ent_id"] = convert_basic(self._dis_ref_ent_id)

        if self._dis_ent_id is not None:
            request_dict["dis_ent_id"] = convert_basic(self._dis_ent_id)

        if self._qu_receivable is not None:
            request_dict["qu_receivable"] = convert_basic(self._qu_receivable)

        if self._xt_is_check is not None:
            request_dict["xt_is_check"] = convert_basic(self._xt_is_check)

        if self._xt_check_code is not None:
            request_dict["xt_check_code"] = convert_basic(self._xt_check_code)

        if self._xt_check_code_desc is not None:
            request_dict["xt_check_code_desc"] = convert_basic(self._xt_check_code_desc)

        if self._drug_list_json is not None:
            request_dict["drug_list_json"] = convert_basic(self._drug_list_json)

        if self._ass_ref_ent_id is not None:
            request_dict["ass_ref_ent_id"] = convert_basic(self._ass_ref_ent_id)

        if self._ass_ent_id is not None:
            request_dict["ass_ent_id"] = convert_basic(self._ass_ent_id)

        if self._ignore_part_success_flag is not None:
            request_dict["ignore_part_success_flag"] = convert_basic(self._ignore_part_success_flag)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


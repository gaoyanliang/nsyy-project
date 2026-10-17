from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryBillstatusRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        begin_date: str = None,
        end_date: str = None,
        bill_type: str = None,
        bill_code: str = None,
        drug_type: str = None,
        deal_status: str = None,
        from_user_id: str = None,
        to_user_id: str = None,
        agent_ref_user_id: str = None,
        page_size: int = None,
        page: int = None
    ):
        """
            企业ID
        """
        self._ref_ent_id = ref_ent_id
        """
            开始日期（没有时分秒，【单据创建时间】）
        """
        self._begin_date = begin_date
        """
            结束日期（没有时分秒，【单据创建时间】）
        """
        self._end_date = end_date
        """
            单据类型 A：全部 AI：全部入库 AO：全部出库
        """
        self._bill_type = bill_type
        """
            单据号
        """
        self._bill_code = bill_code
        """
            药品类型
        """
        self._drug_type = drug_type
        """
            状态  0, 上传成功     3, 处理成功     4, 处理失败
        """
        self._deal_status = deal_status
        """
            发货商
        """
        self._from_user_id = from_user_id
        """
            收货商
        """
        self._to_user_id = to_user_id
        """
            代理商
        """
        self._agent_ref_user_id = agent_ref_user_id
        """
            页大小
        """
        self._page_size = page_size
        """
            页码
        """
        self._page = page

    @property
    def ref_ent_id(self):
        return self._ref_ent_id

    @ref_ent_id.setter
    def ref_ent_id(self, ref_ent_id):
        if isinstance(ref_ent_id, str):
            self._ref_ent_id = ref_ent_id
        else:
            raise TypeError("ref_ent_id must be str")
    @property
    def begin_date(self):
        return self._begin_date

    @begin_date.setter
    def begin_date(self, begin_date):
        if isinstance(begin_date, str):
            self._begin_date = begin_date
        else:
            raise TypeError("begin_date must be str")
    @property
    def end_date(self):
        return self._end_date

    @end_date.setter
    def end_date(self, end_date):
        if isinstance(end_date, str):
            self._end_date = end_date
        else:
            raise TypeError("end_date must be str")
    @property
    def bill_type(self):
        return self._bill_type

    @bill_type.setter
    def bill_type(self, bill_type):
        if isinstance(bill_type, str):
            self._bill_type = bill_type
        else:
            raise TypeError("bill_type must be str")
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
    def drug_type(self):
        return self._drug_type

    @drug_type.setter
    def drug_type(self, drug_type):
        if isinstance(drug_type, str):
            self._drug_type = drug_type
        else:
            raise TypeError("drug_type must be str")
    @property
    def deal_status(self):
        return self._deal_status

    @deal_status.setter
    def deal_status(self, deal_status):
        if isinstance(deal_status, str):
            self._deal_status = deal_status
        else:
            raise TypeError("deal_status must be str")
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
    def agent_ref_user_id(self):
        return self._agent_ref_user_id

    @agent_ref_user_id.setter
    def agent_ref_user_id(self, agent_ref_user_id):
        if isinstance(agent_ref_user_id, str):
            self._agent_ref_user_id = agent_ref_user_id
        else:
            raise TypeError("agent_ref_user_id must be str")
    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, page_size):
        if isinstance(page_size, int):
            self._page_size = page_size
        else:
            raise TypeError("page_size must be int")
    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, page):
        if isinstance(page, int):
            self._page = page
        else:
            raise TypeError("page must be int")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.billstatus"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._begin_date is not None:
            request_dict["begin_date"] = convert_basic(self._begin_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._bill_type is not None:
            request_dict["bill_type"] = convert_basic(self._bill_type)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._drug_type is not None:
            request_dict["drug_type"] = convert_basic(self._drug_type)

        if self._deal_status is not None:
            request_dict["deal_status"] = convert_basic(self._deal_status)

        if self._from_user_id is not None:
            request_dict["from_user_id"] = convert_basic(self._from_user_id)

        if self._to_user_id is not None:
            request_dict["to_user_id"] = convert_basic(self._to_user_id)

        if self._agent_ref_user_id is not None:
            request_dict["agent_ref_user_id"] = convert_basic(self._agent_ref_user_id)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


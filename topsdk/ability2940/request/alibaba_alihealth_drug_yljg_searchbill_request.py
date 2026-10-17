from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugYljgSearchbillRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        auth_ref_user_id: str = None,
        begin_date: str = None,
        end_date: str = None,
        partner_id_send: str = None,
        partner_id_recv: str = None,
        bill_code: str = None,
        bill_type: str = None,
        cur_page: int = None,
        page_size: int = None
    ):
        """
            企业标识
        """
        self._ref_ent_id = ref_ent_id
        """
            单据所有者
        """
        self._auth_ref_user_id = auth_ref_user_id
        """
            开始日期
        """
        self._begin_date = begin_date
        """
            结束日期
        """
        self._end_date = end_date
        """
            发货企业entId
        """
        self._partner_id_send = partner_id_send
        """
            收货企业entId
        """
        self._partner_id_recv = partner_id_recv
        """
            单据号码
        """
        self._bill_code = bill_code
        """
            单据类型  A : 所有  AI :入库    AO:出库
        """
        self._bill_type = bill_type
        """
            当前页
        """
        self._cur_page = cur_page
        """
            页大小
        """
        self._page_size = page_size

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
    def auth_ref_user_id(self):
        return self._auth_ref_user_id

    @auth_ref_user_id.setter
    def auth_ref_user_id(self, auth_ref_user_id):
        if isinstance(auth_ref_user_id, str):
            self._auth_ref_user_id = auth_ref_user_id
        else:
            raise TypeError("auth_ref_user_id must be str")
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
    def partner_id_send(self):
        return self._partner_id_send

    @partner_id_send.setter
    def partner_id_send(self, partner_id_send):
        if isinstance(partner_id_send, str):
            self._partner_id_send = partner_id_send
        else:
            raise TypeError("partner_id_send must be str")
    @property
    def partner_id_recv(self):
        return self._partner_id_recv

    @partner_id_recv.setter
    def partner_id_recv(self, partner_id_recv):
        if isinstance(partner_id_recv, str):
            self._partner_id_recv = partner_id_recv
        else:
            raise TypeError("partner_id_recv must be str")
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
    def bill_type(self):
        return self._bill_type

    @bill_type.setter
    def bill_type(self, bill_type):
        if isinstance(bill_type, str):
            self._bill_type = bill_type
        else:
            raise TypeError("bill_type must be str")
    @property
    def cur_page(self):
        return self._cur_page

    @cur_page.setter
    def cur_page(self, cur_page):
        if isinstance(cur_page, int):
            self._cur_page = cur_page
        else:
            raise TypeError("cur_page must be int")
    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, page_size):
        if isinstance(page_size, int):
            self._page_size = page_size
        else:
            raise TypeError("page_size must be int")

    def get_api_name(self):
        return "alibaba.alihealth.drug.yljg.searchbill"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._auth_ref_user_id is not None:
            request_dict["auth_ref_user_id"] = convert_basic(self._auth_ref_user_id)

        if self._begin_date is not None:
            request_dict["begin_date"] = convert_basic(self._begin_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._partner_id_send is not None:
            request_dict["partner_id_send"] = convert_basic(self._partner_id_send)

        if self._partner_id_recv is not None:
            request_dict["partner_id_recv"] = convert_basic(self._partner_id_recv)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._bill_type is not None:
            request_dict["bill_type"] = convert_basic(self._bill_type)

        if self._cur_page is not None:
            request_dict["cur_page"] = convert_basic(self._cur_page)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


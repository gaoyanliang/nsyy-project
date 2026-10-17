from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgListbillprocesspartsuccessRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        bill_code: str = None,
        error_code: str = None,
        code: str = None,
        page: int = None,
        page_size: int = None
    ):
        """
            企业标识
        """
        self._ref_ent_id = ref_ent_id
        """
            单据号
        """
        self._bill_code = bill_code
        """
            错误码类型
        """
        self._error_code = error_code
        """
            错误码
        """
        self._code = code
        """
            当前页
        """
        self._page = page
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
    def bill_code(self):
        return self._bill_code

    @bill_code.setter
    def bill_code(self, bill_code):
        if isinstance(bill_code, str):
            self._bill_code = bill_code
        else:
            raise TypeError("bill_code must be str")
    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, error_code):
        if isinstance(error_code, str):
            self._error_code = error_code
        else:
            raise TypeError("error_code must be str")
    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        if isinstance(code, str):
            self._code = code
        else:
            raise TypeError("code must be str")
    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, page):
        if isinstance(page, int):
            self._page = page
        else:
            raise TypeError("page must be int")
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
        return "alibaba.alihealth.drugtrace.top.yljg.listbillprocesspartsuccess"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._error_code is not None:
            request_dict["error_code"] = convert_basic(self._error_code)

        if self._code is not None:
            request_dict["code"] = convert_basic(self._code)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


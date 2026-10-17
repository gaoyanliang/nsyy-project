from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugMyjCodewarnCodewarninginfodetaillistRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        code_flow_warning_id: int = None,
        page: int = None,
        page_size: int = None
    ):
        """
            企业标识
        """
        self._ref_ent_id = ref_ent_id
        """
            任务流水编码（码预警任务列表中的ID）
        """
        self._code_flow_warning_id = code_flow_warning_id
        """
            页数
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
    def code_flow_warning_id(self):
        return self._code_flow_warning_id

    @code_flow_warning_id.setter
    def code_flow_warning_id(self, code_flow_warning_id):
        if isinstance(code_flow_warning_id, int):
            self._code_flow_warning_id = code_flow_warning_id
        else:
            raise TypeError("code_flow_warning_id must be int")
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
        return "alibaba.alihealth.drug.myj.codewarn.codewarninginfodetaillist"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._code_flow_warning_id is not None:
            request_dict["code_flow_warning_id"] = convert_basic(self._code_flow_warning_id)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


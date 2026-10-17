from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryUpbilldetailRequest(BaseRequest):

    def __init__(
        self,
        bill_code: str = None,
        ref_ent_id: str = None
    ):
        """
            单据号码
        """
        self._bill_code = bill_code
        """
            本企业refEntId
        """
        self._ref_ent_id = ref_ent_id

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
    def ref_ent_id(self):
        return self._ref_ent_id

    @ref_ent_id.setter
    def ref_ent_id(self, ref_ent_id):
        if isinstance(ref_ent_id, str):
            self._ref_ent_id = ref_ent_id
        else:
            raise TypeError("ref_ent_id must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.upbilldetail"

    def to_dict(self):
        request_dict = {}
        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


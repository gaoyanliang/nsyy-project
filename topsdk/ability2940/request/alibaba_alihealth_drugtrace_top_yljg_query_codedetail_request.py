from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryCodedetailRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        codes: list = None
    ):
        """
            企业唯一标识
        """
        self._ref_ent_id = ref_ent_id
        """
            码列表【多个码用逗号拼接的字符串。要求数量在1000个码以下，但一般不要传这么多，如果网络不好很容易传输一半报错】
        """
        self._codes = codes

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
    def codes(self):
        return self._codes

    @codes.setter
    def codes(self, codes):
        if isinstance(codes, list):
            self._codes = codes
        else:
            raise TypeError("codes must be list")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.codedetail"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._codes is not None:
            request_dict["codes"] = convert_basic_list(self._codes)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


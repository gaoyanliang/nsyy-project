from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugMyjCodewarnGetwarninfoRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        code: str = None
    ):
        """
            企业ref_ent_id
        """
        self._ref_ent_id = ref_ent_id
        """
            单个追溯码
        """
        self._code = code

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
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        if isinstance(code, str):
            self._code = code
        else:
            raise TypeError("code must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drug.myj.codewarn.getwarninfo"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._code is not None:
            request_dict["code"] = convert_basic(self._code)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


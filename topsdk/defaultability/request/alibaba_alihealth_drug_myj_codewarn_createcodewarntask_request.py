from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugMyjCodewarnCreatecodewarntaskRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        codes: str = None,
        bill_code: str = None
    ):
        """
            企业refEntId
        """
        self._ref_ent_id = ref_ent_id
        """
            追溯码列表（多个追溯码，以逗号拼接）
        """
        self._codes = codes
        """
            来源单据号
        """
        self._bill_code = bill_code

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
        if isinstance(codes, str):
            self._codes = codes
        else:
            raise TypeError("codes must be str")
    @property
    def bill_code(self):
        return self._bill_code

    @bill_code.setter
    def bill_code(self, bill_code):
        if isinstance(bill_code, str):
            self._bill_code = bill_code
        else:
            raise TypeError("bill_code must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drug.myj.codewarn.createcodewarntask"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._codes is not None:
            request_dict["codes"] = convert_basic(self._codes)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


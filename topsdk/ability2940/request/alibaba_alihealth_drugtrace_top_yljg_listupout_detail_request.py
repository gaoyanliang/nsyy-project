from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgListupoutDetailRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        bill_code: str = None,
        from_ref_user_id: str = None,
        to_ref_user_id: str = None,
        ass_ref_ent_id: str = None
    ):
        """
            企业id
        """
        self._ref_ent_id = ref_ent_id
        """
            单据编码
        """
        self._bill_code = bill_code
        """
            发货企业refEntId【发货企业和委托企业必须填写一个，否则查询不出来数据】
        """
        self._from_ref_user_id = from_ref_user_id
        """
            收货企业refEntId
        """
        self._to_ref_user_id = to_ref_user_id
        """
            委托企业refEntId【发货企业和委托企业必须填写一个，否则查询不出来数据】
        """
        self._ass_ref_ent_id = ass_ref_ent_id

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
    def from_ref_user_id(self):
        return self._from_ref_user_id

    @from_ref_user_id.setter
    def from_ref_user_id(self, from_ref_user_id):
        if isinstance(from_ref_user_id, str):
            self._from_ref_user_id = from_ref_user_id
        else:
            raise TypeError("from_ref_user_id must be str")
    @property
    def to_ref_user_id(self):
        return self._to_ref_user_id

    @to_ref_user_id.setter
    def to_ref_user_id(self, to_ref_user_id):
        if isinstance(to_ref_user_id, str):
            self._to_ref_user_id = to_ref_user_id
        else:
            raise TypeError("to_ref_user_id must be str")
    @property
    def ass_ref_ent_id(self):
        return self._ass_ref_ent_id

    @ass_ref_ent_id.setter
    def ass_ref_ent_id(self, ass_ref_ent_id):
        if isinstance(ass_ref_ent_id, str):
            self._ass_ref_ent_id = ass_ref_ent_id
        else:
            raise TypeError("ass_ref_ent_id must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.listupout.detail"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._from_ref_user_id is not None:
            request_dict["from_ref_user_id"] = convert_basic(self._from_ref_user_id)

        if self._to_ref_user_id is not None:
            request_dict["to_ref_user_id"] = convert_basic(self._to_ref_user_id)

        if self._ass_ref_ent_id is not None:
            request_dict["ass_ref_ent_id"] = convert_basic(self._ass_ref_ent_id)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryRelationRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        code: str = None,
        des_ref_ent_id: str = None
    ):
        """
            接口调用企业的唯一标识（接口调用者）
        """
        self._ref_ent_id = ref_ent_id
        """
            追溯码,多个码需要逗号拼接，最大10个码
        """
        self._code = code
        """
            目标企业唯一标识（为哪个企业查询，一般与入参ref_ent_id一样）
        """
        self._des_ref_ent_id = des_ref_ent_id

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
    @property
    def des_ref_ent_id(self):
        return self._des_ref_ent_id

    @des_ref_ent_id.setter
    def des_ref_ent_id(self, des_ref_ent_id):
        if isinstance(des_ref_ent_id, str):
            self._des_ref_ent_id = des_ref_ent_id
        else:
            raise TypeError("des_ref_ent_id must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.relation"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._code is not None:
            request_dict["code"] = convert_basic(self._code)

        if self._des_ref_ent_id is not None:
            request_dict["des_ref_ent_id"] = convert_basic(self._des_ref_ent_id)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


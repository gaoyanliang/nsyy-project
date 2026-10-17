from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryGetbyrefentidRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        dest_ref_ent_id: str = None
    ):
        """
            接口调用企业的唯一标识（接口调用者）
        """
        self._ref_ent_id = ref_ent_id
        """
            准备要查询的企业唯一标识（返回该唯一标识企业的详细信息）
        """
        self._dest_ref_ent_id = dest_ref_ent_id

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
    def dest_ref_ent_id(self):
        return self._dest_ref_ent_id

    @dest_ref_ent_id.setter
    def dest_ref_ent_id(self, dest_ref_ent_id):
        if isinstance(dest_ref_ent_id, str):
            self._dest_ref_ent_id = dest_ref_ent_id
        else:
            raise TypeError("dest_ref_ent_id must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.getbyrefentid"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._dest_ref_ent_id is not None:
            request_dict["dest_ref_ent_id"] = convert_basic(self._dest_ref_ent_id)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


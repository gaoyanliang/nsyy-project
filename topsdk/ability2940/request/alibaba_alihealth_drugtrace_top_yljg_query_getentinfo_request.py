from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryGetentinfoRequest(BaseRequest):

    def __init__(
        self,
        ent_name: str = None
    ):
        """
            公司名称(全称)
        """
        self._ent_name = ent_name

    @property
    def ent_name(self):
        return self._ent_name

    @ent_name.setter
    def ent_name(self, ent_name):
        if isinstance(ent_name, str):
            self._ent_name = ent_name
        else:
            raise TypeError("ent_name must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.query.getentinfo"

    def to_dict(self):
        request_dict = {}
        if self._ent_name is not None:
            request_dict["ent_name"] = convert_basic(self._ent_name)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


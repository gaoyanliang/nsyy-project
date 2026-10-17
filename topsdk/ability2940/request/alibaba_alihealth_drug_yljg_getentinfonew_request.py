from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugYljgGetentinfonewRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        query_param: object = None
    ):
        """
            refEntId
        """
        self._ref_ent_id = ref_ent_id
        """
            查询企业信息参数
        """
        self._query_param = query_param

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
    def query_param(self):
        return self._query_param

    @query_param.setter
    def query_param(self, query_param):
        if isinstance(query_param, object):
            self._query_param = query_param
        else:
            raise TypeError("query_param must be object")

    def get_api_name(self):
        return "alibaba.alihealth.drug.yljg.getentinfonew"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._query_param is not None:
            request_dict["query_param"] = convert_struct(self._query_param)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict

class AlibabaAlihealthDrugYljgGetentinfonewTopEntInfoReqDto:
    def __init__(
        self,
        ent_name: str = None,
        org_code: str = None,
        medical_code: str = None
    ):
        """
            查询参数：企业名称，无其他查询条件时不能为空
        """
        self.ent_name = ent_name
        """
            查询参数：统一社会信用代码，无其他查询条件时不能为空
        """
        self.org_code = org_code
        """
            查询参数：诊所备案号或医疗单位登记号，无其他查询条件时不能为空
        """
        self.medical_code = medical_code


from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgServiceGetenddateRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        business: int = None,
        service: int = None
    ):
        """
            调用接口的企业ID
        """
        self._ref_ent_id = ref_ent_id
        """
            药 行业线：传 1 
        """
        self._business = business
        """
            基础版：传 11
        """
        self._service = service

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
    def business(self):
        return self._business

    @business.setter
    def business(self, business):
        if isinstance(business, int):
            self._business = business
        else:
            raise TypeError("business must be int")
    @property
    def service(self):
        return self._service

    @service.setter
    def service(self, service):
        if isinstance(service, int):
            self._service = service
        else:
            raise TypeError("service must be int")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.service.getenddate"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._business is not None:
            request_dict["business"] = convert_basic(self._business)

        if self._service is not None:
            request_dict["service"] = convert_basic(self._service)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgDrugtableRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        physic_name: str = None,
        approval_licence_no: str = None,
        start_date: str = None,
        end_date: str = None,
        ent_name: str = None,
        package_spec: str = None,
        prepn_spec: str = None,
        page_size: int = None,
        page: int = None
    ):
        """
            企业ID
        """
        self._ref_ent_id = ref_ent_id
        """
            药品通用名
        """
        self._physic_name = physic_name
        """
            批准文号
        """
        self._approval_licence_no = approval_licence_no
        """
            开始日期
        """
        self._start_date = start_date
        """
            结束日期
        """
        self._end_date = end_date
        """
            企业名称
        """
        self._ent_name = ent_name
        """
            包装规格
        """
        self._package_spec = package_spec
        """
            制剂规格
        """
        self._prepn_spec = prepn_spec
        """
            页大小
        """
        self._page_size = page_size
        """
            页码
        """
        self._page = page

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
    def physic_name(self):
        return self._physic_name

    @physic_name.setter
    def physic_name(self, physic_name):
        if isinstance(physic_name, str):
            self._physic_name = physic_name
        else:
            raise TypeError("physic_name must be str")
    @property
    def approval_licence_no(self):
        return self._approval_licence_no

    @approval_licence_no.setter
    def approval_licence_no(self, approval_licence_no):
        if isinstance(approval_licence_no, str):
            self._approval_licence_no = approval_licence_no
        else:
            raise TypeError("approval_licence_no must be str")
    @property
    def start_date(self):
        return self._start_date

    @start_date.setter
    def start_date(self, start_date):
        if isinstance(start_date, str):
            self._start_date = start_date
        else:
            raise TypeError("start_date must be str")
    @property
    def end_date(self):
        return self._end_date

    @end_date.setter
    def end_date(self, end_date):
        if isinstance(end_date, str):
            self._end_date = end_date
        else:
            raise TypeError("end_date must be str")
    @property
    def ent_name(self):
        return self._ent_name

    @ent_name.setter
    def ent_name(self, ent_name):
        if isinstance(ent_name, str):
            self._ent_name = ent_name
        else:
            raise TypeError("ent_name must be str")
    @property
    def package_spec(self):
        return self._package_spec

    @package_spec.setter
    def package_spec(self, package_spec):
        if isinstance(package_spec, str):
            self._package_spec = package_spec
        else:
            raise TypeError("package_spec must be str")
    @property
    def prepn_spec(self):
        return self._prepn_spec

    @prepn_spec.setter
    def prepn_spec(self, prepn_spec):
        if isinstance(prepn_spec, str):
            self._prepn_spec = prepn_spec
        else:
            raise TypeError("prepn_spec must be str")
    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, page_size):
        if isinstance(page_size, int):
            self._page_size = page_size
        else:
            raise TypeError("page_size must be int")
    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, page):
        if isinstance(page, int):
            self._page = page
        else:
            raise TypeError("page must be int")

    def get_api_name(self):
        return "alibaba.alihealth.drugtrace.top.yljg.drugtable"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._physic_name is not None:
            request_dict["physic_name"] = convert_basic(self._physic_name)

        if self._approval_licence_no is not None:
            request_dict["approval_licence_no"] = convert_basic(self._approval_licence_no)

        if self._start_date is not None:
            request_dict["start_date"] = convert_basic(self._start_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._ent_name is not None:
            request_dict["ent_name"] = convert_basic(self._ent_name)

        if self._package_spec is not None:
            request_dict["package_spec"] = convert_basic(self._package_spec)

        if self._prepn_spec is not None:
            request_dict["prepn_spec"] = convert_basic(self._prepn_spec)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


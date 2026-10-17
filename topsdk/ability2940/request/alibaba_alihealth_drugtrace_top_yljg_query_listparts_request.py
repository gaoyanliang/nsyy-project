from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgQueryListpartsRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        ent_name: str = None,
        ref_partner_id: str = None,
        begin_date: str = None,
        end_date: str = None,
        audit_flag: int = None,
        page_size: int = None,
        page: int = None
    ):
        """
            企业唯一标识
        """
        self._ref_ent_id = ref_ent_id
        """
            企业名称
        """
        self._ent_name = ent_name
        """
            企业自定义编号
        """
        self._ref_partner_id = ref_partner_id
        """
            开始时间：往来单位最后修改时间（不推荐使用：因为往来单位是共用的，任意企业提交了信息变更都会引起这个值的变更）
        """
        self._begin_date = begin_date
        """
            结束时间：往来单位最后修改时间（不推荐使用：因为往来单位是共用的，任意企业提交了信息变更都会引起这个值的变更）
        """
        self._end_date = end_date
        """
            1:审核通过，2：审核不通过
        """
        self._audit_flag = audit_flag
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
    def ent_name(self):
        return self._ent_name

    @ent_name.setter
    def ent_name(self, ent_name):
        if isinstance(ent_name, str):
            self._ent_name = ent_name
        else:
            raise TypeError("ent_name must be str")
    @property
    def ref_partner_id(self):
        return self._ref_partner_id

    @ref_partner_id.setter
    def ref_partner_id(self, ref_partner_id):
        if isinstance(ref_partner_id, str):
            self._ref_partner_id = ref_partner_id
        else:
            raise TypeError("ref_partner_id must be str")
    @property
    def begin_date(self):
        return self._begin_date

    @begin_date.setter
    def begin_date(self, begin_date):
        if isinstance(begin_date, str):
            self._begin_date = begin_date
        else:
            raise TypeError("begin_date must be str")
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
    def audit_flag(self):
        return self._audit_flag

    @audit_flag.setter
    def audit_flag(self, audit_flag):
        if isinstance(audit_flag, int):
            self._audit_flag = audit_flag
        else:
            raise TypeError("audit_flag must be int")
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
        return "alibaba.alihealth.drugtrace.top.yljg.query.listparts"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._ent_name is not None:
            request_dict["ent_name"] = convert_basic(self._ent_name)

        if self._ref_partner_id is not None:
            request_dict["ref_partner_id"] = convert_basic(self._ref_partner_id)

        if self._begin_date is not None:
            request_dict["begin_date"] = convert_basic(self._begin_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._audit_flag is not None:
            request_dict["audit_flag"] = convert_basic(self._audit_flag)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugYljgQueryUpoutbillcountRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        bill_type: int = None,
        begin_date: str = None,
        end_date: str = None,
        ass_ref_ent_id: str = None
    ):
        """
            企业ID
        """
        self._ref_ent_id = ref_ent_id
        """
            单据类型
        """
        self._bill_type = bill_type
        """
            单据上传开始日期
        """
        self._begin_date = begin_date
        """
            单据上传结束日期
        """
        self._end_date = end_date
        """
            委托企业Id
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
    def bill_type(self):
        return self._bill_type

    @bill_type.setter
    def bill_type(self, bill_type):
        if isinstance(bill_type, int):
            self._bill_type = bill_type
        else:
            raise TypeError("bill_type must be int")
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
    def ass_ref_ent_id(self):
        return self._ass_ref_ent_id

    @ass_ref_ent_id.setter
    def ass_ref_ent_id(self, ass_ref_ent_id):
        if isinstance(ass_ref_ent_id, str):
            self._ass_ref_ent_id = ass_ref_ent_id
        else:
            raise TypeError("ass_ref_ent_id must be str")

    def get_api_name(self):
        return "alibaba.alihealth.drug.yljg.query.upoutbillcount"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._bill_type is not None:
            request_dict["bill_type"] = convert_basic(self._bill_type)

        if self._begin_date is not None:
            request_dict["begin_date"] = convert_basic(self._begin_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._ass_ref_ent_id is not None:
            request_dict["ass_ref_ent_id"] = convert_basic(self._ass_ref_ent_id)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


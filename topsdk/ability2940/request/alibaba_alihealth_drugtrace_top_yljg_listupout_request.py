from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugtraceTopYljgListupoutRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        begin_date: str = None,
        end_date: str = None,
        from_user_id: str = None,
        produce_batch_no: str = None,
        drug_ent_base_info_id: str = None,
        bill_type: str = None,
        physic_type: str = None,
        status: str = None,
        bill_code: str = None,
        ass_en_id: str = None,
        upload_time_begin: str = None,
        upload_time_end: str = None,
        page_size: int = None,
        page: int = None
    ):
        """
            企业ID
        """
        self._ref_ent_id = ref_ent_id
        """
            单据时间的开始日期（不写时分秒），格式：yyyy-MM-dd
        """
        self._begin_date = begin_date
        """
            单据时间的结束日期（不写时分秒），格式：yyyy-MM-dd
        """
        self._end_date = end_date
        """
            发货企业ent_id
        """
        self._from_user_id = from_user_id
        """
            生产批号
        """
        self._produce_batch_no = produce_batch_no
        """
            药品ID
        """
        self._drug_ent_base_info_id = drug_ent_base_info_id
        """
            单据类型
        """
        self._bill_type = bill_type
        """
            药品类型
        """
        self._physic_type = physic_type
        """
            状态
        """
        self._status = status
        """
            单据号
        """
        self._bill_code = bill_code
        """
            委托企业entId
        """
        self._ass_en_id = ass_en_id
        """
            单据上传的开始日期，格式：yyyy-MM-dd HH:mm:ss
        """
        self._upload_time_begin = upload_time_begin
        """
            单据上传的结束日期，格式：yyyy-MM-dd HH:mm:ss
        """
        self._upload_time_end = upload_time_end
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
    def from_user_id(self):
        return self._from_user_id

    @from_user_id.setter
    def from_user_id(self, from_user_id):
        if isinstance(from_user_id, str):
            self._from_user_id = from_user_id
        else:
            raise TypeError("from_user_id must be str")
    @property
    def produce_batch_no(self):
        return self._produce_batch_no

    @produce_batch_no.setter
    def produce_batch_no(self, produce_batch_no):
        if isinstance(produce_batch_no, str):
            self._produce_batch_no = produce_batch_no
        else:
            raise TypeError("produce_batch_no must be str")
    @property
    def drug_ent_base_info_id(self):
        return self._drug_ent_base_info_id

    @drug_ent_base_info_id.setter
    def drug_ent_base_info_id(self, drug_ent_base_info_id):
        if isinstance(drug_ent_base_info_id, str):
            self._drug_ent_base_info_id = drug_ent_base_info_id
        else:
            raise TypeError("drug_ent_base_info_id must be str")
    @property
    def bill_type(self):
        return self._bill_type

    @bill_type.setter
    def bill_type(self, bill_type):
        if isinstance(bill_type, str):
            self._bill_type = bill_type
        else:
            raise TypeError("bill_type must be str")
    @property
    def physic_type(self):
        return self._physic_type

    @physic_type.setter
    def physic_type(self, physic_type):
        if isinstance(physic_type, str):
            self._physic_type = physic_type
        else:
            raise TypeError("physic_type must be str")
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if isinstance(status, str):
            self._status = status
        else:
            raise TypeError("status must be str")
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
    def ass_en_id(self):
        return self._ass_en_id

    @ass_en_id.setter
    def ass_en_id(self, ass_en_id):
        if isinstance(ass_en_id, str):
            self._ass_en_id = ass_en_id
        else:
            raise TypeError("ass_en_id must be str")
    @property
    def upload_time_begin(self):
        return self._upload_time_begin

    @upload_time_begin.setter
    def upload_time_begin(self, upload_time_begin):
        if isinstance(upload_time_begin, str):
            self._upload_time_begin = upload_time_begin
        else:
            raise TypeError("upload_time_begin must be str")
    @property
    def upload_time_end(self):
        return self._upload_time_end

    @upload_time_end.setter
    def upload_time_end(self, upload_time_end):
        if isinstance(upload_time_end, str):
            self._upload_time_end = upload_time_end
        else:
            raise TypeError("upload_time_end must be str")
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
        return "alibaba.alihealth.drugtrace.top.yljg.listupout"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._begin_date is not None:
            request_dict["begin_date"] = convert_basic(self._begin_date)

        if self._end_date is not None:
            request_dict["end_date"] = convert_basic(self._end_date)

        if self._from_user_id is not None:
            request_dict["from_user_id"] = convert_basic(self._from_user_id)

        if self._produce_batch_no is not None:
            request_dict["produce_batch_no"] = convert_basic(self._produce_batch_no)

        if self._drug_ent_base_info_id is not None:
            request_dict["drug_ent_base_info_id"] = convert_basic(self._drug_ent_base_info_id)

        if self._bill_type is not None:
            request_dict["bill_type"] = convert_basic(self._bill_type)

        if self._physic_type is not None:
            request_dict["physic_type"] = convert_basic(self._physic_type)

        if self._status is not None:
            request_dict["status"] = convert_basic(self._status)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._ass_en_id is not None:
            request_dict["ass_en_id"] = convert_basic(self._ass_en_id)

        if self._upload_time_begin is not None:
            request_dict["upload_time_begin"] = convert_basic(self._upload_time_begin)

        if self._upload_time_end is not None:
            request_dict["upload_time_end"] = convert_basic(self._upload_time_end)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


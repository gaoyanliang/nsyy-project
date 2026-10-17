from typing import List
from topsdk.client import BaseRequest
from topsdk.util import convert_struct_list,convert_basic_list,convert_struct,convert_basic
from datetime import datetime


class AlibabaAlihealthDrugMyjCodewarnCodewarninglistRequest(BaseRequest):

    def __init__(
        self,
        ref_ent_id: str = None,
        gmt_create_begin: str = None,
        gmt_create_end: str = None,
        result_status: str = None,
        code: str = None,
        drug_ent_base_info_id: str = None,
        produce_batch_no: str = None,
        produce_ref_ent_id: str = None,
        mah_ref_ent_id: str = None,
        task_type: str = None,
        task_id: int = None,
        bill_code: str = None,
        page: int = None,
        page_size: int = None
    ):
        """
            企业标识
        """
        self._ref_ent_id = ref_ent_id
        """
            生成时间--开始日期
        """
        self._gmt_create_begin = gmt_create_begin
        """
            生成时间--结束日期
        """
        self._gmt_create_end = gmt_create_end
        """
            查询结果状态编码	0查询中 1未见异常 2异常
        """
        self._result_status = result_status
        """
            追溯码
        """
        self._code = code
        """
            药品ID
        """
        self._drug_ent_base_info_id = drug_ent_base_info_id
        """
            产品批号
        """
        self._produce_batch_no = produce_batch_no
        """
            生产企业ID
        """
        self._produce_ref_ent_id = produce_ref_ent_id
        """
            上市许可持有人企业ID
        """
        self._mah_ref_ent_id = mah_ref_ent_id
        """
            11: 扫码生成单据时生成   12: 上游出库单确认入库时生成   21:查询出入库单时生成  22: 查询上游出库单生成  23: 查询委托方上游出库单生成  3: TOP接口生成  4: 重新查询
        """
        self._task_type = task_type
        """
            任务批次编码
        """
        self._task_id = task_id
        """
            来源单据号
        """
        self._bill_code = bill_code
        """
            页数
        """
        self._page = page
        """
            每页条数
        """
        self._page_size = page_size

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
    def gmt_create_begin(self):
        return self._gmt_create_begin

    @gmt_create_begin.setter
    def gmt_create_begin(self, gmt_create_begin):
        if isinstance(gmt_create_begin, str):
            self._gmt_create_begin = gmt_create_begin
        else:
            raise TypeError("gmt_create_begin must be str")
    @property
    def gmt_create_end(self):
        return self._gmt_create_end

    @gmt_create_end.setter
    def gmt_create_end(self, gmt_create_end):
        if isinstance(gmt_create_end, str):
            self._gmt_create_end = gmt_create_end
        else:
            raise TypeError("gmt_create_end must be str")
    @property
    def result_status(self):
        return self._result_status

    @result_status.setter
    def result_status(self, result_status):
        if isinstance(result_status, str):
            self._result_status = result_status
        else:
            raise TypeError("result_status must be str")
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
    def drug_ent_base_info_id(self):
        return self._drug_ent_base_info_id

    @drug_ent_base_info_id.setter
    def drug_ent_base_info_id(self, drug_ent_base_info_id):
        if isinstance(drug_ent_base_info_id, str):
            self._drug_ent_base_info_id = drug_ent_base_info_id
        else:
            raise TypeError("drug_ent_base_info_id must be str")
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
    def produce_ref_ent_id(self):
        return self._produce_ref_ent_id

    @produce_ref_ent_id.setter
    def produce_ref_ent_id(self, produce_ref_ent_id):
        if isinstance(produce_ref_ent_id, str):
            self._produce_ref_ent_id = produce_ref_ent_id
        else:
            raise TypeError("produce_ref_ent_id must be str")
    @property
    def mah_ref_ent_id(self):
        return self._mah_ref_ent_id

    @mah_ref_ent_id.setter
    def mah_ref_ent_id(self, mah_ref_ent_id):
        if isinstance(mah_ref_ent_id, str):
            self._mah_ref_ent_id = mah_ref_ent_id
        else:
            raise TypeError("mah_ref_ent_id must be str")
    @property
    def task_type(self):
        return self._task_type

    @task_type.setter
    def task_type(self, task_type):
        if isinstance(task_type, str):
            self._task_type = task_type
        else:
            raise TypeError("task_type must be str")
    @property
    def task_id(self):
        return self._task_id

    @task_id.setter
    def task_id(self, task_id):
        if isinstance(task_id, int):
            self._task_id = task_id
        else:
            raise TypeError("task_id must be int")
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
    def page(self):
        return self._page

    @page.setter
    def page(self, page):
        if isinstance(page, int):
            self._page = page
        else:
            raise TypeError("page must be int")
    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, page_size):
        if isinstance(page_size, int):
            self._page_size = page_size
        else:
            raise TypeError("page_size must be int")

    def get_api_name(self):
        return "alibaba.alihealth.drug.myj.codewarn.codewarninglist"

    def to_dict(self):
        request_dict = {}
        if self._ref_ent_id is not None:
            request_dict["ref_ent_id"] = convert_basic(self._ref_ent_id)

        if self._gmt_create_begin is not None:
            request_dict["gmt_create_begin"] = convert_basic(self._gmt_create_begin)

        if self._gmt_create_end is not None:
            request_dict["gmt_create_end"] = convert_basic(self._gmt_create_end)

        if self._result_status is not None:
            request_dict["result_status"] = convert_basic(self._result_status)

        if self._code is not None:
            request_dict["code"] = convert_basic(self._code)

        if self._drug_ent_base_info_id is not None:
            request_dict["drug_ent_base_info_id"] = convert_basic(self._drug_ent_base_info_id)

        if self._produce_batch_no is not None:
            request_dict["produce_batch_no"] = convert_basic(self._produce_batch_no)

        if self._produce_ref_ent_id is not None:
            request_dict["produce_ref_ent_id"] = convert_basic(self._produce_ref_ent_id)

        if self._mah_ref_ent_id is not None:
            request_dict["mah_ref_ent_id"] = convert_basic(self._mah_ref_ent_id)

        if self._task_type is not None:
            request_dict["task_type"] = convert_basic(self._task_type)

        if self._task_id is not None:
            request_dict["task_id"] = convert_basic(self._task_id)

        if self._bill_code is not None:
            request_dict["bill_code"] = convert_basic(self._bill_code)

        if self._page is not None:
            request_dict["page"] = convert_basic(self._page)

        if self._page_size is not None:
            request_dict["page_size"] = convert_basic(self._page_size)

        return request_dict

    def get_file_param_dict(self):
        file_param_dict = {}
        return file_param_dict


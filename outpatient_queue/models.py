from typing import Optional, List
from pydantic import BaseModel, Field


class TakeNumberRequest(BaseModel):
    patient_id: str
    patient_name: str
    id_card: Optional[str] = None
    phone: Optional[str] = None
    business_id: str

class CallRequest(BaseModel):
    call_type: str
    window_id: int
    business_type: str
    business_id: Optional[str] = None
    patient_name: Optional[str] = ""
    queue_number: Optional[str] = None

class CompleteRequest(BaseModel):
    queue_number: str
    window_id: int
    status: int

class SkipRequest(BaseModel):
    queue_number: str
    reason: str = "过号"


class WakeUpRequest(BaseModel):
    patient_id: str
    queue_number: str
    business_type: str
    window_id: int

class AsrSubmitRequest(BaseModel):
    patient_info: str
    zhuyuanhao: str
    patient_name: str
    patient_age: str
    patient_sex: str
    dept_id: int
    dept_name: str
    yizhuid: str
    check_items: str
    patient_type: str


class UpdateReportRequest(BaseModel):
    patient_info: Optional[str] = None
    indicator_data: Optional[str] = None
    re_edit: Optional[bool] = False

class TemplateBody(BaseModel):
    check_item: str = Field(..., description="检查项目名称")
    report_template: Optional[str] = Field('', description="报告模板内容")
    group_id: Optional[int] = Field(-1, description="共用模板的分组ID，默认-1")


class EntryBody(BaseModel):
    keyword: str = Field(..., description="关键字")
    seen: Optional[str] = Field('', description="超声所见应补充内容")
    prompt: Optional[str] = Field('', description="超声提示应补充内容")
    check_item_id: Optional[int] = Field(None, description="检查项目ID")
    check_item: Optional[str] = Field('', description="检查项目名称")
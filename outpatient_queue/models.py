from typing import Optional, List
from pydantic import BaseModel

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

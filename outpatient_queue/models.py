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
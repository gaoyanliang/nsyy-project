from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticUndefined


class PatientImportItem(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # ===== 必填 =====
    bingrenzyid: str

    # ===== 普通字段，空值保持 None =====
    admission_no: Optional[str] = Field(None, alias="住院号")
    admission_times: Optional[int] = Field(None, alias="住院次数")
    patient_name: Optional[str] = Field(None, alias="姓名")
    age_text: Optional[str] = Field(None, alias="年龄")
    birth_date: Optional[str] = Field(None, alias="出生日期")
    admission_date: Optional[str] = Field(None, alias="入院日期")
    discharge_date: Optional[str] = Field(None, alias="出院日期")
    stay_days: Optional[int] = Field(None, alias="天数")
    discharge_dept: Optional[str] = Field(None, alias="出院科室")
    discharge_mode: Optional[str] = Field(None, alias="离院方式")
    diagnosis: Optional[str] = Field(None, alias="诊断")
    total_cost: Optional[float] = Field(None, alias="住院费用")
    marital_status: Optional[str] = Field(None, alias="婚姻状况")
    occupation: Optional[str] = Field(None, alias="职业")
    payment_type: Optional[str] = Field(None, alias="费用性质")
    death_order: Optional[str] = Field(None, alias="死亡医嘱")
    discharge_drugs: Optional[str] = Field(None, alias="出院带药")
    terminal_disease: Optional[str] = Field(None, alias="终末期疾病")

    # ===== 是/否字段，空值默认“否” =====
    icu_discharge: str = Field("否", alias="icu出院")
    abandon_treatment: str = Field("否", alias="放弃治疗病历")
    auto_discharge: str = Field("否", alias="自动出院病历")
    rescue_record: str = Field("否", alias="抢救记录病历")
    transfer_dept: str = Field("否", alias="转科")
    admission_critical: str = Field("否", alias="入院病情危急")
    emergency_admission: str = Field("否", alias="急诊入院")
    death_case: str = Field("否", alias="死亡病例")
    palliative_drug: str = Field("否", alias="出院带药_是否姑息药品")
    refuse_surgery: str = Field("否", alias="是否拒绝手术")
    patient_request_discharge: str = Field("否", alias="出院病历_患者要求出院")

    @field_validator("*", mode="before")
    @classmethod
    def fill_empty_with_default(cls, v, info):
        """
        None / 空字符串 / 纯空白 → 用该字段自己声明的默认值。
        无默认值的字段保持原值，交给后续校验或业务层处理。
        """
        if v is not None and not (isinstance(v, str) and v.strip() == ""):
            return v

        field = cls.model_fields.get(info.field_name)
        if field is None or field.default is PydanticUndefined:
            return v
        return field.default


class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    failures: list[dict]
    score_time: str


class PatientUpdateItem(BaseModel):
    """更新患者可编辑字段；未传字段不更新。"""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    age_text: Optional[str] = Field(None, alias="年龄")
    stay_days: Optional[int] = Field(None, alias="天数")
    diagnosis: Optional[str] = Field(None, alias="诊断")
    total_cost: Optional[float] = Field(None, alias="住院费用")

    discharge_mode: Optional[str] = Field('非死亡/医嘱离院', alias="离院方式")
    icu_discharge: Optional[str] = Field('否', alias="icu出院")
    abandon_treatment: Optional[str] = Field('否', alias="放弃治疗病历")
    auto_discharge: Optional[str] = Field('否', alias="自动出院病历")
    rescue_record: Optional[str] = Field('否', alias="抢救记录病历")
    transfer_dept: Optional[str] = Field('否', alias="转科")
    admission_critical: Optional[str] = Field('否', alias="入院病情危急")
    emergency_admission: Optional[str] = Field('否', alias="急诊入院")
    death_case: Optional[str] = Field('否', alias="死亡病例")
    death_order: Optional[str] = Field('否', alias="死亡医嘱")
    palliative_drug: Optional[str] = Field('否', alias="出院带药_是否姑息药品")
    refuse_surgery: Optional[str] = Field('否', alias="是否拒绝手术")
    patient_request_discharge: Optional[str] = Field('否', alias="出院病历_患者要求出院")

    marital_status: Optional[str] = Field('非丧偶', alias="婚姻状况")
    occupation: Optional[str] = Field(None, alias="职业")
    payment_type: Optional[str] = Field(None, alias="费用性质")
    terminal_disease: Optional[str] = Field('否', alias="终末期疾病")
    discharge_drugs: Optional[str] = Field(None, alias="出院带药")
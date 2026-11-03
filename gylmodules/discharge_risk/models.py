from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, String, Integer, DateTime, DECIMAL, Text, SmallInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DischargedPatient(Base):
    __tablename__ = "出院患者"

    id: Mapped[int] = mapped_column("患者记录编号", BigInteger, primary_key=True, autoincrement=True)
    bingrenzyid: Mapped[str] = mapped_column("病人住院标识", String(64), nullable=False)
    admission_no: Mapped[str | None] = mapped_column("住院号", String(64))
    admission_times: Mapped[int | None] = mapped_column("住院次数", Integer)
    patient_name: Mapped[str | None] = mapped_column("姓名", String(64))
    age_text: Mapped[str | None] = mapped_column("年龄", String(32))
    age_value: Mapped[int | None] = mapped_column("年龄数值", Integer)
    age_unit: Mapped[str | None] = mapped_column("年龄单位", String(8))
    birth_date: Mapped[datetime | None] = mapped_column("出生日期", DateTime)
    admission_date: Mapped[datetime | None] = mapped_column("入院日期", DateTime)
    discharge_date: Mapped[datetime] = mapped_column("出院日期", DateTime, nullable=False)
    stay_days: Mapped[int | None] = mapped_column("天数", Integer)
    discharge_dept: Mapped[str | None] = mapped_column("出院科室", String(128))
    icu_discharge: Mapped[str | None] = mapped_column("icu出院", String(8))
    discharge_mode: Mapped[str | None] = mapped_column("离院方式", String(64))
    abandon_treatment: Mapped[str | None] = mapped_column("放弃治疗病历", String(8))
    auto_discharge: Mapped[str | None] = mapped_column("自动出院病历", String(8))
    rescue_record: Mapped[str | None] = mapped_column("抢救记录病历", String(8))
    transfer_dept: Mapped[str | None] = mapped_column("转科", String(8))
    admission_critical: Mapped[str | None] = mapped_column("入院病情危急", String(8))
    diagnosis: Mapped[str | None] = mapped_column("诊断", Text)
    diagnosis_count: Mapped[int] = mapped_column("诊断数量", Integer, default=0)
    emergency_admission: Mapped[str | None] = mapped_column("急诊入院", String(8))
    total_cost: Mapped[Decimal | None] = mapped_column("住院费用", DECIMAL(12, 2))
    marital_status: Mapped[str | None] = mapped_column("婚姻状况", String(32))
    occupation: Mapped[str | None] = mapped_column("职业", String(64))
    payment_type: Mapped[str | None] = mapped_column("费用性质", String(64))
    death_order: Mapped[str | None] = mapped_column("死亡医嘱", String(64))
    death_case: Mapped[str | None] = mapped_column("死亡病例", String(8))
    discharge_drugs: Mapped[str | None] = mapped_column("出院带药", Text)
    palliative_drug: Mapped[str | None] = mapped_column("出院带药_是否姑息药品", String(8))
    terminal_disease: Mapped[str | None] = mapped_column("终末期疾病", String(255))
    refuse_surgery: Mapped[str | None] = mapped_column("是否拒绝手术", String(8))
    patient_request_discharge: Mapped[str | None] = mapped_column("出院病历_患者要求出院", String(8))
    discharge_type: Mapped[str | None] = mapped_column("离院类型", String(32))
    total_score: Mapped[Decimal] = mapped_column("综合评分", DECIMAL(6, 2), default=0)
    risk_level: Mapped[str | None] = mapped_column("预警级别", String(16))
    risk_color: Mapped[str | None] = mapped_column("预警颜色", String(8))
    is_direct_upgrade: Mapped[int] = mapped_column("是否直接升级", SmallInteger, default=0)
    upgrade_reason: Mapped[str | None] = mapped_column("升级原因", String(500))
    data_integrity: Mapped[str | None] = mapped_column("数据完整性", String(128))
    score_version: Mapped[str | None] = mapped_column("评分版本", String(32))
    score_time: Mapped[datetime | None] = mapped_column("评分时间", DateTime)
    created_at: Mapped[datetime] = mapped_column("创建时间", DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        "更新时间", DateTime, default=datetime.now, onupdate=datetime.now
    )


class ScoreRecord(Base):
    __tablename__ = "评分记录"

    id: Mapped[int] = mapped_column("评分记录编号", BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column("患者记录编号", BigInteger, nullable=False)
    score_version: Mapped[str] = mapped_column("评分版本", String(32), nullable=False)
    total_score: Mapped[Decimal] = mapped_column("综合评分", DECIMAL(6, 2), default=0)
    risk_level: Mapped[str] = mapped_column("预警级别", String(16), nullable=False)
    risk_color: Mapped[str] = mapped_column("预警颜色", String(8), nullable=False)
    is_direct_upgrade: Mapped[int] = mapped_column("是否直接升级", SmallInteger, default=0)
    upgrade_reason: Mapped[str | None] = mapped_column("升级原因", String(500))
    data_integrity: Mapped[str | None] = mapped_column("数据完整性", String(128))
    score_time: Mapped[datetime] = mapped_column("评分时间", DateTime, nullable=False)
    is_valid: Mapped[int] = mapped_column("是否有效", SmallInteger, default=1)


class ScoreDetail(Base):
    __tablename__ = "评分明细"

    id: Mapped[int] = mapped_column("评分明细编号", BigInteger, primary_key=True, autoincrement=True)
    score_record_id: Mapped[int] = mapped_column("评分记录编号", BigInteger, nullable=False)
    level: Mapped[str] = mapped_column("指标层级", String(16), nullable=False)
    name: Mapped[str] = mapped_column("指标名称", String(64), nullable=False)
    field: Mapped[str | None] = mapped_column("指标字段", String(64))
    raw_value: Mapped[str | None] = mapped_column("字段原值", String(1000))
    triggered: Mapped[int] = mapped_column("是否触发", SmallInteger, default=0)
    weight: Mapped[Decimal] = mapped_column("权重分", DECIMAL(5, 2), default=0)
    score: Mapped[Decimal] = mapped_column("得分", DECIMAL(5, 2), default=0)
    note: Mapped[str | None] = mapped_column("判断说明", String(500))
    missing: Mapped[int] = mapped_column("是否缺失", SmallInteger, default=0)
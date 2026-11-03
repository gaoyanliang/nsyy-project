from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from .config import SCORE_VERSION
from .models import DischargedPatient, ScoreRecord, ScoreDetail
from .scoring import score_patient, parse_datetime, parse_age, count_diagnosis


def normalize(p: dict) -> dict:
    out = dict(p)
    out["age_value"], out["age_unit"] = parse_age(p.get("age_text"))
    out["diagnosis_count"] = count_diagnosis(p.get("diagnosis"))
    return out


def save_score(db: Session, patient: DischargedPatient, result: dict, score_time: datetime):
    db.query(ScoreRecord).filter(
        ScoreRecord.patient_id == patient.id,
        ScoreRecord.is_valid == 1,
    ).update({ScoreRecord.is_valid: 0})

    rec = ScoreRecord(
        patient_id=patient.id,
        score_version=SCORE_VERSION,
        total_score=Decimal(str(result["score"])),
        risk_level=result["risk_level"],
        risk_color=result["risk_color"],
        is_direct_upgrade=result["is_direct_upgrade"],
        upgrade_reason=result["upgrade_reason"],
        data_integrity=result["data_integrity"],
        score_time=score_time,
        is_valid=1,
    )
    db.add(rec)
    db.flush()

    for d in result["score_details"]:
        db.add(ScoreDetail(
            score_record_id=rec.id,
            level=d["level"],
            name=d["name"],
            field=d["field"],
            raw_value=d["raw_value"],
            triggered=d["triggered"],
            weight=Decimal(str(d["weight"])),
            score=Decimal(str(d["score"])),
            note=d["note"],
            missing=d["missing"],
        ))

    patient.total_score = Decimal(str(result["score"]))
    patient.risk_level = result["risk_level"]
    patient.risk_color = result["risk_color"]
    patient.is_direct_upgrade = result["is_direct_upgrade"]
    patient.upgrade_reason = result["upgrade_reason"]
    patient.data_integrity = result["data_integrity"]
    patient.discharge_type = result["discharge_type"]
    patient.score_version = SCORE_VERSION
    patient.score_time = score_time


def import_one(db: Session, item: dict, score_time: datetime) -> None:
    p = normalize(item)
    discharge_date = parse_datetime(p.get("discharge_date"))
    if not discharge_date:
        raise ValueError("discharge_date invalid")

    times = p.get("admission_times")
    try:
        times = int(times) if times is not None else 0
    except (TypeError, ValueError):
        times = 0

    existing = db.execute(
        select(DischargedPatient).where(
            DischargedPatient.bingrenzyid == p["bingrenzyid"],
            DischargedPatient.admission_no == p.get("admission_no"),
            DischargedPatient.admission_times == times,
            DischargedPatient.discharge_date == discharge_date,
        )
    ).scalars().first()

    if existing:
        patient = existing
    else:
        patient = DischargedPatient(
            bingrenzyid=p["bingrenzyid"],
            admission_no=p.get("admission_no"),
            admission_times=times,
            discharge_date=discharge_date,
        )
        db.add(patient)
        db.flush()

    patient.patient_name = p.get("patient_name")
    patient.age_text = p.get("age_text")
    patient.age_value = p.get("age_value")
    patient.age_unit = p.get("age_unit")
    patient.birth_date = parse_datetime(p.get("birth_date"))
    patient.admission_date = parse_datetime(p.get("admission_date"))
    patient.stay_days = p.get("stay_days")
    patient.discharge_dept = p.get("discharge_dept")
    patient.icu_discharge = p.get("icu_discharge")
    patient.discharge_mode = p.get("discharge_mode")
    patient.abandon_treatment = p.get("abandon_treatment")
    patient.auto_discharge = p.get("auto_discharge")
    patient.rescue_record = p.get("rescue_record")
    patient.transfer_dept = p.get("transfer_dept")
    patient.admission_critical = p.get("admission_critical")
    patient.diagnosis = p.get("diagnosis")
    patient.diagnosis_count = p.get("diagnosis_count") or 0
    patient.emergency_admission = p.get("emergency_admission")
    patient.total_cost = p.get("total_cost")
    patient.marital_status = p.get("marital_status")
    patient.occupation = p.get("occupation")
    patient.payment_type = p.get("payment_type")
    patient.death_order = p.get("death_order")
    patient.death_case = p.get("death_case")
    patient.discharge_drugs = p.get("discharge_drugs")
    patient.palliative_drug = p.get("palliative_drug")
    patient.terminal_disease = p.get("terminal_disease")
    patient.refuse_surgery = p.get("refuse_surgery")
    patient.patient_request_discharge = p.get("patient_request_discharge")

    result = score_patient(p)
    save_score(db, patient, result, score_time)


def import_many(db: Session, items: list[dict]) -> dict:
    score_time = datetime.now()
    ok, fail, failures = 0, 0, []
    for item in items:
        try:
            with db.begin_nested():
                import_one(db, item, score_time)
            ok += 1
        except Exception as e:
            fail += 1
            failures.append({"bingrenzyid": item.get("bingrenzyid"), "error": str(e)})
    db.commit()
    return {
        "total": len(items),
        "success": ok,
        "failed": fail,
        "failures": failures,
        "score_time": score_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def rescore_by_range(db: Session, start: datetime, end: datetime) -> dict:
    rows = db.execute(
        select(DischargedPatient).where(
            DischargedPatient.discharge_date >= start,
            DischargedPatient.discharge_date <= end,
        )
    ).scalars().all()

    score_time = datetime.now()
    ok, fail = 0, 0
    for patient in rows:
        try:
            with db.begin_nested():
                p = {
                    "stay_days": patient.stay_days,
                    "age_text": patient.age_text,
                    "diagnosis": patient.diagnosis,
                    "icu_discharge": patient.icu_discharge,
                    "rescue_record": patient.rescue_record,
                    "admission_critical": patient.admission_critical,
                    "transfer_dept": patient.transfer_dept,
                    "discharge_mode": patient.discharge_mode,
                    "emergency_admission": patient.emergency_admission,
                    "marital_status": patient.marital_status,
                    "discharge_drugs": patient.discharge_drugs,
                    "palliative_drug": patient.palliative_drug,
                    "occupation": patient.occupation,
                    "payment_type": patient.payment_type,
                    "terminal_disease": patient.terminal_disease,
                    "refuse_surgery": patient.refuse_surgery,
                    "abandon_treatment": patient.abandon_treatment,
                    "auto_discharge": patient.auto_discharge,
                    "patient_request_discharge": patient.patient_request_discharge,
                    "death_case": patient.death_case,
                    "death_order": patient.death_order,
                }
                result = score_patient(p)
                save_score(db, patient, result, score_time)
            ok += 1
        except Exception:
            fail += 1
    db.commit()
    return {
        "total": len(rows),
        "success": ok,
        "failed": fail,
        "score_time": score_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def query_patients(db: Session, params: dict) -> tuple[int, list[DischargedPatient]]:
    q = db.query(DischargedPatient)
    if params.get("date_start"):
        q = q.filter(DischargedPatient.discharge_date >= params["date_start"])
    if params.get("date_end"):
        end = datetime.combine(params["date_end"].date(), datetime.max.time())
        q = q.filter(DischargedPatient.discharge_date <= end)
    if params.get("risk_level"):
        q = q.filter(DischargedPatient.risk_level == params["risk_level"])
    if params.get("dept"):
        q = q.filter(DischargedPatient.discharge_dept.like(f"%{params['dept']}%"))
    if params.get("discharge_type"):
        q = q.filter(DischargedPatient.discharge_type == params["discharge_type"])
    if params.get("keyword"):
        kw = f"%{params['keyword']}%"
        q = q.filter(or_(
            DischargedPatient.patient_name.like(kw),
            DischargedPatient.admission_no.like(kw),
            DischargedPatient.bingrenzyid.like(kw),
        ))
    total = q.count()
    rows = q.order_by(
        DischargedPatient.discharge_date.desc(),
        DischargedPatient.total_score.desc(),
    ).offset((params["page"] - 1) * params["page_size"]).limit(params["page_size"]).all()
    return total, rows


def query_patient_detail(db: Session, patient_id: int) -> dict | None:
    patient = db.get(DischargedPatient, patient_id)
    if not patient:
        return None
    rec = db.execute(
        select(ScoreRecord).where(
            ScoreRecord.patient_id == patient_id,
            ScoreRecord.is_valid == 1,
        ).order_by(ScoreRecord.id.desc())
    ).scalars().first()
    details = []
    if rec:
        ds = db.execute(
            select(ScoreDetail)
            .where(ScoreDetail.score_record_id == rec.id)
            .order_by(ScoreDetail.id.asc())
        ).scalars().all()
        details = [{
            "level": d.level, "name": d.name, "field": d.field,
            "raw_value": d.raw_value, "triggered": d.triggered,
            "weight": float(d.weight), "score": float(d.score),
            "note": d.note, "missing": d.missing,
        } for d in ds]

    return {
        "patient": {
            "id": patient.id,
            "bingrenzyid": patient.bingrenzyid,
            "admission_no": patient.admission_no,
            "admission_times": patient.admission_times,
            "patient_name": patient.patient_name,
            "age_text": patient.age_text,
            "discharge_date": patient.discharge_date.strftime("%Y-%m-%d %H:%M:%S") if patient.discharge_date else None,
            "discharge_dept": patient.discharge_dept,
            "stay_days": patient.stay_days,
            "discharge_type": patient.discharge_type,
            "total_score": float(patient.total_score or 0),
            "risk_level": patient.risk_level,
            "risk_color": patient.risk_color,
            "is_direct_upgrade": patient.is_direct_upgrade,
            "upgrade_reason": patient.upgrade_reason,
            "data_integrity": patient.data_integrity,
            "score_version": patient.score_version,
            "score_time": patient.score_time.strftime("%Y-%m-%d %H:%M:%S") if patient.score_time else None,
        },
        "raw": {
            "age_text": patient.age_text,
            "stay_days": patient.stay_days,
            "diagnosis": patient.diagnosis,
            "total_cost": float(patient.total_cost) if patient.total_cost is not None else None,
            "discharge_mode": patient.discharge_mode,
            "icu_discharge": patient.icu_discharge,
            "abandon_treatment": patient.abandon_treatment,
            "auto_discharge": patient.auto_discharge,
            "rescue_record": patient.rescue_record,
            "transfer_dept": patient.transfer_dept,
            "admission_critical": patient.admission_critical,
            "emergency_admission": patient.emergency_admission,
            "death_case": patient.death_case,
            "death_order": patient.death_order,
            "palliative_drug": patient.palliative_drug,
            "refuse_surgery": patient.refuse_surgery,
            "patient_request_discharge": patient.patient_request_discharge,
            "marital_status": patient.marital_status,
            "occupation": patient.occupation,
            "payment_type": patient.payment_type,
            "terminal_disease": patient.terminal_disease,
            "discharge_drugs": patient.discharge_drugs,
        },
        "score_details": details,
    }



def _build_score_input(patient: DischargedPatient) -> dict:
    return {
        "stay_days": patient.stay_days,
        "age_text": patient.age_text,
        "diagnosis": patient.diagnosis,
        "icu_discharge": patient.icu_discharge,
        "rescue_record": patient.rescue_record,
        "admission_critical": patient.admission_critical,
        "transfer_dept": patient.transfer_dept,
        "discharge_mode": patient.discharge_mode,
        "emergency_admission": patient.emergency_admission,
        "marital_status": patient.marital_status,
        "discharge_drugs": patient.discharge_drugs,
        "palliative_drug": patient.palliative_drug,
        "occupation": patient.occupation,
        "payment_type": patient.payment_type,
        "terminal_disease": patient.terminal_disease,
        "refuse_surgery": patient.refuse_surgery,
        "abandon_treatment": patient.abandon_treatment,
        "auto_discharge": patient.auto_discharge,
        "patient_request_discharge": patient.patient_request_discharge,
        "death_case": patient.death_case,
        "death_order": patient.death_order,
    }


def _score_and_save(db: Session, patient: DischargedPatient):
    result = score_patient(_build_score_input(patient))
    score_time = datetime.now()
    save_score(db, patient, result, score_time)
    return result, score_time


def _result_dict(patient_id: int, result: dict, score_time: datetime) -> dict:
    return {
        "patient_id": patient_id,
        "total_score": result["score"],
        "risk_level": result["risk_level"],
        "risk_color": result["risk_color"],
        "is_direct_upgrade": result["is_direct_upgrade"],
        "upgrade_reason": result["upgrade_reason"],
        "discharge_type": result["discharge_type"],
        "data_integrity": result["data_integrity"],
        "score_time": score_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def rescore_one(db: Session, patient_id: int) -> dict | None:
    patient = db.get(DischargedPatient, patient_id)
    if not patient:
        return None
    result, score_time = _score_and_save(db, patient)
    db.commit()
    return _result_dict(patient.id, result, score_time)


# 允许通过 PUT 更新的字段白名单
UPDATABLE_FIELDS = {
    "age_text", "stay_days", "diagnosis", "total_cost",
    "discharge_mode", "icu_discharge", "abandon_treatment", "auto_discharge",
    "rescue_record", "transfer_dept", "admission_critical", "emergency_admission",
    "death_case", "death_order", "palliative_drug", "refuse_surgery",
    "patient_request_discharge", "marital_status", "occupation", "payment_type",
    "terminal_disease", "discharge_drugs",
}


def update_patient_fields(db: Session, patient_id: int, fields: dict) -> dict | None:
    patient = db.get(DischargedPatient, patient_id)
    if not patient:
        return None

    for k, v in fields.items():
        if k in UPDATABLE_FIELDS:
            setattr(patient, k, v)

    # 重算派生字段
    patient.age_value, patient.age_unit = parse_age(patient.age_text)
    patient.diagnosis_count = count_diagnosis(patient.diagnosis)

    db.flush()
    result, score_time = _score_and_save(db, patient)
    db.commit()
    return _result_dict(patient.id, result, score_time)


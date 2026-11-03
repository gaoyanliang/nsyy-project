import io
import json as jsonlib
import logging
from datetime import datetime, date

from flask import Blueprint
from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy import func

from gylmodules.discharge_risk.redis_client import redis_client
from gylmodules.discharge_risk.config import RISK_KEY
from gylmodules.discharge_risk.crud import import_many, rescore_by_range, query_patients, rescore_one, \
    update_patient_fields, query_patient_detail
from gylmodules.discharge_risk.database import get_db
from gylmodules.discharge_risk.models import DischargedPatient
from gylmodules.discharge_risk.redis_client import acquire_lock, clear_stat_cache, release_lock
from gylmodules.discharge_risk.schemas import PatientImportItem, PatientUpdateItem
from gylmodules.discharge_risk.dr_response import dr_api_response as api_response

logger = logging.getLogger(__name__)
dr_system = Blueprint('Discharge Risk Alert', __name__, url_prefix='/dr')

MAX_FILE_SIZE = 50 * 1024 * 1024


def _clean_cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (int, float)):
        f = float(v)
        if f.is_integer():
            return str(int(f))
        return repr(f)
    return str(v).strip()


def _parse_xlsx(content: bytes) -> list[dict]:
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        raise Exception(400, f"Excel 解析失败: {e}")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise Exception(400, "Excel 内容为空")

    header_idx = 0
    for i, row in enumerate(rows):
        if any(c is not None and str(c).strip() for c in row):
            header_idx = i
            break

    headers = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    if "bingrenzyid" not in headers and "病人住院标识" not in headers:
        raise Exception(400, "Excel 缺少 bingrenzyid 或 病人住院标识 列")

    items = []
    for r in rows[header_idx + 1:]:
        if not any(c is not None and str(c).strip() for c in r):
            continue
        d = {}
        for j, h in enumerate(headers):
            if not h:
                continue
            d[h] = _clean_cell(r[j] if j < len(r) else None)
        if not d.get("bingrenzyid") and d.get("病人住院标识"):
            d["bingrenzyid"] = d["病人住院标识"]
        if not d.get("bingrenzyid"):
            continue
        items.append(d)
    return items


def _parse_items(items: list[dict], start_row: int = 1):
    parsed, failures = [], []
    for i, it in enumerate(items):
        try:
            parsed.append(PatientImportItem(**it).model_dump())
        except ValidationError as e:
            failures.append({
                "row": i + start_row,
                "error": str(e)[:300],
                "bingrenzyid": str(it.get("bingrenzyid") or it.get("病人住院标识") or "")[:64],
            })
    return parsed, failures


@dr_system.route("/patients/import", methods=["POST"])
@api_response
def import_patients(json_data):
    items = json_data.get("_list") or []
    if not items:
        raise Exception(400, "请求体必须是患者数组，例如 [{...}]")

    if not acquire_lock("lock:import", expire=900):
        raise Exception(409, "已有导入任务执行中，请稍后重试")
    try:
        db = get_db()
        parsed, failures = _parse_items(items, start_row=1)
        if not parsed:
            return {
                "total": len(items), "success": 0,
                "failed": len(failures), "failures": failures,
                "score_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        result = import_many(db, parsed)
        result["total"] = len(items)
        result["failed"] += len(failures)
        result["failures"] = failures + result["failures"]
        clear_stat_cache()
        return result
    finally:
        release_lock("lock:import")


@dr_system.route("/patients/import-file", methods=["POST"])
@api_response
def import_file(json_data):
    files = json_data.get("_files") or {}
    file = files.get("file")
    if not file:
        raise Exception(400, "缺少上传文件字段 file")

    if not acquire_lock("lock:import", expire=900):
        raise Exception(409, "已有导入任务执行中，请稍后重试")

    try:
        content = file.read()
        if not content:
            raise Exception(400, "文件为空")
        if len(content) > MAX_FILE_SIZE:
            raise Exception(413, "文件超过 50MB，请分批导入")

        name = (file.filename or "").lower()
        if name.endswith(".xlsx") or name.endswith(".xlsm"):
            raw_items = _parse_xlsx(content)
        elif name.endswith(".xls"):
            raise Exception(400, "不支持 .xls 旧格式，请另存为 .xlsx")
        elif name.endswith(".json"):
            try:
                raw_items = jsonlib.loads(content.decode("utf-8"))
            except Exception as e:
                raise Exception(400, f"JSON 解析失败: {e}")
            if not isinstance(raw_items, list):
                raise Exception(400, "JSON 根节点必须是数组")
        else:
            raise Exception(400, "仅支持 .xlsx / .json")

        if not raw_items:
            raise Exception(400, "未解析到任何患者数据")

        db = get_db()
        parsed, failures = _parse_items(raw_items, start_row=2)

        score_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not parsed:
            return {
                "total": len(raw_items), "success": 0,
                "failed": len(failures), "failures": failures,
                "score_time": score_time,
            }

        result = import_many(db, parsed)
        result["total"] = len(raw_items)
        result["failed"] += len(failures)
        result["failures"] = failures + result["failures"]
        clear_stat_cache()
        return result
    finally:
        release_lock("lock:import")


@dr_system.route("/patients/score", methods=["POST"])
@api_response
def rescore(json_data):
    date_start = json_data.get("date_start")
    date_end = json_data.get("date_end")
    if not date_start or not date_end:
        raise Exception(400, "date_start 和 date_end 必填")
    try:
        start = datetime.strptime(date_start, "%Y-%m-%d")
        end = datetime.strptime(date_end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise Exception(400, "日期格式应为 YYYY-MM-DD")
    db = get_db()
    result = rescore_by_range(db, start, end)
    clear_stat_cache()
    return result


@dr_system.route("/patients", methods=["GET"])
@api_response
def list_patients(json_data):
    def _pd(v):
        return datetime.strptime(v, "%Y-%m-%d") if v else None

    try:
        page = int(json_data.get("page") or 1)
        page_size = int(json_data.get("page_size") or 20)
    except ValueError:
        raise Exception(400, "page / page_size 必须是整数")
    if page < 1 or page_size < 1 or page_size > 100:
        raise Exception(400, "page>=1 且 1<=page_size<=100")

    params = {
        "date_start": _pd(json_data.get("date_start")),
        "date_end": _pd(json_data.get("date_end")),
        "risk_level": json_data.get("risk_level"),
        "dept": json_data.get("dept"),
        "discharge_type": json_data.get("discharge_type"),
        "keyword": json_data.get("keyword"),
        "page": page,
        "page_size": page_size,
    }
    db = get_db()
    total, rows = query_patients(db, params)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": r.id,
            "bingrenzyid": r.bingrenzyid,
            "admission_no": r.admission_no,
            "patient_name": r.patient_name,
            "age_text": r.age_text,
            "discharge_date": r.discharge_date.strftime("%Y-%m-%d %H:%M:%S") if r.discharge_date else None,
            "discharge_dept": r.discharge_dept,
            "stay_days": r.stay_days,
            "discharge_type": r.discharge_type,
            "total_score": float(r.total_score or 0),
            "risk_level": r.risk_level,
            "risk_color": r.risk_color,
            "is_direct_upgrade": r.is_direct_upgrade,
            "upgrade_reason": r.upgrade_reason,
            "data_integrity": r.data_integrity,
        } for r in rows],
    }


@dr_system.route("/patients/<int:patient_id>/rescore", methods=["POST"])
@api_response
def rescore_single(json_data):
    patient_id = json_data["patient_id"]
    db = get_db()
    result = rescore_one(db, patient_id)
    if not result:
        raise Exception(404, "patient not found")
    clear_stat_cache()
    return result


@dr_system.route("/patients/<int:patient_id>", methods=["PUT"])
@api_response
def update_patient(json_data):
    patient_id = json_data["patient_id"]
    payload_dict = {k: v for k, v in json_data.items() if k != "patient_id"}
    try:
        payload = PatientUpdateItem(**payload_dict)
    except ValidationError as e:
        raise Exception(422, str(e))

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise Exception(400, "没有需要更新的字段")

    db = get_db()
    result = update_patient_fields(db, patient_id, fields)
    if not result:
        raise Exception(404, "patient not found")
    clear_stat_cache()
    return result


@dr_system.route("/patients/<int:patient_id>", methods=["GET"])
@api_response
def patient_detail(json_data):
    patient_id = json_data["patient_id"]
    db = get_db()
    data = query_patient_detail(db, patient_id)
    if not data:
        raise Exception(404, "patient not found")
    return data


@dr_system.route("/statistics/daily", methods=["GET"])
@api_response
def daily_statistics(json_data):
    date_start = json_data.get("date_start")
    date_end = json_data.get("date_end")
    if not date_start or not date_end:
        raise Exception(400, "date_start 和 date_end 必填")

    dept = json_data.get("dept")
    discharge_type = json_data.get("discharge_type")
    keyword = json_data.get("keyword")

    cache_key = f"stat:daily:{date_start}:{date_end}:{dept or ''}:{discharge_type or ''}:{keyword or ''}"
    cached = redis_client.get(cache_key)
    if cached:
        return jsonlib.loads(cached)

    try:
        start = datetime.strptime(date_start, "%Y-%m-%d")
        end = datetime.strptime(date_end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise Exception(400, "日期格式应为 YYYY-MM-DD")

    db = get_db()
    base = db.query(DischargedPatient).filter(
        DischargedPatient.discharge_date >= start,
        DischargedPatient.discharge_date <= end,
    )
    if dept:
        base = base.filter(DischargedPatient.discharge_dept.like(f"%{dept}%"))
    if discharge_type:
        base = base.filter(DischargedPatient.discharge_type == discharge_type)
    if keyword:
        kw = f"%{keyword}%"
        base = base.filter(
            (DischargedPatient.patient_name.like(kw))
            | (DischargedPatient.admission_no.like(kw))
            | (DischargedPatient.bingrenzyid.like(kw))
        )

    total = base.count()
    direct_count = base.filter(DischargedPatient.is_direct_upgrade == 1).count()

    level_rows = base.with_entities(
        DischargedPatient.risk_level, func.count(DischargedPatient.id)
    ).group_by(DischargedPatient.risk_level).all()
    risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for lv, c in level_rows:
        if lv in RISK_KEY:
            risk_distribution[RISK_KEY[lv]] = c

    type_rows = base.with_entities(
        DischargedPatient.discharge_type, func.count(DischargedPatient.id)
    ).group_by(DischargedPatient.discharge_type).all()
    type_distribution = {(t or "其他"): c for t, c in type_rows}

    dept_rows = base.with_entities(
        DischargedPatient.discharge_dept, func.count(DischargedPatient.id)
    ).group_by(DischargedPatient.discharge_dept).order_by(
        func.count(DischargedPatient.id).desc()
    ).limit(20).all()

    dept_distribution = []
    for d, c in dept_rows:
        high = base.filter(
            DischargedPatient.discharge_dept == d,
            DischargedPatient.risk_level.in_(["高风险", "极高风险"]),
        ).count()
        dept_distribution.append({"dept": d, "total": c, "high_and_above": high})

    result = {
        "total_discharged": total,
        "risk_distribution": risk_distribution,
        "direct_upgrade_count": direct_count,
        "discharge_type_distribution": type_distribution,
        "dept_distribution": dept_distribution,
    }
    redis_client.set(cache_key, jsonlib.dumps(result, ensure_ascii=False), ex=60)
    return result






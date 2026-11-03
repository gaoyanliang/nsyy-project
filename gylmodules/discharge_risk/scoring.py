import re
from datetime import datetime
import math
from datetime import datetime, date, timedelta

from .config import (
    RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL, RISK_COLOR, RISK_RANK,
    RED_DIRECT_FIELDS, RED_DIRECT_LEAVE_MODE, ORANGE_DIRECT_FIELDS,
)


def to_text(v) -> str:
    return "" if v is None else str(v).strip()


def is_yes(v) -> bool:
    return to_text(v) in ("是", "1", "true", "True", "Y", "y")


def is_not_empty(v) -> bool:
    return to_text(v) not in ("", "否", "无", "None", "null")


def parse_datetime(v) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)

    if isinstance(v, (int, float)) and not isinstance(v, bool):
        f = float(v)
        if 1 < f < 100000:
            return datetime(1899, 12, 30) + timedelta(days=f)
        return None

    t = str(v or "")
    # 去不可见字符、全角空格、BOM
    t = (
        t.replace("\u200b", "")
        .replace("\ufeff", "")
        .replace("\u00a0", " ")
        .replace("　", " ")
        .strip()
    )
    if not t:
        return None

    # 纯数字字符串按 Excel 序列号处理
    try:
        f = float(t)
        if 1 < f < 100000 and math.isfinite(f):
            return datetime(1899, 12, 30) + timedelta(days=f)
    except ValueError:
        pass

    fmts = [
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
        "%Y.%m.%d %H:%M:%S", "%Y.%m.%d",
        "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M", "%Y年%m月%d日",
        "%Y%m%d %H:%M:%S", "%Y%m%d",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(t, f)
        except ValueError:
            continue
    return None

def parse_age(v) -> tuple[int | None, str | None]:
    t = to_text(v)
    if not t:
        return None, None
    m = re.search(r"(\d+)", t)
    if not m:
        return None, None
    num = int(m.group(1))
    if "岁" in t:
        return num, "岁"
    if "月" in t:
        return num, "月"
    return num, "岁"


def split_diagnosis(diagnosis) -> list[str]:
    t = to_text(diagnosis)
    if not t:
        return []
    return [x.strip() for x in re.split(r"[、;；]", t) if x.strip()]


def count_diagnosis(diagnosis) -> int:
    return len(split_diagnosis(diagnosis))


def resolve_discharge_type(p: dict) -> str:
    if is_yes(p.get("death_case")) or is_not_empty(p.get("death_order")):
        return "死亡"
    if is_yes(p.get("abandon_treatment")):
        return "放弃治疗"
    if is_yes(p.get("auto_discharge")):
        return "自动出院"
    if is_yes(p.get("patient_request_discharge")):
        return "患者要求出院"
    mode = to_text(p.get("discharge_mode"))
    if mode == "非医嘱离院":
        return "非医嘱离院"
    if mode == "医嘱离院":
        return "医嘱离院"
    return "其他"


def check_data_integrity(p: dict, stay_days, age_value) -> str:
    missing = []
    has_discharge_flag = (
        is_yes(p.get("abandon_treatment"))
        or is_yes(p.get("auto_discharge"))
        or is_yes(p.get("patient_request_discharge"))
    )
    if not to_text(p.get("discharge_mode")) and not has_discharge_flag:
        missing.append("离院标识")
    if not to_text(p.get("diagnosis")):
        missing.append("诊断")
    if age_value is None:
        missing.append("年龄")
    if stay_days is None:
        missing.append("天数")
    return "完整" if not missing else "缺失:" + ",".join(missing)


def level_by_score(score: float) -> str:
    if score >= 18:
        return RISK_CRITICAL
    if score >= 12:
        return RISK_HIGH
    if score >= 6:
        return RISK_MEDIUM
    return RISK_LOW


def score_patient(p: dict) -> dict:
    """
    输入 p：英文字段 dict（导入项 model_dump 后的结果）。
    返回：score / risk_level / risk_color / is_direct_upgrade /
          upgrade_reason / score_details / discharge_type / data_integrity。
    满分 35：核心 6×3=18，重要 6×2=12，参考 5×1=5。
    """
    details: list[dict] = []
    score = 0.0

    def add(level, name, field, raw, triggered, weight, note, missing=False):
        nonlocal score
        got = weight if triggered else 0
        score += got
        details.append({
            "level": level,
            "name": name,
            "field": field,
            "raw_value": to_text(raw)[:1000],
            "triggered": 1 if triggered else 0,
            "weight": weight,
            "score": got,
            "note": note,
            "missing": 1 if missing else 0,
        })

    stay_days = p.get("stay_days")
    try:
        stay_days = int(stay_days) if stay_days not in (None, "") else None
    except (TypeError, ValueError):
        stay_days = None

    age_value, age_unit = parse_age(p.get("age_text"))
    diag_count = count_diagnosis(p.get("diagnosis"))

    # ===== 核心指标 3 分 =====
    add("核心", "是否拒绝手术", "refuse_surgery", p.get("refuse_surgery"),
        is_yes(p.get("refuse_surgery")), 3,
        "refuse_surgery=是" if is_yes(p.get("refuse_surgery")) else "未触发")

    add("核心", "ICU出院", "icu_discharge", p.get("icu_discharge"),
        is_yes(p.get("icu_discharge")), 3,
        "icu_discharge=是" if is_yes(p.get("icu_discharge")) else "未触发")

    add("核心", "抢救记录", "rescue_record", p.get("rescue_record"),
        is_yes(p.get("rescue_record")), 3,
        "rescue_record=是" if is_yes(p.get("rescue_record")) else "未触发")

    add("核心", "入院病情危急", "admission_critical", p.get("admission_critical"),
        is_yes(p.get("admission_critical")), 3,
        "admission_critical=是" if is_yes(p.get("admission_critical")) else "未触发")

    add("核心", "转科", "transfer_dept", p.get("transfer_dept"),
        is_yes(p.get("transfer_dept")), 3,
        "transfer_dept=是" if is_yes(p.get("transfer_dept")) else "未触发")

    non_order = to_text(p.get("discharge_mode")) == "非医嘱离院"
    add("核心", "非医嘱离院", "discharge_mode", p.get("discharge_mode"),
        non_order, 3,
        "discharge_mode=非医嘱离院" if non_order else "未触发",
        missing=not to_text(p.get("discharge_mode")))

    # ===== 重要指标 2 分 =====
    short_stay = stay_days is not None and stay_days < 3
    add("重要", "住院天数过短", "stay_days", p.get("stay_days"),
        short_stay, 2,
        f"stay_days={stay_days}，<3" if short_stay else "未触发",
        missing=stay_days is None)

    many_diag = diag_count >= 3
    add("重要", "诊断数量多", "diagnosis", p.get("diagnosis"),
        many_diag, 2,
        f"诊断数量={diag_count}，>=3" if many_diag else f"诊断数量={diag_count}，未触发")

    add("重要", "急诊入院", "emergency_admission", p.get("emergency_admission"),
        is_yes(p.get("emergency_admission")), 2,
        "emergency_admission=是" if is_yes(p.get("emergency_admission")) else "未触发")

    old_age = age_value is not None and age_unit == "岁" and age_value >= 75
    add("重要", "高龄", "age_text", p.get("age_text"),
        old_age, 2,
        f"年龄={age_value}岁，>=75" if old_age else "未触发")

    widowed = to_text(p.get("marital_status")) == "丧偶"
    add("重要", "丧偶", "marital_status", p.get("marital_status"),
        widowed, 2,
        "marital_status=丧偶" if widowed else "未触发")

    drugs_empty = not to_text(p.get("discharge_drugs"))
    palliative = is_yes(p.get("palliative_drug"))
    add("重要", "出院带药少/姑息", "discharge_drugs", p.get("discharge_drugs"),
        drugs_empty or palliative, 2,
        "出院带药为空（按无带药处理）" if drugs_empty else ("仅姑息药品" if palliative else "未触发"))

    # ===== 参考指标 1 分 =====
    marital = to_text(p.get("marital_status"))
    add("参考", "离婚/未婚", "marital_status", marital,
        marital in ("离婚", "未婚"), 1,
        f"marital_status={marital}" if marital in ("离婚", "未婚") else "未触发")

    add("参考", "稳定工作", "occupation", p.get("occupation"),
        to_text(p.get("occupation")) == "职员", 1,
        "occupation=职员" if to_text(p.get("occupation")) == "职员" else "未触发")

    add("参考", "自费", "payment_type", p.get("payment_type"),
        to_text(p.get("payment_type")) == "自费", 1,
        "payment_type=自费" if to_text(p.get("payment_type")) == "自费" else "未触发")

    diag_text = to_text(p.get("diagnosis"))
    add("参考", "未愈", "diagnosis", diag_text,
        "未愈" in diag_text, 1,
        "诊断含未愈" if "未愈" in diag_text else "未触发")

    terminal = to_text(p.get("terminal_disease"))
    add("参考", "终末期疾病", "terminal_disease", terminal,
        terminal not in ("", "否", "无"), 1,
        "terminal_disease 非空" if terminal not in ("", "否", "无") else "未触发")

    # ===== 直接升级规则 =====
    red_reasons, orange_reasons = [], []
    for f in RED_DIRECT_FIELDS:
        if is_yes(p.get(f)):
            red_reasons.append(f"{f}=是")
    if to_text(p.get("discharge_mode")) == RED_DIRECT_LEAVE_MODE:
        red_reasons.append("discharge_mode=非医嘱离院")
    for f in ORANGE_DIRECT_FIELDS:
        if is_yes(p.get(f)):
            orange_reasons.append(f"{f}=是")

    level = level_by_score(score)
    is_direct = 0
    reasons: list[str] = []
    if red_reasons:
        level = RISK_CRITICAL
        is_direct = 1
        reasons.extend(red_reasons)
    elif orange_reasons:
        if RISK_RANK[level] < RISK_RANK[RISK_HIGH]:
            level = RISK_HIGH
        is_direct = 1
        reasons.extend(orange_reasons)

    add("直接升级", "直接升级规则", "discharge_flag",
        "；".join(reasons), bool(reasons), 0,
        "；".join(reasons) if reasons else "未触发直接升级")

    discharge_type = resolve_discharge_type(p)
    data_integrity = check_data_integrity(p, stay_days, age_value)

    return {
        "score": round(score, 2),
        "risk_level": level,
        "risk_color": RISK_COLOR[level],
        "is_direct_upgrade": is_direct,
        "upgrade_reason": "；".join(reasons),
        "score_details": details,
        "discharge_type": discharge_type,
        "data_integrity": data_integrity,
    }
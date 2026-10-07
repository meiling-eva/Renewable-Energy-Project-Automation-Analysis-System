import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.cleaning.common import (
    CleanResult,
    RowResult,
    bump,
    empty_report,
    map_columns,
    merge_stats,
    new_stats,
    parse_date,
    slugify,
    standardize_missing,
)
from app.models import CheckStatus, Severity

ALIASES: Dict[str, List[str]] = {
    "project_id": ["project_id", "projectid", "project_no", "project_number"],
    "project_name": ["project_name", "project", "site_name", "site"],
    "rule_code": ["rule_code", "code", "rule_id", "rule"],
    "rule_name": ["rule_name", "name", "rule_description", "check", "check_name"],
    "severity": ["severity", "priority", "level", "risk"],
    "status": ["status", "result", "outcome"],
    "message": ["message", "details", "detail", "notes", "comment", "comments"],
    "created_at": ["created_at", "created", "date", "checked_at", "check_date"],
}
FIELDS = [f for f in ALIASES if f != "project_name"]

SEVERITY_SYNONYMS = {
    "critical": "critical", "crit": "critical", "blocker": "critical", "fatal": "critical",
    "high": "high", "h": "high", "major": "high", "error": "high",
    "medium": "medium", "med": "medium", "m": "medium", "moderate": "medium", "warning": "medium", "warn": "medium",
    "low": "low", "l": "low", "minor": "low", "info": "low", "informational": "low",
}
STATUS_SYNONYMS = {
    "passed": "passed", "pass": "passed", "ok": "passed", "success": "passed", "compliant": "passed",
    "yes": "passed", "true": "passed",
    "failed": "failed", "fail": "failed", "failure": "failed", "non_compliant": "failed",
    "noncompliant": "failed", "error": "failed", "no": "failed", "false": "failed",
    "warning": "warning", "warn": "warning", "caution": "warning",
    "pending": "pending", "todo": "pending", "in_progress": "pending", "not_started": "pending",
    "open": "pending", "queued": "pending",
}


def _parse_int(value: Any) -> Optional[int]:
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    return int(number) if number.is_integer() and number > 0 else None


def _clean_row(
    row_number: int,
    raw: pd.Series,
    mapping: Dict[str, Any],
    stats: Dict[str, Any],
    project_ids: Optional[Set[int]],
    project_names: Optional[Dict[str, int]],
    now: datetime,
) -> RowResult:
    def get(field: str) -> Any:
        return raw[mapping[field]] if field in mapping else None

    result = RowResult(row=row_number, data={})
    data, errors, warnings = result.data, result.errors, result.warnings

    for field in mapping:
        if field != "project_name" and get(field) is None:
            bump(stats["missing_values"], field)

    raw_id, raw_name = get("project_id"), get("project_name")
    project_id = None
    if raw_id is not None:
        project_id = _parse_int(raw_id)
        if project_id is None:
            errors["project_id"] = f"Not a valid project id: {raw_id!r}"
    elif raw_name is not None and project_names is not None:
        project_id = project_names.get(str(raw_name).strip().lower())
        if project_id is None:
            errors["project_id"] = f"No project named {raw_name!r}"
        else:
            warnings["project_id"] = f"Matched project name {raw_name!r}"
    else:
        errors["project_id"] = "Required"
    if project_id is not None and project_ids is not None and project_id not in project_ids:
        errors["project_id"] = f"Project {project_id} not found"
    data["project_id"] = project_id

    code = get("rule_code")
    data["rule_code"] = re.sub(r"\s+", "-", str(code).strip().upper()) if code is not None else None
    if not data["rule_code"]:
        errors["rule_code"] = "Required"
    elif len(data["rule_code"]) > 50:
        errors["rule_code"] = "Longer than 50 characters"

    name = get("rule_name")
    if name is None and data["rule_code"]:
        data["rule_name"] = data["rule_code"]
        bump(stats["filled_values"], "rule_name")
        warnings["rule_name"] = "Missing; used rule_code"
    else:
        data["rule_name"] = None if name is None else str(name).strip()
        if not data["rule_name"]:
            errors["rule_name"] = "Required"
        elif len(data["rule_name"]) > 255:
            errors["rule_name"] = "Longer than 255 characters"

    for field, synonyms, default, enum in (
        ("severity", SEVERITY_SYNONYMS, Severity.low.value, Severity),
        ("status", STATUS_SYNONYMS, CheckStatus.pending.value, CheckStatus),
    ):
        value = get(field)
        if value is None:
            data[field] = default
            bump(stats["filled_values"], field)
            warnings[field] = f"Missing; defaulted to {default}"
            continue
        data[field] = synonyms.get(slugify(value))
        if data[field] is None:
            data[field] = str(value)
            errors[field] = f"Unknown {field} {value!r}; expected {', '.join(e.value for e in enum)}"

    message = get("message")
    data["message"] = None if message is None else str(message).strip()

    created, error = parse_date(get("created_at"), now)
    if error:
        errors["created_at"] = error
        stats["invalid_dates"] += 1
    data["created_at"] = created.isoformat() if created and not error else None

    return result


def clean_compliance_checks(
    df: pd.DataFrame,
    project_ids: Optional[Set[int]] = None,
    project_names: Optional[Dict[str, int]] = None,
    now: Optional[datetime] = None,
) -> CleanResult:
    """
    Cleans raw compliance-check rows: drops empty and duplicate rows, normalises severity/status
    synonyms, fills missing severity/status/rule_name, resolves project names and validates dates.
    Pass `project_ids` / `project_names` (lower-cased name -> id) to validate project references.
    """
    now = now or datetime.now()
    mapping, _ = map_columns(df.columns, ALIASES)
    report = empty_report(len(df), mapping, FIELDS)
    if "project_name" in mapping and "project_id" in report["unmapped_fields"]:
        report["unmapped_fields"].remove("project_id")
    if df.empty:
        return CleanResult([], report)

    src = standardize_missing(df)
    empty = src.isna().all(axis=1)
    report["empty_rows_removed"] = int(empty.sum())

    kept: List[RowResult] = []
    first_seen: Dict[Any, int] = {}
    for idx, raw in src[~empty].iterrows():
        stats = new_stats()
        result = _clean_row(int(idx) + 1, raw, mapping, stats, project_ids, project_names, now)
        key = tuple(sorted((k, str(v)) for k, v in result.data.items()))
        if key in first_seen:
            report["duplicates"].append(
                {"row": result.row, "duplicate_of": first_seen[key], "reason": "exact duplicate"}
            )
            continue
        first_seen[key] = result.row
        merge_stats(report, stats)
        kept.append(result)

    report["duplicates_removed"] = len(report["duplicates"])
    report["valid_rows"] = sum(r.is_valid for r in kept)
    report["invalid_rows"] = len(kept) - report["valid_rows"]
    return CleanResult(kept, report)

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "nil", "-", "--", "?", "#n/a"}

EARLIEST_DATE = datetime(1990, 1, 1)
# Tolerate small clock differences between the source system and this server.
FUTURE_TOLERANCE = timedelta(days=1)


@dataclass
class RowResult:
    row: int
    data: Dict[str, Any]
    errors: Dict[str, str] = field(default_factory=dict)
    warnings: Dict[str, str] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class CleanResult:
    rows: List[RowResult]
    report: Dict[str, Any]

    @property
    def valid_rows(self) -> List[RowResult]:
        return [r for r in self.rows if r.is_valid]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report": self.report,
            "rows": [
                {"row": r.row, "data": r.data, "errors": r.errors, "warnings": r.warnings}
                for r in self.rows
            ],
        }


def slugify(text: Any) -> str:
    s = re.sub(r"[()\[\]]", " ", str(text).lower())
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if value is pd.NaT:
        return True
    return isinstance(value, str) and value.strip().lower() in MISSING_TOKENS


def standardize_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Trims strings and turns placeholder tokens (N/A, null, -, …) into None."""

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
        return None if is_missing(value) else value

    return df.apply(lambda col: col.map(clean)).astype(object)


def map_columns(
    columns: Iterable[Any], aliases: Dict[str, List[str]], unit_suffixes: Iterable[str] = ()
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Matches source headers to target fields.
    Returns ({field: source_header}, {field: unit_from_header}).
    """
    lookup = {alias: target for target, names in aliases.items() for alias in names}
    suffixes = sorted(unit_suffixes, key=len, reverse=True)
    mapping: Dict[str, Any] = {}
    header_units: Dict[str, str] = {}

    for header in columns:
        slug = slugify(header)
        target, unit = lookup.get(slug), None
        if target is None:
            for suffix in suffixes:
                if slug.endswith("_" + suffix) and slug[: -len(suffix) - 1] in lookup:
                    target, unit = lookup[slug[: -len(suffix) - 1]], suffix
                    break
        if target and target not in mapping:
            mapping[target] = header
            if unit:
                header_units[target] = unit
    return mapping, header_units


_QUANTITY_RE = re.compile(r"^\s*(-?[\d,]*\.?\d+(?:e[+-]?\d+)?)\s*([a-z]*)\s*$", re.IGNORECASE)

POWER_UNITS = {"w": 0.001, "kw": 1.0, "mw": 1000.0}
ENERGY_UNITS = {"wh": 0.001, "kwh": 1.0, "mwh": 1000.0}
UNIT_SUFFIXES = tuple(POWER_UNITS) + tuple(ENERGY_UNITS) + ("wp", "kwp", "mwp")
UNIT_LABELS = {"w": "W", "kw": "kW", "mw": "MW", "wh": "Wh", "kwh": "kWh", "mwh": "MWh"}


def parse_quantity(
    value: Any, units: Dict[str, float], header_unit: Optional[str] = None
) -> Tuple[Optional[float], bool, Optional[str]]:
    """
    Parses numbers like 6.6, "6,600 W", "1.2 MW", "13.5kWh" into the base unit (kW or kWh).
    Returns (value, was_converted, error).
    """
    if is_missing(value):
        return None, False, None

    if isinstance(value, bool):
        return None, False, "Not a number"
    if isinstance(value, (int, float)):
        number, unit = float(value), ""
    else:
        match = _QUANTITY_RE.match(str(value))
        if not match:
            return None, False, f"Not a number: {value!r}"
        number = float(match.group(1).replace(",", ""))
        unit = match.group(2).lower()

    unit = unit or (header_unit or "")
    if unit.endswith("p") and unit[:-1] in units:  # kWp / Wp (peak) for PV panels
        unit = unit[:-1]
    if unit and unit not in units:
        expected = ", ".join(UNIT_LABELS[u] for u in units)
        return None, False, f"Unexpected unit {unit!r}; expected {expected}"

    factor = units.get(unit, 1.0)
    result = round(number * factor, 2)
    if result < 0:
        return result, factor != 1.0, "Must be 0 or more"
    return result, factor != 1.0, None


TRUE_TOKENS = {"true", "yes", "y", "1", "t", "on"}
FALSE_TOKENS = {"false", "no", "n", "0", "f", "off"}


def parse_bool(value: Any) -> Tuple[Optional[bool], Optional[str]]:
    if is_missing(value):
        return None, None
    if isinstance(value, bool):
        return value, None
    s = str(value).strip().lower()
    if s.endswith(".0"):
        s = s[:-2]
    if s in TRUE_TOKENS:
        return True, None
    if s in FALSE_TOKENS:
        return False, None
    return None, f"Not a yes/no value: {value!r}"


_ISO_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}")


def parse_date(value: Any, now: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Parses and validates a date/datetime. ISO strings (2026-03-04) are read year-month-day;
    other strings are read day-first (04/03/2026 = 4 March 2026).
    """
    if is_missing(value):
        return None, None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip()
        try:
            ts = pd.to_datetime(text, dayfirst=not _ISO_RE.match(text))
        except (ValueError, OverflowError, TypeError):
            return None, f"Invalid date: {value!r}"
        if pd.isna(ts):
            return None, f"Invalid date: {value!r}"
        parsed = ts.to_pydatetime()

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)

    now = now or datetime.now()
    if parsed < EARLIEST_DATE:
        return parsed, f"Date is before {EARLIEST_DATE.year}"
    if parsed > now + FUTURE_TOLERANCE:
        return parsed, "Date is in the future"
    return parsed, None


def empty_report(total_rows: int, mapping: Dict[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    return {
        "total_rows": total_rows,
        "empty_rows_removed": 0,
        "duplicates_removed": 0,
        "duplicates": [],
        "valid_rows": 0,
        "invalid_rows": 0,
        "column_mapping": {k: str(v) for k, v in mapping.items()},
        "unmapped_fields": [f for f in fields if f not in mapping],
        "missing_values": {},
        "filled_values": {},
        "units_converted": {},
        "invalid_dates": 0,
    }


def bump(counter: Dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def new_stats() -> Dict[str, Any]:
    """Per-row counters, merged into the report only for rows that survive de-duplication."""
    return {"missing_values": {}, "filled_values": {}, "units_converted": {}, "invalid_dates": 0}


def merge_stats(report: Dict[str, Any], stats: Dict[str, Any]) -> None:
    for key in ("missing_values", "filled_values", "units_converted"):
        for field, count in stats[key].items():
            report[key][field] = report[key].get(field, 0) + count
    report["invalid_dates"] += stats["invalid_dates"]

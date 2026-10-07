from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from app.cleaning.common import (
    ENERGY_UNITS,
    POWER_UNITS,
    UNIT_LABELS,
    UNIT_SUFFIXES,
    CleanResult,
    RowResult,
    bump,
    empty_report,
    map_columns,
    merge_stats,
    new_stats,
    parse_bool,
    parse_date,
    parse_quantity,
    slugify,
    standardize_missing,
)
from app.models import ProductType, ProjectSegment, SystemType

ALIASES: Dict[str, List[str]] = {
    "project_name": ["project_name", "project", "name", "site_name", "site"],
    "address": ["address", "street", "street_address", "address_line_1"],
    "city": ["city", "suburb", "town"],
    "state": ["state", "province", "region"],
    "system_type": ["system_type", "system", "type"],
    "segment": ["segment", "market_segment", "sector", "customer_type", "category"],
    "product_type": ["product_type", "product"],
    "pv_capacity_kw": ["pv_capacity", "pv", "pv_size", "solar_capacity", "solar", "pv_capacity_kw"],
    "battery_capacity_kwh": ["battery_capacity", "battery", "battery_size", "battery_capacity_kwh"],
    "inverter_capacity_kw": ["inverter_capacity", "inverter", "inverter_size", "inverter_capacity_kw"],
    "grid_connected": ["grid_connected", "grid", "is_grid_connected"],
    "created_at": ["created_at", "created", "created_date", "date_created"],
    "updated_at": ["updated_at", "updated", "updated_date", "last_updated", "modified"],
}
FIELDS = list(ALIASES)

TEXT_LIMITS = {"project_name": 255, "address": 255, "city": 100, "state": 100}
CAPACITY_UNITS = {
    "pv_capacity_kw": POWER_UNITS,
    "inverter_capacity_kw": POWER_UNITS,
    "battery_capacity_kwh": ENERGY_UNITS,
}
SYSTEM_TYPE_SYNONYMS = {
    "on_grid": "on_grid", "ongrid": "on_grid", "grid_tied": "on_grid", "grid_connected": "on_grid",
    "off_grid": "off_grid", "offgrid": "off_grid", "standalone": "off_grid", "stand_alone": "off_grid",
    "hybrid": "hybrid",
}
SEGMENT_SYNONYMS = {
    "commercial": "commercial", "business": "commercial",
    "industrial": "industrial",
}
SOLAR_TOKENS = {"pv", "solar"}
BATTERY_TOKENS = {"battery", "batteries", "storage", "bess"}
FILLER_TOKENS = {"and", "with", "plus", "system", "only"}
PRODUCT_LABELS = {"pv": "PV", "pv_battery": "PV + Battery"}


def _product_from_tokens(tokens: List[str]) -> Optional[str]:
    if any(t in BATTERY_TOKENS for t in tokens):
        return ProductType.pv_battery.value
    if any(t in SOLAR_TOKENS for t in tokens):
        return ProductType.pv.value
    return None


def parse_system_label(value: Any) -> Optional[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """
    Splits a system type label into (system_type, segment, product_type), e.g.
    "Hybrid" -> ("hybrid", None, None), "Commercial PV + Battery" -> (None, "commercial", "pv_battery").
    system_type is None when the label only describes the equipment and must be inferred.
    Returns None if the label is not recognised.
    """
    slug = slugify(value)
    if slug in SYSTEM_TYPE_SYNONYMS:
        return SYSTEM_TYPE_SYNONYMS[slug], None, None

    tokens = [t for t in slug.split("_") if t]
    segment = next((SEGMENT_SYNONYMS[t] for t in tokens if t in SEGMENT_SYNONYMS), None)
    rest = [t for t in tokens if t not in SEGMENT_SYNONYMS and t not in FILLER_TOKENS]
    leftover = [t for t in rest if t not in SOLAR_TOKENS | BATTERY_TOKENS]
    system_type = SYSTEM_TYPE_SYNONYMS.get("_".join(leftover))

    if system_type is None and (leftover or not (segment or rest)):
        return None
    return system_type, segment, _product_from_tokens(rest)


def parse_product_type(value: Any) -> Optional[str]:
    """Reads "PV", "PV + Battery", "Solar & Storage", … as a product type; None if not recognised."""
    tokens = [t for t in slugify(value).split("_") if t and t not in FILLER_TOKENS]
    if any(t not in SOLAR_TOKENS | BATTERY_TOKENS for t in tokens):
        return None
    return _product_from_tokens(tokens)


def project_key(name: Optional[str], address: Optional[str]) -> Tuple[str, str]:
    """Identity used for duplicate detection: case-insensitive project name + address."""
    return ((name or "").strip().lower(), (address or "").strip().lower())


def _clean_row(
    row_number: int,
    raw: pd.Series,
    mapping: Dict[str, Any],
    header_units: Dict[str, str],
    stats: Dict[str, Any],
    now: datetime,
) -> RowResult:
    def get(field: str) -> Any:
        return raw[mapping[field]] if field in mapping else None

    result = RowResult(row=row_number, data={})
    data, errors, warnings = result.data, result.errors, result.warnings

    for field in mapping:
        if get(field) is None:
            bump(stats["missing_values"], field)

    for field, limit in TEXT_LIMITS.items():
        value = get(field)
        data[field] = None if value is None else str(value).strip()
        if data[field] and len(data[field]) > limit:
            errors[field] = f"Longer than {limit} characters"
    if not data["project_name"]:
        errors["project_name"] = "Required"

    for field, units in CAPACITY_UNITS.items():
        original = get(field)
        value, converted, error = parse_quantity(original, units, header_units.get(field))
        data[field] = value
        if error:
            errors[field] = error
        elif converted:
            bump(stats["units_converted"], field)
            header_unit = header_units.get(field)
            cell_has_unit = isinstance(original, str) and any(c.isalpha() for c in original)
            source = original if cell_has_unit or not header_unit else f"{original} {UNIT_LABELS[header_unit.rstrip('p')]}"
            warnings[field] = f"Converted {source} to {value} {'kWh' if units is ENERGY_UNITS else 'kW'}"

    grid, error = parse_bool(get("grid_connected"))
    if error:
        errors["grid_connected"] = error

    raw_type = get("system_type")
    system_type, label_segment, label_product = None, None, None
    if raw_type is not None:
        parsed = parse_system_label(raw_type)
        if parsed is None:
            errors["system_type"] = (
                f"Unknown system type {raw_type!r}; expected {', '.join(t.value for t in SystemType)}"
            )
        else:
            system_type, label_segment, label_product = parsed

    battery = data["battery_capacity_kwh"]
    raw_product = get("product_type")
    product_type = label_product
    if raw_product is not None:
        product_type = parse_product_type(raw_product)
        if product_type is None:
            errors["product_type"] = f"Unknown product type {raw_product!r}; expected PV, PV + Battery"
    elif label_product:
        bump(stats["filled_values"], "product_type")
        warnings["product_type"] = f"Taken from system type {raw_type!r}"
    elif battery or data["pv_capacity_kw"]:
        product_type = ProductType.pv_battery.value if battery else ProductType.pv.value
        bump(stats["filled_values"], "product_type")
        warnings["product_type"] = f"Missing; inferred {PRODUCT_LABELS[product_type]} from capacities"
    data["product_type"] = product_type or raw_product

    if system_type is None and "system_type" not in errors:
        if grid is False:
            system_type = SystemType.off_grid.value
        elif battery or product_type == ProductType.pv_battery.value:
            system_type = SystemType.hybrid.value
        else:
            system_type = SystemType.on_grid.value
        bump(stats["filled_values"], "system_type")
        warnings["system_type"] = (
            f"Missing; inferred {system_type}" if raw_type is None
            else f"Inferred {system_type} from {raw_type!r}"
        )
    data["system_type"] = system_type or raw_type

    raw_segment = get("segment")
    segment = label_segment
    if raw_segment is not None:
        segment = SEGMENT_SYNONYMS.get(slugify(raw_segment))
        if segment is None:
            errors["segment"] = (
                f"Unknown segment {raw_segment!r}; expected {', '.join(s.value for s in ProjectSegment)}"
            )
    elif label_segment:
        bump(stats["filled_values"], "segment")
        warnings["segment"] = f"Taken from system type {raw_type!r}"
    data["segment"] = segment or raw_segment

    if grid is None and "grid_connected" not in errors:
        grid = system_type != SystemType.off_grid.value
        bump(stats["filled_values"], "grid_connected")
        warnings["grid_connected"] = f"Missing; inferred {'yes' if grid else 'no'}"
    data["grid_connected"] = grid

    if system_type == SystemType.off_grid.value and grid is True:
        warnings.setdefault("grid_connected", "Off-grid system marked as grid connected")
    if system_type in (SystemType.off_grid.value, SystemType.hybrid.value) and not battery:
        warnings.setdefault("battery_capacity_kwh", f"No battery capacity for a {system_type} system")

    dates: Dict[str, Optional[datetime]] = {}
    for field in ("created_at", "updated_at"):
        dates[field], error = parse_date(get(field), now)
        if error:
            errors[field] = error
            stats["invalid_dates"] += 1
        data[field] = dates[field].isoformat() if dates[field] and not error else None
    if (
        dates["created_at"] and dates["updated_at"]
        and "created_at" not in errors and "updated_at" not in errors
        and dates["updated_at"] < dates["created_at"]
    ):
        errors["updated_at"] = "Earlier than created_at"
        stats["invalid_dates"] += 1
        data["updated_at"] = None

    return result


def clean_projects(
    df: pd.DataFrame,
    existing_keys: Optional[Set[Tuple[str, str]]] = None,
    now: Optional[datetime] = None,
) -> CleanResult:
    """
    Cleans raw project rows:
      * drops empty rows, exact duplicates and repeated project name + address
        (and, if `existing_keys` is given, projects already in the database)
      * standardises missing values and fills system_type / grid_connected when they can be inferred
      * splits labels like "Commercial PV + Battery" into segment + product_type + inferred system_type
      * converts W / MW / Wh / MWh (in cells or headers) to kW / kWh
      * validates created_at / updated_at dates
    """
    now = now or datetime.now()
    mapping, header_units = map_columns(df.columns, ALIASES, UNIT_SUFFIXES)
    report = empty_report(len(df), mapping, FIELDS)
    if df.empty:
        return CleanResult([], report)

    src = standardize_missing(df)
    empty = src.isna().all(axis=1)
    report["empty_rows_removed"] = int(empty.sum())

    kept: List[RowResult] = []
    first_seen: Dict[Any, int] = {}
    for idx, raw in src[~empty].iterrows():
        stats = new_stats()
        result = _clean_row(int(idx) + 1, raw, mapping, header_units, stats, now)
        exact = tuple(sorted((k, str(v)) for k, v in result.data.items()))
        key = project_key(result.data["project_name"], result.data["address"]) if result.data["project_name"] else None

        reason, duplicate_of = None, None
        if exact in first_seen:
            reason, duplicate_of = "exact duplicate", first_seen[exact]
        elif key and key in first_seen:
            reason, duplicate_of = "same project name and address", first_seen[key]
        elif key and existing_keys and key in existing_keys:
            reason = "already in database"

        if reason:
            report["duplicates"].append({"row": result.row, "duplicate_of": duplicate_of, "reason": reason})
            continue
        first_seen[exact] = result.row
        if key:
            first_seen[key] = result.row
        merge_stats(report, stats)
        kept.append(result)

    report["duplicates_removed"] = len(report["duplicates"])
    report["valid_rows"] = sum(r.is_valid for r in kept)
    report["invalid_rows"] = len(kept) - report["valid_rows"]
    return CleanResult(kept, report)

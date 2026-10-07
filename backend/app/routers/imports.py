from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Set, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.cleaning import clean_compliance_checks, clean_projects, read_table
from app.cleaning.projects import project_key
from app.cleaning.readers import UnsupportedFileError
from app.database import get_db

router = APIRouter(prefix="/import", tags=["import"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CAPACITY_FIELDS = ("pv_capacity_kw", "battery_capacity_kwh", "inverter_capacity_kw")


def _read_upload(file: UploadFile) -> pd.DataFrame:
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")
    try:
        return read_table(file.filename or "", content)
    except UnsupportedFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # malformed Excel/CSV/JSON
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")


def _to_model_values(data: Dict[str, Any]) -> Dict[str, Any]:
    values = dict(data)
    for field in ("created_at", "updated_at"):
        if field in values:
            if values[field] is None:
                del values[field]  # let the database default apply
            else:
                values[field] = datetime.fromisoformat(values[field])
    for field in CAPACITY_FIELDS:
        if values.get(field) is not None:
            values[field] = Decimal(str(values[field]))
    return values


def _existing_project_keys(db: Session) -> Optional[Set[Tuple[str, str]]]:
    try:
        rows = db.execute(select(models.Project.project_name, models.Project.address)).all()
    except SQLAlchemyError:
        db.rollback()
        return None
    return {project_key(name, address) for name, address in rows}


def _project_lookup(db: Session) -> Tuple[Optional[Set[int]], Optional[Dict[str, int]]]:
    try:
        rows = db.execute(select(models.Project.id, models.Project.project_name)).all()
    except SQLAlchemyError:
        db.rollback()
        return None, None
    return {pid for pid, _ in rows}, {name.strip().lower(): pid for pid, name in rows}


def _require_db(available: bool) -> None:
    if not available:
        raise HTTPException(status_code=503, detail="Database is unavailable; cannot save")


@router.post("/projects")
def import_projects(
    file: UploadFile = File(...),
    commit: bool = Query(False, description="Save valid rows to the database"),
    db: Session = Depends(get_db),
):
    """Cleans an uploaded project file. Returns the cleaned rows and a report; saves them if `commit`."""
    df = _read_upload(file)
    existing = _existing_project_keys(db)
    if commit:
        _require_db(existing is not None)

    result = clean_projects(df, existing_keys=existing)
    body = result.to_dict()
    body["file_name"] = file.filename
    body["report"]["database_checked"] = existing is not None
    body["inserted"] = 0

    if commit and result.valid_rows:
        db.add_all(models.Project(**_to_model_values(r.data)) for r in result.valid_rows)
        db.commit()
        body["inserted"] = len(result.valid_rows)
    return body


@router.post("/compliance-checks")
def import_compliance_checks(
    file: UploadFile = File(...),
    commit: bool = Query(False, description="Save valid rows to the database"),
    db: Session = Depends(get_db),
):
    """Cleans an uploaded compliance-check file. Returns the cleaned rows and a report; saves them if `commit`."""
    df = _read_upload(file)
    project_ids, project_names = _project_lookup(db)
    if commit:
        _require_db(project_ids is not None)

    result = clean_compliance_checks(df, project_ids=project_ids, project_names=project_names)
    body = result.to_dict()
    body["file_name"] = file.filename
    body["report"]["database_checked"] = project_ids is not None
    body["inserted"] = 0

    if commit and result.valid_rows:
        db.add_all(models.ComplianceCheck(**_to_model_values(r.data)) for r in result.valid_rows)
        db.commit()
        body["inserted"] = len(result.valid_rows)
    return body

from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.models import CheckStatus, Severity

router = APIRouter(tags=["compliance checks"])


def _project_or_404(db: Session, project_id: int):
    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _check_or_404(db: Session, check_id: int):
    check = crud.get_compliance_check(db, check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Compliance check not found")
    return check


@router.get("/compliance-checks", response_model=List[schemas.ComplianceCheckRead])
def list_compliance_checks(
    project_id: Optional[int] = None,
    check_status: Optional[CheckStatus] = Query(None, alias="status"),
    severity: Optional[Severity] = None,
    rule_code: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_compliance_checks(
        db,
        project_id=project_id,
        status=check_status,
        severity=severity,
        rule_code=rule_code,
        skip=skip,
        limit=limit,
    )


@router.get("/compliance-checks/{check_id}", response_model=schemas.ComplianceCheckRead)
def get_compliance_check(check_id: int, db: Session = Depends(get_db)):
    return _check_or_404(db, check_id)


@router.delete("/compliance-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_compliance_check(check_id: int, db: Session = Depends(get_db)):
    crud.delete_compliance_check(db, _check_or_404(db, check_id))


@router.get(
    "/projects/{project_id}/compliance-checks",
    response_model=List[schemas.ComplianceCheckRead],
)
def list_project_compliance_checks(project_id: int, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    return crud.list_compliance_checks(db, project_id=project_id, limit=500)


@router.post(
    "/projects/{project_id}/compliance-checks",
    response_model=List[schemas.ComplianceCheckRead],
    status_code=status.HTTP_201_CREATED,
)
def create_project_compliance_checks(
    project_id: int,
    data: Union[schemas.ComplianceCheckCreate, List[schemas.ComplianceCheckCreate]],
    db: Session = Depends(get_db),
):
    """Accepts a single check or a list of checks (e.g. the results of one rule run)."""
    _project_or_404(db, project_id)
    items = data if isinstance(data, list) else [data]
    return crud.create_compliance_checks(db, project_id, items)

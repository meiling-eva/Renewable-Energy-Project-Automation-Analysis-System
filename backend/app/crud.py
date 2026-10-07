from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> List[models.Project]:
    stmt = select(models.Project).order_by(models.Project.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    return db.get(models.Project, project_id)


def create_project(db: Session, data: schemas.ProjectCreate) -> models.Project:
    project = models.Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, project: models.Project, data: schemas.ProjectUpdate
) -> models.Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: models.Project) -> None:
    db.delete(project)
    db.commit()


def list_compliance_checks(
    db: Session,
    project_id: Optional[int] = None,
    status: Optional[models.CheckStatus] = None,
    severity: Optional[models.Severity] = None,
    rule_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.ComplianceCheck]:
    stmt = select(models.ComplianceCheck)
    if project_id is not None:
        stmt = stmt.where(models.ComplianceCheck.project_id == project_id)
    if status is not None:
        stmt = stmt.where(models.ComplianceCheck.status == status)
    if severity is not None:
        stmt = stmt.where(models.ComplianceCheck.severity == severity)
    if rule_code is not None:
        stmt = stmt.where(models.ComplianceCheck.rule_code == rule_code)
    stmt = stmt.order_by(models.ComplianceCheck.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_compliance_check(db: Session, check_id: int) -> Optional[models.ComplianceCheck]:
    return db.get(models.ComplianceCheck, check_id)


def create_compliance_checks(
    db: Session, project_id: int, items: List[schemas.ComplianceCheckCreate]
) -> List[models.ComplianceCheck]:
    checks = [models.ComplianceCheck(project_id=project_id, **item.model_dump()) for item in items]
    db.add_all(checks)
    db.commit()
    for check in checks:
        db.refresh(check)
    return checks


def delete_compliance_check(db: Session, check: models.ComplianceCheck) -> None:
    db.delete(check)
    db.commit()

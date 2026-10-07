from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_or_404(db: Session, project_id: int):
    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=List[schemas.ProjectRead])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_projects(db, skip=skip, limit=limit)


@router.post("", response_model=schemas.ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: schemas.ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_project(db, data)


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, project_id)


@router.patch("/{project_id}", response_model=schemas.ProjectRead)
def update_project(
    project_id: int, data: schemas.ProjectUpdate, db: Session = Depends(get_db)
):
    return crud.update_project(db, _get_or_404(db, project_id), data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    crud.delete_project(db, _get_or_404(db, project_id))

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Membership, Project


def require_org_access(db: Session, user_id: str, organization_id: str) -> Membership:
    membership = db.query(Membership).filter_by(user_id=user_id, organization_id=organization_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization not found")
    return membership


def require_project_access(db: Session, user_id: str, project_id: str) -> Project:
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_org_access(db, user_id, project.organization_id)
    return project

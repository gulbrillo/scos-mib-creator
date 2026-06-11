from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..bootstrap import bootstrap_project
from ..db import get_db
from ..models import MibRow, Project, ProjectMember, User
from ..security import get_current_user, get_project_for, project_role
from mibschema.registry import PROFILES

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    profile: str = "ccs5"
    bootstrap: bool = True


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    profile: str | None = None


class MemberAdd(BaseModel):
    username: str
    role: str = "editor"


def project_json(db: Session, p: Project, role: str | None) -> dict:
    counts = dict(db.query(MibRow.table_name, func.count())
                  .filter_by(project_id=p.id).group_by(MibRow.table_name).all())
    return {
        "id": p.id, "name": p.name, "description": p.description, "profile": p.profile,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "role": role, "row_counts": counts, "total_rows": sum(counts.values()),
        "members": [{"user_id": m.user_id, "username": m.user.username, "role": m.role}
                    for m in p.members],
    }


@router.get("")
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.is_admin:
        projects = db.query(Project).order_by(Project.name).all()
    else:
        projects = (db.query(Project).join(ProjectMember)
                    .filter(ProjectMember.user_id == user.id).order_by(Project.name).all())
    return [project_json(db, p, project_role(db, p.id, user)) for p in projects]


@router.post("", status_code=201)
def create_project(req: ProjectCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Project name must not be empty")
    if req.profile not in PROFILES:
        raise HTTPException(400, f"Unknown profile '{req.profile}'")
    if db.query(Project).filter_by(name=name).first():
        raise HTTPException(409, "A project with this name already exists")
    project = Project(name=name, description=req.description, profile=req.profile)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    if req.bootstrap:
        bootstrap_project(db, project.id, name)
    db.commit()
    return project_json(db, project, "owner")


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    project = get_project_for(db, project_id, user)
    return project_json(db, project, project_role(db, project_id, user))


@router.patch("/{project_id}")
def patch_project(project_id: int, req: ProjectPatch, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    project = get_project_for(db, project_id, user, manage=True)
    if req.name is not None and req.name.strip():
        project.name = req.name.strip()
    if req.description is not None:
        project.description = req.description
    if req.profile is not None:
        if req.profile not in PROFILES:
            raise HTTPException(400, f"Unknown profile '{req.profile}'")
        project.profile = req.profile
    db.commit()
    return project_json(db, project, project_role(db, project_id, user))


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    project = get_project_for(db, project_id, user, manage=True)
    db.query(MibRow).filter_by(project_id=project.id).delete(synchronize_session=False)
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.post("/{project_id}/members", status_code=201)
def add_member(project_id: int, req: MemberAdd, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, manage=True)
    if req.role not in ("owner", "editor", "viewer"):
        raise HTTPException(400, "Role must be owner, editor or viewer")
    target = db.query(User).filter_by(username=req.username.strip()).first()
    if target is None:
        raise HTTPException(404, f"User '{req.username}' not found")
    member = db.query(ProjectMember).filter_by(project_id=project_id,
                                               user_id=target.id).first()
    if member:
        member.role = req.role
    else:
        db.add(ProjectMember(project_id=project_id, user_id=target.id, role=req.role))
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, manage=True)
    member = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if member is None:
        raise HTTPException(404, "Member not found")
    db.delete(member)
    db.commit()
    return {"ok": True}

import time

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import Project, ProjectMember, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": int(time.time()) + config.TOKEN_TTL_SECONDS}
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def get_current_user(db: Session = Depends(get_db),
                     mib_session: str | None = Cookie(default=None)) -> User:
    if not mib_session:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(mib_session, config.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Administrator privileges required")
    return user


def project_role(db: Session, project_id: int, user: User) -> str | None:
    """Effective role of a user in a project (admins are implicit owners)."""
    if user.is_admin:
        return "owner"
    m = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user.id).first()
    return m.role if m else None


def get_project_for(db: Session, project_id: int, user: User,
                    write: bool = False, manage: bool = False) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    role = project_role(db, project_id, user)
    if role is None:
        raise HTTPException(403, "You are not a member of this project")
    if manage and role != "owner":
        raise HTTPException(403, "Project owner role required")
    if write and role not in ("owner", "editor"):
        raise HTTPException(403, "Write access required (you have viewer access)")
    return project

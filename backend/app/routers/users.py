from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserPatch(BaseModel):
    password: str | None = None
    is_admin: bool | None = None


@router.get("")
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username, "is_admin": u.is_admin}
            for u in db.query(User).order_by(User.username)]


@router.post("", status_code=201)
def create_user(req: UserCreate, db: Session = Depends(get_db)):
    if not req.username.strip():
        raise HTTPException(400, "Username must not be empty")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.query(User).filter_by(username=req.username.strip()).first():
        raise HTTPException(409, "Username already exists")
    user = User(username=req.username.strip(), password_hash=hash_password(req.password),
                is_admin=req.is_admin)
    db.add(user)
    db.commit()
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}


@router.patch("/{user_id}")
def patch_user(user_id: int, req: UserPatch, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if req.password is not None:
        if len(req.password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        user.password_hash = hash_password(req.password)
    if req.is_admin is not None:
        user.is_admin = req.is_admin
    db.commit()
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(400, "You cannot delete your own account")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..models import User
from ..security import get_current_user, hash_password, make_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


def user_json(u: User) -> dict:
    return {"id": u.id, "username": u.username, "is_admin": u.is_admin}


@router.post("/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=req.username).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    response.set_cookie(config.COOKIE_NAME, make_token(user.id), httponly=True,
                        samesite="lax", max_age=config.TOKEN_TTL_SECONDS, path="/")
    return user_json(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_json(user)


@router.post("/password")
def change_password(req: PasswordChange, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(req.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"ok": True}

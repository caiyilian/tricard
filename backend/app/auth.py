"""账号接口：注册 / 登录。"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import security
from .db import get_db
from .models import AuthToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_INITIAL_BEANS = 100000
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
_NICKNAME_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_]{1,16}$")


class RegisterIn(BaseModel):
    username: str
    password: str
    nickname: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


def _issue_token(db: Session, user: User) -> str:
    raw = security.new_token()
    db.add(AuthToken(user_id=user.id, token_hash=security.hash_token(raw)))
    db.commit()
    return raw


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not _USERNAME_RE.match(body.username):
        raise HTTPException(400, "用户名需 3~32 位字母/数字/下划线")
    if len(body.password) < 4:
        raise HTTPException(400, "密码至少 4 位")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(409, "用户名已存在")
    nickname = body.nickname or body.username
    if not _NICKNAME_RE.match(nickname):
        raise HTTPException(400, "昵称需 1~16 位中英文/数字/_")
    if db.query(User).filter(User.nickname == nickname).first():
        raise HTTPException(409, "昵称已被占用")

    user = User(
        username=body.username,
        password_hash=security.hash_password(body.password),
        nickname=nickname,
        joy_beans=_INITIAL_BEANS,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = _issue_token(db, user)
    return {"token": token, "user": user.public()}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = _issue_token(db, user)
    return {"token": token, "user": user.public()}
"""FastAPI 依赖：当前登录用户（Bearer token）。"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import security
from .db import get_db
from .models import AuthToken, User


def require_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    record = db.query(AuthToken).filter(AuthToken.token_hash == security.hash_token(token)).first()
    if record is None:
        raise HTTPException(status_code=401, detail="invalid token")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user
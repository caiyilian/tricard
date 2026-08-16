"""用户资料接口：查询 / 改昵称 / 上传头像。"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .deps import require_user
from .models import User

router = APIRouter(prefix="/api/users", tags=["users"])

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB


class UpdateMeIn(BaseModel):
    nickname: str | None = None


@router.get("/me")
def get_me(user: User = Depends(require_user)):
    return user.public()


@router.put("/me")
def update_me(body: UpdateMeIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if body.nickname is not None:
        if user.is_ai:
            raise HTTPException(400, "AI 账号不允许改昵称")
        nickname = body.nickname.strip()
        if not 1 <= len(nickname) <= 16:
            raise HTTPException(400, "昵称需 1~16 位")
        clash = db.query(User).filter(User.nickname == nickname, User.id != user.id).first()
        if clash:
            raise HTTPException(409, "昵称已被占用")
        user.nickname = nickname
        db.commit()
        db.refresh(user)
    return user.public()


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if user.is_ai:
        raise HTTPException(400, "AI 账号不允许改头像")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"仅支持 {'/'.join(sorted(ALLOWED_EXT))}")
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(400, "头像不能超过 2MB")

    config.AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    target = config.AVATAR_DIR / f"user{user.id}{ext}"
    target.write_bytes(data)
    user.avatar = f"/avatars/{target.name}"
    db.commit()
    db.refresh(user)
    return {"avatar": user.avatar}
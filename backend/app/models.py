"""数据模型：User / AuthToken / MatchRecord。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    nickname: Mapped[str] = mapped_column(String(32), unique=True)
    avatar: Mapped[str | None] = mapped_column(String(256), nullable=True)  # 形如 /avatars/3.png
    is_ai: Mapped[bool] = mapped_column(default=False)
    joy_beans: Mapped[int] = mapped_column(Integer, default=100000)  # 允许负数
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def games(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> float | None:
        return round(self.wins / self.games, 4) if self.games else None

    def public(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "is_ai": self.is_ai,
            "joy_beans": self.joy_beans,
            "wins": self.wins,
            "losses": self.losses,
            "games": self.games,
            "win_rate": self.win_rate,
        }


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchRecord(Base):
    __tablename__ = "match_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    room_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    base_bet: Mapped[int] = mapped_column(Integer, default=200)
    bombs: Mapped[int] = mapped_column(Integer, default=0)
    spring: Mapped[bool] = mapped_column(default=False)
    landlord: Mapped[str] = mapped_column(String(32))      # 地主用户名
    winner_team: Mapped[str] = mapped_column(String(16))   # landlord / farmers
    beans_delta: Mapped[str] = mapped_column(Text, default="{}")  # JSON: {username: delta}
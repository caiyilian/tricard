"""SQLAlchemy 引擎与会话（SQLite 本机库）。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app import config

config.DATA_DIR.mkdir(parents=True, exist_ok=True)
config.AVATAR_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
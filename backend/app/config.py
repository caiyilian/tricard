import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = BACKEND_DIR / "data"

load_dotenv(PROJECT_ROOT / ".env")


def _list_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [k.strip() for k in raw.split(",") if k.strip()]


# ---- senseNova LLM ----
SENSENOVA_API_KEYS: list[str] = _list_env("SENSENOVA_API_KEYS")
SENSENOVA_BASE_URL: str = os.getenv("SENSENOVA_BASE_URL", "https://token.sensenova.cn/v1")
SENSENOVA_MODEL: str = os.getenv("SENSENOVA_MODEL", "sensenova-6.8-flash-lite")
SENSENOVA_TIMEOUT: float = float(os.getenv("SENSENOVA_TIMEOUT", "20"))

# ---- game ----
PLAY_TIMEOUT: int = int(os.getenv("PLAY_TIMEOUT", "30"))  # 每手出牌限时（秒）
COMMENTATOR_MODE: str = os.getenv("COMMENTATOR_MODE", "hybrid")  # rules_only / hybrid / llm_judge

# ---- douzero ----
DOUZERO_MODELS_DIR: str = os.getenv("DOUZERO_MODELS_DIR", str(BACKEND_DIR / "models" / "douzero_WP"))

# ---- db ----
DB_PATH: Path = Path(os.getenv("DB_PATH", str(DATA_DIR / "doudizhu.db")))
AVATAR_DIR: Path = DATA_DIR / "avatars"

# ---- server ----
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
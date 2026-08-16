import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.usefixtures("_db")


@pytest.fixture(autouse=True)
def _db(tmp_path):
    import app.db as dbmod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    dbmod.engine.dispose()
    test_db = tmp_path / "test.db"
    dbmod.engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    dbmod.SessionLocal = sessionmaker(bind=dbmod.engine, autocommit=False, autoflush=False)
    dbmod.Base.metadata.create_all(dbmod.engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, username="alice", password="pw1234", nickname="Alice"):
    r = client.post("/api/auth/register", json={"username": username, "password": password, "nickname": nickname})
    assert r.status_code == 200, r.text
    return r.json()


class TestAuth:
    def test_register_login(self, client):
        data = _register(client)
        assert data["user"]["joy_beans"] == 100000
        login = client.post("/api/auth/login", json={"username": "alice", "password": "pw1234"})
        assert login.status_code == 200
        assert login.json()["user"]["username"] == "alice"

    def test_duplicate_username_rejected(self, client):
        _register(client)
        r = client.post("/api/auth/register", json={"username": "alice", "password": "xxxxx"})
        assert r.status_code == 409

    def test_password_not_stored_plain(self, client):
        data = _register(client)
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as db:
            user = db.query(User).filter(User.username == "alice").first()
        assert "pw1234" not in user.password_hash
        assert user.password_hash.startswith("pbkdf2$")

    def test_wrong_password_rejected(self, client):
        _register(client)
        r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_token(self, client):
        assert client.get("/api/users/me").status_code == 401

    def test_me_with_token(self, client):
        data = _register(client)
        r = client.get("/api/users/me", headers={"Authorization": f"Bearer {data['token']}"})
        assert r.status_code == 200
        assert r.json()["username"] == "alice"


class TestUsers:
    def test_update_nickname(self, client):
        data = _register(client)
        h = {"Authorization": f"Bearer {data['token']}"}
        r = client.put("/api/users/me", json={"nickname": "新昵称"}, headers=h)
        assert r.status_code == 200
        assert r.json()["nickname"] == "新昵称"

    def test_avatar_upload(self, client):
        data = _register(client)
        h = {"Authorization": f"Bearer {data['token']}"}
        r = client.post("/api/users/avatar", headers=h, files={"file": ("a.png", b"fake-image-bytes", "image/png")})
        assert r.status_code == 200, r.text
        assert r.json()["avatar"].startswith("/avatars/user")


class TestBeansApi:
    def test_settlement_math(self):
        from app.beans import settle_by_players

        # 无炸无春天，地主输
        d = settle_by_players(["a", "b", "c"], landlord_index=0, base_bet=200, bombs=0, spring=False, landlord_win=False)
        assert d == {"a": -400, "b": 200, "c": 200}

        # 王炸x2 + 春天x2，地主赢：mult=4
        d = settle_by_players(["a", "b", "c"], landlord_index=0, base_bet=200, bombs=1, spring=True, landlord_win=True)
        assert d == {"a": 2 * 200 * 4, "b": -200 * 4, "c": -200 * 4}


class TestRanking:
    def test_ranking_sorted(self, client):
        ba = _register(client, "beta", "pw1234", "Beta")
        ha = _register(client, "ham", "pw1234", "Ham")
        bh = {"Authorization": f"Bearer {ba['token']}"}
        hh = {"Authorization": f"Bearer {ha['token']}"}
        # beta 改豆子：通过直接改库更简单，这里用接口不可行，改为直接写库
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as db:
            u = db.query(User).filter(User.username == "beta").one()
            u.joy_beans = 999999
            db.commit()
        r = client.get("/api/ranking", params={"by": "beans", "limit": 5})
        assert r.status_code == 200
        items = r.json()["items"]
        assert items and items[0]["username"] == "beta"

    def test_win_rate_filter(self, client):
        _register(client)
        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as db:
            u = db.query(User).filter(User.username == "alice").one()
            u.wins, u.losses = 3, 1  # 4 场 <5，不上胜率榜
            w = db.query(User).filter(User.username == "beta").one() if db.query(User).filter(User.username == "beta").first() else None
            if w:
                w.wins, w.losses = 5, 0
            db.commit()
        r = client.get("/api/ranking", params={"by": "win_rate"})
        items = r.json()["items"]
        names = [i["username"] for i in items]
        assert "alice" not in names  # <5 场不上胜率榜
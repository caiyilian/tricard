from app.rooms import Room, RoomManager


def make_user(name="bob", uid=1):
    return {"id": uid, "username": name, "nickname": name, "avatar": None}


class TestRoomBasics:
    def test_create_and_list(self):
        mgr = RoomManager()
        r = mgr.create(make_user(), base_bet=500, ai_type="douzero")
        assert len(r.code) == 6
        assert r.status == "waiting"
        assert len([s for s in r.seats if s]) == 3       # 房主 + 2 AI 补位
        assert [s.ai_type for s in r.seats if s.is_ai] == ["douzero", "douzero"]
        assert all(s.ready for s in r.seats if s.is_ai)  # AI 自动就绪
        assert mgr.list_rooms()

    def test_add_human_overwrites_ai(self):
        mgr = RoomManager()
        r = mgr.create(make_user())
        s = r.add_human(make_user("alice", 2))
        assert s is not None
        assert r.seat_of("alice") is not None
        # 第二个真人直接顶替 AI
        s2 = r.add_human(make_user("carol", 3))
        assert r.seat_of("carol") is not None
        humans = [s for s in r.seats if s and not s.is_ai]
        assert len(humans) == 3

    def test_start_gating(self):
        mgr = RoomManager()
        host = make_user()
        r = mgr.create(host, base_bet=200)
        # 房主自动就绪，无其他真人 → 可直接开始
        ok, msg = r.can_start(host["username"])
        assert ok, msg
        # 非房主不能开始
        other = make_user("x", 99)
        r.add_human(other)
        r.set_ready("x", True)
        ok, _ = r.can_start("x")
        assert not ok


class TestSettlement:
    def test_settle_landlord_wins(self):
        mgr = RoomManager()
        r = mgr.create(make_user("host"), base_bet=200)
        # 手动塞一个已结束的 Game（地主赢、无炸）
        from dzcore import dou_dz_adapter as dz
        from dzcore.game import Game

        g = Game()
        g.prime(
            [[dz.Card.new("3c")], [], []], bottom=[], landlord_seat=0, turn=0
        )
        g.play(0, [dz.Card.new("3c")])
        assert g.winner_team == "landlord"
        r.game = g
        result = r.settle()
        # 地主赢且春天（农民没出过牌）→ mult=2；地主 +800，两农民各 -400
        assert result["per_seat"][0]["delta"] == 800
        assert result["per_seat"][1]["delta"] == -400
        assert result["per_seat"][0]["won"] is True
        assert result["spring"] is True  # 农民没出过牌

    def test_settle_farmer_wins_bomb(self):
        mgr = RoomManager()
        r = mgr.create(make_user("host"))
        from dzcore import dou_dz_adapter as dz
        from dzcore.game import Game

        g = Game()
        g.prime(
            [[], [dz.Card.new("4c"), dz.Card.new("4d"), dz.Card.new("4h"), dz.Card.new("4s")], []],
            bottom=[], landlord_seat=0, turn=1,
        )
        g.play(1, dz.Card.card_ints_from_string("4c-4d-4h-4s"))
        assert g.winner_team == "farmers"
        r.game = g
        result = r.settle()
        # 农民赢 + 1炸 + 地主没出过牌（反春）→ mult=4；地主 -1600，农民各 +800
        assert result["per_seat"][1]["delta"] == 800
        assert result["per_seat"][0]["delta"] == -1600
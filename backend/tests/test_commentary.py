import pytest

from app.key_picker import KeyPicker
from dzcore import dou_dz_adapter as dz
from dzcore.commentary import detector
from dzcore.commentary.commentator import Commentator
from dzcore.commentary.salience import FrequencyController
from dzcore.game import Game

C = dz.Card


def fake_game(history, landlord_seat=0, status="finished", winner_team="landlord", winner_seat=0):
    g = Game()
    g.history = history
    g.landlord_seat = landlord_seat
    g.status = status
    g.winner_team = winner_team
    g.winner_seat = winner_seat
    g.bottom = []
    g.hands = [[], [], []]
    g.turn = 0
    return g


def play(seat, cards_str, trick, hand_left):
    cards = C.card_ints_from_string(cards_str)
    labels = dz.cards_label(cards)
    return {"seat": seat, "action": "play", "cards": cards, "labels": labels, "trick": trick, "hand_left": hand_left}


def ps(seat, trick, hand_left):
    return {"seat": seat, "action": "pass", "cards": [], "labels": [], "trick": trick, "hand_left": hand_left}


class TestDetector:
    def test_keng_no_send(self):
        hist = [
            play(0, "3c-3d", 1, 10),   # 农民0 领出对子
            play(2, "5c-5d", 1, 1),    # 农民2 剩1张
        ]
        g = fake_game(hist, landlord_seat=1)
        evs = [e for e in detector.detect(g) if e["archetype"] == "keng_no_send"]
        assert evs and evs[0]["target_seat"] == 0

    def test_keng_step(self):
        hist = [
            play(0, "3c", 1, 5),     # 农民0
            play(2, "Kc", 1, 3),     # 农民2 压队友
            play(1, "2d", 1, 8),     # 地主压过 → 本轮地主赢
        ]
        g = fake_game(hist, landlord_seat=1)
        evs = [e for e in detector.detect(g) if e["archetype"] == "keng_step"]
        assert evs and evs[0]["target_seat"] == 2

    def test_friendly_fire(self):
        hist = [
            play(1, "3c-3d-3h-3s", 1, 9),  # 地主炸
            play(0, "7c-7d-7h-7s", 1, 8),  # 农民0 炸
            play(2, "5c-5d-5h-5s", 1, 6),  # 农民2 再炸（两农民互炸）
        ]
        g = fake_game(hist, landlord_seat=1)
        evs = [e for e in detector.detect(g) if e["archetype"] == "keng_friendly_fire"]
        assert evs

    def test_bright_bomb_on_win(self):
        hist = [play(0, "3c-3d-3h-3s", 1, 0)]  # 农民0 出炸弹清手 -> 农民赢
        g = fake_game(hist, landlord_seat=1, winner_team="farmers", winner_seat=0)
        evs = [e for e in detector.detect(g) if e["archetype"] == "bright_bomb"]
        assert evs and evs[0]["target_seat"] == 0


class TestFrequencyController:
    def test_caps(self):
        fc = FrequencyController(cooldown_turns=1, per_trick_max=2, per_seat_max=3)
        assert fc.can_comment(0, turn=1, trick=1)
        fc.mark_comment(0, turn=1)
        assert fc.can_comment(1, turn=3, trick=1)
        fc.mark_comment(1, turn=3)
        assert not fc.can_comment(2, turn=5, trick=1)  # 该轮已满


class TestCommentator:
    def _ai_seats(self):
        return [{"seat": 0, "name": "地主老赵", "personality": "savage", "ai": True},
                {"seat": 1, "name": "豆子小美", "personality": "kind", "ai": True},
                {"seat": 2, "name": "牌场大魔王", "personality": "savage", "ai": True}]

    def test_phrase_fallback_when_llm_off(self):
        got = []
        seats = self._ai_seats()
        c = Commentator(seats=seats, mode="rules_only", emit=got.append)
        g = fake_game([play(0, "3c-3d", 1, 10), play(2, "5c-5d", 1, 1)], landlord_seat=1)
        c.maybe_comment(g)
        assert len(got) >= 1
        assert got[0]["type"] == "comment"
        assert got[0]["text"]

    def test_llm_commentator_used(self, monkeypatch):
        got = []
        seats = self._ai_seats()
        called = []
        picker = KeyPicker(["k1", "k2"])
        c = Commentator(seats=seats, mode="hybrid", picker=picker, emit=got.append)
        # mock LLM
        class FakeLLM:
            def decide(self, snap):
                called.append(1)
                return {"speaker": "地主老赵", "text": "队友别浪了！"}

        c.llm = FakeLLM()
        g = fake_game([play(0, "3c-3d", 1, 10), play(2, "5c-5d", 1, 1)], landlord_seat=1)
        c.maybe_comment(g)
        assert called and got[0]["text"] == "队友别浪了！"
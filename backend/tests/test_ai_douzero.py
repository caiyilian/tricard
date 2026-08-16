import pytest

from app import config
from dzcore import dou_dz_adapter as dz
from dzcore.ai_douzero import DouZeroAI, seat_to_position
from dzcore.game import Game

DOUZERO_DIR = config.DOUZERO_MODELS_DIR


@pytest.fixture(scope="module")
def dz_ai():
    return DouZeroAI(name="test-douzero", models_dir=DOUZERO_DIR)


class TestSeatMapping:
    def test_mapping(self):
        assert seat_to_position(2, 2) == "landlord"
        assert seat_to_position(0, 2) == "landlord_down"   # 下一家
        assert seat_to_position(1, 2) == "landlord_up"     # 上一家


class TestDouZeroAct:
    def test_lead_legal(self, dz_ai):
        game = Game()
        game.start(seed=11)
        ctx = {"game": game}
        move = dz_ai.choose_action(game.hands[game.turn], game.last_play, ctx)
        assert move is None or dz.is_valid_play(move)
        if move:
            assert dz.has_cards(game.hands[game.turn], move)

    def test_full_douzero_battle(self, dz_ai):
        """三座位全是 DouZero：完整打一局，所有出牌合法。"""
        players = [DouZeroAI(name="d0"), DouZeroAI(name="d1"), DouZeroAI(name="d2")]
        game = Game()
        game.start(seed=5)
        turns = 0
        while game.status == Game.STATUS_PLAYING:
            turns += 1
            assert turns < 1000
            seat = game.turn
            move = players[seat].choose_action(game.hands[seat], game.last_play, {"game": game})
            if move is None:
                assert game.do_pass(seat)
            else:
                assert game.can_play(seat, move), f"illegal douzero move: {move}"
                assert game.play(seat, move)
        assert game.winner_team in ("landlord", "farmers")
        assert turns < 200  # DouZero 打得应该比较紧凑
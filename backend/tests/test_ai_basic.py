import pytest

from dzcore import dou_dz_adapter as dz
from dzcore.ai_basic import BasicAI
from dzcore.game import Game


@pytest.fixture
def ai():
    return BasicAI(name="test-ai")


class TestBasicAI:
    def test_lead_never_none(self, ai):
        game = Game()
        game.start(seed=3)
        for seat in range(3):
            move = ai.choose_action(game.hands[seat], [])
            assert move is not None
            assert dz.is_valid_play(move)
            assert dz.has_cards(game.hands[seat], move)

    def test_pass_when_cannot_beat(self, ai):
        # 对手王炸，自己只有小牌 → 必须过
        hand = dz.Card.card_ints_from_string("3c-5d-9h-10s")
        last = dz.Card.card_ints_from_string("CJ-BJ")
        assert ai.choose_action(hand, last) is None

    def test_beats_with_legal_cards(self, ai):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-10s-2c-2d-4c-4d-4h-7c-7d-7h-Js-Kd-Kh")
        last = dz.Card.card_ints_from_string("5c-5d")  # 一对5
        move = ai.choose_action(hand, last)
        assert move is not None
        assert dz.can_beat(move, last)
        assert dz.has_cards(hand, move)

    def test_full_battle_all_legal(self, ai):
        players = [ai, BasicAI(name="b2"), BasicAI(name="b3")]
        games = 30
        finished = 0
        for seed in range(1, games + 1):
            game = Game()
            game.start(seed=seed)
            turns = 0
            while game.status == Game.STATUS_PLAYING:
                turns += 1
                assert turns < 1000
                seat = game.turn
                move = players[seat].choose_action(game.hands[seat], game.last_play)
                if move is None:
                    assert game.do_pass(seat)
                else:
                    assert game.can_play(seat, move)
                    assert game.play(seat, move)
            finished += 1
            assert game.winner_team in ("landlord", "farmers")
        assert finished == games
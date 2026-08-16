import pytest

from dzcore import dou_dz_adapter as dz
from dzcore.game import Game


@pytest.fixture
def game():
    return Game()


class TestDeal:
    def test_deal_sizes(self):
        g = Game()
        g.start(seed=1)
        assert sorted(len(h) for h in g.hands) == [17, 17, 20]  # 地主 20（含底牌）
        assert len(g.bottom) == 3
        assert g.landlord_seat in (0, 1, 2)

    def test_no_duplicate_cards(self):
        g = Game()
        g.start(seed=2)
        all_cards = [c for h in g.hands for c in h]
        assert sum(len(h) for h in g.hands) == 54
        assert len(set(all_cards)) == 54                       # 54 张各不相同
        for b in g.bottom:                                     # 底牌必在地主手里
            assert b in g.hands[g.landlord_seat]


class TestCanPlay:
    def test_lead_must_play(self, game):
        game.prime(
            [dz.Card.card_ints_from_string("3c-5d-9h-Ks"),
             dz.Card.card_ints_from_string("4c-6d-10h-As"),
             dz.Card.card_ints_from_string("7c-8d-Jh-2s")],
            bottom=[],
            landlord_seat=0,
            turn=0,
        )
        assert not game.can_pass(0)          # 领出不能过
        assert game.can_play(0, [dz.Card.new("5d")])       # 单5可出
        assert game.can_play(0, [dz.Card.new("3c")])       # 领出可出任意合法牌
        assert not game.can_play(0, [dz.Card.new("3c"), dz.Card.new("5d")])  # 不是合法牌型

    def test_must_own_cards(self, game):
        game.prime(
            [[dz.Card.new("3c"), dz.Card.new("9d")], [4], [7]],
            bottom=[], landlord_seat=0, turn=0,
        )
        assert not game.can_play(0, [dz.Card.new("5c")])   # 没有这张牌
        assert game.can_play(0, [dz.Card.new("9d")])

    def test_beat_rule(self, game):
        game.prime(
            [dz.Card.card_ints_from_string("3c-4c-9d-Ks"),
             dz.Card.card_ints_from_string("5c-6c-Jd-2s"),
             dz.Card.card_ints_from_string("7c-8c-Qd-BJ")],
            bottom=[], landlord_seat=0, turn=1,
        )
        # 先让 0 号出一张 3
        game.play(0, [dz.Card.new("3c")])
        assert game.turn == 1
        assert not game.can_play(1, [dz.Card.new("4c")])   # 手里没有 4
        assert game.can_play(1, [dz.Card.new("2s")])       # 手里有且能压过 3
        assert not game.can_play(1, [dz.Card.new("5c"), dz.Card.new("6c")])  # 非合法牌型

    def test_two_passes_clear_trick(self, game):
        game.prime(
            [dz.Card.card_ints_from_string("3c-4c-9d"),
             dz.Card.card_ints_from_string("5c-6c-Jd"),
             dz.Card.card_ints_from_string("7c-8c-Qd")],
            bottom=[], landlord_seat=0, turn=1,
        )
        game.play(1, [dz.Card.new("5c")])  # 1 出 5
        assert game.turn == 2
        game.do_pass(2)    # 2 过
        assert game.pass_count == 1
        game.do_pass(0)    # 0 过
        assert game.pass_count == 0
        assert game.last_play == []      # 一轮结束清零
        assert game.turn == 1            # 由 1 号重新领出
        assert not game.can_pass(1)

    def test_game_finishes_when_empty(self, game):
        game.prime(
            [[dz.Card.new("3c")], [dz.Card.new("4c")], [dz.Card.new("7c"), dz.Card.new("8c")]],
            bottom=[], landlord_seat=0, turn=0,
        )
        game.play(0, [dz.Card.new("3c")])
        assert game.status == Game.STATUS_FINISHED
        assert game.winner_team == "landlord"
        assert game.winner_seat == 0

    def test_farmer_win_team(self, game):
        game.prime(
            [[dz.Card.new("3c"), dz.Card.new("4c")],
             [dz.Card.new("5c")],
             [dz.Card.new("7c")]],
            bottom=[], landlord_seat=0, turn=1,
        )
        game.play(1, [dz.Card.new("5c")])
        assert game.status == Game.STATUS_FINISHED
        assert game.winner_team == "farmers"
        assert game.winner_seat == 1


class TestBombCount:
    def test_bomb_counted(self, game):
        hand0 = dz.Card.card_ints_from_string("3c-5d-9h-Ks")
        # 农民1 有炸弹 3333 + 一对 K
        hand1 = dz.Card.card_ints_from_string("3s-3d-3h-3c-Ks-Kh")
        # 农民2 有王炸
        hand2 = dz.Card.card_ints_from_string("4c-5d-9h-Js-BJ-CJ-Kd")
        game.prime([hand0, hand1, hand2], bottom=[], landlord_seat=0, turn=0)
        # 地主出 3；农民1 用炸弹(4张3) 压
        game.play(0, [dz.Card.new("3c")])
        bomb = dz.Card.card_ints_from_string("3s-3d-3h-3c")
        assert game.can_play(1, bomb)
        game.play(1, bomb)
        assert game.bomb_count == 1


class TestAdapterTypes:
    """覆盖主要牌型识别与压牌关系。"""

    def _ints(self, s):
        return dz.Card.card_ints_from_string(s)

    def test_representative_types_valid(self):
        cases = {
            "3c": "solo",
            "3c-3d": "pair",
            "3c-3d-3h": "trio",
            "3c-3d-3h-4c": "trio_solo",
            "3c-3d-3h-4c-4d": "trio_pair",
            "3c-4d-5h-6s-7c": "solo_chain_5",
            "3c-3d-4c-4d-5c-5d": "pair_chain_3",
            "3c-3d-3h-4c-4d-4h-5c-5d-5h": "trio_chain_3",
            "4c-4d-4h-4s-2c-2d": "four_two_solo",
            "3c-3d-3h-3s": "bomb",
            "CJ-BJ": "rocket",
        }
        for cards_str, expected in cases.items():
            assert dz.play_type(self._ints(cards_str)) == expected, cards_str

    def test_invalid_combos_rejected(self):
        bad = ["3c-4c", "3c-4d-5h-7s-8c", "3c-4d-7h"]
        for b in bad:
            assert dz.play_type(self._ints(b)) is None, b

    def test_beat_relations(self):
        greater = [
            ("5c", "3d"),
            ("2c", "Kd"),
            ("CJ", "2s"),
            ("5c-5d", "3c-3d"),
            ("4c-4d-4h-2s", "3c-3d-3h-5s"),
        ]
        for new_s, last_s in greater:
            assert dz.can_beat(self._ints(new_s), self._ints(last_s)), (new_s, last_s)
        # 炸弹压任意普通 | 王炸最大
        assert dz.can_beat(self._ints("3c-3d-3h-3s"), self._ints("2c-2d-2h-2s-8c-8d"))
        assert dz.can_beat(self._ints("CJ-BJ"), self._ints("3c-3d-3h-3s"))


class TestSimulate:
    def test_greedy_sim_finishes(self):
        from scripts.simulate_game import choose_move

        game = Game()
        game.start(seed=42)
        turns = 0
        while game.status == Game.STATUS_PLAYING:
            turns += 1
            assert turns < 500
            seat = game.turn
            move = choose_move(game, seat)
            if move is None:
                assert game.do_pass(seat)
            else:
                assert game.can_play(seat, move)
                assert game.play(seat, move)
        assert game.winner_team in ("landlord", "farmers")
        assert game.status == Game.STATUS_FINISHED
        assert turns > 2  # 确实打了一阵子
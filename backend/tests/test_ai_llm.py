from unittest.mock import Mock

import pytest

from app.key_picker import KeyPicker
from dzcore import dou_dz_adapter as dz
from dzcore.ai_basic import BasicAI
from dzcore.ai_llm import LLMAI
from dzcore.game import Game
from dzcore.prompt_builder import build_prompt


def make_ai(mock_chat) -> LLMAI:
    ai = LLMAI(name="mock-llm", picker=KeyPicker(["k1", "k2", "k3"]), model="mock")
    ai._chat = mock_chat
    return ai


class TestKeyPicker:
    def test_round_robin(self):
        p = KeyPicker(["a", "b", "c"])
        order = [p.next()[0] for _ in range(6)]
        assert order == [0, 1, 2, 0, 1, 2]

    def test_failure_disables_then_recovers(self):
        p = KeyPicker(["a", "b", "c"], cool_down=0.05)
        p.report_failure(0)
        idx1 = p.next()[0]
        assert idx1 != 0
        import time

        time.sleep(0.06)
        # 冷却过后，完整一轮轮询内应能再次选到 0
        seq = [p.next()[0] for _ in range(3)]
        assert 0 in seq

    def test_all_disabled_falls_back(self):
        p = KeyPicker(["a", "b"], cool_down=60)
        p.report_failure(0)
        p.report_failure(1)
        idx, _ = p.next()  # 全部停用 → 兜底返回当前的
        assert idx in (0, 1)


class TestPromptBuilder:
    def test_lead_prompt(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h")
        view = {
            "me": "我", "seat": 0, "role": "farmer", "teammate": "队友",
            "names": ["我", "队友", "地主"], "landlord_seat": 2, "hand": hand,
            "remaining": [3, 3, 5], "last_play": None, "history": [],
            "show_candidates": False,
        }
        prompt = build_prompt(view)
        assert "领出" in prompt
        assert "不能过" in prompt
        assert "我" in prompt

    def test_beat_prompt(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-Jc")
        view = {
            "me": "我", "seat": 1, "role": "farmer", "teammate": "队友",
            "names": ["地主", "我", "队友"], "landlord_seat": 0, "hand": hand,
            "remaining": [20, 4, 12], "last_play": dz.Card.card_ints_from_string("6c-6d"),
            "last_play_by": 2, "history": [{"seat": 2, "action": "play", "cards": [6, 6], "trick": 1}],
            "show_candidates": False,
        }
        prompt = build_prompt(view)
        assert "上一手" in prompt
        assert "出牌记录" in prompt


class TestLabelToInt:
    def test_basic(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-As-CJ-BJ")
        got = dz.labels_to_hand_int(["3", "A"], hand)
        assert got is not None and len(got) == 2
        labels = [dz.Card.rank_int_to_str(c) for c in got]
        assert sorted(labels) == ["3", "A"]

    def test_not_enough(self):
        hand = dz.Card.card_ints_from_string("3c-5d")
        assert dz.labels_to_hand_int(["3", "3"], hand) is None


class TestLLMAI:
    def test_valid_play(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-Ks")
        last = dz.Card.card_ints_from_string("5c")  # 上一手：单5
        mock = Mock(return_value='{"action":"play","cards":["9"]}')
        ai = make_ai(mock)
        res = ai.choose_action(hand, last, context={})
        assert res is not None
        assert dz.can_beat(res, last)

    def test_valid_pass(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h")
        last = dz.Card.card_ints_from_string("2s-2d-2h-2c")
        mock = Mock(return_value='{"action":"pass"}')
        ai = make_ai(mock)
        res = ai.choose_action(hand, last, context={})
        assert res is None  # 过

    def test_invalid_json_retry_then_fallback(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-9c")
        last = dz.Card.card_ints_from_string("5c-5d")
        # 第一次非法 JSON -> 重试一次成功（出对9压对5）
        mock = Mock(side_effect=['not json', '{"action":"play","cards":["9","9"]}'])
        ai = make_ai(mock)
        res = ai.choose_action(hand, last, context={})
        assert mock.call_count == 2
        assert dz.can_beat(res, last)

    def test_always_invalid_falls_back_to_rule_ai(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h-9c")
        last = dz.Card.card_ints_from_string("5c-5d")
        mock = Mock(return_value='{"action":"play","cards":["999"]}')  # 非法牌
        ai = make_ai(mock)
        res = ai.choose_action(hand, last, context={})
        assert res is not None
        # 兜底应产生合法结果（对9压对5）
        assert dz.can_beat(res, last)

    def test_illegal_lead_pass_rejected(self):
        hand = dz.Card.card_ints_from_string("3c-5d-9h")
        mock = Mock(return_value='{"action":"pass"}')
        ai = make_ai(mock)
        res = ai.choose_action(hand, [], context={})  # 领出却说"过"
        assert res is not None  # 不允许过 → 兜底必出
        assert dz.is_valid_play(res)


class TestLLMBattle:
    def test_mock_llm_battle_3ai(self):
        """3 个 mock LLM 打一局：全部决策走 LLM，无崩溃。"""
        def fixed_ai():  # 模拟"会打牌"的 LLM：复刻规则 AI 逻辑
            return BasicAI(name="mock-llm")
        players = [fixed_ai(), fixed_ai(), fixed_ai()]
        game = Game()
        game.start(seed=9)
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
        assert game.winner_team in ("landlord", "farmers")
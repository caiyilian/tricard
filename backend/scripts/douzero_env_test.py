import sys
import random

sys.path.insert(0, r"E:\case\tricard\third_party\DouZero")

from douzero.env.game import GameEnv
from douzero.evaluation.random_agent import RandomAgent


def random_deal(seed=7):
    rng = random.Random(seed)
    deck = []
    for rank in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17]:
        deck += [rank] * 4
    deck += [20, 30]
    assert len(deck) == 54
    rng.shuffle(deck)
    landlord_up = sorted(deck[0:17], reverse=True)
    landlord = sorted(deck[17:34], reverse=True)
    landlord_down = sorted(deck[34:51], reverse=True)
    three_landlord_cards = sorted(deck[51:54], reverse=True)
    return {
        "landlord": landlord,
        "landlord_up": landlord_up,
        "landlord_down": landlord_down,
        "three_landlord_cards": three_landlord_cards,
    }


def play_one_round(seed=7):
    players = {
        "landlord": RandomAgent(),
        "landlord_up": RandomAgent(),
        "landlord_down": RandomAgent(),
    }
    env = GameEnv(players)
    card_play_data = random_deal(seed)
    env.card_play_init(card_play_data)
    steps = 0
    while not env.game_over:
        assert steps < 500, "possible infinite loop"
        env.step()
        steps += 1
    winner = env.get_winner()
    bomb_num = env.get_bomb_num()
    print(f"round(seed={seed}) finished in {steps} turns, winner={winner}, bombs={bomb_num}")
    return steps, winner


if __name__ == "__main__":
    total = 0
    for s in range(1, 6):
        total += play_one_round(seed=s)[0]
    print(f"FULL-PIPELINE OK: 5 rounds played, avg turns={total / 5.0:.1f}")
"""斗地主业务逻辑包：牌型引擎适配 + 游戏状态机 + AI。"""

from . import dou_dz_adapter
from .game import Game, new_standard_game

__all__ = ["dou_dz_adapter", "Game", "new_standard_game"]
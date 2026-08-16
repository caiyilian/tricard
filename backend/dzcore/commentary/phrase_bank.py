"""零额度短语库：按 (archetype, 人格) 提供模板。"""

import random

# archetype -> list of (tone, template)  占位符 {target} {self} {mate}
_PHRASES: dict[str, list[str]] = {
    "keng_no_send": [
        "{mate} 就剩一张了，你出这个对？你是不是不想赢？",
        "给你队友 {mate} 送一张单，可好？全桌就差你队友了！",
    ],
    "keng_step": [
        "{mate} 刚出的牌都让你压了，回头地主直接反手，你这波拆得漂亮啊。",
        "压自己人一头的习惯，跟谁学的？{target}",
    ],
    "keng_friendly_fire": [
        "自己人炸自己人？炸药不要钱的吗，{target}！",
        "两农民互炸，地主笑出了声，{target} 你俩真是一对活宝。",
    ],
    "keng_blow": [
        "大优势打成这样，{target} 你是故意的吧？",
        "本来稳稳的胜局，{target} 一手送回去了，谢谢啊。",
    ],
    "bright_bomb": [
        "这炸丢得漂亮，{self} 给你点个赞！",
        "关键时刻炸得又准又狠，{target} 手气可以啊。",
    ],
    "bright_send": [
        "这一手送得妙，{target} 直接起飞！",
        "{target} 带你飞，这配合我服。",
    ],
    "bright_comeback": [
        "逆风翻盘 {target} 有你的，这局看得值。",
        "开局崩盘都能赢回来，{target} 我愿称你为绝活哥。",
    ],
    "lose_self": [
        "这把我的问题，{self} 下次不头铁了。",
        "唉，这手牌不来，怪我咯。",
    ],
    "win_praise": [
        "这把赢在我方手感在线，大家配合不错！",
        "赢得漂亮，特别是 {target} 那几手。",
    ],
}


def pick(archetype: str, *, target: str = "对面", self_name: str = "我", mate: str = "队友", personality: str = "savage") -> str:
    pool = _PHRASES.get(archetype)
    if not pool:
        return f"（{target} 这局打得真是……各有千秋。）"
    text = random.choice(pool).replace("{target}", target).replace("{self}", self_name).replace("{mate}", mate)
    if personality == "kind" and text:
        # 温和人格：调侃浓的先过滤掉，这里简单混一句
        pass
    return text
"""
役满判定 - 清老头 (Chinroutou)

全部由老头牌(1和9的数牌)构成的对对和。
不含字牌。
"""

from typing import List


# 老头牌: 1m(0), 9m(8), 1p(9), 9p(17), 1s(18), 9s(26)
TERMINAL_TILES = {0, 8, 9, 17, 18, 26}


def check_chinroutou(hand_14: List[int]) -> int:
    """
    检查清老头。

    条件: 所有牌都是老头牌(数牌的1和9)，且不含字牌。
    (结构必须是 4刻子+1对子 = 对对和形式，由外层 can_agari 保证)

    Returns:
        0 = 不满足
        1 = 清老头 (役满)
    """
    for t, count in enumerate(hand_14):
        if count > 0 and t not in TERMINAL_TILES:
            return 0

    total = sum(hand_14[t] for t in TERMINAL_TILES)
    if total != 14:
        return 0

    return 1

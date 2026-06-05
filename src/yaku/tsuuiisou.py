"""
役满判定 - 字一色 (Tsuuiisou)

全部由字牌(东南西北白发中)构成的对对和或七对子。
"""

from typing import List
from ..tile import NUM_TILES, HONOR_TILES


def check_tsuuiisou(hand_14: List[int]) -> int:
    """
    检查字一色。

    条件: 所有牌都是字牌，且能构成和牌形。
    (结构检查和牌形由外层 can_agari 保证)

    Returns:
        0 = 不满足
        1 = 字一色 (役满)
    """
    # 非字牌必须为 0
    for t in range(27):
        if hand_14[t] > 0:
            return 0

    # 所有 14 张必须都是字牌
    total = sum(hand_14[t] for t in HONOR_TILES)
    if total != 14:
        return 0

    return 1

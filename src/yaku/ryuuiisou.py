"""
役满判定 - 绿一色 (Ryuuiisou)

仅由 2s, 3s, 4s, 6s, 8s, 发 构成的牌型。
"""

from typing import List


# 绿一色合法牌: 2s(19), 3s(20), 4s(21), 6s(23), 8s(25), 发(32)
GREEN_TILES = {19, 20, 21, 23, 25, 32}


def check_ryuuiisou(hand_14: List[int]) -> int:
    """
    检查绿一色。

    Returns:
        0 = 不满足
        1 = 绿一色 (役满)
    """
    for t, count in enumerate(hand_14):
        if count > 0 and t not in GREEN_TILES:
            return 0

    return 1

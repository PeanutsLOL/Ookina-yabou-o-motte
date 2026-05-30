"""
役满判定 - 大四喜 (Daisuushi) / 小四喜 (Shousuushi)

大四喜: 东南西北各一组刻子(或杠) — 双倍役满
小四喜: 东南西北中3组刻子+1组雀头 — 役满
"""

from typing import List

# 风牌: 东(27) 南(28) 西(29) 北(30)
WIND_TILES = [27, 28, 29, 30]


def check_daisuushi(hand_14: List[int]) -> int:
    """
    检查大四喜: 东南西北各一组刻子。

    Returns:
        0 = 不满足
        2 = 大四喜 (双倍役满)
    """
    for t in WIND_TILES:
        if hand_14[t] < 3:
            return 0
    return 2


def check_shousuushi(hand_14: List[int]) -> int:
    """
    检查小四喜: 3组风刻子+1组风雀头。

    Returns:
        0 = 不满足
        1 = 小四喜 (役满)
    """
    kotsu_count = 0
    toitsu_count = 0

    for t in WIND_TILES:
        if hand_14[t] >= 3:
            kotsu_count += 1
        elif hand_14[t] == 2:
            toitsu_count += 1

    if kotsu_count == 3 and toitsu_count == 1:
        return 1

    return 0

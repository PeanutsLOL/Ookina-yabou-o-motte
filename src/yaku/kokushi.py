"""
役满判定 - 国士无双 (Kokushi Musou)

13种幺九牌（1,9万筒索 + 东南西北白发中）各至少1张，
且其中1种至少有2张。

国士无双十三面: 14张均为幺九牌，构成13种幺九各1张+任意幺九1张作雀头。
此时听13种幺九牌中的任意一张。
"""

from typing import List
from ..tile import YAOCHU_TILES, NUM_TILES


def check_kokushi(hand_14: List[int]) -> int:
    """
    检查手牌是否满足国士无双。

    Args:
        hand_14: 长度为34的手牌计数数组 (总和应为14)

    Returns:
        0 = 不满足
        1 = 国士无双
        2 = 国士无双十三面听牌
    """
    # 计算幺九牌的分布
    present_yaochu = 0   # 出现的幺九牌种类数
    has_pair = False     # 是否有至少一种幺九牌≥2张
    single_count = 0     # 恰好1张的幺九牌种类数

    for t in YAOCHU_TILES:
        count = hand_14[t]
        if count >= 1:
            present_yaochu += 1
        if count >= 2:
            has_pair = True
        if count == 1:
            single_count += 1

    # 必须所有幺九牌都出现
    if present_yaochu != 13:
        return 0

    # 必须有至少一个对子
    if not has_pair:
        return 0

    # 检查是否含有非幺九牌
    total_in_yaochu = sum(hand_14[t] for t in YAOCHU_TILES)
    if total_in_yaochu != 14:
        return 0  # 有非幺九牌混入

    # 国士无双十三面: 所有13种幺九牌各1张 + 任意1张幺九 = 恰好有1种2张
    if single_count == 12:
        # 检查是否有超过2张的幺九牌
        for t in YAOCHU_TILES:
            if hand_14[t] >= 3:
                return 1  # 有3张以上的，仅算普通国士
        return 2  # 十三面听牌

    return 1  # 普通国士无双

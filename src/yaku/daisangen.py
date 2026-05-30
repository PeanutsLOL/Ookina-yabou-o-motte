"""
役满判定 - 大三元 (Daisangen)

白(31)、发(32)、中(33)各有一组刻子（或杠）。
不要求门清。
"""

from typing import List


def check_daisangen(hand_14: List[int]) -> int:
    """
    检查手牌是否满足大三元。

    Args:
        hand_14: 手牌计数数组

    Returns:
        0 = 不满足
        1 = 大三元
    """
    # 白(31)、发(32)、中(33)
    dragons = [31, 32, 33]

    for d in dragons:
        if hand_14[d] < 3:
            # 注意：副露中的三元牌已经在 hand_14 中扣除，
            # 所以这里只检查手牌部分不够，需要特殊处理。
            # 当前限制：只能在手牌中有三元刻子时判定。
            # TODO: 后续版本支持从 melds 中读取副露的三元牌。
            return 0

    return 1


def check_shousangen(hand_14: List[int]) -> int:
    """
    检查小三元（非役满，仅内部使用）。
    两刻 + 一对的三元牌。
    """
    dragons = [31, 32, 33]
    kotsu = 0
    toitsu = 0

    for d in dragons:
        if hand_14[d] >= 3:
            kotsu += 1
        elif hand_14[d] == 2:
            toitsu += 1

    return kotsu == 2 and toitsu == 1

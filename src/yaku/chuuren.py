"""
役满判定 - 九莲宝灯 (Chuuren Poutou)

同一种花色的 1112345678999 + 任意一张同花色牌。
必须门清。

纯正九莲宝灯: 听九面（123456789 同花色均可和）。
"""

from typing import List
from ..tile import NUM_TILES, suit, SUIT_JIHAI


def check_chuuren(hand_14: List[int]) -> int:
    """
    检查手牌是否满足九莲宝灯。

    Args:
        hand_14: 手牌计数数组

    Returns:
        0 = 不满足
        1 = 九莲宝灯
        2 = 纯正九莲宝灯（九面听）
    """
    # 检查是否全为同一花色
    dominant_suit = -1
    for t in range(NUM_TILES):
        if hand_14[t] > 0:
            s = suit(t)
            if s == SUIT_JIHAI:
                return 0  # 含字牌，不可能是九莲
            if dominant_suit == -1:
                dominant_suit = s
            elif s != dominant_suit:
                return 0  # 多种花色

    if dominant_suit == -1:
        return 0

    base = dominant_suit * 9  # 0, 9, 18

    # 检查是否满足 1112345678999 模式
    required_pattern = [3, 1, 1, 1, 1, 1, 1, 1, 3]  # 最小要求

    # 当前手牌中该花色的分布
    current = [hand_14[base + i] for i in range(9)]

    # 检查是否至少满足最低模式
    for i in range(9):
        if current[i] < required_pattern[i]:
            return 0

    # 总数应为14
    total = sum(current)
    if total != 14:
        return 0

    # 多出的那张牌在哪里？
    # (每个位置至少 required_pattern[i], 多出的那张是第14张)
    extra_found = False
    for i in range(9):
        if current[i] > required_pattern[i]:
            extra_found = True
            break

    if not extra_found:
        return 0

    # 判断是否为纯正九莲（听九面）
    # 纯正九莲: 1112345678999，即雀头在1或9，且多余牌在中间
    # 更准确: 满足 1112345678999 且没有任何位置超过3张
    is_junsei = True
    for i in range(9):
        if current[i] > 3:  # 某位置超过3张 --> 不是纯正
            is_junsei = False
            break

    if is_junsei:
        # 九面听: 123456789 同花色均可和
        return 2

    return 1

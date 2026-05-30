"""
役满判定 - 四暗刻 (Suu Ankou)

手牌包含4组暗刻（或暗杠）和1组雀头。
必须门清（无明露）。暗杠视为暗刻。

四暗刻单骑: 已有4暗刻，剩余1张单牌等做成雀头。
"""

from typing import List
from ..tile import NUM_TILES, suit, SUIT_JIHAI
from ..state import Meld


def check_suuankou(hand_14: List[int], melds: List[Meld] = None) -> int:
    """
    检查手牌是否满足四暗刻。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        1 = 四暗刻
        2 = 四暗刻单骑听牌
    """
    if melds is None:
        melds = []

    # 必须门清（不能有明露）
    if any(m.is_open for m in melds):
        return 0

    # 统计已有的暗杠（暗刻）
    ankou_count = 0
    for m in melds:
        if m.meld_type == "ankan":
            ankou_count += 1

    # 从手牌中统计暗刻和对子
    remaining = hand_14.copy()

    hand_ankou = 0
    hand_pairs = 0
    hand_singles = 0

    # 找出暗刻 (count ≥ 3)
    for t in range(NUM_TILES):
        if remaining[t] >= 3:
            hand_ankou += remaining[t] // 3  # 可能有多个刻子（比如4张=1刻+1张）
            remaining[t] %= 3

    # 找出对子和单张
    for t in range(NUM_TILES):
        if remaining[t] == 2:
            hand_pairs += 1
        elif remaining[t] == 1:
            hand_singles += 1

    total_ankou = ankou_count + hand_ankou

    # 四暗刻: 4暗刻 + 1雀头
    if total_ankou == 4 and hand_pairs == 1 and hand_singles == 0:
        return 1

    # 四暗刻单骑: 4暗刻 + 1单张（听雀头）
    if total_ankou == 4 and hand_pairs == 0 and hand_singles == 1:
        return 2

    return 0

"""
役满判定 - 大四喜 (Daisuushi) / 小四喜 (Shousuushi)

大四喜: 东南西北各一组刻子(或杠) — 双倍役满
小四喜: 东南西北中3组刻子+1组雀头 — 役满
"""

from typing import List, Optional
from ..state import Meld

# 风牌: 东(27) 南(28) 西(29) 北(30)
WIND_TILES = [27, 28, 29, 30]


def _count_wind_from_melds(melds: List[Meld]) -> List[int]:
    """从副露中统计风牌刻子数（数组索引与 hand 一致）"""
    meld_hand = [0] * 34
    for m in melds:
        if m.meld_type in ("pon", "kan", "ankan", "kakan"):
            t = m.tiles[0]
            if t in WIND_TILES:
                meld_hand[t] += 3  # 一组刻子=3张
    return meld_hand


def check_daisuushi(hand_14: List[int], melds: Optional[List[Meld]] = None) -> int:
    """
    检查大四喜: 东南西北各一组刻子。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        2 = 大四喜 (双倍役满)
    """
    meld_hand = _count_wind_from_melds(melds) if melds else []
    for t in WIND_TILES:
        hand_count = hand_14[t]
        meld_count = meld_hand[t] if melds else 0
        if hand_count + meld_count < 3:
            return 0
    return 2


def check_shousuushi(hand_14: List[int], melds: Optional[List[Meld]] = None) -> int:
    """
    检查小四喜: 3组风刻子+1组风雀头。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        1 = 小四喜 (役满)
    """
    meld_hand = _count_wind_from_melds(melds) if melds else []
    kotsu_count = 0
    toitsu_count = 0

    for t in WIND_TILES:
        hand_count = hand_14[t]
        meld_count = meld_hand[t] if melds else 0
        total = hand_count + meld_count
        if total >= 3:
            kotsu_count += 1
            if total >= 5:
                toitsu_count += 1
        elif total == 2:
            toitsu_count += 1

    if kotsu_count == 3 and toitsu_count == 1:
        return 1

    return 0

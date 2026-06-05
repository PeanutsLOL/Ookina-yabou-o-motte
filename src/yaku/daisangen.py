"""
役满判定 - 大三元 (Daisangen)

白(31)、发(32)、中(33)各有一组刻子（或杠）。
不要求门清。
"""

from typing import List, Optional
from ..state import Meld


def _count_dragon_from_melds(melds: List[Meld]) -> List[int]:
    """从副露中统计三元牌刻子数（数组索引与 hand 一致）"""
    meld_hand = [0] * 34
    for m in melds:
        if m.meld_type in ("pon", "kan", "ankan", "kakan"):
            t = m.tiles[0]
            if t in (31, 32, 33):
                meld_hand[t] += 3  # 一组刻子=3张
    return meld_hand


def check_daisangen(hand_14: List[int], melds: Optional[List[Meld]] = None) -> int:
    """
    检查手牌是否满足大三元。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        1 = 大三元
    """
    dragons = [31, 32, 33]
    meld_hand = _count_dragon_from_melds(melds) if melds else []

    for d in dragons:
        hand_count = hand_14[d]
        meld_count = meld_hand[d] if melds else 0
        if hand_count + meld_count < 3:
            return 0

    return 1


def check_shousangen(hand_14: List[int], melds: Optional[List[Meld]] = None) -> int:
    """
    检查小三元（非役满，仅内部使用）。
    两刻 + 一对的三元牌。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表
    """
    dragons = [31, 32, 33]
    meld_hand = _count_dragon_from_melds(melds) if melds else []
    kotsu = 0
    toitsu = 0

    for d in dragons:
        hand_count = hand_14[d]
        meld_count = meld_hand[d] if melds else 0
        total = hand_count + meld_count
        if total >= 3:
            kotsu += 1
            # 副露3张+手牌2张 → 既有刻子又有对子
            if total >= 5:
                toitsu += 1
        elif total == 2:
            toitsu += 1

    return kotsu == 2 and toitsu == 1

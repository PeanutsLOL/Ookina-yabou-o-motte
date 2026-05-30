"""
役满判定 - 四杠子 (Suukantsu)

四组杠子。4个杠子(明杠或暗杠均可)。
不要求门清（明杠也可以）。

注意: 杠子包括 暗杠(ankan)、明杠(kan)、加杠(kakan)。
"""

from typing import List
from ..state import Meld


def check_suukantsu(hand_14: List[int], melds: List[Meld]) -> int:
    """
    检查四杠子。

    杠子数量 = 副露中的杠 + 手牌中可宣告的杠。
    注意: 手牌中有4张同牌可宣告暗杠，但判定时只看已有副露。

    Args:
        hand_14: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        1 = 四杠子 (役满)
    """
    kan_count = 0

    # 统计副露中的杠
    for m in melds:
        if m.meld_type in ("kan", "ankan", "kakan"):
            kan_count += 1

    # 手牌中有4张同牌 = 可以宣告暗杠（在摸到第4张后）
    for count in hand_14:
        if count >= 4:
            kan_count += 1

    if kan_count >= 4:
        return 1

    return 0

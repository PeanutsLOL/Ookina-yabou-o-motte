"""
普通役种（非役满）计算模块

用于累计役满(数え役满, 13翻+)判定。

参考: https://wiki.queji.com/mediawiki/index.php/%E5%BD%B9%E7%A8%AE%E8%A1%A8
"""

from typing import List, Optional
from ..tile import (
    NUM_TILES, suit, SUIT_JIHAI, is_yaochu, is_terminal, is_honor,
    dora_indicator_to_dora
)
from ..state import GameState


def _has_valid_mentsu_decomp(hand: List[int]) -> bool:
    """简单检查能否拆成4面子+1雀头（不关心役种）"""
    from ..decompose import has_valid_decomposition, check_seven_pairs
    return has_valid_decomposition(hand) or check_seven_pairs(hand)


def _count_sequences(hand: List[int]) -> List[tuple]:
    """
    尝试对14张手牌做面子拆分，返回顺子列表。
    仅用于役种判定，取第一个合法拆分。
    """
    # 使用 decompose_hand 获取一个拆分
    from ..decompose import decompose_hand
    results = decompose_hand(hand)
    if not results:
        return []
    # 取第一个拆分方案
    return [m for m in results[0] if m[0] == 'shuntsu']


def check_pinfu(hand: List[int], pair_tile: int,
                player_wind: int, round_wind: int) -> int:
    """
    平和: 全部顺子 + 雀头非役牌 + 两面听。
    简化: 有顺子拆分且雀头非自风/场风/三元即算。
    """
    shuntsu = _count_sequences(hand)
    if len(shuntsu) != 4:
        return 0
    # 雀头不能是自风/场风/三元
    if pair_tile == player_wind or pair_tile == round_wind:
        return 0
    if pair_tile in (31, 32, 33):  # 三元牌
        return 0
    return 1


def check_tanyao(hand: List[int]) -> int:
    """断幺九: 不含幺九牌(1,9,字)"""
    for t in range(NUM_TILES):
        if hand[t] > 0 and is_yaochu(t):
            return 0
    return 1


def check_iipeikou(hand: List[int]) -> int:
    """
    一杯口: 两组完全相同的顺子。门清限定。
    返回: 1 (一杯口), 或间接用于二杯口判定
    """
    shuntsu = _count_sequences(hand)
    if len(shuntsu) < 2:
        return 0
    # 检查是否有两组相同的顺子
    seen = set()
    for s in shuntsu:
        key = tuple(sorted(s[1]))
        if key in seen:
            return 1
        seen.add(key)
    return 0


def check_ryanpeikou(hand: List[int]) -> int:
    """
    二杯口: 两组一杯口（即4组顺子由两对相同顺子组成）。门清限定。
    实际上就是"7对子形式的顺子"。
    """
    shuntsu = _count_sequences(hand)
    if len(shuntsu) != 4:
        return 0
    # 4组顺子应能配对成2对相同
    keys = [tuple(sorted(s[1])) for s in shuntsu]
    keys.sort()
    if keys[0] == keys[1] and keys[2] == keys[3] and keys[0] != keys[2]:
        return 3
    # 也可能7对子形态
    from ..decompose import check_seven_pairs
    if check_seven_pairs(hand):
        # 七对子中是否有完全相同的顺子型对子?
        # 简化: 如果是7对子且每个对子都有相邻对子构成顺子，算二杯口
        pairs = [t for t in range(NUM_TILES) if hand[t] == 2]
        if len(pairs) == 7:
            seq_pairs = 0
            for t in pairs:
                s = suit(t)
                if s != SUIT_JIHAI:
                    n = t % 9
                    if n <= 6:
                        if (t+1) in pairs and (t+2) in pairs:
                            seq_pairs += 1
            if seq_pairs >= 4:
                return 3
    return 0


def check_ittsuu(hand: List[int]) -> int:
    """
    一气通贯: 同花色的123+456+789三组顺子。
    门清2翻, 副露1翻(简化返回2)。
    """
    for base in (0, 9, 18):
        if (hand[base] >= 1 and hand[base+1] >= 1 and hand[base+2] >= 1 and
            hand[base+3] >= 1 and hand[base+4] >= 1 and hand[base+5] >= 1 and
            hand[base+6] >= 1 and hand[base+7] >= 1 and hand[base+8] >= 1):
            return 2
    return 0


def check_sanshoku(hand: List[int]) -> int:
    """
    三色同顺: 万筒索各一组相同数字的顺子。
    门清2翻, 副露1翻(简化返回2)。
    """
    for n in range(7):  # 1~7
        if (hand[n] >= 1 and hand[n+1] >= 1 and hand[n+2] >= 1 and
            hand[n+9] >= 1 and hand[n+10] >= 1 and hand[n+11] >= 1 and
            hand[n+18] >= 1 and hand[n+19] >= 1 and hand[n+20] >= 1):
            return 2
    return 0


def check_chinitsu(hand: List[int]) -> int:
    """清一色: 所有牌同花色。门清6翻, 副露5翻(简化返回6)。"""
    dominant = -1
    for t in range(NUM_TILES):
        if hand[t] > 0:
            s = suit(t)
            if s == SUIT_JIHAI:
                return 0
            if dominant == -1:
                dominant = s
            elif s != dominant:
                return 0
    return 6 if dominant >= 0 else 0


def check_honitsu(hand: List[int]) -> int:
    """混一色: 同花色数牌+字牌。门清3翻, 副露2翻(简化返回3)。"""
    num_suit = -1
    for t in range(NUM_TILES):
        if hand[t] > 0:
            s = suit(t)
            if s != SUIT_JIHAI:
                if num_suit == -1:
                    num_suit = s
                elif s != num_suit:
                    return 0
    return 3 if num_suit >= 0 else 0


def check_toitoi(hand: List[int]) -> int:
    """对对和: 4刻子+1雀头。2翻。"""
    kotsu = 0
    pairs = 0
    for t in range(NUM_TILES):
        if hand[t] >= 3:
            kotsu += 1
        elif hand[t] == 2:
            pairs += 1
    return 2 if kotsu == 4 and pairs == 1 else 0


def check_sanankou(hand: List[int]) -> int:
    """三暗刻: 3组暗刻。2翻。"""
    ankou = sum(1 for t in range(NUM_TILES) if hand[t] >= 3)
    return 2 if ankou >= 3 else 0


def check_chiitoitsu(hand: List[int]) -> int:
    """七对子: 7个对子。2翻, 门清限定。"""
    from ..decompose import check_seven_pairs
    return 2 if check_seven_pairs(hand) else 0


def calculate_dora(hand: List[int], dora_indicators: List[int],
                   ura_indicators: List[int] = None) -> int:
    """
    计算宝牌数。
    每张宝牌指示牌对应一种宝牌，手牌中每张宝牌=+1翻。
    """
    dora_tiles = set()
    for ind in dora_indicators:
        dora_tiles.add(dora_indicator_to_dora(ind))
    if ura_indicators:
        for ind in ura_indicators:
            dora_tiles.add(dora_indicator_to_dora(ind))

    count = 0
    for d in dora_tiles:
        count += hand[d]
    return count


def calculate_regular_han(state: GameState) -> int:
    """
    计算普通役种的总番数(不含役满)。

    返回总番数。若≥13即为累计役满。
    """
    hand = state.hand
    if state.hand_size != 14:
        return 0

    if not _has_valid_mentsu_decomp(hand):
        return 0

    total = 0
    is_menzen = state.is_menzen

    # ── 牌种系 ──
    chinitsu = check_chinitsu(hand)
    if chinitsu > 0:
        total += chinitsu
    else:
        total += check_honitsu(hand)

    # ── 顺子系 ──
    total += check_ittsuu(hand)
    total += check_sanshoku(hand)

    # ── 二杯口(高于一杯口) ──
    rpk = check_ryanpeikou(hand)
    if rpk > 0:
        total += rpk
    else:
        total += check_iipeikou(hand)

    # ── 刻子系 ──
    tt = check_toitoi(hand)
    if tt > 0:
        total += tt
    total += check_sanankou(hand)

    # ── 七对子 ──
    total += check_chiitoitsu(hand)

    # ── 基础役 ──
    total += check_tanyao(hand)

    # ── 门清系 ──
    if is_menzen:
        total += 1  # 立直 (简化: 总是加)
        total += 1  # 门前清自摸和

    # ── 宝牌 ──
    total += calculate_dora(hand, state.dora_indicators,
                            state.ura_dora_indicators)

    return total

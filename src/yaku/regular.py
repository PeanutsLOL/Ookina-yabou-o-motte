"""
普通役种（非役满）计算模块

用于累计役满(数え役满, 13翻+)判定。

参考: https://wiki.queji.com/mediawiki/index.php/%E5%BD%B9%E7%A8%AE%E8%A1%A8
"""

from typing import Callable, List, Optional
from ..tile import (
    NUM_TILES, suit, SUIT_JIHAI, is_yaochu, is_terminal, is_honor,
    dora_indicator_to_dora
)
from ..state import GameState, Meld


def _has_valid_mentsu_decomp(hand: List[int]) -> bool:
    """简单检查能否拆成4面子+1雀头（不关心役种）"""
    from ..decompose import has_valid_decomposition, check_seven_pairs
    return has_valid_decomposition(hand) or check_seven_pairs(hand)


def _count_sequences(hand: List[int]) -> List[tuple]:
    """
    尝试对14张手牌做面子拆分，返回顺子列表。
    仅用于役种判定，取第一个合法拆分（使用 early-exit 版本）。
    """
    from ..decompose import decompose_hand_first
    result = decompose_hand_first(hand)
    if not result:
        return []
    return [m for m in result if m[0] == 'shuntsu']


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
        # 高点法：如果是7对子且每个对子都有相邻对子构成顺子，算二杯口
        # 示例：112233445566p 11z 同时满足七对子（2番）和二杯口（3番），按3番计算。
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


def check_ittsuu(hand: List[int], is_menzen: bool = True) -> int:
    """
    一气通贯: 同花色的123+456+789三组顺子。
    门清2翻, 副露1翻。
    """
    for base in (0, 9, 18):
        if (hand[base] >= 1 and hand[base+1] >= 1 and hand[base+2] >= 1 and
            hand[base+3] >= 1 and hand[base+4] >= 1 and hand[base+5] >= 1 and
            hand[base+6] >= 1 and hand[base+7] >= 1 and hand[base+8] >= 1):
            return 2 if is_menzen else 1
    return 0


def check_sanshoku(hand: List[int], is_menzen: bool = True) -> int:
    """
    三色同顺: 万筒索各一组相同数字的顺子。
    门清2翻, 副露1翻。
    """
    for n in range(7):  # 1~7
        if (hand[n] >= 1 and hand[n+1] >= 1 and hand[n+2] >= 1 and
            hand[n+9] >= 1 and hand[n+10] >= 1 and hand[n+11] >= 1 and
            hand[n+18] >= 1 and hand[n+19] >= 1 and hand[n+20] >= 1):
            return 2 if is_menzen else 1
    return 0


def check_sanshokudoukou(hand: List[int]) -> int:
    """
    三色同刻: 万筒索各一组相同数字的刻子。
    门清/副露均2翻。

    Returns:
        0 = 不满足
        2 = 三色同刻
    """
    for n in range(9):  # 数字 1~9
        if hand[n] >= 3 and hand[n + 9] >= 3 and hand[n + 18] >= 3:
            return 2
    return 0


def check_honroutou(hand: List[int]) -> int:
    """
    混老头 (Honroutou / Mixed Outside Hand)

    所有牌都是幺九牌(1,9,字牌)，结构为4刻子+1雀头(对对和)。
    必须同时包含老头牌和字牌(区别于清老头和字一色)。

    门清/副露均2翻。
    (注: 纯老头→清老头役满; 纯字牌→字一色役满; 两者混合→混老头2翻)

    Returns:
        0 = 不满足
        2 = 混老头
    """
    has_terminal = False
    has_honor = False
    for t in range(NUM_TILES):
        if hand[t] > 0:
            if not is_yaochu(t):
                return 0  # 含中张牌
            if is_terminal(t):
                has_terminal = True
            if is_honor(t):
                has_honor = True

    if not has_terminal or not has_honor:
        return 0  # 纯老头或纯字牌, 由役满判定处理

    # 全幺九 → 必然是对对和形式, 直接验证
    kotsu = 0
    pairs = 0
    for t in range(NUM_TILES):
        if hand[t] >= 3:
            kotsu += 1
        elif hand[t] == 2:
            pairs += 1
    if kotsu == 4 and pairs == 1:
        return 2
    return 0


def check_yakuhai(hand: List[int], player_wind: int, round_wind: int) -> int:
    """
    役牌: 自风/场风/三元(白发中)的刻子各计1翻。

    Returns:
        役牌总翻数 (0~)
    """
    total = 0
    # 三元牌: 白(31) 发(32) 中(33) — 各1翻
    for t in (31, 32, 33):
        if hand[t] >= 3:
            total += 1
    # 自风
    if player_wind and hand[player_wind] >= 3:
        total += 1
    # 场风
    if round_wind and hand[round_wind] >= 3:
        total += 1
    return total


def check_honchantaiyaochuu(hand: List[int], is_menzen: bool = True) -> int:
    """
    混全带幺九 (Honchantaiyaochuu / Half Outside Hand)

    所有面子(顺子/刻子)和雀头都包含幺九牌(1,9或字牌)。
    必须包含至少一张字牌(区别于纯全带幺九)。

    门清2翻, 副露1翻。

    Returns:
        0 = 不满足
        2 = 混全带幺九 (门清)
        1 = 混全带幺九 (副露)
    """
    # 必须包含至少一张字牌
    has_honor = any(hand[t] > 0 and is_honor(t) for t in range(NUM_TILES))
    if not has_honor:
        return 0

    # 检查是否存在满足约束的拆分
    if not _check_honchantaiyaochuu_decomp(hand):
        return 0

    return 2 if is_menzen else 1


def _check_honchantaiyaochuu_decomp(hand: List[int]) -> bool:
    """检查手牌能否拆成4面子+1雀头，每个都包含幺九牌"""
    return _check_constrained_decomp(hand, is_yaochu, is_yaochu)


def _check_constrained_decomp(
    hand: List[int],
    pair_ok: Callable[[int], bool],
    kotsu_ok: Callable[[int], bool],
) -> bool:
    """
    泛型拆分检查：4面子+1雀头，雀头和刻子受 given predicates 约束。

    Args:
        hand: 14张手牌计数数组
        pair_ok(tile) -> bool: 雀头候选
        kotsu_ok(tile) -> bool: 刻子候选
    """
    for janto in range(NUM_TILES):
        if hand[janto] >= 2 and pair_ok(janto):
            c = hand.copy()
            c[janto] -= 2
            if _check_melds_constrained(c, 4, kotsu_ok):
                return True
    return False


def _check_melds_constrained(
    counts: List[int], needed: int, kotsu_ok: Callable[[int], bool]
) -> bool:
    """
    递归检查能否拆出 needed 个面子，每个都包含幺九牌。

    允许的面子:
      - kotsu_ok(t) 为真的刻子
      - 123 顺子 (包含老头1)
      - 789 顺子 (包含老头9)
    """
    if needed == 0:
        return all(c == 0 for c in counts)

    # 找到第一个非零牌
    first = -1
    for i in range(NUM_TILES):
        if counts[i] > 0:
            first = i
            break
    if first == -1:
        return False

    s = suit(first)
    n = first % 9

    # 尝试刻子
    if counts[first] >= 3 and kotsu_ok(first):
        counts[first] -= 3
        if _check_melds_constrained(counts, needed - 1, kotsu_ok):
            counts[first] += 3
            return True
        counts[first] += 3

    # 尝试顺子 (仅123或789包含幺九)
    if s != SUIT_JIHAI:
        # 123: tiles at n=0,1,2, shuntsu starts at n=0
        # 789: tiles at n=6,7,8, shuntsu starts at n=6
        shuntsu_start = -1
        if n <= 2:
            shuntsu_start = 0
        elif n >= 6:
            shuntsu_start = 6

        if shuntsu_start >= 0:
            base = s * 9
            t0, t1, t2 = base + shuntsu_start, base + shuntsu_start + 1, base + shuntsu_start + 2
            if counts[t0] >= 1 and counts[t1] >= 1 and counts[t2] >= 1:
                counts[t0] -= 1
                counts[t1] -= 1
                counts[t2] -= 1
                if _check_melds_constrained(counts, needed - 1, kotsu_ok):
                    counts[t0] += 1
                    counts[t1] += 1
                    counts[t2] += 1
                    return True
                counts[t0] += 1
                counts[t1] += 1
                counts[t2] += 1

    return False


def check_junchantaiyaochuu(hand: List[int], is_menzen: bool = True) -> int:
    """
    纯全带幺九 (Junchan Taiyaochuu / Pure Outside Hand)

    所有面子(顺子/刻子)和雀头都包含老头牌(1或9)。
    不得包含任何字牌(区别于混全带幺九)。

    门清3翻, 副露2翻。

    Returns:
        0 = 不满足
        3 = 纯全带幺九 (门清)
        2 = 纯全带幺九 (副露)
    """
    # 不得包含字牌
    has_honor = any(hand[t] > 0 and is_honor(t) for t in range(NUM_TILES))
    if has_honor:
        return 0

    # 必须包含至少一张老头牌(否则会是断幺九)
    has_terminal = any(hand[t] > 0 and is_terminal(t) for t in range(NUM_TILES))
    if not has_terminal:
        return 0

    # 检查是否存在满足约束的拆分（雀头和刻子都必须是老头牌）
    if not _check_constrained_decomp(hand, is_terminal, is_terminal):
        return 0

    return 3 if is_menzen else 2


def check_chinitsu(hand: List[int], is_menzen: bool = True) -> int:
    """清一色: 所有牌同花色。门清6翻, 副露5翻。"""
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
    if dominant >= 0:
        return 6 if is_menzen else 5
    return 0


def check_honitsu(hand: List[int], is_menzen: bool = True) -> int:
    """混一色: 同花色数牌+字牌。门清3翻, 副露2翻。"""
    num_suit = -1
    for t in range(NUM_TILES):
        if hand[t] > 0:
            s = suit(t)
            if s != SUIT_JIHAI:
                if num_suit == -1:
                    num_suit = s
                elif s != num_suit:
                    return 0
    if num_suit >= 0:
        return 3 if is_menzen else 2
    return 0


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


def check_sankantsu(hand: List[int], melds: List[Meld]) -> int:
    """
    三杠子 (San Kantsu / Three Quads)

    三组杠子(明杠/暗杠/加杠均可)。门清/副露均2翻。

    Args:
        hand: 手牌计数数组
        melds: 副露列表

    Returns:
        0 = 不满足
        2 = 三杠子
    """
    kan_count = 0

    # 统计副露中的杠
    for m in melds:
        if m.meld_type in ("kan", "ankan", "kakan"):
            kan_count += 1

    # 手牌中有4张同牌 = 可以宣告暗杠
    for count in hand:
        if count >= 4:
            kan_count += 1

    return 2 if kan_count == 3 else 0


def calculate_dora(hand: List[int], dora_indicators: List[int],
                   ura_indicators: Optional[List[int]] = None) -> int:
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
    chinitsu = check_chinitsu(hand, is_menzen)
    if chinitsu > 0:
        total += chinitsu
    else:
        total += check_honitsu(hand, is_menzen)

    # ── 顺子系 ──
    total += check_ittsuu(hand, is_menzen)
    total += check_sanshoku(hand, is_menzen)

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
    total += check_sanshokudoukou(hand)
    # 三杠子: 与二杯口同时出现时只算二杯口
    if rpk == 0:
        total += check_sankantsu(hand, state.melds)

    # ── 小三元 (2翻) ──
    from .daisangen import check_shousangen
    if check_shousangen(hand, state.melds):
        total += 2

    # ── 七对子 ──
    total += check_chiitoitsu(hand)

    # ── 基础役 ──
    total += check_honchantaiyaochuu(hand, is_menzen)
    total += check_junchantaiyaochuu(hand, is_menzen)
    total += check_honroutou(hand)
    total += check_tanyao(hand)

    # ── 役牌 ──
    total += check_yakuhai(hand, state.player_wind, state.round_wind)

    # ── 门清系 ──
    if is_menzen:
        total += 1  # 立直 (简化: 总是加)
        total += 1  # 门前清自摸和

    # ── 宝牌 ──
    total += calculate_dora(hand, state.dora_indicators,
                            state.ura_dora_indicators)

    return total


def has_any_yaku(state: GameState) -> bool:
    """
    检查14张和牌是否有任何役(≥1翻)。用于"最快和牌"模式。

    检查最基础的役种: 断幺九, 役牌, 平和, 一杯口, 七对子, 立直, 门前自摸。
    只要有任何一种即返回True。
    """
    hand = state.hand

    if not _has_valid_mentsu_decomp(hand):
        return False

    # 断幺九 (1翻)
    if check_tanyao(hand):
        return True

    # 混全带幺九 (门清2翻, 副露1翻)
    if check_honchantaiyaochuu(hand, state.is_menzen):
        return True

    # 纯全带幺九 (门清3翻, 副露2翻)
    if check_junchantaiyaochuu(hand, state.is_menzen):
        return True

    # 三色同刻 (2翻)
    if check_sanshokudoukou(hand):
        return True

    # 三杠子 (2翻)
    if check_sankantsu(hand, state.melds):
        return True

    # 混老头 (2翻)
    if check_honroutou(hand):
        return True

    # 役牌: 自风/场风/三元 刻子
    if check_yakuhai(hand, state.player_wind, state.round_wind) > 0:
        return True

    # 平和 (1翻, 需门清)
    if state.is_menzen:
        from ..decompose import has_valid_decomposition
        if has_valid_decomposition(hand):
            # 简化: 有4顺子拆分就可能有平和
            shuntsu = _count_sequences(hand)
            if len(shuntsu) == 4:
                return True

    # 一杯口 (1翻, 门清)
    if state.is_menzen and check_iipeikou(hand):
        return True

    # 七对子 (2翻, 门清)
    if state.is_menzen:
        from ..decompose import check_seven_pairs
        if check_seven_pairs(hand):
            return True

    # 门清自摸 (1翻): 搜索中所有和牌均为自摸, 门清时至少有门清自摸1翻。
    # 注意: 此假设仅适用于搜索上下文(自摸和). 若用于荣和判定需改为 False.
    if state.is_menzen:
        return True  # 门清自摸=1翻

    return False

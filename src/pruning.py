"""
剪枝与乐观估计模块

实现乐观估计函数 optimistic_bonus()，用于分支定界剪枝。
乐观估计: 在当前状态下，最多还能获得多少额外的役满倍数。
"""

from typing import List
from .tile import (
    NUM_TILES, suit, SUIT_JIHAI, SUIT_MANZU, SUIT_PINZU, SUIT_SOUZU,
    YAOCHU_TILES
)
from .state import GameState


def optimistic_bonus(state: GameState, remaining_draws: int) -> int:
    """
    计算乐观估计: 在剩余摸牌次数内最多还能达成多少役满。

    对每种役满分别估算"距离达成还差多少张关键牌"，
    如果缺牌数 ≤ remaining_draws，则乐观加上该役满的分数。

    Args:
        state: 当前牌局状态
        remaining_draws: 剩余可摸牌次数

    Returns:
        乐观估计额外能获得的役满倍数
    """
    bonus = 0
    hand = state.hand
    is_menzen = state.is_menzen

    # ── 国士无双 ──────────────────────────────
    if is_menzen:
        present_yaochu = sum(1 for t in YAOCHU_TILES if hand[t] >= 1)
        missing_yaochu = 13 - present_yaochu

        # 缺的幺九牌种类数 ≤ 剩余摸牌次数 → 可以凑齐
        if missing_yaochu <= remaining_draws:
            # 还需要凑一个对子 (至少一张已有幺九达到2张)
            has_pair = any(hand[t] >= 2 for t in YAOCHU_TILES)
            if has_pair or remaining_draws >= missing_yaochu + 1:
                bonus += 1
                # 十三面可能
                if present_yaochu + missing_yaochu >= 12 and remaining_draws >= 1:
                    bonus += 1

    # ── 四暗刻 ──────────────────────────────
    if is_menzen:
        pairs = sum(1 for t in range(NUM_TILES) if hand[t] >= 2)
        # 已有的刻子（含3张和4张）
        existing_kotsu = sum(1 for t in range(NUM_TILES) if hand[t] >= 3)
        # 已有对子可发展的
        needed_ankou = max(0, 4 - existing_kotsu - pairs)

        if needed_ankou <= remaining_draws:
            # 检查是否有可能凑足4个刻子
            # 每个对子需要1张牌变刻子
            can_form = True
            if needed_ankou > 0:
                # 对子数够不够
                available_pairs = sum(1 for t in range(NUM_TILES) if hand[t] == 2)
                can_form = available_pairs >= needed_ankou

            if can_form:
                bonus += 1
                # 四暗刻单骑
                if existing_kotsu + pairs >= 4 and remaining_draws >= 1:
                    bonus += 1

    # ── 大三元 ──────────────────────────────
    dragons = [31, 32, 33]  # 白发中
    sangen_needed = 0
    for d in dragons:
        have = hand[d]
        sangen_needed += max(0, 3 - have)

    # 每摸1张牌可以补1张三元牌
    if sangen_needed <= remaining_draws:
        bonus += 1

    # ── 九莲宝灯 ──────────────────────────────
    if is_menzen:
        # 检查手牌最多的花色
        suit_counts = [sum(hand[i*9:(i+1)*9]) for i in range(3)]
        max_suit_count = max(suit_counts)
        max_suit_idx = suit_counts.index(max_suit_count)

        # 纯一色才有可能九莲
        non_max_count = sum(hand[t] for t in range(NUM_TILES)
                            if suit(t) != max_suit_idx and suit(t) != SUIT_JIHAI)
        # 如果有非目标花色的数牌，需要替换
        if non_max_count <= remaining_draws:
            # 简化: 如果同花色牌数 + 剩余摸牌 ≥ 14，乐观加上
            if max_suit_count + remaining_draws >= 14:
                bonus += 1

    return bonus


# ── 互斥表 ──────────────────────────────────────────

# 某些役满之间不能同时存在
MUTUALLY_EXCLUSIVE = {
    ('kokushi', 'chuuren'): True,   # 国士含字+19，九莲全同花色
    ('kokushi', 'tsuuiisou'): False,  # 国士含19数牌，字一色全字
    ('tsuuiisou', 'chinitsu'): True,  # 字 vs 数
}


def are_yaku_compatible(yaku_a: str, yaku_b: str) -> bool:
    """检查两种役满是否可以共存"""
    return not MUTUALLY_EXCLUSIVE.get(
        (yaku_a, yaku_b),
        MUTUALLY_EXCLUSIVE.get((yaku_b, yaku_a), False)
    )

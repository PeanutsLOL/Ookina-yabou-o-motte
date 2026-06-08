"""
剪枝与乐观估计模块

实现乐观估计函数 optimistic_bonus()，用于分支定界剪枝。
乐观估计: 在当前状态下，最多还能获得多少额外的役满倍数。
"""

from typing import List
from .tile import (
    NUM_TILES, suit, SUIT_JIHAI, YAOCHU_TILES
)
from .state import GameState


def optimistic_bonus(state: GameState, remaining_draws: int) -> int:
    """
    计算乐观估计: 从当前状态出发最多能达成多少役满倍数。

    每种役满独立估算"距离达成还差多少张关键牌"，
    缺牌数 ≤ remaining_draws 则乐观加上该役满。

    注意: 返回的是"从当前状态能达成的总倍数上限"，不是增量。
    """
    bonus = 0
    hand = state.hand
    is_menzen = state.is_menzen

    # ── 国士无双 ──────────────────────────────
    if is_menzen:
        present_yaochu = sum(1 for t in YAOCHU_TILES if hand[t] >= 1)
        missing_yaochu = 13 - present_yaochu
        if missing_yaochu <= remaining_draws:
            has_pair = any(hand[t] >= 2 for t in YAOCHU_TILES)
            if has_pair or remaining_draws >= missing_yaochu + 1:
                bonus += 1
                if present_yaochu + missing_yaochu >= 12 and remaining_draws >= 1:
                    bonus += 1

    # ── 四暗刻 ──────────────────────────────
    if is_menzen:
        pairs = sum(1 for t in range(NUM_TILES) if hand[t] >= 2)
        existing_kotsu = sum(1 for t in range(NUM_TILES) if hand[t] >= 3)
        needed_ankou = max(0, 4 - existing_kotsu - min(pairs, 4 - existing_kotsu))
        # 简化: 已有对子+刻子≥4且有剩余摸牌
        if existing_kotsu + pairs >= 4 and remaining_draws >= 1:
            bonus += 1
            # 四暗刻单骑: 已有4刻子+1单张
            if existing_kotsu >= 4:
                bonus += 1
            elif existing_kotsu + pairs >= 4 and pairs >= 1:
                bonus += 1  # 乐观估计单骑
        elif existing_kotsu + pairs + remaining_draws >= 4:
            bonus += 1

    # ── 大三元 ──────────────────────────────
    dragons = [31, 32, 33]
    sangen_needed = sum(max(0, 3 - hand[d]) for d in dragons)
    if sangen_needed <= remaining_draws:
        bonus += 1

    # ── 大四喜 ──────────────────────────────
    winds = [27, 28, 29, 30]
    wind_needed = sum(max(0, 3 - hand[w]) for w in winds)
    if wind_needed <= remaining_draws:
        bonus += 2  # 大四喜=2倍

    # ── 小四喜 ──────────────────────────────
    wind_kotsu = sum(1 for w in winds if hand[w] >= 3)
    wind_pair = sum(1 for w in winds if hand[w] == 2)
    if wind_kotsu + wind_pair >= 3 and remaining_draws >= (3 - wind_kotsu):
        bonus += 1

    # ── 字一色 ──────────────────────────────
    non_honor = sum(hand[t] for t in range(27))
    if non_honor <= remaining_draws:
        bonus += 1

    # ── 清老头 ──────────────────────────────
    non_terminal = sum(hand[t] for t in range(NUM_TILES)
                       if t not in (0, 8, 9, 17, 18, 26))
    if non_terminal <= remaining_draws:
        bonus += 1

    # ── 四杠子 ──────────────────────────────
    kan_in_melds = sum(1 for m in state.melds
                       if m.meld_type in ("kan", "ankan", "kakan"))
    kan_in_hand = sum(1 for t in range(NUM_TILES) if hand[t] >= 4)
    near_kan = sum(1 for t in range(NUM_TILES) if hand[t] == 3)
    potential_kan = kan_in_melds + kan_in_hand + min(near_kan, remaining_draws)
    if potential_kan >= 4:
        bonus += 1

    # ── 绿一色 ──────────────────────────────
    from .yaku.ryuuiisou import GREEN_TILES
    non_green = sum(hand[t] for t in range(NUM_TILES) if t not in GREEN_TILES)
    if non_green <= remaining_draws:
        bonus += 1

    # ── 九莲宝灯 ──────────────────────────────
    if is_menzen:
        suit_counts = [sum(hand[i*9:(i+1)*9]) for i in range(3)]
        max_suit_count = max(suit_counts)
        max_suit_idx = suit_counts.index(max_suit_count)
        non_max = sum(hand[t] for t in range(NUM_TILES)
                      if suit(t) != max_suit_idx and suit(t) != SUIT_JIHAI)
        if non_max <= remaining_draws and max_suit_count + remaining_draws >= 14:
            bonus += 1

    return bonus

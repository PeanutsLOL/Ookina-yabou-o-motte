"""
核心搜索算法模块

实现 DFS + 分支定界搜索，寻找理论最大番数。

搜索模型（正确的一巡流程）:
  1. 手牌 13 张（标准状态）
  2. 摸 1 张牌 → 14 张
  3. 检查是否可以和牌 → 记录番数
  4. 若未达深度上限: 弃 1 张牌 → 回到 13 张
  5. 递归进入下一巡

关键修正:
  - 14 张手牌只在"摸牌后瞬间"出现，是和牌检查点
  - 和牌检查后不应 return，而是继续尝试弃牌 → 递归
  - 初始状态应为 13 张（标准），若输入 14 张则先检查和牌再弃牌
"""

from typing import List, Tuple, Optional
import time

from .tile import NUM_TILES, tile_name
from .state import GameState, Meld, SearchNode, SearchResult
from .decompose import can_agari, get_waits
from .yaku import (
    check_kokushi, check_suuankou, check_daisangen, check_chuuren,
    check_daisuushi, check_shousuushi, check_tsuuiisou,
    check_ryuuiisou, check_chinroutou, check_suukantsu,
)
from .pruning import optimistic_bonus


def calculate_score(state: GameState) -> int:
    """
    计算当前状态下的番数（役满倍数）。

    仅在手牌14张（和牌形态）时调用。
    役满之间可累加（复合役满），按正确的互斥规则处理。

    理论最大: 字一色+四杠子+四暗刻单骑+大四喜 = 6倍役满
    役满参考: https://wiki.queji.com/mediawiki/index.php/%E5%BD%B9%E7%A8%AE%E8%A1%A8
    """
    hand = state.hand
    melds = state.melds

    if state.hand_size != 14:
        return 0

    # ── 判定所有役满 ─────────────────────────────
    kokushi = check_kokushi(hand)
    suuankou = check_suuankou(hand, melds)
    daisangen = check_daisangen(hand)       # TODO: 也检查 melds 中的三元牌
    chuuren = check_chuuren(hand)
    daisuushi = check_daisuushi(hand)        # TODO: 也检查 melds 中的风牌
    shousuushi = check_shousuushi(hand)
    tsuuiisou = check_tsuuiisou(hand)
    ryuuiisou = check_ryuuiisou(hand)
    chinroutou = check_chinroutou(hand)
    suukantsu = check_suukantsu(hand, melds)

    # ── 累加（处理互斥）─────────────────────────
    #
    # 核心约束: 和牌 = 4面子 + 1雀头 (或七对子/国士特殊形)
    # 每个面子槽只能被一个役满占用。
    #
    # 面子槽占用:
    #   大四喜=4个风刻(4槽)  小四喜=3风刻+1风对(3槽+雀头)
    #   大三元=3个三元刻(3槽) 四暗刻=4暗刻(4槽,门清)
    #   字一色=全字牌(描述牌种) 绿一色/清老头=特定牌种(描述牌种)
    #   四杠子=4杠子(4槽)     国士/九莲=特殊形(独立结构)
    #
    # 互斥规则:
    #   国士无双(特殊结构) ↔ 需要面子结构的役满 → 不可能共存
    #   九莲宝灯(特殊结构) ↔ 需要面子结构的役满 → 不可能共存
    #   大四喜(4槽) ↔ 大三元(3槽) → 7槽 > 4 → 不可能共存
    #   小四喜(3槽+雀头) ↔ 大三元(3槽) → 6槽 > 4 → 不可能共存
    #   大四喜(4槽) ↔ 小四喜(3槽+雀头) → 大四喜优先
    #   字一色(牌种) 可与大四喜/大三元/四暗刻共存
    #   四杠子(杠状态) 可与任何役满共存

    # 1. 国士无双 / 九莲宝灯: 特殊结构, 互斥对方也互斥其他面子系役满
    if kokushi > 0 or chuuren > 0:
        # 国士和九莲彼此互斥，且不能与面子系役满共存
        return max(kokushi, chuuren)

    # 2. 面子系役满: 从0开始累加
    score = 0

    # 大四喜(4风刻) vs 大三元(3三元刻) → 7刻 > 4面子槽 → 不可能共存
    if daisuushi > 0 and daisangen > 0:
        score += max(daisuushi, daisangen)
    else:
        # 大四喜 ↔ 小四喜: 大四喜优先
        if daisuushi > 0:
            score += daisuushi
        else:
            score += shousuushi
        score += daisangen

    # 3. 四暗刻: 门清限定, 可与其他役满共存
    score += suuankou

    # 4. 牌种系役满: 字一色/绿一色/清老头（三者check函数互斥）
    score += tsuuiisou
    score += ryuuiisou
    score += chinroutou

    # 5. 四杠子: 杠状态, 可与任何役满共存
    score += suukantsu

    return score


def _useful_draws(state: GameState, waits: List[int]) -> List[int]:
    """
    返回"对役满有贡献"的摸牌候选，而非全部34种牌。

    策略:
      1. 若已听牌: 只摸被听牌
      2. 否则: 分析当前手牌接近哪些役满，只摸关键牌
         - 清老头: 1m,9m,1p,9p,1s,9s
         - 国士无双: 所有幺九牌
         - 字一色: 字牌
         - 大三元/大四喜/小四喜: 三元牌/风牌
         - 九莲宝灯: 手牌最多的花色
         - 绿一色: 绿牌(23468s+发)
         - 四暗刻: 手牌中已有的对子/刻子
      3. 兜底: 如果没有任何役满潜力, 返回空列表
    """
    from .tile import is_yaochu, YAOCHU_TILES, suit, SUIT_JIHAI
    from .yaku.ryuuiisou import GREEN_TILES

    hand = state.hand

    # 已听牌 → 只摸被听牌
    if waits:
        return [t for t in waits if state.rest[t] > 0]

    useful: set[int] = set()

    # ── 分析役满潜力 ──────────────────────
    # 清老头潜力: 手牌中老头牌占比
    terminal_count = sum(hand[t] for t in (0, 8, 9, 17, 18, 26))
    non_terminal_count = state.hand_size - terminal_count
    # 只算数牌中的非老头 (不含字牌, 字牌不计入清老头)
    non_terminal_numbers = sum(
        hand[t] for t in range(27)
        if t not in (0, 8, 9, 17, 18, 26)
    )
    if non_terminal_numbers <= 3 and terminal_count >= 8:
        # 接近清老头, 只摸老头牌
        useful.update({0, 8, 9, 17, 18, 26})

    # 国士无双潜力: 幺九牌种类数
    present_yaochu = sum(1 for t in YAOCHU_TILES if hand[t] >= 1)
    if present_yaochu >= 8:  # 至少8种幺九才值得追
        useful.update(YAOCHU_TILES)

    # 字一色 / 风牌/三元牌 潜力
    honor_count = sum(hand[t] for t in range(27, 34))
    if honor_count >= 8:
        useful.update(range(27, 34))

    # 大四喜/小四喜/大三元: 风牌/三元牌 ≥ 6张
    wind_count = sum(hand[t] for t in range(27, 31))
    dragon_count = sum(hand[t] for t in range(31, 34))
    if wind_count >= 6:
        useful.update(range(27, 31))
    if dragon_count >= 6:
        useful.update(range(31, 34))

    # 九莲宝灯潜力: 单花色 ≥ 10张
    for base in (0, 9, 18):
        suit_count = sum(hand[base:base+9])
        if suit_count >= 10:
            useful.update(range(base, base + 9))

    # 绿一色潜力: 绿牌 ≥ 8张
    green_count = sum(hand[t] for t in GREEN_TILES)
    if green_count >= 8:
        useful.update(GREEN_TILES)

    # 四暗刻潜力: 手牌中已有的对子/刻子的牌
    for t in range(NUM_TILES):
        if hand[t] >= 2:
            useful.add(t)

    # ── 如果没有任何方向, 返回空 ──
    if not useful:
        return []

    # 过滤掉已用完的牌
    result = [t for t in useful if state.rest[t] > 0 and state.hand[t] < 4]

    # 按剩余数量和幺九优先级排序
    def sort_key(t: int) -> int:
        return -(state.rest[t] * 10 + (5 if is_yaochu(t) else 0))

    result.sort(key=sort_key)
    return result


def _discard_candidates(state: GameState, waits: Optional[List[int]] = None) -> List[int]:
    """
    弃牌候选排序: 优先弃孤立牌/非听牌。

    策略:
      1. 如果已听牌: 只弃非听牌（安全弃牌）
      2. 如果未听牌: 弃孤立牌（只有1张且不与相邻牌构成搭子）
      3. 限制最多 8 个弃牌候选，控制分支因子
    """
    from .tile import suit, SUIT_JIHAI

    if waits is None:
        waits = []

    hand = state.hand
    candidates = []
    singles = []

    for t in range(NUM_TILES):
        if hand[t] <= 0:
            continue

        # 已听牌时: 只弃非听牌
        if waits:
            if t not in waits:
                candidates.append(t)
            continue

        # 未听牌时: 评估是否为孤立牌
        if hand[t] == 1:
            s = suit(t)
            n = t % 9
            is_isolated = True

            # 检查是否有相邻牌构成搭子
            if s != SUIT_JIHAI:
                # 检查 ±1 和 ±2 是否有牌
                if n >= 1 and hand[t - 1] >= 1:
                    is_isolated = False
                if n <= 7 and hand[t + 1] >= 1:
                    is_isolated = False
                if n >= 2 and hand[t - 2] >= 1:
                    is_isolated = False  # 坎张搭子
            else:
                # 字牌: 如果只有1张且不是对子 → 孤立
                if hand[t] >= 2:
                    is_isolated = False

            if is_isolated:
                singles.append(t)
            else:
                candidates.append(t)
        else:
            candidates.append(t)

    # 孤立牌优先丢弃
    candidates = singles + candidates

    # 限制候选数量
    if len(candidates) > 8:
        candidates = candidates[:8]

    if not candidates:
        # 兜底: 所有牌都可以弃
        candidates = [t for t in range(NUM_TILES) if hand[t] > 0][:8]

    return candidates


def search_max_score(
    initial_state: GameState,
    max_depth: int = 5,
    enable_pruning: bool = True,
) -> SearchResult:
    """
    DFS + 分支定界搜索，寻找理论最大番数。

    正确的一巡流程 (13 → 14 → 13):
      摸牌(13→14) → 和牌检查 → 弃牌(14→13) → 递归

    Args:
        initial_state: 初始牌局状态
                       手牌应为 13 张（标准状态）
                       若为 14 张则首先检查和牌再弃牌继续
        max_depth: 最大搜索深度（最多摸几张牌），默认5
        enable_pruning: 是否启用剪枝

    Returns:
        SearchResult 包含最大番数、最优路径、节点统计
    """
    best_score = 0
    best_path: List[Tuple[str, int]] = []
    nodes_searched = 0
    nodes_pruned = 0
    visited: dict = {}  # (hand_tuple, depth) → avoid re-search

    start_time = time.perf_counter()

    def search(state: GameState, depth: int,
               path: List[Tuple[str, int]]):
        nonlocal best_score, best_path, nodes_searched, nodes_pruned

        nodes_searched += 1

        if depth >= max_depth:
            return

        # ── 状态缓存: 同样手牌+深度只搜一次 ──
        hand_key = tuple(state.hand)
        cache_key = (hand_key, depth)
        if cache_key in visited:
            nodes_pruned += 1
            return
        visited[cache_key] = True

        # ── 剪枝 (修正: 比较乐观上限 vs 当前最优) ──
        remaining_draws = max_depth - depth
        if enable_pruning and best_score > 0:
            max_bonus = optimistic_bonus(state, remaining_draws)
            if max_bonus <= best_score:
                nodes_pruned += 1
                return

        waits_before = get_waits(state.hand)
        draw_order = _useful_draws(state, waits_before)

        for draw_tile in draw_order:
            if state.rest[draw_tile] <= 0 or state.hand[draw_tile] >= 4:
                continue
            if waits_before and draw_tile not in waits_before:
                continue

            # ——— 摸牌 ———
            state.hand[draw_tile] += 1
            state.rest[draw_tile] -= 1
            path.append(('draw', draw_tile))

            # ——— 和牌检查 ———
            if can_agari(state.hand):
                s = calculate_score(state)
                if s > best_score:
                    best_score = s
                    best_path = path.copy()
                    if best_score >= 6:  # 理论最大
                        path.pop()
                        state.rest[draw_tile] += 1
                        state.hand[draw_tile] -= 1
                        return

            # ——— 弃牌 → 递归 ———
            if depth + 1 < max_depth:
                if best_score > 0:
                    if optimistic_bonus(state, remaining_draws - 1) <= best_score:
                        path.pop()
                        state.rest[draw_tile] += 1
                        state.hand[draw_tile] -= 1
                        continue

                discards = _discard_candidates(state, get_waits(state.hand))[:4]

                for discard_tile in discards:
                    if state.hand[discard_tile] <= 0:
                        continue

                    # 避免无意义循环: 刚摸的牌立刻弃 (且原本只有1张)
                    if discard_tile == draw_tile and hand_key[discard_tile] <= 1:
                        continue

                    if best_score > 0 and enable_pruning:
                        state.hand[discard_tile] -= 1
                        pot = optimistic_bonus(state, max_depth - depth - 1)
                        state.hand[discard_tile] += 1
                        if pot <= 0:
                            continue

                    state.hand[discard_tile] -= 1
                    state.rest[discard_tile] += 1
                    path.append(('discard', discard_tile))

                    search(state, depth + 1, path)

                    path.pop()
                    state.rest[discard_tile] -= 1
                    state.hand[discard_tile] += 1

            path.pop()
            state.rest[draw_tile] += 1
            state.hand[draw_tile] -= 1

    # ── 入口处理 ─────────────────────────────────

    # 确保初始状态为 13 张
    if initial_state.hand_size == 14:
        # 用户传入 14 张（如在摸牌后）→ 先检查和牌
        if can_agari(initial_state.hand):
            score = calculate_score(initial_state)
            if score > best_score:
                best_score = score
                best_path = [('_initial', -1)]  # 标记初始即和

        # 弃 1 张 → 回到 13 张, 然后开始搜索
        candidates = _discard_candidates(initial_state)
        best_initial_score = best_score

        for discard_tile in candidates:
            if initial_state.hand[discard_tile] <= 0:
                continue
            state = initial_state.copy()
            state.hand[discard_tile] -= 1
            state.rest[discard_tile] += 1
            search(state, 0, [('discard', discard_tile)])

        # 恢复可能的最佳路径
        if best_score > best_initial_score:
            pass  # 搜索过程中已更新
        elif best_initial_score > 0:
            best_score = best_initial_score

    elif initial_state.hand_size == 13:
        # 标准 13 张 → 直接开始搜索
        search(initial_state, 0, [])

    else:
        raise ValueError(
            f"手牌数量不正确: {initial_state.hand_size} "
            f"(期望 13 或 14)"
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return SearchResult(
        max_score=best_score,
        best_path=best_path,
        nodes_searched=nodes_searched,
        nodes_pruned=nodes_pruned,
        elapsed_ms=elapsed_ms,
    )


def search_no_pruning(initial_state: GameState,
                       max_depth: int = 5) -> int:
    """
    无剪枝搜索（用于对比节点数）。
    """
    nodes = 0

    def search(state: GameState, depth: int):
        nonlocal nodes
        nodes += 1

        if depth >= max_depth:
            return

        waits_before = get_waits(state.hand)
        draw_order = _useful_draws(state, waits_before)

        for draw_tile in draw_order:
            if state.rest[draw_tile] <= 0:
                continue
            if state.hand[draw_tile] >= 4:
                continue

            state.hand[draw_tile] += 1
            state.rest[draw_tile] -= 1

            if depth + 1 < max_depth:
                # 弃牌（无剪枝: 只尝试前3个弃牌候选以控制规模）
                discards = _discard_candidates(state)[:3]
                for discard_tile in discards:
                    if state.hand[discard_tile] <= 0:
                        continue
                    state.hand[discard_tile] -= 1
                    state.rest[discard_tile] += 1
                    search(state, depth + 1)
                    state.rest[discard_tile] -= 1
                    state.hand[discard_tile] += 1

            state.rest[draw_tile] += 1
            state.hand[draw_tile] -= 1

    # 入口
    if initial_state.hand_size == 14:
        for discard_tile in _discard_candidates(initial_state)[:3]:
            if initial_state.hand[discard_tile] <= 0:
                continue
            state = initial_state.copy()
            state.hand[discard_tile] -= 1
            state.rest[discard_tile] += 1
            search(state, 0)
    elif initial_state.hand_size == 13:
        search(initial_state, 0)

    return nodes

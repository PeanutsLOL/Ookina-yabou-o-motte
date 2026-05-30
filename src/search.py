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
from .yaku import check_kokushi, check_suuankou, check_daisangen, check_chuuren
from .pruning import optimistic_bonus


def calculate_score(state: GameState) -> int:
    """
    计算当前状态下的番数（役满倍数）。

    仅在手牌14张（和牌形态）时调用。
    役满累加规则:
      - 每种役满独立判定，结果累加
      - 国士无双 + 四暗刻 可以共存
      - 国士无双 + 九莲宝灯 互斥
    """
    hand = state.hand
    melds = state.melds

    if state.hand_size != 14:
        return 0

    yakuman_score = 0

    # P0 役满判定
    kokushi_result = check_kokushi(hand)
    suuankou_result = check_suuankou(hand, melds)
    daisangen_result = check_daisangen(hand)
    chuuren_result = check_chuuren(hand)

    # 累加（互斥处理）
    if kokushi_result > 0 and chuuren_result > 0:
        yakuman_score += max(kokushi_result, chuuren_result)
    else:
        yakuman_score += kokushi_result
        yakuman_score += chuuren_result

    yakuman_score += suuankou_result
    yakuman_score += daisangen_result

    return yakuman_score


def _draw_priority(waits: List[int], rest: List[int]) -> List[int]:
    """
    摸牌优先级: 听牌 > 剩余数量多 > 幺九牌（国士候选）
    """
    from .tile import is_yaochu

    def sort_key(tile: int) -> int:
        score = 0
        if tile in waits:
            score += 10000
        score += rest[tile] * 10
        if is_yaochu(tile):
            score += 5
        return -score

    candidates = [t for t in range(NUM_TILES) if rest[t] > 0]
    candidates.sort(key=sort_key)
    return candidates


def _discard_candidates(state: GameState, waits: List[int] = None) -> List[int]:
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

    start_time = time.perf_counter()

    # ── 内部递归函数 ───────────────────────────────
    # state 约定: 传入时 hand_size = 13（标准状态）
    # 函数内部: draw → 14 → check agari → discard → 13 → recurse

    def search(state: GameState, depth: int,
               path: List[Tuple[str, int]]):
        nonlocal best_score, best_path, nodes_searched, nodes_pruned

        nodes_searched += 1

        # ── 深度限制 ──
        if depth >= max_depth:
            return

        # ── 剪枝检查 ──
        remaining_draws = max_depth - depth
        if enable_pruning:
            upper_bound = best_score + optimistic_bonus(state, remaining_draws)
            if upper_bound <= best_score and best_score > 0:
                nodes_pruned += 1
                return

        # ── 听牌列表（摸牌前计算，用于优先摸听牌）──
        waits_before_draw = get_waits(state.hand)  # 13张时的听牌

        # ── 摸牌顺序 ──
        draw_order = _draw_priority(waits_before_draw, state.rest)

        for draw_tile in draw_order:
            if state.rest[draw_tile] <= 0:
                continue
            if state.hand[draw_tile] >= 4:
                continue

            # 如果已听牌且非听牌 → 跳过（除非剩余摸牌>1）
            if waits_before_draw and draw_tile not in waits_before_draw:
                if remaining_draws <= 1:
                    continue  # 只有1次摸牌机会，摸非听牌无意义

            # ——— 摸牌 ———
            state.hand[draw_tile] += 1   # 13 → 14
            state.rest[draw_tile] -= 1
            path.append(('draw', draw_tile))

            # ——— 和牌检查 ———
            if can_agari(state.hand):
                current_score = calculate_score(state)
                if current_score > best_score:
                    best_score = current_score
                    best_path = path.copy()

            # ——— 弃牌 → 递归（继续搜索下一巡）———
            if depth + 1 < max_depth:
                # 找到和牌后: 仅当乐观估计能超过当前最优时才继续
                if best_score > 0:
                    opt = optimistic_bonus(state, remaining_draws - 1)
                    if best_score + opt <= best_score:
                        # 无法改善，跳过弃牌循环
                        path.pop()
                        state.rest[draw_tile] += 1
                        state.hand[draw_tile] -= 1
                        continue

                # 14张时的听牌列表（用于确定安全弃牌）
                waits_after_draw = get_waits(state.hand)
                discards = _discard_candidates(state, waits_after_draw)

                for discard_tile in discards:
                    if state.hand[discard_tile] <= 0:
                        continue

                    # 快速评估: 弃牌后的状态是否有潜力
                    if best_score > 0 and enable_pruning:
                        state.hand[discard_tile] -= 1
                        opt_after = optimistic_bonus(state, max_depth - depth - 1)
                        state.hand[discard_tile] += 1
                        if opt_after <= 0:
                            continue  # 弃这张牌后无役满潜力，跳过

                    # 弃牌
                    state.hand[discard_tile] -= 1  # 14 → 13
                    state.rest[discard_tile] += 1
                    path.append(('discard', discard_tile))

                    # 递归进入下一巡
                    search(state, depth + 1, path)

                    # 回溯弃牌
                    path.pop()
                    state.rest[discard_tile] -= 1
                    state.hand[discard_tile] += 1

            # ——— 回溯摸牌 ———
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
        draw_order = _draw_priority(waits_before, state.rest)

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

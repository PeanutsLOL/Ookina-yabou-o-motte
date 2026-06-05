"""
牌局模拟模块

模拟对手摸牌和弃牌过程，生成牌河数据（牌河），用于为搜索算法提供
逼真的已见牌信息。同时自动补全宝牌/里宝牌指示牌。

弃牌策略: 基于向听数最小化（牌效最优）。
"""

import random
from typing import List, Optional, Tuple

from .tile import (
    NUM_TILES, suit, SUIT_JIHAI, is_honor,
    dora_indicator_to_dora, tile_name,
)
from .decompose import count_shanten


# ── 辅助函数 ──────────────────────────────────────────

def _is_isolated(hand: List[int], tile: int) -> bool:
    """
    判断一张牌是否"孤立"（在 ±2 范围内无相邻同花色牌）。

    字牌 count=1 即孤立，count≥2 为对子不孤立。
    """
    if hand[tile] > 1:
        return False
    s = suit(tile)
    if s == SUIT_JIHAI:
        return hand[tile] == 1
    n = tile % 9
    for dn in (-2, -1, 1, 2):
        adj = tile + dn
        if 0 <= adj < NUM_TILES and suit(adj) == s and hand[adj] > 0:
            return False
    return True


def _is_dora_adjacent(tile: int, dora_tiles: set) -> bool:
    """
    判断 tile 是否与任何宝牌相邻（同花色 ±1）。

    用于弃牌平分时：与宝牌相邻的牌更有价值，不应该优先弃。
    """
    if not dora_tiles:
        return False
    s = suit(tile)
    if s == SUIT_JIHAI:
        return False
    n = tile % 9
    for dn in (-1, 1):
        adj = tile + dn
        if 0 <= adj < NUM_TILES and suit(adj) == s and adj in dora_tiles:
            return True
    return False


# ── 弃牌决策 ──────────────────────────────────────────

def best_discard(
    hand_14: List[int],
    dora_indicators: Optional[List[int]] = None,
) -> int:
    """
    基于向听数最小化选择最优弃牌。

    对 14 张手牌中每种可能的弃牌，计算弃后 13 张的 shanten 数。
    选择 shanten 最低者。平分时按以下优先级：
      1. 优先弃孤立牌
      2. 优先弃非字牌（数牌能组顺子，保留价值更高）
      3. 优先弃非宝牌邻接牌（宝牌附近有潜在价值）

    Args:
        hand_14: 14 张手牌计数数组（sum=14）
        dora_indicators: 宝牌指示牌列表，用于计算宝牌邻接

    Returns:
        最优弃牌编码 (0~33)
    """
    if dora_indicators is None:
        dora_indicators = []

    # 计算所有宝牌（从指示牌推导）
    dora_tiles: set[int] = set()
    for ind in dora_indicators:
        dora_tiles.add(dora_indicator_to_dora(ind))

    # 评估每种可能的弃牌
    candidates: List[tuple] = []  # (shanten, tiebreak, tile)

    for t in range(NUM_TILES):
        if hand_14[t] == 0:
            continue

        # 不移除已构成刻子的牌（count≥3 的部分）
        # 但允许移除 count=3 中多出的一张（如 count=4 → 移除1张后仍有3张）
        # 这里简化：不移除构成刻子的核心3张
        # 实际上是允许的, shanten 计算会自然惩罚

        hand_14[t] -= 1
        shanten = count_shanten(hand_14)
        hand_14[t] += 1

        # 计算 tie-break 分数（越低越优先弃）
        isolated_score = 0 if _is_isolated(hand_14, t) else 10
        honor_score = 5 if is_honor(t) else 0
        dora_adj_score = 3 if _is_dora_adjacent(t, dora_tiles) else 0
        tiebreak = isolated_score + honor_score + dora_adj_score

        candidates.append((shanten, tiebreak, t))

    # 排序：先按 shanten（越低越好），再按 tiebreak（越低越好）
    candidates.sort(key=lambda x: (x[0], x[1]))

    return candidates[0][2]


# ── 发牌 ──────────────────────────────────────────────

def deal_opponent_hands(
    rest: List[int],
    num_opponents: int = 3,
    rng: Optional[random.Random] = None,
) -> List[List[int]]:
    """
    从牌山剩余牌中随机给对手发 13 张。

    原地修改 rest（扣除已发出的牌）。

    Args:
        rest: 牌山剩余计数数组（会被原地修改）
        num_opponents: 对手数量（默认3）
        rng: 随机数生成器实例

    Returns:
        对手手牌列表，每个为长度34的计数数组（sum=13）

    Raises:
        ValueError: 牌山剩余牌数不足以发牌
    """
    if rng is None:
        rng = random.Random()

    # 构建 flat pool
    pool = []
    for t in range(NUM_TILES):
        pool.extend([t] * rest[t])

    needed = num_opponents * 13
    if len(pool) < needed:
        raise ValueError(
            f"牌山剩余牌数不足，无法发牌给 {num_opponents} 家对手 "
            f"(需要 {needed} 张，实际 {len(pool)} 张)"
        )

    rng.shuffle(pool)

    hands = []
    for i in range(num_opponents):
        hand = [0] * NUM_TILES
        start = i * 13
        for t in pool[start:start + 13]:
            hand[t] += 1
            rest[t] -= 1
        hands.append(hand)

    return hands


# ── 宝牌/里宝牌生成 ──────────────────────────────────

def _generate_dora_indicators(
    user_hand: List[int],
    opponent_hands: List[List[int]],
    existing_dora: List[int],
    rng: random.Random,
) -> Tuple[List[int], List[int]]:
    """
    随机生成宝牌指示牌和里宝牌指示牌。

    规则：
    - 从 existing_dora 开始（用户已输入的宝牌）
    - 若不足 5 张，从可用牌中随机补足至 5 张
    - 里宝牌同样随机选取 5 张
    - 必须与所有手牌和已有宝牌无冲突（每种牌最多4张）

    Args:
        user_hand: 用户手牌计数
        opponent_hands: 对手手牌列表
        existing_dora: 用户已输入的宝牌指示牌
        rng: 随机数生成器

    Returns:
        (full_dora_indicators, ura_dora_indicators)
    """
    # 统计已用牌数
    used = [0] * NUM_TILES
    for t in range(NUM_TILES):
        used[t] += user_hand[t]
    for hand in opponent_hands:
        for t in range(NUM_TILES):
            used[t] += hand[t]
    for t in existing_dora:
        used[t] += 1

    # ── 宝牌指示牌 ──
    dora = list(existing_dora)  # 保留用户输入的

    if len(dora) < 5:
        # 构建可用牌池
        dora_pool = []
        for t in range(NUM_TILES):
            remaining = 4 - used[t]
            dora_pool.extend([t] * remaining)
        rng.shuffle(dora_pool)

        needed = 5 - len(dora)
        if len(dora_pool) < needed:
            raise ValueError(
                f"牌池不足以补全宝牌指示牌 "
                f"(需 {needed} 张，实际可用 {len(dora_pool)} 张)"
            )

        for t in dora_pool[:needed]:
            dora.append(t)
            used[t] += 1

    # ── 里宝牌指示牌 ──
    ura_pool = []
    for t in range(NUM_TILES):
        remaining = 4 - used[t]
        ura_pool.extend([t] * remaining)
    rng.shuffle(ura_pool)

    if len(ura_pool) < 5:
        raise ValueError(
            f"牌池不足以生成里宝牌指示牌 "
            f"(需 5 张，实际可用 {len(ura_pool)} 张)"
        )

    ura_dora = ura_pool[:5]
    for t in ura_dora:
        used[t] += 1

    return dora, ura_dora


# ── 主模拟入口 ────────────────────────────────────────

def simulate_game(
    user_hand: List[int],
    rest: List[int],
    max_turns: int,
    dora_indicators: Optional[List[int]] = None,
    seed: Optional[int] = None,
) -> Tuple[List[List[int]], List[int], List[int], List[int]]:
    """
    模拟对手摸牌和弃牌过程，生成牌河和宝牌数据。

    工作流程:
      1. 从牌山随机发牌给 3 家对手（各 13 张）
      2. 随机生成宝牌/里宝牌指示牌（不与任何手牌冲突）
      3. 模拟 max_turns 巡的摸打过程：
         每巡每家 → 摸 1 张（随机）→ 弃 1 张（牌效最优）
      4. 记录所有弃牌到各家牌河

    Args:
        user_hand: 用户手牌计数数组（sum=13，不被修改）
        rest: 牌山剩余计数数组（会被原地修改：发牌 + 摸牌 + 宝牌扣除）
        max_turns: 最大模拟巡数（每巡 3 家各摸打一次）
        dora_indicators: 用户已输入的宝牌指示牌（可为空或 None）
        seed: 随机种子（用于可复现性）

    Returns:
        Tuple of:
          - rivers: 3 个对手各自的牌河（List[List[int]]，每个 length=34）
          - combined: 合并后的总牌河（List[int]，length=34）
          - full_dora: 完整宝牌指示牌列表（5 张）
          - ura_dora: 里宝牌指示牌列表（5 张）
    """
    rng = random.Random(seed)
    if dora_indicators is None:
        dora_indicators = []

    # ── Step 1: 发牌 ──
    opponent_hands = deal_opponent_hands(rest, num_opponents=3, rng=rng)

    # ── Step 2: 生成宝牌/里宝牌 ──
    full_dora, ura_dora = _generate_dora_indicators(
        user_hand, opponent_hands,
        existing_dora=list(dora_indicators),
        rng=rng,
    )

    # ── Step 3: 从牌山扣除王牌区（宝牌+里宝牌）──
    for t in full_dora:
        if rest[t] > 0:
            rest[t] -= 1
    for t in ura_dora:
        if rest[t] > 0:
            rest[t] -= 1

    # ── Step 4: 模拟摸打 ──
    rivers = [[0] * NUM_TILES for _ in range(3)]

    for turn in range(max_turns):
        for opp_idx in range(3):
            # 构建可用牌池
            deck = []
            for t in range(NUM_TILES):
                deck.extend([t] * rest[t])

            if not deck:
                # 牌山耗尽
                break

            # 摸牌
            draw = rng.choice(deck)
            rest[draw] -= 1
            opponent_hands[opp_idx][draw] += 1  # 现在是 14 张

            # 弃牌（牌效最优）
            discard = best_discard(opponent_hands[opp_idx], full_dora)
            opponent_hands[opp_idx][discard] -= 1  # 回到 13 张
            rivers[opp_idx][discard] += 1
            # 弃牌不进牌山 — 牌河中的牌不再可摸

        # 检查是否牌山耗尽（外层也检查）
        if sum(rest) == 0:
            break

    # ── Step 5: 汇总 ──
    combined = [0] * NUM_TILES
    for t in range(NUM_TILES):
        for i in range(3):
            combined[t] += rivers[i][t]

    return rivers, combined, full_dora, ura_dora

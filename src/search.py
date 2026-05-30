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


def calculate_score(state: GameState,
                     tenpai_hand: Optional[List[int]] = None) -> int:
    """
    计算当前状态下的番数（役满倍数）。

    仅在手牌14张（和牌形态）时调用。
    役满之间可累加（复合役满），按正确的互斥规则处理。

    Args:
        state: 和牌状态 (14张手牌)
        tenpai_hand: 摸牌前的13张听牌状态 (可选, 用于判定四暗刻单骑)

    理论最大: 字一色+四杠子+四暗刻单骑+大四喜 = 6倍役满
    """
    hand = state.hand
    melds = state.melds

    if state.hand_size != 14:
        return 0

    # ── 判定所有役满 ─────────────────────────────
    kokushi = check_kokushi(hand)

    # 四暗刻判定:
    #   14张手牌 → check_suuankou 返回 1 (四暗刻) 或 0
    #   13张听牌 → check_suuankou 返回 2 (单骑) 或 0
    #   仅当听牌显示单骑时才升级为2倍, 否则保留14张的结果
    suuankou_14 = check_suuankou(hand, melds)
    if tenpai_hand is not None and suuankou_14 > 0:
        suuankou_tanki = check_suuankou(tenpai_hand, melds)
        if suuankou_tanki == 2:
            suuankou = 2  # 升级为单骑
        else:
            suuankou = suuankou_14  # 普通四暗刻
    else:
        suuankou = suuankou_14

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

    # 6. 累计役满(数え役满): 无真役满时, 检查普通番是否≥13
    if score == 0:
        from .yaku.regular import calculate_regular_han
        regular_han = calculate_regular_han(state)
        if regular_han >= 13:
            score = 1  # 累计役满=1倍役满

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
    # 核心思路: 降低各役满门槛，宁可多搜不漏搜
    dominant_suit = -1
    dominant_count = 0

    # 清老头潜力
    terminal_count = sum(hand[t] for t in (0, 8, 9, 17, 18, 26))
    non_terminal_numbers = sum(
        hand[t] for t in range(27)
        if t not in (0, 8, 9, 17, 18, 26)
    )
    if non_terminal_numbers <= 5 and terminal_count >= 7:
        useful.update({0, 8, 9, 17, 18, 26})

    # 国士无双潜力
    present_yaochu = sum(1 for t in YAOCHU_TILES if hand[t] >= 1)
    if present_yaochu >= 7:
        useful.update(YAOCHU_TILES)

    # 字一色 / 风牌/三元牌
    honor_count = sum(hand[t] for t in range(27, 34))
    if honor_count >= 7:
        useful.update(range(27, 34))
    wind_count = sum(hand[t] for t in range(27, 31))
    dragon_count = sum(hand[t] for t in range(31, 34))
    if wind_count >= 6:
        useful.update(range(27, 31))
    if dragon_count >= 6:
        useful.update(range(31, 34))

    # 九莲宝灯/清一色潜力: 找主导花色
    for base in (0, 9, 18):
        suit_count = sum(hand[base:base+9])
        if suit_count > dominant_count:
            dominant_count = suit_count
            dominant_suit = base
        if suit_count >= 8:
            useful.update(range(base, base + 9))

    # 绿一色潜力
    green_count = sum(hand[t] for t in GREEN_TILES)
    if green_count >= 7:
        useful.update(GREEN_TILES)

    # 四暗刻潜力: 对子/刻子
    for t in range(NUM_TILES):
        if hand[t] >= 2:
            useful.add(t)

    # ── 兜底: 主导花色 ≥ 7 张 → 至少追清一色/九莲 ──
    if not useful and dominant_count >= 7:
        useful.update(range(dominant_suit, dominant_suit + 9))
        # 再加入幺九牌(万一转国士)
        useful.update(YAOCHU_TILES)

    # ── 兜底2: 仍然空 → 摸所有已有牌的种类(至少能凑对子/刻子) ──
    if not useful:
        for t in range(NUM_TILES):
            if hand[t] >= 1:
                useful.add(t)

    # ── 兜底3: 为累计役满添加宝牌相关牌 ──
    # 搜索阶段可能通过累计普通役种+宝牌达成数え役满
    if state.dora_indicators:
        from .tile import dora_indicator_to_dora
        for ind in state.dora_indicators:
            dora = dora_indicator_to_dora(ind)
            if state.rest[dora] > 0:
                useful.add(dora)
    # 添加相邻牌（靠张）
    for t in range(NUM_TILES):
        if hand[t] >= 1 and t not in useful and state.rest[t] > 0:
            s = suit(t)
            if s != SUIT_JIHAI:
                n = t % 9
                for dn in (-2, -1, 1, 2):
                    adj = t + dn
                    if 0 <= adj < s*9+9 and hand[adj] >= 1 and state.rest[t] > 0:
                        useful.add(t)
                        break

    # 过滤掉已用完的牌
    result = [t for t in useful if state.rest[t] > 0 and state.hand[t] < 4]

    # 按剩余数量和幺九优先级排序
    def sort_key(t: int) -> int:
        return -(state.rest[t] * 10 + (5 if is_yaochu(t) else 0))

    result.sort(key=sort_key)
    return result


def _discard_candidates(state: GameState, waits: Optional[List[int]] = None) -> List[int]:
    """
    弃牌候选排序: 优先弃孤立牌/非目标花色牌。

    策略:
      1. 已听牌: 只弃非听牌
      2. 未听牌: 先弃孤立牌 → 非主导花色 → 其他
      3. 限制最多 6 个弃牌候选
    """
    from .tile import suit, SUIT_JIHAI

    if waits is None:
        waits = []

    hand = state.hand

    # ── 找主导花色 ──
    suit_counts = [sum(hand[b:b+9]) for b in (0, 9, 18)]
    max_suit = max(suit_counts)
    # 降低主导花色门槛，两花色接近时选多的
    dominant_suit = suit_counts.index(max_suit) if max_suit >= 7 else -1

    extras = []          # 多余牌(count≥4 或 count≥3且非主导花色)
    singles = []         # 孤立牌
    minority = []        # 非主导花色的牌
    majority_singles = []  # 主导花色中的孤立牌(最后才弃)
    others = []

    for t in range(NUM_TILES):
        if hand[t] <= 0:
            continue

        # 已听牌: 只弃非听牌
        if waits:
            if t not in waits:
                others.append(t)
            continue

        # 多余牌: count≥4 可以安全丢弃1张
        if hand[t] >= 4:
            extras.append(t)
            continue

        # 非主导花色的刻子(count=3): 也可丢弃
        s = suit(t)
        if dominant_suit >= 0 and s != dominant_suit and s != SUIT_JIHAI and hand[t] == 3:
            minority.insert(0, t)
            continue

        n = t % 9

        # 检查是否孤立
        is_isolated = False
        if hand[t] == 1:
            is_isolated = True
            if s != SUIT_JIHAI:
                if n >= 1 and hand[t - 1] >= 1:
                    is_isolated = False
                if n <= 7 and hand[t + 1] >= 1:
                    is_isolated = False
                if n >= 2 and hand[t - 2] >= 1:
                    is_isolated = False
            else:
                if hand[t] >= 2:
                    is_isolated = False

        # 分类
        if is_isolated:
            if dominant_suit >= 0 and s != dominant_suit and s != SUIT_JIHAI:
                singles.insert(0, t)
            elif dominant_suit >= 0 and s == dominant_suit:
                majority_singles.append(t)
            else:
                singles.append(t)
        elif dominant_suit >= 0 and s != dominant_suit and s != SUIT_JIHAI:
            minority.append(t)
        else:
            others.append(t)

    # 最终顺序: 多余牌 → 非目标花色孤立牌 → 非目标花色 → 其他孤立牌 → 其他 → 主导花色孤立
    candidates = extras + singles + minority + majority_singles + others

    if len(candidates) > 6:
        candidates = candidates[:6]

    if not candidates:
        candidates = [t for t in range(NUM_TILES) if hand[t] > 0][:6]

    return candidates


def _gen_melds(state: GameState) -> list:
    """
    快模式: 生成可行的鸣牌动作 (碰/吃/明杠)。

    返回: [(meld_type, called_tile, [hand_tiles]), ...]
    """
    from .tile import suit, SUIT_JIHAI

    hand = state.hand
    rest = state.rest
    actions = []

    # ── 碰: 手中有≥2张, 剩余牌山中≥1张 ──
    for t in range(NUM_TILES):
        if hand[t] >= 2 and rest[t] >= 1:
            actions.append(('pon', t, [t, t]))

    # ── 吃: 手中有2张可组成顺子, 剩余牌山中有衔接牌 ──
    for t in range(NUM_TILES):
        if rest[t] <= 0:
            continue
        s = suit(t)
        if s == SUIT_JIHAI:
            continue
        n = t % 9

        # 吃法1: t做第一张, 需要 hand[t+1]>=1 and hand[t+2]>=1
        if n <= 6 and hand[t+1] >= 1 and hand[t+2] >= 1:
            actions.append(('chi', t, [t+1, t+2]))
        # 吃法2: t做第二张, 需要 hand[t-1]>=1 and hand[t+1]>=1
        if 1 <= n <= 7 and hand[t-1] >= 1 and hand[t+1] >= 1:
            actions.append(('chi', t, [t-1, t+1]))
        # 吃法3: t做第三张, 需要 hand[t-2]>=1 and hand[t-1]>=1
        if n >= 2 and hand[t-2] >= 1 and hand[t-1] >= 1:
            actions.append(('chi', t, [t-2, t-1]))

    # 优先碰(完成刻子比顺子快)
    actions.sort(key=lambda a: 0 if a[0] == 'pon' else 1)
    return actions


def _describe_yaku(state: GameState, score: int,
                    tenpai_hand: List[int] = None) -> List[str]:
    """生成役种明细文字列表"""
    details = []
    hand = state.hand

    kokushi = check_kokushi(hand)
    suuankou = check_suuankou(hand, state.melds)
    daisangen = check_daisangen(hand)
    chuuren = check_chuuren(hand)
    daisuushi = check_daisuushi(hand)
    shousuushi = check_shousuushi(hand)
    tsuuiisou = check_tsuuiisou(hand)
    ryuuiisou = check_ryuuiisou(hand)
    chinroutou = check_chinroutou(hand)
    suukantsu = check_suukantsu(hand, state.melds)

    # 四暗刻单骑判定
    if tenpai_hand and suuankou > 0:
        tanki = check_suuankou(tenpai_hand, state.melds)
        if tanki == 2:
            suuankou = 2

    if kokushi >= 2: details.append("国士无双十三面 (双倍役满)")
    elif kokushi == 1: details.append("国士无双 (役满)")
    if chuuren >= 2: details.append("纯正九莲宝灯 (双倍役满)")
    elif chuuren == 1: details.append("九莲宝灯 (役满)")
    if daisuushi >= 2: details.append("大四喜 (双倍役满)")
    if shousuushi and not daisuushi: details.append("小四喜 (役满)")
    if daisangen: details.append("大三元 (役满)")
    if suuankou >= 2: details.append("四暗刻单骑 (双倍役满)")
    elif suuankou == 1: details.append("四暗刻 (役满)")
    if tsuuiisou: details.append("字一色 (役满)")
    if ryuuiisou: details.append("绿一色 (役满)")
    if chinroutou: details.append("清老头 (役满)")
    if suukantsu: details.append("四杠子 (役满)")

    # 累计役满判定
    if score == 1 and not details:
        from .yaku.regular import calculate_regular_han, calculate_dora
        han = calculate_regular_han(state)
        dora = calculate_dora(hand, state.dora_indicators, state.ura_dora_indicators)
        details.append(f"累计役满 (数え役满, {han}翻)")
        if dora > 0:
            details.append(f"  含宝牌 {dora} 翻")

    if not details:
        details.append(f"役满 ({score}倍)")

    return details


def search_max_score(
    initial_state: GameState,
    max_depth: int = 5,
    enable_pruning: bool = True,
    mode: str = "max",
) -> SearchResult:
    """
    搜索理论最优。

    mode:
      "max"  - 最大番数 (默认), 寻找最高役满倍数
      "fast" - 最快和牌, 寻找最少摸牌次数内能和的任意有役手牌

    Args:
        initial_state: 初始牌局状态 (13张标准)
        max_depth: 最大摸牌次数
        enable_pruning: 是否启用剪枝
        mode: "max" | "fast"
    """
    best_score = 0
    best_path: List[Tuple[str, int]] = []
    best_hand: List[int] = []       # 最优和牌的14张手牌
    best_yaku: List[str] = []       # 最优和牌的役种明细
    nodes_searched = 0
    nodes_pruned = 0
    found: bool = False  # 快模式: 找到即全局停止
    visited: dict = {}   # max模式: (hand_tuple, depth) → avoid re-search

    start_time = time.perf_counter()

    def search(state: GameState, depth: int,
               path: List[Tuple[str, int]]):
        nonlocal best_score, best_path, best_hand, best_yaku
        nonlocal nodes_searched, nodes_pruned, found

        if found:  # 快模式已找到, 全停止
            return
        nodes_searched += 1

        if depth >= max_depth:
            return

        # ── max模式: 状态缓存 ──
        if mode == "max":
            hand_key = tuple(state.hand)
            cache_key = (hand_key, depth)
            if cache_key in visited:
                nodes_pruned += 1
                return
            visited[cache_key] = True
        else:
            hand_key = tuple(state.hand)

        # ── max模式: 剪枝 ──
        remaining_draws = max_depth - depth
        if mode == "max" and enable_pruning and best_score > 0:
            if optimistic_bonus(state, remaining_draws) <= best_score:
                nodes_pruned += 1
                return

        waits_before = get_waits(state.hand)
        if mode == "fast":
            # 快模式: 听牌→只摸被听牌, 未听→摸靠张(避免全摸)
            if waits_before:
                draw_order = [t for t in waits_before
                              if state.rest[t] > 0 and state.hand[t] < 4]
            else:
                # 摸手牌中已有牌 + 相邻牌 (最多15种)
                useful = set()
                for t in range(NUM_TILES):
                    if state.hand[t] >= 1 and state.rest[t] > 0 and state.hand[t] < 4:
                        useful.add(t)
                        s = t // 9
                        n = t % 9
                        if s < 3:
                            for dn in (-2, -1, 1, 2):
                                adj = t + dn
                                if s*9 <= adj < s*9+9 and state.rest[adj] > 0 and state.hand[adj] < 4:
                                    useful.add(adj)
                draw_order = list(useful)
            # 按剩余数量和已有数量排序
            draw_order.sort(key=lambda t: -(state.rest[t]*3 + state.hand[t]*5))
        else:
            draw_order = _useful_draws(state, waits_before)

        for draw_tile in draw_order:
            if found:
                return
            if state.rest[draw_tile] <= 0 or state.hand[draw_tile] >= 4:
                continue
            if mode == "max" and waits_before and draw_tile not in waits_before:
                continue

            # ——— 摸牌 ———
            state.hand[draw_tile] += 1
            state.rest[draw_tile] -= 1
            path.append(('draw', draw_tile))

            # ——— 和牌检查 ———
            # 快模式: 和牌手牌数 = 14 - 2*n_melds (每次碰/吃减2张手牌)
            meld_count = sum(1 for a, _ in path if a in ('pon', 'chi', 'kan'))
            target_size = 14 - 2 * meld_count
            if state.hand_size == target_size and can_agari(state.hand):
                if mode == "fast":
                    from .yaku.regular import has_any_yaku
                    if has_any_yaku(state):
                        best_score = 1
                        best_path = path.copy()
                        best_hand = state.hand.copy()
                        best_yaku = ["最快和牌 (任意有役)"]
                        found = True
                        path.pop()
                        state.rest[draw_tile] += 1
                        state.hand[draw_tile] -= 1
                        return
                else:
                    if target_size == 14:  # max模式不处理鸣牌
                        tenpai = state.hand.copy()
                        tenpai[draw_tile] -= 1
                        s = calculate_score(state, tenpai_hand=tenpai)
                        if s > best_score:
                            best_score = s
                            best_path = path.copy()
                            best_hand = state.hand.copy()
                            best_yaku = _describe_yaku(state, s, tenpai_hand=tenpai)
                            if best_score >= 6:
                                path.pop()
                                state.rest[draw_tile] += 1
                                state.hand[draw_tile] -= 1
                                return

            # ——— 弃牌/鸣牌 → 递归 ———
            if depth + 1 < max_depth and not found:
                if mode == "max" and best_score > 0:
                    if optimistic_bonus(state, remaining_draws - 1) <= best_score:
                        path.pop()
                        state.rest[draw_tile] += 1
                        state.hand[draw_tile] -= 1
                        continue

                discards = _discard_candidates(state, get_waits(state.hand))[:4]

                for discard_tile in discards:
                    if found:
                        break
                    if state.hand[discard_tile] <= 0:
                        continue
                    if discard_tile == draw_tile and hand_key[discard_tile] <= 1:
                        continue
                    if mode == "max" and best_score > 0 and enable_pruning:
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

            # ——— 快模式鸣牌 (碰/吃) ———
            if mode == "fast" and depth + 1 < max_depth and not found:
                meld_actions = _gen_melds(state)
                for meld_type, called_tile, hand_tiles in meld_actions[:3]:
                    if found:
                        break
                    # 从手牌移除面子牌
                    for ht in hand_tiles:
                        if state.hand[ht] <= 0:
                            break
                    else:
                        for ht in hand_tiles:
                            state.hand[ht] -= 1
                        state.rest[called_tile] -= 1
                        path.append((meld_type, called_tile))

                        # 鸣牌后弃1张 → 递归
                        post_discards = _discard_candidates(state)[:3]
                        for discard_tile in post_discards:
                            if found:
                                break
                            if state.hand[discard_tile] <= 0:
                                continue
                            state.hand[discard_tile] -= 1
                            state.rest[discard_tile] += 1
                            path.append(('discard', discard_tile))

                            search(state, depth + 1, path)

                            path.pop()
                            state.rest[discard_tile] -= 1
                            state.hand[discard_tile] += 1

                        path.pop()
                        state.rest[called_tile] += 1
                        for ht in hand_tiles:
                            state.hand[ht] += 1

            path.pop()
            state.rest[draw_tile] += 1
            state.hand[draw_tile] -= 1

    # ── 入口处理 ─────────────────────────────────

    if initial_state.hand_size == 14:
        # 用户传入 14 张（如在摸牌后）→ 先检查和牌
        if can_agari(initial_state.hand):
            score = calculate_score(initial_state)
            if score > best_score:
                best_score = score
                best_path = [('_initial', -1)]
                best_hand = initial_state.hand.copy()
                best_yaku = _describe_yaku(initial_state, score)

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
        final_hand=best_hand,
        yaku_details=best_yaku,
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

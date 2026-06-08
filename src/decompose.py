"""
手牌拆分算法模块

将和了手牌（14张）拆分为 4 面子 + 1 雀头。
支持标准形、七对子、国士无双。

算法：基于 DFS 回溯的通用面子拆分。
"""

from typing import List, Tuple, Optional
from .tile import (
    NUM_TILES, SUIT_JIHAI, suit, is_yaochu, YAOCHU_TILES
)


def count_melds(counts: List[int]) -> int:
    """
    贪心 + 回溯计算最大可拆出的面子数（去掉雀头后使用）。
    对字牌只能做刻子；对数牌先尝试顺子，再回溯。

    返回能拆出的最大面子数（0~4）。
    """
    # 找第一个非零牌
    first = -1
    for i in range(NUM_TILES):
        if counts[i] > 0:
            first = i
            break
    if first == -1:
        return 0  # 所有牌都处理完

    best = 0

    # 尝试刻子
    if counts[first] >= 3:
        counts[first] -= 3
        best = max(best, 1 + count_melds(counts))
        counts[first] += 3
        if best == 4:
            return 4

    # 尝试顺子 (仅数牌, first%9 <= 6)
    s = suit(first)
    n = first % 9
    if s != SUIT_JIHAI and n <= 6:
        if counts[first] >= 1 and counts[first + 1] >= 1 and counts[first + 2] >= 1:
            counts[first] -= 1
            counts[first + 1] -= 1
            counts[first + 2] -= 1
            best = max(best, 1 + count_melds(counts))
            counts[first] += 1
            counts[first + 1] += 1
            counts[first + 2] += 1
            if best == 4:
                return 4

    return best


def has_valid_decomposition(counts: List[int]) -> bool:
    """
    判断是否能拆成 4 面子 + 1 雀头（标准形）。
    遍历所有可能的雀头，对剩下的牌用 count_melds 检查。
    """
    for janto_tile in range(NUM_TILES):
        if counts[janto_tile] >= 2:
            c = counts.copy()
            c[janto_tile] -= 2
            if count_melds(c) == 4:
                return True
    return False


def check_seven_pairs(counts: List[int]) -> bool:
    """检查是否为七对子形（7个对子）"""
    pairs = 0
    for c in counts:
        if c == 2:
            pairs += 1
        elif c != 0:
            return False
    return pairs == 7


def check_kokushi_structure(counts: List[int]) -> bool:
    """
    检查是否为国士无双的结构（不考虑役种）。
    13种幺九各≥1，其中一种≥2。
    """
    has_pair = False
    present_count = 0
    for t in YAOCHU_TILES:
        if counts[t] >= 1:
            present_count += 1
        if counts[t] >= 2:
            has_pair = True
    return present_count == 13 and has_pair


def can_agari(counts_14: List[int]) -> bool:
    """
    判断 14 张牌是否可以和牌（仅检查牌形结构，不检查役种）。

    支持三种和牌形：
    1. 标准形：4面子 + 1雀头
    2. 七对子：7个对子
    3. 国士无双：13种幺九 + 一对
    """
    if check_seven_pairs(counts_14):
        return True

    if check_kokushi_structure(counts_14):
        return True

    return has_valid_decomposition(counts_14)


def can_agari_with_melds(hand: List[int], num_melds: int) -> bool:
    """
    判断手牌 + 已有副露是否构成和牌形。

    每个副露面子算 1 组已完成的面子（刻子或顺子），
    剩余手牌需组成 (4 - num_melds) 组面子 + 1 组雀头。

    仅支持标准形（不支持七对子/国士 + 副露的组合）。
    暗杠算 1 组刻子，不影响门清判定。

    Args:
        hand: 手牌计数数组（张数 < 14）
        num_melds: 已有副露面子的数量

    Returns:
        True 若手牌 + 副露构成和牌形
    """
    # 无副露时直接用 can_agari（支持国士/七对子）
    if num_melds == 0:
        return can_agari(hand)

    needed_melds = 4 - num_melds
    needed_tiles = needed_melds * 3 + 2  # 面子 + 雀头

    if needed_melds < 0:
        return False
    if sum(hand) != needed_tiles:
        return False

    for t in range(NUM_TILES):
        if hand[t] >= 2:
            c = hand.copy()
            c[t] -= 2
            if count_melds(c) == needed_melds:
                return True
    return False


def get_waits(counts_13: List[int]) -> List[int]:
    """
    给定 13 张手牌，返回所有能使之和牌的被听牌列表。

    Args:
        counts_13: 手牌计数数组 (总和应为13)

    Returns:
        被听牌编码列表
    """
    waits = []
    for tile in range(NUM_TILES):
        if counts_13[tile] >= 4:
            continue  # 该牌已用尽
        counts_13[tile] += 1
        if can_agari(counts_13):
            waits.append(tile)
        counts_13[tile] -= 1
    return waits


def decompose_hand(counts_14: List[int]) -> List[List[Tuple[str, List[int]]]]:
    """
    返回所有合法的手牌拆分方案。

    每个方案是一个列表，包含 5 个元素：4 个面子 + 1 个雀头。
    每元素为 (type, tiles):
      - ('shuntsu', [a, b, c]) 顺子
      - ('kotsu', [a, a, a])   刻子
      - ('toitsu', [a, a])     雀头

    由于枚举所有拆分可能数量很大（尤其是多面听），
    此函数主要用于普通番种计算。役满判定不依赖此函数。
    """
    results = []

    def dfs(remaining: List[int], split: List[Tuple[str, List[int]]],
            janto_found: bool):
        # 边界
        if all(c == 0 for c in remaining):
            if janto_found:
                results.append(split.copy())
            return

        # 找第一个非零牌
        first = -1
        for i in range(NUM_TILES):
            if remaining[i] > 0:
                first = i
                break
        if first == -1:
            return

        s = suit(first)
        n = first % 9

        # 尝试刻子
        if remaining[first] >= 3:
            remaining[first] -= 3
            split.append(('kotsu', [first, first, first]))
            dfs(remaining, split, janto_found)
            split.pop()
            remaining[first] += 3

        # 尝试顺子
        if s != SUIT_JIHAI and n <= 6:
            if (remaining[first] >= 1 and
                    remaining[first + 1] >= 1 and
                    remaining[first + 2] >= 1):
                remaining[first] -= 1
                remaining[first + 1] -= 1
                remaining[first + 2] -= 1
                split.append(('shuntsu', [first, first + 1, first + 2]))
                dfs(remaining, split, janto_found)
                split.pop()
                remaining[first] += 1
                remaining[first + 1] += 1
                remaining[first + 2] += 1

        # 尝试雀头
        if not janto_found and remaining[first] >= 2:
            remaining[first] -= 2
            split.append(('toitsu', [first, first]))
            dfs(remaining, split, True)
            split.pop()
            remaining[first] += 2

    dfs(counts_14.copy(), [], False)
    return results


def decompose_hand_first(
    counts_14: List[int]
) -> Optional[List[Tuple[str, List[int]]]]:
    """
    返回第一个合法拆分方案（找到即返回，不枚举全部）。

    与 decompose_hand() 结果格式相同，但仅返回一个方案或 None。
    用于只需要任意一个合法拆分的场景（如普通役种判定），
    避免多面听手牌的全量枚举开销。
    """
    result: List[Optional[List[Tuple[str, List[int]]]]] = [None]

    def dfs(remaining: List[int], split: List[Tuple[str, List[int]]],
            janto_found: bool):
        if result[0] is not None:
            return  # 已找到, 提前退出

        if all(c == 0 for c in remaining):
            if janto_found:
                result[0] = split.copy()
            return

        first = -1
        for i in range(NUM_TILES):
            if remaining[i] > 0:
                first = i
                break
        if first == -1:
            return

        s = suit(first)
        n = first % 9

        # 尝试刻子
        if remaining[first] >= 3:
            remaining[first] -= 3
            split.append(('kotsu', [first, first, first]))
            dfs(remaining, split, janto_found)
            if result[0] is not None:
                return
            split.pop()
            remaining[first] += 3

        # 尝试顺子
        if s != SUIT_JIHAI and n <= 6:
            if (remaining[first] >= 1 and
                    remaining[first + 1] >= 1 and
                    remaining[first + 2] >= 1):
                remaining[first] -= 1
                remaining[first + 1] -= 1
                remaining[first + 2] -= 1
                split.append(('shuntsu', [first, first + 1, first + 2]))
                dfs(remaining, split, janto_found)
                if result[0] is not None:
                    return
                split.pop()
                remaining[first] += 1
                remaining[first + 1] += 1
                remaining[first + 2] += 1

        # 尝试雀头
        if not janto_found and remaining[first] >= 2:
            remaining[first] -= 2
            split.append(('toitsu', [first, first]))
            dfs(remaining, split, True)
            if result[0] is not None:
                return
            split.pop()
            remaining[first] += 2

    dfs(counts_14.copy(), [], False)
    return result[0]


def count_shanten(counts_13: List[int]) -> int:
    """
    计算向听数（距离听牌还差几步）。

    向听数 = 0 表示已听牌，向听数 = 1 表示差一步听牌。

    计算公式（简化）:
      shanten = 8 - 2×面子数 - 雀头候选数

    这是一个简化版本，对役满搜索足够。
    """
    # 找出当前已有的面子数 + 部分面子
    c = counts_13.copy()

    # 计算已有的完整面子
    melds = 0
    # 先数刻子
    for t in range(NUM_TILES):
        while c[t] >= 3:
            c[t] -= 3
            melds += 1

    # 再数顺子（贪心）
    for t in range(NUM_TILES):
        s = suit(t)
        n = t % 9
        if s != SUIT_JIHAI and n <= 6:
            while c[t] >= 1 and c[t + 1] >= 1 and c[t + 2] >= 1:
                c[t] -= 1
                c[t + 1] -= 1
                c[t + 2] -= 1
                melds += 1

    # 数对子和孤张
    pairs = sum(1 for x in c if x >= 2)
    singles = sum(1 for x in c if x == 1)

    # 部分面子: 对子 + 搭子
    partial = pairs + singles // 2

    shanten = 8 - 2 * melds - min(partial, 4 - melds)
    return max(-1, shanten)  # -1 表示已经和了

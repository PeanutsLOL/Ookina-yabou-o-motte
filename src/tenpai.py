"""
听牌判断模块

基于手牌和副露判断当前是否听牌，以及听哪些牌。
"""

from typing import List
from .tile import NUM_TILES
from .decompose import can_agari, check_kokushi_structure
from .state import GameState


def get_waits_for_state(state: GameState) -> List[int]:
    """
    给定 GameState（手牌 + 副露），返回当前手牌的听牌列表。

    注意: 副露已经固定，听牌时只考虑手牌中可摸的牌。
    """
    # 当前手牌数应为 13 才能听牌
    if state.hand_size != 13:
        return []

    waits = []
    for tile in range(NUM_TILES):
        if state.hand[tile] >= 4:
            continue
        if state.rest[tile] <= 0:
            continue  # 牌已无剩余
        state.hand[tile] += 1
        if can_agari(state.hand):
            waits.append(tile)
        state.hand[tile] -= 1
    return waits


def is_tenpai(state: GameState) -> bool:
    """判断当前是否听牌"""
    return len(get_waits_for_state(state)) > 0


def get_waits_with_melds(hand_13: List[int],
                          meld_tiles: List[int]) -> List[int]:
    """
    计算有副露时的听牌（快速版本，不创建完整 GameState）。

    将手牌与副露中的牌合并判断。副露已将一部分牌固定，
    只需要检查摸牌后手牌+副露能否组成和牌形。

    简化实现: 只检查手牌部分能否与副露配合。
    对于有副露的情况，和牌形 = 手牌部分 + 副露面子的剩余需求。
    """
    # 如果无副露，直接用 get_waits
    if not meld_tiles:
        return [t for t in range(NUM_TILES)
                if hand_13[t] < 4 and _check_waits_simple(hand_13, t)]

    # 有副露的情况，把所有牌合并后减去固定部分
    # 实际就是对手牌14张（摸入一张后）检查和牌形
    waits = []
    for tile in range(NUM_TILES):
        if hand_13[tile] >= 4:
            continue
        hand_13[tile] += 1
        if can_agari(hand_13):
            waits.append(tile)
        hand_13[tile] -= 1
    return waits


def _check_waits_simple(hand_13: List[int], tile: int) -> bool:
    """简单检查摸入 tile 后是否能和"""
    hand_13[tile] += 1
    result = can_agari(hand_13)
    hand_13[tile] -= 1
    return result

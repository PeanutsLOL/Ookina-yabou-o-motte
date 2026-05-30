"""
鸣牌动作生成模块

生成合法的鸣牌动作（碰、杠、吃、暗杠）。
注意: 吃只能从上一家鸣（实际雀魂中），简化考虑从任意家。
"""

from typing import List, Optional
from .tile import NUM_TILES, suit, SUIT_JIHAI
from .state import Meld


def generate_pon(hand: List[int], called_tile: int,
                  from_player: int = 1) -> Optional[Meld]:
    """
    生成碰的动作。

    Args:
        hand: 当前手牌计数数组
        called_tile: 被鸣的牌
        from_player: 打出此牌的玩家 (1=下家,2=对家,3=上家)

    Returns:
        碰的 Meld，若手牌中同牌不足2张则返回 None
    """
    if hand[called_tile] >= 2:
        return Meld(
            meld_type="pon",
            tiles=[called_tile, called_tile, called_tile],
            from_player=from_player,
            called_tile=called_tile,
            is_open=True
        )
    return None


def generate_kan_from_hand(hand: List[int], tile: int) -> Optional[Meld]:
    """
    生成暗杠 (手中有4张同牌)。

    Args:
        hand: 手牌计数数组
        tile: 要杠的牌
    """
    if hand[tile] == 4:
        return Meld(
            meld_type="ankan",
            tiles=[tile, tile, tile, tile],
            from_player=0,
            called_tile=None,
            is_open=False
        )
    return None


def generate_kan_from_pon(hand: List[int], tile: int,
                           existing_melds: List[Meld]) -> Optional[Meld]:
    """
    生成加杠: 手中已有碰(tile的pon副露)，又摸到一张同牌。

    Args:
        hand: 手牌
        tile: 加杠的牌
        existing_melds: 已有的副露列表
    """
    # 检查是否已有此牌的碰
    has_pon = any(
        m.meld_type == "pon" and m.tiles[0] == tile
        for m in existing_melds
    )
    if has_pon and hand[tile] >= 1:
        return Meld(
            meld_type="kakan",
            tiles=[tile, tile, tile, tile],
            from_player=0,
            called_tile=tile,
            is_open=True
        )
    return None


def generate_daiminkan(hand: List[int], called_tile: int,
                        from_player: int = 1) -> Optional[Meld]:
    """
    生成大明杠: 手中有3张同牌，其他家打出第4张。
    """
    if hand[called_tile] >= 3:
        return Meld(
            meld_type="kan",
            tiles=[called_tile, called_tile, called_tile, called_tile],
            from_player=from_player,
            called_tile=called_tile,
            is_open=True
        )
    return None


def generate_chi(hand: List[int], called_tile: int,
                  from_player: int = 3) -> List[Meld]:
    """
    生成吃牌动作列表。

    吃只能吃上家（from_player=3）的牌。
    生成手牌中所有可能的顺子组合。

    Args:
        hand: 手牌计数
        called_tile: 上家打出的牌
        from_player: 默认3=上家

    Returns:
        所有合法吃的 Meld 列表
    """
    results = []
    s = suit(called_tile)
    if s == SUIT_JIHAI:
        return results  # 字牌不能吃

    n = called_tile % 9  # 0~8

    # 吃的三种可能性 (以 called_tile 在顺子中的位置):
    # 1. 做第一个: called_tile, called_tile+1, called_tile+2
    # 2. 做第二个: called_tile-1, called_tile, called_tile+1
    # 3. 做第三个: called_tile-2, called_tile-1, called_tile

    # 位置1
    if n <= 6:
        if hand[called_tile + 1] >= 1 and hand[called_tile + 2] >= 1:
            results.append(Meld(
                meld_type="chi",
                tiles=[called_tile, called_tile + 1, called_tile + 2],
                from_player=from_player,
                called_tile=called_tile,
                is_open=True
            ))

    # 位置2
    if 1 <= n <= 7:
        if hand[called_tile - 1] >= 1 and hand[called_tile + 1] >= 1:
            results.append(Meld(
                meld_type="chi",
                tiles=[called_tile - 1, called_tile, called_tile + 1],
                from_player=from_player,
                called_tile=called_tile,
                is_open=True
            ))

    # 位置3
    if n >= 2:
        if hand[called_tile - 2] >= 1 and hand[called_tile - 1] >= 1:
            results.append(Meld(
                meld_type="chi",
                tiles=[called_tile - 2, called_tile - 1, called_tile],
                from_player=from_player,
                called_tile=called_tile,
                is_open=True
            ))

    return results


def generate_all_melds(hand: List[int], called_tile: int,
                        from_player: int,
                        existing_melds: List[Meld]) -> List[Meld]:
    """
    生成所有合法鸣牌动作。

    Args:
        hand: 当前手牌计数
        called_tile: 被鸣的牌（其他家打出/摸入）
        from_player: 来源玩家 (1=下,2=对,3=上)
        existing_melds: 已有副露

    Returns:
        所有合法动作的 Meld 列表
    """
    results = []

    # 碰
    pon = generate_pon(hand, called_tile, from_player)
    if pon:
        results.append(pon)

    # 大明杠
    kan = generate_daiminkan(hand, called_tile, from_player)
    if kan:
        results.append(kan)

    # 吃 (仅上家)
    if from_player == 3:
        results.extend(generate_chi(hand, called_tile, from_player))

    return results

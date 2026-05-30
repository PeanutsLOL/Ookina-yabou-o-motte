"""
牌编码与辅助函数模块

牌编码 tile: 0~33
  0~8:   1m~9m (万子 Manzu)
  9~17:  1p~9p (筒子 Pinzu)
  18~26: 1s~9s (索子 Souzu)
  27~33: 东南西北白发中 (字牌 Jihai)
          27=东, 28=南, 29=西, 30=北, 31=白, 32=发, 33=中
"""

from typing import List, Tuple

# ── 常量 ──────────────────────────────────────────────

NUM_TILES = 34

# 花色
SUIT_MANZU = 0    # 万子
SUIT_PINZU = 1    # 筒子
SUIT_SOUZU = 2    # 索子
SUIT_JIHAI = 3    # 字牌

SUIT_NAMES = {0: "万", 1: "筒", 2: "索", 3: "字"}

# 幺九牌索引 (终端牌 + 字牌)
YAOCHU_TILES = {
    0, 8,           # 1m, 9m
    9, 17,          # 1p, 9p
    18, 26,         # 1s, 9s
    27, 28, 29, 30, 31, 32, 33  # 东南西北白发中
}

# 字牌索引
HONOR_TILES = {27, 28, 29, 30, 31, 32, 33}

# 老头牌索引（1和9）
TERMINAL_TILES = {0, 8, 9, 17, 18, 26}

# 风牌索引
WIND_TILES = {27, 28, 29, 30}

# 三元牌索引
DRAGON_TILES = {31, 32, 33}

# 牌名映射 (用于显示)
TILE_NAMES: dict[int, str] = {}
for i in range(9):
    TILE_NAMES[i] = f"{i+1}m"
for i in range(9):
    TILE_NAMES[i+9] = f"{i+1}p"
for i in range(9):
    TILE_NAMES[i+18] = f"{i+1}s"
TILE_NAMES[27] = "东"
TILE_NAMES[28] = "南"
TILE_NAMES[29] = "西"
TILE_NAMES[30] = "北"
TILE_NAMES[31] = "白"
TILE_NAMES[32] = "发"
TILE_NAMES[33] = "中"

# 反向映射: 牌名 → 编码
NAME_TO_TILE: dict[str, int] = {v: k for k, v in TILE_NAMES.items()}
# 添加不带后缀的数字作为别名 (m=万默认)
for i in range(1, 10):
    NAME_TO_TILE[str(i)] = i - 1


# ── 辅助函数 ──────────────────────────────────────────

def suit(tile: int) -> int:
    """返回牌的花色: 0=万, 1=筒, 2=索, 3=字"""
    return tile // 9


def num(tile: int) -> int:
    """返回牌的数字 1~9，字牌返回 0"""
    if suit(tile) == SUIT_JIHAI:
        return 0
    return (tile % 9) + 1


def is_yaochu(tile: int) -> bool:
    """判断是否为幺九牌（1/9 或字牌）"""
    return tile in YAOCHU_TILES


def is_terminal(tile: int) -> bool:
    """判断是否为老头牌（1 或 9）"""
    return tile in TERMINAL_TILES


def is_honor(tile: int) -> bool:
    """判断是否为字牌"""
    return tile in HONOR_TILES


def is_wind(tile: int) -> bool:
    """判断是否为风牌"""
    return tile in WIND_TILES


def is_dragon(tile: int) -> bool:
    """判断是否为三元牌"""
    return tile in DRAGON_TILES


def is_valid_tile(tile: int) -> bool:
    """判断是否为合法牌编码"""
    return 0 <= tile < NUM_TILES


def tile_name(tile: int) -> str:
    """返回牌的中文名称"""
    return TILE_NAMES.get(tile, f"未知({tile})")


def parse_tile(name: str) -> int:
    """
    解析牌名，返回编码。
    支持格式: '1m', '5p', '9s', '东', '白', 或纯数字(默认万)
    """
    if name in NAME_TO_TILE:
        return NAME_TO_TILE[name]
    raise ValueError(f"无法解析的牌名: {name}")


def parse_hand_str(hand_str: str) -> List[int]:
    """
    解析手牌字符串，返回长度为34的计数数组。

    格式示例:
      '123m456p789s12344z'  → 万筒索字依次排列
      '1m1m1m2p3p4p5s6s7s东东西西'
      '111m 222p 333s 77z 55z'

    后缀字母: m=万, p=筒, s=索, z=字
    字牌数字映射: 1=东,2=南,3=西,4=北,5=白,6=发,7=中
    """
    import re

    counts = [0] * NUM_TILES

    # 移除空白
    hand_str = re.sub(r'\s+', '', hand_str)

    # 匹配模式: 数字+后缀 或 单个中文字牌
    # 支持: 123m, 77z, 东, 白白
    pattern = r'(\d*)([mpsz])|([东南西北白发中])'
    pos = 0
    while pos < len(hand_str):
        # 尝试中文字牌
        if hand_str[pos] in '东南西北白发中':
            t = parse_tile(hand_str[pos])
            counts[t] += 1
            pos += 1
            continue

        # 尝试数字+后缀
        match = re.match(r'(\d*)([mpsz])', hand_str[pos:])
        if match:
            digits = match.group(1)
            suffix = match.group(2)
            if suffix == 'm':
                base = 0
            elif suffix == 'p':
                base = 9
            elif suffix == 's':
                base = 18
            else:  # z
                base = 27

            for d in digits:
                n = int(d)
                if suffix == 'z':
                    # 字牌: 1=东 2=南 3=西 4=北 5=白 6=发 7=中
                    if 1 <= n <= 7:
                        counts[base + n - 1] += 1
                else:
                    if 1 <= n <= 9:
                        counts[base + n - 1] += 1
            pos += len(digits) + 1
        else:
            raise ValueError(f"无法解析的手牌字符串，位置 {pos}: '{hand_str[pos:]}'")

    return counts


def counts_to_str(counts: List[int]) -> str:
    """将计数数组转换回手牌字符串"""
    parts = []
    for suffix, base in [('m', 0), ('p', 9), ('s', 18)]:
        s = ''
        for i in range(9):
            s += str(i + 1) * counts[base + i]
        if s:
            parts.append(s + suffix)

    z_str = ''
    for i in range(7):
        z_str += str(i + 1) * counts[27 + i]
    if z_str:
        parts.append(z_str + 'z')

    return ''.join(parts)


def hand_to_list(counts: List[int]) -> List[int]:
    """将计数数组展开为牌编码列表（每张牌一个元素）"""
    result = []
    for t in range(NUM_TILES):
        result.extend([t] * counts[t])
    return result


def count_tiles(counts: List[int]) -> int:
    """计数数组中的总牌数"""
    return sum(counts)


def dora_indicator_to_dora(indicator: int) -> int:
    """
    根据宝牌指示牌计算实际宝牌。
    规则: 指示牌的下一张即为宝牌。
    万: 1→2, 2→3, ... 9→1
    筒/索同理
    字牌: 东→南→西→北→东, 白→发→中→白
    """
    s = suit(indicator)
    n = num(indicator)

    if s == SUIT_JIHAI:
        # 风牌: 东南西北循环
        if indicator <= 30:
            next_offset = (indicator - 27 + 1) % 4
            return 27 + next_offset
        # 三元牌: 白发中循环
        else:
            next_offset = (indicator - 31 + 1) % 3
            return 31 + next_offset
    else:
        # 数牌: 1~9 循环
        new_n = (n % 9) + 1  # 1→2, 9→1
        return s * 9 + (new_n - 1)


# ── 常量：所有34种牌的列表 ─────────────────────────────

ALL_TILES = list(range(NUM_TILES))

# 按花色分组的牌列表
MANZU_TILES = list(range(0, 9))
PINZU_TILES = list(range(9, 18))
SOUZU_TILES = list(range(18, 27))
JIHAI_TILES = list(range(27, 34))

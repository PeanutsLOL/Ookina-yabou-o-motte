"""
tile.py 单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tile import (
    suit, num, is_yaochu, is_terminal, is_honor,
    is_wind, is_dragon, is_valid_tile, tile_name,
    parse_tile, parse_hand_str, counts_to_str,
    hand_to_list, count_tiles, dora_indicator_to_dora,
    NUM_TILES, ALL_TILES
)


class TestTileEncoding:
    """牌编码基本测试"""

    def test_suit(self):
        assert suit(0) == 0    # 1m → 万
        assert suit(8) == 0    # 9m → 万
        assert suit(9) == 1    # 1p → 筒
        assert suit(17) == 1   # 9p → 筒
        assert suit(18) == 2   # 1s → 索
        assert suit(26) == 2   # 9s → 索
        assert suit(27) == 3   # 东 → 字
        assert suit(33) == 3   # 中 → 字

    def test_num(self):
        assert num(0) == 1    # 1m
        assert num(8) == 9    # 9m
        assert num(10) == 2   # 2p
        assert num(27) == 0   # 东 (字牌无数字)

    def test_num_tiles(self):
        assert NUM_TILES == 34
        assert len(ALL_TILES) == 34

    def test_is_valid_tile(self):
        assert is_valid_tile(0)
        assert is_valid_tile(33)
        assert not is_valid_tile(-1)
        assert not is_valid_tile(34)


class TestTileClassification:
    """牌分类函数测试"""

    def test_is_yaochu(self):
        # 幺九牌
        assert is_yaochu(0)    # 1m
        assert is_yaochu(8)    # 9m
        assert is_yaochu(9)    # 1p
        assert is_yaochu(17)   # 9p
        assert is_yaochu(18)   # 1s
        assert is_yaochu(26)   # 9s
        assert is_yaochu(27)   # 东
        assert is_yaochu(33)   # 中
        # 非幺九
        assert not is_yaochu(3)   # 4m
        assert not is_yaochu(14)  # 6p

    def test_is_terminal(self):
        assert is_terminal(0)   # 1m
        assert is_terminal(8)   # 9m
        assert not is_terminal(27)  # 东 (是字牌但不是老头)

    def test_is_honor(self):
        assert is_honor(27)  # 东
        assert is_honor(31)  # 白
        assert not is_honor(0)  # 1m

    def test_is_wind_dragon(self):
        assert is_wind(27)   # 东
        assert is_wind(30)   # 北
        assert not is_wind(31)  # 白

        assert is_dragon(31)  # 白
        assert is_dragon(33)  # 中
        assert not is_dragon(27)  # 东


class TestTileName:
    """牌名函数测试"""

    def test_tile_name(self):
        assert tile_name(0) == "1m"
        assert tile_name(9) == "1p"
        assert tile_name(18) == "1s"
        assert tile_name(27) == "东"
        assert tile_name(33) == "中"

    def test_parse_tile(self):
        assert parse_tile("1m") == 0
        assert parse_tile("9m") == 8
        assert parse_tile("5p") == 13
        assert parse_tile("东") == 27
        assert parse_tile("白") == 31
        assert parse_tile("中") == 33


class TestParseHandStr:
    """手牌字符串解析测试"""

    def test_simple_parse(self):
        # 国士无双13面
        counts = parse_hand_str("19m19p19s1234567z")
        assert sum(counts) == 13
        assert counts[0] == 1   # 1m
        assert counts[8] == 1   # 9m
        assert counts[27] == 1  # 东
        assert counts[33] == 1  # 中

    def test_double_digit(self):
        # 22m 表示两张2m
        counts = parse_hand_str("22m")
        assert counts[1] == 2  # 2m ×2

    def test_count_to_str_roundtrip(self):
        original = "123m456p789s11z"
        counts = parse_hand_str(original)
        result = counts_to_str(counts)
        # 重新解析应得到相同结果
        counts2 = parse_hand_str(result)
        assert counts == counts2

    def test_total_14(self):
        # 已和牌: 111m+234p+567s+东东东+白白
        counts = parse_hand_str("111m234p567s111z55z")
        assert sum(counts) == 14

    def test_chinese_names(self):
        """中文牌名解析"""
        counts = [0] * 34
        counts[27] = 1  # 东
        expected = parse_hand_str("1z")
        assert expected[27] == 1


class TestDora:
    """宝牌计算测试"""

    def test_dora_indicator_manzu(self):
        assert dora_indicator_to_dora(0) == 1   # 1m → 2m
        assert dora_indicator_to_dora(7) == 8   # 8m → 9m
        assert dora_indicator_to_dora(8) == 0   # 9m → 1m

    def test_dora_indicator_wind(self):
        assert dora_indicator_to_dora(27) == 28  # 东 → 南
        assert dora_indicator_to_dora(28) == 29  # 南 → 西
        assert dora_indicator_to_dora(29) == 30  # 西 → 北
        assert dora_indicator_to_dora(30) == 27  # 北 → 东

    def test_dora_indicator_dragon(self):
        assert dora_indicator_to_dora(31) == 32  # 白 → 发
        assert dora_indicator_to_dora(32) == 33  # 发 → 中
        assert dora_indicator_to_dora(33) == 31  # 中 → 白


class TestHandToList:
    def test_hand_to_list(self):
        counts = parse_hand_str("123m456p789s11z")
        lst = hand_to_list(counts)
        assert len(lst) == 11
        # 应有 1m, 2m, 3m
        assert 0 in lst
        assert 1 in lst
        assert 2 in lst


if __name__ == "__main__":
    # 运行所有测试
    import pytest
    pytest.main([__file__, "-v"])

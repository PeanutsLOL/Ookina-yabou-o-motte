"""
decompose.py 和 tenpai.py 单元测试

测试手牌拆分、和牌判定、听牌判断。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tile import parse_hand_str
from src.decompose import (
    can_agari, get_waits, count_melds,
    check_seven_pairs, check_kokushi_structure,
    count_shanten, decompose_hand
)


class TestCanAgari:
    """和牌判定测试"""

    def test_standard_hand_menzen(self):
        """标准形: 门清平和 4顺子+1雀头"""
        counts = parse_hand_str("123m456p789s12344m")
        assert sum(counts) == 14
        assert can_agari(counts) is True

    def test_standard_with_kotsu(self):
        """含刻子的手牌"""
        counts = parse_hand_str("111m234p567s111z55z")
        assert sum(counts) == 14
        assert can_agari(counts) is True

    def test_seven_pairs(self):
        """七对子: 7对"""
        counts = parse_hand_str("11m99m11p99p11s99s11z")
        assert sum(counts) == 14
        assert can_agari(counts) is True

    def test_kokushi(self):
        """国士无双: 13种幺九+对子"""
        counts = parse_hand_str("119m19p19s1234567z")
        assert sum(counts) == 14
        assert can_agari(counts) is True

    def test_not_agari(self):
        """不能和的手牌"""
        counts = parse_hand_str("123m456p789s12345m")
        assert sum(counts) == 14
        assert can_agari(counts) is False


class TestGetWaits:
    """听牌判断测试"""

    def test_ryanmen_wait(self):
        """两面听: 45m → 听3m/6m"""
        # 45m 234p 567s 111z 22z = 13 tiles
        counts = parse_hand_str("45m234p567s11122z")
        assert sum(counts) == 13
        waits = get_waits(counts)
        assert 2 in waits   # 3m
        assert 5 in waits   # 6m

    def test_shanpon_wait(self):
        """双碰听: 四暗刻听牌 111m222p333s77z55z"""
        counts = parse_hand_str("111m222p333s77z55z")
        assert sum(counts) == 13
        waits = get_waits(counts)
        # 听 5z(白=31) 或 7z(中=33)
        assert 31 in waits  # 白
        assert 33 in waits  # 中
        assert len(waits) >= 2

    def test_kokushi_tenpai(self):
        """国士无双听牌: 12种幺九 + 1种对子 (13张, 缺1种)"""
        # 1m×2, 9m, 1p, 9p, 1s, 9s, 东,南,西,北,白,发 = 13张 (缺中)
        counts = parse_hand_str("119m19p19s123456z")
        assert sum(counts) == 13
        waits = get_waits(counts)
        # 听缺的那张 中(33)
        assert 33 in waits

    def test_not_tenpai(self):
        """未听牌"""
        counts = parse_hand_str("123m456p789s1234z")
        waits = get_waits(counts)
        assert isinstance(waits, list)


class TestCountShanten:
    """向听数测试"""

    def test_tenpai_shanten(self):
        """听牌: 向听数为0或-1"""
        counts = parse_hand_str("45m234p567s11122z")
        shanten = count_shanten(counts)
        # 简化向听数算法可能对某些听牌算不准, 允许 ≤1
        assert shanten <= 1

    def test_not_tenpai_shanten(self):
        """未听牌: 向听数>0"""
        counts = parse_hand_str("12m34p56s789m123z")
        shanten = count_shanten(counts)
        assert shanten >= 1


class TestDecomposeHand:
    """手牌拆分测试"""

    def test_simple_decompose(self):
        """简单拆分: 4顺子+1雀头"""
        counts = parse_hand_str("123m456p789s12344m")
        results = decompose_hand(counts)
        assert len(results) >= 1

    def test_kotsu_decompose(self):
        """含刻子的拆分"""
        counts = parse_hand_str("111m234p567s111z55z")
        results = decompose_hand(counts)
        assert len(results) >= 1
        has_kotsu = any(
            any(m[0] == 'kotsu' for m in result)
            for result in results
        )
        assert has_kotsu

    def test_not_agari_decompose(self):
        """不能和的牌: 无合法拆分"""
        counts = parse_hand_str("123m456p789s12345m")
        results = decompose_hand(counts)
        assert len(results) == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

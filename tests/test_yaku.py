"""
役满判定模块单元测试

测试国士无双、四暗刻、大三元、九莲宝灯的判定函数。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tile import parse_hand_str
from src.yaku.kokushi import check_kokushi
from src.yaku.suuankou import check_suuankou
from src.yaku.daisangen import check_daisangen
from src.yaku.chuuren import check_chuuren


class TestKokushi:
    """国士无双判定测试"""

    def test_kokushi_normal(self):
        """国士无双十三面: 13种幺九各1+1种2张 (14张已和)"""
        counts = parse_hand_str("119m19p19s1234567z")
        assert sum(counts) == 14
        result = check_kokushi(counts)
        # 12单张+1对子是13面形 → 2倍役满
        assert result == 2

    def test_kokushi_not_13men(self):
        """12种幺九+1对+1张: 不是完整的国士 (缺一种幺九)"""
        counts = [0] * 34
        # 1m×2, 9m, 1p, 9p, 1s, 9s, 东南西北白发 (缺中) = 13张
        counts[0] = 2  # 1m×2
        counts[8] = 1  # 9m
        counts[9] = 1  # 1p
        counts[17] = 1  # 9p
        counts[18] = 1  # 1s
        counts[26] = 1  # 9s
        for t in range(27, 33):  # 东南西北白发
            counts[t] = 1
        assert sum(counts) == 13
        # 13张, 缺一种幺九(中), 不是完整的国士
        result = check_kokushi(counts)
        assert result == 0  # 手牌只有13张, 不完整

    def test_not_kokushi(self):
        """非国士无双"""
        counts = parse_hand_str("123m456p789s12344z")
        result = check_kokushi(counts)
        assert result == 0


class TestSuuankou:
    """四暗刻判定测试"""

    def test_suuankou_standard(self):
        """标准四暗刻: 4暗刻+1雀头"""
        counts = parse_hand_str("111m222p333s777z55z")
        assert sum(counts) == 14
        result = check_suuankou(counts)
        assert result == 1

    def test_suuankou_tanki(self):
        """四暗刻单骑: 4暗刻+1单张 (13张听牌)"""
        counts = parse_hand_str("111m222p333s777z5z")
        assert sum(counts) == 13
        result = check_suuankou(counts)
        assert result == 2

    def test_not_suuankou(self):
        """非四暗刻"""
        counts = parse_hand_str("123m456p789s12344z")
        result = check_suuankou(counts)
        assert result == 0


class TestDaisangen:
    """大三元判定测试"""

    def test_daisangen(self):
        """大三元: 白发中各一暗刻"""
        # 111m 白白白 发发发 中中中 77z → 15张, 取13张听牌
        # 白白白=555z, 发发发=666z, 中中中=777z
        # 但111m222p555666777z是15张。去掉1组面子: 111m555666777z11z
        counts = parse_hand_str("111m555666777z11z")
        assert sum(counts) == 14
        result = check_daisangen(counts)
        assert result == 1

    def test_not_daisangen(self):
        """非大三元"""
        counts = parse_hand_str("123m456p789s12344z")
        result = check_daisangen(counts)
        assert result == 0


class TestChuuren:
    """九莲宝灯判定测试"""

    def test_chuuren_standard(self):
        """九莲宝灯: 1112345678999 + 任意1张"""
        counts = [0] * 34
        # 万子: 1112345678999
        counts[0] = 3  # 1m ×3
        counts[1] = 1  # 2m
        counts[2] = 1  # 3m
        counts[3] = 1  # 4m
        counts[4] = 1  # 5m
        counts[5] = 1  # 6m
        counts[6] = 1  # 7m
        counts[7] = 1  # 8m
        counts[8] = 3  # 9m ×3
        # 再加1张(第14张): 多1张5m
        counts[4] += 1
        assert sum(counts) == 14
        result = check_chuuren(counts)
        assert result >= 1  # 九莲宝灯 (可能是纯正倍数)

    def test_chuuren_not_9men(self):
        """非纯正九莲: 某牌超过3张"""
        counts = [0] * 34
        counts[0] = 4  # 1m ×4 (超过3)
        counts[1] = 1  # 2m
        counts[2] = 1  # 3m
        counts[3] = 1  # 4m
        counts[4] = 1  # 5m
        counts[5] = 1  # 6m
        counts[6] = 1  # 7m
        counts[7] = 1  # 8m
        counts[8] = 3  # 9m ×3
        assert sum(counts) == 14
        result = check_chuuren(counts)
        assert result == 1  # 普通九莲

    def test_not_chuuren(self):
        """非九莲宝灯: 多花色"""
        counts = parse_hand_str("123m456p789s12344z")
        result = check_chuuren(counts)
        assert result == 0

    def test_chuuren_mixed_suit(self):
        """多花色: 不是九莲"""
        counts = parse_hand_str("123m456p789s12344z")
        result = check_chuuren(counts)
        assert result == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

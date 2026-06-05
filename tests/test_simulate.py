"""
牌局模拟模块单元测试

测试 simulate.py 中的发牌、宝牌生成、弃牌决策和主模拟流程。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random
from src.tile import (
    NUM_TILES, tile_name, parse_hand_str, is_honor,
    dora_indicator_to_dora, suit, SUIT_JIHAI,
)
from src.decompose import count_shanten
from src.simulate import (
    _is_isolated,
    best_discard,
    deal_opponent_hands,
    _generate_dora_indicators,
    simulate_game,
)


class TestIsIsolated:
    """孤立牌判定测试"""

    def test_single_honor_isolated(self):
        """单张字牌应判定为孤立"""
        hand = [0] * NUM_TILES
        hand[27] = 1  # 东
        assert _is_isolated(hand, 27) is True

    def test_pair_not_isolated(self):
        """对子不应判定为孤立"""
        hand = [0] * NUM_TILES
        hand[27] = 2  # 东×2
        assert _is_isolated(hand, 27) is False

    def test_adjacent_minus1_not_isolated(self):
        """有 -1 相邻牌不应孤立"""
        hand = [0] * NUM_TILES
        hand[0] = 1  # 1m
        hand[1] = 1  # 2m (相邻)
        assert _is_isolated(hand, 0) is False  # 1m 有 2m 相邻

    def test_adjacent_plus1_not_isolated(self):
        """有 +1 相邻牌不应孤立"""
        hand = [0] * NUM_TILES
        hand[1] = 1  # 2m
        hand[2] = 1  # 3m (相邻)
        assert _is_isolated(hand, 1) is False  # 2m 有 3m 相邻

    def test_adjacent_minus2_not_isolated(self):
        """有 -2 相邻牌不应孤立"""
        hand = [0] * NUM_TILES
        hand[0] = 1  # 1m
        hand[2] = 1  # 3m (相邻±2)
        assert _is_isolated(hand, 0) is False

    def test_adjacent_plus2_not_isolated(self):
        """有 +2 相邻牌不应孤立"""
        hand = [0] * NUM_TILES
        hand[0] = 1  # 1m
        hand[2] = 1  # 3m (相邻±2)
        assert _is_isolated(hand, 2) is False

    def test_truly_isolated_numeral(self):
        """距离 ≥3 的数牌应判定为孤立"""
        hand = [0] * NUM_TILES
        hand[0] = 1  # 1m
        hand[4] = 1  # 5m (距离=4)
        assert _is_isolated(hand, 0) is True


class TestBestDiscard:
    """弃牌决策测试"""

    def test_discard_isolated_honor_first(self):
        """孤立字牌应优先被弃"""
        # 构造: 111m234p567s + 东×3 + 南×1 + 2m×1 = 14张
        # 南(28)是孤立字牌，2m(1)在万子中有搭子
        counts = [0] * NUM_TILES
        counts[0] = 3   # 1m×3 (刻子)
        counts[1] = 1   # 2m×1 (有1m相邻，非孤立)
        counts[9] = 1   # 2p
        counts[10] = 1  # 3p
        counts[11] = 1  # 4p (234p顺子)
        counts[18] = 1  # 5s
        counts[19] = 1  # 6s
        counts[20] = 1  # 7s (567s顺子)
        counts[27] = 3  # 东×3 (刻子)
        counts[28] = 1  # 南×1 (孤立!)
        assert sum(counts) == 14, f"手牌应为14张, got {sum(counts)}"
        discard = best_discard(counts)
        # 南(28)是唯一的孤立牌，应被优先弃
        assert discard == 28, f"应弃孤立字牌 南(28), got {tile_name(discard)}({discard})"

    def test_preserves_kotsu(self):
        """不应优先破坏已有刻子"""
        # 手牌: 1m×3 + 234m + 567p + 789s + 11z → 14张（刻子+面子+对子）
        counts = parse_hand_str("111234m567p789s11z")
        discard = best_discard(counts)
        # 不应弃 1m（已构成刻子）
        assert discard != 0, f"不应弃 1m（已有刻子）, got {tile_name(discard)}"

    def test_preserves_pair(self):
        """不应优先破坏对子"""
        # 手牌: 123m456p789s1122z → 14张（2个对子）
        counts = parse_hand_str("123m456p789s1122z")
        discard = best_discard(counts)
        # 东和白都是对子，弃任何一张都会破坏对子结构
        # 但这是已和手牌(14张)，shanten=-1，几乎任何弃牌都回到 tenpai
        # 只验证返回的是合法牌
        assert counts[discard] > 0, "弃牌必须在手牌中"

    def test_tenpai_preserves_waits(self):
        """听牌手牌弃牌后应尽量保持听牌"""
        # 构造已听牌形: 111m234p567s + 东×3 + 南×1 + 2m×1 = 14张
        # 已有4个完整面子，等一个对子即和牌
        counts = [0] * NUM_TILES
        counts[0] = 3   # 1m×3 (刻子)
        counts[1] = 1   # 2m×1 (单张，需配成对子即和)
        counts[9] = 1   # 2p
        counts[10] = 1  # 3p
        counts[11] = 1  # 4p (234p顺子)
        counts[18] = 1  # 5s
        counts[19] = 1  # 6s
        counts[20] = 1  # 7s (567s顺子)
        counts[27] = 3  # 东×3 (刻子)
        counts[28] = 1  # 南×1 (单张，也可作为对子基础)
        assert sum(counts) == 14, f"手牌应为14张, got {sum(counts)}"
        discard = best_discard(counts)
        # 检查弃牌后仍为听牌(shanten=0)
        counts[discard] -= 1
        shanten = count_shanten(counts)
        assert shanten == 0, f"弃牌后应仍为听牌(shanten=0), got shanten={shanten}"

    def test_tiebreak_isolated_over_connected(self):
        """平分时孤立牌优先于搭子牌"""
        # 构造手牌: 1m×3, 2m×1, 234p, 567s, 东×3, 南×1 = 14张
        # 南(孤立) vs 2m(搭子): 弃牌后shanten相同，但孤立优先
        counts = [0] * NUM_TILES
        counts[0] = 3   # 1m×3 (刻子)
        counts[1] = 1   # 2m×1 (与1m搭子，非孤立)
        counts[9] = 1   # 2p
        counts[10] = 1  # 3p
        counts[11] = 1  # 4p
        counts[18] = 1  # 5s
        counts[19] = 1  # 6s
        counts[20] = 1  # 7s
        counts[27] = 3  # 东×3 (刻子)
        counts[28] = 1  # 南×1 (孤立!)
        assert sum(counts) == 14, f"手牌应为14张, got {sum(counts)}"
        discard = best_discard(counts)
        # 南(孤立)优先于2m(搭子)
        assert discard == 28, (
            f"应优先弃孤立牌 南(28), got {tile_name(discard)}({discard})"
        )


class TestDealOpponentHands:
    """发牌测试"""

    def test_deal_three_opponents(self):
        """基本发牌：3家各13张"""
        rest = [4] * NUM_TILES
        original_total = sum(rest)
        hands = deal_opponent_hands(rest, num_opponents=3)

        assert len(hands) == 3
        for i, hand in enumerate(hands):
            assert sum(hand) == 13, f"对手{i+1}手牌应为13张"

        # 牌山应减少 39 张
        assert sum(rest) == original_total - 39

    def test_rest_mutation(self):
        """验证 rest 被原地修改"""
        rest = [4] * NUM_TILES
        rest_before = rest.copy()
        hands = deal_opponent_hands(rest, num_opponents=3)

        # rest 中每张牌的减少量应等于3家手牌中该牌的增量
        for t in range(NUM_TILES):
            dealt = sum(h[t] for h in hands)
            assert rest[t] == rest_before[t] - dealt

    def test_seed_reproducibility(self):
        """相同种子应产生相同手牌"""
        rest1 = [4] * NUM_TILES
        rest2 = [4] * NUM_TILES
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        hands1 = deal_opponent_hands(rest1, num_opponents=3, rng=rng1)
        hands2 = deal_opponent_hands(rest2, num_opponents=3, rng=rng2)

        for t in range(NUM_TILES):
            for i in range(3):
                assert hands1[i][t] == hands2[i][t]

    def test_different_seeds_different_hands(self):
        """不同种子大概率不同（不验证严格不等，只验证不崩溃）"""
        rest1 = [4] * NUM_TILES
        rest2 = [4] * NUM_TILES
        rng1 = random.Random(1)
        rng2 = random.Random(9999)

        hands1 = deal_opponent_hands(rest1, num_opponents=3, rng=rng1)
        hands2 = deal_opponent_hands(rest2, num_opponents=3, rng=rng2)

        # 至少应返回3家
        assert len(hands1) == len(hands2) == 3

    def test_insufficient_tiles_raises(self):
        """牌数不足应抛异常"""
        rest = [0] * NUM_TILES
        rest[0] = 10  # 只有10张牌
        try:
            deal_opponent_hands(rest, num_opponents=3)
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "不足" in str(e) or "牌" in str(e)


class TestGenerateDoraIndicators:
    """宝牌/里宝牌生成测试"""

    def test_generate_from_empty(self):
        """用户未输入宝牌，生成 5+5"""
        user_hand = parse_hand_str("123m456p789s12345z")
        opp_hands = [
            parse_hand_str("111m222p333s44455z"),
            parse_hand_str("555m666p777s88899z"),
            parse_hand_str("999m111p222s33366z"),
        ]
        rng = random.Random(42)

        dora, ura = _generate_dora_indicators(
            user_hand, opp_hands, existing_dora=[], rng=rng
        )

        assert len(dora) == 5
        assert len(ura) == 5
        # 所有值应为合法牌编码
        for t in dora + ura:
            assert 0 <= t < NUM_TILES

    def test_fill_partial_dora(self):
        """用户提供 2 张宝牌，补全至 5 张"""
        user_hand = parse_hand_str("123m456p789s12345z")
        opp_hands = [
            parse_hand_str("111m222p333s44455z"),
            parse_hand_str("555m666p777s88899z"),
            parse_hand_str("999m111p222s33366z"),
        ]
        rng = random.Random(42)

        existing = [0, 8]  # 用户已提供 1m 和 9m
        dora, ura = _generate_dora_indicators(
            user_hand, opp_hands, existing_dora=existing, rng=rng
        )

        assert len(dora) == 5
        assert dora[0] == 0  # 保留用户输入的 1m
        assert dora[1] == 8  # 保留用户输入的 9m
        assert len(ura) == 5

    def test_already_five_dora(self):
        """用户已提供 5 张宝牌，只生成里宝牌"""
        user_hand = parse_hand_str("123m456p789s12345z")
        opp_hands = [
            parse_hand_str("111m222p333s44455z"),
            parse_hand_str("555m666p777s88899z"),
            parse_hand_str("999m111p222s33366z"),
        ]
        rng = random.Random(42)

        existing = [0, 8, 18, 26, 31]  # 5 张
        dora, ura = _generate_dora_indicators(
            user_hand, opp_hands, existing_dora=existing, rng=rng
        )

        assert dora == existing  # 完全保留用户输入
        assert len(ura) == 5

    def test_no_conflict_with_hands(self):
        """生成的宝牌不应与手牌冲突（每种牌最多4张）"""
        user_hand = parse_hand_str("123m456p789s12345z")
        opp_hands = [
            parse_hand_str("111m222p333s44455z"),
            parse_hand_str("555m666p777s88899z"),
            parse_hand_str("999m111p222s33366z"),
        ]
        rng = random.Random(42)

        dora, ura = _generate_dora_indicators(
            user_hand, opp_hands, existing_dora=[], rng=rng
        )

        # 统计所有牌的使用量
        used = [0] * NUM_TILES
        for t in range(NUM_TILES):
            used[t] += user_hand[t]
            for hand in opp_hands:
                used[t] += hand[t]
        for t in dora:
            used[t] += 1
        for t in ura:
            used[t] += 1

        # 每种牌不超过 4 张
        for t in range(NUM_TILES):
            assert used[t] <= 4, (
                f"牌 {tile_name(t)} 使用量 {used[t]} > 4"
            )

    def test_insufficient_pool_raises(self):
        """牌池不足时抛异常（极端情况）"""
        # 构造几乎所有牌都被用完的场景
        user_hand = [0] * NUM_TILES
        # 用户手牌用掉大部分牌
        user_hand[0] = 4; user_hand[1] = 4; user_hand[2] = 4
        opp_hands = [parse_hand_str("444m555p666s777z")]  # 12张

        rng = random.Random(42)
        try:
            dora, ura = _generate_dora_indicators(
                user_hand, opp_hands, existing_dora=[], rng=rng
            )
            # 可能成功也可能失败，取决于剩余牌数
        except ValueError:
            pass  # 预期行为


class TestSimulateGame:
    """主模拟流程测试"""

    def test_basic_simulation(self):
        """基本模拟：1巡应生成 3 张牌河"""
        user_hand = parse_hand_str("123m456p789s12345z")
        rest = [4] * NUM_TILES
        for t in range(NUM_TILES):
            rest[t] -= user_hand[t]

        rivers, combined, full_dora, ura_dora = simulate_game(
            user_hand=user_hand,
            rest=rest,
            max_turns=1,
            seed=42,
        )

        # 1巡 × 4家 = 4张弃牌
        total_discards = sum(combined)
        assert total_discards == 4, f"1巡应生成4张牌河, got {total_discards}"
        assert len(rivers) == 4
        assert len(full_dora) == 5
        assert len(ura_dora) == 5

    def test_zero_turns(self):
        """max_turns=0：无弃牌"""
        user_hand = parse_hand_str("123m456p789s12345z")
        rest = [4] * NUM_TILES
        for t in range(NUM_TILES):
            rest[t] -= user_hand[t]

        rivers, combined, full_dora, ura_dora = simulate_game(
            user_hand=user_hand,
            rest=rest,
            max_turns=0,
            seed=42,
        )

        assert sum(combined) == 0
        for river in rivers:
            assert sum(river) == 0

    def test_combined_equals_sum(self):
        """combined 应等于 3 家牌河之和"""
        user_hand = parse_hand_str("123m456p789s12345z")
        rest = [4] * NUM_TILES
        for t in range(NUM_TILES):
            rest[t] -= user_hand[t]

        rivers, combined, _, _ = simulate_game(
            user_hand=user_hand,
            rest=rest,
            max_turns=3,
            seed=42,
        )

        for t in range(NUM_TILES):
            expected = sum(rivers[i][t] for i in range(4))
            assert combined[t] == expected, (
                f"牌 {tile_name(t)}: combined={combined[t]}, sum={expected}"
            )

    def test_dora_not_in_hands(self):
        """宝牌/里宝牌不应与用户手牌冲突"""
        user_hand = parse_hand_str("123m456p789s12345z")
        rest = [4] * NUM_TILES
        for t in range(NUM_TILES):
            rest[t] -= user_hand[t]

        _, _, full_dora, ura_dora = simulate_game(
            user_hand=user_hand,
            rest=rest,
            max_turns=1,
            seed=42,
        )

        # 检查宝牌/里宝牌的每种牌数与手牌数之和 ≤ 4
        for t in full_dora + ura_dora:
            total_same = sum(1 for d in full_dora if d == t)
            total_same += sum(1 for d in ura_dora if d == t)
            assert total_same + user_hand[t] <= 4, (
                f"牌 {tile_name(t)}: 手牌{user_hand[t]} + 宝牌{total_same} > 4"
            )

    def test_seed_reproducibility(self):
        """相同种子产生相同结果"""
        hand_template = parse_hand_str("123m456p789s12345z")

        def run_sim(seed):
            hand = hand_template.copy()
            rest = [4] * NUM_TILES
            for t in range(NUM_TILES):
                rest[t] -= hand[t]
            return simulate_game(hand, rest, max_turns=2, seed=seed)

        r1 = run_sim(42)
        r2 = run_sim(42)

        rivers1, combined1, dora1, ura1 = r1
        rivers2, combined2, dora2, ura2 = r2

        assert combined1 == combined2
        assert dora1 == dora2
        assert ura1 == ura2
        for i in range(4):
            assert rivers1[i] == rivers2[i]

    def test_wall_exhaustion_handled(self):
        """牌山不足时优雅处理（不崩溃）"""
        # 构造极小的牌山
        user_hand = [0] * NUM_TILES
        # 给用户发13张
        for t in range(13):
            user_hand[t] = 1

        rest = [0] * NUM_TILES
        # 只有刚好够发牌+少量摸牌的牌数
        for t in range(34):
            if user_hand[t] == 0:
                rest[t] = min(4, max(0, 4 - user_hand[t]))

        total_rest = sum(rest)
        if total_rest >= 53:
            # 牌山够用，正常模拟
            rivers, combined, _, _ = simulate_game(
                user_hand=user_hand,
                rest=rest,
                max_turns=5,
                seed=42,
            )
            # 不应崩溃
            assert len(rivers) == 4
        else:
            # 牌山不足，deal_opponent_hands 应抛异常
            try:
                simulate_game(user_hand, rest, max_turns=5, seed=42)
                # 如果没抛异常，也应返回合理结果
            except ValueError:
                pass  # 预期行为


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

"""
命令行交互界面

支持手动输入手牌（文本格式）和通过图像识别输入。
"""

import sys
from typing import List, Optional

from .tile import (
    NUM_TILES, tile_name, parse_hand_str, counts_to_str,
    hand_to_list, dora_indicator_to_dora
)
from .state import GameState
from .search import search_max_score, search_no_pruning
from .simulate import simulate_game


# ── 辅助函数 ──────────────────────────────────────────

def _print_tile_grid(counts: List[int], highlight: Optional[List[int]] = None):
    """以网格形式打印手牌，方便确认"""
    if highlight is None:
        highlight = []

    lines = []
    for suit_name, base in [("万", 0), ("筒", 9), ("索", 18)]:
        tiles = []
        for i in range(9):
            t = base + i
            cnt = counts[t]
            if cnt > 0:
                marker = f"【{tile_name(t)}×{cnt}】" if t in highlight else f"{tile_name(t)}×{cnt}"
                tiles.append(marker)
        if tiles:
            lines.append(f"  {suit_name}: {' '.join(tiles)}")

    # 字牌
    z_tiles = []
    for i in range(7):
        t = 27 + i
        cnt = counts[t]
        if cnt > 0:
            marker = f"【{tile_name(t)}×{cnt}】" if t in highlight else f"{tile_name(t)}×{cnt}"
            z_tiles.append(marker)
    if z_tiles:
        lines.append(f"  字: {' '.join(z_tiles)}")

    print('\n'.join(lines))


def _input_hand_interactive() -> List[int]:
    """交互式输入手牌"""
    print("\n请输入手牌（格式: 123m456p789s12344z 或 1m1m1m...）")
    print("  后缀: m=万, p=筒, s=索, z=字(1东2南3西4北5白6发7中)")
    print("  也可直接输入中文牌名: 东东南南...")

    while True:
        try:
            hand_str = input("手牌> ").strip()
            if not hand_str:
                continue
            counts = parse_hand_str(hand_str)
            total = sum(counts)
            if total not in (13, 14):
                print(f"  错误: 手牌应为13或14张，当前输入为{total}张，请重新输入")
                continue
            print("\n  识别结果:")
            _print_tile_grid(counts)
            confirm = input("\n  确认? (y/n) ").strip().lower()
            if confirm == 'y':
                return counts
        except ValueError as e:
            print(f"  解析错误: {e}")
        except KeyboardInterrupt:
            print("\n  已取消")
            sys.exit(0)


def _input_dora_indicators() -> List[int]:
    """输入宝牌指示牌"""
    print("\n请输入已出现的宝牌指示牌（用逗号分隔，如 5m,9p,白）")
    print("直接回车跳过（无宝牌，将在模拟中随机生成）")

    try:
        dora_str = input("宝牌指示牌> ").strip()
    except KeyboardInterrupt:
        return []

    if not dora_str:
        return []

    indicators = []
    from .tile import parse_tile, NAME_TO_TILE

    for part in dora_str.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            t = parse_tile(part)
            indicators.append(t)
            dora = dora_indicator_to_dora(t)
            print(f"  {tile_name(t)} → 宝牌是 {tile_name(dora)}")
        except ValueError:
            print(f"  无法识别: {part}，已跳过")

    return indicators


def _input_river() -> Optional[List[int]]:
    """输入牌河（所有家已打出的牌）"""
    print("\n请输入牌河中所有已打出的牌（可选，直接回车跳过）")
    print("这是所有玩家已经打出的牌的总和（用于计算剩余牌数）")

    try:
        river_str = input("牌河> ").strip()
    except KeyboardInterrupt:
        return None

    if not river_str:
        return None

    try:
        return parse_hand_str(river_str)
    except ValueError as e:
        print(f"  解析错误: {e}，牌河将忽略")
        return None


# ── 牌局模拟 ──────────────────────────────────────────

def _input_simulation(
    hand: List[int],
    dora_indicators: List[int],
) -> tuple:
    """
    询问用户是否模拟牌局以生成牌河数据。

    若用户选择模拟，则随机发牌给 3 家对手，自动补全宝牌/里宝牌，
    按牌效最优模拟摸打过程，返回生成的牌河和宝牌数据。

    Args:
        hand: 用户手牌计数数组（sum=13）
        dora_indicators: 用户已输入的宝牌指示牌（可能为空或不足5张）

    Returns:
        (river, full_dora, ura_dora) — 均为 Optional
        若用户跳过则返回 (None, None, None)
    """
    print()
    print("是否模拟牌局生成牌河？")
    print("  系统将随机给 3 家对手发牌，按牌效最优模拟摸打过程，")
    print("  自动补全宝牌/里宝牌（各补足至 5 张），生成牌河数据。")
    try:
        choice = input("(y/n, 直接回车跳过): ").strip().lower()
    except KeyboardInterrupt:
        return None, None, None

    if choice != 'y':
        return None, None, None

    # ── 模拟巡目数 ──
    try:
        turns_str = input("模拟巡目数 (直接回车=8): ").strip()
        max_turns = int(turns_str) if turns_str else 8
    except (ValueError, KeyboardInterrupt):
        max_turns = 8

    # ── 随机种子 ──
    try:
        seed_str = input("随机种子 (直接回车=随机): ").strip()
        seed = int(seed_str) if seed_str else None
    except (ValueError, KeyboardInterrupt):
        seed = None

    # ── 构建临时牌山 ──
    # 从 4 张/种开始，减去用户手牌（宝牌由 simulate_game 内部处理）
    temp_rest = [4] * NUM_TILES
    for t in range(NUM_TILES):
        temp_rest[t] -= hand[t]

    # 检查最少牌数：发牌 39 + 王牌区 10 + 首巡摸 4 = 53
    available = sum(temp_rest)
    if available < 53:
        print(f"  错误: 牌山剩余牌数不足 ({available}张)，无法进行有意义的模拟")
        return None, None, None

    # ── 执行模拟 ──
    print(f"\n  正在模拟 {max_turns} 巡...")
    try:
        rivers, combined, full_dora, ura_dora = simulate_game(
            user_hand=hand,
            rest=temp_rest,
            max_turns=max_turns,
            dora_indicators=dora_indicators if dora_indicators else None,
            seed=seed,
        )
    except ValueError as e:
        print(f"  模拟失败: {e}")
        return None, None, None

    # ── 展示结果 ──
    total_discards = sum(combined)
    print(f"\n  === 模拟结果: {max_turns}巡指定, 实际生成 {total_discards} 张牌河 ===")

    # 宝牌/里宝牌
    dora_names = ' '.join(tile_name(t) for t in full_dora)
    ura_names = ' '.join(tile_name(t) for t in ura_dora)
    dora_tiles = ' '.join(
        tile_name(dora_indicator_to_dora(t)) for t in full_dora
    )
    print(f"  宝牌指示牌 ({len(full_dora)}张): {dora_names}")
    print(f"  对应宝牌:                 {dora_tiles}")
    print(f"  里宝牌指示牌 ({len(ura_dora)}张): {ura_names}")

    # 各家牌河
    labels = ["对手1", "对手2", "对手3", "自家"]
    for i in range(4):
        tile_list = []
        for t in range(NUM_TILES):
            tile_list.extend([tile_name(t)] * rivers[i][t])
        river_str = ' '.join(tile_list) if tile_list else '(空)'
        discards = sum(rivers[i])
        print(f"  {labels[i]}牌河 ({discards}张): {river_str}")

    return combined, full_dora, ura_dora


# ── 主入口 ─────────────────────────────────────────────

def run_cli():
    """命令行主入口"""
    print("=" * 60)
    print("  日本麻将 理论最大得点搜索算法")
    print("  Theoretical Max Score Search for Japanese Mahjong")
    print("=" * 60)

    # Step 1: 输入手牌
    hand = _input_hand_interactive()

    # Step 2: 输入宝牌指示牌
    dora_indicators = _input_dora_indicators()

    # Step 3: 模拟牌局生成牌河（可选）
    sim_river, full_dora, ura_dora = _input_simulation(hand, dora_indicators)

    if sim_river is not None:
        # 使用模拟结果
        river = sim_river
        dora_indicators = full_dora
        ura_dora_indicators = ura_dora
        print("\n  (已使用模拟生成的牌河和宝牌，跳过手动输入)")
    else:
        # Step 3b: 手动输入牌河（可选）
        river = _input_river()
        ura_dora_indicators = []

    # Step 4: 输入自风和场风 (用于役牌判定)
    print()
    wind_names = {"1": "东", "2": "南", "3": "西", "4": "北"}
    wind_tiles = {"1": 27, "2": 28, "3": 29, "4": 30}
    try:
        pw = input("自风 (1=东/2=南/3=西/4=北, 直接回车=东): ").strip()
        player_wind = wind_tiles.get(pw, 27)
        rw = input("场风 (1=东/2=南/3=西/4=北, 直接回车=东): ").strip()
        round_wind = wind_tiles.get(rw, 27)
    except KeyboardInterrupt:
        player_wind, round_wind = 27, 27
    print(f"  自风: {wind_names.get(str(player_wind-26), '东')}, 场风: {wind_names.get(str(round_wind-26), '东')}")

    # Step 5: 选择模式
    print()
    print("搜索模式:")
    print("  1. 最大番数 (默认) - 寻找最高役满倍数")
    print("  2. 最快和牌 - 最少摸牌次数内和任意有役手牌")
    try:
        mode_str = input("选择模式 (1/2, 直接回车=1): ").strip()
        mode = "fast" if mode_str == "2" else "max"
    except KeyboardInterrupt:
        mode = "max"
    print(f"  模式: {'最快和牌' if mode == 'fast' else '最大番数'}")

    # Step 6: 输入巡目
    print()
    try:
        turn_str = input("当前巡目 (直接回车=5): ").strip()
        turn = int(turn_str) if turn_str else 5
    except (ValueError, KeyboardInterrupt):
        turn = 5

    max_depth = min(turn, 5)
    print(f"  最大搜索深度: {max_depth} (巡目={turn})")

    # Step 5: 构建 GameState
    state = GameState(
        hand=hand,
        dora_indicators=dora_indicators,
        ura_dora_indicators=ura_dora_indicators,
        turn=turn,
        player_wind=player_wind,
        round_wind=round_wind,
    )

    # 初始化剩余牌
    if river:
        state.init_rest_from_visible(river_counts=river)
    else:
        # 仅从手牌和宝牌指示牌计算
        state.init_rest_from_visible()

    # Step 7: 搜索
    print("\n" + "-" * 40)
    print("正在搜索...")

    result = search_max_score(state, max_depth=max_depth, enable_pruning=True, mode=mode)

    # 无剪枝对比
    nodes_no_prune = search_no_pruning(state, max_depth=max_depth)
    result.nodes_no_prune = nodes_no_prune

    # Step 7: 输出结果
    print("\n" + "=" * 60)
    print("  搜索结果")
    print("=" * 60)

    if result.max_score == 0:
        print("\n  ★ 未找到和牌路径")
        print(f"  (搜索了 {result.nodes_searched} 个节点)")
    elif mode == "fast":
        turns = len([a for a, _ in result.best_path if a == 'draw'])
        print(f"\n  ★ 最快和牌: {turns} 巡内可和")

        if result.final_hand:
            tiles = []
            for t, c in enumerate(result.final_hand):
                if c > 0:
                    tiles.append(f"{tile_name(t)}×{c}")
            print(f"\n  【和牌牌型】")
            print(f"  {'  '.join(tiles)}")

        print(f"\n  【达成路径】")
        for i, (action, tile) in enumerate(result.best_path, 1):
            print(f"    {i}. {action} → {tile_name(tile)}")
    else:
        score_str = f"{result.max_score}倍役满 ({result.max_score * 13}番)"
        print(f"\n  ★ 理论最大番数: {score_str}")

        if result.final_hand:
            tiles = []
            for t, c in enumerate(result.final_hand):
                if c > 0:
                    tiles.append(f"{tile_name(t)}×{c}")
            print(f"\n  【和牌牌型】")
            print(f"  {'  '.join(tiles)}")

        if result.yaku_details:
            print(f"\n  【役种明细】")
            for d in result.yaku_details:
                print(f"    {d}")

        print(f"\n  【达成路径】")
        for i, (action, tile) in enumerate(result.best_path, 1):
            print(f"    {i}. {action} → {tile_name(tile)}")

    print(f"\n  搜索统计:")
    print(f"    有剪枝节点数: {result.nodes_searched}")
    print(f"    无剪枝节点数: {result.nodes_no_prune}")
    print(f"    剪枝节点数:   {result.nodes_pruned}")
    if result.nodes_no_prune > 0:
        prune_rate = (1 - result.nodes_searched / result.nodes_no_prune) * 100
        print(f"    剪枝率:       {prune_rate:.1f}%")
    print(f"    耗时:         {result.elapsed_ms:.2f}ms")
    print()

    return result


if __name__ == "__main__":
    run_cli()

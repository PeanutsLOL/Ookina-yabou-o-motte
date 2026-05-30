"""
牌局状态数据结构

定义 GameState, Meld, SearchNode, SearchResult 等核心数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .tile import tile_name

# 牌编码常量
NUM_TILES = 34


@dataclass
class Meld:
    """副露（鸣牌组）

    Attributes:
        meld_type: "pon"(碰), "kan"(明杠), "chi"(吃), "ankan"(暗杠), "kakan"(加杠)
        tiles: 副露中的牌编码列表 (3张碰/吃, 4张杠)
        from_player: 从哪位玩家鸣的
                      0=自家(暗杠), 1=下家, 2=对家, 3=上家
        called_tile: 被鸣的那张牌编码 (吃/碰/明杠时)
        is_open: 是否为明露 (暗杠为 False)
    """
    meld_type: str
    tiles: List[int]
    from_player: int
    called_tile: Optional[int] = None
    is_open: bool = True

    def __post_init__(self):
        """验证副露合法性"""
        valid_types = {"pon", "kan", "chi", "ankan", "kakan"}
        if self.meld_type not in valid_types:
            raise ValueError(f"非法的副露类型: {self.meld_type}")

        if self.meld_type in ("pon", "chi"):
            if len(self.tiles) != 3:
                raise ValueError(f"{self.meld_type} 必须有3张牌")
        elif self.meld_type in ("kan", "ankan", "kakan"):
            if len(self.tiles) != 4:
                raise ValueError(f"{self.meld_type} 必须有4张牌")

        if self.meld_type == "ankan":
            self.is_open = False

    def tiles_count(self) -> int:
        """返回副露中的牌数（用于手牌数计算）"""
        return len(self.tiles)


@dataclass
class GameState:
    """牌局状态

    Attributes:
        hand: 长度34的数组，手牌中每种牌的数量 (0~4)
        melds: 副露列表
        rest: 长度34的数组，每种牌在牌山中剩余的数量 (0~4)
              初始值 = 4 - 手牌中 - 副露中 - 宝牌指示牌 - 牌河中
        dora_indicators: 表宝牌指示牌列表
        ura_dora_indicators: 里宝牌指示牌列表 (立直后可用)
        turn: 当前巡目 (0-based)
        total_turns: 总局数 (通常 17 巡)
        player_wind: 玩家的自风 (用于役牌判定)
        round_wind: 场风 (用于役牌判定)
    """
    hand: List[int] = field(default_factory=lambda: [0] * NUM_TILES)
    melds: List[Meld] = field(default_factory=list)
    rest: List[int] = field(default_factory=lambda: [4] * NUM_TILES)
    dora_indicators: List[int] = field(default_factory=list)
    ura_dora_indicators: List[int] = field(default_factory=list)
    turn: int = 0
    total_turns: int = 17
    player_wind: int = 27  # 默认东 (27=东)
    round_wind: int = 27    # 默认东

    @property
    def hand_size(self) -> int:
        """当前手牌数量 (0~14)"""
        return sum(self.hand)

    @property
    def meld_count(self) -> int:
        """副露组数"""
        return len(self.melds)

    @property
    def is_menzen(self) -> bool:
        """是否为门清状态 (无任何明露)"""
        return all(not m.is_open for m in self.melds)

    @property
    def is_open(self) -> bool:
        """是否有明露"""
        return any(m.is_open for m in self.melds)

    def copy(self) -> "GameState":
        """深拷贝当前状态"""
        return GameState(
            hand=self.hand.copy(),
            melds=[Meld(
                meld_type=m.meld_type,
                tiles=m.tiles.copy(),
                from_player=m.from_player,
                called_tile=m.called_tile,
                is_open=m.is_open
            ) for m in self.melds],
            rest=self.rest.copy(),
            dora_indicators=self.dora_indicators.copy(),
            ura_dora_indicators=self.ura_dora_indicators.copy(),
            turn=self.turn,
            total_turns=self.total_turns,
            player_wind=self.player_wind,
            round_wind=self.round_wind,
        )

    def add_to_hand(self, tile: int) -> None:
        """摸入一张牌"""
        if self.hand[tile] >= 4:
            raise ValueError(f"牌 {tile} 已有4张，不能再摸入")
        if self.rest[tile] <= 0:
            raise ValueError(f"牌 {tile} 已无剩余")
        self.hand[tile] += 1
        self.rest[tile] -= 1

    def remove_from_hand(self, tile: int) -> None:
        """打出一张牌"""
        if self.hand[tile] <= 0:
            raise ValueError(f"手牌中没有牌 {tile}")
        self.hand[tile] -= 1
        self.rest[tile] += 1

    def add_meld(self, meld: Meld) -> None:
        """添加副露，从手牌中移除对应牌"""
        for t in meld.tiles:
            if meld.meld_type == "chi" and t == meld.called_tile:
                continue  # 吃的那张牌来自牌河，不在手牌中
            if self.hand[t] <= 0:
                raise ValueError(f"手牌中没有足够的牌 {t} 来组成副露")
            self.hand[t] -= 1

        # 副露中的牌从剩余计数中扣除（如果来自手牌）
        for t in meld.tiles:
            if meld.meld_type == "chi" and t == meld.called_tile:
                self.rest[t] -= 1  # 从牌河拿的
            # 手牌的已在 hand 中扣除，rest 不变（本来就是不可用的）

        self.melds.append(meld)

    def init_rest_from_visible(self,
                                river_counts: List[int] = None,
                                other_melds: List[List[int]] = None) -> None:
        """
        根据所有已见牌初始化 rest 数组。
        已见牌 = 手牌 + 副露 + 宝牌指示牌 + 牌河 + 其他家副露

        Args:
            river_counts: 所有家牌河中每种牌的数量 (含自家已打出)
            other_melds: 其他家的副露 (每个元素是牌编码列表)
        """
        # 初始每种牌4张
        self.rest = [4] * NUM_TILES

        # 减去手牌
        for t in range(NUM_TILES):
            self.rest[t] -= self.hand[t]

        # 减去自家副露
        for m in self.melds:
            for t in m.tiles:
                self.rest[t] -= 1

        # 减去宝牌指示牌
        for t in self.dora_indicators:
            self.rest[t] -= 1
        for t in self.ura_dora_indicators:
            self.rest[t] -= 1

        # 减去牌河
        if river_counts:
            for t in range(NUM_TILES):
                self.rest[t] -= river_counts[t]

        # 减去其他家副露
        if other_melds:
            for meld_tiles in other_melds:
                for t in meld_tiles:
                    self.rest[t] -= 1

        # 验证合法性
        for t in range(NUM_TILES):
            if self.rest[t] < 0:
                raise ValueError(
                    f"牌 {tile_name(t)} 剩余数量为负 ({self.rest[t]})，请检查输入"
                )
            if self.rest[t] > 4:
                self.rest[t] = 4  # 安全截断


@dataclass
class SearchNode:
    """搜索树节点

    Attributes:
        state: 当前牌局状态
        path: 到达该节点的路径 [(动作, 牌), ...]
              动作类型: 'draw'(摸牌), 'pon'(碰), 'kan'(杠), 'chi'(吃), 'ankan'(暗杠)
        score: 当前路径的番数 (若已和牌)
        depth: 当前搜索深度 (已摸牌次数)
    """
    state: GameState
    path: List[Tuple[str, int]] = field(default_factory=list)
    score: int = 0
    depth: int = 0


@dataclass
class SearchResult:
    """搜索结果

    Attributes:
        max_score: 理论最大番数 (役满倍数, 1倍=13番)
        best_path: 最优路径 [(动作, 牌), ...]
        nodes_searched: 实际搜索节点数
        nodes_pruned: 被剪枝节点数
        nodes_no_prune: 无剪枝时的节点数 (对比用, 需额外运行)
        elapsed_ms: 搜索耗时 (毫秒)
    """
    max_score: int = 0
    best_path: List[Tuple[str, int]] = field(default_factory=list)
    nodes_searched: int = 0
    nodes_pruned: int = 0
    nodes_no_prune: int = -1  # -1 表示未测试
    elapsed_ms: float = 0.0

    def summary(self) -> str:
        """生成结果摘要"""
        if self.max_score == 0:
            return "未找到役满路径"

        yakuman_count = self.max_score
        if yakuman_count == 1:
            score_str = "1倍役满 (13番)"
        elif yakuman_count == 2:
            score_str = "双倍役满 (26番)"
        elif yakuman_count == 3:
            score_str = "三倍役满 (39番)"
        else:
            score_str = f"{yakuman_count}倍役满 ({yakuman_count * 13}番)"

        path_str = " → ".join(
            f"{action}({tile_name(tile)})"
            for action, tile in self.best_path
        )

        return (
            f"理论最大番数: {score_str}\n"
            f"达成路径: {path_str}\n"
            f"搜索节点: {self.nodes_searched} (剪枝: {self.nodes_pruned})\n"
            f"耗时: {self.elapsed_ms:.2f}ms"
        )

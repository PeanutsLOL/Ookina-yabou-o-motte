# 🀗 Maj — 日本麻将理论最大得点搜索

给定任意日本麻将牌局状态，通过确定性 DFS + 分支限界搜索，在有限摸牌轮数内找到可达到的**理论最高得分**（役满倍数 + 累计役满）。同时支持"最速和牌"模式，以最少摸牌轮数实现任意有效和牌。

## 快速开始

```bash
# 交互式命令行
python main.py

# 运行全部测试
python -m pytest tests/ -v
```

**依赖**：纯 Python 3，无第三方运行时依赖。

测试依赖 pytest (需单独安装):

```bash
pip install pytest
python -m pytest tests/ -v
```

## 使用示例

```python
from src.tile import parse_hand_str
from src.state import GameState
from src.search import search_max_score

# 手牌: 国士无双13面听
counts = parse_hand_str("19m19p19s1234567z")
state = GameState(hand=counts)
state.init_rest_from_visible()          # 初始化牌山 (每种牌4张 − 已见)

result = search_max_score(state, max_depth=5, mode="max")
print(result.summary())
# 输出: 国士无双(十三面) 2倍役满, reached in 0 draws
```

## 牌编码

牌使用整数 0–33 编码，手牌始终表示为 `List[int]` 长度 34 的**计数数组**：

| 编码 | 牌种 |
|:---:|------|
| 0–8 | 1m–9m (万) |
| 9–17 | 1p–9p (筒) |
| 18–26 | 1s–9s (索) |
| 27–33 | 东南西北白发中 (字牌) |

```python
parse_hand_str("123m456p789s东东东白白")  # → List[int] len 34
```

## 两种搜索模式

| | `mode="max"` (最大得点) | `mode="fast"` (最速和牌) |
|---|---|---|
| 目标 | 最高役满倍数 | 任意有效和牌, 最少轮数 |
| 状态缓存 | ✅ | ❌ |
| 剪枝 | `optimistic_bonus()` | 无 |
| 鸣牌 | 不支持 | pon / chi / kan |
| 和牌判定 | `calculate_score()` | `has_any_yaku()` |

## 架构

```
main.py → src/cli.py (交互式 CLI)
              ↓
       src/search.py  (核心: DFS + 分支限界)
       ├── state.py       GameState / Meld / SearchResult 数据结构
       ├── decompose.py   手牌拆分 (4面子+1雀头), 听牌判定, 向听数
       ├── pruning.py     optimistic_bonus() — 各役满"还差几张"乐观估算
       ├── meld.py        合法鸣牌生成 (pon/chi/kan/ankan/kakan)
       ├── tenpai.py      听牌检测 (感知 rest[] 剩余牌)
       └── yaku/          役满 + 普通役种判定
```

### 搜索流程

每轮: 13 张 → 摸牌 (14) → 和牌检查 → 弃牌 (13) → 递归

- **摸牌剪枝**: 只摸对役满有贡献的牌 (如字牌→字一色、绿牌→绿一色)
- **弃牌排序**: 多余牌 → 孤张 → 非主花色 → 主花色单张 (上限6候选)
- **状态缓存**: `(hand_tuple, depth)` 去重，避免重复搜索

## 支持役种

### 役满

| 役满 | 函数 | 双倍条件 |
|---|---|---|
| 国士无双 | `check_kokushi` | 13面听 |
| 四暗刻 | `check_suuankou` | 单骑听牌 |
| 大三元 | `check_daisangen` | — |
| 九莲宝灯 | `check_chuuren` | 纯正9面听 |
| 大四喜 | `check_daisuushi` | 始终2× |
| 小四喜 | `check_shousuushi` | — |
| 字一色 | `check_tsuuiisou` | — |
| 绿一色 | `check_ryuuiisou` | — |
| 清老头 | `check_chinroutou` | — |
| 四杠子 | `check_suukantsu` | — |
| 累计役满 | `calculate_regular_han` | 普通番≥13 |

### 普通役种 (45项)

**6翻**: 清一色

**3翻**: 混一色、纯全带幺九、二盃口

**2翻**: 七对子、对对和、三暗刻、三色同刻、三色同顺、一气通贯、混全带幺九、混老头、小三元、三杠子、双立直

**1翻**: 立直、门前清自摸和、断幺九、平和、一盃口、役牌(三元+自风+场风)

## 开发

```bash
# 全部测试
python -m pytest tests/ -v

# 单个测试文件
python -m pytest tests/test_yaku.py -v

# 单个用例
python -m pytest tests/test_yaku.py::TestKokushi::test_kokushi_normal -v
```

测试文件:

| 文件 | 覆盖范围 |
|---|---|
| `tests/test_tile.py` | 牌编码、分类、解析 |
| `tests/test_decompose.py` | 手牌拆分、听牌判定 |
| `tests/test_yaku.py` | 役满判定 + 复合役满 |
| `tests/test_search.py` | 搜索集成测试 |
| `tests/test_simulate.py` | 牌局模拟模块 |

## 关键设计决策

- **乐观剪枝**: `optimistic_bonus()` 故意宽松——宁可保留不可能的分支，也不能错误剪掉真正的最优解
- **役满互斥**: 国士/九莲与门前役满互斥；大四喜+大三元=7刻位>4槽位→不可能
- **副露感知**: fast模式下手牌大小 = `14 − 2×num_melds`，和牌判定随副露数变化
- **计数组编码**: 牌始终用 `List[int]` 长度34 的计数数组，不用平铺列表

## 参考

- [雀吉 Wiki — 役种表](https://wiki.queji.com/mediawiki/index.php/%E5%BD%B9%E7%A8%AE%E8%A1%A8)
- [Wikipedia — 日本麻将和牌牌型列表](https://zh.wikipedia.org/zh-cn/%E6%97%A5%E6%9C%AC%E9%BA%BB%E5%B0%87%E7%9A%84%E5%92%8C%E7%89%8C%E7%89%8C%E5%9E%8B%E5%88%97%E8%A1%A8)

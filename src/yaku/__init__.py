"""
役满判定模块

每种役满有独立的判定函数，返回役满倍数(0/1/2)。
役满之间可以累加（复合役满），但需检查互斥关系。

役满倍数约定:
  0 = 不满足
  1 = 满足 (1倍役满)
  2 = 双倍 (例如国士十三面、四暗刻单骑、纯正九莲、大四喜)

参考: https://wiki.queji.com/mediawiki/index.php/%E5%BD%B9%E7%A8%AE%E8%A1%A8
"""
from .kokushi import check_kokushi
from .suuankou import check_suuankou
from .daisangen import check_daisangen, check_shousangen
from .chuuren import check_chuuren
from .daisuushi import check_daisuushi, check_shousuushi
from .tsuuiisou import check_tsuuiisou
from .ryuuiisou import check_ryuuiisou
from .chinroutou import check_chinroutou
from .suukantsu import check_suukantsu

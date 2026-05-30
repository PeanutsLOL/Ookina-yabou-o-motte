"""
役满判定模块

每种役满有独立的判定函数，返回役满倍数(0/1/2)。
役满之间可以累加（复合役满），但需检查互斥关系。

役满倍数约定:
  0 = 不满足
  1 = 满足 (1倍役满)
  2 = 双倍 (例如国士十三面、四暗刻单骑、纯正九莲)
"""
from .kokushi import check_kokushi
from .suuankou import check_suuankou
from .daisangen import check_daisangen
from .chuuren import check_chuuren

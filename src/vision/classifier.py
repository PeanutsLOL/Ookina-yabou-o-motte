"""
图像识别模块 - 牌面分类

通过模板匹配或 CNN 将单张牌图像分类为牌编码 (0~33)。
"""

import numpy as np
from typing import List, Tuple, Optional
import os


# 默认模板目录
DEFAULT_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "templates"
)


class TileClassifier:
    """
    牌面分类器。

    支持两种模式:
    1. 模板匹配 (template matching)
    2. CNN 分类 (暂未实现)
    """

    def __init__(self, method: str = "template",
                 template_dir: str = None):
        """
        Args:
            method: "template" 或 "cnn"
            template_dir: 模板图片目录路径
        """
        self.method = method
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.templates: dict[int, np.ndarray] = {}  # tile_id → template image
        self._loaded = False

    def load_templates(self) -> bool:
        """
        加载模板图像。

        从 data/templates/ 目录加载所有34种牌的模板。
        模板文件命名: manzu/1m.png, pinzu/5p.png, souzu/9s.png, jihai/ton.png 等

        Returns:
            True 如果加载成功
        """
        from ..tile import TILE_NAMES

        self.templates = {}
        loaded_count = 0

        for tile_id in range(34):
            name = TILE_NAMES[tile_id]
            template_path = self._get_template_path(tile_id)
            if template_path and os.path.exists(template_path):
                try:
                    import cv2
                    img = cv2.imread(template_path, cv2.IMREAD_COLOR)
                    if img is not None:
                        self.templates[tile_id] = img
                        loaded_count += 1
                except ImportError:
                    pass

        self._loaded = loaded_count >= 30  # 至少加载30种
        return self._loaded

    def _get_template_path(self, tile_id: int) -> Optional[str]:
        """获取指定牌的模板文件路径"""
        from ..tile import suit, num, TILE_NAMES

        s = suit(tile_id)
        if s == 0:  # 万
            folder = "manzu"
            filename = f"{num(tile_id)}m.png"
        elif s == 1:  # 筒
            folder = "pinzu"
            filename = f"{num(tile_id)}p.png"
        elif s == 2:  # 索
            folder = "souzu"
            filename = f"{num(tile_id)}s.png"
        else:  # 字
            folder = "jihai"
            # 字牌文件名映射
            wind_names = {27: "ton", 28: "nan", 29: "shaa", 30: "pei"}
            dragon_names = {31: "haku", 32: "hatsu", 33: "chun"}
            if tile_id in wind_names:
                filename = f"{wind_names[tile_id]}.png"
            else:
                filename = f"{dragon_names[tile_id]}.png"

        return os.path.join(self.template_dir, folder, filename)

    def classify(self, tile_image: np.ndarray) -> Tuple[int, float]:
        """
        对单张牌图像进行分类。

        Args:
            tile_image: 单张牌的 BGR 图像

        Returns:
            (tile_id, confidence)
            tile_id = -1 表示无法识别
            confidence = 匹配置信度 (0~1)
        """
        if self.method == "template":
            return self._classify_template(tile_image)
        else:
            raise ValueError(f"不支持的方法: {self.method}")

    def _classify_template(self, tile_image: np.ndarray) -> Tuple[int, float]:
        """模板匹配分类"""
        import cv2

        if not self._loaded:
            self.load_templates()

        if not self.templates:
            return -1, 0.0

        # 将输入图像转为灰度
        if len(tile_image.shape) == 3:
            tile_gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
        else:
            tile_gray = tile_image

        best_tile = -1
        best_score = -1.0

        for tile_id, template in self.templates.items():
            # 确保模板和输入大小相近
            h, w = tile_gray.shape
            template_resized = cv2.resize(
                template, (w, h),
                interpolation=cv2.INTER_AREA
            )
            if len(template_resized.shape) == 3:
                template_gray = cv2.cvtColor(template_resized, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template_resized

            # 归一化互相关
            result = cv2.matchTemplate(
                tile_gray, template_gray, cv2.TM_CCOEFF_NORMED
            )
            score = float(np.max(result))

            if score > best_score:
                best_score = score
                best_tile = tile_id

        # 置信度阈值
        THRESHOLD = 0.6
        if best_score < THRESHOLD:
            return -1, best_score

        return best_tile, best_score

    def classify_hand(
        self,
        tile_images: List[np.ndarray]
    ) -> Tuple[List[int], List[float]]:
        """
        批量分类手牌中的多张牌。

        Args:
            tile_images: 每张牌的图像列表

        Returns:
            (tile_ids, confidences)
        """
        tiles = []
        confs = []
        for img in tile_images:
            t, c = self.classify(img)
            tiles.append(t)
            confs.append(c)
        return tiles, confs

    def get_template_count(self) -> int:
        """返回已加载的模板数量"""
        return len(self.templates) if self._loaded else 0

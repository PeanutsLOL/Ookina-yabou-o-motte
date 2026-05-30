"""
图像识别模块 - 牌区域检测

从雀魂截图中定位手牌区域和单张牌的位置。
"""

import numpy as np
from typing import List, Tuple, Optional


def detect_hand_region(
    image: np.ndarray,
    method: str = "auto"
) -> Optional[Tuple[int, int, int, int]]:
    """
    从全屏/手牌截图中检测手牌区域。

    Args:
        image: BGR 图像 (H, W, 3)
        method: "auto" 自动检测 / "manual" 手动框选 / "ratio" 按比例分割

    Returns:
        (x, y, w, h) 手牌区域坐标，或 None
    """
    # TODO: 实现雀魂手牌区域检测
    # 雀魂手牌通常在屏幕底部约 85-95% 高度位置
    # 颜色特征: 深色背景上的亮色牌面
    if method == "ratio":
        h, w = image.shape[:2]
        # 手牌区域: 底部 15% 高度, 中间 80% 宽度
        x = int(w * 0.1)
        y = int(h * 0.85)
        bw = int(w * 0.8)
        bh = int(h * 0.12)
        return (x, y, bw, bh)

    # "auto": 基于颜色和边缘的检测
    # 占位实现 — 需要用户提供雀魂截图进行调参
    h, w = image.shape[:2]
    return (int(w * 0.1), int(h * 0.85), int(w * 0.8), int(h * 0.12))


def split_tiles_from_region(
    image: np.ndarray,
    tile_count: int = 13
) -> List[np.ndarray]:
    """
    从手牌区域图像中等距切分出每张牌的图像。

    Args:
        image: 手牌区域图像 (BGR)
        tile_count: 预期的牌数量 (通常13)

    Returns:
        每张牌的图像切片列表
    """
    h, w = image.shape[:2]

    # 等距切分（雀魂手牌间距均匀）
    tile_width = w // tile_count
    tiles = []

    for i in range(tile_count):
        x = i * tile_width
        # 留一些边距
        margin = int(tile_width * 0.05)
        tile_img = image[:, x + margin: x + tile_width - margin]
        tiles.append(tile_img)

    return tiles


def detect_tiles_by_contours(
    image: np.ndarray
) -> List[Tuple[int, int, int, int]]:
    """
    通过轮廓检测定位每张牌的位置。

    使用边缘检测 + 轮廓查找来定位牌面。

    Args:
        image: 手牌区域灰度图或 BGR 图

    Returns:
        每张牌的边界框 [(x, y, w, h), ...]
    """
    import cv2

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 自适应二值化
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # 查找轮廓
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # 按 x 坐标排序
    rects = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # 过滤太小/太大的区域
        if w > 20 and h > 40 and w < image.shape[1] // 3:
            rects.append((x, y, w, h))

    rects.sort(key=lambda r: r[0])  # 从左到右排序
    return rects

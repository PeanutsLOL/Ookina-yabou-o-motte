"""
图像识别模块 - 图像预处理

去噪、尺寸归一化、颜色标准化等。
"""

import numpy as np
from typing import Tuple


def preprocess_for_detection(image: np.ndarray) -> np.ndarray:
    """
    预处理图像用于牌区域检测。

    - 转灰度
    - 高斯模糊去噪
    - 自适应直方图均衡化增强对比度
    """
    import cv2

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # CLAHE 对比度增强
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)

    return enhanced


def preprocess_for_classification(
    tile_image: np.ndarray,
    target_size: Tuple[int, int] = (64, 96)
) -> np.ndarray:
    """
    预处理单张牌图像用于分类。

    - 缩放到统一尺寸
    - 边缘增强
    - 颜色归一化
    """
    import cv2

    # 缩放
    resized = cv2.resize(tile_image, target_size, interpolation=cv2.INTER_AREA)

    # 转灰度（如果需要）
    if len(resized.shape) == 3:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized

    # 归一化到 0~255
    normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

    return normalized


def normalize_screenshot(image: np.ndarray,
                          target_width: int = 1920) -> np.ndarray:
    """
    将不同分辨率的截图标准化到目标宽度。
    保持宽高比。
    """
    import cv2

    h, w = image.shape[:2]
    if w == target_width:
        return image

    scale = target_width / w
    new_h = int(h * scale)
    return cv2.resize(image, (target_width, new_h), interpolation=cv2.INTER_LANCZOS4)

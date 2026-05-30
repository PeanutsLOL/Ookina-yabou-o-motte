"""
图像识别模块 - 模板管理

负责模板图像的管理: 添加、删除、列出模板。
"""


def list_templates(template_dir: str) -> dict:
    """列出所有已安装的模板"""
    import os
    from ..tile import TILE_NAMES

    result = {}
    for tile_id in range(34):
        name = TILE_NAMES[tile_id]
        # 查找模板文件
        from .classifier import TileClassifier
        classifier = TileClassifier(template_dir=template_dir)
        path = classifier._get_template_path(tile_id)
        result[name] = {
            'tile_id': tile_id,
            'path': path,
            'exists': os.path.exists(path) if path else False,
        }
    return result


def add_template(tile_id: int, image_path: str, template_dir: str) -> bool:
    """添加一张模板图像"""
    import os
    import shutil
    from .classifier import TileClassifier

    if not os.path.exists(image_path):
        return False

    classifier = TileClassifier(template_dir=template_dir)
    target = classifier._get_template_path(tile_id)
    if target is None:
        return False

    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy(image_path, target)
    return True

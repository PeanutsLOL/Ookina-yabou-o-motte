"""
入口文件: 日本麻将理论最大得点搜索算法

用法:
  python main.py          # 交互式命令行
  python -m src.cli       # 等价方式
"""

from src.cli import run_cli

if __name__ == "__main__":
    run_cli()

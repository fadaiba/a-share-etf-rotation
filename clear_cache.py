#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理数据缓存脚本
"""

import os
import shutil
from pathlib import Path

def clear_cache():
    """清理data/cache目录中的所有缓存文件"""
    cache_dir = Path("data/cache")

    if not cache_dir.exists():
        print("缓存目录不存在，无需清理")
        return

    # 统计缓存文件
    cache_files = list(cache_dir.glob("*.pkl"))
    total_size = sum(f.stat().st_size for f in cache_files)

    print(f"发现 {len(cache_files)} 个缓存文件，总大小: {total_size / 1024 / 1024:.2f} MB")

    # 删除缓存
    for file in cache_files:
        file.unlink()
        print(f"  已删除: {file.name}")

    print(f"✓ 缓存清理完成！")

if __name__ == "__main__":
    clear_cache()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据加载测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.loader import create_data_loader
import yaml

def test_data_loading():
    """测试数据加载"""
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print("配置加载成功")
    print(f"ETF池: {config['etf_pool']}")
    print(f"时间范围: {config['backtest']['start_date']} 到 {config['backtest']['end_date']}")

    # 创建数据加载器
    data_loader = create_data_loader()

    # 测试加载一个ETF
    symbol = "510300"
    start_date = "2020-01-01"
    end_date = "2020-01-31"

    print(f"\n测试加载 {symbol} 从 {start_date} 到 {end_date}")
    try:
        df = data_loader.get_etf_price(symbol, start_date, end_date)
        print(f"加载成功，数据形状: {df.shape}")
        print(f"数据列: {df.columns.tolist()}")
        print(f"数据日期范围: {df.index.min()} 到 {df.index.max()}")
        print(f"前5行数据:\n{df.head()}")
    except Exception as e:
        print(f"加载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_loading()
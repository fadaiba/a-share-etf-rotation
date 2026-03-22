#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股ETF量化交易系统 - 实盘主程序
"""

import sys
import os
import time
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.xtquant_api import XTQuantAPI, LiveTrader
from strategy.portfolio import PortfolioManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/live_trading.log'),
        logging.StreamHandler()
    ]
)

def strategy_function():
    """实盘策略函数"""
    # 这里应该实现完整的实盘策略逻辑
    # 暂时返回等权重配置

    portfolio_manager = PortfolioManager()

    # 简化的ETF选择
    selected_etfs = ["510300", "510500", "159915"]  # 示例

    # 等权重
    weights = {etf: 1.0 / len(selected_etfs) for etf in selected_etfs}

    return weights

def run_live_trading():
    """运行实盘交易"""
    print("Starting live trading...")

    # 初始化API
    api = XTQuantAPI()

    # 初始化交易器
    trader = LiveTrader(api)

    # 连接
    if not api.connect():
        print("Failed to connect to trading API")
        return

    print("Connected to trading API")

    try:
        # 运行实盘交易循环
        trader.run_live_trading(strategy_function)

    except KeyboardInterrupt:
        print("Live trading stopped by user")
    except Exception as e:
        logging.error(f"Live trading error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        api.disconnect()
        print("Disconnected from trading API")

if __name__ == "__main__":
    try:
        run_live_trading()
    except Exception as e:
        print(f"Live trading failed: {e}")
        import traceback
        traceback.print_exc()
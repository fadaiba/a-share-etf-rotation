#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据类型修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_portfolio_rebalance():
    """测试投资组合调仓功能"""
    print("Testing portfolio rebalance...")

    try:
        from strategy.portfolio import PortfolioManager

        # 创建PortfolioManager实例
        pm = PortfolioManager()

        # 模拟账户持仓（Account.positions格式）
        current_positions = {
            '510300': {'shares': 1000, 'avg_price': 3.5},
            '510500': {'shares': 500, 'avg_price': 2.8}
        }

        # 目标权重
        target_weights = {
            '510300': 0.6,
            '510500': 0.4
        }

        # 当前价格
        current_prices = {
            '510300': 3.6,
            '510500': 2.9
        }

        total_value = 5000.0

        # 测试调仓计算
        trades = pm.rebalance_portfolio(current_positions, target_weights, current_prices, total_value)

        print("✓ Portfolio rebalance successful")
        print(f"Generated {len(trades)} trades:")
        for etf, trade in trades.items():
            print(f"  {etf}: {trade['action']} {trade['shares']:.0f} shares (${trade['value']:.2f})")

        return True

    except Exception as e:
        print(f"✗ Portfolio rebalance error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_strategy_function():
    """测试策略函数"""
    print("\nTesting strategy function...")

    try:
        from main_backtest import strategy_function

        # 模拟输入
        current_date = "2020-02-01"
        current_positions = {
            '510300': {'shares': 1000, 'avg_price': 3.5}
        }
        current_prices = {
            '510300': 3.6,
            '510500': 2.9
        }
        total_value = 3600.0

        # 调用策略函数（简化模式）
        trades = strategy_function(current_date, current_positions, current_prices, total_value)

        print("✓ Strategy function successful")
        print(f"Generated {len(trades)} trades")

        return True

    except Exception as e:
        print(f"✗ Strategy function error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_portfolio_rebalance()
    success2 = test_strategy_function()

    if success1 and success2:
        print("\n🎉 All tests passed! Data type issue resolved.")
    else:
        print("\n❌ Some tests failed.")
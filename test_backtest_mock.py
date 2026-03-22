#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立回测测试脚本 - 强制使用模拟数据
"""

import sys
import os
import yaml
import pandas as pd
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.loader import MockDataLoader, CachedDataLoader
from strategy.portfolio import PortfolioManager
from backtest.engine import BacktestEngine
from backtest.metrics import PerformanceMetrics

def load_config():
    """加载配置"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def prepare_mock_data(config):
    """准备模拟数据"""
    print("Loading mock data...")

    data_loader = CachedDataLoader(MockDataLoader())

    etf_pool = config['etf_pool']
    start_date = config['backtest']['start_date']
    end_date = config['backtest']['end_date']

    # 加载ETF数据
    price_data = {}
    for symbol in etf_pool:
        print(f"Loading {symbol}...")
        df = data_loader.get_etf_price(symbol, start_date, end_date)
        if not df.empty:
            price_data[symbol] = df
            print(f"  Loaded {len(df)} days of data")
        else:
            print(f"  No data for {symbol}")

    # 加载指数数据（用于市场过滤）
    index_symbol = config['risk']['market_filter']['index']
    index_df = data_loader.get_index_price(index_symbol, start_date, end_date)

    print(f"Loaded {len(price_data)} ETFs and index data")
    return price_data, index_df

def strategy_function(current_date, current_positions, current_prices, total_value, price_data=None, index_df=None):
    """策略函数 - 完整的量化策略实现"""
    try:
        config = load_config()
        portfolio_manager = PortfolioManager()

        # 如果没有提供历史数据，使用简化逻辑
        if price_data is None or index_df is None:
            # 简化的ETF选择（实际应该基于历史数据）
            selected_etfs = config['etf_pool'][:3]  # 选择前3个

            # 计算权重（等权重）
            weights = {etf: 1.0 / len(selected_etfs) for etf in selected_etfs}
        else:
            # 完整的策略流程
            # 1. ETF选择
            selected_etfs = portfolio_manager.select_etfs(config['etf_pool'], price_data)

            # 2. 计算权重
            weights = portfolio_manager.calculate_weights(selected_etfs, price_data, index_df)

        # 3. 计算调仓交易
        trades = portfolio_manager.rebalance_portfolio(
            current_positions, weights, current_prices, total_value
        )

        # 4. 应用交易限制
        trades = portfolio_manager.apply_trading_restrictions(trades, price_data or {})

        return trades

    except Exception as e:
        print(f"Strategy error: {e}")
        return {}

def run_backtest():
    """运行回测"""
    print("Starting backtest with mock data...")

    config = load_config()

    # 准备模拟数据
    price_data, index_df = prepare_mock_data(config)

    if not price_data:
        print("No data available, exiting")
        return

    # 创建回测引擎
    engine = BacktestEngine()

    # 运行回测
    start_date = config['backtest']['start_date']
    end_date = config['backtest']['end_date']
    initial_cash = 1000000.0

    account = engine.run_backtest(
        strategy_function, start_date, end_date, initial_cash, price_data, index_df
    )

    # 保存结果
    engine.save_results(account, "backtest_results_mock.json")

    # 计算绩效指标
    metrics = PerformanceMetrics(account.history)

    # 生成报告
    report = metrics.generate_report()

    print("\n=== 回测结果 (模拟数据) ===")
    for category, indicators in report.items():
        print(f"\n{category}:")
        for key, value in indicators.items():
            print(f"  {key}: {value}")

    # 保存详细报告
    with open("backtest_report_mock.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("回测完成，结果已保存到 backtest_results_mock.json 和 backtest_report_mock.json")

if __name__ == "__main__":
    try:
        run_backtest()
    except Exception as e:
        print(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
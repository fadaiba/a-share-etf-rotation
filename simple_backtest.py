#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化回测测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.loader import create_data_loader
from backtest.engine import BacktestEngine, Account
import yaml

def simple_strategy(current_date, current_positions, current_prices, total_value):
    """简化策略：等权重持有前3个ETF"""
    config = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))
    selected_etfs = config['etf_pool'][:3]
    weights = {etf: 1.0 / len(selected_etfs) for etf in selected_etfs}

    # 简化的调仓逻辑
    trades = {}
    for etf in selected_etfs:
        if etf in current_prices:
            target_value = weights[etf] * total_value
            current_value = current_positions.get(etf, 0) * current_prices[etf]
            value_diff = target_value - current_value

            if abs(value_diff) > 100:  # 最小交易金额
                shares = abs(value_diff) / current_prices[etf]
                if value_diff > 0:
                    trades[etf] = {'action': 'buy', 'shares': shares, 'value': value_diff}
                else:
                    trades[etf] = {'action': 'sell', 'shares': shares, 'value': abs(value_diff)}

    return trades

def test_backtest():
    """测试回测"""
    print("开始简化回测测试...")

    # 加载配置
    config = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))
    start_date = "2020-01-01"
    end_date = "2020-03-31"  # 只测试一个月

    # 加载数据
    data_loader = create_data_loader()
    price_data = {}
    for symbol in config['etf_pool'][:3]:  # 只加载前3个
        print(f"加载 {symbol}...")
        df = data_loader.get_etf_price(symbol, start_date, end_date)
        if not df.empty:
            price_data[symbol] = df
            print(f"  加载成功: {len(df)} 条记录")

    if not price_data:
        print("没有数据，退出")
        return

    print(f"共加载 {len(price_data)} 个ETF")

    # 创建账户
    account = Account(100000.0)  # 10万初始资金

    # 简化的回测循环
    dates = list(price_data[list(price_data.keys())[0]].index)
    dates = [d for d in dates if start_date <= str(d.date()) <= end_date]

    print(f"回测日期范围: {dates[0].date()} 到 {dates[-1].date()}")

    for current_date in dates[:10]:  # 只测试前10个交易日
        date_str = str(current_date.date())

        # 获取当日价格
        current_prices = {}
        for symbol, df in price_data.items():
            if current_date in df.index:
                current_prices[symbol] = df.loc[current_date, 'close']

        if not current_prices:
            continue

        # 更新账户价值
        account.update_total_value(current_prices)

        # 执行策略
        try:
            trades = simple_strategy(date_str, account.positions, current_prices, account.total_value)
            print(f"{date_str}: 账户价值 {account.total_value:.2f}, 交易数量 {len(trades)}")
        except Exception as e:
            print(f"{date_str}: 策略错误 {e}")

    print(f"\n最终账户价值: {account.total_value:.2f}")
    print(f"最终现金: {account.cash:.2f}")
    print(f"持仓: {account.positions}")

if __name__ == "__main__":
    test_backtest()
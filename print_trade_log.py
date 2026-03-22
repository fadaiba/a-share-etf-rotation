#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日志打印工具 - 从日志文件直接提取
"""

import re
from pathlib import Path

def extract_trades_from_log():
    """从日志文件中提取交易记录"""
    log_file = Path("logs/trading_system.log")

    if not log_file.exists():
        print("错误：找不到日志文件 logs/trading_system.log")
        return []

    trades = []

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # 查找包含"执行交易"的行
            if "执行交易" in line:
                try:
                    # 解析日志行
                    # 格式: 时间 | 级别 | 模块 | 执行交易: SYMBOL | ACTION | 数量: SHARES | 价格: PRICE | 价值: VALUE
                    parts = line.split('|')
                    if len(parts) >= 6:
                        trade_info = parts[-1].strip()

                        # 使用正则表达式提取交易信息
                        pattern = r'执行交易:\s*(\w+)\s*\|\s*(\w+)\s*\|\s*数量:\s*([0-9.]+)\s*\|\s*价格:\s*([0-9.]+)\s*\|\s*价值:\s*([0-9,.]+)'
                        match = re.search(pattern, trade_info)

                        if match:
                            symbol, action, shares, price, value = match.groups()
                            # 提取日期时间
                            date_time = parts[0].strip()
                            date = date_time.split()[0] if ' ' in date_time else date_time

                            trades.append({
                                'date': date,
                                'symbol': symbol,
                                'action': action,
                                'shares': float(shares),
                                'price': float(price.replace(',', '')),
                                'value': float(value.replace(',', ''))
                            })
                except Exception as e:
                    continue

    return trades

def print_trade_log():
    """打印交易日志"""
    print("=" * 100)
    print("A股ETF量化交易系统 - 交易日志")
    print("=" * 100)

    trades = extract_trades_from_log()

    if not trades:
        print("未发现任何交易记录")
        return

    print(f"共发现 {len(trades)} 笔交易记录")
    print("-" * 100)
    print(f"{'日期':<12} {'标的':<8} {'方向':<6} {'数量':<10} {'价格':<10} {'金额':<12}")
    print("-" * 100)

    total_buy_value = 0
    total_sell_value = 0
    total_trades = len(trades)

    for trade in trades:
        print(f"{trade['date']:<12} {trade['symbol']:<8} {trade['action']:<6} {trade['shares']:<10.0f} {trade['price']:<10.4f} {trade['value']:<12.2f}")

        if trade['action'] == 'buy':
            total_buy_value += trade['value']
        else:
            total_sell_value += trade['value']

    print("-" * 100)
    print(f"汇总统计:")
    print(f"  总交易次数: {total_trades}")
    print(f"  买入交易: {len([t for t in trades if t['action'] == 'buy'])} 笔")
    print(f"  卖出交易: {len([t for t in trades if t['action'] == 'sell'])} 笔")
    print(f"  总买入金额: {total_buy_value:,.2f}")
    print(f"  总卖出金额: {total_sell_value:,.2f}")
    print(f"  净买入金额: {total_buy_value - total_sell_value:,.2f}")
    print("=" * 100)

if __name__ == "__main__":
    print_trade_log()
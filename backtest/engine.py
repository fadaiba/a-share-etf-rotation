import pandas as pd
import numpy as np
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

# 导入日志模块
from logger import logger, log_backtest_progress, log_trade_execution

class Account:
    """账户模型"""

    def __init__(self, initial_cash: float = 1000000.0):
        self.cash = initial_cash
        self.positions = {}  # {symbol: {'shares': int, 'avg_price': float}}
        self.total_value = initial_cash
        self.history = []  # 每日快照

    def update_total_value(self, prices: Dict[str, float]):
        """更新总价值"""
        position_value = sum(
            self.positions.get(symbol, {}).get('shares', 0) * prices.get(symbol, 0)
            for symbol in self.positions.keys()
        )
        self.total_value = self.cash + position_value

    def execute_trade(self, symbol: str, shares: int, price: float, fee_rate: float):
        """执行交易"""
        cost = shares * price
        fee = abs(cost) * fee_rate

        if shares > 0:  # 买入
            total_cost = cost + fee
            if self.cash >= total_cost:
                # 资金充足，正常执行
                self.cash -= total_cost
                if symbol in self.positions:
                    old_shares = self.positions[symbol]['shares']
                    old_cost = old_shares * self.positions[symbol]['avg_price']
                    new_cost = old_cost + cost
                    new_shares = old_shares + shares
                    self.positions[symbol]['shares'] = new_shares
                    self.positions[symbol]['avg_price'] = new_cost / new_shares
                else:
                    self.positions[symbol] = {'shares': shares, 'avg_price': price}
                return shares  # 返回实际执行的股票数量
            else:
                # 资金不足，计算可用资金能买多少股票
                available_cash = self.cash
                # 预留手续费空间，假设手续费率
                max_cost_for_shares = available_cash / (1 + fee_rate)
                affordable_shares = int(max_cost_for_shares // price)

                if affordable_shares > 0:
                    # 执行部分交易
                    actual_cost = affordable_shares * price
                    actual_fee = actual_cost * fee_rate
                    total_actual_cost = actual_cost + actual_fee

                    self.cash -= total_actual_cost
                    if symbol in self.positions:
                        old_shares = self.positions[symbol]['shares']
                        old_cost = old_shares * self.positions[symbol]['avg_price']
                        new_cost = old_cost + actual_cost
                        new_shares = old_shares + affordable_shares
                        self.positions[symbol]['shares'] = new_shares
                        self.positions[symbol]['avg_price'] = new_cost / new_shares
                    else:
                        self.positions[symbol] = {'shares': affordable_shares, 'avg_price': price}
                    return affordable_shares  # 返回实际执行的股票数量
                else:
                    return 0  # 无法执行任何交易
        else:  # 卖出
            if symbol in self.positions and self.positions[symbol]['shares'] >= abs(shares):
                self.cash += (abs(cost) - fee)
                self.positions[symbol]['shares'] += shares  # shares为负数
                if self.positions[symbol]['shares'] == 0:
                    del self.positions[symbol]
                return abs(shares)  # 返回实际执行的股票数量
            else:
                # 持仓不足，卖出所有可用股票
                if symbol in self.positions:
                    available_shares = self.positions[symbol]['shares']
                    if available_shares > 0:
                        actual_cost = available_shares * price
                        actual_fee = actual_cost * fee_rate
                        self.cash += (actual_cost - actual_fee)
                        self.positions[symbol]['shares'] = 0
                        del self.positions[symbol]
                        return available_shares  # 返回实际执行的股票数量
                return 0  # 无法执行任何交易

    def get_position_value(self, symbol: str, price: float) -> float:
        """获取持仓价值"""
        if symbol in self.positions:
            return self.positions[symbol]['shares'] * price
        return 0.0

    def save_snapshot(self, date: str, prices: Dict[str, float]):
        """保存每日快照"""
        self.update_total_value(prices)
        snapshot = {
            'date': date,
            'cash': self.cash,
            'positions': self.positions.copy(),
            'total_value': self.total_value
        }
        self.history.append(snapshot)

class BacktestEngine:
    """回测引擎"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.fee_rate = config['backtest']['fee_rate']
        self.slippage = config['backtest']['slippage']
        self.trade_records = []  # 交易记录列表

    def run_backtest(self, strategy_func, start_date: str, end_date: str,
                    initial_cash: float = 1000000.0, price_data: Dict[str, pd.DataFrame] = None,
                    index_df: pd.DataFrame = None) -> Account:
        """运行回测"""
        logger.bind(context="backtest").info("初始化回测账户和参数")

        account = Account(initial_cash)
        self.price_data = price_data or {}
        self.index_df = index_df

        # 获取所有交易日
        trading_dates = self._get_trading_dates(start_date, end_date)
        logger.bind(context="backtest").info(f"生成交易日历: {len(trading_dates)} 个交易日")

        last_rebalance = None
        rebalance_freq = self.config['trading']['rebalance_freq']
        total_trades = 0

        logger.bind(context="backtest").info("开始回测循环")

        for i, current_date in enumerate(trading_dates):
            # 获取当日价格
            prices = self._get_prices_at_date(current_date)

            if not prices:
                logger.bind(context="backtest").debug(f"{current_date}: 无价格数据，跳过")
                continue

            # 更新账户价值
            account.update_total_value(prices)

            # 止损检查
            self._check_stop_loss(account, prices, current_date)

            # 调仓逻辑
            days_since_rebalance = (pd.to_datetime(current_date) - pd.to_datetime(last_rebalance)).days if last_rebalance else 999

            if days_since_rebalance >= (7 / rebalance_freq):  # 每周调仓
                try:
                    logger.bind(context="backtest").debug(f"{current_date}: 执行策略调仓")
                    trades = strategy_func(current_date, account.positions, prices, account.total_value,
                                         self.price_data, self.index_df)

                    executed_trades = self._execute_trades(account, trades, prices, current_date)
                    total_trades += executed_trades
                    last_rebalance = current_date

                except Exception as e:
                    logger.bind(context="backtest").error(f"{current_date}: 策略执行错误: {e}")

            # 保存快照
            account.save_snapshot(current_date, prices)

            # 每100个交易日记录一次进度
            if (i + 1) % 100 == 0:
                log_backtest_progress(current_date, account.total_value, total_trades)

        logger.bind(context="backtest").info(f"回测循环完成，共执行 {total_trades} 笔交易")
        logger.bind(context="backtest").info(f"最终账户价值: {account.total_value:,.2f}")

        return account

    def _get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日历（简化版）"""
        # 这里应该从数据源获取真实的交易日历
        # 暂时使用工作日
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        return [d.strftime('%Y-%m-%d') for d in date_range]

    def _get_prices_at_date(self, date: str) -> Dict[str, float]:
        """获取指定日期的价格"""
        prices = {}
        target_date = pd.to_datetime(date)

        for symbol, df in self.price_data.items():
            if not df.empty:
                # 找到最接近的交易日价格
                available_dates = df.index
                if len(available_dates) > 0:
                    # 找到小于等于目标日期的最近日期
                    valid_dates = available_dates[available_dates <= target_date]
                    if len(valid_dates) > 0:
                        closest_date = valid_dates.max()
                        # 使用iloc获取最后一个值，确保返回标量
                        close_price_series = df.loc[df.index <= target_date, 'close']
                        if not close_price_series.empty:
                            # 获取最后一个值并转换为float
                            close_price = float(close_price_series.iloc[-1])
                            prices[symbol] = close_price

        return prices

    def _check_stop_loss(self, account: Account, prices: Dict[str, float], date: str):
        """止损检查"""
        try:
            from strategy.risk import RiskManager
        except ImportError:
            # 如果相对导入失败，尝试绝对导入
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from strategy.risk import RiskManager

        risk_manager = RiskManager()

        to_sell = []
        for symbol, position in account.positions.items():
            current_price = prices.get(symbol, 0)
            entry_price = position['avg_price']

            if risk_manager.stop_loss_check(current_price, entry_price):
                to_sell.append((symbol, position['shares']))

        # 执行止损卖出
        for symbol, shares in to_sell:
            price = prices.get(symbol, 0) * (1 - self.slippage)  # 卖出滑点
            account.execute_trade(symbol, -shares, price, self.fee_rate)

    def _execute_trades(self, account: Account, trades: Dict[str, Dict],
                       prices: Dict[str, float], date: str):
        """执行交易"""
        logger.bind(context="trading").debug(f"{date}: 开始执行 {len(trades)} 笔交易")

        executed_count = 0
        total_value = 0
        partial_trades = 0  # 部分执行的交易数量

        for symbol, trade in trades.items():
            shares = trade['shares']
            action = trade['action']

            # 获取持仓信息用于计算收益
            position_info = account.positions.get(symbol, {'shares': 0, 'avg_price': 0})
            avg_price = position_info['avg_price'] if action == 'sell' else 0

            if action == 'buy':
                price = prices.get(symbol, 0) * (1 + self.slippage)  # 买入滑点
                actual_shares = int(shares)  # 取整
                profit = 0.0  # 买入没有收益
            else:  # sell
                price = prices.get(symbol, 0) * (1 - self.slippage)  # 卖出滑点
                actual_shares = -int(shares)  # 取整为负数
                # 计算收益：(卖出价 - 成本价) * 数量
                profit = (price - avg_price) * abs(shares) if avg_price > 0 else 0.0

            if actual_shares != 0:
                # 执行交易，返回实际执行的股票数量
                executed_shares = account.execute_trade(symbol, actual_shares, price, self.fee_rate)

                if executed_shares > 0:
                    executed_count += 1
                    trade_value = executed_shares * price
                    total_value += trade_value

                    # 检查是否为部分执行
                    requested_shares = abs(actual_shares)
                    if executed_shares < requested_shares:
                        partial_trades += 1
                        logger.bind(context="trading").warning(
                            f"{date}: {symbol} 资金不足，请求 {requested_shares} 股，实际执行 {executed_shares} 股"
                        )

                    # 记录交易日志
                    log_trade_execution(symbol, action, executed_shares, price, trade_value)

                    # 保存交易记录到列表
                    self.trade_records.append({
                        'date': date,
                        'symbol': symbol,
                        'action': action,
                        'price': price,
                        'shares': executed_shares,
                        'value': trade_value,
                        'profit': profit if action == 'sell' else 0.0,
                        'avg_cost': avg_price if action == 'sell' else 0.0
                    })
                else:
                    logger.bind(context="trading").debug(f"{date}: {symbol} 无法执行交易（资金或持仓不足）")
            else:
                logger.bind(context="trading").debug(f"{date}: {symbol} 交易份额为0，跳过")

        if partial_trades > 0:
            logger.bind(context="trading").info(
                f"{date}: 成功执行 {executed_count} 笔交易（其中 {partial_trades} 笔为部分执行），总价值: {total_value:,.2f}"
            )
        else:
            logger.bind(context="trading").info(f"{date}: 成功执行 {executed_count} 笔交易，总价值: {total_value:,.2f}")
        return executed_count

    def save_results(self, account: Account, output_path: str = "backtest_results.json"):
        """保存回测结果"""
        results = {
            'final_value': account.total_value,
            'final_cash': account.cash,
            'final_positions': account.positions,
            'history': account.history
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def save_trade_report(self, start_date: str, end_date: str, output_path: str = None):
        """保存交易报告到txt文件"""
        if output_path is None:
            output_path = f"回测报告_{start_date}_{end_date}.txt"

        # ETF代码到名称的映射
        etf_names = {
            '510300': '沪深300ETF', '510500': '中证500ETF', '159915': '创业板ETF',
            '159919': '沪深300ETF', '512100': '医药ETF', '512880': '证券ETF',
            '515050': '5GETF', '516160': '新能源ETF', '159949': '恒生ETF',
            '518880': '黄金ETF', '159952': '创业板ETF', '159926': '国债ETF',
            '159941': '纳斯达克ETF'
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write("=" * 140 + "\n")
            f.write(f"A股ETF量化交易系统 - 回测交易报告\n")
            f.write(f"回测期间: {start_date} 至 {end_date}\n")
            f.write(f"总交易数: {len(self.trade_records)} 笔\n")
            f.write("=" * 140 + "\n\n")

            # 写入表头
            f.write(f"{'交易日期':<12} {'股票代码':<10} {'股票名称':<15} {'买卖类型':<8} {'价格':<12} {'数量':>12} {'交易金额':>15} {'收益':>15}\n")
            f.write("-" * 140 + "\n")

            # 统计数据
            total_buy_value = 0
            total_sell_value = 0
            total_profit = 0
            buy_count = 0
            sell_count = 0

            # 写入每笔交易
            for record in self.trade_records:
                date = record['date']
                symbol = record['symbol']
                name = etf_names.get(symbol, '未知ETF')  # 获取ETF名称
                action = '买入' if record['action'] == 'buy' else '卖出'
                price = record['price']
                shares = record['shares']
                value = record['value']
                profit = record['profit']

                # 格式化输出
                if record['action'] == 'buy':
                    profit_str = "-"
                    total_buy_value += value
                    buy_count += 1
                else:
                    profit_str = f"{profit:>15.2f}"
                    total_sell_value += value
                    total_profit += profit
                    sell_count += 1

                f.write(f"{date:<12} {symbol:<10} {name:<15} {action:<8} {price:<12.4f} {shares:>12.0f} {value:>15.2f} {profit_str}\n")

            # 写入汇总统计
            f.write("-" * 140 + "\n")
            f.write("汇总统计:\n")
            f.write(f"  买入交易: {buy_count} 笔，总金额: {total_buy_value:,.2f} 元\n")
            f.write(f"  卖出交易: {sell_count} 笔，总金额: {total_sell_value:,.2f} 元\n")
            f.write(f"  总收益: {total_profit:,.2f} 元\n")
            f.write(f"  收益率: {(total_profit / total_buy_value * 100) if total_buy_value > 0 else 0:.2f}%\n")
            f.write("=" * 140 + "\n")

        logger.bind(context="backtest").info(f"交易报告已保存到: {output_path}")
        return output_path
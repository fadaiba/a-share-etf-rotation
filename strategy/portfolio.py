import pandas as pd
import numpy as np
import yaml
from typing import Dict, List

# 导入日志模块
from logger import logger

class PortfolioManager:
    """投资组合管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config

    def select_etfs(self, etf_pool: List[str], price_data: Dict[str, pd.DataFrame]) -> List[str]:
        """ETF选择流程：聚类 -> 筛选 -> 因子评分 -> Top N"""
        logger.bind(context="strategy").debug("开始ETF选择流程")

        from .clustering import ETFClustering
        from .factors import FactorCalculator

        # 1. 聚类分析
        logger.bind(context="strategy").debug("执行ETF聚类分析")
        clustering = ETFClustering()
        returns_df = clustering.calculate_returns(price_data)
        clusters = clustering.cluster_etfs(returns_df)

        # 2. 每个cluster选20日收益率最高
        etf_candidates = clustering.select_top_etf_per_cluster(price_data, clusters)
        logger.bind(context="strategy").debug(f"聚类筛选后剩余 {len(etf_candidates)} 个ETF候选")

        # 如果聚类筛选结果不足，使用原始池
        min_candidates = max(3, len(etf_pool) // 3)  # 至少3个，或ETF池的1/3
        if len(etf_candidates) < min_candidates:
            etf_candidates = etf_pool.copy()
            logger.bind(context="strategy").warning(f"聚类筛选结果不足({len(etf_candidates)} < {min_candidates})，使用全池ETF")

        # 3. 因子评分
        logger.bind(context="strategy").debug("计算ETF因子评分")
        factor_calc = FactorCalculator()
        scores = factor_calc.score_etfs({etf: price_data.get(etf, pd.DataFrame())
                                       for etf in etf_candidates})

        # 4. 选择Top N
        selected_etfs = factor_calc.select_top_etfs(scores, self.config['selection']['top_n'])
        logger.bind(context="strategy").info(f"ETF选择完成: 选中 {len(selected_etfs)} 个ETF: {selected_etfs}")

        return selected_etfs

    def calculate_weights(self, selected_etfs: List[str],
                         price_data: Dict[str, pd.DataFrame],
                         index_df: pd.DataFrame) -> Dict[str, float]:
        """计算目标权重"""
        logger.bind(context="strategy").debug("开始计算投资组合权重")

        from .risk import RiskManager

        risk_manager = RiskManager()

        # 1. 市场过滤
        market_ok = risk_manager.market_filter(index_df)
        if not market_ok:
            logger.bind(context="strategy").warning("市场过滤触发，执行空仓策略")
            return {}  # 空仓

        # 2. 风险预算权重
        etf_scores = {etf: 1.0 for etf in selected_etfs}  # 简化为相等评分
        weights = risk_manager.risk_budget_weights(etf_scores, price_data)
        logger.bind(context="strategy").debug(f"风险预算权重计算完成: {len(weights)} 个ETF")

        # 3. 波动率目标控制
        current_vol = risk_manager.get_portfolio_volatility(weights, price_data)
        weights = risk_manager.volatility_target_scaling(weights, current_vol)

        # 过滤掉权重过小的ETF
        weights = {etf: w for etf, w in weights.items() if w > 0.001}
        logger.bind(context="strategy").info(f"权重计算完成: {len(weights)} 个有效权重，总权重: {sum(weights.values()):.4f}")

        return weights

    def rebalance_portfolio(self, current_positions: Dict[str, Dict],
                           target_weights: Dict[str, float],
                           current_prices: Dict[str, float],
                           total_value: float) -> Dict[str, Dict]:
        """计算调仓交易"""
        logger.bind(context="strategy").debug(f"开始计算调仓交易，总价值: {total_value:,.2f}")

        trades = {}

        # 计算目标持仓价值
        target_values = {etf: target_weights.get(etf, 0) * total_value
                        for etf in set(current_positions.keys()) | set(target_weights.keys())}

        trade_count = 0
        for etf in target_values.keys():
            # 获取当前持仓数量（从positions字典中提取shares）
            position_info = current_positions.get(etf, {'shares': 0, 'avg_price': 0})
            current_shares = position_info.get('shares', 0)
            current_value = current_shares * current_prices.get(etf, 0)
            target_value = target_values[etf]

            value_diff = target_value - current_value

            if abs(value_diff) > 1e-6:  # 避免微小交易
                trades[etf] = {
                    'action': 'buy' if value_diff > 0 else 'sell',
                    'value': abs(value_diff),
                    'shares': abs(value_diff) / current_prices.get(etf, 1)
                }
                trade_count += 1

        logger.bind(context="strategy").info(f"调仓交易计算完成: 生成 {trade_count} 个交易")
        return trades

    def apply_trading_restrictions(self, trades: Dict[str, Dict],
                                  price_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """应用交易限制：最小交易单位、涨跌停等"""
        logger.bind(context="strategy").debug(f"开始应用交易限制，初始交易数量: {len(trades)}")

        min_shares = self.config['trading']['min_shares']
        filtered_trades = {}
        filtered_count = 0

        for etf, trade in trades.items():
            shares = trade['shares']

            # 最小交易单位
            if shares < min_shares:
                logger.bind(context="strategy").debug(f"  {etf}: 交易份额 {shares:.0f} 小于最小交易单位 {min_shares}，跳过")
                continue

            # 取整到最小交易单位
            shares = int(shares // min_shares * min_shares)

            if shares == 0:
                logger.bind(context="strategy").debug(f"  {etf}: 取整后份额为0，跳过")
                continue

            # 检查涨跌停（简化版）
            df = price_data.get(etf, pd.DataFrame())
            if not df.empty:
                current_price = df['close'].iloc[-1]
                high_limit = df['high'].iloc[-1]  # 简化为前日最高
                low_limit = df['low'].iloc[-1]   # 简化为前日最低

                if trade['action'] == 'buy' and current_price >= high_limit * 0.99:  # 接近涨停
                    logger.bind(context="strategy").debug(f"  {etf}: 买入时价格接近涨停，跳过")
                    continue
                elif trade['action'] == 'sell' and current_price <= low_limit * 1.01:  # 接近跌停
                    logger.bind(context="strategy").debug(f"  {etf}: 卖出时价格接近跌停，跳过")
                    continue

            filtered_trades[etf] = {
                'action': trade['action'],
                'shares': shares,
                'value': shares * current_price
            }
            filtered_count += 1

        logger.bind(context="strategy").info(f"交易限制应用完成: 剩余 {filtered_count} 个有效交易")
        return filtered_trades
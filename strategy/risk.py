import pandas as pd
import numpy as np
import yaml

class RiskManager:
    """风险管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config['risk']

    def market_filter(self, index_df: pd.DataFrame) -> bool:
        """市场过滤：如果指数收盘价 < MA60，则空仓"""
        if index_df.empty or len(index_df) < self.config['market_filter']['ma_period']:
            return False  # 默认不过滤

        ma60 = index_df['close'].rolling(window=self.config['market_filter']['ma_period']).mean().iloc[-1]
        current_close = index_df['close'].iloc[-1]

        return current_close >= ma60  # True表示可以交易

    def calculate_downside_volatility(self, returns: pd.Series) -> float:
        """计算下行波动率"""
        if returns.empty:
            return 0.0

        # 下行收益率
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return 0.0

        # 下行波动率
        downside_vol = downside_returns.std() * np.sqrt(252)  # 年化
        return downside_vol

    def risk_budget_weights(self, etf_scores: dict, price_data: dict) -> dict:
        """风险预算权重计算"""
        weights = {}

        for etf in etf_scores.keys():
            df = price_data.get(etf, pd.DataFrame())
            if df.empty:
                weights[etf] = 0.0
                continue

            # 计算日收益率
            returns = df['close'].pct_change().dropna()

            if self.config['downside_vol']:
                vol = self.calculate_downside_volatility(returns)
            else:
                vol = returns.std() * np.sqrt(252)

            if vol > 0:
                weights[etf] = 1.0 / vol
            else:
                weights[etf] = 0.0

        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {etf: w / total_weight for etf, w in weights.items()}

        return weights

    def volatility_target_scaling(self, weights: dict, current_vol: float) -> dict:
        """波动率目标控制"""
        target_vol = self.config['vol_target']

        if current_vol == 0:
            return weights

        scale = target_vol / current_vol

        # 限制scale在合理范围内
        scale = np.clip(scale, 0.1, 2.0)

        scaled_weights = {etf: w * scale for etf, w in weights.items()}

        return scaled_weights

    def drawdown_control(self, portfolio_returns: pd.Series) -> float:
        """回撤控制"""
        if portfolio_returns.empty:
            return 1.0  # 正常仓位

        # 计算累积收益
        cum_returns = (1 + portfolio_returns).cumprod()

        # 计算回撤
        peak = cum_returns.expanding().max()
        drawdown = (cum_returns - peak) / peak

        max_drawdown = drawdown.min()

        if max_drawdown < self.config['drawdown_limit']:
            return 0.5  # 仓位减半

        return 1.0  # 正常仓位

    def stop_loss_check(self, current_price: float, entry_price: float) -> bool:
        """单标止损检查"""
        if entry_price == 0:
            return False

        return_pct = (current_price - entry_price) / entry_price

        return return_pct < self.config['stop_loss']  # True表示需要止损

    def get_portfolio_volatility(self, weights: dict, price_data: dict) -> float:
        """计算组合波动率"""
        if not weights:
            return 0.0

        # 获取收益率数据
        returns_list = []
        for etf, weight in weights.items():
            if weight == 0:
                continue
            df = price_data.get(etf, pd.DataFrame())
            if not df.empty:
                ret = df['close'].pct_change().dropna()
                returns_list.append(ret * weight)

        if not returns_list:
            return 0.0

        # 组合收益率
        portfolio_returns = pd.concat(returns_list, axis=1).sum(axis=1)

        # 年化波动率
        vol = portfolio_returns.std() * np.sqrt(252)

        return vol
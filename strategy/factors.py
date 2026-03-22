import pandas as pd
import numpy as np
import yaml

class FactorCalculator:
    """因子计算器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config['factors']

    def calculate_momentum(self, df: pd.DataFrame) -> float:
        """计算质量动量因子"""
        if df.empty or len(df) < 60:
            return 0.0

        # 计算20日和60日收益率
        ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) if len(df) >= 20 else 0
        ret_60d = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1)

        # 计算波动率（使用日收益率的标准差）
        daily_returns = df['close'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252)  # 年化波动率

        if volatility == 0:
            return 0.0

        # 质量动量 = (0.6 * ret20 + 0.4 * ret60) / volatility
        momentum = (self.config['momentum']['ret20_weight'] * ret_20d +
                   self.config['momentum']['ret60_weight'] * ret_60d) / volatility

        return momentum

    def calculate_trend(self, df: pd.DataFrame) -> float:
        """计算趋势强度因子"""
        if df.empty or len(df) < 60:
            return 0.0

        # 计算MA20和MA60
        ma20 = df['close'].rolling(window=self.config['trend']['ma20_period']).mean().iloc[-1]
        ma60 = df['close'].rolling(window=self.config['trend']['ma60_period']).mean().iloc[-1]

        if ma60 == 0:
            return 0.0

        # 趋势强度 = (MA20 - MA60) / MA60
        trend = (ma20 - ma60) / ma60

        return trend

    def calculate_final_score(self, momentum: float, trend: float) -> float:
        """计算最终评分"""
        final_score = (self.config['final_score']['momentum_weight'] * momentum +
                      self.config['final_score']['trend_weight'] * trend)
        return final_score

    def score_etfs(self, price_data: dict) -> dict:
        """为所有ETF计算评分"""
        scores = {}

        for symbol, df in price_data.items():
            if df.empty:
                scores[symbol] = 0.0
                continue

            momentum = self.calculate_momentum(df)
            trend = self.calculate_trend(df)
            final_score = self.calculate_final_score(momentum, trend)

            scores[symbol] = final_score

        return scores

    def select_top_etfs(self, scores: dict, top_n: int = 3) -> list:
        """选择评分最高的ETF"""
        sorted_etfs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [etf for etf, score in sorted_etfs[:top_n]]
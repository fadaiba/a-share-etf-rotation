import pandas as pd
import numpy as np
from typing import List, Dict
import json

class PerformanceMetrics:
    """绩效指标计算"""

    def __init__(self, account_history: List[Dict], benchmark_returns: pd.Series = None):
        self.history = account_history
        self.benchmark = benchmark_returns

        # 提取净值序列
        self.portfolio_values = pd.Series(
            [h['total_value'] for h in self.history],
            index=[pd.to_datetime(h['date']) for h in self.history]
        )

        # 计算日收益率
        self.returns = self.portfolio_values.pct_change().dropna()

    def calculate_annual_return(self) -> float:
        """年化收益"""
        if len(self.returns) < 2:
            return 0.0

        total_return = self.portfolio_values.iloc[-1] / self.portfolio_values.iloc[0] - 1
        years = (self.portfolio_values.index[-1] - self.portfolio_values.index[0]).days / 365.25

        if years > 0:
            return (1 + total_return) ** (1 / years) - 1
        return 0.0

    def calculate_cumulative_return(self) -> float:
        """累计收益"""
        if len(self.portfolio_values) < 2:
            return 0.0
        return self.portfolio_values.iloc[-1] / self.portfolio_values.iloc[0] - 1

    def calculate_volatility(self) -> float:
        """波动率（年化）"""
        if len(self.returns) < 2:
            return 0.0
        return self.returns.std() * np.sqrt(252)

    def calculate_max_drawdown(self) -> float:
        """最大回撤"""
        if len(self.portfolio_values) < 2:
            return 0.0

        peak = self.portfolio_values.expanding().max()
        drawdown = (self.portfolio_values - peak) / peak
        return drawdown.min()

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """夏普比率"""
        if len(self.returns) < 2:
            return 0.0

        excess_returns = self.returns - risk_free_rate / 252  # 日化无风险利率
        vol = self.returns.std() * np.sqrt(252)

        if vol > 0:
            return excess_returns.mean() * 252 / vol
        return 0.0

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.03) -> float:
        """索提诺比率"""
        if len(self.returns) < 2:
            return 0.0

        excess_returns = self.returns - risk_free_rate / 252
        downside_returns = self.returns[self.returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0

        if downside_vol > 0:
            return excess_returns.mean() * 252 / downside_vol
        return 0.0

    def calculate_win_rate(self) -> float:
        """胜率"""
        if len(self.returns) < 2:
            return 0.0

        winning_days = (self.returns > 0).sum()
        return winning_days / len(self.returns)

    def calculate_profit_loss_ratio(self) -> float:
        """盈亏比"""
        if len(self.returns) < 2:
            return 0.0

        winning_returns = self.returns[self.returns > 0]
        losing_returns = self.returns[self.returns < 0]

        if len(winning_returns) == 0 or len(losing_returns) == 0:
            return 0.0

        avg_win = winning_returns.mean()
        avg_loss = abs(losing_returns.mean())

        if avg_loss > 0:
            return avg_win / avg_loss
        return 0.0

    def calculate_alpha_beta(self, benchmark_returns: pd.Series = None) -> tuple:
        """计算alpha和beta"""
        if benchmark_returns is None or len(self.returns) != len(benchmark_returns):
            return 0.0, 1.0

        # 对齐数据
        common_index = self.returns.index.intersection(benchmark_returns.index)
        if len(common_index) < 2:
            return 0.0, 1.0

        port_returns = self.returns.loc[common_index]
        bench_returns = benchmark_returns.loc[common_index]

        # 计算beta
        covariance = np.cov(port_returns, bench_returns)[0, 1]
        bench_var = bench_returns.var()

        beta = covariance / bench_var if bench_var > 0 else 1.0

        # 计算alpha（年化）
        port_annual_return = self.calculate_annual_return()
        bench_annual_return = (1 + bench_returns.mean() * 252) - 1
        risk_free_rate = 0.03

        alpha = port_annual_return - risk_free_rate - beta * (bench_annual_return - risk_free_rate)

        return alpha, beta

    def generate_report(self) -> Dict:
        """生成完整绩效报告"""
        alpha, beta = self.calculate_alpha_beta(self.benchmark)

        report = {
            '收益指标': {
                '年化收益': f"{self.calculate_annual_return():.4f}",
                '累计收益': f"{self.calculate_cumulative_return():.4f}",
                '年化波动率': f"{self.calculate_volatility():.4f}",
                '夏普比率': f"{self.calculate_sharpe_ratio():.4f}",
                '索提诺比率': f"{self.calculate_sortino_ratio():.4f}"
            },
            '风险指标': {
                '最大回撤': f"{self.calculate_max_drawdown():.4f}",
                '胜率': f"{self.calculate_win_rate():.4f}",
                '盈亏比': f"{self.calculate_profit_loss_ratio():.4f}"
            },
            '基准对比': {
                'Alpha': f"{alpha:.4f}",
                'Beta': f"{beta:.4f}"
            },
            '交易统计': {
                '总交易日数': len(self.returns),
                '起始净值': f"{self.portfolio_values.iloc[0]:.2f}",
                '结束净值': f"{self.portfolio_values.iloc[-1]:.2f}"
            }
        }

        return report

    def plot_performance(self, save_path: str = "performance.png"):
        """绘制绩效图表"""
        try:
            import matplotlib.pyplot as plt
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            fig, axes = plt.subplots(2, 2, figsize=(15, 10))

            # 净值曲线
            axes[0, 0].plot(self.portfolio_values.index, self.portfolio_values.values)
            axes[0, 0].set_title('净值曲线')
            axes[0, 0].set_ylabel('净值')
            axes[0, 0].grid(True)

            # 回撤曲线
            peak = self.portfolio_values.expanding().max()
            drawdown = (self.portfolio_values - peak) / peak
            axes[0, 1].fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
            axes[0, 1].set_title('回撤曲线')
            axes[0, 1].set_ylabel('回撤')
            axes[0, 1].grid(True)

            # 月度收益
            monthly_returns = self.returns.groupby(pd.Grouper(freq='ME')).apply(lambda x: (1 + x).prod() - 1)
            axes[1, 0].bar(range(len(monthly_returns)), monthly_returns.values)
            axes[1, 0].set_title('月度收益')
            axes[1, 0].set_xlabel('月份')
            axes[1, 0].set_ylabel('收益')
            axes[1, 0].grid(True)

            # 滚动夏普比率
            rolling_sharpe = self.returns.rolling(window=252).apply(
                lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else 0
            )
            axes[1, 1].plot(rolling_sharpe.index, rolling_sharpe.values)
            axes[1, 1].set_title('滚动夏普比率')
            axes[1, 1].set_ylabel('夏普比率')
            axes[1, 1].grid(True)

            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()

        except ImportError:
            print("matplotlib not installed, skipping plot generation")
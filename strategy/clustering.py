import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
import yaml

class ETFClustering:
    """ETF聚类分析"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.lookback_days = config['clustering']['lookback_days']

    def calculate_returns(self, price_data: dict) -> pd.DataFrame:
        """计算历史收益率"""
        returns = {}
        for symbol, df in price_data.items():
            if df.empty:
                continue
            # 计算日收益率
            daily_returns = df['close'].pct_change().dropna()
            # 计算滚动收益率（这里简化为日收益率的累积，但实际可能需要调整）
            # 文档说120日收益率，可能是120日累积收益率
            cum_returns = (1 + daily_returns).rolling(window=self.lookback_days).apply(lambda x: x.prod() - 1).dropna()
            returns[symbol] = cum_returns

        # 对齐日期
        returns_df = pd.DataFrame(returns)
        returns_df = returns_df.dropna()  # 去除NaN
        return returns_df

    def cluster_etfs(self, returns_df: pd.DataFrame) -> dict:
        """执行层次聚类"""
        if returns_df.empty or len(returns_df.columns) < 2:
            return {symbol: 0 for symbol in returns_df.columns}

        # 计算相关性矩阵
        corr_matrix = returns_df.corr()

        # 计算距离矩阵：distance = 1 - correlation
        distance_matrix = 1 - corr_matrix

        # 转换为距离向量
        distance_vector = pdist(distance_matrix.values)

        # 层次聚类
        linkage_matrix = linkage(distance_vector, method='ward')

        # 自动确定聚类数量（调整为更合适的数量）
        # 对于13个ETF，使用更多的聚类以获得更好的筛选结果
        n_clusters = max(3, min(8, len(returns_df.columns) // 2))  # 至少3个，最多8个，每个聚类平均2个ETF

        # 获取聚类标签
        cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')

        # 创建结果字典
        clusters = {}
        for i, symbol in enumerate(returns_df.columns):
            clusters[symbol] = cluster_labels[i] - 1  # 使cluster_id从0开始

        return clusters

    def select_top_etf_per_cluster(self, price_data: dict, clusters: dict) -> list:
        """每个cluster选择多个ETF（基于收益率排序）"""
        selected_etfs = []

        # 按cluster分组
        cluster_groups = {}
        for etf, cluster_id in clusters.items():
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(etf)

        for cluster_id, etfs in cluster_groups.items():
            if not etfs:
                continue

            # 计算每个ETF的20日收益率并排序
            etf_returns = []
            for etf in etfs:
                df = price_data.get(etf, pd.DataFrame())
                if df.empty or len(df) < 20:
                    continue

                # 计算20日收益率
                ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1)
                etf_returns.append((etf, ret_20d))

            # 按收益率降序排序，选择前50%的ETF（至少1个）
            etf_returns.sort(key=lambda x: x[1], reverse=True)
            n_select = max(1, len(etf_returns) // 2)  # 选择前50%，至少1个

            for etf, _ in etf_returns[:n_select]:
                selected_etfs.append(etf)

        return selected_etfs
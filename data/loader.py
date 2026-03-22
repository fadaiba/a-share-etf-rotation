import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import yaml
import os
from datetime import datetime, timedelta

# 导入日志模块
from logger import logger

class DataLoader(ABC):
    """抽象数据加载器"""

    @abstractmethod
    def get_etf_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF价格数据"""
        pass

    @abstractmethod
    def get_index_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数价格数据"""
        pass

class AKShareLoader(DataLoader):
    """基于akshare的数据加载器"""

    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            raise ImportError("akshare not installed")

    def get_etf_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF日线数据"""
        try:
            df = self.ak.fund_etf_hist_em(symbol=symbol, period="daily",
                                        start_date=start_date, end_date=end_date)
            if df.empty:
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"Error loading ETF {symbol}: {e}")
            return pd.DataFrame()

    def get_index_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数日线数据"""
        try:
            df = self.ak.stock_zh_index_daily_em(symbol=symbol,
                                               start_date=start_date, end_date=end_date)
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'volume': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"Error loading index {symbol}: {e}")
            return pd.DataFrame()

class MockDataLoader(DataLoader):
    """模拟数据加载器，用于测试"""

    def __init__(self):
        self.price_data = {}
        self._generate_mock_data()

    def _generate_mock_data(self):
        """生成模拟数据"""
        logger.info("开始生成模拟ETF数据")

        # 生成日期序列
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2023, 12, 31)
        dates = pd.date_range(start_date, end_date, freq='D')

        # ETF代码列表
        etf_codes = [
            "510300", "510500", "159915", "159919", "512100",
            "512880", "515050", "516160", "159949", "518880",
            "159952", "159926", "159941"
        ]

        logger.info(f"为 {len(etf_codes)} 个ETF生成数据，时间范围: {start_date.date()} 到 {end_date.date()}")

        np.random.seed(42)  # 固定随机种子

        for symbol in etf_codes:
            # 生成价格数据
            n_days = len(dates)
            base_price = np.random.uniform(1.0, 5.0)  # 基础价格

            # 生成随机收益率
            returns = np.random.normal(0.0005, 0.02, n_days)  # 日均收益率0.05%，波动率2%

            # 计算价格序列
            prices = [base_price]
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)

            # 生成OHLC数据
            closes = np.array(prices)
            highs = closes * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
            lows = closes * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
            opens = closes + np.random.normal(0, closes * 0.005, n_days)
            volumes = np.random.randint(100000, 10000000, n_days)

            # 创建DataFrame
            df = pd.DataFrame({
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            }, index=dates)

            self.price_data[symbol] = df

        logger.info(f"模拟数据生成完成，共 {len(self.price_data)} 个ETF")

    def get_etf_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF价格数据"""
        if symbol in self.price_data:
            df = self.price_data[symbol]
            mask = (df.index >= start_date) & (df.index <= end_date)
            return df[mask].copy()
        return pd.DataFrame()

    def get_index_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数价格数据（使用沪深300模拟）"""
        # 简化处理，使用510300的数据作为指数
        return self.get_etf_price("510300", start_date, end_date)

class CachedDataLoader:
    """带缓存的数据加载器"""

    def __init__(self, loader: DataLoader, cache_dir: str = "data/cache"):
        self.loader = loader
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol: str, data_type: str) -> str:
        return os.path.join(self.cache_dir, f"{data_type}_{symbol}.pkl")

    def _load_from_cache(self, symbol: str, data_type: str) -> pd.DataFrame:
        cache_path = self._get_cache_path(symbol, data_type)
        if os.path.exists(cache_path):
            return pd.read_pickle(cache_path)
        return pd.DataFrame()

    def _save_to_cache(self, df: pd.DataFrame, symbol: str, data_type: str):
        if not df.empty:
            cache_path = self._get_cache_path(symbol, data_type)
            df.to_pickle(cache_path)

    def get_etf_price(self, symbol: str, start_date: str, end_date: str,
                     use_cache: bool = True) -> pd.DataFrame:
        if use_cache:
            cached = self._load_from_cache(symbol, "etf")
            if not cached.empty:
                # 检查是否需要更新
                last_date = cached.index.max()
                if last_date >= pd.to_datetime(end_date):
                    return cached.loc[start_date:end_date]

        df = self.loader.get_etf_price(symbol, start_date, end_date)
        if not df.empty and use_cache:
            # 合并缓存数据
            if not cached.empty:
                df = pd.concat([cached, df]).drop_duplicates().sort_index()
            self._save_to_cache(df, symbol, "etf")

        return df.loc[start_date:end_date] if not df.empty else df

    def get_index_price(self, symbol: str, start_date: str, end_date: str,
                       use_cache: bool = True) -> pd.DataFrame:
        if use_cache:
            cached = self._load_from_cache(symbol, "index")
            if not cached.empty:
                last_date = cached.index.max()
                if last_date >= pd.to_datetime(end_date):
                    return cached.loc[start_date:end_date]

        df = self.loader.get_index_price(symbol, start_date, end_date)
        if not df.empty and use_cache:
            if not cached.empty:
                df = pd.concat([cached, df]).drop_duplicates().sort_index()
            self._save_to_cache(df, symbol, "index")

        return df.loc[start_date:end_date] if not df.empty else df

def create_data_loader(config_path: str = "config.yaml") -> CachedDataLoader:
    """工厂函数创建数据加载器"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    data_source = config['data']['source']

    if data_source == "akshare":
        loader = AKShareLoader()
    elif data_source == "xtquant":
        loader = XTQuantLoader()
    elif data_source == "mock":
        loader = MockDataLoader()
    else:
        raise ValueError(f"Unsupported data source: {data_source}")

    return CachedDataLoader(loader)
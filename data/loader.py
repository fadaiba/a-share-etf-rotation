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
            import requests
            self.ak = ak

            # 禁用代理，避免代理错误
            session = requests.Session()
            session.trust_env = False  # 禁用系统代理设置
            session.proxies = {'http': None, 'https': None}  # 明确禁用代理

            # 替换akshare的session（如果可能）
            logger.info("akshare数据加载器初始化完成（已禁用代理）")

        except ImportError:
            raise ImportError("akshare not installed")

    def get_etf_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF日线数据"""
        try:
            logger.bind(context="data").debug(f"正在获取ETF {symbol} 数据: {start_date} 到 {end_date}")

            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '')
            end_date_fmt = end_date.replace('-', '')

            df = self.ak.fund_etf_hist_em(symbol=symbol, period="daily",
                                        start_date=start_date_fmt, end_date=end_date_fmt)

            if df.empty:
                logger.bind(context="data").warning(f"ETF {symbol} 数据为空")
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
            result = df[['open', 'high', 'low', 'close', 'volume']]

            logger.bind(context="data").debug(f"成功获取 {symbol} 数据，共 {len(result)} 条记录")
            return result

        except Exception as e:
            logger.bind(context="data").error(f"获取ETF {symbol} 数据失败: {e}")
            logger.bind(context="data").warning(f"建议：1) 检查网络连接 2) 尝试使用mock数据源 3) 检查日期格式")
            return pd.DataFrame()

    def get_index_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数日线数据"""
        try:
            logger.bind(context="data").debug(f"正在获取指数 {symbol} 数据: {start_date} 到 {end_date}")

            # 转换日期格式
            start_date_fmt = start_date.replace('-', '')
            end_date_fmt = end_date.replace('-', '')

            df = self.ak.stock_zh_index_daily_em(symbol=symbol,
                                               start_date=start_date_fmt, end_date=end_date_fmt)
            if df.empty:
                logger.bind(context="data").warning(f"指数 {symbol} 数据为空")
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
            result = df[['open', 'high', 'low', 'close', 'volume']]

            logger.bind(context="data").debug(f"成功获取指数 {symbol} 数据，共 {len(result)} 条记录")
            return result

        except Exception as e:
            logger.bind(context="data").error(f"获取指数 {symbol} 数据失败: {e}")
            return pd.DataFrame()

class MockDataLoader(DataLoader):
    """模拟数据加载器，用于测试"""

    def __init__(self):
        self.price_data = {}
        self._generate_mock_data()

    def _generate_mock_data(self):
        """生成模拟数据"""
        logger.info("开始生成模拟ETF数据")

        # 读取配置文件获取日期范围和ETF列表
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 从配置获取日期范围
            backtest_config = config.get('backtest', {})
            start_date = pd.to_datetime(backtest_config.get('start_date', '2020-01-01'))
            end_date = pd.to_datetime(backtest_config.get('end_date', '2025-12-31'))

            # 从配置获取ETF列表
            etf_codes = config.get('etf_pool', [
                "510300", "510500", "159915", "159919", "512100",
                "512880", "515050", "516160", "159949", "518880",
                "159952", "159926", "159941"
            ])

            # 从配置获取Mock数据生成参数
            mock_config = config.get('data', {}).get('mock', {})
            base_price_min = mock_config.get('base_price_min', 1.0)
            base_price_max = mock_config.get('base_price_max', 5.0)
            daily_return_mean = mock_config.get('daily_return_mean', 0.0005)
            daily_return_std = mock_config.get('daily_return_std', 0.02)
            high_low_range = mock_config.get('high_low_range', 0.01)
            open_close_range = mock_config.get('open_close_range', 0.005)
            volume_min = mock_config.get('volume_min', 100000)
            volume_max = mock_config.get('volume_max', 10000000)
            random_seed = mock_config.get('random_seed', 42)

        except Exception as e:
            # 配置读取失败时使用默认值
            logger.warning(f"读取配置文件失败，使用默认值: {e}")
            start_date = datetime(2020, 1, 1)
            end_date = datetime(2025, 12, 31)
            etf_codes = ["510300", "510500", "159915"]
            base_price_min = 1.0
            base_price_max = 5.0
            daily_return_mean = 0.0005
            daily_return_std = 0.02
            high_low_range = 0.01
            open_close_range = 0.005
            volume_min = 100000
            volume_max = 10000000
            random_seed = 42

        # 生成日期序列
        dates = pd.date_range(start_date, end_date, freq='D')

        logger.info(f"为 {len(etf_codes)} 个ETF生成数据，时间范围: {start_date.date()} 到 {end_date.date()}")
        logger.debug(f"Mock参数: base_price={base_price_min}-{base_price_max}, "
                    f"return_mean={daily_return_mean:.4f}, return_std={daily_return_std:.2f}")

        np.random.seed(random_seed)  # 使用配置的随机种子

        for symbol in etf_codes:
            # 生成价格数据
            n_days = len(dates)
            base_price = np.random.uniform(base_price_min, base_price_max)  # 使用配置的基础价格范围

            # 生成随机收益率（使用配置的收益率参数）
            returns = np.random.normal(daily_return_mean, daily_return_std, n_days)

            # 计算价格序列
            prices = [base_price]
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)

            # 生成OHLC数据（使用配置的波动范围）
            closes = np.array(prices)
            highs = closes * (1 + np.abs(np.random.normal(0, high_low_range, n_days)))
            lows = closes * (1 - np.abs(np.random.normal(0, high_low_range, n_days)))
            opens = closes + np.random.normal(0, closes * open_close_range, n_days)
            volumes = np.random.randint(volume_min, volume_max, n_days)

            # 创建DataFrame
            df = pd.DataFrame({
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            }, index=dates)

            self.price_data[symbol] = df

        logger.info(f"模拟数据生成完成，共 {len(self.price_data)} 个ETF，每天 {len(dates)} 条数据")

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
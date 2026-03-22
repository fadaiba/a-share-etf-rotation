#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的回测测试 - 验证导入修复
"""

import sys
import os
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有导入"""
    print("Testing imports...")

    try:
        from backtest.engine import BacktestEngine
        print("✓ BacktestEngine imported")

        from strategy.portfolio import PortfolioManager
        print("✓ PortfolioManager imported")

        from strategy.risk import RiskManager
        print("✓ RiskManager imported")

        from data.loader import MockDataLoader, CachedDataLoader
        print("✓ Data loaders imported")

        # 测试实例化
        engine = BacktestEngine()
        print("✓ BacktestEngine instantiated")

        portfolio = PortfolioManager()
        print("✓ PortfolioManager instantiated")

        risk = RiskManager()
        print("✓ RiskManager instantiated")

        print("\n=== All imports successful! ===")
        return True

    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_simple_backtest():
    """运行简化的回测测试"""
    print("\n=== Running Simple Backtest ===")

    try:
        # 加载配置
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print(f"ETF pool: {len(config['etf_pool'])} ETFs")
        print(f"Date range: {config['backtest']['start_date']} to {config['backtest']['end_date']}")

        # 创建数据加载器
        from data.loader import MockDataLoader, CachedDataLoader
        data_loader = CachedDataLoader(MockDataLoader())

        # 加载少量数据进行测试
        test_etfs = config['etf_pool'][:3]  # 只测试前3个
        price_data = {}

        for symbol in test_etfs:
            df = data_loader.get_etf_price(symbol, '2020-01-01', '2020-12-31')
            if not df.empty:
                price_data[symbol] = df
                print(f"✓ Loaded {symbol}: {len(df)} days")

        if price_data:
            print(f"\nSuccessfully loaded {len(price_data)} ETFs for testing")
            return True
        else:
            print("No data loaded")
            return False

    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        success = run_simple_backtest()

    if success:
        print("\n🎉 All tests passed! Import issue resolved.")
    else:
        print("\n❌ Tests failed.")
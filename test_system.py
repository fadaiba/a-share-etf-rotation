#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统测试脚本
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有模块导入"""
    try:
        # 简化测试，只测试关键模块
        from strategy.factors import FactorCalculator
        from strategy.risk import RiskManager
        print("✓ 核心模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_config():
    """测试配置加载"""
    try:
        import yaml
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✓ 配置加载成功，ETF池包含 {len(config['etf_pool'])} 个标的")
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

def test_factor_calculation():
    """测试因子计算"""
    try:
        import pandas as pd
        import numpy as np
        from strategy.factors import FactorCalculator

        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        test_df = pd.DataFrame({
            'close': np.random.uniform(3.0, 4.0, 100)
        }, index=dates)

        calculator = FactorCalculator()
        momentum = calculator.calculate_momentum(test_df)
        trend = calculator.calculate_trend(test_df)
        final_score = calculator.calculate_final_score(momentum, trend)

        print(f"✓ 因子计算测试成功: momentum={momentum:.4f}, trend={trend:.4f}, score={final_score:.4f}")
        return True
    except Exception as e:
        print(f"✗ 因子计算测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=== A股ETF量化交易系统测试 ===\n")

    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config),
        ("因子计算", test_factor_calculation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"测试: {test_name}")
        if test_func():
            passed += 1
        print()

    print(f"=== 测试结果: {passed}/{total} 通过 ===")

    if passed == total:
        print("🎉 系统测试全部通过！可以开始使用。")
        print("\n运行回测: python main_backtest.py")
        print("运行实盘: python main_live.py")
    else:
        print("❌ 部分测试失败，请检查代码。")

if __name__ == "__main__":
    main()
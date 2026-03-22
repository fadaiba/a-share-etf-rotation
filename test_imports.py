#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print('Testing imports...')

try:
    from backtest.engine import BacktestEngine
    print('✓ BacktestEngine import successful')

    from strategy.risk import RiskManager
    print('✓ RiskManager import successful')

    from strategy.portfolio import PortfolioManager
    print('✓ PortfolioManager import successful')

    # 测试BacktestEngine实例化
    engine = BacktestEngine()
    print('✓ BacktestEngine instantiation successful')

    print('All imports working correctly!')

except Exception as e:
    print(f'✗ Import error: {e}')
    import traceback
    traceback.print_exc()
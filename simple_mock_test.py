#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单Mock数据测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print('Testing mock data loader...')
from data.loader import MockDataLoader
loader = MockDataLoader()

# Test loading one ETF
df = loader.get_etf_price('510300', '2020-01-01', '2020-01-31')
print(f'Data shape: {df.shape}')
if not df.empty:
    print('Sample data:')
    print(df.head(3))
    print(f'Date range: {df.index.min()} to {df.index.max()}')
else:
    print('No data loaded')

print('Mock data test completed.')
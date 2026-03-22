#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF代码验证脚本
验证ETF池中的ETF代码格式和基本有效性
"""

import yaml
import re

def validate_etf_format(etf_code):
    """验证ETF代码格式"""
    # A股ETF代码规则：
    # 上海ETF: 5开头，6位数字
    # 深圳ETF: 1或0开头，6位数字
    pattern = r'^(5\d{5}|1\d{5}|0\d{5})$'
    return bool(re.match(pattern, etf_code))

def get_etf_category(etf_code):
    """根据代码判断ETF类别"""
    if etf_code.startswith('5'):
        return "上海ETF"
    elif etf_code.startswith('1'):
        return "深圳ETF"
    elif etf_code.startswith('0'):
        return "深圳ETF"
    else:
        return "未知"

def validate_etf_codes():
    """验证ETF代码有效性"""
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    etf_pool = config['etf_pool']
    print(f"验证ETF池中的 {len(etf_pool)} 个ETF代码...")
    print("="*60)

    valid_codes = []
    invalid_codes = []

    # 已知的ETF代码映射（部分）
    known_etfs = {
        "510300": "沪深300ETF",
        "510500": "中证500ETF",
        "159915": "创业板ETF",
        "159919": "沪深300ETF",
        "512100": "医药ETF",
        "512880": "证券ETF",
        "515050": "5GETF",
        "516160": "新能源ETF",
        "159949": "恒生ETF",
        "518880": "黄金ETF",
        "159952": "创业板ETF",
        "159926": "国债ETF",
        "159941": "纳斯达克ETF"
    }

    for etf_code in etf_pool:
        is_valid_format = validate_etf_format(etf_code)
        category = get_etf_category(etf_code)
        name = known_etfs.get(etf_code, "未知ETF")

        if is_valid_format:
            print("2d"            valid_codes.append(etf_code)
        else:
            print("2d"            invalid_codes.append(etf_code)

    print("\n" + "="*60)
    print("验证结果:")
    print(f"有效ETF: {len(valid_codes)} 个")
    print(f"无效ETF: {len(invalid_codes)} 个")

    if invalid_codes:
        print(f"\n无效ETF列表: {invalid_codes}")

    # 显示ETF分类统计
    print("
ETF分类统计:")
    categories = {}
    for etf in valid_codes:
        cat = get_etf_category(etf)
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in categories.items():
        print(f"  {cat}: {count} 个")

    return valid_codes, invalid_codes

if __name__ == "__main__":
    validate_etf_codes()
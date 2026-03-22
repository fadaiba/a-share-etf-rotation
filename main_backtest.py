#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股ETF量化交易系统 - 回测主程序
"""

import sys
import os
import yaml
import pandas as pd
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入日志模块
from logger import logger, log_backtest_start, log_backtest_progress, log_performance_metrics

from data.loader import create_data_loader
from strategy.portfolio import PortfolioManager
from backtest.engine import BacktestEngine
from backtest.metrics import PerformanceMetrics

def load_config():
    """加载配置"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def prepare_data(config):
    """准备数据"""
    logger.info("开始准备回测数据")

    # 尝试使用配置的数据源
    data_source = config['data']['source']

    # 如果是akshare，先尝试加载，失败则自动回退到mock
    if data_source == 'akshare':
        try:
            logger.info("尝试使用akshare数据源...")

            # 禁用代理环境变量
            import os
            os.environ['NO_PROXY'] = '*'
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''

            from data.loader import AKShareLoader, CachedDataLoader
            loader = AKShareLoader()

            # 测试是否能正常获取数据
            test_df = loader.get_etf_price('510300', '2024-01-01', '2024-01-10')

            if test_df.empty:
                logger.warning("akshare数据获取失败，自动切换到mock数据源")
                from data.loader import MockDataLoader
                loader = MockDataLoader()

            data_loader = CachedDataLoader(loader)

        except Exception as e:
            logger.warning(f"akshare初始化失败: {e}，自动切换到mock数据源")
            from data.loader import MockDataLoader, CachedDataLoader
            data_loader = CachedDataLoader(MockDataLoader())
    elif data_source == 'mock':
        # 直接使用mock数据源
        from data.loader import MockDataLoader, CachedDataLoader
        logger.info("使用mock数据源")
        data_loader = CachedDataLoader(MockDataLoader())
    elif data_source == 'xtquant':
        # 使用xtquant数据源（需要迅投平台）
        try:
            from data.loader import XTQuantLoader, CachedDataLoader
            logger.info("使用xtquant数据源")
            data_loader = CachedDataLoader(XTQuantLoader())
        except NameError:
            logger.error("XTQuantLoader未实现，请安装迅投量化平台或切换到mock数据源")
            raise
        except Exception as e:
            logger.warning(f"xtquant初始化失败: {e}，切换到mock数据源")
            from data.loader import MockDataLoader, CachedDataLoader
            data_loader = CachedDataLoader(MockDataLoader())
    else:
        # 未知数据源，回退到mock
        logger.warning(f"未知数据源: {data_source}，切换到mock数据源")
        from data.loader import MockDataLoader, CachedDataLoader
        data_loader = CachedDataLoader(MockDataLoader())

    etf_pool = config['etf_pool']
    start_date = config['backtest']['start_date']
    end_date = config['backtest']['end_date']

    logger.info(f"ETF池包含 {len(etf_pool)} 个ETF: {etf_pool[:5]}...")  # 只显示前5个
    logger.info(f"回测时间范围: {start_date} 到 {end_date}")

    # 加载ETF数据
    price_data = {}
    loaded_count = 0
    failed_count = 0

    for symbol in etf_pool:
        logger.debug(f"加载ETF数据: {symbol}")
        df = data_loader.get_etf_price(symbol, start_date, end_date)
        if not df.empty:
            price_data[symbol] = df
            loaded_count += 1
            logger.debug(f"  {symbol}: 加载了 {len(df)} 天的数据")
        else:
            failed_count += 1
            logger.warning(f"  {symbol}: 未加载到数据")

    logger.info(f"ETF数据加载完成: 成功 {loaded_count} 个，失败 {failed_count} 个")

    # 加载指数数据（用于市场过滤）
    index_symbol = config['risk']['market_filter']['index']
    logger.debug(f"加载指数数据: {index_symbol}")
    index_df = data_loader.get_index_price(index_symbol, start_date, end_date)

    if not index_df.empty:
        logger.info(f"指数数据加载完成: {index_symbol}, {len(index_df)} 天的数据")
    else:
        logger.warning(f"指数数据加载失败: {index_symbol}")

    logger.info(f"数据准备完成: 加载了 {len(price_data)} 个ETF和指数数据")
    return price_data, index_df

def strategy_function(current_date, current_positions, current_prices, total_value, price_data=None, index_df=None):
    """策略函数 - 完整的量化策略实现"""
    try:
        logger.bind(context="strategy").debug(f"执行策略: {current_date}, 总价值: {total_value:,.2f}")

        config = load_config()
        portfolio_manager = PortfolioManager()

        # 如果没有提供历史数据，使用简化逻辑
        if price_data is None or index_df is None:
            logger.bind(context="strategy").warning("无历史数据，使用简化策略")
            # 简化的ETF选择（实际应该基于历史数据）
            selected_etfs = config['etf_pool'][:3]  # 选择前3个

            # 计算权重（等权重）
            weights = {etf: 1.0 / len(selected_etfs) for etf in selected_etfs}
        else:
            # 完整的策略流程
            # 1. ETF选择
            selected_etfs = portfolio_manager.select_etfs(config['etf_pool'], price_data)
            logger.bind(context="strategy").info(f"ETF选择完成: 选中 {len(selected_etfs)} 个ETF")

            # 2. 计算权重
            weights = portfolio_manager.calculate_weights(selected_etfs, price_data, index_df)
            logger.bind(context="strategy").debug(f"权重计算完成: {len(weights)} 个ETF有权重")

        # 3. 计算调仓交易
        trades = portfolio_manager.rebalance_portfolio(
            current_positions, weights, current_prices, total_value
        )
        logger.bind(context="strategy").info(f"调仓计算完成: 生成 {len(trades)} 个交易")

        # 4. 应用交易限制
        trades = portfolio_manager.apply_trading_restrictions(trades, price_data or {})
        logger.bind(context="strategy").debug(f"交易限制应用完成: 剩余 {len(trades)} 个有效交易")

        return trades

    except Exception as e:
        logger.bind(context="strategy").error(f"策略执行错误: {e}")
        return {}

def run_backtest():
    """运行回测"""
    logger.info("=== 开始A股ETF量化交易系统回测 ===")

    config = load_config()
    log_backtest_start(config)

    # 准备数据
    price_data, index_df = prepare_data(config)

    if not price_data:
        logger.error("无有效数据，回测终止")
        return

    # 创建回测引擎
    logger.info("初始化回测引擎")
    engine = BacktestEngine()

    # 运行回测
    start_date = config['backtest']['start_date']
    end_date = config['backtest']['end_date']
    initial_cash = config['backtest'].get('initial_cash', 1000000.0)  # 从配置读取初始资金

    logger.info(f"开始执行回测: {start_date} 到 {end_date}, 初始资金: {initial_cash:,.0f}")
    start_time = datetime.now()

    account = engine.run_backtest(
        strategy_function, start_date, end_date, initial_cash, price_data, index_df
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"回测执行完成，耗时: {duration:.2f} 秒")

    # 保存结果
    logger.info("保存回测结果")
    engine.save_results(account, "backtest_results.json")

    # 计算绩效指标
    logger.info("计算绩效指标")
    metrics = PerformanceMetrics(account.history)

    # 生成报告
    report = metrics.generate_report()
    log_performance_metrics(report)

    # 保存详细报告
    with open("backtest_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("回测完成，结果已保存到 backtest_results.json 和 backtest_report.json")

    # 生成交易报告
    logger.info("生成交易报告")
    try:
        start_date = config['backtest']['start_date']
        end_date = config['backtest']['end_date']
        report_path = engine.save_trade_report(start_date, end_date)
        logger.info(f"交易报告已保存到: {report_path}")
    except Exception as e:
        logger.warning(f"交易报告生成失败: {e}")
        import traceback
        traceback.print_exc()

    # 生成图表
    try:
        metrics.plot_performance("backtest_performance.png")
        logger.info("绩效图表已保存到: backtest_performance.png")
    except Exception as e:
        logger.warning(f"图表生成失败: {e}")

    logger.info("=== 回测流程全部完成 ===")

if __name__ == "__main__":
    try:
        run_backtest()
    except Exception as e:
        print(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
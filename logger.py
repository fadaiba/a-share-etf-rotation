#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
使用loguru库提供统一的日志功能
"""

import os
import sys
from pathlib import Path
from loguru import logger

def setup_logger(log_level: str = "INFO", log_to_file: bool = True):
    """配置loguru日志器"""

    # 移除默认的handler
    logger.remove()

    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        enqueue=True  # 异步写入，提高性能
    )

    # 文件输出
    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 普通日志文件
        logger.add(
            log_dir / "trading_system.log",
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
            enqueue=True
        )

        # 错误日志文件
        logger.add(
            log_dir / "trading_system_error.log",
            format=log_format,
            level="ERROR",
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
            enqueue=True
        )

        # 回测专用日志
        logger.add(
            log_dir / "backtest.log",
            format=log_format,
            level=log_level,
            rotation="50 MB",
            retention="90 days",
            encoding="utf-8",
            enqueue=True,
            filter=lambda record: "backtest" in record["extra"] or "strategy" in record["extra"]
        )

    return logger

# 创建全局logger实例
logger = setup_logger()

def get_logger(name: str = None):
    """获取带有上下文的logger"""
    if name:
        return logger.bind(module=name)
    return logger

# 便捷函数
def log_backtest_start(config: dict):
    """记录回测开始信息"""
    logger.bind(context="backtest").info("开始回测")
    logger.bind(context="backtest").info(f"ETF池: {config['etf_pool']}")
    logger.bind(context="backtest").info(f"时间范围: {config['backtest']['start_date']} 到 {config['backtest']['end_date']}")
    logger.bind(context="backtest").info(f"初始资金: {config['backtest'].get('initial_cash', 1000000)}")

def log_backtest_progress(date: str, total_value: float, trades_count: int):
    """记录回测进度"""
    logger.bind(context="backtest").info(
        f"日期: {date} | 总价值: {total_value:,.2f} | 交易数量: {trades_count}"
    )

def log_strategy_execution(date: str, selected_etfs: list, weights: dict):
    """记录策略执行信息"""
    logger.bind(context="strategy").info(f"日期: {date} | 选中ETF: {selected_etfs}")
    logger.bind(context="strategy").debug(f"目标权重: {weights}")

def log_trade_execution(etf: str, action: str, shares: float, price: float, value: float):
    """记录交易执行信息"""
    logger.bind(context="trading").info(
        f"执行交易: {etf} | {action} | 数量: {shares:.0f} | 价格: {price:.4f} | 价值: {value:,.2f}"
    )

def log_error(error_msg: str, exc_info=None):
    """记录错误信息"""
    if exc_info:
        logger.bind(context="error").exception(error_msg)
    else:
        logger.bind(context="error").error(error_msg)

def log_performance_metrics(metrics: dict):
    """记录绩效指标"""
    logger.bind(context="performance").info("回测绩效指标:")
    for category, indicators in metrics.items():
        logger.bind(context="performance").info(f"  {category}:")
        for key, value in indicators.items():
            logger.bind(context="performance").info(f"    {key}: {value}")
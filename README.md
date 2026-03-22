# A股ETF量化交易系统

## 项目概述

这是一个基于多因子动量策略的A股ETF量化交易系统，实现了ETF聚类筛选、风险控制、回测分析和实盘交易功能。

## 主要特性

- **ETF聚类筛选**：使用层次聚类降低同质化风险
- **多因子Alpha模型**：质量动量 + 趋势强度双因子评分
- **多层风险控制**：市场过滤、下行波动控制、风险预算、波动率目标控制、回撤控制、止损
- **完整回测系统**：支持日频回测，包含详细绩效分析
- **实盘交易**：集成xtquant API，支持TWAP拆单执行

## 系统架构

```
strategy/          # 策略模块
├── factors.py     # 因子计算
├── clustering.py  # 聚类分析
├── risk.py        # 风险控制
└── portfolio.py   # 组合管理

backtest/          # 回测模块
├── engine.py      # 回测引擎
└── metrics.py     # 绩效指标

execution/         # 执行模块
├── xtquant_api.py # xtquant接口
└── trader.py      # 交易执行

data/              # 数据模块
└── loader.py      # 数据加载器
```

## 安装依赖

```bash
pip install numpy pandas scipy pyyaml matplotlib akshare
```

## 配置说明

编辑 `config.yaml` 文件进行参数配置：

- `etf_pool`: ETF标的池
- `clustering`: 聚类参数
- `factors`: 因子权重参数
- `risk`: 风险控制参数
- `trading`: 交易参数
- `backtest`: 回测参数
- `live`: 实盘参数

## 使用方法

### 回测

```bash
python main_backtest.py
```

### 实盘交易

```bash
python main_live.py
```

## 策略逻辑

1. **数据准备**：加载ETF和指数历史数据
2. **聚类筛选**：基于120日收益率进行层次聚类，每个cluster选20日收益率最高ETF
3. **因子评分**：计算质量动量和趋势强度，最终选择Top 3 ETF
4. **风险控制**：
   - 市场过滤：沪深300 < MA60时空仓
   - 风险预算：基于下行波动率的权重分配
   - 波动率目标：控制年化波动率至10%
   - 回撤控制：最大回撤>5%时仓位减半
   - 止损：单标跌幅>8%时卖出
5. **交易执行**：每周调仓，TWAP 5次拆单

## 绩效指标

- 年化收益、累计收益
- 波动率、最大回撤
- 夏普比率、索提诺比率
- 胜率、盈亏比
- Alpha、Beta（相对沪深300）

## 注意事项

- 回测结果不代表未来表现
- 实盘交易存在风险，请谨慎使用
- 建议先进行充分的回测验证
- 交易前请确保xtquant环境正确配置

## 开发约束

- 禁止使用未来数据
- 所有参数必须配置化
- 支持新因子和策略扩展
- 数据源可替换（akshare/xtquant）

## 许可证

本项目仅供学习和研究使用，不构成投资建议。
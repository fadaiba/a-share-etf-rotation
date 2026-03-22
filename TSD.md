
# 📘 一、项目概述

## 🎯 项目目标

开发一个A股ETF量化交易系统，实现：

* ETF聚类筛选
* 多因子动量策略（Sharpe优化版）
* 多层风险控制
* 回测系统（含绩效分析）
* 实盘交易（xtquant接入）

---

# 🧠 二、策略逻辑（必须严格实现）

---

## 1️⃣ 标的池

* A股ETF（初始列表由配置提供）
* 示例：

  ```python
  ["510300","510500","159915","512100","512880","515050","516160","159949"]
  ```

---

## 2️⃣ 聚类（降低同质化风险）

### 输入：

* ETF历史收益率（120日）

### 方法：

* 层次聚类（Hierarchical Clustering）
* 距离：

  ```
  distance = 1 - correlation
  ```

### 输出：

```python
{etf: cluster_id}
```

---

## 3️⃣ ETF池筛选

每个cluster选：

* 20日收益率最高ETF

输出：

```python
etf_pool = [etf1, etf2, ...]
```

---

## 4️⃣ 核心Alpha模型（重点）

### ✅ 因子1：质量动量（核心）

```python
score = (0.6 * ret20 + 0.4 * ret60) / volatility
```

---

### ✅ 因子2：趋势强度

```python
trend = (MA20 - MA60) / MA60
```

---

### ✅ 最终评分

```python
final_score = 0.7 * momentum + 0.3 * trend
```

---

## 5️⃣ ETF选择

* 按评分排序
* 选 Top 3

---

# 🛡 三、风险控制（必须全部实现）

---

## ✅ 1. 市场过滤（强制）

标的：沪深300指数

规则：

```python
if close < MA60:
    空仓
```

---

## ✅ 2. 下行波动控制（替代普通波动）

```python
downside_vol = std(returns where return < 0)
```

---

## ✅ 3. 风险预算（核心）

```python
weight = 1 / downside_vol
normalize(weights)
```

---

## ✅ 4. 波动率目标控制

目标：

```text
年化波动 = 10%
```

调整：

```python
scale = target_vol / current_vol
```

---

## ✅ 5. 回撤控制

```python
if drawdown < -5%:
    仓位减半
```

---

## ✅ 6. 止损（单标的）

```python
if return < -8%:
    卖出
```

---

# ⚙️ 四、交易逻辑

---

## 1️⃣ 调仓频率

* 每周1–2次（默认每周一次）

---

## 2️⃣ 调仓流程

```text
获取当前持仓
计算目标权重
计算差值
执行：
    卖出多余
    买入不足
```

---

## 3️⃣ 执行优化（必须）

### TWAP拆单：

```python
分5次下单
每次间隔3秒
```

---

## 4️⃣ 交易限制

* 最小交易单位：100股
* 涨停：禁止买入
* 跌停：禁止卖出

---

# 📊 五、回测系统要求

---

## 1️⃣ 回测引擎

必须支持：

* 日频回测
* 手续费：万2
* 滑点：0.1%

---

## 2️⃣ 账户模型

```python
cash
positions
total_value
```

---

## 3️⃣ 输出指标（必须）

### 收益类：

* 年化收益
* 累计收益

### 风险类：

* 最大回撤
* 波动率

### 风险收益：

* 夏普比率
* 超额收益（对比 沪深300指数）

---

## 4️⃣ 图表输出

* 净值曲线
* 回撤曲线
* 对比指数

---

# 🔌 六、实盘交易（xtquant）

---

## 1️⃣ 必须实现接口

```python
connect()
get_positions()
order_target_percent()
get_account()
```

---

## 2️⃣ 调仓时间

* 每日 14:55

---

## 3️⃣ 实时风控

* 每5分钟检查止损

---

## 4️⃣ 异常处理

* 下单失败 → 重试3次
* 网络错误 → 自动重连

---

# 🧱 七、系统架构

```text
strategy/
    factors.py
    clustering.py
    risk.py
    portfolio.py

backtest/
    engine.py
    metrics.py

execution/
    xtquant_api.py
    trader.py

data/
    loader.py

main_backtest.py
main_live.py
```

---

# 💾 八、数据与存储

---

## 必须实现：

### 1️⃣ 本地缓存

```text
data/cache/
```

---

### 2️⃣ 持仓持久化

```text
positions.json
```

---

### 3️⃣ 日志系统

```text
logs/
```

---

# ⚠️ 九、关键开发约束

---

## ❗1. 禁止未来函数

* 回测中不能用未来数据

---

## ❗2. 配置化

所有参数必须在：

```yaml
config.yaml
```

---

## ❗3. 可扩展性

必须支持：

* 新因子接入
* 多策略组合

---

## ❗4. 数据源解耦

* 不允许写死 akshare
* 需支持替换为 xtquant 

---

# 🚀 十、交付要求

开发人员需交付：

---

## ✅ 1. 完整代码工程

* 可运行
* 模块清晰

---

## ✅ 2. 回测报告

包含：

* 收益曲线
* 指标统计

---

## ✅ 3. 实盘运行脚本

```bash
python main_live.py
```

---

## ✅ 4. 文档

* README
* 配置说明

---

# 🏁 最终总结（给开发人员）

这是一个：

> **多因子ETF轮动 + 风险预算 + 波动控制的量化交易系统**

核心目标：

* Sharpe Ratio ≥ 1.5（目标2.0+）
* 最大回撤 ≤ 15%

---

# 🔥 给你的建议（很关键）

把这份文档发给开发时，加一句：

```text
优先保证：
1. 风控正确
2. 回测无未来函数
3. 可扩展性

其次才是收益优化
```



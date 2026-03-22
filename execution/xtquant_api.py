import time
import json
import os
from typing import Dict, List, Optional
import yaml

class XTQuantAPI:
    """xtquant交易接口封装"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config['live']

        # 初始化xtquant连接（这里是模拟）
        self.connected = False
        self.session_id = None

    def connect(self) -> bool:
        """连接xtquant"""
        try:
            # 这里应该实现真实的xtquant连接
            # from xtquant import xtdata, xttrader
            # self.session_id = xttrader.login()
            # xtdata.connect()
            print("XTQuant connected (simulated)")
            self.connected = True
            return True
        except Exception as e:
            print(f"XTQuant connection failed: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.connected:
            # xtdata.disconnect()
            print("XTQuant disconnected")
            self.connected = False

    def get_account(self) -> Dict:
        """获取账户信息"""
        if not self.connected:
            return {}

        try:
            # 模拟账户信息
            return {
                'cash': 1000000.0,
                'total_value': 1000000.0,
                'positions': {}
            }
        except Exception as e:
            print(f"Get account failed: {e}")
            return {}

    def get_positions(self) -> Dict[str, Dict]:
        """获取持仓信息"""
        if not self.connected:
            return {}

        try:
            # 模拟持仓信息
            return {
                '510300': {'shares': 1000, 'avg_price': 3.5},
                '510500': {'shares': 800, 'avg_price': 2.8}
            }
        except Exception as e:
            print(f"Get positions failed: {e}")
            return {}

    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        if not self.connected:
            return 0.0

        try:
            # 模拟获取价格
            # price = xtdata.get_market_data(['close'], [symbol])[symbol]['close']
            return 3.5  # 模拟价格
        except Exception as e:
            print(f"Get price failed for {symbol}: {e}")
            return 0.0

    def order_target_percent(self, symbol: str, target_percent: float) -> bool:
        """调整持仓到目标百分比"""
        if not self.connected:
            return False

        try:
            account = self.get_account()
            total_value = account.get('total_value', 0)
            target_value = total_value * target_percent
            current_price = self.get_current_price(symbol)

            if current_price == 0:
                return False

            target_shares = int(target_value / current_price)

            # 获取当前持仓
            positions = self.get_positions()
            current_shares = positions.get(symbol, {}).get('shares', 0)

            shares_diff = target_shares - current_shares

            if shares_diff > 0:
                # 买入
                return self._place_order(symbol, shares_diff, 'buy')
            elif shares_diff < 0:
                # 卖出
                return self._place_order(symbol, abs(shares_diff), 'sell')
            else:
                return True  # 无需交易

        except Exception as e:
            print(f"Order target percent failed for {symbol}: {e}")
            return False

    def _place_order(self, symbol: str, shares: int, action: str) -> bool:
        """下单"""
        try:
            # TWAP拆单
            twap_splits = self.config.get('twap_splits', 5)
            twap_interval = self.config.get('twap_interval', 3)

            shares_per_order = shares // twap_splits
            remainder = shares % twap_splits

            for i in range(twap_splits):
                order_shares = shares_per_order + (remainder if i == 0 else 0)

                if order_shares == 0:
                    continue

                # 模拟下单
                # order_id = xttrader.order(symbol, order_shares, action)
                print(f"Placed {action} order for {order_shares} shares of {symbol}")

                if i < twap_splits - 1:
                    time.sleep(twap_interval)

            return True

        except Exception as e:
            print(f"Place order failed: {e}")
            return False

    def cancel_all_orders(self) -> bool:
        """取消所有挂单"""
        if not self.connected:
            return False

        try:
            # xttrader.cancel_all()
            print("Cancelled all orders")
            return True
        except Exception as e:
            print(f"Cancel orders failed: {e}")
            return False

class LiveTrader:
    """实盘交易器"""

    def __init__(self, api: XTQuantAPI):
        self.api = api
        self.positions_file = "positions.json"
        self.last_check = 0

    def load_positions(self) -> Dict[str, Dict]:
        """加载持仓记录"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_positions(self, positions: Dict[str, Dict]):
        """保存持仓记录"""
        with open(self.positions_file, 'w', encoding='utf-8') as f:
            json.dump(positions, f, ensure_ascii=False, indent=2)

    def execute_rebalance(self, target_weights: Dict[str, float]):
        """执行调仓"""
        if not self.api.connected:
            print("API not connected")
            return False

        try:
            # 获取当前持仓
            current_positions = self.api.get_positions()
            account = self.api.get_account()
            total_value = account.get('total_value', 0)

            success = True
            for symbol, target_weight in target_weights.items():
                if not self.api.order_target_percent(symbol, target_weight):
                    success = False

            if success:
                # 保存新持仓
                self.save_positions(current_positions)

            return success

        except Exception as e:
            print(f"Rebalance failed: {e}")
            return False

    def check_stop_loss(self):
        """检查止损"""
        current_time = time.time()
        if current_time - self.last_check < 300:  # 5分钟检查一次
            return

        try:
            positions = self.api.get_positions()

            for symbol, position in positions.items():
                current_price = self.api.get_current_price(symbol)
                entry_price = position.get('avg_price', 0)

                # 简化的止损逻辑
                if current_price > 0 and entry_price > 0:
                    return_pct = (current_price - entry_price) / entry_price
                    if return_pct < -0.08:  # 8%止损
                        # 卖出
                        shares = position.get('shares', 0)
                        if self.api._place_order(symbol, shares, 'sell'):
                            print(f"Stop loss triggered for {symbol}")

            self.last_check = current_time

        except Exception as e:
            print(f"Stop loss check failed: {e}")

    def run_live_trading(self, strategy_func):
        """运行实盘交易"""
        if not self.api.connect():
            return

        print("Live trading started")

        try:
            while True:
                current_time = time.localtime()
                current_hour = current_time.tm_hour
                current_min = current_time.tm_min

                # 每日14:55调仓
                if current_hour == 14 and current_min == 55:
                    try:
                        # 获取目标权重
                        target_weights = strategy_func()
                        self.execute_rebalance(target_weights)
                        print("Rebalance completed")
                    except Exception as e:
                        print(f"Rebalance error: {e}")

                # 每5分钟检查止损
                self.check_stop_loss()

                time.sleep(60)  # 每分钟检查一次

        except KeyboardInterrupt:
            print("Live trading stopped")
        finally:
            self.api.disconnect()
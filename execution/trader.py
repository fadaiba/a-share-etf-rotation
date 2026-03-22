import time
import logging
import os
from typing import Dict, List
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trader.log'),
        logging.StreamHandler()
    ]
)

class Trader:
    """交易执行器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.config = config['trading']

        # 确保日志目录存在
        os.makedirs('logs', exist_ok=True)

    def execute_trades(self, trades: Dict[str, Dict]) -> Dict[str, bool]:
        """执行交易"""
        results = {}

        for symbol, trade in trades.items():
            try:
                success = self._execute_single_trade(symbol, trade)
                results[symbol] = success

                if success:
                    logging.info(f"Trade executed: {trade['action']} {trade['shares']} shares of {symbol}")
                else:
                    logging.error(f"Trade failed: {trade['action']} {trade['shares']} shares of {symbol}")

            except Exception as e:
                logging.error(f"Trade error for {symbol}: {e}")
                results[symbol] = False

        return results

    def _execute_single_trade(self, symbol: str, trade: Dict) -> bool:
        """执行单笔交易"""
        action = trade['action']
        shares = trade['shares']

        # TWAP拆单执行
        twap_splits = self.config['twap_splits']
        twap_interval = self.config['twap_interval']

        shares_per_order = shares // twap_splits
        remainder = shares % twap_splits

        success_count = 0

        for i in range(twap_splits):
            order_shares = shares_per_order + (remainder if i == 0 else 0)

            if order_shares == 0:
                continue

            # 模拟下单（实际应该调用xtquant API）
            if self._place_order(symbol, order_shares, action):
                success_count += 1
                logging.info(f"Order {i+1}/{twap_splits}: {action} {order_shares} shares of {symbol}")
            else:
                logging.error(f"Order {i+1}/{twap_splits} failed: {action} {order_shares} shares of {symbol}")

            # 间隔执行
            if i < twap_splits - 1:
                time.sleep(twap_interval)

        # 如果大部分订单成功，认为交易成功
        return success_count >= twap_splits * 0.8

    def _place_order(self, symbol: str, shares: int, action: str) -> bool:
        """下单（模拟）"""
        try:
            # 这里应该调用真实的交易API
            # 模拟成功率90%
            import random
            success = random.random() < 0.9

            if success:
                logging.info(f"Order placed: {action} {shares} shares of {symbol}")
            else:
                logging.warning(f"Order rejected: {action} {shares} shares of {symbol}")

            return success

        except Exception as e:
            logging.error(f"Place order error: {e}")
            return False

    def cancel_pending_orders(self) -> bool:
        """取消所有挂单"""
        try:
            # 模拟取消
            logging.info("Cancelled all pending orders")
            return True
        except Exception as e:
            logging.error(f"Cancel orders error: {e}")
            return False

    def get_order_status(self, order_id: str) -> Dict:
        """获取订单状态"""
        # 模拟订单状态
        return {
            'order_id': order_id,
            'status': 'filled',  # pending, filled, cancelled, rejected
            'filled_shares': 100,
            'avg_price': 3.5
        }

    def retry_failed_trades(self, failed_trades: Dict[str, Dict], max_retries: int = 3) -> Dict[str, bool]:
        """重试失败的交易"""
        results = {}

        for symbol, trade in failed_trades.items():
            success = False

            for attempt in range(max_retries):
                logging.info(f"Retry {attempt + 1}/{max_retries} for {symbol}")
                success = self._execute_single_trade(symbol, trade)

                if success:
                    break
                else:
                    time.sleep(1)  # 重试间隔

            results[symbol] = success

            if success:
                logging.info(f"Trade succeeded after retry: {symbol}")
            else:
                logging.error(f"Trade failed after {max_retries} retries: {symbol}")

        return results
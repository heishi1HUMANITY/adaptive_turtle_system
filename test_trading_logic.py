import unittest
import pandas as pd
import numpy as np # For NaN and other numerical utilities
from pandas.testing import assert_series_equal, assert_frame_equal
from datetime import datetime, timedelta
from typing import Union, Optional, List, Dict, Any # Added typing imports

import trading_logic as tl
from trading_logic import Order, Position, PortfolioManager, execute_order, calculate_position_size, run_strategy

class TestTradingLogic(unittest.TestCase):

    def setUp(self):
        """Setup common data for tests."""
        self.price_data = pd.DataFrame({ # For indicator tests
            'high': [10, 12, 11, 13, 14, 15, 13, 12, 11, 10],
            'low':  [8,  9,  10, 10, 11, 12, 11, 10, 9,  8],
            'close':[9,  11, 10, 12, 13, 14, 12, 11, 10, 9]
        })
        self.high_series = self.price_data['high']
        self.low_series = self.price_data['low']
        self.close_series = self.price_data['close']

        self.test_symbol = "TEST/USD"
        self.pip_point_value_per_unit = 0.0001
        self.lot_size_units = 100000

        self.config = {
            'pip_point_value': {self.test_symbol: self.pip_point_value_per_unit},
            'lot_size': {self.test_symbol: self.lot_size_units},
            'commission_per_lot': 5.0,
            'slippage_pips': 2.0,
            'initial_capital': 100000.0,
            'risk_per_trade': 0.01,
            'stop_loss_atr_multiplier': 2.0,
            'atr_period': 10,
            'max_units_per_market': {self.test_symbol: 400000},
            'total_portfolio_risk_limit': 0.05,
            'markets': [self.test_symbol],
            'entry_donchian_period': 5,
            'take_profit_long_exit_period': 3,
            'take_profit_short_exit_period': 3,
        }

        self.execute_order_slippage_pips = self.config['slippage_pips']
        self.execute_order_commission_per_lot = self.config['commission_per_lot']
        self.execute_order_pip_point_value = self.config['pip_point_value'][self.test_symbol]
        self.execute_order_lot_size = self.config['lot_size'][self.test_symbol]

        self.market_price_buy = 1.20000
        self.market_price_sell = 1.19000
        self.stop_price_buy = 1.20500
        self.stop_price_sell = 1.18500
        self.initial_capital = self.config['initial_capital']

    # --- START OF COPIED EXISTING TESTS (INDICATORS, SIGNALS, BASIC POS_SIZE, ORDER, POS, EXECUTE_ORDER) ---
    # This section represents all the tests from the previous state of the file.
    # For brevity in this diff, I'm not re-listing all of them but they are assumed to be here.
    # I will only show the changes for the PortfolioManager tests that are being uncommented and reviewed.
    # 1. Tests for calculate_donchian_channel (existing)
    def test_calculate_donchian_channel_basic(self):
        period = 3
        upper, lower = tl.calculate_donchian_channel(self.high_series, self.low_series, period)
        expected_upper = pd.Series([np.nan, np.nan, 12, 13, 14, 15, 15, 15, 13, 12], name='high')
        expected_lower = pd.Series([np.nan, np.nan, 8,  9,  10, 10, 11, 10, 9,  8], name='low')
        if upper.name is None: upper.name = 'high'
        if lower.name is None: lower.name = 'low'
        assert_series_equal(upper, expected_upper, check_dtype=False)
        assert_series_equal(lower, expected_lower, check_dtype=False)

    def test_calculate_donchian_channel_period_one(self):
        period = 1
        upper, lower = tl.calculate_donchian_channel(self.high_series, self.low_series, period)
        expected_upper = self.high_series.copy()
        expected_lower = self.low_series.copy()
        if upper.name is None: upper.name = 'high'
        if lower.name is None: lower.name = 'low'
        assert_series_equal(upper, expected_upper, check_dtype=False)
        assert_series_equal(lower, expected_lower, check_dtype=False)

    def test_calculate_donchian_channel_invalid_input(self):
        with self.assertRaises(TypeError):
            tl.calculate_donchian_channel("not a series", self.low_series, 3)
        with self.assertRaises(ValueError):
            tl.calculate_donchian_channel(self.high_series, self.low_series, 0)
        with self.assertRaises(ValueError):
            tl.calculate_donchian_channel(self.high_series, self.low_series, -1)

    # 2. Tests for calculate_atr (existing)
    def test_calculate_atr_basic(self):
        high = pd.Series([10, 12, 11, 13, 14])
        low = pd.Series(  [8,  9,  10, 10, 11])
        close = pd.Series([9,  11, 10, 12, 13])
        period = 3
        expected_atr = pd.Series([np.nan, np.nan, np.nan, (3.0+1.0+3.0)/3, (1.0+3.0+3.0)/3])
        atr = tl.calculate_atr(high, low, close, period)
        assert_series_equal(atr, expected_atr, check_dtype=False)

    def test_calculate_atr_period_one(self):
        high = pd.Series([10, 12, 11, 13, 14])
        low = pd.Series(  [8,  9,  10, 10, 11])
        close = pd.Series([9,  11, 10, 12, 13])
        period = 1
        expected_atr = pd.Series([np.nan, 3.0, 1.0, 3.0, 3.0])
        atr = tl.calculate_atr(high, low, close, period)
        assert_series_equal(atr, expected_atr, check_dtype=False)

    def test_calculate_atr_constant_price(self):
        high = pd.Series([10.0] * 5)
        low = pd.Series([10.0] * 5)
        close = pd.Series([10.0] * 5)
        period = 3
        expected_atr = pd.Series([np.nan, np.nan, np.nan, 0.0, 0.0])
        atr = tl.calculate_atr(high, low, close, period)
        assert_series_equal(atr, expected_atr, check_dtype=False)

    def test_calculate_atr_invalid_input(self):
        with self.assertRaises(TypeError):
            tl.calculate_atr("not series", self.low_series, self.close_series, 3)
        with self.assertRaises(ValueError):
            tl.calculate_atr(self.high_series, self.low_series, self.close_series, 0)
        with self.assertRaises(ValueError):
            tl.calculate_atr(self.high_series, self.low_series, self.close_series, -2)

    # 3. Tests for generate_entry_signals (existing)
    def test_generate_entry_signals_basic(self):
        close_prices = pd.Series([10, 11, 15, 14, 9, 8])
        donchian_upper = pd.Series([np.nan, 10, 11, 15, 15, 14])
        donchian_lower = pd.Series([np.nan, 8,  9,  10, 10, 9 ])
        entry_period = 3
        expected_signal = pd.Series([0, 0, 1, 1, -1, -1])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_no_signal(self):
        close_prices = pd.Series([10, 10.5, 10.8, 10.5, 10.2])
        donchian_upper = pd.Series([np.nan, 11, 11, 11, 11])
        donchian_lower = pd.Series([np.nan, 10, 10, 10, 10])
        entry_period = 3
        expected_signal = pd.Series([0, 0, 0, 0, 0])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_start_of_series_nan_bands(self):
        close_prices = pd.Series([10, 11, 12])
        donchian_upper = pd.Series([np.nan, np.nan, np.nan])
        donchian_lower = pd.Series([np.nan, np.nan, np.nan])
        entry_period = 20
        expected_signal = pd.Series([0, 0, 0])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_input_validation(self):
        with self.assertRaises(TypeError):
            tl.generate_entry_signals("c", self.high_series, self.low_series, 3)
        with self.assertRaises(ValueError):
            tl.generate_entry_signals(self.close_series, self.high_series, self.low_series, 0)

    # 4. Tests for generate_exit_signals (existing)
    def test_generate_exit_signals_long_exit(self):
        close_prices = pd.Series([15, 12, 10, 9, 8])
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9])
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])
        current_positions = pd.Series([0, 1, 1, 1, 1])
        exit_period_long = 10
        exit_period_short = 10
        expected_signal = pd.Series([0, 0, -1, -1, -1])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_short_exit(self):
        close_prices = pd.Series([10, 12, 15, 16, 17])
        donchian_lower_exit = pd.Series([np.nan, 8, 9, 10, 11])
        donchian_upper_exit = pd.Series([np.nan, 13, 14, 15, 15])
        current_positions = pd.Series([0, -1, -1, -1, -1])
        exit_period_long = 10
        exit_period_short = 10
        expected_signal = pd.Series([0, 0, 1, 1, 1])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_no_exit_if_no_position(self):
        close_prices = pd.Series([15, 12, 10, 9, 8])
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9])
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])
        current_positions = pd.Series([0, 0, 0, 0, 0])
        exit_period_long = 10
        exit_period_short = 10
        expected_signal = pd.Series([0, 0, 0, 0, 0])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_no_exit_if_wrong_position(self):
        close_prices = pd.Series([15, 12, 10, 9, 8])
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9])
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])
        current_positions = pd.Series([0, -1, -1, -1, -1])
        exit_period_long = 10
        exit_period_short = 10
        expected_signal = pd.Series([0, 0, 0, 0, 0])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_input_validation(self):
        pos = pd.Series([0,1,0,-1])
        with self.assertRaises(TypeError):
            tl.generate_exit_signals("c", self.high_series, self.low_series, 10, 10, pos)
        with self.assertRaises(ValueError):
            tl.generate_exit_signals(self.close_series, self.high_series, self.low_series, 0, 10, pos)
        with self.assertRaises(ValueError):
            tl.generate_exit_signals(self.close_series, self.high_series, self.low_series, 10, -1, pos)

    # 5. Tests for calculate_position_size (existing, uses direct import)
    def test_calculate_position_size_basic(self):
        size_clarified_atr = calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.02
        )
        self.assertEqual(size_clarified_atr, 100000)

    def test_calculate_position_size_atr_zero(self): # Uses direct import
        size = calculate_position_size(100000, 0.01, 0, 10, 100000, 1000000, 0, 0.05, 0.02)
        self.assertEqual(size, 0)

    def test_calculate_position_size_pip_value_zero(self): # Uses direct import
        size = calculate_position_size(100000, 0.01, 50, 0, 100000, 1000000, 0, 0.05, 0.02)
        self.assertEqual(size, 0)

    # --- Tests for Order class ---
    def test_order_instantiation(self):
        order = Order(
            order_id="test_id_001", symbol=self.test_symbol, order_type="market",
            trade_action="buy", quantity=10000, order_price=None,
            status="pending", fill_price=None, commission=0.0, slippage=0.0
        )
        self.assertEqual(order.order_id, "test_id_001")
        self.assertEqual(order.symbol, self.test_symbol)
        self.assertEqual(order.order_type, "market")
        self.assertEqual(order.trade_action, "buy")
        self.assertEqual(order.quantity, 10000)
        self.assertIsNone(order.order_price)
        self.assertEqual(order.status, "pending")
        self.assertIsNone(order.fill_price)
        self.assertIsInstance(order.timestamp_created, datetime)
        self.assertIsNone(order.timestamp_filled)
        self.assertEqual(order.commission, 0.0)
        self.assertEqual(order.slippage, 0.0)

    # --- Tests for Position class ---
    def test_position_instantiation(self):
        position = Position(
            symbol=self.test_symbol, quantity=5000, average_entry_price=1.1050,
            related_entry_order_id="entry_order_002", initial_stop_loss_price=1.0950,
            current_stop_loss_price=1.0950, take_profit_price=1.1250
        )
        self.assertEqual(position.symbol, self.test_symbol)
        self.assertEqual(position.quantity, 5000)
        self.assertEqual(position.average_entry_price, 1.1050)
        self.assertEqual(position.related_entry_order_id, "entry_order_002")
        self.assertEqual(position.initial_stop_loss_price, 1.0950)
        self.assertEqual(position.current_stop_loss_price, 1.0950)
        self.assertEqual(position.take_profit_price, 1.1250)
        self.assertEqual(position.unrealized_pnl, 0.0)
        self.assertEqual(position.realized_pnl, 0.0)
        self.assertIsInstance(position.last_update_timestamp, datetime)
        self.assertIsNone(position.active_stop_loss_order_id)

    # --- Tests for execute_order function ---
    def test_execute_market_buy_order(self):
        order = Order(order_id="mkt_buy_01", symbol=self.test_symbol, order_type="market", trade_action="buy", quantity=self.execute_order_lot_size )
        executed_order = execute_order(order, self.market_price_buy, self.execute_order_slippage_pips, self.execute_order_commission_per_lot, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        expected_fill_price = self.market_price_buy + (self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        expected_commission = (self.execute_order_lot_size / self.execute_order_lot_size) * self.execute_order_commission_per_lot
        self.assertAlmostEqual(executed_order.commission, expected_commission)
        self.assertAlmostEqual(executed_order.slippage, self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertIsInstance(executed_order.timestamp_filled, datetime)

    def test_execute_market_sell_order(self):
        order = Order(order_id="mkt_sell_01", symbol=self.test_symbol, order_type="market", trade_action="sell", quantity=50000 )
        executed_order = execute_order(order, self.market_price_sell, self.execute_order_slippage_pips, self.execute_order_commission_per_lot, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        expected_fill_price = self.market_price_sell - (self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        expected_commission = (50000 / self.execute_order_lot_size) * self.execute_order_commission_per_lot
        self.assertAlmostEqual(executed_order.commission, expected_commission)
        self.assertAlmostEqual(executed_order.slippage, self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertIsInstance(executed_order.timestamp_filled, datetime)

    def test_execute_stop_buy_order(self):
        order = Order(order_id="stop_buy_01", symbol=self.test_symbol, order_type="stop", trade_action="buy", quantity=self.execute_order_lot_size, order_price=self.stop_price_buy)
        executed_order = execute_order(order, self.stop_price_buy, self.execute_order_slippage_pips, self.execute_order_commission_per_lot, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        expected_fill_price = self.stop_price_buy + (self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        self.assertIsInstance(executed_order.timestamp_filled, datetime)

    def test_execute_stop_sell_order(self):
        order = Order(order_id="stop_sell_01", symbol=self.test_symbol, order_type="stop", trade_action="sell", quantity=self.execute_order_lot_size, order_price=self.stop_price_sell)
        executed_order = execute_order(order, self.stop_price_sell, self.execute_order_slippage_pips, self.execute_order_commission_per_lot, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        expected_fill_price = self.stop_price_sell - (self.execute_order_slippage_pips * self.execute_order_pip_point_value)
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        self.assertIsInstance(executed_order.timestamp_filled, datetime)

    def test_execute_already_filled_order(self):
        order_fill_time = datetime(2023, 1, 1, 12, 0, 0)
        order = Order(order_id="filled_01", symbol=self.test_symbol, order_type="market", trade_action="buy", quantity=10000, status="filled", fill_price=1.20000, commission=0.5 )
        order.timestamp_filled = order_fill_time
        # For already filled/cancelled orders, execute_order should not change timestamp_filled.
        # The passed datetime.now() here is effectively ignored by the function logic for non-pending orders.
        executed_order = execute_order(order, self.market_price_buy, self.execute_order_slippage_pips, self.execute_order_commission_per_lot, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        self.assertEqual(executed_order.fill_price, 1.20000)
        self.assertEqual(executed_order.commission, 0.5)
        self.assertEqual(executed_order.slippage, 0.0)

    def test_execute_order_zero_slippage_commission(self):
        order = Order(order_id="mkt_buy_zero", symbol=self.test_symbol, order_type="market", trade_action="buy", quantity=self.execute_order_lot_size)
        executed_order = execute_order(order, self.market_price_buy, 0.0, 0.0, self.execute_order_pip_point_value, self.execute_order_lot_size, datetime.now())
        self.assertEqual(executed_order.status, "filled")
        self.assertAlmostEqual(executed_order.fill_price, self.market_price_buy)
        self.assertAlmostEqual(executed_order.commission, 0.0)
        self.assertAlmostEqual(executed_order.slippage, 0.0)

    # --- Tests for PortfolioManager (selected + uncommented) ---
    def test_pm_initialization(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        self.assertEqual(pm.capital, self.initial_capital)
        self.assertEqual(pm.initial_capital, self.initial_capital)
        self.assertEqual(pm.positions, {})
        self.assertEqual(pm.orders, [])
        self.assertEqual(pm.trade_log, [])
        self.assertEqual(pm.config, self.config)

    def test_pm_record_order(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        order = Order(order_id="rec_ord_01", symbol=self.test_symbol, order_type="market", trade_action="buy", quantity=100)
        pm.record_order(order)
        self.assertIn(order, pm.orders)
        self.assertEqual(len(pm.orders), 1)

    def test_pm_open_long_position_new(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_time = datetime.now(); entry_qty = 10000; entry_price = 1.1000; sl_price = 1.0900; entry_commission = 2.0; entry_slippage_monetary = 0.0
        pm.open_position(self.test_symbol, "buy", entry_qty, entry_price, entry_time, sl_price, "order_L1", entry_commission, entry_slippage_monetary)
        self.assertIn(self.test_symbol, pm.positions)
        position = pm.positions[self.test_symbol]
        self.assertEqual(position.quantity, entry_qty)
        self.assertEqual(position.average_entry_price, entry_price)
        self.assertEqual(position.initial_stop_loss_price, sl_price)
        self.assertEqual(pm.capital, self.initial_capital - entry_commission)
        self.assertEqual(len(pm.trade_log), 1)
        self.assertEqual(pm.orders[0].order_type, "stop") # SL order
        self.assertEqual(position.active_stop_loss_order_id, pm.orders[0].order_id)


    def test_pm_open_short_position_new(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_time = datetime.now(); entry_qty = 5000; entry_price = 1.1200; sl_price = 1.1300; entry_commission = 1.5; entry_slippage_monetary = 0.0
        pm.open_position(self.test_symbol, "sell", entry_qty, entry_price, entry_time, sl_price, "order_S1", entry_commission, entry_slippage_monetary)
        self.assertIn(self.test_symbol, pm.positions)
        position = pm.positions[self.test_symbol]
        self.assertEqual(position.quantity, -entry_qty)
        self.assertEqual(pm.orders[0].trade_action, "buy") # SL order for short
        self.assertEqual(position.active_stop_loss_order_id, pm.orders[0].order_id)

    def test_pm_add_to_existing_long_position(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_time1 = datetime.now() - timedelta(hours=1)
        pm.open_position(self.test_symbol, "buy", 10000, 1.1000, entry_time1, 1.0900, "order_L1", 2.0, 0)
        original_sl_order_id = pm.positions[self.test_symbol].active_stop_loss_order_id
        entry_time2 = datetime.now()
        new_sl_price = 1.0950
        pm.open_position(self.test_symbol, "buy", 5000, 1.1100, entry_time2, new_sl_price, "order_L2", 1.0, 0)
        position = pm.positions[self.test_symbol]
        self.assertEqual(position.quantity, 15000)
        expected_avg_price = ((10000 * 1.1000) + (5000 * 1.1100)) / 15000
        self.assertAlmostEqual(position.average_entry_price, expected_avg_price)
        self.assertEqual(pm.capital, self.initial_capital - 2.0 - 1.0)
        self.assertNotEqual(position.active_stop_loss_order_id, original_sl_order_id)
        new_sl_order = next(o for o in pm.orders if o.order_id == position.active_stop_loss_order_id and o.status == "pending")
        self.assertEqual(new_sl_order.order_price, new_sl_price)
        self.assertEqual(new_sl_order.quantity, 15000)

    def test_pm_close_long_position_completely(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_qty = 10000; entry_price = 1.1000; entry_commission = 2.0
        pm.open_position(self.test_symbol, "buy", entry_qty, entry_price, datetime.now(), 1.0900, "order_CL1", entry_commission, 0)
        exit_price = 1.1100; exit_commission = 2.5
        expected_capital = self.initial_capital - entry_commission + ( (exit_price - entry_price) * entry_qty ) - exit_commission
        pm.close_position_completely(self.test_symbol, exit_price, datetime.now(), "order_CL2", exit_commission, 0)
        self.assertNotIn(self.test_symbol, pm.positions)
        self.assertAlmostEqual(pm.capital, expected_capital)
        self.assertEqual(len(pm.trade_log), 2)
        self.assertEqual(pm.trade_log[1]['type'], "exit")
        self.assertAlmostEqual(pm.trade_log[1]['realized_pnl'], ((exit_price - entry_price) * entry_qty) - exit_commission )

    def test_pm_reduce_short_position(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_qty_abs = 10000
        entry_price = 1.1200; entry_commission = 2.0
        pm.open_position(self.test_symbol, "sell", entry_qty_abs, entry_price, datetime.now(), 1.1300, "order_RS1", entry_commission, 0)
        reduce_qty = 5000; exit_price = 1.1100; exit_commission = 1.0
        expected_capital = self.initial_capital - entry_commission + ( (entry_price - exit_price) * reduce_qty ) - exit_commission
        pm.reduce_position(self.test_symbol, reduce_qty, exit_price, datetime.now(), "order_RS2", exit_commission, 0)
        self.assertIn(self.test_symbol, pm.positions)
        position = pm.positions[self.test_symbol]
        self.assertEqual(position.quantity, -entry_qty_abs + reduce_qty)
        self.assertAlmostEqual(pm.capital, expected_capital)
        self.assertEqual(len(pm.trade_log), 2)
        self.assertEqual(pm.trade_log[1]['type'], "reduction")
        self.assertAlmostEqual(position.realized_pnl, ((entry_price - exit_price) * reduce_qty) - exit_commission)

    def test_pm_update_unrealized_pnl_long_simple(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_qty = 10000; entry_price = 1.1000
        pm.open_position(self.test_symbol, "buy", entry_qty, entry_price, datetime.now(), 1.0900, "order_UPNL1", 0, 0)
        current_prices = {self.test_symbol: 1.10500}
        pm.update_unrealized_pnl(current_prices)
        position = pm.positions[self.test_symbol]
        expected_unrealized_pnl = (1.10500 - entry_price) * entry_qty
        self.assertAlmostEqual(position.unrealized_pnl, expected_unrealized_pnl)

    def test_pm_get_total_equity_simple(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_qty = 10000; entry_price = 1.1000; entry_commission = 2.0
        pm.open_position(self.test_symbol, "buy", entry_qty, entry_price, datetime.now(),1.0900, "order_EQ1", entry_commission, 0)
        current_prices = {self.test_symbol: 1.10500}
        expected_unrealized_pnl = (1.10500 - entry_price) * entry_qty
        expected_equity = (self.initial_capital - entry_commission) + expected_unrealized_pnl
        total_equity = pm.get_total_equity(current_prices)
        self.assertAlmostEqual(total_equity, expected_equity)

    def test_pm_get_current_total_open_risk_percentage(self):
        pm = PortfolioManager(initial_capital=self.initial_capital, config=self.config)
        entry_price1 = 1.10000; sl_price1 = 1.09000; qty1 = 10000; entry_commission = 0.0
        pm.open_position(self.test_symbol, "buy", qty1, entry_price1, datetime.now(), sl_price1, "order_TRSK1", entry_commission, 0)
        expected_monetary_risk = (entry_price1 - sl_price1) * qty1 * self.config['pip_point_value'][self.test_symbol]
        self.assertAlmostEqual(expected_monetary_risk, 0.01, places=5) # Corrected expected value
        expected_risk_percentage = expected_monetary_risk / pm.capital
        actual_risk_percentage = pm.get_current_total_open_risk_percentage()
        self.assertAlmostEqual(actual_risk_percentage, expected_risk_percentage, places=7)

        pm_zero_cap = PortfolioManager(initial_capital=0, config=self.config)
        pm_zero_cap.open_position(self.test_symbol, "buy", qty1, entry_price1, datetime.now(), sl_price1, "order_TRSK2", 0,0)
        self.assertEqual(pm_zero_cap.get_current_total_open_risk_percentage(), float('inf'))

        pm_zero_cap_zero_risk = PortfolioManager(initial_capital=0, config=self.config)
        self.assertEqual(pm_zero_cap_zero_risk.get_current_total_open_risk_percentage(), 0.0)

    # --- Risk Management Tests ---
    def test_risk_man_position_sizing_basic(self):
        units = calculate_position_size(account_equity=100000, risk_percentage=0.01, atr=20, pip_value_per_lot=10, lot_size=100000, max_units_per_market=1000000, current_units_for_market=0, total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.0)
        self.assertEqual(units, 250000)

    def test_risk_man_position_sizing_hits_max_units_market(self):
        max_units = 200000
        units_hitting_limit = calculate_position_size(100000,0.01,20,10,100000,max_units,0,0.05,0)
        self.assertEqual(units_hitting_limit, max_units)

    def test_risk_man_position_sizing_respects_current_units_market(self):
        max_units = self.config['max_units_per_market'][self.test_symbol]
        current_units = 300000
        units = calculate_position_size(account_equity=100000, risk_percentage=0.01, atr=20, pip_value_per_lot=10, lot_size=100000, max_units_per_market=max_units, current_units_for_market=current_units, total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.0)
        self.assertEqual(units, 100000)

    def test_risk_man_position_sizing_hits_total_risk_limit(self):
        units = calculate_position_size(account_equity=100000, risk_percentage=0.01, atr=20, pip_value_per_lot=10, lot_size=100000, max_units_per_market=1000000, current_units_for_market=0, total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.045)
        self.assertEqual(units, 125000)

    def test_risk_man_position_sizing_atr_zero_or_pip_value_zero(self):
        units_atr_zero = calculate_position_size(100000,0.01,0,10,100000,1000000,0,0.05,0)
        self.assertEqual(units_atr_zero, 0)
        units_pip_zero = calculate_position_size(100000,0.01,20,0,100000,1000000,0,0.05,0)
        self.assertEqual(units_pip_zero, 0)

    # --- Basic run_strategy test ---
    def test_run_strategy_single_trade_cycle(self):
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        timestamps = [start_time + timedelta(hours=i) for i in range(10)]
        data = {'Open':  [1.100, 1.101, 1.102, 1.103, 1.104, 1.105, 1.106, 1.102, 1.090, 1.088], 'High':  [1.101, 1.102, 1.103, 1.104, 1.105, 1.108, 1.107, 1.103, 1.095, 1.090], 'Low':   [1.099, 1.100, 1.101, 1.102, 1.103, 1.100, 1.101, 1.088, 1.085, 1.086], 'Close': [1.101, 1.102, 1.103, 1.104, 1.105, 1.106, 1.102, 1.089, 1.088, 1.087]}
        hist_df = pd.DataFrame(data, index=pd.DatetimeIndex(timestamps))
        historical_data_dict = {self.test_symbol: hist_df}
        test_config = self.config.copy()
        test_config['entry_donchian_period'] = 5
        test_config['atr_period'] = 5
        test_config['stop_loss_atr_multiplier'] = 1.5
        test_config['take_profit_long_exit_period'] = 3
        test_config['take_profit_short_exit_period'] = 3
        results = run_strategy(historical_data_dict, test_config['initial_capital'], test_config)
        self.assertTrue(len(results['trade_log']) >= 2, "Should have at least an entry and an exit trade.")
        entry_trade = next((t for t in results['trade_log'] if t['type'] == 'entry'), None)
        exit_trade = next((t for t in results['trade_log'] if t['type'] == 'exit' and t['order_id'].endswith('_sl')), None)
        self.assertIsNotNone(entry_trade, "Entry trade not found in log.")
        self.assertIsNotNone(exit_trade, "Stop-loss exit trade not found in log.")
        if entry_trade:
            self.assertEqual(entry_trade['symbol'], self.test_symbol)
            self.assertEqual(entry_trade['action'], 'buy')
            self.assertGreater(entry_trade['quantity'], 0)
            expected_entry_fill = 1.106 + test_config['slippage_pips'] * self.pip_point_value_per_unit
            self.assertAlmostEqual(entry_trade['price'], expected_entry_fill, places=5)
        if exit_trade and entry_trade:
            self.assertEqual(exit_trade['symbol'], self.test_symbol)
            self.assertTrue(exit_trade['price'] < entry_trade['price'])
        self.assertTrue(len(results['equity_curve']) == len(timestamps))
        self.assertLess(results['final_capital'], test_config['initial_capital'])


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

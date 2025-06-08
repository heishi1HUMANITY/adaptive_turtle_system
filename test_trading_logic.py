import unittest
import pandas as pd
import numpy as np # For NaN and other numerical utilities
from pandas.testing import assert_series_equal

# Assuming trading_logic.py is in the same directory or accessible in PYTHONPATH
import trading_logic as tl
from datetime import datetime, timezone

class TestTradingLogic(unittest.TestCase):

    def setUp(self):
        """Setup common data for tests."""
        self.price_data = pd.DataFrame({
            'high': [10, 12, 11, 13, 14, 15, 13, 12, 11, 10],
            'low':  [8,  9,  10, 10, 11, 12, 11, 10, 9,  8],
            'close':[9,  11, 10, 12, 13, 14, 12, 11, 10, 9]
        })
        self.high_series = self.price_data['high']
        self.low_series = self.price_data['low']
        self.close_series = self.price_data['close']

        self.sample_config = {
            "markets": ["EUR/USD", "USD/JPY"],
            "slippage_pips": 0.2,
            "commission_per_lot": 5.0, # Assuming in account currency
            "pip_point_value": {"EUR/USD": 0.0001, "USD/JPY": 0.01},
            "lot_size": {"EUR/USD": 100000, "USD/JPY": 100000},
            "stop_loss_atr_multiplier": 2.0,
            "risk_percentage_per_trade": 0.01, # 1%
            "max_units_per_market": {"EUR/USD": 500000, "USD/JPY": 5000000},
            "total_risk_percentage_limit": 0.05, # 5%
            "account_currency": "USD",
            "entry_donchian_period": 20,
            "take_profit_long_exit_period": 10,
            "take_profit_short_exit_period": 10,
        }
        # Sample historical data for run_strategy tests (simplified)
        idx = pd.to_datetime(['2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 12:00',
                              '2023-01-01 13:00', '2023-01-01 14:00', '2023-01-01 15:00'])
        self.sample_historical_data_df = pd.DataFrame({
            ('EUR/USD', 'Open'):  [1.1000, 1.1010, 1.1020, 1.1015, 1.1025, 1.1030],
            ('EUR/USD', 'High'):  [1.1005, 1.1015, 1.1025, 1.1020, 1.1030, 1.1035],
            ('EUR/USD', 'Low'):   [1.0995, 1.1005, 1.1010, 1.1010, 1.1020, 1.1025],
            ('EUR/USD', 'Close'): [1.1000, 1.1010, 1.1015, 1.1012, 1.1028, 1.1032],
            ('EUR/USD', 'ATR'):   [0.0010, 0.0010, 0.0010, 0.0010, 0.0010, 0.0010], # 10 pips
            ('USD/JPY', 'Open'):  [130.00, 130.10, 130.20, 130.15, 130.25, 130.30],
            ('USD/JPY', 'High'):  [130.05, 130.15, 130.25, 130.20, 130.30, 130.35],
            ('USD/JPY', 'Low'):   [129.95, 130.05, 130.10, 130.10, 130.20, 130.25],
            ('USD/JPY', 'Close'): [130.00, 130.10, 130.15, 130.12, 130.28, 130.32],
            ('USD/JPY', 'ATR'):   [0.10,   0.10,   0.10,   0.10,   0.10,   0.10], # 10 pips
        }, index=idx)

        self.integration_test_config = self.sample_config.copy()
        self.integration_test_config["markets"] = ["TESTA", "TESTB"]
        self.integration_test_config["pip_point_value"] = {"TESTA": 0.01, "TESTB": 1.0} # TESTA like USD/JPY, TESTB like BTC/USD
        self.integration_test_config["lot_size"] = {"TESTA": 1000, "TESTB": 1} # Smaller lot sizes for easier testing
        self.integration_test_config["max_units_per_market"] = {"TESTA": 50, "TESTB": 10}
        self.integration_test_config["risk_percentage_per_trade"] = 0.10 # 10% for bigger impact in small test
        self.integration_test_config["total_risk_percentage_limit"] = 0.25 # 25%
        self.integration_test_config["commission_per_lot"] = 2.0 # $2 per lot
        self.integration_test_config["entry_donchian_period"] = 5 # Shorter for test data
        self.integration_test_config["take_profit_long_exit_period"] = 3 # Shorter
        self.integration_test_config["take_profit_short_exit_period"] = 3 # Shorter


    def _create_integration_test_df(self, num_periods=30):
        idx = pd.date_range(start="2023-01-01", periods=num_periods, freq="H")
        data = {}
        # Market A (TESTA) - designed for an entry and then a stop-loss
        data[('TESTA', 'Open')] = np.linspace(100, 110, num_periods)
        data[('TESTA', 'High')] = data[('TESTA', 'Open')] + 2 # Make High always break Donchian for entry
        data[('TESTA', 'Low')]  = data[('TESTA', 'Open')] - 1
        data[('TESTA', 'Close')]= data[('TESTA', 'Open')] + 0.5
        data[('TESTA', 'ATR')]  = np.full(num_periods, 0.5) # ATR of 0.5 price units

        # Trigger entry for TESTA (long) around period 6-7 (after Donchian period 5)
        # High of period 6 (index 5) will be data[('TESTA', 'Open')][5] + 2
        # Close of period 6 will be data[('TESTA', 'Open')][5] + 0.5
        # Let's make it break out: data[('TESTA', 'Close')][6] needs to be > DonchianUpperEntry[5]
        # DonchianUpperEntry looks back 5 periods.
        # To ensure entry: data[('TESTA', 'High')][6] = 100 + (110-100)/29 * 6 + 2 + 5 = ~104 + 7 = 111
        # data[('TESTA', 'Close')][6] = 100 + (110-100)/29 * 6 + 0.5 + 5 = ~104.5 + 5 = 109.5
        # This should ensure data[('TESTA', 'Close')][6] > data[('TESTA', 'High')][1:6].max() (shifted)

        # Setup for stop-loss for TESTA:
        # Entry at index 6 (7th period). Price ~104.5. ATR=0.5. SL mult=2. SL pips = 1.0 price unit.
        # SL price = ~104.5 - 1.0 = ~103.5.
        # We need data[('TESTA', 'Low')] to hit this.
        data[('TESTA', 'Low')][10] = data[('TESTA', 'Close')][6] - (data[('TESTA', 'ATR')][6] * self.integration_test_config["stop_loss_atr_multiplier"]) - 0.1 # Hit SL

        # Market B (TESTB) - designed for an entry and then a take-profit
        data[('TESTB', 'Open')] = np.linspace(2000, 2200, num_periods)
        data[('TESTB', 'High')] = data[('TESTB', 'Open')] + 20
        data[('TESTB', 'Low')]  = data[('TESTB', 'Open')] - 10
        data[('TESTB', 'Close')]= data[('TESTB', 'Open')] + 5
        data[('TESTB', 'ATR')]  = np.full(num_periods, 10.0)

        # Entry for TESTB (long) around period 15
        # data[('TESTB', 'High')][15] += 50 # Ensure breakout for entry
        # data[('TESTB', 'Close')][15] += 50

        # Setup for Take Profit for TESTB (long exit based on 3-period low)
        # Entry at index 15. Price ~2100 + 5 = 2105.
        # TP Donchian (3-period low).
        # At index 19 (20th period), we want Close[19] < Low[16:19].min() (shifted)
        # Low values: data[('TESTB', 'Low')][16], data[('TESTB', 'Low')][17], data[('TESTB', 'Low')][18]
        # Make data[('TESTB', 'Close')][19] dip below the min of these.
        # data[('TESTB', 'Close')][19] = data[('TESTB', 'Low')][16:19].min() - 1
        # This setup is tricky without actually running the loop. Let's make a clear dip.
        # Example: Lows around 2100. Make Close[19] = 2050.
        # data[('TESTB', 'Close')][19] = data[('TESTB', 'Open')][19] - 15 # Ensure it's a significant dip

        df = pd.DataFrame(data, index=idx)
        # Ensure Close is within High/Low after manipulation
        for market_symbol in ["TESTA", "TESTB"]:
            df[(market_symbol, 'High')] = df[[(market_symbol, 'Open'), (market_symbol, 'Close')]].max(axis=1) + np.random.rand(num_periods) * 0.1 * df[(market_symbol, 'ATR')]
            df[(market_symbol, 'Low')] = df[[(market_symbol, 'Open'), (market_symbol, 'Close')]].min(axis=1) - np.random.rand(num_periods) * 0.1 * df[(market_symbol, 'ATR')]
            df.loc[df[(market_symbol, 'Close')] > df[(market_symbol, 'High')], (market_symbol, 'High')] = df[(market_symbol, 'Close')]
            df.loc[df[(market_symbol, 'Close')] < df[(market_symbol, 'Low')], (market_symbol, 'Low')] = df[(market_symbol, 'Close')]


        return df


    # 1. Tests for calculate_donchian_channel (Existing)
    def test_calculate_donchian_channel_basic(self):
        period = 3
        upper, lower = tl.calculate_donchian_channel(self.high_series, self.low_series, period)

        expected_upper = pd.Series([np.nan, np.nan, 12, 13, 14, 15, 15, 15, 13, 12], name='high')
        expected_lower = pd.Series([np.nan, np.nan, 8,  9,  10, 10, 11, 10, 9,  8], name='low')

        # Rolling functions in pandas < 2.x might not set `name` attribute as expected by default.
        # Let's ensure names are consistent for comparison if they are None.
        if upper.name is None: upper.name = 'high'
        if lower.name is None: lower.name = 'low'

        assert_series_equal(upper, expected_upper, check_dtype=False)
        assert_series_equal(lower, expected_lower, check_dtype=False)

    def test_calculate_donchian_channel_period_one(self):
        period = 1
        upper, lower = tl.calculate_donchian_channel(self.high_series, self.low_series, period)
        # With period 1, Donchian channel is just the current high/low
        expected_upper = self.high_series.copy()
        expected_lower = self.low_series.copy()

        if upper.name is None: upper.name = 'high' # Consistency for older pandas
        if lower.name is None: lower.name = 'low'   # Consistency for older pandas

        assert_series_equal(upper, expected_upper, check_dtype=False)
        assert_series_equal(lower, expected_lower, check_dtype=False)

    def test_calculate_donchian_channel_invalid_input(self):
        with self.assertRaises(TypeError):
            tl.calculate_donchian_channel("not a series", self.low_series, 3)
        with self.assertRaises(ValueError):
            tl.calculate_donchian_channel(self.high_series, self.low_series, 0)
        with self.assertRaises(ValueError):
            tl.calculate_donchian_channel(self.high_series, self.low_series, -1)

    # 2. Tests for calculate_atr
    def test_calculate_atr_basic(self):
        high = pd.Series([10, 12, 11, 13, 14])
        low = pd.Series(  [8,  9,  10, 10, 11])
        close = pd.Series([9,  11, 10, 12, 13])
        period = 3

        # Manual TR calculation:
        # prev_close = close.shift(1) -> [nan, 9, 11, 10, 12]
        # tr1 (h-l) = [2, 3, 1, 3, 3]
        # tr2 (abs(h-pc)) = [nan, 3, 0, 3, 2]  (10-nan=nan, 12-9=3, 11-11=0, 13-10=3, 14-12=2)
        # tr3 (abs(l-pc)) = [nan, 1, 1, 0, 1]  (8-nan=nan,  9-9=0->abs(0)=0, no, 9-9=0, abs(low[0]-close[-1]) -> 9-9=0, abs(low[1]-close[0]) -> abs(9-9)=0, abs(10-11)=1, abs(10-10)=0, abs(11-12)=1)
        # Corrected tr2/tr3:
        # prev_close = [nan, 9.0, 11.0, 10.0, 12.0]
        # high - low:      [2.0, 3.0,  1.0,  3.0,  3.0]
        # abs(high - pc): [ nan, 3.0,  0.0,  3.0,  2.0]
        # abs(low - pc):  [ nan, 0.0,  1.0,  0.0,  1.0]
        # TR = max(h-l, abs(h-pc), abs(l-pc))
        # TR: [nan, 3.0, 1.0, 3.0, 3.0] -> Note: pandas max of (2,nan,nan) is 2, not nan unless skipna=False. The function uses skipna=False.
        # The first TR is usually high-low if not using previous_close, or NaN if strict.
        # trading_logic.py uses skipna=False on the DataFrame of tr1,tr2,tr3.
        # So, for index 0: tr1=2, tr2=nan, tr3=nan. max(2,nan,nan) with skipna=False is nan. Correct.

        # Expected TR: [nan, 3.0, 1.0, 3.0, 3.0]
        # Expected ATR (SMA of TR, period 3):
        # [nan, nan, nan, (3+1+3)/3=7/3=2.3333, (1+3+3)/3=7/3=2.3333]

        expected_atr = pd.Series([np.nan, np.nan, np.nan, (3.0+1.0+3.0)/3, (1.0+3.0+3.0)/3])
        atr = tl.calculate_atr(high, low, close, period)
        assert_series_equal(atr, expected_atr, check_dtype=False)

    def test_calculate_atr_period_one(self):
        high = pd.Series([10, 12, 11, 13, 14])
        low = pd.Series(  [8,  9,  10, 10, 11])
        close = pd.Series([9,  11, 10, 12, 13])
        period = 1
        # Expected TR: [nan, 3.0, 1.0, 3.0, 3.0]
        # ATR with period 1 is just the TR values
        expected_atr = pd.Series([np.nan, 3.0, 1.0, 3.0, 3.0])
        atr = tl.calculate_atr(high, low, close, period)
        assert_series_equal(atr, expected_atr, check_dtype=False)

    def test_calculate_atr_constant_price(self):
        high = pd.Series([10.0] * 5)
        low = pd.Series([10.0] * 5)
        close = pd.Series([10.0] * 5)
        period = 3
        # TR: [nan, 0, 0, 0, 0] (h-l=0, abs(h-pc)=0, abs(l-pc)=0 for non-nan pc)
        # ATR: [nan, nan, nan, 0, 0]
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

    # 3. Tests for generate_entry_signals
    def test_generate_entry_signals_basic(self):
        close_prices = pd.Series([10, 11, 15, 14, 9, 8]) # Length 6
        # Assume entry_period is 3 for Donchian calculation, then these bands are shifted by 1
        # So, Donchian values at index i are for period ending at i
        # For signal at index i, we use Donchian from i-1
        donchian_upper = pd.Series([np.nan, 10, 11, 15, 15, 14]) # Example pre-calculated Donchian upper
        donchian_lower = pd.Series([np.nan, 8,  9,  10, 10, 9 ]) # Example pre-calculated Donchian lower
        entry_period = 3 # This is mostly for context/validation in the function

        # close:            [10,    11,    15,    14,    9,     8]
        # prev_upper_shifted: [nan, nan, 10.0,  11.0,  15.0,  15.0]
        # prev_lower_shifted: [nan, nan,  8.0,   9.0,  10.0,  10.0]

        # Long conditions (close > prev_upper_shifted):
        # index 2: 15 > 10.0 (True) -> Signal 1
        # index 3: 14 > 11.0 (True) -> Signal 1
        # Short conditions (close < prev_lower_shifted):
        # index 4: 9 < 10.0 (True) -> Signal -1
        # index 5: 8 < 10.0 (True) -> Signal -1

        # If both long and short are true for a point (not possible with X>A and X<B if A>B),
        # the implementation overwrites long with short.

        expected_signal = pd.Series([0, 0, 1, 1, -1, -1])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_no_signal(self):
        close_prices = pd.Series([10, 10.5, 10.8, 10.5, 10.2])
        donchian_upper = pd.Series([np.nan, 11, 11, 11, 11])
        donchian_lower = pd.Series([np.nan, 10, 10, 10, 10])
        entry_period = 3
        # prev_upper_shifted: [nan, nan, 11, 11, 11]
        # prev_lower_shifted: [nan, nan, 10, 10, 10]
        # close:              [10, 10.5, 10.8, 10.5, 10.2]
        # No close > prev_upper, no close < prev_lower
        expected_signal = pd.Series([0, 0, 0, 0, 0])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_start_of_series_nan_bands(self):
        close_prices = pd.Series([10, 11, 12])
        # Shifted Donchian bands will have NaNs at the start
        donchian_upper = pd.Series([np.nan, np.nan, np.nan])
        donchian_lower = pd.Series([np.nan, np.nan, np.nan])
        entry_period = 20 # Period doesn't affect NaNs from shift if bands already NaN
        # prev_upper_shifted: [nan, nan, nan]
        # prev_lower_shifted: [nan, nan, nan]
        # Comparisons with NaN (e.g., 10 > np.nan) are False.
        expected_signal = pd.Series([0, 0, 0])
        signals = tl.generate_entry_signals(close_prices, donchian_upper, donchian_lower, entry_period)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_entry_signals_input_validation(self):
        with self.assertRaises(TypeError):
            tl.generate_entry_signals("c", self.high_series, self.low_series, 3)
        with self.assertRaises(ValueError):
            tl.generate_entry_signals(self.close_series, self.high_series, self.low_series, 0)

    # 4. Tests for generate_exit_signals
    def test_generate_exit_signals_long_exit(self):
        close_prices = pd.Series([15, 12, 10, 9, 8])
        # For exits, let's assume a 10-period Donchian for example
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9]) # Lower band for long exits
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])# Upper band for short exits (not used here)
        current_positions = pd.Series([0, 1, 1, 1, 1]) # Holding long from index 1
        exit_period_long = 10 # For context/validation
        exit_period_short = 10 # For context/validation

        # close_prices:              [15,   12,   10,    9,    8]
        # prev_donchian_lower_exit:  [nan, nan, 11.0, 10.0,  9.0] (shifted)
        # current_positions:         [0,    1,    1,    1,    1]

        # Long Exit (pos==1 and close < prev_lower_exit):
        # Index 2: pos=1, close=10. 10 < 11.0 (True) -> Exit signal -1
        # Index 3: pos=1, close=9.  9 < 10.0 (True) -> Exit signal -1
        # Index 4: pos=1, close=8.  8 < 9.0  (True) -> Exit signal -1
        # Expected: [0,0,-1,-1,-1] (No exit at index 1 as prev_donchian_lower is nan after shift)
        expected_signal = pd.Series([0, 0, -1, -1, -1])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_short_exit(self):
        close_prices = pd.Series([10, 12, 15, 16, 17])
        donchian_lower_exit = pd.Series([np.nan, 8, 9, 10, 11]) # Not used here
        donchian_upper_exit = pd.Series([np.nan, 13, 14, 15, 15])# Upper band for short exits
        current_positions = pd.Series([0, -1, -1, -1, -1]) # Holding short
        exit_period_long = 10
        exit_period_short = 10

        # close_prices:             [10,   12,   15,   16,   17]
        # prev_donchian_upper_exit: [nan, nan, 13.0, 14.0, 15.0] (shifted)
        # current_positions:        [0,   -1,   -1,   -1,   -1]

        # Short Exit (pos==-1 and close > prev_upper_exit):
        # Index 2: pos=-1, close=15. 15 > 13.0 (True) -> Exit signal 1
        # Index 3: pos=-1, close=16. 16 > 14.0 (True) -> Exit signal 1
        # Index 4: pos=-1, close=17. 17 > 15.0 (True) -> Exit signal 1
        expected_signal = pd.Series([0, 0, 1, 1, 1])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_no_exit_if_no_position(self):
        close_prices = pd.Series([15, 12, 10, 9, 8])
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9])
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])
        current_positions = pd.Series([0, 0, 0, 0, 0]) # Not holding any position
        exit_period_long = 10
        exit_period_short = 10
        expected_signal = pd.Series([0, 0, 0, 0, 0])
        signals = tl.generate_exit_signals(close_prices, donchian_upper_exit, donchian_lower_exit,
                                           exit_period_long, exit_period_short, current_positions)
        assert_series_equal(signals, expected_signal, check_dtype=False)

    def test_generate_exit_signals_no_exit_if_wrong_position(self):
        close_prices = pd.Series([15, 12, 10, 9, 8]) # Potential long exit conditions
        donchian_lower_exit = pd.Series([np.nan, 11, 10, 9, 9])
        donchian_upper_exit = pd.Series([np.nan, 18, 17, 16, 15])
        current_positions = pd.Series([0, -1, -1, -1, -1]) # Holding SHORT position
        exit_period_long = 10
        exit_period_short = 10
        # Conditions for long exit might be met (close < prev_lower), but pos is -1.
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

    # Existing tests for calculate_atr, generate_entry_signals, generate_exit_signals ...

    # 6. Tests for Order Class
    def test_order_creation(self):
        order_time = datetime.now(timezone.utc) # Make timezone aware for consistency
        order = tl.Order(order_id="test001", symbol="EUR/USD", order_type="market",
                           trade_action="buy", quantity=10000, order_price=None,
                           status="pending", commission=5.0, slippage=0.00002)
        self.assertEqual(order.order_id, "test001")
        self.assertEqual(order.symbol, "EUR/USD")
        self.assertEqual(order.order_type, "market")
        self.assertEqual(order.trade_action, "buy")
        self.assertEqual(order.quantity, 10000)
        self.assertIsNone(order.order_price)
        self.assertEqual(order.status, "pending")
        self.assertIsNone(order.fill_price) # Not filled yet
        self.assertLessEqual((datetime.now(timezone.utc) - order.timestamp_created).total_seconds(), 1)
        self.assertIsNone(order.timestamp_filled)
        self.assertEqual(order.commission, 5.0)
        self.assertEqual(order.slippage, 0.00002)

    # 7. Tests for Position Class
    def test_position_creation(self):
        entry_time = datetime.now(timezone.utc)
        pos = tl.Position(symbol="USD/JPY", quantity=5000, average_entry_price=130.50,
                            related_entry_order_id="entry002", initial_stop_loss_price=130.00,
                            current_stop_loss_price=130.10, take_profit_price=131.50)
        self.assertEqual(pos.symbol, "USD/JPY")
        self.assertEqual(pos.quantity, 5000)
        self.assertEqual(pos.average_entry_price, 130.50)
        self.assertEqual(pos.related_entry_order_id, "entry002")
        self.assertEqual(pos.initial_stop_loss_price, 130.00)
        self.assertEqual(pos.current_stop_loss_price, 130.10)
        self.assertEqual(pos.take_profit_price, 131.50)
        self.assertEqual(pos.unrealized_pnl, 0.0) # Initial
        self.assertEqual(pos.realized_pnl, 0.0)   # Initial
        self.assertLessEqual((datetime.now(timezone.utc) - pos.last_update_timestamp).total_seconds(), 1)


    # 8. Tests for calculate_initial_stop_loss function
    def test_calculate_initial_stop_loss_long(self):
        sl = tl.calculate_initial_stop_loss(entry_price=1.1000, trade_action="buy",
                                            atr_value=0.0010, atr_multiplier=2)
        self.assertAlmostEqual(sl, 1.1000 - (0.0010 * 2)) # 1.0980

    def test_calculate_initial_stop_loss_short(self):
        sl = tl.calculate_initial_stop_loss(entry_price=130.00, trade_action="sell",
                                            atr_value=0.10, atr_multiplier=2.5)
        self.assertAlmostEqual(sl, 130.00 + (0.10 * 2.5)) # 130.25

    def test_calculate_initial_stop_loss_zero_atr(self):
        with self.assertRaises(ValueError): # ATR must be positive
            tl.calculate_initial_stop_loss(1.1000, "buy", 0, 2)

    def test_calculate_initial_stop_loss_zero_multiplier(self):
        with self.assertRaises(ValueError): # Multiplier must be positive
            tl.calculate_initial_stop_loss(1.1000, "buy", 0.0010, 0)


    # 9. Tests for execute_order function
    def test_execute_market_buy_order(self):
        order = tl.Order("ord1", "EUR/USD", "market", "buy", 10000)
        market_price = 1.10000
        slippage_pips = self.sample_config['slippage_pips'] # 0.2 pips
        pip_val = self.sample_config['pip_point_value']["EUR/USD"] # 0.0001
        comm_lot = self.sample_config['commission_per_lot'] # 5.0
        lot_sz = self.sample_config['lot_size']["EUR/USD"] # 100000

        expected_slippage_amount = slippage_pips * pip_val # 0.2 * 0.0001 = 0.00002
        expected_fill_price = market_price + expected_slippage_amount # 1.10002
        expected_commission = (order.quantity / lot_sz) * comm_lot # (10000/100000) * 5.0 = 0.1 * 5.0 = 0.5

        executed_order = tl.execute_order(order, market_price, slippage_pips, comm_lot, pip_val, lot_sz)

        self.assertEqual(executed_order.status, "filled")
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        self.assertAlmostEqual(executed_order.commission, expected_commission)
        self.assertAlmostEqual(executed_order.slippage, expected_slippage_amount)
        self.assertIsNotNone(executed_order.timestamp_filled)

    def test_execute_market_sell_order(self):
        order = tl.Order("ord2", "USD/JPY", "market", "sell", 50000)
        market_price = 130.00
        slippage_pips = self.sample_config['slippage_pips'] # 0.2 pips
        pip_val = self.sample_config['pip_point_value']["USD/JPY"] # 0.01
        comm_lot = self.sample_config['commission_per_lot']
        lot_sz = self.sample_config['lot_size']["USD/JPY"]

        expected_slippage_amount = slippage_pips * pip_val # 0.2 * 0.01 = 0.002
        expected_fill_price = market_price - expected_slippage_amount # 130.00 - 0.002 = 129.998
        expected_commission = (order.quantity / lot_sz) * comm_lot # (50000/100000) * 5.0 = 0.5 * 5.0 = 2.5

        executed_order = tl.execute_order(order, market_price, slippage_pips, comm_lot, pip_val, lot_sz)
        self.assertEqual(executed_order.status, "filled")
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)
        self.assertAlmostEqual(executed_order.commission, expected_commission)

    def test_execute_stop_sell_order(self): # e.g. SL for a long position
        stop_price = 1.0950
        order = tl.Order("ord3", "EUR/USD", "stop", "sell", 10000, order_price=stop_price)
        market_price_at_trigger = 1.0948 # Market moved beyond stop, actual current price irrelevant for fill calc based on logic
        slippage_pips = self.sample_config['slippage_pips']
        pip_val = self.sample_config['pip_point_value']["EUR/USD"]
        comm_lot = self.sample_config['commission_per_lot']
        lot_sz = self.sample_config['lot_size']["EUR/USD"]

        expected_slippage_amount = slippage_pips * pip_val
        expected_fill_price = stop_price - expected_slippage_amount # Sells below stop price

        executed_order = tl.execute_order(order, market_price_at_trigger, slippage_pips, comm_lot, pip_val, lot_sz)
        self.assertEqual(executed_order.status, "filled")
        self.assertAlmostEqual(executed_order.fill_price, expected_fill_price)

    def test_execute_order_already_filled(self):
        order = tl.Order("ord4", "EUR/USD", "market", "buy", 10000, status="filled", fill_price=1.1)
        original_fill_price = order.fill_price
        executed_order = tl.execute_order(order, 1.2, 0.2, 5, 0.0001, 100000)
        self.assertEqual(executed_order.status, "filled") # Stays filled
        self.assertEqual(executed_order.fill_price, original_fill_price) # Fill price does not change

    # 10. Basic Tests for PortfolioManager Class
    def test_pm_initialization(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        self.assertEqual(pm.capital, 100000)
        self.assertEqual(pm.initial_capital, 100000)
        self.assertEqual(len(pm.positions), 0)
        self.assertEqual(len(pm.orders), 0)
        self.assertEqual(len(pm.trade_log), 0)
        self.assertEqual(pm.config, self.sample_config)

    def test_pm_record_order(self):
        pm = tl.PortfolioManager(10000, self.sample_config)
        order = tl.Order("rec_ord1", "EUR/USD", "market", "buy", 1000)
        pm.record_order(order)
        self.assertIn(order, pm.orders)

    def test_pm_open_new_long_position(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol = "EUR/USD"
        quantity = 10000
        entry_price = 1.1000
        entry_time = datetime.now(timezone.utc)
        stop_loss_price = 1.0980
        order_id = "long_entry1"
        commission = 0.5 # Calculated from execute_order
        slippage_val = 0.00002 # Calculated from execute_order

        pm.open_position(symbol, "buy", quantity, entry_price, entry_time,
                           stop_loss_price, order_id, commission, slippage_val)

        self.assertIn(symbol, pm.positions)
        position = pm.positions[symbol]
        self.assertEqual(position.quantity, quantity)
        self.assertEqual(position.average_entry_price, entry_price)
        self.assertEqual(position.initial_stop_loss_price, stop_loss_price)
        self.assertEqual(pm.capital, 100000 - commission)
        self.assertEqual(len(pm.trade_log), 1)
        self.assertEqual(pm.trade_log[0]['order_id'], order_id)
        self.assertEqual(pm.trade_log[0]['type'], "entry")

        # Check for SL order
        self.assertEqual(len(pm.orders), 1) # Should only be the SL order now
        sl_order = pm.orders[0]
        self.assertEqual(sl_order.order_id, f"{order_id}_sl")
        self.assertEqual(sl_order.symbol, symbol)
        self.assertEqual(sl_order.order_type, "stop")
        self.assertEqual(sl_order.trade_action, "sell") # Opposite for SL
        self.assertEqual(sl_order.quantity, quantity)
        self.assertEqual(sl_order.order_price, stop_loss_price)
        self.assertEqual(sl_order.status, "pending")

    def test_pm_close_long_position_completely(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol = "EUR/USD"
        entry_qty = 10000
        entry_price = 1.1000
        entry_time = datetime.now(timezone.utc) - pd.Timedelta(hours=1)
        sl_price = 1.0900
        entry_order_id = "close_test_entry"
        entry_commission = 0.5
        pm.open_position(symbol, "buy", entry_qty, entry_price, entry_time, sl_price, entry_order_id, entry_commission, 0)

        # SL order was created by open_position
        original_sl_order = next(o for o in pm.orders if o.order_id == f"{entry_order_id}_sl")
        self.assertEqual(original_sl_order.status, "pending")

        exit_price = 1.1050 # Profit
        exit_time = datetime.now(timezone.utc)
        exit_order_id = "close_test_exit"
        exit_commission = 0.5

        initial_capital_after_entry = 100000 - entry_commission # 99999.5

        pm.close_position_completely(symbol, exit_price, exit_time, exit_order_id, exit_commission, 0)

        self.assertNotIn(symbol, pm.positions)
        # P&L = (1.1050 - 1.1000) * 10000 = 0.0050 * 10000 = 50
        # Net P&L = 50 - exit_commission = 50 - 0.5 = 49.5
        # Expected capital = initial_capital_after_entry + Net P&L = 99999.5 + 49.5 = 100049.0
        self.assertAlmostEqual(pm.capital, 100049.0)
        self.assertEqual(len(pm.trade_log), 2)
        self.assertEqual(pm.trade_log[1]['type'], "exit")
        self.assertAlmostEqual(pm.trade_log[1]['realized_pnl'], 49.5)

        # Check if SL order was cancelled
        self.assertEqual(original_sl_order.status, "cancelled")

    def test_pm_reduce_long_position(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol = "EUR/USD"
        entry_qty = 20000
        entry_price = 1.1000
        entry_time = datetime.now(timezone.utc) - pd.Timedelta(hours=1)
        sl_price = 1.0900
        entry_order_id = "reduce_test_entry"
        entry_commission = 1.0 # For 0.2 lots
        pm.open_position(symbol, "buy", entry_qty, entry_price, entry_time, sl_price, entry_order_id, entry_commission, 0)

        initial_capital_after_entry = 100000 - entry_commission # 99999.0

        reduce_qty = 5000
        exit_price = 1.1020 # Profit on this portion
        exit_time = datetime.now(timezone.utc)
        exit_order_id = "reduce_test_exit"
        # Commission for 0.05 lots (5000 units / 100000 lot_size * 5.0 comm_per_lot = 0.05 * 5.0 = 0.25)
        exit_commission_partial = 0.25

        pm.reduce_position(symbol, reduce_qty, exit_price, exit_time, exit_order_id, exit_commission_partial, 0)

        position = pm.get_open_position(symbol)
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, entry_qty - reduce_qty) # 15000
        self.assertEqual(position.average_entry_price, entry_price) # Avg price unchanged on partial close

        # P&L for reduced portion = (1.1020 - 1.1000) * 5000 = 0.0020 * 5000 = 10
        # Net P&L = 10 - exit_commission_partial = 10 - 0.25 = 9.75
        # Expected capital = initial_capital_after_entry + Net P&L = 99999.0 + 9.75 = 100008.75
        self.assertAlmostEqual(pm.capital, 100008.75)
        self.assertEqual(len(pm.trade_log), 2)
        self.assertEqual(pm.trade_log[1]['type'], "reduction")
        self.assertAlmostEqual(pm.trade_log[1]['realized_pnl'], 9.75)
        self.assertAlmostEqual(position.realized_pnl, 9.75) # Accumulated on position object

    def test_pm_get_current_total_open_risk_percentage(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        current_prices = {"EUR/USD": 1.1000, "USD/JPY": 130.00}
        # No positions, no risk
        self.assertAlmostEqual(pm.get_current_total_open_risk_percentage(current_prices), 0.0)

        # Open EUR/USD long position
        eurusd_entry_price = 1.1000
        eurusd_sl_price = 1.0980 # Risk = 1.1000 - 1.0980 = 0.0020 per unit
        eurusd_quantity = 50000
        pm.open_position("EUR/USD", "buy", eurusd_quantity, eurusd_entry_price, datetime.now(timezone.utc),
                           eurusd_sl_price, "eurusd1", 0.0, 0) # Commission ignored for simplicity here

        # Risk for EUR/USD = 0.0020 * 50000 = 100 USD
        # Capital is 100000. Equity is 100000 (no P&L yet, commission ignored).
        # Expected total risk % = 100 / 100000 = 0.001 (0.1%)
        current_prices_eurusd_pos = {"EUR/USD": 1.1000, "USD/JPY": 130.00}
        self.assertAlmostEqual(pm.get_current_total_open_risk_percentage(current_prices_eurusd_pos), 0.001)

        # Open USD/JPY short position
        usdjpy_entry_price = 130.00
        usdjpy_sl_price = 130.25 # Risk = 130.25 - 130.00 = 0.25 per unit
        usdjpy_quantity = 20000
        pm.open_position("USD/JPY", "sell", usdjpy_quantity, usdjpy_entry_price, datetime.now(timezone.utc),
                           usdjpy_sl_price, "usdjpy1", 0.0, 0)

        # Risk for USD/JPY = 0.25 * 20000 = 5000 USD
        # Total risk value = 100 (EUR/USD) + 5000 (USD/JPY) = 5100 USD
        # Equity still 100000 (assuming no P&L from EUR/USD yet for simplicity of this risk calc)
        # Expected total risk % = 5100 / 100000 = 0.051 (5.1%)
        current_prices_both_pos = {"EUR/USD": 1.1000, "USD/JPY": 130.00} # Keep prices at entry for simplicity
        pm.update_unrealized_pnl(current_prices_both_pos) # Update PnL to ensure equity is correct
        self.assertAlmostEqual(pm.get_total_equity(current_prices_both_pos), 100000) # Should be 100k as prices are at entry
        self.assertAlmostEqual(pm.get_current_total_open_risk_percentage(current_prices_both_pos), 0.051)


    def test_pm_update_unrealized_pnl_and_equity(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol = "EUR/USD"
        pm.open_position(symbol, "buy", 10000, 1.1000, datetime.now(timezone.utc), 1.0900, "pnl_test", 0.5, 0)

        current_prices = {symbol: 1.1020} # 20 pips profit
        pm.update_unrealized_pnl(current_prices)

        position = pm.get_open_position(symbol)
        # Unrealized P&L = (1.1020 - 1.1000) * 10000 = 0.0020 * 10000 = 20
        self.assertAlmostEqual(position.unrealized_pnl, 20.0)

        # Capital was 100000 - 0.5 (commission) = 99999.5
        # Equity = Capital + Unrealized P&L = 99999.5 + 20 = 100019.5
        equity = pm.get_total_equity(current_prices)
        self.assertAlmostEqual(equity, 100019.5)

    # 11. Tests for calculate_position_size (New Signature)
    def test_calc_pos_size_basic_new_signature(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol = "EUR/USD"
        atr_value = 0.0010 # 10 pips for EUR/USD
        current_prices = {symbol: 1.1000, "USD/JPY": 130.00} # Need prices for equity calc

        # risk_percentage_per_trade = 0.01 (1000 USD)
        # stop_loss_atr_multiplier = 2.0
        # stop_loss_pips_for_trade = 2.0 * 0.0010 = 0.0020 (20 pips)
        # pip_value_for_symbol (EUR/USD) = 0.0001
        # risk_per_unit_trade = 0.0020 * 0.0001 = 0.0000002 (Mistake here, pip_value is value of 1 pip, not price increment)
        # Correct risk_per_unit_trade: stop_loss_pips (20) * pip_value_for_1_unit_1_pip (0.0001 USD for EURUSD if 1 unit)
        # The config pip_point_value is the value of 1 pip *per standard price increment*.
        # So, risk_per_unit_trade = stop_loss_pips_for_trade (0.0020 = 20 pips) * (pip_point_value[EUR/USD] / point_size[EUR/USD])
        # Let's use the definition in calculate_position_size:
        # stop_loss_pips_for_trade = ATR (0.0010) * Multiplier (2) = 0.0020
        # risk_per_unit_trade = stop_loss_pips_for_trade (as price change) * pip_value_for_symbol (value of 1 point change)
        # This needs pip_value_for_symbol to be "value per unit per point of price change".
        # Config pip_point_value is "value of 1 pip". A pip is 0.0001 for EURUSD.
        # So, if price moves by 1 pip (0.0001), value changes by pip_point_value.
        # Risk per unit = (stop_loss_pips_for_trade / pip_size) * pip_value_for_symbol (per unit)
        # This is simpler: risk_per_unit_trade = (stop_loss_pips_for_trade / 0.0001) * self.sample_config['pip_point_value'][symbol]
        # stop_loss_pips_for_trade = 20 pips (0.0020 in price)
        # risk_per_unit_trade = 20 pips * 0.0001 USD/pip/unit = 0.002 USD per unit.

        # monetary_risk_per_trade = 100000 * 0.01 = 1000 USD
        # num_units_trade_risk_limited = floor(1000 USD / 0.002 USD/unit) = floor(500000) = 500000 units.
        # max_units_per_market for EUR/USD = 500000. available_units_market = 500000.
        # num_units_market_limited = min(500000, 500000) = 500000.
        # current_total_open_risk_perc = 0 (no open positions)
        # potential_new_trade_risk_value = 500000 units * 0.002 USD/unit = 1000 USD.
        # potential_total_risk_value = 0 + 1000 = 1000 USD.
        # potential_total_risk_perc = 1000 / 100000 = 0.01.
        # total_risk_percentage_limit = 0.05.  0.01 <= 0.05. So, no change.
        # Expected units = 500000.

        size = tl.calculate_position_size(pm, symbol, atr_value, current_prices, self.sample_config)
        self.assertEqual(size, 500000)

    def test_calc_pos_size_exceeds_total_risk_limit_new_sig(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        symbol_eurusd = "EUR/USD"
        symbol_usdjpy = "USD/JPY"
        atr_eurusd = 0.0010 # 10 pips, risk per unit = 0.002 USD
        atr_usdjpy = 0.10   # 10 pips, risk per unit = 0.10 * 2 * 0.01 = 0.002 USD (mistake here, pip for JPY is 0.01)
                            # For USDJPY, 1 pip = 0.01 price increment.
                            # stop_loss_pips_usdjpy = 2 * 0.10 (ATR price units) = 0.20 (price units)
                            # This is 0.20 / 0.01 = 20 pips.
                            # risk_per_unit_usdjpy = 20 pips * 0.01 USD/pip/unit = 0.20 USD per unit.

        current_prices = {symbol_eurusd: 1.1000, symbol_usdjpy: 130.00}

        # Open a position in EUR/USD first, 250,000 units. Risk = 250000 * 0.002 = 500 USD (0.5% of equity)
        # SL for EUR/USD is 1.1000 - 0.0020 = 1.0980
        pm.open_position(symbol_eurusd, "buy", 250000, 1.1000, datetime.now(timezone.utc), 1.0980, "eurusd_pos", 0, 0)
        # pm.capital is now 100000. Position risk is 500. current_total_open_risk_perc = 500/100000 = 0.005

        # Now try to size for USD/JPY
        # monetary_risk_per_trade = 1000 USD
        # risk_per_unit_usdjpy = 0.20 USD
        # num_units_trade_risk_limited = floor(1000 / 0.20) = 50000 units
        # max_units_usdjpy = 5,000,000. available = 5M. num_units_market_limited = 50000.

        # Total Risk Limit Check:
        # current_total_open_risk_perc = 0.005 (from EUR/USD position)
        # potential_new_trade_risk_value (USDJPY) = 50000 units * 0.20 USD/unit = 10000 USD
        # current_total_risk_value = 0.005 * 100000 = 500 USD
        # potential_total_risk_value = 500 + 10000 = 10500 USD
        # potential_total_risk_perc = 10500 / 100000 = 0.105
        # total_risk_percentage_limit = 0.05.  0.105 > 0.05.
        # allowed_additional_monetary_risk = max(0, (0.05 * 100000) - 500) = max(0, 5000 - 500) = 4500 USD
        # affordable_units_for_additional_risk = floor(4500 / 0.20) = floor(22500) units.
        # num_units_final = min(50000, 22500) = 22500.

        size = tl.calculate_position_size(pm, symbol_usdjpy, atr_usdjpy, current_prices, self.sample_config)
        self.assertEqual(size, 22500)

    def test_calc_pos_size_no_equity_new_signature(self):
        pm = tl.PortfolioManager(initial_capital=0, config=self.sample_config) # Zero equity
        size = tl.calculate_position_size(pm, "EUR/USD", 0.0010, {"EUR/USD": 1.1}, self.sample_config)
        self.assertEqual(size, 0)

    def test_calc_pos_size_atr_zero_new_signature(self):
        pm = tl.PortfolioManager(initial_capital=100000, config=self.sample_config)
        size = tl.calculate_position_size(pm, "EUR/USD", 0, {"EUR/USD": 1.1}, self.sample_config)
        self.assertEqual(size, 0)

    # 12. Integration Tests for run_strategy
    def test_run_strategy_basic_flow(self):
        initial_capital = 100000.0
        test_df = self._create_integration_test_df(num_periods=25) # Use 25 periods for this test

        # --- Manually craft data points to ensure signal triggers ---
        # Config: entry_donchian_period = 5, take_profit_long_exit_period = 3
        # Start offset in run_strategy is max(5,3,3) = 5. Loop starts at index 5 (6th row).

        # TESTA: Entry (Long)
        # Ensure data at index 6 (7th row) triggers a long entry for TESTA.
        # Donchian period 5, uses data from index 1 to 5 for Donchian calc for signal at index 6.
        # Donchian Upper for entry at index 6 looks at Highs from index 1 to 5.
        # test_df.loc[test_df.index[1:6], ('TESTA', 'High')] needs to be < test_df.loc[test_df.index[6], ('TESTA', 'Close')]
        test_df.loc[test_df.index[1:6], ('TESTA', 'High')] = 102 # Keep previous highs low
        test_df.loc[test_df.index[6], ('TESTA', 'Close')] = 103 # Breakout close
        test_df.loc[test_df.index[6], ('TESTA', 'High')] = 103.1 # Ensure high is above close

        # TESTA: Stop-Loss
        # Entry at index 6, price 103. ATR=0.5. SL mult=2. SL dist = 1.0. SL price = 103 - 1.0 = 102.0
        # Trigger SL at index 10.
        test_df.loc[test_df.index[10], ('TESTA', 'Low')] = 101.9 # Hit SL
        test_df.loc[test_df.index[10], ('TESTA', 'Close')] = 101.9 # Close at SL hit

        # TESTB: Entry (Long)
        # Ensure data at index 12 triggers a long entry for TESTB.
        # (Assuming TESTA position is closed by SL before this, so no total risk issue for entry)
        # Donchian Upper for entry at index 12 looks at Highs from index 7 to 11.
        test_df.loc[test_df.index[7:12], ('TESTB', 'High')] = 2050
        test_df.loc[test_df.index[12], ('TESTB', 'Close')] = 2060 # Breakout close
        test_df.loc[test_df.index[12], ('TESTB', 'High')] = 2061

        # TESTB: Take-Profit (Donchian Exit)
        # Entry at index 12, price 2060. Long position.
        # Take profit is 3-period low.
        # To exit at index 16: Close[16] < min(Low[13], Low[14], Low[15]) (shifted)
        test_df.loc[test_df.index[13], ('TESTB', 'Low')] = 2055
        test_df.loc[test_df.index[14], ('TESTB', 'Low')] = 2054
        test_df.loc[test_df.index[15], ('TESTB', 'Low')] = 2053 # Min low is 2053 for exit signal at index 16
        test_df.loc[test_df.index[16], ('TESTB', 'Close')] = 2052 # Trigger TP exit
        test_df.loc[test_df.index[16], ('TESTB', 'High')] = 2052.1 # ensure high/low accommodate close
        test_df.loc[test_df.index[16], ('TESTB', 'Low')] = 2051.9


        results = tl.run_strategy(test_df, initial_capital, self.integration_test_config)
        trade_log_df = pd.DataFrame(results['trade_log'])

        # Assertions
        self.assertGreater(len(results['equity_curve']), 0)
        self.assertGreater(len(results['orders']), 0)
        self.assertGreater(len(results['trade_log']), 0)

        # TESTA assertions
        testa_trades = trade_log_df[trade_log_df['symbol'] == 'TESTA']
        self.assertEqual(len(testa_trades), 2) # Entry and Stop-loss
        entry_testa = testa_trades[testa_trades['type'] == 'entry'].iloc[0]
        sl_testa = testa_trades[testa_trades['type'] == 'exit'].iloc[0] # SL is an exit

        self.assertEqual(entry_testa['action'], 'buy')
        self.assertAlmostEqual(entry_testa['price'], 103 + (self.integration_test_config['slippage_pips'] * self.integration_test_config['pip_point_value']['TESTA']))

        # Check SL order for TESTA in main order list
        entry_order_id_testa = entry_testa['order_id']
        sl_order_for_entry_testa = next(o for o in results['orders'] if o.order_id == f"{entry_order_id_testa}_sl")
        self.assertEqual(sl_order_for_entry_testa.status, "filled") # SL was hit
        self.assertEqual(sl_order_for_entry_testa.order_id, sl_testa['order_id'])


        # TESTB assertions
        testb_trades = trade_log_df[trade_log_df['symbol'] == 'TESTB']
        self.assertEqual(len(testb_trades), 2) # Entry and Take-profit
        entry_testb = testb_trades[testb_trades['type'] == 'entry'].iloc[0]
        tp_testb = testb_trades[testb_trades['type'] == 'exit'].iloc[0]

        self.assertEqual(entry_testb['action'], 'buy')
        self.assertAlmostEqual(entry_testb['price'], 2060 + (self.integration_test_config['slippage_pips'] * self.integration_test_config['pip_point_value']['TESTB']))

        # Check SL order for TESTB (should be cancelled as TP was hit)
        entry_order_id_testb = entry_testb['order_id']
        sl_order_for_entry_testb = next(o for o in results['orders'] if o.order_id == f"{entry_order_id_testb}_sl")
        self.assertEqual(sl_order_for_entry_testb.status, "cancelled")
        self.assertEqual(tp_testb['order_id'], f"TESTB_{test_df.index[16].strftime('%Y%m%d%H%M')}_tp_exit_{len(results['orders'])-2}") # approx ID check

        # Check P&L and commissions (example for one trade)
        # TESTA SL: Entry 103.02 (price + slippage), SL order price 102.0. Fill price for SL order 102 - slippage = 101.996
        # P&L = (101.996 - 103.02) * entry_testa['quantity'] - entry_testa['commission'] - sl_testa['commission']
        self.assertTrue('realized_pnl' in sl_testa)
        self.assertTrue(sl_testa['realized_pnl'] < 0) # Should be a loss
        self.assertTrue(tp_testb['realized_pnl'] > 0) # Should be a profit for TESTB TP


    def test_run_strategy_risk_limits_max_units(self):
        initial_capital = 10000.0 # Smaller capital for easier % risk impact
        test_df = self._create_integration_test_df(num_periods=15)

        # Config: max_units_per_market for TESTA is 50. risk_percentage_per_trade = 0.10
        # ATR for TESTA = 0.5. SL multiplier = 2. SL distance = 1.0 price units.
        # Pip value for TESTA = 0.01. Risk per unit = 1.0 * 0.01 = 0.01 USD.
        # Monetary risk per trade = 10000 * 0.10 = 1000 USD.
        # Units based on trade risk = 1000 / 0.01 = 100,000 units.
        # This should be capped by max_units_per_market = 50.

        # Ensure entry for TESTA
        test_df.loc[test_df.index[1:6], ('TESTA', 'High')] = 102
        test_df.loc[test_df.index[6], ('TESTA', 'Close')] = 103
        test_df.loc[test_df.index[6], ('TESTA', 'High')] = 103.1

        results = tl.run_strategy(test_df, initial_capital, self.integration_test_config)
        trade_log_df = pd.DataFrame(results['trade_log'])

        testa_entry_trades = trade_log_df[(trade_log_df['symbol'] == 'TESTA') & (trade_log_df['type'] == 'entry')]
        self.assertEqual(len(testa_entry_trades), 1)
        self.assertEqual(testa_entry_trades.iloc[0]['quantity'], self.integration_test_config['max_units_per_market']['TESTA']) # Should be 50


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

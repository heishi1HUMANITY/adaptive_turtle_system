import unittest
import pandas as pd
import numpy as np # For NaN and other numerical utilities
from pandas.testing import assert_series_equal

# Assuming trading_logic.py is in the same directory or accessible in PYTHONPATH
import trading_logic as tl

class TestTradingLogic(unittest.TestCase):

    def setUp(self):
        """Setup common data for tests."""
        # Sample price data for general use
        self.price_data = pd.DataFrame({
            'high': [10, 12, 11, 13, 14, 15, 13, 12, 11, 10],
            'low':  [8,  9,  10, 10, 11, 12, 11, 10, 9,  8],
            'close':[9,  11, 10, 12, 13, 14, 12, 11, 10, 9]
        })
        self.high_series = self.price_data['high']
        self.low_series = self.price_data['low']
        self.close_series = self.price_data['close']

    # 1. Tests for calculate_donchian_channel
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

    # 5. Tests for calculate_position_size
    def test_calculate_position_size_basic(self):
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=0.0050, # 50 pips if price is X.XXXX
            pip_value_per_lot=10, lot_size=100000, # Forex standard
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.02
        )
        # risk_amount_per_trade = 100000 * 0.01 = 1000
        # stop_loss_pips = 2 * 0.0050 = 0.0100 (which is 100 pips if 1 pip = 0.0001)
        # Assuming ATR is given in price units, so 0.0050 is 50 pips if 1 pip = 0.0001
        # Let's clarify ATR input. If ATR is 50 (pips), then stop_loss_pips = 2 * 50 = 100 pips.
        # Let's re-evaluate with ATR = 50 (pips) for clarity, not price units.
        # Recalculate with ATR = 50 pips
        # stop_loss_pips = 2 * 50 = 100 pips
        # risk_per_lot = 100 pips * $10/pip/lot = 1000
        # num_lots_raw = risk_amount_per_trade (1000) / risk_per_lot (1000) = 1 lot
        # num_units = floor(1 * 100000) = 100000 units.

        # Market limit: available = 1M - 0 = 1M. num_units = min(100k, 1M) = 100k.
        # Total risk limit:
        # max_additional_monetary_risk = (100k * 0.05) - (100k * 0.02) = 5000 - 2000 = 3000
        # risk_of_this_trade_monetary = (100k / 100k lotsize) * 1000 risk/lot = 1 * 1000 = 1000
        # 1000 <= 3000. So, num_units is not changed by total risk limit.
        # Expected: 100000

        # Re-running the logic with ATR = 50 (pips)
        size_clarified_atr = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50, # ATR is 50 pips
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.02
        )
        self.assertEqual(size_clarified_atr, 100000)

    def test_calculate_position_size_atr_zero(self):
        size = tl.calculate_position_size(100000, 0.01, 0, 10, 100000, 1000000, 0, 0.05, 0.02)
        self.assertEqual(size, 0)

    def test_calculate_position_size_pip_value_zero(self):
        size = tl.calculate_position_size(100000, 0.01, 50, 0, 100000, 1000000, 0, 0.05, 0.02)
        self.assertEqual(size, 0)

    def test_calculate_position_size_exceeds_market_limit(self):
        # Same as basic, but max_units_per_market is small
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=50000, current_units_for_market=0, # Max 50k units
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.02
        )
        # Initial units = 100000. Available market = 50000. So, capped at 50000.
        # Risk of 50k units = 0.5 lots * 1000 risk/lot = 500. This is < 3000 (max_additional_monetary_risk).
        self.assertEqual(size, 50000)

    def test_calculate_position_size_market_limit_current_full(self):
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=50000, current_units_for_market=50000, # Already at max
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.02
        )
        # Available market = 50000 - 50000 = 0.
        self.assertEqual(size, 0)

    def test_calculate_position_size_exceeds_total_risk_limit(self):
        # Basic calc gives 100k units (1 lot), risk is 1000 (1% of equity)
        # Make current_total_open_risk_percentage higher so this trade is too risky
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.045 # Only 0.005 (500 monetary) risk left
        )
        # risk_amount_per_trade = 1000. stop_loss_pips=100. risk_per_lot=1000. num_lots_raw=1. num_units=100k.
        # Market limit: 1M, OK.
        # Total risk: max_additional_monetary_risk = (100k*0.05) - (100k*0.045) = 5000 - 4500 = 500.
        # risk_of_this_trade_monetary for 100k units (1 lot) = 1 * 1000 = 1000.
        # 1000 > 500. So, scale down.
        # affordable_lots = 500 / 1000 = 0.5 lots.
        # num_units = floor(0.5 * 100000) = 50000.
        self.assertEqual(size, 50000)

    def test_calculate_position_size_total_risk_limit_already_met(self):
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.05 # Already at limit
        )
        self.assertEqual(size, 0)

    def test_calculate_position_size_total_risk_limit_already_exceeded(self):
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.06 # Exceeded limit
        )
        self.assertEqual(size, 0)

    def test_calculate_position_size_zero_equity(self):
        with self.assertRaises(ValueError): # Validation should catch this
             tl.calculate_position_size(0, 0.01, 50, 10, 100000, 1000000, 0, 0.05, 0.02)

    def test_calculate_position_size_invalid_risk_percentage(self):
        with self.assertRaises(ValueError):
            tl.calculate_position_size(100000, 1.5, 50, 10, 100000,1000000, 0, 0.05, 0.02) # >1
        with self.assertRaises(ValueError):
            tl.calculate_position_size(100000, 0, 50, 10, 100000,1000000, 0, 0.05, 0.02) # ==0
        with self.assertRaises(ValueError):
            tl.calculate_position_size(100000, -0.01, 50, 10, 100000,1000000, 0, 0.05, 0.02) # <0

    def test_calculate_position_size_no_risk_capital_left_for_trade(self):
        # Scenario: total risk allows some, but not enough for even 1 unit if risk_per_lot is high
        size = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=0.01, # atr = 1 pip
            pip_value_per_lot=10, lot_size=100000, # risk_per_lot = 2*1*10 = 20
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.0499 # only 0.0001% risk capital left = $10
        )
        # risk_amount_per_trade = 1000
        # stop_loss_pips = 2 * 1 = 2 pips
        # risk_per_lot = 2 pips * $10/pip/lot = 20
        # num_lots_raw = 1000 / 20 = 50 lots. num_units = 5,000,000
        # Market limit: 1M. num_units = 1,000,000
        # Total risk: max_additional_monetary_risk = (100k*0.05) - (100k*0.0499) = 5000 - 4990 = 10
        # risk_of_this_trade_monetary for 1M units (10 lots) = 10 * 20 = 200.
        # 200 > 10. So, scale down.
        # affordable_lots = 10 / 20 = 0.5 lots.
        # num_units = floor(0.5 * 100000) = 50000.
        self.assertEqual(size, 50000)

        # If max_additional_monetary_risk was even smaller, e.g., 5 (less than risk_per_lot for 1 unit)
        size_very_low_remaining_risk = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=0.01,
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.04995 # only 0.00005% risk capital left = $5
        )
        # max_additional_monetary_risk = 5000 - 4995 = 5
        # affordable_lots = 5 / 20 = 0.25 lots
        # num_units = floor(0.25 * 100000) = 25000
        self.assertEqual(size_very_low_remaining_risk, 25000)

        # What if max_additional_monetary_risk_allowed is positive but too small for 1 unit?
        # e.g., risk_per_unit = risk_per_lot / lot_size = 20 / 100000 = 0.0002
        # if max_additional_monetary_risk_allowed = 0.0001, then affordable_units = 0.0001 / 0.0002 = 0.5 units. floor(0.5) = 0
        size_tiny_risk = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.0000001, atr=0.01, # risk_per_trade is 0.01
            pip_value_per_lot=10, lot_size=100000,
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.0 # Plenty of total risk
        )
        # risk_amount_per_trade = 100000 * 0.0000001 = 0.01
        # risk_per_lot = 20
        # num_lots_raw = 0.01 / 20 = 0.0005
        # num_units = floor(0.0005 * 100000) = floor(50) = 50.
        # Risk of this trade = (50/100000) * 20 = 0.0005 * 20 = 0.01. This is fine.
        self.assertEqual(size_tiny_risk, 50)

        # Test case where num_units becomes 0 after total risk constraint
        size_becomes_zero = tl.calculate_position_size(
            account_equity=100000, risk_percentage=0.01, atr=50, # risk_per_lot = 1000
            pip_value_per_lot=10, lot_size=1, # lot_size = 1 for easy check of unit count
            max_units_per_market=1000000, current_units_for_market=0,
            total_risk_percentage_limit=0.05, current_total_open_risk_percentage=0.049999 # Allow $1 risk
        )
        # risk_amount_per_trade = 1000. num_lots_raw = 1000/1000 = 1. num_units = 1. (since lot_size=1)
        # available_units_market = 1M. num_units = min(1, 1M) = 1.
        # max_additional_monetary_risk = (100k*0.05) - (100k*0.049999) = 5000 - 4999.9 = 0.1
        # risk_of_this_trade_monetary = (1 unit / 1 unit_per_lot) * 1000 risk_per_lot = 1000.
        # 1000 > 0.1. So scale down.
        # affordable_lots = 0.1 / 1000 = 0.0001
        # num_units = floor(0.0001 * 1 (lot_size)) = floor(0.0001) = 0.
        self.assertEqual(size_becomes_zero, 0)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

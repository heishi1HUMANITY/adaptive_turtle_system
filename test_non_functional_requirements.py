import unittest
import tempfile
import shutil
import os
import json
import sys
import copy # Added for deepcopy
from io import StringIO
import pandas as pd
from unittest.mock import patch, mock_open

# Add project root to sys.path to allow direct import of modules
# Assuming the test script is run from the root or a similar context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now try importing the modules
try:
    import main_backtest
    import config_loader
    import data_loader
    # trading_logic is not directly tested here for logging, but main_backtest uses it.
    # logger.py is used by other modules.
except ImportError as e:
    print(f"Error importing modules: {e}. Check sys.path and file locations.")
    # To prevent further errors if imports fail, raise the error or exit
    raise

class TestNonFunctionalRequirements(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_stdout = StringIO()
        self.mock_stderr = StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self.mock_stdout
        sys.stderr = self.mock_stderr

        # Default config content
        self.default_config_data = {
            "market": "EUR/USD",
            "timeframe": "H1",
            "stop_loss_atr_multiplier": 2,
            "take_profit_atr_multiplier": 10,
            "risk_per_trade": 1.0, # Representing 1%
            "max_units_per_market": { "EUR/USD": 40000 },
            "max_total_risk_percentage": 5.0, # Representing 5%
            "total_portfolio_risk_limit": 0.05, # Consistent name used in code
            "slippage_pips": 0.2,
            "commission_per_lot": 500,
            "markets": ["EUR/USD"],
            "take_profit_long_exit_period": 10,
            "take_profit_short_exit_period": 10,
            "entry_donchian_period": 20,
            "atr_period": 20,
            "account_currency": "JPY",
            "initial_capital": 1000000.0,
            "pip_point_value": {"EUR/USD": 0.0001},
            "lot_size": {"EUR/USD": 100000},
            "logging": {
                "log_file_path": os.path.join(self.test_dir, "test_run.log"),
                "log_level": "INFO"
            },
            "emergency_stop": False
        }
        self.config_file_path = os.path.join(self.test_dir, "config.json")
        self._write_config(self.default_config_data)

        # Default historical data
        self.historical_data_file_path = os.path.join(self.test_dir, "historical_data.csv")
        # Call with a default that is sufficient for ATR and Donchian periods
        self._create_dummy_historical_data(self.historical_data_file_path, rows=max(self.default_config_data.get("entry_donchian_period", 20), self.default_config_data.get("atr_period", 20)) + 5)


    def _write_config(self, data):
        with open(self.config_file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _create_dummy_historical_data(self, filepath, rows=20):
        start_date = pd.to_datetime('2023-01-01 00:00:00')
        timestamps = pd.date_range(start=start_date, periods=rows, freq='D')

        base_price = 1.1000
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        # Use entry_donchian_period from default_config_data if available, else 20
        # This ensures test data generation aligns with potential config changes.
        entry_donchian_period = self.default_config_data.get("entry_donchian_period", 20)

        for i in range(rows):
            open_val = base_price + (i * 0.00001) # Minimal trend
            high_val = open_val + 0.0001 # Default tight high
            low_val = open_val - 0.0001  # Default tight low
            close_val = open_val         # Default flat close
            volume = 1000 + i * 10

            # Logic to generate a breakout signal
            # Condition for signal at loop index `idx = entry_donchian_period + 1` (e.g. 21 for P=20)
            # is Close[P] > max(High[1...P])
            if rows >= entry_donchian_period + 2: # Ensure enough data for the logic below
                # Phase 1: Data for indices 0 to P-1 (e.g., 0-19 for P=20)
                # These highs will form the Donchian band for the signal.
                if i < entry_donchian_period:
                    open_val = base_price
                    high_val = base_price + 0.0010 # Capped high for the formation period
                    low_val = base_price - 0.0010
                    close_val = base_price

                # Phase 2: Data for index P (e.g., 20 for P=20)
                # Close[P] is the `prev_close` for the signal check at loop index P+1.
                # High[P] is part of the Donchian window max(High[1...P]).
                elif i == entry_donchian_period:
                    open_val = base_price # Can be same as previous
                    # Set High[P] to be the same as previous highs to control the Donchian band
                    high_val = base_price + 0.0010
                    low_val = base_price - 0.0005 # Arbitrary low
                    # Set Close[P] to be above the established Donchian band (max(High[0...P-1]))
                    # and also above High[P] for the condition Close[P] > max(High[1...P])
                    close_val = base_price + 0.0020 # This ensures Close[P] > H_cap (0.0010)

                # Phase 3: Post-signal bars (optional, to keep trade open)
                elif i > entry_donchian_period and i < entry_donchian_period + 5:
                    open_val = closes[-1] # Open at previous close
                    high_val = open_val + 0.0005
                    low_val = open_val - 0.0005
                    close_val = open_val + (0.0001 if i % 2 == 0 else -0.0001)

            # Ensure OHLC consistency
            current_prices = [open_val, high_val, low_val, close_val]
            final_high = max(current_prices)
            final_low = min(current_prices)
            # Ensure close is within high and low
            final_close = min(max(close_val, final_low), final_high)
            # Ensure open is within high and low
            final_open = min(max(open_val, final_low), final_high)

            if final_high == final_low: # Avoid flat bar
                final_high += 0.0001

            opens.append(final_open)
            highs.append(final_high)
            lows.append(final_low)
            closes.append(final_close)
            volumes.append(volume)

        data = {
            'Timestamp': timestamps,
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)

    def tearDown(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        shutil.rmtree(self.test_dir)

    # --- Test Implementations Will Go Here ---

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_log_file_creation_and_format(self, mock_generate_report, mock_calculate_kpis, mock_run_strategy, mock_load_data, mock_load_config_main):
        # This mock_load_config_main is for the main_backtest.py's direct call
        # It ensures that main_backtest.main() gets the config it needs to setup logging.
        mock_load_config_main.return_value = self.default_config_data

        dummy_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2023-01-01']),
            'Open': [1.0], 'High': [1.1], 'Low': [0.9], 'Close': [1.05], 'Volume': [100]
        })
        # Ensure a fresh copy of dummy_df is returned each time load_csv_data is called
        mock_load_data.side_effect = lambda *args, **kwargs: dummy_df.copy()
        mock_run_strategy.return_value = {
            "equity_curve": [(pd.Timestamp('2023-01-01'), 1000000)], "trade_log": [], "final_capital": 1000000,
            "portfolio_summary": {"initial_capital": 1000000, "final_equity": 1000000, "total_trades": 0}
        }
        mock_calculate_kpis.return_value = {"total_return": 0.0}
        mock_generate_report.return_value = None

        # Call main. main_backtest.main will call config_loader.load_config('config.json')
        # which is mocked by mock_load_config_main.
        # It will also call data_loader.load_csv_data('historical_data.csv'), mocked by mock_load_data.
        main_backtest.main()

        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path), "Log file was not created.")

        with open(log_file_path, 'r') as f:
            log_content = f.read()

        self.assertIn("Configuration loaded:", log_content, "Expected log message not found.")
        # Example: 2023-10-26 10:00:00,123 - INFO - main_backtest - Configuration loaded: ...
        # A more robust regex might be: r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - \w+ - [\w.]+ - .+"
        # For simplicity, just check for a known part of the message for now.
        self.assertRegex(log_content, r"- INFO - main_backtest - Starting backtest process...")
        self.assertRegex(log_content, r"- INFO - main_backtest - Configuration loaded:")
        # Check for the format: timestamp - LEVEL - module - message
        # This regex is basic. A stricter one would validate each part more thoroughly.
        self.assertRegex(log_content, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - INFO - main_backtest - ")

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_different_log_levels(self, mock_generate_report, mock_calculate_kpis, mock_run_strategy, mock_load_data, mock_load_config_main):
        # Common mock setups
        # Provide a slightly more substantial dummy_df to avoid issues with ATR calculation if strategy runs further
        num_rows_dummy = max(self.default_config_data.get("entry_donchian_period", 20), self.default_config_data.get("atr_period", 20)) + 5
        dummy_df_data = {
            'Timestamp': pd.date_range(start='2023-01-01', periods=num_rows_dummy, freq='D'),
            'Open': [1.0 + i*0.001 for i in range(num_rows_dummy)], # Use different data than global dummy
            'High': [1.005 + i*0.001 for i in range(num_rows_dummy)],
            'Low': [0.995 + i*0.001 for i in range(num_rows_dummy)],
            'Close': [1.0 + i*0.001 for i in range(num_rows_dummy)],
            'Volume': [100 + i*10 for i in range(num_rows_dummy)]
        }
        dummy_df_for_this_test = pd.DataFrame(dummy_df_data)

        mock_load_data.side_effect = lambda *args, **kwargs: dummy_df_for_this_test.copy()
        mock_run_strategy.return_value = {
            "equity_curve": [(pd.Timestamp('2023-01-01'), 1000000)], "trade_log": [], "final_capital": 1000000,
            "portfolio_summary": {"initial_capital": 1000000, "final_equity": 1000000, "total_trades": 0}
        }
        mock_calculate_kpis.return_value = {"total_return": 0.0}
        mock_generate_report.return_value = None

        # --- Test DEBUG level ---
        debug_log_file_path = os.path.join(self.test_dir, "debug_test.log")
        debug_config = copy.deepcopy(self.default_config_data)
        debug_config["logging"]["log_level"] = "DEBUG"
        debug_config["logging"]["log_file_path"] = debug_log_file_path
        self._write_config(debug_config)
        mock_load_config_main.return_value = debug_config
        main_backtest.main()

        self.assertTrue(os.path.exists(debug_log_file_path))
        with open(debug_log_file_path, 'r') as f:
            log_content_debug = f.read()
        self.assertIn("Test DEBUG message: main_backtest main_logger initialized.", log_content_debug)
        self.assertIn("Configuration loaded:", log_content_debug)

        # --- Test WARNING level (console output part for incomplete config) ---
        if os.path.exists(debug_log_file_path): os.remove(debug_log_file_path)
        warning_config_incomplete = copy.deepcopy(self.default_config_data)
        warning_config_incomplete["logging"]["log_level"] = "WARNING"
        del warning_config_incomplete["logging"]["log_file_path"] # Trigger incompleteness
        self._write_config(warning_config_incomplete)
        mock_load_config_main.return_value = warning_config_incomplete
        main_backtest.main()
        self.assertIn("Warning: Logging configuration missing or incomplete", self.mock_stdout.getvalue())

        # --- Test WARNING Log Level (File Content for specific warning message) ---
        default_log_file_to_clean = self.default_config_data["logging"]["log_file_path"] # Path from original default config
        if os.path.exists(default_log_file_to_clean): os.remove(default_log_file_to_clean)

        # Use a different log file for this specific warning test
        warning_specific_log_path = os.path.join(self.test_dir, "warning_specific_test.log")
        warning_config_specific = copy.deepcopy(self.default_config_data) # Fresh copy
        warning_config_specific["logging"]["log_level"] = "WARNING"
        warning_config_specific["logging"]["log_file_path"] = warning_specific_log_path
        warning_config_specific["emergency_stop"] = True # To ensure a WARNING message is logged
        self._write_config(warning_config_specific)
        mock_load_config_main.return_value = warning_config_specific
        main_backtest.main()

        self.assertTrue(os.path.exists(warning_specific_log_path))
        with open(warning_specific_log_path, 'r') as f:
            log_content_warning = f.read()
        self.assertNotIn("Test DEBUG message: main_backtest main_logger initialized.", log_content_warning)
        self.assertNotIn("Configuration loaded:", log_content_warning)
        self.assertIn("EMERGENCY STOP ACTIVATED", log_content_warning)
        self.assertRegex(log_content_warning, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - WARNING - main_backtest - EMERGENCY STOP ACTIVATED")

    def test_console_warning_for_default_logging_config(self):
        config_missing_logging_keys = copy.deepcopy(self.default_config_data)
        del config_missing_logging_keys["logging"]["log_level"]
        self._write_config(config_missing_logging_keys)
        with patch('main_backtest.config_loader.load_config', return_value=config_missing_logging_keys):
            try:
                main_backtest.main()
            except SystemExit:
                pass
            except Exception:
                pass
        self.assertIn("Warning: Logging configuration missing or incomplete", self.mock_stdout.getvalue())

    # --- Error Handling Tests ---
    def test_missing_config_file(self):
        with patch('main_backtest.config_loader.load_config', side_effect=FileNotFoundError("Simulated FileNotFoundError for config.json")):
            try:
                main_backtest.main()
            except SystemExit:
                pass
        self.assertIn("Critical Error: Required file not found before logger initialization", self.mock_stdout.getvalue())

    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_corrupted_config_file(self, mock_report, mock_kpis, mock_strategy, mock_data_load):
        with patch('main_backtest.config_loader.load_config', side_effect=json.JSONDecodeError("Simulated JSON error", "doc", 0)):
            try:
                main_backtest.main()
            except SystemExit:
                pass
        self.assertIn("Critical Error: Value error before logger initialization: Simulated JSON error", self.mock_stdout.getvalue())

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_missing_historical_data_file(self, mock_report, mock_kpis, mock_strategy, mock_load_config):
        mock_load_config.return_value = self.default_config_data
        with patch('main_backtest.data_loader.load_csv_data', side_effect=FileNotFoundError(f"Simulated FileNotFoundError for {self.historical_data_file_path}")):
            try:
                main_backtest.main()
            except SystemExit:
                pass
        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("main_backtest - Error: Required file not found", log_content)
        self.assertIn("Simulated FileNotFoundError", log_content)

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_empty_historical_data_file(self, mock_report, mock_kpis, mock_strategy, mock_load_config):
        mock_load_config.return_value = self.default_config_data
        with patch('main_backtest.data_loader.load_csv_data', side_effect=pd.errors.EmptyDataError("Simulated EmptyDataError")):
            try:
                main_backtest.main()
            except SystemExit:
                pass
            except pd.errors.EmptyDataError:
                pass
        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("main_backtest - Error: Value error encountered: Simulated EmptyDataError", log_content)
        self.assertIn("Simulated EmptyDataError", log_content)

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.calculate_position_size')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_trading_logic_value_error_propagation(self, mock_report, mock_kpis, mock_calc_pos_size, mock_load_data, mock_load_config):
        mock_load_config.return_value = self.default_config_data

        # Use a specific dummy_df for this test to ensure enough data for ATR etc.
        # if the new _create_dummy_historical_data isn't used by default by this test's mock_load_data
        num_rows_for_test = 50
        test_specific_df_data = {
            'Timestamp': pd.date_range(start='2023-01-01', periods=num_rows_for_test, freq='D'),
            'Open': [1.1000 + i*0.0001 for i in range(num_rows_for_test)],
            'High': [1.1000 + 0.0010 + i*0.0001 for i in range(num_rows_for_test)], # Data that should generate a trade
            'Low': [1.1000 - 0.0010 + i*0.0001 for i in range(num_rows_for_test)],
            'Close': [1.1000 + 0.0020 + i*0.0001 for i in range(num_rows_for_test)], # Breakout close
            'Volume': [1000 + i*10 for i in range(num_rows_for_test)]
        }
        # Ensure High[P] is capped for Donchian, and Close[P] breaks it.
        # P = self.default_config_data.get("entry_donchian_period", 20)
        # test_specific_df_data['High'][P] = test_specific_df_data['Low'][P] + 0.0010 # Keep High[P] low
        # test_specific_df_data['Close'][P] = test_specific_df_data['Low'][P] + 0.0020 # Make Close[P] break max(High[0..P-1])

        # The _create_dummy_historical_data should be providing data that generates trades now.
        # So, we can rely on the mock_load_data set up by _run_main_for_emergency_stop_test
        # or ensure this test uses a DataFrame from _create_dummy_historical_data.
        # For simplicity, let's ensure this test uses data from _create_dummy_historical_data.
        self._create_dummy_historical_data(self.historical_data_file_path, rows=num_rows_for_test)
        current_dummy_df = pd.read_csv(self.historical_data_file_path, parse_dates=['Timestamp'])
        mock_load_data.return_value = current_dummy_df

        mock_calc_pos_size.side_effect = ValueError("Simulated ValueError from calculate_position_size")
        mock_kpis.return_value = {"total_return": 0.0}
        mock_report.return_value = None

        try:
            main_backtest.main()
        except SystemExit:
            pass
        except ValueError as e:
            if "Simulated ValueError" in str(e):
                pass
            else:
                raise

        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        expected_log_message = "main_backtest - Error: Value error encountered: Simulated ValueError from calculate_position_size"
        self.assertIn(expected_log_message, log_content)
        self.assertIn("Simulated ValueError from calculate_position_size", log_content)

    # --- Emergency Stop Tests ---
    def _run_main_for_emergency_stop_test(self, config_overrides):
        test_config = copy.deepcopy(self.default_config_data) # Use deepcopy
        test_config.update(config_overrides)
        if "logging" not in test_config:
            test_config["logging"] = copy.deepcopy(self.default_config_data["logging"])
        test_config["logging"]["log_file_path"] = os.path.join(self.test_dir, "emergency_stop_test.log")
        self._write_config(test_config)

        with patch('main_backtest.config_loader.load_config', return_value=test_config) as mock_cfg_load, \
             patch('main_backtest.data_loader.load_csv_data') as mock_data_load, \
             patch('main_backtest.trading_logic.calculate_position_size') as mock_calc_pos_size, \
             patch('main_backtest.performance_analyzer.calculate_all_kpis') as mock_kpis, \
             patch('main_backtest.performance_analyzer.generate_text_report') as mock_report:

            mock_calc_pos_size.return_value = 1000 # Force position size to be > 0. Added mock for calculate_position_size above.
            self._create_dummy_historical_data(self.historical_data_file_path, rows=50) # Ensure enough rows
            dummy_df_for_run = pd.read_csv(self.historical_data_file_path, parse_dates=['Timestamp'])
            mock_data_load.return_value = dummy_df_for_run # Use this specific df

            mock_kpis.return_value = {"total_return": 0.0}
            mock_report.return_value = None

            global_results_store = {}
            # Signature must match the actual keyword argument 'risk_free_rate_annual'
            def capture_results_for_kpi(backtest_res, cfg, risk_free_rate_annual):
                global_results_store['backtest_results'] = backtest_res
                return {"total_return": 0.0}
            mock_kpis.side_effect = capture_results_for_kpi

            main_backtest.main()
            return global_results_store.get('backtest_results', {}).get('trade_log', [])

    def test_emergency_stop_true_no_new_trades(self):
        trade_log = self._run_main_for_emergency_stop_test({"emergency_stop": True})
        log_file_path = os.path.join(self.test_dir, "emergency_stop_test.log")
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("EMERGENCY STOP ACTIVATED: New trade entries will be disabled.", log_content)
        entry_trades = [trade for trade in trade_log if trade.get("type") == "entry"]
        self.assertEqual(len(entry_trades), 0, "No new entry trades should be made when emergency stop is active.")

    def test_emergency_stop_false_allows_trades(self):
        trade_log = self._run_main_for_emergency_stop_test({"emergency_stop": False})
        log_file_path = os.path.join(self.test_dir, "emergency_stop_test.log")
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("Emergency stop is not activated. System operating normally.", log_content)
        entry_trades = [trade for trade in trade_log if trade.get("type") == "entry"]
        self.assertTrue(len(entry_trades) > 0, "Entry trades should be allowed and generated with this data when emergency stop is false.")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

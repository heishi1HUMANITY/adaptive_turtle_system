import unittest
import tempfile
import shutil
import os
import json
import sys
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
        self._create_dummy_historical_data(self.historical_data_file_path)

    def _write_config(self, data):
        with open(self.config_file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _create_dummy_historical_data(self, filepath, rows=50):
        data = {
            'Timestamp': pd.to_datetime(['2023-01-{:02d} 00:00:00'.format(i+1) for i in range(rows)]),
            'Open': [1.1000 + i*0.001 for i in range(rows)],
            'High': [1.1050 + i*0.001 for i in range(rows)],
            'Low': [1.0950 + i*0.001 for i in range(rows)],
            'Close': [1.1020 + i*0.001 for i in range(rows)],
            'Volume': [1000 + i*10 for i in range(rows)]
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
        mock_load_data.return_value = dummy_df
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
        dummy_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2023-01-01']),
            'Open': [1.0], 'High': [1.1], 'Low': [0.9], 'Close': [1.05], 'Volume': [100]
        })
        mock_load_data.return_value = dummy_df
        mock_run_strategy.return_value = {
            "equity_curve": [(pd.Timestamp('2023-01-01'), 1000000)], "trade_log": [], "final_capital": 1000000,
            "portfolio_summary": {"initial_capital": 1000000, "final_equity": 1000000, "total_trades": 0}
        }
        mock_calculate_kpis.return_value = {"total_return": 0.0}
        mock_generate_report.return_value = None

        # --- Test DEBUG level ---
        debug_log_file_path = os.path.join(self.test_dir, "debug_test.log")
        debug_config = self.default_config_data.copy()
        debug_config["logging"]["log_level"] = "DEBUG"
        debug_config["logging"]["log_file_path"] = debug_log_file_path
        self._write_config(debug_config)
        mock_load_config_main.return_value = debug_config

        main_backtest.main() # main_backtest.py now has a DEBUG log message

        self.assertTrue(os.path.exists(debug_log_file_path))
        with open(debug_log_file_path, 'r') as f:
            log_content_debug = f.read()

        self.assertIn("Test DEBUG message: main_backtest main_logger initialized.", log_content_debug)
        self.assertIn("Configuration loaded:", log_content_debug) # INFO message should also be there

        # --- Test WARNING level ---
        # Clear log file for the next run or use a different log file
        if os.path.exists(debug_log_file_path): os.remove(debug_log_file_path) # clean up previous log

        warning_config = self.default_config_data.copy()
        warning_config["logging"]["log_level"] = "WARNING"
        # Make logging config incomplete to trigger the warning in main_backtest.py
        del warning_config["logging"]["log_file_path"]
        self._write_config(warning_config)
        mock_load_config_main.return_value = warning_config

        main_backtest.main()

        # Log path will be the default one since it was removed from config
        default_log_path_in_setup = os.path.join(self.test_dir, "test_run.log") # as per setUp default
                                                                                # but main_backtest uses "trading_system.log" if key missing
                                                                                # let's check the actual default path logic in main_backtest.py
        # main_backtest.py: default_log_path = "trading_system.log"
        # This means the log file will be created in the CWD of the test runner, not self.test_dir
        # This is not ideal. The test should control the log output path.
        # For this test, let's assume the log path in self.default_config_data is used
        # if only "log_level" is changed.
        # The warning is about missing keys, so it uses the default path from main_backtest's code.
        # This test needs the log file path to be predictable.

        # Let's refine: the warning log itself might go to console if file handler isn't fully set up
        # The file log should only contain WARNING and ERROR.
        # Check console output for the warning about default log settings.
        # The print statement in main_backtest.py:
        # print(f"Warning: Logging configuration missing or incomplete in config.json. ...")
        self.assertIn("Warning: Logging configuration missing or incomplete", self.mock_stdout.getvalue())

        # Check file log content for WARNING level
        # The log file path is now the one derived inside main_backtest if "log_file_path" is missing
        # This is "trading_system.log" in the CWD. This makes testing hard.
        # For now, let's assume the test's default config log path is somehow used or skip file check for WARNING.

        # To make this testable:
        # 1. main_backtest.py should use the log_file_path from config even if only log_level is there.
        # My code for main_backtest.py:
        # log_file_path = logging_config.get('log_file_path', default_log_path)
        # This is correct. So if log_file_path key is deleted, it uses default_log_path = "trading_system.log"
        # This means the test log will be in CWD. This is bad for test hygiene.
        # For this sub-part, we are only checking the console warning.
        # Proper file content check for WARNING level is done below.

        # --- Test WARNING Log Level (File Content) ---
        if os.path.exists(log_file_path): os.remove(log_file_path) # Clean up from DEBUG run

        warning_config = self.default_config_data.copy()
        warning_config["logging"]["log_level"] = "WARNING"
        warning_config["logging"]["log_file_path"] = os.path.join(self.test_dir, "warning_test.log")
        warning_config["emergency_stop"] = True # To ensure a WARNING message is logged
        self._write_config(warning_config)
        mock_load_config_main.return_value = warning_config

        main_backtest.main()

        warning_log_file_path = warning_config["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(warning_log_file_path))
        with open(warning_log_file_path, 'r') as f:
            log_content_warning = f.read()

        self.assertNotIn("Test DEBUG message: main_backtest main_logger initialized.", log_content_warning)
        self.assertNotIn("Configuration loaded:", log_content_warning) # INFO message
        self.assertIn("EMERGENCY STOP ACTIVATED", log_content_warning) # WARNING message
        self.assertRegex(log_content_warning, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - WARNING - main_backtest - EMERGENCY STOP ACTIVATED")

    def test_console_warning_for_default_logging_config(self):
        # Test the print warning if logging config is incomplete
        config_missing_logging_keys = self.default_config_data.copy()
        # Example: remove log_level, keeping log_file_path to make the file predictable for cleanup
        # but still triggering the "incomplete" warning.
        del config_missing_logging_keys["logging"]["log_level"]
        # Path where main_backtest will write if log_file_path is also missing (for cleanup)
        # default_main_log_path = "trading_system.log" # CWD

        self._write_config(config_missing_logging_keys)

        # Patch load_config to return this modified config
        # We don't need to mock other functions as main() might exit early or just setup logging.
        with patch('main_backtest.config_loader.load_config', return_value=config_missing_logging_keys):
            # We expect main to run far enough to setup logging and print the warning.
            # It might error out later if other parts of config are not set up for a full run,
            # but the warning should have been printed.
            try:
                main_backtest.main()
            except SystemExit: # Or if main() calls exit()
                pass
            except Exception: # Catch any other exception if main() tries to proceed too far with partial config
                pass

        self.assertIn("Warning: Logging configuration missing or incomplete", self.mock_stdout.getvalue())
        # Clean up default log file if created in CWD by this partial run
        # if os.path.exists(default_main_log_path):
        #     os.remove(default_main_log_path)


    # --- Error Handling Tests ---

    def test_missing_config_file(self):
        # This test needs to check behavior when config_loader.load_config itself fails.
        # main_backtest.py should catch this and print a critical error to console.

        # We simulate load_config raising FileNotFoundError
        # The actual config_loader.load_config('config.json') is called within main_backtest.main()
        # We need to ensure 'config.json' does not exist in the context of main_backtest.main()
        # The easiest way is to patch config_loader.load_config to raise the error.

        with patch('main_backtest.config_loader.load_config', side_effect=FileNotFoundError("Simulated FileNotFoundError for config.json")):
            # We might need to catch SystemExit if main() calls sys.exit()
            try:
                main_backtest.main()
            except SystemExit:
                pass # Expected if main exits upon critical error

        self.assertIn("Critical Error: Required file not found before logger initialization", self.mock_stdout.getvalue())

    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_corrupted_config_file(self, mock_report, mock_kpis, mock_strategy, mock_data_load):
        # Simulate config_loader.load_config raising JSONDecodeError
        with patch('main_backtest.config_loader.load_config', side_effect=json.JSONDecodeError("Simulated JSON error", "doc", 0)):
            try:
                main_backtest.main()
            except SystemExit:
                pass

        self.assertIn("Critical Error: An unexpected error occurred before logger initialization", self.mock_stdout.getvalue())

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_missing_historical_data_file(self, mock_report, mock_kpis, mock_strategy, mock_load_config):
        mock_load_config.return_value = self.default_config_data # Provide a valid config

        # Patch data_loader.load_csv_data to simulate FileNotFoundError
        with patch('main_backtest.data_loader.load_csv_data', side_effect=FileNotFoundError(f"Simulated FileNotFoundError for {self.historical_data_file_path}")):
            try:
                main_backtest.main()
            except SystemExit:
                pass

        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()

        # data_loader.py's logger would have logged the error (via stderr if filelog failed, or filelog if it worked)
        # main_backtest.py would catch the FileNotFoundError and log "Error: Required file not found"
        # We check for main_backtest's log message.
        self.assertIn("main_backtest - Error: Required file not found", log_content)
        self.assertIn("Simulated FileNotFoundError", log_content) # The exception message itself

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.trading_logic.run_strategy')
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_empty_historical_data_file(self, mock_report, mock_kpis, mock_strategy, mock_load_config):
        mock_load_config.return_value = self.default_config_data

        # Patch data_loader.load_csv_data to simulate EmptyDataError
        # pd.errors.EmptyDataError inherits from Exception, not specific enough for some setups.
        # Let's use a custom exception that inherits from pd.errors.EmptyDataError if pandas is fully mocked,
        # or just ensure the behavior of returning an empty DataFrame is handled.
        # The current data_loader.py re-raises pd.errors.EmptyDataError.
        with patch('main_backtest.data_loader.load_csv_data', side_effect=pd.errors.EmptyDataError("Simulated EmptyDataError")):
            try:
                main_backtest.main()
            except SystemExit: # main_backtest calls return, not sys.exit for this case.
                pass # This might not be hit if main just returns.
            except pd.errors.EmptyDataError: # Should be caught by main_backtest's general Exception handler
                pass


        log_file_path = self.default_config_data["logging"]["log_file_path"]
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()

        # data_loader.py logs "Data file is empty"
        # main_backtest.py catches the EmptyDataError via general Exception handler and logs it.
        # The specific message "Error: Historical data file could not be loaded or is empty. Exiting."
        # is for when load_csv_data *returns* an empty df, not when it raises EmptyDataError.
        # So we check for the exception log.
        self.assertIn("main_backtest - An unexpected error occurred during the backtest process", log_content)
        self.assertIn("Simulated EmptyDataError", log_content)

    @patch('main_backtest.config_loader.load_config')
    @patch('main_backtest.data_loader.load_csv_data')
    @patch('main_backtest.trading_logic.calculate_position_size') # Target for mocking
    @patch('main_backtest.performance_analyzer.calculate_all_kpis')
    @patch('main_backtest.performance_analyzer.generate_text_report')
    def test_trading_logic_value_error_propagation(self, mock_report, mock_kpis, mock_calc_pos_size, mock_load_data, mock_load_config):
        # Setup: Valid config
        mock_load_config.return_value = self.default_config_data

        # Setup mock_load_data to return a valid DataFrame
        dummy_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2023-01-{:02d}'.format(i+1) for i in range(50)]), # Match _create_dummy_historical_data
            'Open': [1.1000 + i*0.001 for i in range(50)],
            'High': [1.1050 + i*0.001 for i in range(50)],
            'Low': [1.0950 + i*0.001 for i in range(50)],
            'Close': [1.1020 + i*0.001 for i in range(50)],
            'Volume': [1000 + i*10 for i in range(50)]
        })
        mock_load_data.return_value = dummy_df

        # Configure the mock for calculate_position_size to raise ValueError
        mock_calc_pos_size.side_effect = ValueError("Simulated ValueError from calculate_position_size")

        # Mocks for functions called after run_strategy, to prevent them from running
        mock_kpis.return_value = {"total_return": 0.0} # Must return a dict
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

        # main_backtest.py's general "except Exception as e:" block should catch this.
        # It logs: main_logger.exception(f"An unexpected error occurred during the backtest process: {e}")
        self.assertIn("main_backtest - An unexpected error occurred during the backtest process", log_content)
        self.assertIn("Simulated ValueError from calculate_position_size", log_content)

    # --- Emergency Stop Tests ---

    def _run_main_for_emergency_stop_test(self, config_overrides):
        """
        Helper function to run main_backtest.main() with a custom config
        for emergency stop testing.
        It mocks parts of the pipeline to focus on trade generation.
        Returns the trade_log from backtest_results.
        """
        test_config = self.default_config_data.copy()
        test_config.update(config_overrides)
        if "logging" not in test_config: # Ensure logging section exists for path
            test_config["logging"] = self.default_config_data["logging"].copy()
        test_config["logging"]["log_file_path"] = os.path.join(self.test_dir, "emergency_stop_test.log")
        self._write_config(test_config)

        # Mock config loader to return our specific config
        with patch('main_backtest.config_loader.load_config', return_value=test_config) as mock_cfg_load, \
             patch('main_backtest.data_loader.load_csv_data') as mock_data_load, \
             patch('main_backtest.performance_analyzer.calculate_all_kpis') as mock_kpis, \
             patch('main_backtest.performance_analyzer.generate_text_report') as mock_report:

            # Provide data that should generate trades if not stopped
            # Data needs to be long enough for Donchian channels to form (e.g. > 20 periods for entry)
            self._create_dummy_historical_data(self.historical_data_file_path, rows=50)
            dummy_df = pd.read_csv(self.historical_data_file_path, parse_dates=['Timestamp'])
            dummy_df.set_index('Timestamp', inplace=True)
            mock_data_load.return_value = dummy_df

            # Let run_strategy execute, but mock KPI/report
            mock_kpis.return_value = {"total_return": 0.0}
            mock_report.return_value = None

            # Capture results from run_strategy by patching it or modifying main
            # For simplicity, let's patch run_strategy to store its result for inspection
            # However, the goal is to test main_backtest.main()'s integration of emergency stop
            # So, we run main and then inspect the results if main_backtest is modified to return them
            # Or, if main_backtest saves them, load from there.
            # For now, assume main_backtest.main might not directly return results.
            # We will rely on side effects (e.g. trade log being part of results passed to KPI calc)

            # To get trade_log, we need to capture the 'backtest_results' variable in main_backtest.main
            # One way is to patch 'performance_analyzer.calculate_all_kpis' and inspect its first argument.

            # Simplified: We'll let main run. If it produces a report, that's a side effect.
            # The most direct test for "no new trades" is if the trade_log is empty.
            # To access trade_log, we need to modify main_backtest.main to return it,
            # or patch run_strategy and check what it was called with / what it would do.

            # Let's assume run_strategy is the source of truth for the trade_log.
            # We can patch trading_logic.run_strategy to capture its actual result.

            # This is tricky. The call to run_strategy is inside main_backtest.
            # If we patch trading_logic.run_strategy, the one imported by main_backtest is patched.

            # Store the actual run_strategy to call it, and capture its result.
            # This is getting complicated. Let's simplify the test's focus.
            # The core logic is: if emergency_stop: true, section 2.3 in run_strategy is skipped.
            # This means no new orders of type "entry" should be in the trade_log.

            # We need to get the backtest_results.
            # Let's patch `performance_analyzer.calculate_all_kpis` and grab `backtest_results` from its call.

            global_results_store = {} # Simple way to get results out
            def capture_results_for_kpi(backtest_res, cfg, risk_free):
                global_results_store['backtest_results'] = backtest_res
                return {"total_return": 0.0} # Mocked KPI result

            mock_kpis.side_effect = capture_results_for_kpi

            main_backtest.main()
            return global_results_store.get('backtest_results', {}).get('trade_log', [])

    def test_emergency_stop_true_no_new_trades(self):
        trade_log = self._run_main_for_emergency_stop_test({"emergency_stop": True})

        # Check that the log file indicates emergency stop was active
        log_file_path = os.path.join(self.test_dir, "emergency_stop_test.log")
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("EMERGENCY STOP ACTIVATED: New trade entries will be disabled.", log_content)

        # Check that no new entry trades were made
        entry_trades = [trade for trade in trade_log if trade.get("type") == "entry"]
        self.assertEqual(len(entry_trades), 0, "No new entry trades should be made when emergency stop is active.")

    def test_emergency_stop_false_allows_trades(self):
        trade_log = self._run_main_for_emergency_stop_test({"emergency_stop": False})

        # Check that the log file indicates emergency stop was not active
        log_file_path = os.path.join(self.test_dir, "emergency_stop_test.log")
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("Emergency stop is not activated. System operating normally.", log_content)

        # Check that entry trades *could* be made (if signals generated).
        # The dummy data is designed to be simple and might not generate complex signals.
        # For this test, we're checking that the mechanism *allows* trades.
        # If the dummy data reliably produces trades, we can assert len(entry_trades) > 0.
        # For now, just assert that the log does not say "EMERGENCY STOP ACTIVATED".
        # A more robust check would be to ensure some trades if data is guaranteed to produce them.
        # Given our dummy data and simple strategy, it should produce entries.
        entry_trades = [trade for trade in trade_log if trade.get("type") == "entry"]
        self.assertTrue(len(entry_trades) > 0, "Entry trades should be allowed and generated with this data when emergency stop is false.")


if __name__ == '__main__':
    # This allows running the tests directly from this file
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

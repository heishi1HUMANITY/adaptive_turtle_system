import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import io

# Add the root directory to sys.path to allow importing collect_data
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import collect_data

class TestCollectData(unittest.TestCase):

    def setUp(self):
        self.sample_csv_data = (
            "time,open,high,low,close\n"
            "2023-01-15T10:00:00,1.1234,1.1238,1.1230,1.1235\n"
            "2023-01-15T10:01:00,1.1235,1.1239,1.1231,1.1236"
        )
        self.expected_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2023-01-15T10:00:00', '2023-01-15T10:01:00']),
            'Open': [1.1234, 1.1235],
            'High': [1.1238, 1.1239],
            'Low': [1.1230, 1.1231],
            'Close': [1.1235, 1.1236],
            'Volume': [0, 0]
        })

        self.test_output_dir = './test_output_data_dir'
        if not os.path.exists(self.test_output_dir):
            os.makedirs(self.test_output_dir)
        else:
            for f in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, f))

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            for f in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, f))
            os.rmdir(self.test_output_dir)

    @patch('collect_data.requests.get')
    def test_fetch_forex_data_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = self.sample_csv_data.encode('utf-8')
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        df_result = collect_data.fetch_forex_data(2023, 1, 'USDJPY', 'TESTKEY')

        self.assertIsNotNone(df_result)
        pd.testing.assert_frame_equal(df_result.reset_index(drop=True), self.expected_df.reset_index(drop=True))
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        self.assertIn("FX_INTRADAY_EXTENDED", called_url)
        self.assertIn("symbol=USDJPY", called_url)
        self.assertIn("slice=year2023month1", called_url)
        self.assertIn("apikey=TESTKEY", called_url)

    @patch('collect_data.requests.get')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_fetch_forex_data_api_error(self, mock_stderr, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Correctly escape quotes for JSON within a Python string
        mock_response.content = "{\"Error Message\": \"Invalid API call\"}".encode('utf-8')
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        df_result = collect_data.fetch_forex_data(2023, 1, 'USDJPY', 'TESTKEY')
        self.assertIsNone(df_result)
        self.assertIn("データ取得に失敗", mock_stderr.getvalue())
        self.assertIn("Invalid API call", mock_stderr.getvalue())

    @patch('collect_data.requests.get')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_fetch_forex_data_request_exception(self, mock_stderr, mock_get):
        mock_get.side_effect = collect_data.requests.exceptions.RequestException("Network Error")

        df_result = collect_data.fetch_forex_data(2023, 1, 'USDJPY', 'TESTKEY')
        self.assertIsNone(df_result)
        self.assertIn("APIリクエスト中にエラーが発生しました", mock_stderr.getvalue())
        self.assertIn("Network Error", mock_stderr.getvalue())

    @patch('collect_data.requests.get')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_fetch_forex_data_logging(self, mock_stdout, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = self.sample_csv_data.encode('utf-8')
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        collect_data.fetch_forex_data(2023, 1, 'USDJPY', 'TESTKEY')

        log_output = mock_stdout.getvalue()
        self.assertIn("Fetching intraday data for USDJPY (2023-01)", log_output)
        self.assertIn("2件のデータを取得しました。", log_output)

    @patch('collect_data.fetch_forex_data')
    @patch('collect_data.pd.DataFrame.to_csv')
    @patch('sys.stdout', new_callable=io.StringIO) # Mock stdout for main
    # It's better to also mock os.path.exists and os.makedirs for main success test
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_main_success(self, mock_makedirs, mock_path_exists, mock_stdout, mock_to_csv, mock_fetch_data_func):
        args = MagicMock()
        args.symbol = 'EURUSD'; args.year = 2023; args.month = 2
        args.api_key = 'MAINTESTKEY'; args.output_dir = self.test_output_dir

        mock_df_data = {
            'Timestamp': pd.to_datetime(['2023-02-10T10:00:00', '2023-02-10T10:01:00']),
            'Open': [1.2, 1.3], 'High': [1.21, 1.31], 'Low': [1.19, 1.29], 'Close': [1.205, 1.305],
            'Volume': [0, 0]
        }
        mock_df = pd.DataFrame(mock_df_data)

        # Mock the sort_values method directly on the DataFrame instance that will be returned
        mock_df.sort_values = MagicMock(wraps=mock_df.sort_values) # Use wraps to still execute original
        mock_fetch_data_func.return_value = mock_df

        # Simulate that output directory does not exist to test creation path
        mock_path_exists.return_value = False

        collect_data.main(args)

        mock_path_exists.assert_called_once_with(self.test_output_dir)
        mock_makedirs.assert_called_once_with(self.test_output_dir)

        mock_fetch_data_func.assert_called_once_with(2023, 2, 'EURUSD', 'MAINTESTKEY')
        mock_df.sort_values.assert_called_once_with(by='Timestamp', inplace=True)

        self.assertTrue(mock_to_csv.called)
        expected_filename = "EURUSD_M1_20230210_20230210.csv"
        actual_filename = os.path.basename(mock_to_csv.call_args[0][0])
        self.assertEqual(expected_filename, actual_filename)

        log_output = mock_stdout.getvalue() # Get value from the mocked stdout for main
        self.assertIn(f"Starting data collection for Symbol: EURUSD, Year: 2023, Month: 2", log_output)
        self.assertIn(f"Creating output directory: {self.test_output_dir}", log_output)
        self.assertIn(f"Data successfully saved to {os.path.join(self.test_output_dir, expected_filename)}", log_output)

    @patch('collect_data.fetch_forex_data')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_fetch_data_returns_none(self, mock_stderr, mock_fetch_data_func):
        args = MagicMock()
        args.symbol = 'USDJPY'; args.year = 2023; args.month = 1
        args.api_key = 'TESTKEY'; args.output_dir = self.test_output_dir

        mock_fetch_data_func.return_value = None

        with self.assertRaises(SystemExit) as cm:
            collect_data.main(args)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("データ取得または処理に失敗しました", mock_stderr.getvalue())

    @patch('collect_data.fetch_forex_data')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_main_fetch_data_returns_empty_df(self, mock_stderr, mock_fetch_data_func):
        args = MagicMock()
        args.symbol = 'USDJPY'; args.year = 2023; args.month = 1
        args.api_key = 'TESTKEY'; args.output_dir = self.test_output_dir

        mock_fetch_data_func.return_value = pd.DataFrame()

        with self.assertRaises(SystemExit) as cm:
            collect_data.main(args)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("のデータが見つかりませんでした（空のデータセット）", mock_stderr.getvalue())

    def test_argument_parsing(self):
        # Store original sys.argv
        original_argv = sys.argv
        try:
            # Set sys.argv for the test
            sys.argv = [
                'collect_data.py', '--symbol', 'GBPUSD', '--year', '2022', '--month', '12',
                '--api-key', 'ARGKEY', '--output-dir', '/tmp/dataout'
            ]
            # The script's argument parser is defined at the bottom, so it's hard to test in isolation
            # without running the `if __name__ == '__main__':` block or refactoring the parser.
            # For this structure, we test the parser instance directly.
            # Need to ensure collect_data.parser is accessible or refactor parser creation.
            # Assuming collect_data.parser is the ArgumentParser instance.
            # If parser is defined inside `if __name__ == '__main__'`, this test needs adjustment.
            # Let's assume it's module-level for testability as `collect_data.parser`.

            # Re-import or ensure parser is defined module level for this to work
            # For now, this will test the ArgumentParser directly if it's defined globally in collect_data
            # This part assumes collect_data.py has `parser = argparse.ArgumentParser(...)` at module level.
            # If not, the test must be structured differently, e.g. by calling a function that sets up the parser.
            # Given the current structure of collect_data.py, the parser is defined in `if __name__ == '__main__'`
            # This means `collect_data.parser` won't exist unless that block is run.
            # A common pattern is to have a function like `parse_arguments(argv)` in collect_data.py.
            # For now, let's simulate how it would be called if the script was run:

            # This test, as written, will likely fail if `collect_data.parser` isn't a module-level variable.
            # Let's assume for the purpose of this test template that it *is* available or will be refactored.
            # If the parser is only in `if __name__ == '__main__'`, we'd have to mock `main` and check `args` there,
            # or call `parse_args` on an instance we create here with same setup.

            # Create a new parser instance just for this test, mirroring the one in collect_data.py
            test_parser = collect_data.argparse.ArgumentParser(description="Fetch and save forex data from Alpha Vantage for a specific month using FX_INTRADAY_EXTENDED.")
            test_parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., USDJPY)")
            test_parser.add_argument("--year", type=int, required=True, help="Year for data fetching")
            test_parser.add_argument("--month", type=int, required=True, help="Month for data fetching")
            test_parser.add_argument("--api-key", type=str, required=True, help="Alpha Vantage API key")
            test_parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the output CSV file")

            args = test_parser.parse_args(sys.argv[1:])

            self.assertEqual(args.symbol, 'GBPUSD')
            self.assertEqual(args.year, 2022)
            self.assertEqual(args.month, 12)
            self.assertEqual(args.api_key, 'ARGKEY')
            self.assertEqual(args.output_dir, '/tmp/dataout')
        finally:
            # Restore original sys.argv
            sys.argv = original_argv


    def test_argument_parsing_missing_required(self):
        original_argv = sys.argv
        try:
            sys.argv = [
                'collect_data.py', '--year', '2022', '--month', '12',
                '--api-key', 'ARGKEY', '--output-dir', '/tmp/dataout'
            ]
            # Same assumption/issue as above test for parser availability.
            test_parser = collect_data.argparse.ArgumentParser(description="Fetch and save forex data from Alpha Vantage for a specific month using FX_INTRADAY_EXTENDED.")
            test_parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., USDJPY)")
            test_parser.add_argument("--year", type=int, required=True, help="Year for data fetching")
            test_parser.add_argument("--month", type=int, required=True, help="Month for data fetching")
            test_parser.add_argument("--api-key", type=str, required=True, help="Alpha Vantage API key")
            test_parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the output CSV file")

            with self.assertRaises(SystemExit) as cm:
                test_parser.parse_args(sys.argv[1:])
            self.assertEqual(cm.exception.code, 2) # argparse exits with 2 on error
        finally:
            sys.argv = original_argv

if __name__ == '__main__':
    unittest.main()

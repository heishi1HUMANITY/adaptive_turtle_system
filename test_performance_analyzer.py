import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import os
import math

# Assuming performance_analyzer.py is in the same directory or PYTHONPATH
from performance_analyzer import (
    calculate_total_net_profit, calculate_profit_factor,
    calculate_max_drawdown, calculate_sharpe_ratio,
    calculate_trade_statistics, calculate_all_kpis, generate_text_report
)

class TestPerformanceAnalyzer(unittest.TestCase):
    def setUp(self):
        """Setup common data for tests."""
        self.dummy_config = {
            'initial_capital': 100000.0,
            'markets': ['EUR/USD', 'GBP/USD'],
            'entry_donchian_period': 20,
            'take_profit_long_exit_period': 10,
            'take_profit_short_exit_period': 10,
            'atr_period': 14, # Used for SL calc in strategy, good to have in config for report
            'stop_loss_atr_multiplier': 2.0,
            'risk_per_trade': 0.01, # 1%
            'total_portfolio_risk_limit': 0.05, # 5%
            'slippage_pips': 0.2,
            'commission_per_lot': 5.0,
            'account_currency': 'USD',
            'risk_free_rate_annual': 0.01 # For Sharpe Ratio testing
        }

        self.timestamps = [
            datetime(2023,1,1,0,0,0), datetime(2023,1,1,1,0,0),
            datetime(2023,1,1,2,0,0), datetime(2023,1,1,3,0,0),
            datetime(2023,1,1,4,0,0)
        ]
        self.equity_values = [100000.0, 101000.0, 100500.0, 102000.0, 101500.0]
        self.dummy_equity_curve = list(zip(self.timestamps, self.equity_values))

        self.dummy_trade_log = [
            {'realized_pnl': 1000.0, 'type': 'exit', 'symbol': 'EUR/USD'},
            {'realized_pnl': -500.0, 'type': 'exit', 'symbol': 'EUR/USD'},
            {'realized_pnl': 200.0, 'type': 'reduction', 'symbol': 'GBP/USD'}, # Reduction is a valid trade type
            {'realized_pnl': 0.0, 'type': 'exit', 'symbol': 'EUR/USD'},
            {'realized_pnl': 100.0, 'type': 'entry', 'symbol': 'EUR/USD'} # Should be ignored by trade_statistics
        ]

        self.dummy_backtest_results = {
            'equity_curve': self.dummy_equity_curve,
            'trade_log': self.dummy_trade_log,
            'portfolio_summary': { # This structure is expected by calculate_all_kpis
                'initial_capital': self.dummy_config['initial_capital'],
                'final_equity': self.equity_values[-1],
                'total_trades': 3 # Example: may differ from what calculate_trade_statistics counts
            },
            'final_capital': self.equity_values[-1] # Cash, might differ from equity
        }
        self.report_path = 'test_generated_report.txt'

    def tearDown(self):
        """Clean up generated files after tests."""
        if os.path.exists(self.report_path):
            os.remove(self.report_path)

    # 1. Test calculate_total_net_profit
    def test_calculate_total_net_profit(self):
        self.assertEqual(calculate_total_net_profit(100000, 110000), 10000)
        self.assertEqual(calculate_total_net_profit(100000, 90000), -10000)
        self.assertEqual(calculate_total_net_profit(100000, 100000), 0)

    # 2. Test calculate_profit_factor
    def test_calculate_profit_factor(self):
        log_profit_loss = [{'type': 'exit', 'realized_pnl': 100}, {'type': 'exit', 'realized_pnl': -50}]
        self.assertAlmostEqual(calculate_profit_factor(log_profit_loss), 2.0)

        log_profit_only = [{'type': 'exit', 'realized_pnl': 100}, {'type': 'exit', 'realized_pnl': 50}]
        self.assertEqual(calculate_profit_factor(log_profit_only), float('inf'))

        log_loss_only = [{'type': 'exit', 'realized_pnl': -100}, {'type': 'exit', 'realized_pnl': -50}]
        self.assertEqual(calculate_profit_factor(log_loss_only), 0.0)

        log_no_pnl_trades = [{'type': 'entry', 'realized_pnl': 100}] # Entry trades ignored
        self.assertEqual(calculate_profit_factor(log_no_pnl_trades), 0.0)

        log_empty = []
        self.assertEqual(calculate_profit_factor(log_empty), 0.0)

        log_zero_pnl_exit = [{'type': 'exit', 'realized_pnl': 0.0}]
        self.assertEqual(calculate_profit_factor(log_zero_pnl_exit), 0.0)

        log_profit_and_zero_loss = [{'type': 'exit', 'realized_pnl': 100.0}, {'type': 'exit', 'realized_pnl': 0.0}]
        self.assertEqual(calculate_profit_factor(log_profit_and_zero_loss), float('inf'))


    # 3. Test calculate_max_drawdown
    def test_calculate_max_drawdown(self):
        # MDD: Peak 102000, Trough 100500. Abs MDD = 1500. Pct MDD = 1500/102000
        pct_mdd, abs_mdd = calculate_max_drawdown(self.dummy_equity_curve)
        self.assertAlmostEqual(abs_mdd, 1500.0)
        self.assertAlmostEqual(pct_mdd, 1500.0 / 102000.0)

        always_increasing = list(zip(self.timestamps, [100, 110, 120, 130]))
        self.assertEqual(calculate_max_drawdown(always_increasing), (0.0, 0.0))

        # Peak 100, Trough 70. Abs MDD = 30. Pct MDD = 30/100 = 0.3
        always_decreasing = list(zip(self.timestamps, [100, 90, 80, 70]))
        pct_mdd_dec, abs_mdd_dec = calculate_max_drawdown(always_decreasing)
        self.assertAlmostEqual(abs_mdd_dec, 30.0)
        self.assertAlmostEqual(pct_mdd_dec, 0.3)

        flat_curve = list(zip(self.timestamps, [100, 100, 100, 100]))
        self.assertEqual(calculate_max_drawdown(flat_curve), (0.0, 0.0))

        self.assertEqual(calculate_max_drawdown([]), (0.0, 0.0))
        self.assertEqual(calculate_max_drawdown([self.dummy_equity_curve[0]]), (0.0, 0.0))

    # 4. Test calculate_sharpe_ratio
    def test_calculate_sharpe_ratio(self):
        # For self.dummy_equity_curve: [100000, 101000, 100500, 102000, 101500]
        # Returns: 0.01, -0.0049505, 0.01492537, -0.00490196
        # Mean daily return: approx 0.003768
        # Std dev daily returns: approx 0.009148
        # Daily RFR (0.01 annual): (1+0.01)**(1/252)-1 = approx 0.0000395
        # Sharpe = (0.003768 - 0.0000395) / 0.009148 * sqrt(252) = approx 6.49
        # Note: Exact values depend on float precision.
        sharpe = calculate_sharpe_ratio(self.dummy_equity_curve, risk_free_rate_annual=0.01)
        # This is a complex calculation, so we check for a plausible range or specific known good value
        # For this dummy data, let's calculate expected more precisely:
        returns = pd.Series(self.equity_values).pct_change().dropna()
        mean_ret = returns.mean()
        std_ret = returns.std()
        daily_rfr = (1 + 0.01)**(1/252) - 1
        expected_sharpe = (mean_ret - daily_rfr) / std_ret * math.sqrt(252)
        self.assertAlmostEqual(sharpe, expected_sharpe)

        sharpe_no_rfr = calculate_sharpe_ratio(self.dummy_equity_curve, risk_free_rate_annual=0.0)
        expected_sharpe_no_rfr = mean_ret / std_ret * math.sqrt(252)
        self.assertAlmostEqual(sharpe_no_rfr, expected_sharpe_no_rfr)

        flat_curve = list(zip(self.timestamps, [100, 100, 100, 100]))
        self.assertEqual(calculate_sharpe_ratio(flat_curve), 0.0) # Std dev is 0

        self.assertEqual(calculate_sharpe_ratio([]), 0.0)
        self.assertEqual(calculate_sharpe_ratio([self.dummy_equity_curve[0]]), 0.0)

    # 5. Test calculate_trade_statistics
    def test_calculate_trade_statistics(self):
        stats = calculate_trade_statistics(self.dummy_trade_log)
        self.assertEqual(stats['total_trades'], 3) # 1 entry ignored, 1 zero pnl is breakeven
        self.assertEqual(stats['winning_trades'], 2) # 1000, 200
        self.assertEqual(stats['losing_trades'], 1) # -500
        self.assertEqual(stats['breakeven_trades'], 1) # 0 PnL exit
        self.assertAlmostEqual(stats['win_rate'], 2 / (2 + 1)) # 2 wins / (2 wins + 1 loss)
        self.assertAlmostEqual(stats['average_win_amount'], (1000 + 200) / 2)
        self.assertAlmostEqual(stats['average_loss_amount'], 500) # abs value
        self.assertAlmostEqual(stats['gross_profit'], 1200)
        self.assertAlmostEqual(stats['gross_loss'], 500)

        empty_stats = calculate_trade_statistics([])
        for key in stats.keys(): # Check all keys are present
            self.assertIn(key, empty_stats)
        self.assertEqual(empty_stats['total_trades'], 0)

        win_only_log = [{'type': 'exit', 'realized_pnl': 100}, {'type': 'exit', 'realized_pnl': 50}]
        win_stats = calculate_trade_statistics(win_only_log)
        self.assertEqual(win_stats['winning_trades'], 2)
        self.assertEqual(win_stats['losing_trades'], 0)
        self.assertEqual(win_stats['win_rate'], 1.0)

        loss_only_log = [{'type': 'exit', 'realized_pnl': -100}, {'type': 'exit', 'realized_pnl': -50}]
        loss_stats = calculate_trade_statistics(loss_only_log)
        self.assertEqual(loss_stats['winning_trades'], 0)
        self.assertEqual(loss_stats['losing_trades'], 2)
        self.assertEqual(loss_stats['win_rate'], 0.0)

        breakeven_only_log = [{'type': 'exit', 'realized_pnl': 0.0}]
        be_stats = calculate_trade_statistics(breakeven_only_log)
        self.assertEqual(be_stats['breakeven_trades'], 1)
        self.assertEqual(be_stats['win_rate'], 0.0) # No wins or losses

    # 6. Test calculate_all_kpis
    def test_calculate_all_kpis(self):
        kpis = calculate_all_kpis(self.dummy_backtest_results, self.dummy_config,
                                  risk_free_rate_annual=self.dummy_config['risk_free_rate_annual'])

        expected_keys = [
            "Initial Capital", "Final Equity", "Total Net Profit", "Gross Profit", "Gross Loss",
            "Profit Factor", "Max Drawdown (%)", "Max Drawdown (Absolute)", "Sharpe Ratio",
            "Total Trades", "Winning Trades", "Losing Trades", "Breakeven Trades",
            "Win Rate (%)", "Average Win Amount", "Average Loss Amount"
        ]
        for key in expected_keys:
            self.assertIn(key, kpis)

        self.assertAlmostEqual(kpis['Initial Capital'], self.dummy_config['initial_capital'])
        self.assertAlmostEqual(kpis['Final Equity'], self.equity_values[-1])
        self.assertAlmostEqual(kpis['Total Net Profit'], self.equity_values[-1] - self.dummy_config['initial_capital'])

        # Compare with direct calculation for a few KPIs
        expected_mdd_pct, expected_mdd_abs = calculate_max_drawdown(self.dummy_equity_curve)
        self.assertAlmostEqual(kpis['Max Drawdown (Absolute)'], expected_mdd_abs)
        self.assertAlmostEqual(kpis['Max Drawdown (%)'], expected_mdd_pct * 100)

        trade_stats_direct = calculate_trade_statistics(self.dummy_trade_log)
        self.assertEqual(kpis['Total Trades'], trade_stats_direct['total_trades'])
        self.assertAlmostEqual(kpis['Win Rate (%)'], trade_stats_direct['win_rate'] * 100)

    # 7. Test generate_text_report
    def test_generate_text_report(self):
        kpis = calculate_all_kpis(self.dummy_backtest_results, self.dummy_config,
                                  risk_free_rate_annual=self.dummy_config['risk_free_rate_annual'])
        generate_text_report(self.dummy_backtest_results, self.dummy_config, kpis, self.report_path)

        self.assertTrue(os.path.exists(self.report_path))

        with open(self.report_path, 'r') as f:
            content = f.read()

        self.assertIn("BACKTEST PERFORMANCE REPORT", content)
        self.assertIn("BACKTEST PARAMETERS", content)
        self.assertIn("PERFORMANCE SUMMARY", content)

        self.assertIn(f"Initial Capital: {self.dummy_config['initial_capital']:,.2f}", content)
        self.assertIn(f"Markets Traded: {', '.join(self.dummy_config['markets'])}", content)
        start_date_str = self.timestamps[0].strftime('%Y-%m-%d %H:%M:%S') # Default datetime str format
        self.assertIn(start_date_str, content)

        for kpi_name in kpis.keys():
            self.assertIn(kpi_name, content)

        # Check formatting for a percentage and a monetary value
        self.assertRegex(content, r"Win Rate \(%\): [\d\.]+%")
        self.assertRegex(content, r"Total Net Profit: [\d,\.\-]+") # Allows for negative profit

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

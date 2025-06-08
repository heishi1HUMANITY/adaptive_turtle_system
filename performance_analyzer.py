import math
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any

def calculate_total_net_profit(initial_capital: float, final_equity: float) -> float:
    """Calculates the total net profit of the trading strategy.

    Args:
        initial_capital (float): The starting capital.
        final_equity (float): The final equity after trading.

    Returns:
        float: The total net profit (final_equity - initial_capital).
    """
    return final_equity - initial_capital

def calculate_profit_factor(trade_log: List[Dict[str, Any]]) -> float:
    """Calculates the profit factor from a list of trades.

    Profit Factor = Gross Profit / Gross Loss.
    Gross Profit is the sum of PnL from all winning trades.
    Gross Loss is the absolute sum of PnL from all losing trades.

    Args:
        trade_log (List[Dict[str, Any]]): A list of trade dictionaries.
            Each dictionary should have a 'realized_pnl' key for closed trades.

    Returns:
        float: The profit factor. Returns 0.0 if there are no losses (to avoid division by zero)
               or if the trade log is empty or contains no PnL.
    """
    gross_profit = 0.0
    gross_loss = 0.0

    if not trade_log:
        return 0.0

    for trade in trade_log:
        pnl = trade.get('realized_pnl', 0.0)
        if pnl > 0:
            gross_profit += pnl
        elif pnl < 0:
            gross_loss += abs(pnl)

    if gross_loss == 0:
        if gross_profit > 0:
            return float('inf') # Infinite profit factor if profit but no loss
        return 0.0  # No profit and no loss, or profit but no loss

    return gross_profit / gross_loss

def calculate_max_drawdown(equity_curve: List[Tuple[Any, float]]) -> Tuple[float, float]:
    """Calculates the maximum drawdown (MDD) from an equity curve.

    MDD is the largest peak-to-trough decline during a specific period.

    Args:
        equity_curve (List[Tuple[Any, float]]): A list of (timestamp, equity) tuples.
            Timestamps can be any type, equity values must be floats.

    Returns:
        Tuple[float, float]: A tuple containing:
            - mdd_percentage (float): Maximum drawdown as a percentage.
            - mdd_absolute (float): Maximum drawdown in absolute monetary value.
            Returns (0.0, 0.0) if the equity curve is empty or has less than 2 points.
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0, 0.0

    peak_equity = equity_curve[0][1]
    max_drawdown_absolute = 0.0
    max_drawdown_percentage = 0.0

    for _, equity in equity_curve:
        if equity > peak_equity:
            peak_equity = equity

        drawdown = peak_equity - equity
        if drawdown > max_drawdown_absolute:
            max_drawdown_absolute = drawdown

        if peak_equity != 0: # Avoid division by zero if peak is zero
            drawdown_percentage_from_current_peak = (drawdown / peak_equity)
            if drawdown_percentage_from_current_peak > max_drawdown_percentage:
                max_drawdown_percentage = drawdown_percentage_from_current_peak

    return max_drawdown_percentage, max_drawdown_absolute

def calculate_sharpe_ratio(equity_curve: List[Tuple[Any, float]], risk_free_rate_annual: float = 0.0) -> float:
    """Calculates the annualized Sharpe Ratio from an equity curve.

    Sharpe Ratio = (mean_daily_return - daily_risk_free_rate) / std_dev_daily_returns * sqrt(252).

    Args:
        equity_curve (List[Tuple[Any, float]]): A list of (timestamp, equity) tuples.
        risk_free_rate_annual (float, optional): The annualized risk-free rate. Defaults to 0.0.

    Returns:
        float: The annualized Sharpe Ratio. Returns 0.0 if there are less than 2 data points
               in the equity curve or if standard deviation of returns is zero.
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    equity_values = pd.Series([item[1] for item in equity_curve])
    daily_returns = equity_values.pct_change().dropna()

    if daily_returns.empty:
        return 0.0

    mean_daily_return = daily_returns.mean()
    std_dev_daily_returns = daily_returns.std()

    if std_dev_daily_returns == 0: # Avoid division by zero if returns are constant
        return 0.0

    # Convert annual risk-free rate to daily
    # (1 + R_annual)^(1/252) - 1
    # If risk_free_rate_annual is 0, daily_risk_free_rate will be 0.
    daily_risk_free_rate = (1 + risk_free_rate_annual)**(1/252) - 1 if risk_free_rate_annual != 0 else 0.0

    sharpe_ratio = (mean_daily_return - daily_risk_free_rate) / std_dev_daily_returns
    annualized_sharpe_ratio = sharpe_ratio * math.sqrt(252) # Annualize

    return annualized_sharpe_ratio

def calculate_trade_statistics(trade_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates various trade statistics from a list of trades.

    Args:
        trade_log (List[Dict[str, Any]]): A list of trade dictionaries.
            Each dictionary should have a 'realized_pnl' key for closed/reduced trades
            and a 'type' key (e.g., 'exit', 'reduction').

    Returns:
        Dict[str, Any]: A dictionary containing trade statistics:
            - total_trades (int)
            - winning_trades (int)
            - losing_trades (int)
            - breakeven_trades (int)
            - win_rate (float)
            - average_win_amount (float)
            - average_loss_amount (float)
            - gross_profit (float)
            - gross_loss (float)
    """
    if not trade_log:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0, "breakeven_trades": 0,
            "win_rate": 0.0, "average_win_amount": 0.0, "average_loss_amount": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0
        }

    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    breakeven_trades = 0
    gross_profit = 0.0
    gross_loss = 0.0
    total_win_pnl = 0.0
    total_loss_pnl = 0.0 # Sum of negative PnLs

    # Consider only trades that are 'exit' or 'reduction' as contributing to closed trade stats
    # Assuming 'entry' trades don't have 'realized_pnl' or it's irrelevant for this summary.
    relevant_trades = [t for t in trade_log if t.get('type') in ['exit', 'reduction'] and 'realized_pnl' in t]

    total_trades = len(relevant_trades)

    for trade in relevant_trades:
        pnl = trade.get('realized_pnl', 0.0)
        if pnl > 0:
            winning_trades += 1
            total_win_pnl += pnl
            gross_profit += pnl
        elif pnl < 0:
            losing_trades += 1
            total_loss_pnl += pnl # This will be negative
            gross_loss += abs(pnl)
        else: # pnl == 0
            breakeven_trades += 1

    win_rate = (winning_trades / (winning_trades + losing_trades)) if (winning_trades + losing_trades) > 0 else 0.0
    average_win_amount = (total_win_pnl / winning_trades) if winning_trades > 0 else 0.0
    average_loss_amount = abs(total_loss_pnl / losing_trades) if losing_trades > 0 else 0.0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "breakeven_trades": breakeven_trades,
        "win_rate": win_rate,
        "average_win_amount": average_win_amount,
        "average_loss_amount": average_loss_amount,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }

if __name__ == '__main__':
    # Example Usage (optional, for quick testing)
    sample_initial_capital = 100000.0
    sample_final_equity = 115000.0
    print(f"Total Net Profit: {calculate_total_net_profit(sample_initial_capital, sample_final_equity)}")

    sample_trade_log = [
        {'order_id': '1', 'symbol': 'EUR/USD', 'type': 'entry', 'realized_pnl': 0}, # Entry
        {'order_id': '2', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 150.0}, # Win
        {'order_id': '3', 'symbol': 'EUR/USD', 'type': 'entry', 'realized_pnl': 0}, # Entry
        {'order_id': '4', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': -50.0}, # Loss
        {'order_id': '5', 'symbol': 'EUR/USD', 'type': 'entry', 'realized_pnl': 0}, # Entry
        {'order_id': '6', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 200.0}, # Win
        {'order_id': '7', 'symbol': 'EUR/USD', 'type': 'entry', 'realized_pnl': 0}, # Entry
        {'order_id': '8', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': -75.0}, # Loss
        {'order_id': '9', 'symbol': 'EUR/USD', 'type': 'entry', 'realized_pnl': 0}, # Entry
        {'order_id': '10', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 0.0} # Breakeven
    ]
    print(f"Profit Factor: {calculate_profit_factor(sample_trade_log)}")
    print(f"Trade Statistics: {calculate_trade_statistics(sample_trade_log)}")

    sample_equity_curve_timestamps = pd.to_datetime([
        '2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
        '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10'
    ])
    sample_equity_curve_values = [
        10000, 10100, 10050, 10200, 10150,  # Peak 10200, Trough 10050 (DD=150 from 10200)
        9900,  9950,  10300, 10250, 10400   # Peak 10300 (DD from this peak to 10250 is 50)
                                            # Overall peak 10400. MDD from 10200 to 9900 (DD=300)
                                            # Or from 10300 to any later trough (none here)
    ]
    # Corrected equity curve for a more illustrative drawdown
    sample_equity_curve_values_dd = [
        10000, 10200, 10100, # Peak 10200
        9800,  # Trough after 10200, Drawdown = 10200 - 9800 = 400
        10300, # New peak
        10000, # Trough after 10300, Drawdown = 10300 - 10000 = 300
        10500, # New peak
        10400, # Drawdown = 10500 - 10400 = 100
        10350, # Drawdown = 10500 - 10350 = 150
        10600  # Final peak
    ] # Expected MDD should be 400 (from 10200 to 9800)

    sample_equity_curve = list(zip(sample_equity_curve_timestamps, sample_equity_curve_values_dd))
    mdd_percent, mdd_abs = calculate_max_drawdown(sample_equity_curve)
    print(f"Max Drawdown: Percentage = {mdd_percent*100:.2f}%, Absolute = {mdd_abs:.2f}")

    sharpe = calculate_sharpe_ratio(sample_equity_curve, risk_free_rate_annual=0.02)
    print(f"Sharpe Ratio (annualized): {sharpe:.2f}")

    # Test with empty/minimal data
    print(f"Profit Factor (empty log): {calculate_profit_factor([])}")
    print(f"Trade Statistics (empty log): {calculate_trade_statistics([])}")
    print(f"Max Drawdown (empty curve): {calculate_max_drawdown([])}")
    print(f"Sharpe Ratio (empty curve): {calculate_sharpe_ratio([])}")
    print(f"Max Drawdown (single point curve): {calculate_max_drawdown([(sample_equity_curve_timestamps[0],10000)])}")
    print(f"Sharpe Ratio (single point curve): {calculate_sharpe_ratio([(sample_equity_curve_timestamps[0],10000)])}")

    # Test profit factor with no losses
    winning_trades_only = [{'realized_pnl': 100}, {'realized_pnl': 50}]
    print(f"Profit Factor (no losses): {calculate_profit_factor(winning_trades_only)}")
    # Test profit factor with no profit no loss
    no_profit_no_loss = [{'realized_pnl': 0}]
    print(f"Profit Factor (no profit no loss): {calculate_profit_factor(no_profit_no_loss)}")


    # Test trade statistics with different scenarios
    stats_no_trades = calculate_trade_statistics([])
    assert stats_no_trades['total_trades'] == 0
    stats_win_only = calculate_trade_statistics([{'type': 'exit', 'realized_pnl': 100}])
    assert stats_win_only['winning_trades'] == 1
    assert stats_win_only['win_rate'] == 1.0
    stats_loss_only = calculate_trade_statistics([{'type': 'exit', 'realized_pnl': -100}])
    assert stats_loss_only['losing_trades'] == 1
    assert stats_loss_only['win_rate'] == 0.0

    # Test Max Drawdown specific cases
    flat_equity = [(pd.Timestamp('2023-01-01'), 10000), (pd.Timestamp('2023-01-02'), 10000)]
    mdd_p, mdd_a = calculate_max_drawdown(flat_equity)
    assert mdd_p == 0.0 and mdd_a == 0.0, "MDD for flat equity should be 0"

    always_increasing_equity = [(pd.Timestamp('2023-01-01'), 10000), (pd.Timestamp('2023-01-02'), 10100)]
    mdd_p, mdd_a = calculate_max_drawdown(always_increasing_equity)
    assert mdd_p == 0.0 and mdd_a == 0.0, "MDD for always increasing equity should be 0"

    # Test Sharpe Ratio specific cases
    sharpe_flat = calculate_sharpe_ratio(flat_equity)
    assert sharpe_flat == 0.0, "Sharpe for flat equity (zero std dev) should be 0"

    print("Basic assertions in __main__ passed.")


# --- New functions to be added ---

def calculate_all_kpis(backtest_results: Dict[str, Any], config: Dict[str, Any], risk_free_rate_annual: float = 0.0) -> Dict[str, Any]:
    """
    Calculates all Key Performance Indicators (KPIs) from backtest results.

    Args:
        backtest_results (Dict[str, Any]): The dictionary returned by run_strategy.
                                           Expected keys: "equity_curve", "trade_log", "portfolio_summary".
        config (Dict[str, Any]): The configuration dictionary for the backtest.
                                 Expected key: "initial_capital".
        risk_free_rate_annual (float, optional): The annualized risk-free rate. Defaults to 0.0.

    Returns:
        Dict[str, Any]: A dictionary where keys are KPI names and values are the calculated KPIs.
    """
    equity_curve = backtest_results.get("equity_curve", [])
    trade_log = backtest_results.get("trade_log", [])
    portfolio_summary = backtest_results.get("portfolio_summary", {})

    initial_capital = portfolio_summary.get('initial_capital', config.get('initial_capital', 0.0))
    # final_equity can be derived from equity_curve or portfolio_summary
    if equity_curve:
        final_equity = equity_curve[-1][1]
    elif 'final_equity' in portfolio_summary:
        final_equity = portfolio_summary.get('final_equity')
    else: # Fallback if equity_curve is empty and final_equity not in summary
        final_equity = initial_capital


    trade_stats = calculate_trade_statistics(trade_log)
    mdd_percentage, mdd_absolute = calculate_max_drawdown(equity_curve)

    kpis = {
        "Initial Capital": initial_capital,
        "Final Equity": final_equity,
        "Total Net Profit": calculate_total_net_profit(initial_capital, final_equity),
        "Gross Profit": trade_stats['gross_profit'],
        "Gross Loss": trade_stats['gross_loss'],
        "Profit Factor": calculate_profit_factor(trade_log), # Uses its own PnL summation logic
        "Max Drawdown (%)": mdd_percentage * 100,
        "Max Drawdown (Absolute)": mdd_absolute,
        "Sharpe Ratio": calculate_sharpe_ratio(equity_curve, risk_free_rate_annual),
        "Total Trades": trade_stats['total_trades'],
        "Winning Trades": trade_stats['winning_trades'],
        "Losing Trades": trade_stats['losing_trades'],
        "Breakeven Trades": trade_stats['breakeven_trades'],
        "Win Rate (%)": trade_stats['win_rate'] * 100,
        "Average Win Amount": trade_stats['average_win_amount'],
        "Average Loss Amount": trade_stats['average_loss_amount'],
    }
    return kpis

def generate_text_report(backtest_results: Dict[str, Any], config: Dict[str, Any], kpi_results: Dict[str, Any], report_path: str) -> None:
    """
    Generates a text-based performance report and saves it to a file.

    Args:
        backtest_results (Dict[str, Any]): Results from run_strategy.
        config (Dict[str, Any]): Configuration dictionary used for the backtest.
        kpi_results (Dict[str, Any]): Dictionary of calculated KPIs from calculate_all_kpis.
        report_path (str): File path to save the generated report.
    """
    try:
        with open(report_path, 'w') as f:
            f.write("="*50 + "\n")
            f.write("BACKTEST PERFORMANCE REPORT\n")
            f.write("="*50 + "\n\n")

            # Section 1: Backtest Parameters
            f.write("-" * 40 + "\n")
            f.write("BACKTEST PARAMETERS\n")
            f.write("-" * 40 + "\n")

            initial_capital = kpi_results.get("Initial Capital", config.get('initial_capital', 'N/A'))
            f.write(f"Initial Capital: {initial_capital:,.2f}\n")

            markets = config.get('markets', [])
            f.write(f"Markets Traded: {', '.join(markets) if markets else 'N/A'}\n")

            equity_curve = backtest_results.get("equity_curve", [])
            if equity_curve:
                start_date = equity_curve[0][0]
                end_date = equity_curve[-1][0]
                # Assuming timestamps are datetime objects or similar that can be str() formatted well
                f.write(f"Data Period: {str(start_date)} to {str(end_date)}\n")
            else:
                f.write("Data Period: N/A\n")

            f.write("\nStrategy Parameters:\n")
            f.write(f"  Entry Donchian Period: {config.get('entry_donchian_period', 'N/A')}\n")
            f.write(f"  Long Exit Donchian Period: {config.get('take_profit_long_exit_period', 'N/A')}\n")
            f.write(f"  Short Exit Donchian Period: {config.get('take_profit_short_exit_period', 'N/A')}\n")
            f.write(f"  ATR Period for Stop-Loss: {config.get('atr_period', 'N/A')}\n") # Assuming 'atr_period' is for SL ATR
            f.write(f"  Stop-Loss ATR Multiplier: {config.get('stop_loss_atr_multiplier', 'N/A')}\n")

            risk_per_trade = config.get('risk_per_trade', 0)
            # Assuming risk_per_trade in config is decimal (e.g., 0.01 for 1%)
            # If it can be whole number (e.g. 1 for 1%), adjustment might be needed here or rely on config structure
            f.write(f"  Risk Per Trade: {risk_per_trade*100:.2f}%\n")

            total_risk_limit = config.get('total_portfolio_risk_limit', 0)
            f.write(f"  Total Portfolio Risk Limit: {total_risk_limit*100:.2f}%\n")

            f.write("\nExecution Parameters:\n")
            f.write(f"  Slippage (pips): {config.get('slippage_pips', 'N/A')}\n")
            f.write(f"  Commission (per lot): {config.get('commission_per_lot', 'N/A')}\n\n")

            # Section 2: Performance Summary
            f.write("-" * 40 + "\n")
            f.write("PERFORMANCE SUMMARY\n")
            f.write("-" * 40 + "\n")
            for key, value in kpi_results.items():
                if isinstance(value, float):
                    if "Rate" in key or "%" in key: # Percentages
                        f.write(f"{key}: {value:.2f}%\n")
                    elif "Amount" in key or "Profit" in key or "Loss" in key or "Equity" in key or "Capital" in key or "Absolute" in key: # Monetary values
                        f.write(f"{key}: {value:,.2f}\n")
                    else: # Ratios or other floats
                        f.write(f"{key}: {value:.4f}\n")
                else: # Integers or other types
                    f.write(f"{key}: {value}\n")
            f.write("\n" + "="*50 + "\n")
            f.write("End of Report\n")
            f.write("="*50 + "\n")

        print(f"Report generated successfully at {report_path}")

    except IOError as e:
        print(f"Error writing report to {report_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during report generation: {e}")


if __name__ == '__main__':
    # Example Usage (optional, for quick testing)
    sample_initial_capital = 100000.0
    sample_final_equity = 115000.0
    print(f"Total Net Profit: {calculate_total_net_profit(sample_initial_capital, sample_final_equity)}")

    sample_trade_log = [
        {'order_id': '1', 'symbol': 'EUR/USD', 'type': 'entry'},
        {'order_id': '2', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 150.0},
        {'order_id': '3', 'symbol': 'EUR/USD', 'type': 'entry'},
        {'order_id': '4', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': -50.0},
        {'order_id': '5', 'symbol': 'EUR/USD', 'type': 'entry'},
        {'order_id': '6', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 200.0},
        {'order_id': '7', 'symbol': 'EUR/USD', 'type': 'entry'},
        {'order_id': '8', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': -75.0},
        {'order_id': '9', 'symbol': 'EUR/USD', 'type': 'entry'},
        {'order_id': '10', 'symbol': 'EUR/USD', 'type': 'exit', 'realized_pnl': 0.0}
    ]
    print(f"Profit Factor: {calculate_profit_factor(sample_trade_log)}")
    pf_stats = calculate_trade_statistics(sample_trade_log)
    print(f"Trade Statistics: {pf_stats}")
    assert pf_stats['total_trades'] == 4
    assert pf_stats['winning_trades'] == 2
    assert pf_stats['losing_trades'] == 2
    assert pf_stats['breakeven_trades'] == 1

    sample_equity_curve_timestamps = pd.to_datetime([
        '2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
        '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10'
    ])
    sample_equity_curve_values_dd = [
        10000, 10200, 10100, 9800, 10300, 10000, 10500, 10400, 10350, 10600
    ]

    sample_equity_curve = list(zip(sample_equity_curve_timestamps, sample_equity_curve_values_dd))
    mdd_percent, mdd_abs = calculate_max_drawdown(sample_equity_curve)
    print(f"Max Drawdown: Percentage = {mdd_percent*100:.2f}%, Absolute = {mdd_abs:.2f}")
    assert abs(mdd_abs - 400) < 1e-9, f"MDD Absolute failed: Expected 400, got {mdd_abs}"
    assert abs(mdd_percent - (400/10200)) < 1e-9, f"MDD Percentage failed: Expected {400/10200}, got {mdd_percent}"

    sharpe = calculate_sharpe_ratio(sample_equity_curve, risk_free_rate_annual=0.02)
    print(f"Sharpe Ratio (annualized): {sharpe:.2f}")

    print(f"Profit Factor (empty log): {calculate_profit_factor([])}")
    print(f"Trade Statistics (empty log): {calculate_trade_statistics([])}")
    print(f"Max Drawdown (empty curve): {calculate_max_drawdown([])}")
    print(f"Sharpe Ratio (empty curve): {calculate_sharpe_ratio([])}")
    single_point_curve = [(sample_equity_curve_timestamps[0],10000)]
    print(f"Max Drawdown (single point curve): {calculate_max_drawdown(single_point_curve)}")
    print(f"Sharpe Ratio (single point curve): {calculate_sharpe_ratio(single_point_curve)}")

    winning_trades_only = [{'type': 'exit', 'realized_pnl': 100}, {'type': 'exit', 'realized_pnl': 50}]
    print(f"Profit Factor (no losses): {calculate_profit_factor(winning_trades_only)}")
    assert calculate_profit_factor(winning_trades_only) == float('inf')

    no_profit_no_loss = [{'type': 'exit', 'realized_pnl': 0.0}]
    print(f"Profit Factor (no profit no loss): {calculate_profit_factor(no_profit_no_loss)}")
    assert calculate_profit_factor(no_profit_no_loss) == 0.0

    loss_only_trades = [{'type': 'exit', 'realized_pnl': -100.0}]
    print(f"Profit Factor (loss only): {calculate_profit_factor(loss_only_trades)}")
    assert calculate_profit_factor(loss_only_trades) == 0.0

    flat_equity = [(pd.Timestamp('2023-01-01'), 10000.0), (pd.Timestamp('2023-01-02'), 10000.0)]
    mdd_p, mdd_a = calculate_max_drawdown(flat_equity)
    assert mdd_p == 0.0 and mdd_a == 0.0, "MDD for flat equity should be 0"

    always_increasing_equity = [(pd.Timestamp('2023-01-01'), 10000.0), (pd.Timestamp('2023-01-02'), 10100.0)]
    mdd_p, mdd_a = calculate_max_drawdown(always_increasing_equity)
    assert mdd_p == 0.0 and mdd_a == 0.0, "MDD for always increasing equity should be 0"

    sharpe_flat = calculate_sharpe_ratio(flat_equity)
    assert sharpe_flat == 0.0, "Sharpe for flat equity (zero std dev) should be 0"

    print("Basic assertions in __main__ passed.")

    # --- Test new functions: calculate_all_kpis and generate_text_report ---
    print("\n--- Testing calculate_all_kpis and generate_text_report ---")
    dummy_config = {
        'initial_capital': sample_initial_capital,
        'markets': ['EUR/USD', 'USD/JPY'],
        'entry_donchian_period': 20,
        'take_profit_long_exit_period': 10,
        'take_profit_short_exit_period': 10,
        'atr_period': 14,
        'stop_loss_atr_multiplier': 2.5,
        'risk_per_trade': 0.01, # 1%
        'total_portfolio_risk_limit': 0.05, # 5%
        'slippage_pips': 1.0,
        'commission_per_lot': 4.0,
    }
    dummy_backtest_results = {
        "equity_curve": sample_equity_curve,
        "trade_log": sample_trade_log,
        "final_capital": sample_equity_curve[-1][1], # Not directly used by calculate_all_kpis if portfolio_summary is present
        "portfolio_summary": {
            "initial_capital": sample_initial_capital,
            "final_equity": sample_equity_curve[-1][1],
            "total_trades": pf_stats['total_trades'], # This might differ from trade_stats internal count
        }
    }

    kpi_results_dict = calculate_all_kpis(dummy_backtest_results, dummy_config, risk_free_rate_annual=0.01)
    print("\nCalculated KPIs:")
    for k, v in kpi_results_dict.items():
        print(f"  {k}: {v}")

    # Verify some KPI results (optional, but good for confidence)
    assert abs(kpi_results_dict['Total Net Profit'] - (sample_equity_curve[-1][1] - sample_initial_capital)) < 1e-9
    assert kpi_results_dict['Total Trades'] == pf_stats['total_trades']
    assert abs(kpi_results_dict['Max Drawdown (%)'] - (mdd_percent * 100)) < 1e-9

    report_file_path = "dummy_backtest_report.txt"
    generate_text_report(dummy_backtest_results, dummy_config, kpi_results_dict, report_file_path)

    # To verify, you would manually check the content of "dummy_backtest_report.txt"
    # For automated testing, you could read the file and assert its content.
    try:
        with open(report_file_path, 'r') as f_report:
            report_content = f_report.read()
            assert "BACKTEST PERFORMANCE REPORT" in report_content
            assert f"Initial Capital: {dummy_config['initial_capital']:,.2f}" in report_content
            assert "Total Net Profit" in report_content
            assert f"Markets Traded: {', '.join(dummy_config['markets'])}" in report_content
        print(f"\nContent of '{report_file_path}' seems okay based on basic checks.")
    except FileNotFoundError:
        print(f"ERROR: Report file '{report_file_path}' was not generated.")

    print("\nExample usage for new functions completed.")

import pandas as pd
import math

def add_position(positions, new_position, capital):
    """Adds a new position and updates capital.

    Args:
        positions (dict): Current open positions.
        new_position (dict): Position to be added.
        capital (float): Available capital.

    Returns:
        tuple: Updated positions and capital.
    """
    if not all(key in new_position for key in ['symbol', 'quantity', 'price']):
        raise ValueError("Missing required keys in new_position: 'symbol', 'quantity', 'price'")

    cost = new_position['quantity'] * new_position['price']

    if capital < cost:
        raise ValueError("Not enough capital to add position.")

    symbol = new_position['symbol']
    if symbol in positions:
        existing_position = positions[symbol]
        total_quantity = existing_position['quantity'] + new_position['quantity']
        if total_quantity == 0: # handles case where new_position is effectively closing out the existing one
            del positions[symbol]
        else:
            existing_position['price'] = (existing_position['price'] * existing_position['quantity'] + \
                                         new_position['price'] * new_position['quantity']) / total_quantity
            existing_position['quantity'] = total_quantity
    else:
        positions[symbol] = new_position.copy() # Use copy to avoid modifying the original new_position dict

    capital -= cost
    return positions, capital

def close_position(positions, position_to_close, capital):
    """Closes an existing position and updates capital.

    Args:
        positions (dict): Current open positions.
        position_to_close (dict): Position to be closed.
        capital (float): Available capital.

    Returns:
        tuple: Updated positions and capital.
    """
    if not all(key in position_to_close for key in ['symbol', 'quantity', 'price']):
        raise ValueError("Missing required keys in position_to_close: 'symbol', 'quantity', 'price'")

    symbol = position_to_close['symbol']
    quantity_to_close = position_to_close['quantity']
    price = position_to_close['price']

    if symbol not in positions:
        raise ValueError(f"Symbol {symbol} not found in positions.")

    existing_position = positions[symbol]

    if quantity_to_close <= 0:
        raise ValueError("Quantity to close must be positive.")

    if quantity_to_close > existing_position['quantity']:
        raise ValueError(f"Cannot close {quantity_to_close} shares of {symbol}. "
                         f"Only {existing_position['quantity']} shares held.")

    value_closed = quantity_to_close * price
    capital += value_closed

    existing_position['quantity'] -= quantity_to_close

    if existing_position['quantity'] == 0:
        del positions[symbol]

    return positions, capital

def calculate_pnl(positions, current_prices):
    """Calculates PnL for all open positions.

    Args:
        positions (dict): Current open positions.
        current_prices (dict): Current market prices.

    Returns:
        float: Total PnL.
    """
    total_pnl = 0.0
    for symbol, position_data in positions.items():
        quantity = position_data['quantity']
        cost_basis = position_data['price']

        if symbol not in current_prices:
            raise ValueError(f"Current price for symbol {symbol} not available in current_prices.")

        current_market_price = current_prices[symbol]

        current_value = quantity * current_market_price
        initial_cost = quantity * cost_basis
        position_pnl = current_value - initial_cost
        total_pnl += position_pnl

    return total_pnl

def run_strategy(historical_data, capital, strategy_params):
    """Simulates trading strategy on historical data.

    Args:
        historical_data (list): List of historical market data.
        capital (float): Available capital.
        strategy_params (dict): Trading strategy parameters.

    Returns:
        float: PnL from the strategy execution.
    """
    positions = {}
    current_capital = capital

    # Example: Iterate through historical data (assuming data points have a 'price' field)
    # This is a placeholder for actual strategy logic.
    # A real strategy would generate buy/sell signals and call add_position/close_position.
    for data_point_index, data_point in enumerate(historical_data):
        # Placeholder: Print current capital at each step
        # print(f"Step {data_point_index}: Capital = {current_capital}")

        # In a real strategy, you would:
        # 1. Analyze data_point and strategy_params to decide actions.
        # 2. Potentially call add_position or close_position.
        #    Example:
        #    if should_buy_signal:
        #        new_pos = {'symbol': 'XYZ', 'quantity': 10, 'price': data_point['price']}
        #        try:
        #            positions, current_capital = add_position(positions, new_pos, current_capital)
        #        except ValueError as e:
        #            print(f"Error adding position: {e}")
        #
        #    elif should_sell_signal and 'XYZ' in positions:
        #        pos_to_close = {'symbol': 'XYZ', 'quantity': 5, 'price': data_point['price']}
        #        try:
        #            positions, current_capital = close_position(positions, pos_to_close, current_capital)
        #        except ValueError as e:
        #            print(f"Error closing position: {e}")
        pass # No actual trading logic for this placeholder

    # Calculate final PnL based on remaining positions and last prices
    # Assuming the last data_point contains the relevant closing prices for PnL calculation
    if not historical_data:
        return 0.0 # No data, no PnL

    final_prices = {}
    # This is a simplification. In reality, you'd need to map symbols in positions
    # to their prices in the last data_point.
    # For this placeholder, we'll assume historical_data contains prices for symbols we might hold.
    # For a robust solution, historical_data entries should be dicts with symbol keys,
    # or you need a way to get the price for each symbol held in `positions`.

    # If positions is empty, PnL is simply current_capital - initial_capital
    if not positions:
        return current_capital - capital # PnL is the change in capital

    # If there are positions, we need their final market prices to calculate PnL.
    # This part requires a bit more structure in historical_data or a separate price feed.
    # For this placeholder, we'll assume the last data point might be a dict of prices
    # or we'll just calculate PnL based on capital changes if no positions are left.

    # Simplified: if any positions are held, this PnL calculation would be more complex.
    # For now, as no actual trades are made that change 'positions',
    # the PnL is effectively the change from initial capital.
    # If trades were made, we would use calculate_pnl with the final prices.

    # Let's assume the goal is to return the total PnL of the strategy,
    # not just the PnL of open positions at the end.
    # The PnL is the final capital minus the initial capital.
    return current_capital - capital


def calculate_donchian_channel(high, low, period):
    """Calculates the Donchian Channel.

    Args:
        high (pd.Series): Series of high prices.
        low (pd.Series): Series of low prices.
        period (int): Lookback period.

    Returns:
        tuple: upper_band (pd.Series), lower_band (pd.Series).
    """
    if not isinstance(high, pd.Series) or \
       not isinstance(low, pd.Series):
        raise TypeError("Inputs high and low must be pandas Series.")
    if period <= 0:
        raise ValueError("Period must be a positive integer.")

    upper_band = high.rolling(window=period, min_periods=period).max()
    lower_band = low.rolling(window=period, min_periods=period).min()
    return upper_band, lower_band

def calculate_atr(high, low, close, period):
    """Calculates the Average True Range (ATR).

    Args:
        high (pd.Series): Series of high prices.
        low (pd.Series): Series of low prices.
        close (pd.Series): Series of close prices.
        period (int): Lookback period for ATR calculation.

    Returns:
        pd.Series: ATR values.
    """
    if not isinstance(high, pd.Series) or \
       not isinstance(low, pd.Series) or \
       not isinstance(close, pd.Series):
        raise TypeError("Inputs high, low, and close must be pandas Series.")

    if period <= 0:
        raise ValueError("Period must be a positive integer.")

    # Calculate True Range (TR)
    # TR = max(high - low, abs(high - previous_close), abs(low - previous_close))

    # Shift close prices to get previous_close
    previous_close = close.shift(1)

    # Component 1: high - low
    tr1 = high - low

    # Component 2: abs(high - previous_close)
    tr2 = abs(high - previous_close)

    # Component 3: abs(low - previous_close)
    tr3 = abs(low - previous_close)

    # True Range is the maximum of these three components
    # Use a DataFrame to handle NaNs correctly during max(axis=1)
    tr_df = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3})
    true_range = tr_df.max(axis=1, skipna=False)

    # Handle the first TR value which will be NaN due to previous_close.
    # Some ATR definitions set the first TR to (high - low) of the first period.
    # However, consistent with rolling calculations, it's fine to let it be NaN
    # and have the rolling mean handle it. Or, we can fill the first TR specifically.
    # For simplicity, we let the rolling mean handle it.
    # If high, low, close are of length N, true_range will be length N with first element NaN.

    # Calculate ATR as the Simple Moving Average (SMA) of True Range
    # min_periods=0 ensures that it calculates even if there are fewer than 'period' non-NaN values,
    # which can happen at the beginning of the series.
    # However, for ATR, it's more standard to have NaNs until enough data is available.
    # So, we'll use min_periods=period.
    atr = true_range.rolling(window=period, min_periods=period).mean()

    return atr


def generate_entry_signals(close, donchian_upper_entry, donchian_lower_entry, entry_period):
    """
    Generates entry signals based on Donchian Channel breakouts.

    Args:
        close (pd.Series): Closing prices.
        donchian_upper_entry (pd.Series): Donchian Channel upper band for entry (e.g., 20-period).
        donchian_lower_entry (pd.Series): Donchian Channel lower band for entry (e.g., 20-period).
        entry_period (int): The period used for the entry Donchian Channel (e.g., 20).
                            This is used to correctly shift the bands for comparison.

    Returns:
        pd.Series: Signal (1 for long, -1 for short, 0 for no signal).
    """
    if not all(isinstance(s, pd.Series) for s in [close, donchian_upper_entry, donchian_lower_entry]):
        raise TypeError("Inputs close, donchian_upper_entry, donchian_lower_entry must be pandas Series.")
    if not isinstance(entry_period, int) or entry_period <= 0:
        raise ValueError("entry_period must be a positive integer.")

    signal = pd.Series(0, index=close.index)

    # Shift Donchian bands by 1 to use the previous bar's Donchian value for the current bar's close.
    # This aligns with "price breaks out of the previous period's high/low".
    prev_donchian_upper = donchian_upper_entry.shift(1)
    prev_donchian_lower = donchian_lower_entry.shift(1)

    # Long entry: Current close breaks above the previous bar's Donchian upper band.
    long_entry_condition = (close > prev_donchian_upper)
    # To ensure it's a "cross", we could also check that the previous close was not already above.
    # close.shift(1) <= prev_donchian_upper.shift(1)  (using a further shift for prev_donchian_upper's previous value)
    # However, the problem states "H1の価格が過去20期間のH1高値を更新した場合" (price updates the high).
    # A simple check `close > prev_donchian_upper` captures this "update" or "breakout".

    signal[long_entry_condition] = 1

    # Short entry: Current close breaks below the previous bar's Donchian lower band.
    short_entry_condition = (close < prev_donchian_lower)
    signal[short_entry_condition] = -1

    # Ensure that long and short conditions are mutually exclusive if they occur on same bar due to data error or extreme volatility.
    # If both true (highly unlikely with typical data), prioritize (e.g. set to 0 or handle based on rules)
    # For now, if short condition is met after long, it will overwrite. This is often acceptable.
    # A more robust way could be:
    # signal.loc[long_entry_condition & short_entry_condition] = 0 # Or some other conflict resolution
    # However, with `close > X` and `close < Y` where X > Y, this is impossible.

    return signal

def generate_exit_signals(close, donchian_upper_exit, donchian_lower_exit,
                          exit_period_long, exit_period_short, current_positions):
    """
    Generates exit signals based on Donchian Channels and current positions.

    Args:
        close (pd.Series): Closing prices.
        donchian_upper_exit (pd.Series): Donchian Channel upper band for short exit (e.g., 10-period).
        donchian_lower_exit (pd.Series): Donchian Channel lower band for long exit (e.g., 10-period).
        exit_period_long (int): The period used for the long exit Donchian Channel (e.g., 10).
        exit_period_short (int): The period used for the short exit Donchian Channel (e.g., 10).
        current_positions (pd.Series): Current positions (1 for long, -1 for short, 0 for flat).

    Returns:
        pd.Series: Exit signal (-1 to exit long, 1 to exit short, 0 for no exit).
    """
    if not all(isinstance(s, pd.Series) for s in [close, donchian_upper_exit, donchian_lower_exit, current_positions]):
        raise TypeError("Inputs close, donchian_upper_exit, donchian_lower_exit, current_positions must be pandas Series.")
    if not isinstance(exit_period_long, int) or exit_period_long <= 0:
        raise ValueError("exit_period_long must be a positive integer.")
    if not isinstance(exit_period_short, int) or exit_period_short <= 0:
        raise ValueError("exit_period_short must be a positive integer.")

    exit_signal = pd.Series(0, index=close.index)

    # Shift Donchian bands by 1 for comparison against current close
    prev_donchian_lower_exit = donchian_lower_exit.shift(1)
    prev_donchian_upper_exit = donchian_upper_exit.shift(1)

    # Long exit: Holding long AND current close falls below the previous bar's 10-period Donchian lower band.
    long_exit_condition = (current_positions == 1) & (close < prev_donchian_lower_exit)
    exit_signal[long_exit_condition] = -1 # Signal to exit long

    # Short exit: Holding short AND current close rises above the previous bar's 10-period Donchian upper band.
    short_exit_condition = (current_positions == -1) & (close > prev_donchian_upper_exit)
    exit_signal[short_exit_condition] = 1 # Signal to exit short

    return exit_signal

def calculate_position_size(account_equity, risk_percentage, atr,
                            pip_value_per_lot, lot_size,
                            max_units_per_market, current_units_for_market,
                            total_risk_percentage_limit, current_total_open_risk_percentage):
    """
    Calculates the position size in units based on risk management rules.

    Args:
        account_equity (float): Current total value of the trading account.
        risk_percentage (float): Desired risk per trade (e.g., 0.01 for 1%).
        atr (float): Current ATR(20) value for the instrument.
        pip_value_per_lot (float): Value of one pip movement per standard lot.
        lot_size (int): Number of units in one standard lot.
        max_units_per_market (int): Maximum units allowed for this instrument.
        current_units_for_market (int): Currently held units for this instrument.
        total_risk_percentage_limit (float): Max total risk across all positions (e.g., 0.05).
        current_total_open_risk_percentage (float): Sum of risk from current open positions (as % of equity).

    Returns:
        int: Number of units to trade. Returns 0 if no trade should be made.
    """

    # Input Validations
    if not all(isinstance(val, (int, float)) for val in [account_equity, risk_percentage, atr, pip_value_per_lot, total_risk_percentage_limit, current_total_open_risk_percentage]):
        raise TypeError("Numeric inputs must be of type int or float.")
    if not all(isinstance(val, int) for val in [lot_size, max_units_per_market, current_units_for_market]):
        raise TypeError("Lot size and unit counts must be integers.")

    if account_equity <= 0:
        raise ValueError("Account equity must be positive.")
    if not (0 < risk_percentage < 1):
        raise ValueError("Risk percentage per trade must be between 0 and 1 (exclusive).")
    if atr <= 0:
        # ATR can be zero in rare flat market conditions for a very short period,
        # or if data is missing. Sizing would be infinite or undefined.
        # Depending on broker/asset, pip_value_per_lot could also be zero if not configured.
        return 0 # Cannot size with non-positive ATR
    if pip_value_per_lot <= 0:
        return 0 # Cannot size with non-positive pip value per lot
    if lot_size <= 0:
        raise ValueError("Lot size must be a positive integer.")
    if max_units_per_market < 0 or current_units_for_market < 0:
        raise ValueError("Unit counts cannot be negative.")
    if not (0 < total_risk_percentage_limit <= 1): # Can be 1 (100%) in some aggressive strategies
        raise ValueError("Total risk percentage limit must be between 0 (exclusive) and 1 (inclusive).")
    if not (0 <= current_total_open_risk_percentage < total_risk_percentage_limit):
        # current_total_open_risk_percentage can be 0. It can also be >= total_risk_percentage_limit
        # if existing positions' risk grew or limit was reduced. No new trades then.
        if current_total_open_risk_percentage >= total_risk_percentage_limit:
            return 0 # Already at or over total risk limit

    # 1. Risk Amount per Trade
    risk_amount_per_trade = account_equity * risk_percentage

    # 2. Stop Loss Distance in Pips/Points
    stop_loss_pips = 2 * atr # Stop loss is 2 * ATR(20)

    # 3. Risk per Lot
    if stop_loss_pips == 0 : # ATR is positive, but could be extremely small
        return 0 # Avoid division by zero if stop_loss_pips rounds to 0 or is effectively 0
    risk_per_lot = stop_loss_pips * pip_value_per_lot
    if risk_per_lot <= 0: # Should not happen if atr and pip_value_per_lot are positive
        return 0

    # 4. Number of Lots (Raw)
    num_lots_raw = risk_amount_per_trade / risk_per_lot

    # 5. Number of Units (Initial)
    num_units = math.floor(num_lots_raw * lot_size)

    if num_units <= 0:
        return 0

    # 6. Market Limit Constraint
    available_units_market = max_units_per_market - current_units_for_market
    if available_units_market < 0: # Should not happen with valid inputs
        available_units_market = 0
    num_units = min(num_units, available_units_market)

    if num_units <= 0:
        return 0

    # 7. Total Risk Limit Constraint
    # Max additional monetary risk we can take on this new trade
    max_additional_monetary_risk_allowed = (account_equity * total_risk_percentage_limit) - \
                                           (account_equity * current_total_open_risk_percentage)

    # Ensure it's not negative due to floating point math or if current risk somehow exceeded limit
    max_additional_monetary_risk_allowed = max(0, max_additional_monetary_risk_allowed)

    # Risk this specific trade would add with the current num_units
    risk_of_this_trade_monetary = (num_units / lot_size) * risk_per_lot

    if risk_of_this_trade_monetary > max_additional_monetary_risk_allowed:
        if risk_per_lot > 0:
            # How many lots can we afford under the remaining risk capital
            affordable_lots = max_additional_monetary_risk_allowed / risk_per_lot
            num_units = math.floor(affordable_lots * lot_size)
        else: # Should be caught by earlier risk_per_lot <=0 check
            num_units = 0

    # 8. Ensure num_units is not negative and round down (already done by floor)
    if num_units <= 0:
        return 0

    return int(num_units) # Return as integer

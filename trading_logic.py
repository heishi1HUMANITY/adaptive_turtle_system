import pandas as pd
import math
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any # Added Optional, List, Dict, Tuple, Any

class Order:
    """
    Represents a trading order in the system.

    Attributes:
        order_id (str): Unique identifier for the order.
        symbol (str): The financial instrument (e.g., "EUR/USD").
        order_type (str): Type of order (e.g., "market", "stop", "limit").
        trade_action (str): Action to take ("buy" or "sell").
        quantity (float): Number of units to trade.
        order_price (Optional[float]): The price at which to trigger a stop or limit order.
                                       None for market orders at creation. Defaults to None.
        status (str): Current status of the order (e.g., "pending", "filled", "cancelled").
                      Defaults to "pending".
        fill_price (Optional[float]): The price at which the order was filled.
                                      None until filled. Defaults to None.
        timestamp_created (datetime): Timestamp of when the order was created.
        timestamp_filled (Optional[datetime]): Timestamp of when the order was filled.
                                               None until filled. Defaults to None.
        commission (float): Commission fee associated with the trade. Defaults to 0.0.
        slippage (float): Monetary value of slippage incurred on execution. Defaults to 0.0.
    """
    def __init__(self, order_id: str, symbol: str, order_type: str, trade_action: str,
                 quantity: float, order_price: Optional[float] = None, status: str = "pending",
                 fill_price: Optional[float] = None, commission: float = 0.0, slippage: float = 0.0,
                 timestamp_created: Optional[datetime] = None):
        """
        Initializes an Order object.

        Args:
            order_id: Unique identifier for the order.
            symbol: The financial instrument.
            order_type: Type of order (e.g., "market", "stop").
            trade_action: "buy" or "sell".
            quantity: Number of units.
            order_price: Price for stop or limit orders. Defaults to None.
            status: Initial status of the order. Defaults to "pending".
            fill_price: Fill price if known at creation (rare). Defaults to None.
            commission: Commission for the trade. Defaults to 0.0.
            slippage: Slippage value if known (rare). Defaults to 0.0.
            timestamp_created: Timestamp of order creation. If None, defaults to `datetime.now()`.
                               It's recommended to pass this for backtesting consistency.
        """
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type
        self.trade_action = trade_action
        self.quantity = quantity
        self.order_price = order_price
        self.status = status
        self.fill_price = fill_price
        self.timestamp_created = timestamp_created if timestamp_created is not None else datetime.now()
        self.timestamp_filled: Optional[datetime] = None # Explicitly Optional
        self.commission = commission
        self.slippage = slippage # Monetary value of slippage

class Position:
    """
    Represents an open trading position for a specific symbol.

    Attributes:
        symbol (str): The financial instrument (e.g., "EUR/USD").
        quantity (float): Number of units. Positive for a long position, negative for a short position.
        average_entry_price (float): The average price at which the units in the position were acquired.
        related_entry_order_id (str): The ID of the order that initially opened this position.
                                      Can be updated if position is averaged up/down.
        initial_stop_loss_price (Optional[float]): The stop-loss price set when the position
                                                   (or its first part) was opened.
        current_stop_loss_price (Optional[float]): The current, potentially adjusted (e.g., trailed),
                                                   stop-loss price for the entire position.
        take_profit_price (Optional[float]): The take-profit price for the position.
                                             Note: In this system, Donchian channel exits are used for
                                             take-profit, so this might not be a traditional TP order price.
        unrealized_pnl (float): The current unrealized profit or loss for this position,
                                calculated based on the current market price. Updated by PortfolioManager.
        realized_pnl (float): The accumulated profit or loss from any portions of this position
                              that have already been closed (e.g., via `reduce_position`).
        last_update_timestamp (datetime): Timestamp of the last event or update related to this position
                                          (e.g., creation, partial close, P&L update).
    """
    def __init__(self, symbol: str, quantity: float, average_entry_price: float,
                 related_entry_order_id: str, initial_stop_loss_price: Optional[float] = None,
                 current_stop_loss_price: Optional[float] = None, take_profit_price: Optional[float] = None,
                 timestamp: Optional[datetime] = None):
        """
        Initializes a Position object.

        Args:
            symbol: The financial instrument symbol.
            quantity: Number of units (positive for long, negative for short).
            average_entry_price: The average entry price for these units.
            related_entry_order_id: The ID of the entry order associated with opening this position.
            initial_stop_loss_price: The initial stop-loss price. Defaults to None.
            current_stop_loss_price: The current stop-loss price (often same as initial). Defaults to None.
            take_profit_price: The take-profit price, if applicable. Defaults to None.
            timestamp: The timestamp for position creation/update. If None, defaults to `datetime.now()`.
                       Recommended to pass for backtesting.
        """
        self.symbol = symbol
        self.quantity = quantity
        self.average_entry_price = average_entry_price
        self.initial_stop_loss_price = initial_stop_loss_price
        self.current_stop_loss_price = current_stop_loss_price
        self.take_profit_price = take_profit_price
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.last_update_timestamp = timestamp if timestamp is not None else datetime.now()
        self.related_entry_order_id = related_entry_order_id

def execute_order(order: Order, current_market_price: float, slippage_pips: float,
                  commission_per_lot: float, pip_point_value: float, lot_size: int,
                  timestamp: Optional[datetime] = None) -> Order:
    """
    Simulates the execution of a trading order, calculating fill price and commission.

    This function modifies the given order object in-place by updating its status,
    fill price, commission, slippage, and filled timestamp.

    Args:
        order: The Order object to be executed. Must be in "pending" status.
        current_market_price: The current market price for the order's symbol.
                              Used for market order execution. For stop orders, the
                              order.order_price is used as the basis for fill price calculation.
        slippage_pips: The amount of slippage in pips to apply to the execution.
                       Slippage makes buy prices higher and sell prices lower.
        commission_per_lot: The commission fee charged per standard lot.
        pip_point_value: The monetary value of one pip (or point) movement for the instrument.
                         Assumed to be the value of a single pip for a single unit of quantity.
        lot_size: The number of units in one standard lot for the instrument.
        timestamp: The timestamp of execution. If None, defaults to `datetime.now()`.
                   Recommended to pass for backtesting.

    Returns:
        The updated Order object with execution details (status="filled", fill_price, etc.).
        If the order was not pending, it's returned unchanged.

    Raises:
        ValueError: If order.trade_action or order.order_type is invalid,
                    or if lot_size is non-positive.
    """
    if order.status != "pending":
        return order

    slippage_amount = slippage_pips * pip_point_value

    if order.order_type == "market":
        if order.trade_action == "buy":
            order.fill_price = current_market_price + slippage_amount
        elif order.trade_action == "sell":
            order.fill_price = current_market_price - slippage_amount
        else:
            raise ValueError(f"Invalid trade action: {order.trade_action}")
    elif order.order_type == "stop":
        if order.trade_action == "sell":
            order.fill_price = order.order_price - slippage_amount
        elif order.trade_action == "buy":
            order.fill_price = order.order_price + slippage_amount
        else:
            raise ValueError(f"Invalid trade action for stop order: {order.trade_action}")
    else:
        raise ValueError(f"Unsupported order type: {order.order_type}")

    if lot_size <= 0:
        raise ValueError("Lot size must be positive to calculate commission.")
    order.commission = (order.quantity / lot_size) * commission_per_lot
    order.slippage = slippage_amount

    order.status = "filled"
    order.timestamp_filled = timestamp if timestamp is not None else datetime.now()
    return order

class PortfolioManager:
    """
    Manages the overall trading portfolio, including positions, orders, capital,
    and trade logging. It provides methods for opening, closing, and adjusting
    positions, as well as for calculating portfolio-level metrics like equity and risk.
    """
    def __init__(self, initial_capital: float, config: Dict[str, Any]): # Changed to Dict
        """
        Initializes the PortfolioManager.

        Args:
            initial_capital (float): The starting capital for the portfolio.
            config (dict): A configuration dictionary containing trading parameters
                           such as pip values, lot sizes, risk settings, etc.
        """
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.trade_log: List[Dict[str, Any]] = []
        self.config = config

    def record_order(self, order: Order):
        """
        Adds an order to the portfolio's list of all orders.

        Args:
            order: The Order object to record.
        """
        self.orders.append(order)

    def get_open_position(self, symbol: str) -> Optional[Position]: # Changed to Optional[Position]
        """
        Retrieves the open Position object for a given symbol.

        Args:
            symbol: The financial instrument symbol (e.g., "EUR/USD").

        Returns:
            The Position object if an open position exists for the symbol, otherwise None.
        """
        return self.positions.get(symbol)

    def open_position(self, symbol: str, trade_action: str, quantity: float,
                        entry_price: float, entry_time: datetime,
                        stop_loss_price: float, order_id: str,
                        commission: float, slippage_value: float):
        """
        Opens a new position or adds to an existing one based on a filled entry order.
        ... (rest of docstring as before)
        """
        if quantity <= 0:
            raise ValueError("Quantity for opening a position must be positive.")
        position_quantity_signed = quantity if trade_action == "buy" else -quantity
        trade_details = {
            "order_id": order_id, "symbol": symbol, "action": trade_action,
            "quantity": quantity, "price": entry_price, "timestamp": entry_time,
            "commission": commission, "slippage": slippage_value, "type": "entry"
        }
        if symbol not in self.positions:
            new_position = Position(
                symbol=symbol, quantity=position_quantity_signed,
                average_entry_price=entry_price, initial_stop_loss_price=stop_loss_price,
                current_stop_loss_price=stop_loss_price, related_entry_order_id=order_id,
                timestamp=entry_time
            )
            self.positions[symbol] = new_position
        else:
            existing_position = self.positions[symbol]
            if (existing_position.quantity > 0 and trade_action == "sell") or \
               (existing_position.quantity < 0 and trade_action == "buy"):
                raise ValueError(
                    f"Opposing trade action '{trade_action}' for existing position on {symbol}. "
                    "Close existing position first or handle reduction/reversal explicitly."
                )
            total_value_existing = existing_position.quantity * existing_position.average_entry_price
            total_value_new_trade = position_quantity_signed * entry_price
            new_total_quantity = existing_position.quantity + position_quantity_signed
            if new_total_quantity == 0:
                print(f"Warning: Position for {symbol} effectively closed by 'open_position' call. "
                      f"P&L not explicitly calculated for this closure. Order ID: {order_id}")
                del self.positions[symbol]
            else:
                existing_position.average_entry_price = \
                    (total_value_existing + total_value_new_trade) / new_total_quantity
                existing_position.quantity = new_total_quantity
                existing_position.last_update_timestamp = entry_time
                if stop_loss_price:
                    existing_position.initial_stop_loss_price = stop_loss_price
                    existing_position.current_stop_loss_price = stop_loss_price
        self.capital -= commission
        self.trade_log.append(trade_details)
        if symbol in self.positions and stop_loss_price is not None and stop_loss_price > 0:
            sl_order_id = f"{order_id}_sl"
            sl_trade_action = "sell" if trade_action == "buy" else "buy"
            final_position_obj = self.positions[symbol]
            sl_quantity = abs(final_position_obj.quantity)
            stop_loss_order = Order(
                order_id=sl_order_id, symbol=symbol, order_type="stop",
                trade_action=sl_trade_action, quantity=sl_quantity,
                order_price=stop_loss_price, status="pending",
                timestamp_created=entry_time
            )
            self.record_order(stop_loss_order)

    def close_position_completely(self, symbol: str, exit_price: float, exit_time: datetime,
                                  order_id: str, commission: float, slippage_value: float):
        """
        Closes the entire open position for a given symbol.
        ... (rest of docstring as before)
        """
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to close.")
        quantity_closed = abs(position.quantity)
        closing_trade_action = "sell" if position.quantity > 0 else "buy"
        if position.quantity > 0:
            realized_pnl = (exit_price - position.average_entry_price) * position.quantity
        else:
            realized_pnl = (position.average_entry_price - exit_price) * abs(position.quantity)
        net_realized_pnl = realized_pnl - commission
        self.capital += net_realized_pnl
        trade_details = {
            "order_id": order_id, "symbol": symbol, "action": closing_trade_action,
            "quantity": quantity_closed, "price": exit_price, "timestamp": exit_time,
            "commission": commission, "slippage": slippage_value,
            "realized_pnl": net_realized_pnl, "type": "exit"
        }
        self.trade_log.append(trade_details)
        position.realized_pnl += net_realized_pnl
        del self.positions[symbol]
        for order_in_list in self.orders:
            if order_in_list.symbol == symbol and order_in_list.status == "pending":
                if order_in_list.order_type == "stop":
                    order_in_list.status = "cancelled"

    def reduce_position(self, symbol: str, quantity_to_close: float, exit_price: float,
                        exit_time: datetime, order_id: str, commission: float, slippage_value: float):
        """
        Reduces an open position by a specified quantity and realizes P&L for that portion.
        ... (rest of docstring as before)
        """
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to reduce.")
        if quantity_to_close <= 0:
            raise ValueError("Quantity to close must be positive.")
        if quantity_to_close > abs(position.quantity):
            raise ValueError(f"Cannot close {quantity_to_close} units, only {abs(position.quantity)} held for {symbol}.")
        if quantity_to_close == abs(position.quantity):
            return self.close_position_completely(symbol, exit_price, exit_time, order_id, commission, slippage_value)
        closing_trade_action = "sell" if position.quantity > 0 else "buy"
        if position.quantity > 0:
            realized_pnl_reduction = (exit_price - position.average_entry_price) * quantity_to_close
        else:
            realized_pnl_reduction = (position.average_entry_price - exit_price) * quantity_to_close
        net_realized_pnl_reduction = realized_pnl_reduction - commission
        self.capital += net_realized_pnl_reduction
        position.realized_pnl += net_realized_pnl_reduction
        if position.quantity > 0:
            position.quantity -= quantity_to_close
        else:
            position.quantity += quantity_to_close
        position.last_update_timestamp = exit_time
        trade_details = {
            "order_id": order_id, "symbol": symbol, "action": closing_trade_action,
            "quantity": quantity_to_close, "price": exit_price, "timestamp": exit_time,
            "commission": commission, "slippage": slippage_value,
            "realized_pnl": net_realized_pnl_reduction, "type": "reduction"
        }
        self.trade_log.append(trade_details)

    def update_unrealized_pnl(self, current_prices: Dict[str, float]): # Changed to Dict
        """
        Updates the unrealized P&L for all currently open positions.
        ... (rest of docstring as before)
        """
        for symbol, position in self.positions.items():
            if symbol not in current_prices or pd.isna(current_prices[symbol]):
                print(f"Warning: Current price for {symbol} not available in current_prices. "
                      f"Unrealized P&L for this position will not be updated at this step.")
                continue
            current_price = current_prices[symbol]
            if position.quantity > 0:
                position.unrealized_pnl = (current_price - position.average_entry_price) * position.quantity
            elif position.quantity < 0:
                position.unrealized_pnl = (position.average_entry_price - current_price) * abs(position.quantity)
            else:
                position.unrealized_pnl = 0.0
            position.last_update_timestamp = datetime.now()

    def get_total_equity(self, current_prices: Dict[str, float]) -> float: # Changed to Dict
        """
        Calculates the total equity of the portfolio.
        ... (rest of docstring as before)
        """
        self.update_unrealized_pnl(current_prices)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values() if pos.unrealized_pnl is not None)
        return self.capital + total_unrealized_pnl

    def get_current_total_open_risk_percentage(self, current_prices: Dict[str, float]) -> float: # Changed to Dict
        """
        Calculates the current total risk exposure from all open positions...
        ... (rest of docstring as before)
        """
        total_risk_value_monetary = 0.0
        total_equity = self.get_total_equity(current_prices)
        if total_equity <= 0:
            return float('inf')
        for symbol, position in self.positions.items():
            if position.current_stop_loss_price is None or position.current_stop_loss_price <= 0:
                print(f"Warning: Position {symbol} (ID: {position.related_entry_order_id}) has no valid "
                      f"current_stop_loss_price. Skipping its contribution to total open risk calculation.")
                continue
            current_price_for_symbol = current_prices.get(symbol)
            if current_price_for_symbol is None or pd.isna(current_price_for_symbol):
                print(f"Warning: Current price for {symbol} not available for risk calculation. "
                      "Skipping its contribution to total open risk calculation.")
                continue
            if position.quantity > 0:
                risk_per_unit = max(0, current_price_for_symbol - position.current_stop_loss_price)
            else:
                risk_per_unit = max(0, position.current_stop_loss_price - current_price_for_symbol)
            position_risk_monetary = risk_per_unit * abs(position.quantity)
            total_risk_value_monetary += position_risk_monetary
        if total_equity <= 0:
             return float('inf')
        if total_risk_value_monetary == 0:
            return 0.0
        total_risk_percentage = total_risk_value_monetary / total_equity
        return total_risk_percentage

def calculate_initial_stop_loss(entry_price: float, trade_action: str, atr_value: float, atr_multiplier: float) -> float:
    """
    Calculates the initial stop-loss price for a new trade.
    ... (rest of docstring as before)
    """
    if atr_value <= 0:
        raise ValueError("ATR value must be positive for stop-loss calculation.")
    if atr_multiplier <= 0:
        raise ValueError("ATR multiplier must be positive.")
    if trade_action == "buy":
        return entry_price - (atr_value * atr_multiplier)
    elif trade_action == "sell":
        return entry_price + (atr_value * atr_multiplier)
    else:
        raise ValueError(f"Invalid trade action '{trade_action}' for stop-loss calculation.")

def calculate_position_size(portfolio_manager: PortfolioManager,
                            symbol_to_trade: str,
                            atr_value: float,
                            current_prices_for_risk_calc: Dict[str, float], # Changed to Dict
                            config: Dict[str, Any]) -> int: # Changed to Dict
    """
    Calculates the position size in units based on multiple risk management rules.
    ... (rest of docstring as before)
    """
    if atr_value <= 0:
        print(f"Warning: ATR value for {symbol_to_trade} is {atr_value}. Cannot size position.")
        return 0
    try:
        risk_percentage_per_trade = config['risk_percentage_per_trade']
        stop_loss_atr_multiplier = config['stop_loss_atr_multiplier']
        max_units_config = config.get('max_units_per_market')
        if isinstance(max_units_config, dict):
            max_units_per_market = max_units_config.get(symbol_to_trade, float('inf'))
        elif isinstance(max_units_config, (int, float)):
            max_units_per_market = max_units_config
        else:
            max_units_per_market = float('inf')
        total_risk_percentage_limit = config['total_risk_percentage_limit']
        pip_value_for_symbol_per_unit = config['pip_point_value'][symbol_to_trade]
    except KeyError as e:
        print(f"Error: Missing required configuration key: {e} in config: {config}")
        return 0
    if not (0 < risk_percentage_per_trade < 1):
         print(f"Warning: risk_percentage_per_trade ({risk_percentage_per_trade}) from config is out of bounds (0,1).")
         return 0
    if not (0 < total_risk_percentage_limit <= 1):
         print(f"Warning: total_risk_percentage_limit ({total_risk_percentage_limit}) from config is out of bounds (0,1].")
         return 0
    account_equity = portfolio_manager.get_total_equity(current_prices_for_risk_calc)
    if account_equity <= 0:
        print("Warning: Account equity is zero or negative. Cannot size position.")
        return 0
    stop_loss_distance_price_units = stop_loss_atr_multiplier * atr_value
    if stop_loss_distance_price_units <= 0:
        print(f"Warning: stop_loss_distance_price_units for {symbol_to_trade} is non-positive ({stop_loss_distance_price_units}).")
        return 0
    pip_size = 0.0001
    if "JPY" in symbol_to_trade.upper() or symbol_to_trade == "TESTA":
        pip_size = 0.01
    elif symbol_to_trade == "TESTB":
        pip_size = 1.0
    stop_loss_as_pips = stop_loss_distance_price_units / pip_size
    risk_per_unit_trade = stop_loss_as_pips * pip_value_for_symbol_per_unit
    if risk_per_unit_trade <= 0:
        print(f"Warning: risk_per_unit_trade for {symbol_to_trade} is non-positive ({risk_per_unit_trade}). "
              f"Check ATR ({atr_value}), pip_value ({pip_value_for_symbol_per_unit}), pip_size ({pip_size}).")
        return 0
    monetary_risk_allotted_for_trade = account_equity * risk_percentage_per_trade
    num_units_trade_risk_limited = math.floor(monetary_risk_allotted_for_trade / risk_per_unit_trade)
    if num_units_trade_risk_limited <= 0:
        return 0
    current_pos_for_symbol = portfolio_manager.get_open_position(symbol_to_trade)
    current_units_held_for_market = abs(current_pos_for_symbol.quantity) if current_pos_for_symbol else 0
    available_units_for_market = max_units_per_market - current_units_held_for_market
    if available_units_for_market <= 0 :
        print(f"Warning: Already at or over max_units_per_market for {symbol_to_trade} "
              f"({current_units_held_for_market}/{max_units_per_market}). Cannot add more units.")
        return 0
    num_units_market_limited = min(num_units_trade_risk_limited, math.floor(available_units_for_market))
    if num_units_market_limited <= 0:
        return 0
    current_total_open_risk_percentage = portfolio_manager.get_current_total_open_risk_percentage(current_prices_for_risk_calc)
    if current_total_open_risk_percentage >= total_risk_percentage_limit:
        print(f"Warning: Current total open risk ({current_total_open_risk_percentage:.2%}) "
              f"already at/exceeds limit ({total_risk_percentage_limit:.2%}). No new trades.")
        return 0
    monetary_risk_of_potential_new_trade = num_units_market_limited * risk_per_unit_trade
    current_total_risk_monetary = current_total_open_risk_percentage * account_equity if account_equity > 0 else 0
    potential_total_risk_monetary = current_total_risk_monetary + monetary_risk_of_potential_new_trade
    potential_total_risk_percentage = potential_total_risk_monetary / account_equity if account_equity > 0 else float('inf')
    num_units_final = num_units_market_limited
    if potential_total_risk_percentage > total_risk_percentage_limit:
        allowed_additional_monetary_risk = max(0, (total_risk_percentage_limit * account_equity) - current_total_risk_monetary)
        if allowed_additional_monetary_risk <= 0:
            num_units_final = 0
        else:
            affordable_units_under_total_risk = math.floor(allowed_additional_monetary_risk / risk_per_unit_trade)
            num_units_final = min(num_units_market_limited, affordable_units_under_total_risk)
    if num_units_final <= 0:
        return 0
    return int(math.floor(num_units_final))

def run_strategy(historical_data_df: pd.DataFrame, initial_capital: float, config: Dict[str, Any]) -> Dict[str, Any]: # Changed to Dict
    """
    Simulates a trading strategy over a period of historical market data.

    The strategy involves:
    - Trading multiple markets as defined in the `config`.
    - Using Donchian Channels for entry signals (breakout of N-period high/low).
    - Using Donchian Channels for take-profit exit signals (breakout of M-period low for longs, high for shorts).
    - Applying ATR-based stop-loss orders for risk management on each trade.
    - Sizing positions based on per-trade risk percentage, market-specific unit limits,
      and a total portfolio risk limit.

    Args:
        historical_data_df (pd.DataFrame): A pandas DataFrame containing historical
            market data. It must be indexed by datetime and have a MultiIndex for
            columns of the format (Symbol, Feature), e.g., ('EUR/USD', 'Open'),
            ('EUR/USD', 'High'), ('EUR/USD', 'Low'), ('EUR/USD', 'Close'), ('EUR/USD', 'ATR').
            'ATR' (Average True Range) is assumed to be in price units, consistent
            with Open/High/Low/Close prices for that symbol.
        initial_capital (float): The starting capital for the simulation.
        config (dict): A configuration dictionary containing all necessary parameters
                       for the strategy, portfolio management, and risk controls. This includes:
                       - 'markets' (list): List of symbols to trade (e.g., ["EUR/USD", "USD/JPY"]).
                       - 'entry_donchian_period' (int): Lookback period for entry Donchian Channel.
                       - 'take_profit_long_exit_period' (int): Lookback for Donchian low for long position exits.
                       - 'take_profit_short_exit_period' (int): Lookback for Donchian high for short position exits.
                       - 'stop_loss_atr_multiplier' (float): ATR multiplier for stop-loss calculation.
                       - 'slippage_pips' (float): Slippage in pips to apply on order execution.
                       - 'commission_per_lot' (float): Commission fee per lot in account currency.
                       - 'pip_point_value' (dict): Maps symbol to its pip/point value in account currency for 1 unit.
                       - 'lot_size' (dict): Maps symbol to its contract size (units per lot).
                       - Plus, risk management parameters used by `calculate_position_size`
                         (e.g., 'risk_percentage_per_trade', 'max_units_per_market', 'total_risk_percentage_limit').

    Returns:
        dict: A dictionary containing the results of the simulation:
              - 'equity_curve' (pd.DataFrame): DataFrame with 'timestamp' and 'equity' columns,
                                               tracking portfolio equity over time.
              - 'trade_log' (list): A list of dictionaries, where each dictionary represents
                                    an executed trade with its details.
              - 'orders' (list): A list of all Order objects (pending, filled, cancelled)
                                 created during the simulation.

    Main Simulation Loop per Timestamp:
    1.  **Data Preparation**: At the start, Donchian channels for entry and exit are
        pre-calculated for all markets and added to `historical_data_df`.
    2.  **Iteration**: The function iterates through each timestamp (row) of the
        `historical_data_df` starting from an offset to ensure indicators are valid.
    3.  **Portfolio Update**: For each timestamp:
        a.  Current market prices and ATR values are extracted.
        b.  Unrealized P&L for all open positions is updated in `portfolio_manager`.
    4.  **Event Processing (Order of Operations is important):**
        a.  **Section A: Process Pending Stop Orders**: Checks if any active stop-loss
            orders have been triggered by the current bar's High/Low prices. If triggered,
            the stop order is executed, and the corresponding position is closed.
            The `current_positions_snapshot` and `historical_position_states` are updated.
        b.  **Section B: Generate Entry Signals**: For markets where the portfolio is
            currently flat (i.e., no open position for that symbol), Donchian entry
            signals are generated. If a valid entry signal occurs:
            i.  Position size is calculated considering risk parameters.
            ii. If size > 0, a market order is created and executed.
            iii.The new position is opened in `portfolio_manager`.
            iv. An associated stop-loss order is automatically created and recorded.
            v.  `current_positions_snapshot` and `historical_position_states` are updated.
        c.  **Section C: Generate Take-Profit Exit Signals**: For markets with active
            positions (that were not stopped out in Section A of the current bar),
            Donchian exit signals are generated. If an exit signal is triggered for an
            existing position, a market order is created and executed to close that position.
            `current_positions_snapshot` and `historical_position_states` are updated.
    5.  **Record Equity (Section D)**: Portfolio equity is calculated and recorded for
        the current timestamp.
    6.  **Results**: After iterating through all data, the function returns the
        equity curve, trade log, and list of all orders.
    """
    portfolio_manager = PortfolioManager(initial_capital, config)
    markets = config.get('markets', [])
    entry_donchian_period = config.get('entry_donchian_period', 20)
    long_exit_donchian_period = config.get('take_profit_long_exit_period', 10)
    short_exit_donchian_period = config.get('take_profit_short_exit_period', 10)

    for symbol in markets:
        if (symbol, 'High') not in historical_data_df.columns or \
           (symbol, 'Low') not in historical_data_df.columns:
            raise ValueError(f"Missing High/Low data for symbol {symbol} in historical_data_df")
        if (symbol, 'ATR') not in historical_data_df.columns:
            raise ValueError(f"Missing ATR data for symbol {symbol} in historical_data_df")
        historical_data_df[(symbol, 'DonchianUpperEntry')], historical_data_df[(symbol, 'DonchianLowerEntry')] = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       entry_donchian_period)
        _, historical_data_df[(symbol, 'DonchianLowerExitLong')] = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       long_exit_donchian_period)
        historical_data_df[(symbol, 'DonchianUpperExitShort')], _ = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       short_exit_donchian_period)
    equity_curve = []
    current_positions_snapshot = {symbol: 0 for symbol in markets}
    historical_position_states = {
        market: pd.Series(0, index=historical_data_df.index) for market in markets
    }
    start_offset = max(entry_donchian_period, long_exit_donchian_period, short_exit_donchian_period)
    historical_data_df = historical_data_df.sort_index()

    for timestamp, row in historical_data_df.iloc[start_offset:].iterrows():
        current_prices = {
            symbol: row[(symbol, 'Close')]
            for symbol in markets
            if (symbol, 'Close') in row and pd.notna(row[(symbol, 'Close')])
        }
        current_atr_values = {
            symbol: row[(symbol, 'ATR')]
            for symbol in markets
            if (symbol, 'ATR') in row and pd.notna(row[(symbol, 'ATR')])
        }
        if not current_prices:
            current_equity = portfolio_manager.capital + sum(
                p.unrealized_pnl for p in portfolio_manager.positions.values() if p.unrealized_pnl is not None
            )
            equity_curve.append({'timestamp': timestamp, 'equity': current_equity})
            continue
        portfolio_manager.update_unrealized_pnl(current_prices)
        # --- A. Process Pending Orders (Mainly Stop-Loss Orders) ---
        for order in list(portfolio_manager.orders):
            if order.status == "pending" and order.order_type == "stop":
                position = portfolio_manager.get_open_position(order.symbol)
                if not position:
                    order.status = "cancelled"
                    continue
                symbol_low_price = row.get((order.symbol, 'Low'))
                symbol_high_price = row.get((order.symbol, 'High'))
                if pd.isna(symbol_low_price) or pd.isna(symbol_high_price):
                    print(f"Warning: Missing Low/High price for {order.symbol} at {timestamp}. "
                          f"Cannot process stop order {order.order_id}")
                    continue
                should_execute_stop = False
                if position.quantity > 0 and symbol_low_price <= order.order_price:
                    should_execute_stop = True
                elif position.quantity < 0 and symbol_high_price >= order.order_price:
                    should_execute_stop = True
                if should_execute_stop:
                    executed_stop_order = execute_order(
                        order=order,
                        current_market_price=order.order_price,
                        slippage_pips=config['slippage_pips'],
                        commission_per_lot=config['commission_per_lot'],
                        pip_point_value=config['pip_point_value'][order.symbol],
                        lot_size=config['lot_size'][order.symbol],
                        timestamp=timestamp
                    )
                    portfolio_manager.close_position_completely(
                        symbol=executed_stop_order.symbol,
                        exit_price=executed_stop_order.fill_price,
                        exit_time=timestamp,
                        order_id=executed_stop_order.order_id,
                        commission=executed_stop_order.commission,
                        slippage_value=executed_stop_order.slippage
                    )
                    current_positions_snapshot[order.symbol] = 0
                    historical_position_states[order.symbol].loc[timestamp:] = 0
        # --- B. Generate Entry Signals (for each market) ---
        for symbol in markets:
            if current_positions_snapshot.get(symbol, 0) == 0:
                close_series_to_current = historical_data_df.loc[:timestamp, (symbol, 'Close')]
                donchian_upper_entry_to_current = historical_data_df.loc[:timestamp, (symbol, 'DonchianUpperEntry')]
                donchian_lower_entry_to_current = historical_data_df.loc[:timestamp, (symbol, 'DonchianLowerEntry')]
                if close_series_to_current.empty or \
                   len(close_series_to_current) < entry_donchian_period or \
                   pd.isna(close_series_to_current.iloc[-1]):
                    continue
                entry_signals = generate_entry_signals(
                    close_series_to_current,
                    donchian_upper_entry_to_current,
                    donchian_lower_entry_to_current,
                    entry_donchian_period
                )
                current_signal = entry_signals.iloc[-1] if not entry_signals.empty else 0
                if current_signal == 1 or current_signal == -1:
                    trade_action = "buy" if current_signal == 1 else "sell"
                    atr_val = current_atr_values.get(symbol)
                    if atr_val is None or pd.isna(atr_val) or atr_val <= 0 :
                        print(f"Warning: Invalid ATR value {atr_val} for {symbol} at {timestamp}. Cannot size position.")
                        continue
                    if symbol not in current_prices or pd.isna(current_prices[symbol]):
                        print(f"Warning: Missing current price for {symbol} at {timestamp} for position sizing.")
                        continue
                    num_units = calculate_position_size(
                        portfolio_manager, symbol, atr_val, current_prices, config
                    )
                    if num_units > 0:
                        entry_order_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M%S')}_entry_{len(portfolio_manager.orders)}"
                        market_entry_order = Order(
                            order_id=entry_order_id, symbol=symbol, order_type="market",
                            trade_action=trade_action, quantity=num_units,
                            timestamp_created=timestamp
                        )
                        portfolio_manager.record_order(market_entry_order)
                        executed_entry_order = execute_order(
                            order=market_entry_order,
                            current_market_price=current_prices[symbol],
                            slippage_pips=config['slippage_pips'],
                            commission_per_lot=config['commission_per_lot'],
                            pip_point_value=config['pip_point_value'][symbol],
                            lot_size=config['lot_size'][symbol],
                            timestamp=timestamp
                        )
                        stop_loss_price = calculate_initial_stop_loss(
                            entry_price=executed_entry_order.fill_price,
                            trade_action=trade_action,
                            atr_value=atr_val,
                            atr_multiplier=config['stop_loss_atr_multiplier']
                        )
                        portfolio_manager.open_position(
                            symbol=symbol, trade_action=trade_action, quantity=num_units,
                            entry_price=executed_entry_order.fill_price, entry_time=timestamp,
                            stop_loss_price=stop_loss_price, order_id=executed_entry_order.order_id,
                            commission=executed_entry_order.commission,
                            slippage_value=executed_entry_order.slippage
                        )
                        new_pos_state = 1 if trade_action == "buy" else -1
                        current_positions_snapshot[symbol] = new_pos_state
                        historical_position_states[symbol].loc[timestamp:] = new_pos_state
        # --- C. Generate Exit Signals (Donchian-based Take-Profit) ---
        for symbol in markets:
            current_pos_state_on_bar_open = historical_position_states[symbol].shift(1).fillna(0).loc[timestamp]
            if current_pos_state_on_bar_open != 0:
                if current_positions_snapshot.get(symbol, 0) == 0:
                    continue
                close_series = historical_data_df.loc[:timestamp, (symbol, 'Close')]
                if close_series.empty or pd.isna(close_series.iloc[-1]):
                    continue
                donchian_upper_exit_series = historical_data_df.loc[:timestamp, (symbol, 'DonchianUpperExitShort')]
                donchian_lower_exit_series = historical_data_df.loc[:timestamp, (symbol, 'DonchianLowerExitLong')]
                position_series_for_signal = historical_position_states[symbol].loc[:timestamp]
                exit_period_long = config.get('take_profit_long_exit_period', 10)
                exit_period_short = config.get('take_profit_short_exit_period', 10)
                exit_signals = generate_exit_signals(
                    close_series, donchian_upper_exit_series, donchian_lower_exit_series,
                    exit_period_long, exit_period_short, position_series_for_signal
                )
                current_exit_signal = exit_signals.iloc[-1] if not exit_signals.empty else 0
                if (current_pos_state_on_bar_open == 1 and current_exit_signal == -1) or \
                   (current_pos_state_on_bar_open == -1 and current_exit_signal == 1):
                    open_pos = portfolio_manager.get_open_position(symbol)
                    if not open_pos:
                        continue
                    trade_action = "sell" if current_pos_state_on_bar_open == 1 else "buy"
                    exit_order_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M%S')}_tp_exit_{len(portfolio_manager.orders)}"
                    quantity_to_close = abs(open_pos.quantity)
                    market_exit_order = Order(
                        order_id=exit_order_id, symbol=symbol, order_type="market",
                        trade_action=trade_action, quantity=quantity_to_close,
                        timestamp_created=timestamp
                    )
                    portfolio_manager.record_order(market_exit_order)
                    if symbol not in current_prices or pd.isna(current_prices[symbol]):
                        print(f"Warning: Missing current price for {symbol} at {timestamp} for TP exit execution.")
                        market_exit_order.status = "cancelled_no_price"
                        continue
                    executed_exit_order = execute_order(
                        order=market_exit_order,
                        current_market_price=current_prices[symbol],
                        slippage_pips=config['slippage_pips'],
                        commission_per_lot=config['commission_per_lot'],
                        pip_point_value=config['pip_point_value'][symbol],
                        lot_size=config['lot_size'][symbol],
                        timestamp=timestamp
                    )
                    portfolio_manager.close_position_completely(
                        symbol=symbol, exit_price=executed_exit_order.fill_price,
                        exit_time=timestamp, order_id=executed_exit_order.order_id,
                        commission=executed_exit_order.commission,
                        slippage_value=executed_exit_order.slippage
                    )
                    current_positions_snapshot[symbol] = 0
                    historical_position_states[symbol].loc[timestamp:] = 0
        # --- D. Record Equity for this Timestamp ---
        current_equity = portfolio_manager.get_total_equity(current_prices if current_prices else {})
        equity_curve.append({'timestamp': timestamp, 'equity': current_equity})
    return {
        'equity_curve': pd.DataFrame(equity_curve).set_index('timestamp') if equity_curve else pd.DataFrame(),
        'trade_log': portfolio_manager.trade_log,
        'orders': portfolio_manager.orders
    }

def calculate_donchian_channel(high, low, period):
    """Calculates the Donchian Channel.
    ... (rest of docstring as before)
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
    ... (rest of docstring as before)
    """
    if not isinstance(high, pd.Series) or \
       not isinstance(low, pd.Series) or \
       not isinstance(close, pd.Series):
        raise TypeError("Inputs high, low, and close must be pandas Series.")
    if period <= 0:
        raise ValueError("Period must be a positive integer.")
    previous_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - previous_close)
    tr3 = abs(low - previous_close)
    tr_df = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3})
    true_range = tr_df.max(axis=1, skipna=False)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    return atr

def generate_entry_signals(close, donchian_upper_entry, donchian_lower_entry, entry_period):
    """
    Generates entry signals based on Donchian Channel breakouts.
    ... (rest of docstring as before)
    """
    if not all(isinstance(s, pd.Series) for s in [close, donchian_upper_entry, donchian_lower_entry]):
        raise TypeError("Inputs close, donchian_upper_entry, donchian_lower_entry must be pandas Series.")
    if not isinstance(entry_period, int) or entry_period <= 0:
        raise ValueError("entry_period must be a positive integer.")
    signal = pd.Series(0, index=close.index)
    prev_donchian_upper = donchian_upper_entry.shift(1)
    prev_donchian_lower = donchian_lower_entry.shift(1)
    long_entry_condition = (close > prev_donchian_upper)
    signal[long_entry_condition] = 1
    short_entry_condition = (close < prev_donchian_lower)
    signal[short_entry_condition] = -1
    return signal

def generate_exit_signals(close, donchian_upper_exit, donchian_lower_exit,
                          exit_period_long, exit_period_short, current_positions):
    """
    Generates exit signals based on Donchian Channels and current positions.
    ... (rest of docstring as before)
    """
    if not all(isinstance(s, pd.Series) for s in [close, donchian_upper_exit, donchian_lower_exit, current_positions]):
        raise TypeError("Inputs close, donchian_upper_exit, donchian_lower_exit, current_positions must be pandas Series.")
    if not isinstance(exit_period_long, int) or exit_period_long <= 0:
        raise ValueError("exit_period_long must be a positive integer.")
    if not isinstance(exit_period_short, int) or exit_period_short <= 0:
        raise ValueError("exit_period_short must be a positive integer.")
    exit_signal = pd.Series(0, index=close.index)
    prev_donchian_lower_exit = donchian_lower_exit.shift(1)
    prev_donchian_upper_exit = donchian_upper_exit.shift(1)
    long_exit_condition = (current_positions == 1) & (close < prev_donchian_lower_exit)
    exit_signal[long_exit_condition] = -1
    short_exit_condition = (current_positions == -1) & (close > prev_donchian_upper_exit)
    exit_signal[short_exit_condition] = 1
    return exit_signal

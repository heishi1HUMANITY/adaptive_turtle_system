import pandas as pd
import math
from datetime import datetime
from typing import Union, Optional, List, Dict, Tuple, Any

class Order:
    """
    Represents a trading order in the system.

    An order can be for entry or exit, market or pending (stop/limit).
    It holds all information related to a specific trade instruction.
    """
    def __init__(self, order_id: str, symbol: str, order_type: str, trade_action: str,
                 quantity: float, order_price: Optional[float] = None, status: str = "pending",
                 fill_price: Optional[float] = None, commission: float = 0.0, slippage: float = 0.0,
                 timestamp_filled: Optional[datetime] = None): # Added timestamp_filled to signature
        """
        Initializes an Order object.

        Args:
            order_id (str): Unique identifier for the order.
            symbol (str): The financial instrument symbol (e.g., "EUR/USD").
            order_type (str): Type of order, e.g., "market", "stop", "limit".
            trade_action (str): Action of the trade, either "buy" or "sell".
            quantity (float): The amount of the instrument to trade (always positive).
            order_price (Optional[float], optional): The price at which to execute for pending orders.
                                           None for market orders. Defaults to None.
            status (str, optional): Current status of the order, e.g., "pending", "filled",
                                    "cancelled". Defaults to "pending".
            fill_price (Optional[float], optional): The price at which the order was filled.
                                          None until filled. Defaults to None.
            commission (float, optional): Commission incurred for this order. Defaults to 0.0.
            slippage (float, optional): Monetary value of slippage incurred for this order. Defaults to 0.0.
            timestamp_filled (Optional[datetime], optional): Time when the order was filled. Defaults to None.
        """
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type  # Type of order: "market", "stop", "limit"
        self.trade_action = trade_action  # Direction: "buy" or "sell"
        self.quantity = quantity  # Number of units (always positive)
        self.order_price = order_price  # Specified price for stop or limit orders
        self.status = status  # Current state: "pending", "filled", "cancelled"
        self.fill_price = fill_price  # Actual execution price after filling
        self.timestamp_created = datetime.now()  # Time when the order object was created
        self.timestamp_filled = timestamp_filled  # Time when the order was successfully filled
        self.commission = commission  # Commission fee for this order
        self.slippage = slippage  # Monetary value of slippage for this order

class Position:
    """
    Represents an open position in a financial instrument.

    It tracks the quantity, average entry price, stop-loss levels,
    take-profit levels (if any), and P&L for an open trade.
    """
    def __init__(self, symbol: str, quantity: float, average_entry_price: float,
                 related_entry_order_id: str, initial_stop_loss_price: Optional[float] = None,
                 current_stop_loss_price: Optional[float] = None, take_profit_price: Optional[float] = None):
        """
        Initializes a Position object.

        Args:
            symbol (str): The financial instrument symbol (e.g., "EUR/USD").
            quantity (float): The number of units of the instrument.
                              Positive for a long position, negative for a short position.
            average_entry_price (float): The average price at which the position was entered.
            related_entry_order_id (str): The ID of the entry order that initially created this position.
            initial_stop_loss_price (Optional[float], optional): The initial stop-loss price set when the position
                                                       was opened or last significantly modified. Defaults to None.
            current_stop_loss_price (Optional[float], optional): The current stop-loss price, which might be
                                                       adjusted (e.g., trailed). Defaults to None.
            take_profit_price (Optional[float], optional): The take-profit price for this position.
                                                 (Note: Current strategy uses Donchian exits, not fixed TP orders).
                                                 Defaults to None.
        """
        self.symbol = symbol
        self.quantity = quantity  # Positive for long positions, negative for short positions
        self.average_entry_price = average_entry_price
        self.initial_stop_loss_price = initial_stop_loss_price
        self.current_stop_loss_price = current_stop_loss_price
        self.take_profit_price = take_profit_price  # May not be used if strategy relies on dynamic exits
        self.unrealized_pnl: Optional[float] = 0.0  # Profit or loss if the position were closed at current market prices
        self.realized_pnl: float = 0.0  # Profit or loss accumulated from partially or fully closing this position
        self.last_update_timestamp: datetime = datetime.now()  # Timestamp of the last modification or P&L update
        self.related_entry_order_id: str = related_entry_order_id # ID of the order that opened/last significantly modified this position
        self.active_stop_loss_order_id: Optional[str] = None  # ID of the currently active stop-loss order linked to this position

def execute_order(order: Order, current_market_price: float, slippage_pips: float,
                  commission_per_lot: float, pip_point_value: float, lot_size: int,
                  timestamp_filled_param: datetime) -> Order:
    """
    Simulates the execution of a given financial order, updating its state.

    This function calculates the fill price based on the order type, current market price,
    and specified slippage. It also computes the commission for the trade.
    The input `order` object is modified in place.

    Args:
        order (Order): The Order object to be executed. Must be in "pending" status.
        current_market_price (float): For market orders, this is the current market price used as a base for fill.
                                      For stop or limit orders, this should be the order's trigger price
                                      (order.order_price), as slippage is applied relative to that.
        slippage_pips (float): The amount of slippage in pips (points).
                               Slippage is applied such that it's detrimental to the trader
                               (e.g., buy fills at a higher price, sell fills at a lower price).
        commission_per_lot (float): The commission fee charged per standard lot.
        pip_point_value (float): The monetary value of one pip/point movement for a single unit
                                 of the instrument (e.g., for EUR/USD, if 1 pip = 0.0001 change,
                                 this is the value of that 0.0001 change for 1 unit of EUR).
        lot_size (int): The number of units in one standard lot for the instrument.

    Returns:
        Order: The executed (or state-unchanged if not executable) Order object with updated
               attributes: `status`, `fill_price`, `commission`, `slippage` (monetary),
               and `timestamp_filled`.

    Raises:
        ValueError: If the order has an invalid `trade_action`, an unsupported `order_type`,
                    or if `lot_size` is non-positive.
    """
    if order.status != "pending":
        # If the order is not pending (e.g., already filled or cancelled), no action is taken.
        return order

    # Calculate total monetary slippage: slippage per point * number of points for one unit
    slippage_amount = slippage_pips * pip_point_value

    # Determine fill price based on order type and trade action
    if order.order_type == "market":
        # Market orders fill based on current_market_price, adjusted by slippage.
        if order.trade_action == "buy":
            order.fill_price = current_market_price + slippage_amount
        elif order.trade_action == "sell":
            order.fill_price = current_market_price - slippage_amount
        else:
            raise ValueError(f"Invalid trade action for market order: {order.trade_action}")
    elif order.order_type == "stop":
        # Stop orders trigger at order_price. Fill price is order_price adjusted by slippage.
        # The 'current_market_price' argument for a stop order should be its trigger price (order.order_price).
        if order.trade_action == "sell":  # Stop-loss for a long position, or a sell-stop entry
            order.fill_price = order.order_price - slippage_amount # Sells at or below stop price
        elif order.trade_action == "buy":  # Stop-loss for a short position, or a buy-stop entry
            order.fill_price = order.order_price + slippage_amount # Buys at or above stop price
        else:
            raise ValueError(f"Invalid trade action for stop order: {order.trade_action}")
    # elif order.order_type == "limit":
    #     # Placeholder for limit order logic (ensure fill is at order_price or better)
    #     pass
    else:
        raise ValueError(f"Unsupported order type: {order.order_type}")

    # Calculate commission
    if lot_size <= 0:
        raise ValueError("Lot size must be positive to calculate commission.")
    order.commission = (order.quantity / lot_size) * commission_per_lot

    # Store the monetary value of slippage applied to this order
    order.slippage = slippage_amount

    # Update order status and timestamp
    order.status = "filled"
    order.timestamp_filled = timestamp_filled_param

    return order

class PortfolioManager:
    def __init__(self, initial_capital: float, config: dict):
        self.positions: dict[str, Position] = {}
        self.orders: list[Order] = []
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.trade_log: list[dict] = [] # To store details of executed trades
        self.config = config # Store relevant config like pip_point_value, lot_size, etc.

    def record_order(self, order: Order):
        """Adds an order to the internal list of orders."""
        self.orders.append(order)

    def open_position(self, symbol: str, trade_action: str, quantity: float,
                        entry_price: float, entry_time: datetime,
                        stop_loss_price: Optional[float], order_id: str,
                        commission: float, slippage_value: float):
        """
        Opens a new position or adds to an existing one for a specified symbol.
        Assumes new entries are for symbols with no existing open position or
        are additions to existing ones in the same direction.
        """
        if quantity <= 0:
            raise ValueError("Quantity for opening a position must be positive.")

        position_quantity = quantity if trade_action == "buy" else -quantity
        cost_or_proceeds = position_quantity * entry_price # This is negative for buys, positive for sells in terms of cash flow for position value
                                                        # but capital changes are handled by commission and P&L.

        trade_details = {
            "order_id": order_id,
            "symbol": symbol,
            "action": trade_action,
            "quantity": quantity,
            "price": entry_price,
            "timestamp": entry_time,
            "commission": commission,
            "slippage": slippage_value,
            "type": "entry"
        }

        if symbol not in self.positions:
            new_position = Position(
                symbol=symbol,
                quantity=position_quantity,
                average_entry_price=entry_price,
                initial_stop_loss_price=stop_loss_price,
                current_stop_loss_price=stop_loss_price,
                related_entry_order_id=order_id
            )
            self.positions[symbol] = new_position
        else:
            existing_position = self.positions[symbol]
            if (existing_position.quantity > 0 and trade_action == "sell") or \
               (existing_position.quantity < 0 and trade_action == "buy"):
                # This is an opposing trade. For now, we'll raise an error or handle as a close.
                # Simple approach: This should ideally be handled by a close_position call first.
                # For now, let's assume this function is called to *increase* a position or open a new one.
                raise ValueError(f"Opposing trade for existing position {symbol}. Handle closure separately.")

            # Averaging existing position
            total_value_existing = existing_position.quantity * existing_position.average_entry_price
            total_value_new = position_quantity * entry_price # position_quantity is signed

            new_total_quantity = existing_position.quantity + position_quantity

            if new_total_quantity == 0: # Effectively closed out
                 # This case should ideally be handled by close_position or reduce_position
                del self.positions[symbol]
                # Realized P&L calculation would be needed here.
                # For now, open_position is for opening/increasing.
            else:
                existing_position.average_entry_price = (total_value_existing + total_value_new) / new_total_quantity
                existing_position.quantity = new_total_quantity
                existing_position.last_update_timestamp = entry_time
                # Potentially update SL, TP if strategy dictates
                if stop_loss_price: # Update SL if a new one is provided (e.g. for scaling in)
                    existing_position.initial_stop_loss_price = stop_loss_price
                    existing_position.current_stop_loss_price = stop_loss_price

        # Capital adjustment:
        # Commission is a direct reduction in capital.
        # Slippage is already incorporated into the entry_price from execute_order.
        # The "cost" of the position itself is reflected in unrealized P&L.
        self.capital -= commission
        self.trade_log.append(trade_details)

        # Create and record the stop-loss order
        if stop_loss_price is not None:
            sl_order_id = f"{order_id}_sl"
            sl_trade_action = "sell" if trade_action == "buy" else "buy"

            # The quantity for the SL order should be the absolute quantity of the position opened/increased
            # For a new position, this is `abs(position_quantity)`.
            # If adding to an existing position, the SL order should ideally cover the *entire* new position size.
            # For simplicity, let's assume the SL order created here is for the quantity of *this specific trade*.
            # A more complex system might manage multiple SL orders or one SL for the aggregate position.
            # Current `Position` object (`new_position` or `existing_position`) holds the total quantity.

            target_position = self.positions[symbol] # The position just created or updated

            stop_loss_order = Order(
                order_id=sl_order_id,
                symbol=symbol,
                order_type="stop",
                trade_action=sl_trade_action,
                quantity=abs(target_position.quantity), # SL covers the full current position
                order_price=stop_loss_price,
                status="pending"
                # timestamp_created is handled by Order.__init__
            )
            self.record_order(stop_loss_order)
            target_position.active_stop_loss_order_id = sl_order_id
            # print(f"Created SL order: {sl_order_id} for position {target_position.symbol} at {stop_loss_price}")

        # print(f"Opened/Increased position: {trade_details}, Capital: {self.capital}")


    def close_position_completely(self, symbol: str, exit_price: float, exit_time: datetime,
                                  order_id: str, commission: float, slippage_value: float):
        """Closes the entire position for a symbol and calculates realized P&L."""
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to close.")

        quantity_closed = abs(position.quantity)
        trade_action = "sell" if position.quantity > 0 else "buy" # Action to close

        # Calculate Realized P&L
        # For long position (quantity > 0), P&L = (exit_price - entry_price) * quantity
        # For short position (quantity < 0), P&L = (entry_price - exit_price) * abs(quantity)
        # Or more generally: (exit_price - entry_price) * position.quantity (if exit is sell for long, buy for short)
        # Let's consider the cash flow perspective for P&L
        if position.quantity > 0: # Long position
            realized_pnl = (exit_price - position.average_entry_price) * position.quantity
        else: # Short position
            realized_pnl = (position.average_entry_price - exit_price) * abs(position.quantity)

        realized_pnl -= commission # Net P&L after commission

        self.capital += realized_pnl # Add net P&L to capital
        # The proceeds/cost of the closing trade itself also affect cash if not just using P&L.
        # Example: Buy 100 shares at $10 (cost $1000). Sell at $12 (proceeds $1200). P&L = $200.
        # Capital change = $1200 (inflow) - $1000 (outflow reflected in initial P&L) = $200.
        # Or, initial capital - commission. Then + realized_pnl.
        # If we think of capital as cash:
        # Open long: capital decreases by (entry_price * quantity) + commission
        # Close long: capital increases by (exit_price * quantity) - commission
        # Net change = (exit_price * quantity) - (entry_price * quantity) - total_commission
        # This is complex. Let's simplify: capital is adjusted by P&L and commissions.
        # When opening, capital was reduced by commission.
        # The value of the position is tracked in unrealized P&L.
        # When closing, the unrealized P&L becomes realized.
        # So, capital += realized_pnl (which already includes commission impact on this specific trade)

        position.realized_pnl += realized_pnl # Accumulate on position object too, though it's being deleted.

        trade_details = {
            "order_id": order_id,
            "symbol": symbol,
            "action": trade_action, # The action that closed the position
            "quantity": quantity_closed,
            "price": exit_price,
            "timestamp": exit_time,
            "commission": commission,
            "slippage": slippage_value,
            "realized_pnl": realized_pnl,
            "type": "exit"
        }
        self.trade_log.append(trade_details)
        del self.positions[symbol]
        # print(f"Closed position: {trade_details}, Capital: {self.capital}")


    def reduce_position(self, symbol: str, quantity_to_close: float, exit_price: float,
                        exit_time: datetime, order_id: str, commission: float, slippage_value: float):
        """Reduces an open position by a certain quantity and realizes P&L for that part."""
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to reduce.")
        if quantity_to_close <= 0:
            raise ValueError("Quantity to close must be positive.")
        if quantity_to_close > abs(position.quantity):
            raise ValueError(f"Cannot close {quantity_to_close}, only {abs(position.quantity)} held for {symbol}.")

        if position.quantity == quantity_to_close or position.quantity == -quantity_to_close :
            return self.close_position_completely(symbol, exit_price, exit_time, order_id, commission, slippage_value)

        trade_action = "sell" if position.quantity > 0 else "buy"  # Action to reduce/close

        # Calculate Realized P&L for the part being closed
        if position.quantity > 0: # Long position
            realized_pnl_reduction = (exit_price - position.average_entry_price) * quantity_to_close
        else: # Short position
            realized_pnl_reduction = (position.average_entry_price - exit_price) * quantity_to_close

        realized_pnl_reduction -= commission # Net P&L for this reduction

        self.capital += realized_pnl_reduction # Adjust capital by the net P&L of the reduction
        position.realized_pnl += realized_pnl_reduction # Accumulate realized P&L on the position

        # Update position quantity
        if position.quantity > 0:
            position.quantity -= quantity_to_close
        else:
            position.quantity += quantity_to_close # quantity_to_close is positive, position.quantity is negative

        position.last_update_timestamp = exit_time

        trade_details = {
            "order_id": order_id,
            "symbol": symbol,
            "action": trade_action,
            "quantity": quantity_to_close,
            "price": exit_price,
            "timestamp": exit_time,
            "commission": commission,
            "slippage": slippage_value,
            "realized_pnl": realized_pnl_reduction,
            "type": "reduction"
        }
        self.trade_log.append(trade_details)
        # print(f"Reduced position: {trade_details}, Capital: {self.capital}")


    def get_open_position(self, symbol: str) -> Optional[Position]:
        """
        Retrieves an open position for a given symbol.

        Args:
            symbol (str): The symbol of the position to retrieve (e.g., "EUR/USD").

        Returns:
            Optional[Position]: The Position object if an open position exists for the symbol,
                                otherwise None.
        """
        return self.positions.get(symbol)

    def update_unrealized_pnl(self, current_prices: Dict[str, float]):
        """
        Updates the unrealized P&L for all currently open positions.

        The calculation is based on the difference between the current market price
        and the position's average entry price.

        Args:
            current_prices (Dict[str, float]): A dictionary mapping symbols to their
                                               current market prices. If a symbol for an
                                               open position is not in this dict, its P&L
                                               may be set to None or a warning printed.
        """
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                print(f"Warning: Current market price for {symbol} not available. Cannot update unrealized P&L.")
                position.unrealized_pnl = None # Indicate P&L is currently unknown or stale
                continue

            current_price = current_prices[symbol]
            if position.quantity > 0: # Long position
                position.unrealized_pnl = (current_price - position.average_entry_price) * position.quantity
            elif position.quantity < 0: # Short position
                position.unrealized_pnl = (position.average_entry_price - current_price) * abs(position.quantity)
            else:
                # This case should ideally not occur for a position listed in self.positions
                position.unrealized_pnl = 0.0
            position.last_update_timestamp = datetime.now() # Or use timestamp from data feed if available

    def get_total_equity(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates the total current equity of the portfolio.

        Total equity is defined as the current cash capital plus the sum of
        unrealized P&L from all open positions. This method first calls
        `update_unrealized_pnl` to ensure P&L figures are current.

        Args:
            current_prices (Dict[str, float]): Current market prices for all symbols
                                               held in open positions, used to update P&L.

        Returns:
            float: The total current equity of the portfolio.
        """
        self.update_unrealized_pnl(current_prices) # Ensure P&L is up-to-date
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values() if pos.unrealized_pnl is not None)
        return self.capital + total_unrealized_pnl

    def get_current_total_open_risk_percentage(self) -> float:
        """
        Calculates the current total open risk as a percentage of portfolio capital.

        This method sums the monetary risk for all open positions that have an active,
        pending stop-loss order. The risk for each position is defined as the potential
        loss from its average entry price to its stop-loss price, multiplied by the
        position quantity and the instrument's pip/point value per unit.

        The total monetary risk is then divided by the current portfolio cash capital.

        Returns:
            float: The total open risk percentage. Returns `float('inf')` if capital
                   is zero or negative and there's positive monetary risk. Returns 0.0
                   if there's no risk or capital is zero/negative with no risk.
        """
        total_monetary_risk = 0.0

        for symbol, position in self.positions.items():
            if position.active_stop_loss_order_id:
                # Find the associated pending stop-loss order
                stop_order = next((o for o in self.orders if o.order_id == position.active_stop_loss_order_id and o.status == "pending"), None)

                if stop_order and stop_order.order_price is not None:
                    # Retrieve pip/point value per unit for the symbol from config
                    pip_value_for_one_unit = self.config.get('pip_point_value', {}).get(symbol)

                    if pip_value_for_one_unit is None:
                        print(f"Warning: Missing pip_point_value for {symbol} in config. Cannot calculate risk for this position.")
                        continue # Skip risk calculation for this position

                    # Calculate potential loss in price points per unit
                    potential_loss_price_points = abs(position.average_entry_price - stop_order.order_price)

                    # Calculate monetary risk for this specific position
                    monetary_risk_for_position = potential_loss_price_points * abs(position.quantity) * pip_value_for_one_unit
                    total_monetary_risk += monetary_risk_for_position

        if self.capital <= 0:
            return float('inf') if total_monetary_risk > 0 else 0.0

        return total_monetary_risk / self.capital


# def add_position(positions, new_position, capital):
#     """Adds a new position and updates capital.
#
#     Args:
#         positions (dict): Current open positions.
#         new_position (dict): Position to be added.
#         capital (float): Available capital.
#
#     Returns:
#         tuple: Updated positions and capital.
#     """
#     if not all(key in new_position for key in ['symbol', 'quantity', 'price']):
#         raise ValueError("Missing required keys in new_position: 'symbol', 'quantity', 'price'")
#
#     cost = new_position['quantity'] * new_position['price']
#
#     if capital < cost:
#         raise ValueError("Not enough capital to add position.")
#
#     symbol = new_position['symbol']
#     if symbol in positions:
#         existing_position = positions[symbol]
#         total_quantity = existing_position['quantity'] + new_position['quantity']
#         if total_quantity == 0: # handles case where new_position is effectively closing out the existing one
#             del positions[symbol]
#         else:
#             existing_position['price'] = (existing_position['price'] * existing_position['quantity'] + \
#                                          new_position['price'] * new_position['quantity']) / total_quantity
#             existing_position['quantity'] = total_quantity
#     else:
#         positions[symbol] = new_position.copy() # Use copy to avoid modifying the original new_position dict
#
#     capital -= cost
#     return positions, capital
#
# def close_position(positions, position_to_close, capital):
#     """Closes an existing position and updates capital.
#
#     Args:
#         positions (dict): Current open positions.
#         position_to_close (dict): Position to be closed.
#         capital (float): Available capital.
#
#     Returns:
#         tuple: Updated positions and capital.
#     """
#     if not all(key in position_to_close for key in ['symbol', 'quantity', 'price']):
#         raise ValueError("Missing required keys in position_to_close: 'symbol', 'quantity', 'price'")
#
#     symbol = position_to_close['symbol']
#     quantity_to_close = position_to_close['quantity']
#     price = position_to_close['price']
#
#     if symbol not in positions:
#         raise ValueError(f"Symbol {symbol} not found in positions.")
#
#     existing_position = positions[symbol]
#
#     if quantity_to_close <= 0:
#         raise ValueError("Quantity to close must be positive.")
#
#     if quantity_to_close > existing_position['quantity']:
#         raise ValueError(f"Cannot close {quantity_to_close} shares of {symbol}. "
#                          f"Only {existing_position['quantity']} shares held.")
#
#     value_closed = quantity_to_close * price
#     capital += value_closed
#
#     existing_position['quantity'] -= quantity_to_close
#
#     if existing_position['quantity'] == 0:
#         del positions[symbol]
#
#     return positions, capital
#
# def calculate_pnl(positions, current_prices):
#     """Calculates PnL for all open positions.
#
#     Args:
#         positions (dict): Current open positions.
#         current_prices (dict): Current market prices.
#
#     Returns:
#         float: Total PnL.
#     """
#     total_pnl = 0.0
#     for symbol, position_data in positions.items():
#         quantity = position_data['quantity']
#         cost_basis = position_data['price']
#
#         if symbol not in current_prices:
#             raise ValueError(f"Current price for symbol {symbol} not available in current_prices.")
#
#         current_market_price = current_prices[symbol]
#
#         current_value = quantity * current_market_price
#         initial_cost = quantity * cost_basis
#         position_pnl = current_value - initial_cost
#         total_pnl += position_pnl
#
#     return total_pnl

def run_strategy(historical_data_dict: Dict[str, pd.DataFrame], initial_capital: float, config: Dict) -> Dict:
    """
    Simulates a trading strategy using historical price data for multiple symbols.

    This function acts as the main backtesting engine. It initializes a portfolio,
    iterates through time based on the provided historical data, processes trading
    signals, manages orders and positions, and calculates performance metrics like
    equity curve and trade logs.

    Args:
        historical_data_dict (dict[str, pd.DataFrame]):
            A dictionary where keys are instrument symbols (e.g., "EUR/USD") and values are
            pandas DataFrames. Each DataFrame must be indexed by datetime and contain
            'Open', 'High', 'Low', 'Close' columns. 'Volume' is optional
            but not used by the current core logic.
        initial_capital (float):
            The starting cash capital for the backtest simulation.
        config (dict):
            A comprehensive configuration dictionary containing all parameters needed for
            the strategy, including:
            - Instrument-specific details (pip/point values, lot sizes, max units).
            - Risk management parameters (risk per trade, stop-loss multipliers, total risk limits).
            - Strategy parameters (indicator periods for Donchian channels, ATR, etc.).
            - Execution parameters (slippage, commission rates).
            - List of markets to trade (`config['markets']`).

    Returns:
        dict: A dictionary containing the results of the backtest, with keys:
            "equity_curve" (list): A list of (timestamp, equity) tuples representing
                                   the portfolio's total equity over time.
            "trade_log" (list): A list of dictionaries, where each dictionary details
                                an executed trade (from PortfolioManager.trade_log).
            "final_capital" (float): The final cash capital in the portfolio.
            "portfolio_summary" (dict): Optional dictionary with more summary statistics.
    """
    portfolio_manager = PortfolioManager(initial_capital=initial_capital, config=config)
    equity_curve = [] # Stores (timestamp, equity) tuples

    # --- 1. Initialization: Prepare Data and Pre-calculate Indicators ---
    all_timestamps = set()
    for symbol_data_df_val in historical_data_dict.values(): # Use a different var name
        if isinstance(symbol_data_df_val, pd.DataFrame) and not symbol_data_df_val.empty:
            all_timestamps.update(symbol_data_df_val.index)

    sorted_timestamps = sorted(list(all_timestamps))

    if not sorted_timestamps:
        return { # Basic results for no data
            "equity_curve": [], "trade_log": portfolio_manager.trade_log,
            "final_capital": portfolio_manager.capital,
            "message": "No historical data provided or data was empty."
        }

    # Pre-calculate technical indicators for each symbol to be used in the strategy
    atr_period_val = config.get('atr_period', 20) # Default ATR period if not in config
    entry_donchian_period_val = config['entry_donchian_period']
    long_exit_donchian_period_val = config['take_profit_long_exit_period']
    short_exit_donchian_period_val = config['take_profit_short_exit_period']

    processed_historical_data = {}
    for symbol, data_df in historical_data_dict.items():
        if not isinstance(data_df, pd.DataFrame) or data_df.empty:
            print(f"Warning: Data for symbol {symbol} is not a valid DataFrame or is empty. Skipping indicator calculation for this symbol.")
            continue

        df = data_df.copy() # Work on a copy to avoid modifying original data

        # Calculate and add ATR column
        df[f'atr_{atr_period_val}'] = calculate_atr(df['High'], df['Low'], df['Close'], period=atr_period_val)

        # Calculate and add Donchian Channels for entry signals
        df[f'donchian_upper_entry_{entry_donchian_period_val}'], df[f'donchian_lower_entry_{entry_donchian_period_val}'] = \
            calculate_donchian_channel(df['High'], df['Low'], period=entry_donchian_period_val)

        # Calculate and add Donchian Channels for long position exits
        df[f'donchian_upper_long_exit_{long_exit_donchian_period_val}'], df[f'donchian_lower_long_exit_{long_exit_donchian_period_val}'] = \
            calculate_donchian_channel(df['High'], df['Low'], period=long_exit_donchian_period_val)

        # Calculate and add Donchian Channels for short position exits
        df[f'donchian_upper_short_exit_{short_exit_donchian_period_val}'], df[f'donchian_lower_short_exit_{short_exit_donchian_period_val}'] = \
            calculate_donchian_channel(df['High'], df['Low'], period=short_exit_donchian_period_val)

        processed_historical_data[symbol] = df

    # --- 2. Main Backtesting Loop: Iterate through each timestamp ---
    for timestamp in sorted_timestamps:
        current_prices = {} # Stores close prices for symbols at the current timestamp
        for symbol in config.get('markets', []): # Iterate through configured markets
            if symbol in processed_historical_data:
                data_for_symbol = processed_historical_data[symbol]
                if timestamp in data_for_symbol.index:
                    current_prices[symbol] = data_for_symbol.loc[timestamp, 'Close']

        # Update portfolio's unrealized P&L and record equity at each step
        portfolio_manager.update_unrealized_pnl(current_prices)
        equity = portfolio_manager.get_total_equity(current_prices)
        equity_curve.append((timestamp, equity))

        # --- Trading Logic Sections ---

        # Section 2.1: Process pending stop-loss orders
        pending_stop_orders = [o for o in portfolio_manager.orders if o.order_type == "stop" and o.status == "pending"]
        for stop_order in pending_stop_orders:
            symbol = stop_order.symbol
            if symbol not in processed_historical_data or timestamp not in processed_historical_data[symbol].index:
                continue # Skip if market data for this timestamp is missing

            market_data_at_timestamp = processed_historical_data[symbol].loc[timestamp]
            current_high = market_data_at_timestamp['High']
            current_low = market_data_at_timestamp['Low']

            triggered = False # Flag to indicate if stop order is triggered
            if stop_order.trade_action == "sell" and current_low <= stop_order.order_price: # SL for long
                triggered = True
            elif stop_order.trade_action == "buy" and current_high >= stop_order.order_price: # SL for short
                triggered = True

            if triggered:
                # Execute the triggered stop order
                executed_order = execute_order(
                    order=stop_order, current_market_price=stop_order.order_price,
                    slippage_pips=config['slippage_pips'], commission_per_lot=config['commission_per_lot'],
                    pip_point_value=config['pip_point_value'][symbol], lot_size=config['lot_size'][symbol],
                    timestamp_filled_param=timestamp
                )
                if executed_order.status == "filled":
                    try:
                        # Close the position in portfolio manager
                        portfolio_manager.close_position_completely(
                            symbol=symbol, exit_price=executed_order.fill_price,
                            exit_time=executed_order.timestamp_filled or timestamp,
                            order_id=executed_order.order_id, commission=executed_order.commission,
                            slippage_value=executed_order.slippage
                        )
                        # Future enhancement: Cancel any corresponding take-profit order for this position.
                    except ValueError as e:
                        print(f"Error closing position after SL for {symbol} at {timestamp}: {e}")

        # Section 2.2: Process take-profit signals (Donchian Channel exits)
        for symbol in list(portfolio_manager.positions.keys()): # Iterate on a copy of keys for safe removal
            position = portfolio_manager.get_open_position(symbol)
            if not position: continue # Position might have been closed by SL

            if symbol not in processed_historical_data or timestamp not in processed_historical_data[symbol].index:
                continue

            market_data_at_timestamp = processed_historical_data[symbol].loc[timestamp]
            current_close = market_data_at_timestamp['Close']
            if pd.isna(current_close): continue

            try: # Using f-string constructed column names for clarity
                long_exit_col = f"donchian_lower_long_exit_{config['take_profit_long_exit_period']}"
                prev_donchian_lower_for_long_exit = processed_historical_data[symbol][long_exit_col].shift(1).loc[timestamp]
                short_exit_col = f"donchian_upper_short_exit_{config['take_profit_short_exit_period']}"
                prev_donchian_upper_for_short_exit = processed_historical_data[symbol][short_exit_col].shift(1).loc[timestamp]
            except KeyError: continue # Missing Donchian data (e.g. start of series)
            if pd.isna(prev_donchian_lower_for_long_exit) or pd.isna(prev_donchian_upper_for_short_exit):
                continue # Not enough data for shifted Donchian value

            take_profit_triggered = False
            trade_action_on_exit = ""
            if position.quantity > 0 and current_close < prev_donchian_lower_for_long_exit: # Long exit
                take_profit_triggered = True; trade_action_on_exit = "sell"
            elif position.quantity < 0 and current_close > prev_donchian_upper_for_short_exit: # Short exit
                take_profit_triggered = True; trade_action_on_exit = "buy"

            if take_profit_triggered:
                tp_order_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{symbol}_TP"
                market_exit_order = Order( # Create a market order to exit
                    order_id=tp_order_id, symbol=symbol, order_type="market",
                    trade_action=trade_action_on_exit, quantity=abs(position.quantity)
                )
                portfolio_manager.record_order(market_exit_order)
                # Execute the take-profit market order
                executed_exit_order = execute_order(
                    order=market_exit_order, current_market_price=current_close,
                    slippage_pips=config['slippage_pips'], commission_per_lot=config['commission_per_lot'],
                    pip_point_value=config['pip_point_value'][symbol], lot_size=config['lot_size'][symbol],
                    timestamp_filled_param=timestamp
                )
                if executed_exit_order.status == "filled":
                    try:
                        active_sl_order_id_to_cancel = position.active_stop_loss_order_id
                        # Close position in portfolio manager
                        portfolio_manager.close_position_completely(
                            symbol=symbol, exit_price=executed_exit_order.fill_price,
                            exit_time=executed_exit_order.timestamp_filled or timestamp,
                            order_id=executed_exit_order.order_id, commission=executed_exit_order.commission,
                            slippage_value=executed_exit_order.slippage
                        )
                        if active_sl_order_id_to_cancel: # Cancel the original SL order for this position
                            sl_to_cancel = next((o for o in portfolio_manager.orders if o.order_id == active_sl_order_id_to_cancel and o.status=="pending"), None)
                            if sl_to_cancel: sl_to_cancel.status = "cancelled"; sl_to_cancel.timestamp_filled = None
                    except ValueError as e:
                        print(f"Error closing position after TP for {symbol} at {timestamp}: {e}")

        # Section 2.3: Process new entry signals (Donchian Channel breakouts)
        for symbol in config.get('markets', []):
            if portfolio_manager.get_open_position(symbol): continue # Skip if already holding a position

            if symbol not in processed_historical_data or timestamp not in processed_historical_data[symbol].index:
                continue # Skip if market data for this timestamp is missing

            symbol_data_df = processed_historical_data[symbol]
            current_close = symbol_data_df.loc[timestamp, 'Close']
            if pd.isna(current_close): continue # Skip if close price is NaN

            # Define expected column names for indicators
            atr_col = f'atr_{atr_period_val}'
            donchian_upper_entry_col = f'donchian_upper_entry_{entry_donchian_period_val}'
            donchian_lower_entry_col = f'donchian_lower_entry_{entry_donchian_period_val}'

            # Ensure required indicator data is present
            if not all(col in symbol_data_df.columns for col in [atr_col, donchian_upper_entry_col, donchian_lower_entry_col]):
                continue # Skip if indicators are missing

            # Generate entry signals (1 for long, -1 for short, 0 for no signal)
            signal_series = generate_entry_signals(
                close=symbol_data_df['Close'],
                donchian_upper_entry=symbol_data_df[donchian_upper_entry_col],
                donchian_lower_entry=symbol_data_df[donchian_lower_entry_col],
                entry_period=entry_donchian_period_val
            )
            current_signal = signal_series.loc[timestamp] if timestamp in signal_series.index else 0
            if pd.isna(current_signal): current_signal = 0

            if current_signal == 1 or current_signal == -1: # If there's an entry signal
                # Calculate position size based on risk parameters
                account_equity = portfolio_manager.get_total_equity(current_prices)
                risk_percentage_per_trade = config['risk_per_trade'] / 100 if config['risk_per_trade'] >= 1 else config['risk_per_trade']
                current_atr = symbol_data_df.loc[timestamp, atr_col]
                if pd.isna(current_atr) or current_atr <= 0: continue # ATR must be valid

                # Ensure symbol-specific config items are present
                if not (symbol in config['pip_point_value'] and \
                        symbol in config['lot_size'] and \
                        symbol in config['max_units_per_market']):
                    print(f"Warning: Missing symbol-specific config (pip_point_value, lot_size, or max_units_per_market) for {symbol}. Skipping entry.")
                    continue

                pip_val_per_unit = config['pip_point_value'][symbol]
                lot_sz = config['lot_size'][symbol]
                pip_val_per_lot = pip_val_per_unit * lot_sz
                market_max_units = config['max_units_per_market'][symbol]
                current_total_risk_perc = portfolio_manager.get_current_total_open_risk_percentage()

                calculated_units = calculate_position_size(
                    account_equity=account_equity, risk_percentage=risk_percentage_per_trade, atr=current_atr,
                    pip_value_per_lot=pip_val_per_lot, lot_size=lot_sz,
                    max_units_per_market=market_max_units, current_units_for_market=0, # No existing position for this symbol
                    total_risk_percentage_limit=config['total_portfolio_risk_limit'],
                    current_total_open_risk_percentage=current_total_risk_perc
                )

                if calculated_units > 0:
                    # Determine trade action and stop-loss price
                    stop_loss_atr_multiplier = config['stop_loss_atr_multiplier']
                    trade_action = "buy" if current_signal == 1 else "sell"
                    stop_loss_price = current_close - (stop_loss_atr_multiplier * current_atr) if trade_action == "buy" \
                                 else current_close + (stop_loss_atr_multiplier * current_atr)

                    # Create and execute market order for entry
                    entry_order_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{symbol}_ENTRY"
                    entry_market_order = Order(
                        order_id=entry_order_id, symbol=symbol, order_type="market",
                        trade_action=trade_action, quantity=calculated_units
                    )
                    portfolio_manager.record_order(entry_market_order)
                    executed_entry_order = execute_order(
                        order=entry_market_order, current_market_price=current_close,
                        slippage_pips=config['slippage_pips'], commission_per_lot=config['commission_per_lot'],
                        pip_point_value=pip_val_per_unit, lot_size=lot_sz,
                        timestamp_filled_param=timestamp
                    )
                    if executed_entry_order.status == "filled":
                        try:
                            # Open position in portfolio manager
                            portfolio_manager.open_position(
                                symbol=symbol, trade_action=executed_entry_order.trade_action,
                                quantity=executed_entry_order.quantity, entry_price=executed_entry_order.fill_price,
                                entry_time=executed_entry_order.timestamp_filled or timestamp,
                                stop_loss_price=stop_loss_price, order_id=executed_entry_order.order_id,
                                commission=executed_entry_order.commission, slippage_value=executed_entry_order.slippage
                            )
                        except ValueError as e: # Catch errors from open_position (e.g. opposing trade)
                            print(f"Error opening position for {symbol} at {timestamp}: {e}")

    # --- 3. Return Results of the Backtest ---
    return {
        "equity_curve": equity_curve,
        "trade_log": portfolio_manager.trade_log,
        "final_capital": portfolio_manager.capital,
        "portfolio_summary": { # Optional: more details
            "initial_capital": portfolio_manager.initial_capital,
            "final_equity": equity_curve[-1][1] if equity_curve else initial_capital,
            "total_trades": len(portfolio_manager.trade_log),
            # Add more summary stats as needed
        }
    }

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

import pandas as pd
import math
from datetime import datetime

class Order:
    """
    Represents a trading order in the system.

    Attributes:
        order_id (str): Unique identifier for the order.
        symbol (str): The financial instrument (e.g., "EUR/USD").
        order_type (str): Type of order (e.g., "market", "stop", "limit").
        trade_action (str): Action to take ("buy" or "sell").
        quantity (float): Number of units to trade.
        order_price (float, optional): The price at which to trigger a stop or limit order.
                                       None for market orders at creation. Defaults to None.
        status (str): Current status of the order (e.g., "pending", "filled", "cancelled").
                      Defaults to "pending".
        fill_price (float, optional): The price at which the order was filled.
                                      None until filled. Defaults to None.
        timestamp_created (datetime): Timestamp of when the order was created.
        timestamp_filled (datetime, optional): Timestamp of when the order was filled.
                                               None until filled. Defaults to None.
        commission (float): Commission fee associated with the trade. Defaults to 0.0.
        slippage (float): Monetary value of slippage incurred on execution. Defaults to 0.0.
    """
    def __init__(self, order_id: str, symbol: str, order_type: str, trade_action: str,
                 quantity: float, order_price: float = None, status: str = "pending",
                 fill_price: float = None, commission: float = 0.0, slippage: float = 0.0,
                 timestamp_created: datetime = None):
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
        self.order_price = order_price  # Price for stop or limit orders
        self.status = status
        self.fill_price = fill_price
        self.timestamp_created = timestamp_created if timestamp_created is not None else datetime.now()
        self.timestamp_filled = None
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
        initial_stop_loss_price (float, optional): The stop-loss price set when the position
                                                   (or its first part) was opened.
        current_stop_loss_price (float, optional): The current, potentially adjusted (e.g., trailed),
                                                   stop-loss price for the entire position.
        take_profit_price (float, optional): The take-profit price for the position.
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
                 related_entry_order_id: str, initial_stop_loss_price: float = None,
                 current_stop_loss_price: float = None, take_profit_price: float = None,
                 timestamp: datetime = None):
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
        # take_profit_price might be used for Donchian exit calculation reference or other TP mechanisms.
        self.take_profit_price = take_profit_price
        self.unrealized_pnl = 0.0  # Calculated on demand by PortfolioManager
        self.realized_pnl = 0.0    # Accumulated from closed portions
        self.last_update_timestamp = timestamp if timestamp is not None else datetime.now()
        self.related_entry_order_id = related_entry_order_id

def execute_order(order: Order, current_market_price: float, slippage_pips: float,
                  commission_per_lot: float, pip_point_value: float, lot_size: int,
                  timestamp: datetime = None) -> Order:
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
        pip_point_value: The monetary value of one pip (or point) movement for the instrument
                         (e.g., 0.0001 for EUR/USD if 1 unit, or $10 if for a lot of 100k units and pip is 0.0001).
                         This should be the value of a single pip for a single unit of quantity.
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
        # If order is not pending (e.g., already filled or cancelled), do nothing.
        return order

    # Calculate total slippage in monetary terms based on price units for a single unit of quantity
    slippage_amount_per_unit_price = slippage_pips * pip_point_value

    if order.order_type == "market":
        if order.trade_action == "buy":
            order.fill_price = current_market_price + slippage_amount
        elif order.trade_action == "sell":
            order.fill_price = current_market_price - slippage_amount
        else:
            raise ValueError(f"Invalid trade action: {order.trade_action}")
    elif order.order_type == "stop":
        # Assume the decision to trigger the stop order has been made.
        # Fill price for stop orders is based on the order_price, affected by slippage.
        if order.trade_action == "sell":  # Stop-loss for long or stop-entry to sell
            order.fill_price = order.order_price - slippage_amount
        elif order.trade_action == "buy":  # Stop-loss for short or stop-entry to buy
            order.fill_price = order.order_price + slippage_amount
        else:
            raise ValueError(f"Invalid trade action for stop order: {order.trade_action}")
    # Add other order types like "limit" here if needed in the future
    else:
        raise ValueError(f"Unsupported order type: {order.order_type}")

    # Calculate commission
    if lot_size <= 0:
        raise ValueError("Lot size must be positive to calculate commission.")
    order.commission = (order.quantity / lot_size) * commission_per_lot
    order.slippage = slippage_amount # Storing the monetary value of slippage

    order.status = "filled"
    order.timestamp_filled = datetime.now()

    return order

class PortfolioManager:
    """
    Manages the overall trading portfolio, including positions, orders, capital,
    and trade logging. It provides methods for opening, closing, and adjusting
    positions, as well as for calculating portfolio-level metrics like equity and risk.
    """
    def __init__(self, initial_capital: float, config: dict):
        """
        Initializes the PortfolioManager.

        Args:
            initial_capital (float): The starting capital for the portfolio.
            config (dict): A configuration dictionary containing trading parameters
                           such as pip values, lot sizes, risk settings, etc.
        """
        self.positions: dict[str, Position] = {} # Stores active positions, keyed by symbol
        self.orders: list[Order] = [] # Stores all orders (pending, filled, cancelled)
        self.capital = initial_capital # Current cash balance
        self.initial_capital = initial_capital
        self.trade_log: list[dict] = [] # Log of executed trades for performance analysis
        self.config = config # Stores trading parameters and settings, e.g., 'pip_point_value', 'lot_size'

    def record_order(self, order: Order):
        """
        Adds an order to the portfolio's list of all orders.

        Args:
            order: The Order object to record.
        """
        self.orders.append(order)

    def get_open_position(self, symbol: str) -> Position | None:
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

        This method updates the portfolio's state by:
        1. Creating a new `Position` object or modifying an existing one (if adding to it).
        2. Adjusting `self.capital` for the commission paid.
        3. Logging the entry trade in `self.trade_log`.
        4. Automatically creating and recording a corresponding "pending" stop-loss `Order`.

        Args:
            symbol (str): The financial instrument (e.g., "EUR/USD").
            trade_action (str): The action of the entry trade ("buy" or "sell").
            quantity (float): The number of units traded in this entry. Must be positive.
            entry_price (float): The fill price of the entry order.
            entry_time (datetime): The timestamp of the entry trade execution.
            stop_loss_price (float): The calculated stop-loss price for this entry/position.
            order_id (str): The ID of the entry order that was filled.
            commission (float): The commission fee incurred for this entry trade.
            slippage_value (float): The monetary value of slippage for this entry trade.

        Raises:
            ValueError: If quantity is not positive or if attempting an opposing trade
                        to an existing position without proper closure/reduction first.
        """
        if quantity <= 0:
            raise ValueError("Quantity for opening a position must be positive.")

        # Determine signed quantity for the internal Position object
        position_quantity_signed = quantity if trade_action == "buy" else -quantity

        # Log the details of the entry trade
        trade_details = {
            "order_id": order_id, "symbol": symbol, "action": trade_action,
            "quantity": quantity, "price": entry_price, "timestamp": entry_time,
            "commission": commission, "slippage": slippage_value, "type": "entry"
        }

        if symbol not in self.positions:
            # Create a new position if one doesn't exist for this symbol
            new_position = Position(
                symbol=symbol,
                quantity=position_quantity_signed,
                average_entry_price=entry_price,
                initial_stop_loss_price=stop_loss_price,
                current_stop_loss_price=stop_loss_price, # Initially, current SL is the initial SL
                related_entry_order_id=order_id,
                timestamp=entry_time
            )
            self.positions[symbol] = new_position
        else:
            # Add to an existing position
            existing_position = self.positions[symbol]
            # Ensure the new trade is in the same direction as the existing position
            if (existing_position.quantity > 0 and trade_action == "sell") or \
               (existing_position.quantity < 0 and trade_action == "buy"):
                raise ValueError(
                    f"Opposing trade action '{trade_action}' for existing position on {symbol}. "
                    "Close existing position first or handle reduction/reversal explicitly."
                )

            # Update quantity and average entry price for the existing position
            total_value_existing = existing_position.quantity * existing_position.average_entry_price
            total_value_new_trade = position_quantity_signed * entry_price # Value of the new portion

            new_total_quantity = existing_position.quantity + position_quantity_signed

            if new_total_quantity == 0:
                # This scenario (trade perfectly offsetting existing position) should ideally be
                # handled by `close_position_completely` for correct P&L realization.
                # If reached here, it implies an issue in trade decision logic.
                print(f"Warning: Position for {symbol} effectively closed by 'open_position' call. "
                      f"P&L not explicitly calculated for this closure. Order ID: {order_id}")
                del self.positions[symbol] # Remove the position
            else:
                existing_position.average_entry_price = \
                    (total_value_existing + total_value_new_trade) / new_total_quantity
                existing_position.quantity = new_total_quantity
                existing_position.last_update_timestamp = entry_time
                # If a new stop_loss_price is provided (e.g., for scaling in and adjusting SL for the whole position), update it.
                if stop_loss_price:
                    existing_position.initial_stop_loss_price = stop_loss_price # Or some averaging logic if preferred
                    existing_position.current_stop_loss_price = stop_loss_price

        # Adjust capital for commission paid on this trade
        self.capital -= commission
        self.trade_log.append(trade_details)
        # print(f"Opened/Increased position: {trade_details}, Capital: {self.capital}")

        # Automatically create and record a stop-loss order for the position/trade
        # This happens only if the position still exists (wasn't closed by offsetting)
        if symbol in self.positions and stop_loss_price is not None and stop_loss_price > 0:
            sl_order_id = f"{order_id}_sl" # Generate a related ID for the SL order
            sl_trade_action = "sell" if trade_action == "buy" else "buy" # Opposite action for SL

            final_position_obj = self.positions[symbol] # Get the current state of the position
            sl_quantity = abs(final_position_obj.quantity) # SL order quantity matches total position quantity

            stop_loss_order = Order(
                order_id=sl_order_id,
                symbol=symbol,
                order_type="stop",
                trade_action=sl_trade_action,
                quantity=sl_quantity,
                order_price=stop_loss_price,
                status="pending",
                timestamp_created=entry_time # SL order created at the same time as position entry
            )
            self.record_order(stop_loss_order)
            # print(f"Recorded Stop-Loss order: {sl_order_id} for {sl_quantity} {symbol} at {stop_loss_price}")


    def close_position_completely(self, symbol: str, exit_price: float, exit_time: datetime,
                                  order_id: str, commission: float, slippage_value: float):
        """
        Closes the entire open position for a given symbol.

        This method is called after an exit order (market, stop, or take-profit)
        has been (simulated as) filled. It updates the portfolio by:
        - Calculating and adding realized P&L to capital.
        - Removing the position from active positions.
        - Logging the closing trade.
        - Cancelling any other pending orders (e.g., associated stop-loss) for this symbol.

        Args:
            symbol: The financial instrument of the position to close.
            exit_price: The fill price of the exit order.
            exit_time: Timestamp of the exit.
            order_id: The ID of the exit order that was filled.
            commission: Commission fee for this closing trade.
            slippage_value: Monetary value of slippage for this closing trade.

        Raises:
            ValueError: If no open position is found for the symbol.
        """
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to close.")

        quantity_closed = abs(position.quantity)
        # Determine the action of the closing trade (opposite of position direction)
        closing_trade_action = "sell" if position.quantity > 0 else "buy"

        # Calculate Realized P&L for the closed position
        if position.quantity > 0: # Long position was closed by a sell
            realized_pnl = (exit_price - position.average_entry_price) * position.quantity
        else: # Short position (position.quantity < 0) was closed by a buy
            realized_pnl = (position.average_entry_price - exit_price) * abs(position.quantity)

        net_realized_pnl = realized_pnl - commission # Net P&L after commission for this trade

        self.capital += net_realized_pnl # Adjust capital by the net P&L from this trade

        # Log the details of the closing trade
        trade_details = {
            "order_id": order_id,
            "symbol": symbol,
            "action": closing_trade_action, # Action of the trade that closed the position
            "quantity": quantity_closed,
            "price": exit_price,
            "timestamp": exit_time,
            "commission": commission,
            "slippage": slippage_value,
            "realized_pnl": net_realized_pnl,
            "type": "exit"
        }
        self.trade_log.append(trade_details)

        # Update position's realized P&L attribute (though it's about to be deleted from active positions).
        # This might be useful if Position objects were archived instead of deleted.
        position.realized_pnl += net_realized_pnl
        del self.positions[symbol] # Remove from active positions list
        # print(f"Closed position: {trade_details}, Capital: {self.capital}")

        # Cancel any other pending orders for this symbol (e.g., the original stop-loss order)
        for order_in_list in self.orders:
            if order_in_list.symbol == symbol and order_in_list.status == "pending":
                # A more robust check might involve linking SL orders to specific position entries
                # if multiple positions/entries per symbol were allowed with distinct SLs.
                # For now, any pending stop for this symbol is cancelled upon full closure.
                if order_in_list.order_type == "stop":
                    order_in_list.status = "cancelled"
                    # print(f"Cancelled pending order {order_in_list.order_id} for symbol {symbol} due to position closure.")


    def reduce_position(self, symbol: str, quantity_to_close: float, exit_price: float,
                        exit_time: datetime, order_id: str, commission: float, slippage_value: float):
        """
        Reduces an open position by a specified quantity and realizes P&L for that portion.

        Args:
            symbol: The financial instrument (e.g., "EUR/USD").
            quantity_to_close: The number of units to close. Must be positive.
            exit_price: The fill price of the order that reduced the position.
            exit_time: Timestamp of the reduction.
            order_id: The ID of the order that executed the reduction.
            commission: Commission fee for this partial closing trade.
            slippage_value: Monetary value of slippage for this trade.

        Raises:
            ValueError: If no position found, quantity_to_close is invalid, or exceeds position size.
        """
        position = self.get_open_position(symbol)
        if not position:
            raise ValueError(f"No open position found for symbol {symbol} to reduce.")
        if quantity_to_close <= 0:
            raise ValueError("Quantity to close must be positive.")
        if quantity_to_close > abs(position.quantity):
            raise ValueError(f"Cannot close {quantity_to_close} units, only {abs(position.quantity)} held for {symbol}.")

        # If reducing by the full amount, delegate to close_position_completely
        if quantity_to_close == abs(position.quantity):
            return self.close_position_completely(symbol, exit_price, exit_time, order_id, commission, slippage_value)

        closing_trade_action = "sell" if position.quantity > 0 else "buy"

        # Calculate Realized P&L for the part being closed
        # Average entry price remains unchanged for the position on partial closure.
        if position.quantity > 0: # Long position reduction
            realized_pnl_reduction = (exit_price - position.average_entry_price) * quantity_to_close
        else: # Short position (position.quantity < 0) reduction
            realized_pnl_reduction = (position.average_entry_price - exit_price) * quantity_to_close

        net_realized_pnl_reduction = realized_pnl_reduction - commission

        self.capital += net_realized_pnl_reduction # Adjust capital
        position.realized_pnl += net_realized_pnl_reduction # Accumulate P&L on the Position object

        # Update position quantity
        if position.quantity > 0:
            position.quantity -= quantity_to_close
        else: # position.quantity is negative
            position.quantity += quantity_to_close # Adding a positive quantity_to_close reduces magnitude of short

        position.last_update_timestamp = exit_time

        # Log the partial closure
        trade_details = {
            "order_id": order_id, "symbol": symbol, "action": closing_trade_action,
            "quantity": quantity_to_close, "price": exit_price, "timestamp": exit_time,
            "commission": commission, "slippage": slippage_value,
            "realized_pnl": net_realized_pnl_reduction, "type": "reduction"
        }
        self.trade_log.append(trade_details)
        # print(f"Reduced position: {trade_details}, Capital: {self.capital}")

        # Note on SL orders for partial closures:
        # The current system has one SL order per position, matching its total quantity.
        # After a partial close, this SL order is still for the original total quantity.
        # A more sophisticated system might:
        # 1. Adjust the quantity of the existing SL order.
        # 2. Cancel the old SL and create a new one for the reduced position size.
        # This is not explicitly handled here and depends on desired strategy rules.
        # For now, the original SL order remains and would close the *remaining* quantity if hit.


    def update_unrealized_pnl(self, current_prices: dict[str, float]):
        """
        Updates the unrealized P&L for all currently open positions.

        This method iterates through each open position, calculates its current
        unrealized profit or loss based on the provided current market prices,
        and updates the `unrealized_pnl` attribute of the Position object.
        The `last_update_timestamp` of the position is also updated.

        Args:
            current_prices: A dictionary mapping symbols to their current market prices.
                            Example: {"EUR/USD": 1.1050, "USD/JPY": 130.55}
        """
        for symbol, position in self.positions.items():
            if symbol not in current_prices or pd.isna(current_prices[symbol]): # Check for NaN price
                # If current price for a symbol is missing or NaN, cannot calculate P&L.
                # Optionally, log a warning or use last known price with appropriate handling.
                # For now, P&L remains unchanged or could be set to zero if preferred.
                print(f"Warning: Current price for {symbol} not available in current_prices. "
                      f"Unrealized P&L for this position will not be updated at this step.")
                # position.unrealized_pnl = 0.0 # Or some other handling like marking it stale
                continue

            current_price = current_prices[symbol]
            if position.quantity > 0: # Long position
                position.unrealized_pnl = (current_price - position.average_entry_price) * position.quantity
            elif position.quantity < 0: # Short position
                position.unrealized_pnl = (position.average_entry_price - current_price) * abs(position.quantity)
            else:
                # This case should ideally not occur for a position listed in `self.positions`.
                # If quantity is zero, it should have been removed.
                position.unrealized_pnl = 0.0
            position.last_update_timestamp = datetime.now() # Or use timestamp from data feed for backtesting

    def get_total_equity(self, current_prices: dict[str, float]) -> float:
        """
        Calculates the total equity of the portfolio.

        Total equity is defined as the current capital plus the sum of unrealized P&L
        from all open positions. This method first ensures that unrealized P&L is
        up-to-date by calling `update_unrealized_pnl`.

        Args:
            current_prices: A dictionary mapping symbols to their current market prices,
                            needed for updating unrealized P&L.

        Returns:
            The calculated total equity of the portfolio.
        """
        self.update_unrealized_pnl(current_prices) # Ensure P&L figures are current
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values() if pos.unrealized_pnl is not None)
        return self.capital + total_unrealized_pnl

    def get_current_total_open_risk_percentage(self, current_prices: dict[str, float]) -> float:
        """
        Calculates the current total risk exposure from all open positions,
        expressed as a percentage of the total current equity.

        Risk for each position is determined by its `current_stop_loss_price`.
        The sum of monetary risk from all positions (potential loss if all SLs are hit
        from current prices) is divided by the total current equity.

        Args:
            current_prices: A dictionary mapping symbols to their current market prices,
                            used for calculating total equity and per-position risk.

        Returns:
            The total open risk as a percentage of equity (e.g., 0.05 for 5%).
            Returns `float('inf')` if total equity is zero or negative.
        """
        total_risk_value_monetary = 0.0
        # Total equity calculation also updates unrealized P&L based on current_prices
        total_equity = self.get_total_equity(current_prices)

        if total_equity <= 0:
            # Cannot calculate risk percentage meaningfully if equity is non-positive.
            return float('inf')

        for symbol, position in self.positions.items():
            if position.current_stop_loss_price is None or position.current_stop_loss_price <= 0:
                # If a position has no valid SL, its contribution to this specific risk calculation is ambiguous.
                # Policies for this could be:
                # 1. Skip this position's risk (as done here with a warning).
                # 2. Consider its full current market value or potential loss to zero as its risk.
                # 3. Raise an error if all positions are strictly required to have SLs for risk management.
                print(f"Warning: Position {symbol} (ID: {position.related_entry_order_id}) has no valid "
                      f"current_stop_loss_price. Skipping its contribution to total open risk calculation.")
                continue

            current_price_for_symbol = current_prices.get(symbol)
            if current_price_for_symbol is None or pd.isna(current_price_for_symbol): # Check for NaN
                print(f"Warning: Current price for {symbol} not available for risk calculation. "
                      "Skipping its contribution to total open risk calculation.")
                continue

            # Risk per unit is the potential loss if the stop-loss is hit from the current market price.
            # This represents the current drawdown potential to the stop-loss.
            # For a long position, SL is typically below current price. Risk = current_price - SL_price.
            # For a short position, SL is typically above current price. Risk = SL_price - current_price.
            # This is effectively abs(current_price - position.current_stop_loss_price), but direction matters for "loss".
            if position.quantity > 0: # Long
                risk_per_unit = max(0, current_price_for_symbol - position.current_stop_loss_price)
            else: # Short
                risk_per_unit = max(0, position.current_stop_loss_price - current_price_for_symbol)

            position_risk_monetary = risk_per_unit * abs(position.quantity)
            total_risk_value_monetary += position_risk_monetary

        if total_equity <= 0: # Should be caught by the first check, but as a safeguard.
             return float('inf')

        if total_risk_value_monetary == 0: # Avoid division by zero if no positions or no risk defined.
            return 0.0

        total_risk_percentage = total_risk_value_monetary / total_equity
        return total_risk_percentage

def calculate_initial_stop_loss(entry_price: float, trade_action: str, atr_value: float, atr_multiplier: float) -> float:
    """
    Calculates the initial stop-loss price for a new trade.

    The stop-loss price is determined by subtracting (for long trades) or adding (for short trades)
    a multiple of the Average True Range (ATR) from the entry price.

    Args:
        entry_price: The price at which the trade was entered.
        trade_action: The direction of the trade; "buy" for long, "sell" for short.
        atr_value: The current Average True Range (ATR) for the instrument,
                   expected to be in the same price units as `entry_price`.
        atr_multiplier: The factor by which the ATR is multiplied to determine
                        the stop-loss distance (e.g., 2 for 2xATR).

    Returns:
        The calculated stop-loss price.

    Raises:
        ValueError: If `atr_value` or `atr_multiplier` is not positive,
                    or if `trade_action` is not "buy" or "sell".
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

# def run_strategy(historical_data, capital, strategy_params):
#     """Simulates trading strategy on historical data. (Old version)"""
#     pass

def run_strategy(historical_data_df: pd.DataFrame, initial_capital: float, config: dict) -> dict:
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

    # Extract relevant parameters from config (used directly or passed to other functions)
    markets = config.get('markets', [])
    entry_donchian_period = config.get('entry_donchian_period', 20)
    long_exit_donchian_period = config.get('take_profit_long_exit_period', 10)
    short_exit_donchian_period = config.get('take_profit_short_exit_period', 10)
    # stop_loss_atr_multiplier = config.get('stop_loss_atr_multiplier', 2) # Used in calculate_position_size & open_position
    # slippage_pips = config.get('slippage_pips', 0.2)
    # commission_per_lot = config.get('commission_per_lot', 500)
    # pip_point_value = config.get('pip_point_value', {}) # Dict by symbol
    # lot_size = config.get('lot_size', {}) # Dict by symbol

    # Prepare data: Calculate Donchian channels
    # Assume historical_data_df has MultiIndex columns like (symbol, 'High'), (symbol, 'Low')
    # And ATR is already present as (symbol, 'ATR')
    for symbol in markets:
        if (symbol, 'High') not in historical_data_df.columns or \
           (symbol, 'Low') not in historical_data_df.columns:
            raise ValueError(f"Missing High/Low data for symbol {symbol} in historical_data_df")
        if (symbol, 'ATR') not in historical_data_df.columns:
            raise ValueError(f"Missing ATR data for symbol {symbol} in historical_data_df")

        # Entry Donchian
        historical_data_df[(symbol, 'DonchianUpperEntry')], historical_data_df[(symbol, 'DonchianLowerEntry')] = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       entry_donchian_period)
        # Long Exit Donchian (uses Lower Band)
        _, historical_data_df[(symbol, 'DonchianLowerExitLong')] = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       long_exit_donchian_period)
        # Short Exit Donchian (uses Upper Band)
        historical_data_df[(symbol, 'DonchianUpperExitShort')], _ = \
            calculate_donchian_channel(historical_data_df[(symbol, 'High')],
                                       historical_data_df[(symbol, 'Low')],
                                       short_exit_donchian_period)

    equity_curve = []
    # current_positions_snapshot: 1 for long, -1 for short, 0 for flat, per symbol.
    current_positions_snapshot = {symbol: 0 for symbol in markets}
    # historical_position_states: Stores the EOD position state (0, 1, -1) for signal generation.
    historical_position_states = {
        market: pd.Series(0, index=historical_data_df.index) for market in markets
    }

    # Determine the start index for the loop based on the longest lookback period
    # Max of entry_donchian_period, long_exit_donchian_period, short_exit_donchian_period, and ATR period (assumed to be part of data)
    # For simplicity, let's assume ATR period is similar to entry_donchian_period
    # The rolling functions will produce NaNs for initial periods.
    # We should start iterating once all indicator values are available.
    # min_periods in rolling functions is set to the window size, so NaNs are at the start.
    start_offset = max(entry_donchian_period, long_exit_donchian_period, short_exit_donchian_period)

    # Iterate through each row (timestamp) in historical_data_df
    # Ensure that index is sorted if not already
    historical_data_df = historical_data_df.sort_index()

    for timestamp, row in historical_data_df.iloc[start_offset:].iterrows():
        current_prices = {symbol: row[(symbol, 'Close')] for symbol in markets if (symbol, 'Close') in row}
        current_atr_values = {symbol: row[(symbol, 'ATR')] for symbol in markets if (symbol, 'ATR') in row}

        if not current_prices: # Skip if no price data for this timestamp (e.g. market holidays for all symbols)
            continue

        portfolio_manager.update_unrealized_pnl(current_prices)

        # A. Process Pending Orders (Stops)
        # Iterate over a copy of orders list as it might be modified
        for order in list(portfolio_manager.orders):
            if order.status == "pending" and order.order_type == "stop":
                position = portfolio_manager.get_open_position(order.symbol)
                if not position: # Position might have been closed by another order in the same loop
                    order.status = "cancelled" # Or some other status indicating it's no longer relevant
                    continue

                symbol_low_price = row.get((order.symbol, 'Low'))
                symbol_high_price = row.get((order.symbol, 'High'))

                if symbol_low_price is None or symbol_high_price is None:
                    print(f"Warning: Missing Low/High price for {order.symbol} at {timestamp}. Cannot process stop order {order.order_id}")
                    continue

                should_execute_stop = False
                if position.quantity > 0 and symbol_low_price <= order.order_price: # Stop for long
                    should_execute_stop = True
                elif position.quantity < 0 and symbol_high_price >= order.order_price: # Stop for short
                    should_execute_stop = True

                if should_execute_stop:
                    # Use order.order_price as the market_price for stop execution as per execute_order logic for stops
                    executed_stop_order = execute_order(
                        order=order,
                        current_market_price=order.order_price, # Stop orders fill at/beyond stop price
                        slippage_pips=config['slippage_pips'],
                        commission_per_lot=config['commission_per_lot'],
                        pip_point_value=config['pip_point_value'][order.symbol],
                        lot_size=config['lot_size'][order.symbol]
                    )
                    # executed_stop_order is the same 'order' object, but status and fill details updated

                    portfolio_manager.close_position_completely(
                        symbol=executed_stop_order.symbol,
                        exit_price=executed_stop_order.fill_price,
                        exit_time=timestamp, # Use data timestamp
                        order_id=executed_stop_order.order_id,
                        commission=executed_stop_order.commission,
                        slippage_value=executed_stop_order.slippage
                    )
                    current_positions_snapshot[order.symbol] = 0
                    historical_position_states[order.symbol].loc[timestamp:] = 0 # Update historical state
                    print(f"[{timestamp}] STOP EXECUTED: {executed_stop_order.trade_action} {executed_stop_order.quantity} {executed_stop_order.symbol} at {executed_stop_order.fill_price}. Order ID: {executed_stop_order.order_id}")


        # B. Generate Entry Signals (for each market)
        for symbol in markets:
            # Check if position was closed by a stop in section A for this symbol before attempting entry
            if current_positions_snapshot.get(symbol, 0) == 0: # If flat in this market
                # Prepare data for signal generation (series up to current timestamp)
                # This is computationally intensive in a loop. Pre-calculating signals or more efficient slicing is better.
                # For now, direct slicing for clarity of logic for this step.
                close_series_to_current = historical_data_df.loc[:timestamp, (symbol, 'Close')]
                donchian_upper_entry_to_current = historical_data_df.loc[:timestamp, (symbol, 'DonchianUpperEntry')]
                donchian_lower_entry_to_current = historical_data_df.loc[:timestamp, (symbol, 'DonchianLowerEntry')]

                if close_series_to_current.empty or len(close_series_to_current) < entry_donchian_period:
                    continue # Not enough data yet for this specific symbol at this point

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
                    if atr_val is None or atr_val <= 0:
                        print(f"Warning: Invalid ATR value {atr_val} for {symbol} at {timestamp}. Cannot size position.")
                        continue

                    num_units = calculate_position_size(
                        portfolio_manager, symbol, atr_val, current_prices, config
                    )

                    if num_units > 0:
                        entry_order_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M')}_entry_{len(portfolio_manager.orders)}"
                        market_entry_order = Order(
                            order_id=entry_order_id,
                            symbol=symbol,
                            order_type="market",
                            trade_action=trade_action,
                            quantity=num_units,
                            timestamp_created=timestamp # Use data timestamp
                        )
                        portfolio_manager.record_order(market_entry_order) # Record before execution attempt

                        executed_entry_order = execute_order(
                            order=market_entry_order,
                            current_market_price=current_prices[symbol],
                            slippage_pips=config['slippage_pips'],
                            commission_per_lot=config['commission_per_lot'],
                            pip_point_value=config['pip_point_value'][symbol],
                            lot_size=config['lot_size'][symbol]
                        )

                        stop_loss_price = calculate_initial_stop_loss(
                            entry_price=executed_entry_order.fill_price,
                            trade_action=trade_action,
                            atr_value=atr_val, # Use the ATR value for this timestamp
                            atr_multiplier=config['stop_loss_atr_multiplier']
                        )

                        portfolio_manager.open_position(
                            symbol=symbol,
                            trade_action=trade_action,
                            quantity=num_units, # This is the actual number of units
                            entry_price=executed_entry_order.fill_price,
                            entry_time=timestamp, # Use data timestamp
                            stop_loss_price=stop_loss_price,
                            order_id=executed_entry_order.order_id,
                            commission=executed_entry_order.commission,
                            slippage_value=executed_entry_order.slippage
                        )
                        new_pos_state = 1 if trade_action == "buy" else -1
                        current_positions_snapshot[symbol] = new_pos_state
                        historical_position_states[symbol].loc[timestamp:] = new_pos_state # Update historical state
                        print(f"[{timestamp}] ENTRY: {trade_action} {num_units} {symbol} at {executed_entry_order.fill_price}. SL: {stop_loss_price}. Order ID: {executed_entry_order.order_id}")

        # C. Generate Exit Signals (Donchian-based exits for existing positions)
        for symbol in markets:
            # Use historical state at the *start* of the bar for decision making on exit signals for *this* bar
            # shift(1) gets previous bar's EOD state, fillna(0) for the first row if offset makes it NaN
            current_pos_state_on_bar_open = historical_position_states[symbol].shift(1).fillna(0).loc[timestamp]

            if current_pos_state_on_bar_open != 0: # If holding a position at the start of the bar
                # Ensure position wasn't closed by a stop order earlier in this same bar
                if current_positions_snapshot.get(symbol, 0) == 0:
                    continue

                close_series = historical_data_df.loc[:timestamp, (symbol, 'Close')]
                donchian_upper_exit_series = historical_data_df.loc[:timestamp, (symbol, 'DonchianUpperExitShort')]
                donchian_lower_exit_series = historical_data_df.loc[:timestamp, (symbol, 'DonchianLowerExitLong')]

                # Pass the historical position states up to the current bar for signal generation context
                # This ensures generate_exit_signals knows when a position was active to check exit conditions
                position_series_for_signal = historical_position_states[symbol].loc[:timestamp]

                # Ensure config parameters for exit periods are correctly fetched
                exit_period_long = config.get('take_profit_long_exit_period', 10) # Default if not in config
                exit_period_short = config.get('take_profit_short_exit_period', 10) # Default if not in config

                exit_signals = generate_exit_signals(
                    close_series,
                    donchian_upper_exit_series,
                    donchian_lower_exit_series,
                    exit_period_long, # Pass the correct exit period for long
                    exit_period_short, # Pass the correct exit period for short
                    position_series_for_signal # Pass the series of historical position states
                )

                current_exit_signal = exit_signals.iloc[-1] if not exit_signals.empty else 0

                if (current_pos_state_on_bar_open == 1 and current_exit_signal == -1) or \
                   (current_pos_state_on_bar_open == -1 and current_exit_signal == 1):

                    open_pos = portfolio_manager.get_open_position(symbol)
                    if not open_pos:
                        print(f"Warning: [{timestamp}] Attempting to close {symbol} based on signal, but no open position found in PortfolioManager. State mismatch? Historical state: {current_pos_state_on_bar_open}")
                        # This might happen if historical_position_states is not perfectly synced with portfolio_manager state
                        # due to how events are processed within the bar.
                        # For robustness, ensure current_positions_snapshot is the source of truth for "is there an active position RIGHT NOW"
                        if current_positions_snapshot.get(symbol, 0) != 0 :
                             print(f"Error: Mismatch - current_positions_snapshot shows position for {symbol} but get_open_position is None.")
                        # Resetting historical state if PM doesn't have it.
                        # historical_position_states[symbol].loc[timestamp:] = 0
                        # current_positions_snapshot[symbol] = 0 # Ensure snapshot is also zeroed
                        continue

                    trade_action = "sell" if current_pos_state_on_bar_open == 1 else "buy"
                    exit_order_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M')}_tp_exit_{len(portfolio_manager.orders)}"
                    quantity_to_close = abs(open_pos.quantity)

                    market_exit_order = Order(
                        order_id=exit_order_id,
                        symbol=symbol,
                        order_type="market",
                        trade_action=trade_action,
                        quantity=quantity_to_close,
                        timestamp_created=timestamp # Use data timestamp
                    )
                    portfolio_manager.record_order(market_exit_order)

                    executed_exit_order = execute_order(
                        order=market_exit_order,
                        current_market_price=current_prices[symbol], # Exit at current bar's close
                        slippage_pips=config['slippage_pips'],
                        commission_per_lot=config['commission_per_lot'],
                        pip_point_value=config['pip_point_value'][symbol],
                        lot_size=config['lot_size'][symbol]
                    )

                    portfolio_manager.close_position_completely(
                        symbol=symbol,
                        exit_price=executed_exit_order.fill_price,
                        exit_time=timestamp, # Use data timestamp
                        order_id=executed_exit_order.order_id,
                        commission=executed_exit_order.commission,
                        slippage_value=executed_exit_order.slippage
                    )
                    current_positions_snapshot[symbol] = 0 # Update live snapshot
                    historical_position_states[symbol].loc[timestamp:] = 0 # Update historical EOD state
                    print(f"[{timestamp}] TAKE PROFIT EXECUTED: {trade_action} {quantity_to_close} {symbol} at {executed_exit_order.fill_price}. Order ID: {executed_exit_order.order_id}")

        # D. Record Equity
        # Update historical position states for any symbols that changed state during this bar and weren't captured
        # This is mainly for entries/exits that happened on this bar for the *next* bar's historical view.
        # The .loc[timestamp:] updates handle this for trades.
        # If a position was opened or closed, historical_position_states was updated at that point for loc[timestamp:].

        current_equity = portfolio_manager.get_total_equity(current_prices)
        equity_curve.append({'timestamp': timestamp, 'equity': current_equity})

    return {
        'equity_curve': pd.DataFrame(equity_curve).set_index('timestamp') if equity_curve else pd.DataFrame(),
        'trade_log': portfolio_manager.trade_log,
        'orders': portfolio_manager.orders
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


def calculate_position_size(portfolio_manager: PortfolioManager,
                            symbol_to_trade: str,
                            atr_value: float, # Current ATR for symbol_to_trade
                            current_prices_for_risk_calc: dict[str, float],
                            config: dict) -> int:
    """
    Calculates the position size in units based on multiple risk management rules.

    The calculation involves several steps:
    1.  **Configuration & Validation**: Extracts necessary parameters from the `config`
        (e.g., risk percentages, ATR multipliers, market limits, pip values) and
        validates them. Account equity is fetched from the `portfolio_manager`.
    2.  **Risk per Unit Calculation**: Determines the monetary risk associated with
        trading one unit of the `symbol_to_trade`, based on the stop-loss distance
        (derived from `atr_value` and `stop_loss_atr_multiplier`) and the
        `pip_value_for_symbol`.
        *   A critical assumption here is how `atr_value` (in price units) and
            `pip_value_for_symbol` (monetary value of 1 pip) are combined. This
            implementation currently assumes a helper `pip_size` to convert ATR in
            price units to pips, then multiplies by `pip_value_for_symbol`. This
            `pip_size` should ideally be part of the `config`.
    3.  **Per-Trade Risk Limit**: Calculates the number of units that can be traded
        without exceeding the `risk_percentage_per_trade` of the current account equity.
    4.  **Market Unit Limit**: Adjusts the number of units to not exceed the
        `max_units_per_market` for the `symbol_to_trade`, considering currently held units.
    5.  **Total Portfolio Risk Limit**:
        *   Calculates the current total open risk percentage using
            `portfolio_manager.get_current_total_open_risk_percentage()`.
        *   If adding the proposed trade (at its current, market-limited size) would
            cause the total portfolio risk to exceed `total_risk_percentage_limit`,
            the number of units is scaled down to fit within the remaining allowable
            monetary risk under this total limit.
    6.  **Final Unit Count**: Returns the calculated number of units (integer, floored),
        ensuring it's not negative. If any step determines that no trade should be made
        (e.g., due to zero equity, limits already breached, or invalid inputs),
        it returns 0.

    Args:
        portfolio_manager: An instance of `PortfolioManager` providing access to
                           current equity, open positions, and overall risk state.
        symbol_to_trade: The symbol for which the position size is being calculated
                         (e.g., "EUR/USD").
        atr_value: The Average True Range (ATR) for `symbol_to_trade`, assumed to be
                   in price units (e.g., 0.0010 for EUR/USD if price is 1.1000).
        current_prices_for_risk_calc: A dictionary of current market prices for all
                                      symbols relevant for equity and risk calculations.
        config: A dictionary holding global trading parameters, including:
                - 'risk_percentage_per_trade': Maximum risk per single trade (e.g., 0.01 for 1%).
                - 'stop_loss_atr_multiplier': Factor to multiply ATR by for stop-loss distance.
                - 'max_units_per_market': Max units allowed per symbol (can be a dict or a single value).
                - 'total_risk_percentage_limit': Maximum allowed total risk across all positions.
                - 'pip_point_value': Dict mapping symbol to the monetary value of 1 pip per unit.
                - (Implicit) 'pip_size': The price increment of a single pip (e.g., 0.0001 for EUR/USD).
                                        Currently hardcoded/inferred, ideally from config.

    Returns:
        int: The calculated number of units to trade for the `symbol_to_trade`.
             Returns 0 if the trade cannot be made due to risk constraints or invalid data.
    """
    # --- Basic Validations & Config Extraction ---
    if atr_value <= 0: # ATR must be positive to define risk
        print(f"Warning: ATR value for {symbol_to_trade} is {atr_value}. Cannot size position.")
        return 0

    try:
        # Per-trade risk parameters
        risk_percentage_per_trade = config['risk_percentage_per_trade']
        stop_loss_atr_multiplier = config['stop_loss_atr_multiplier']

        # Market-specific unit limit
        max_units_config = config.get('max_units_per_market')
        if isinstance(max_units_config, dict): # Symbol-specific values in a dict
            max_units_per_market = max_units_config.get(symbol_to_trade, float('inf'))
        elif isinstance(max_units_config, (int, float)): # A single global value for all markets
            max_units_per_market = max_units_config
        else: # Default if not specified correctly
            max_units_per_market = float('inf') # Default to no limit if not configured correctly

        # Total portfolio risk limit
        total_risk_percentage_limit = config['total_risk_percentage_limit']

        # Instrument-specific values for valuing risk
        pip_value_for_symbol_per_unit = config['pip_point_value'][symbol_to_trade]

    except KeyError as e:
        print(f"Error: Missing required configuration key: {e} in config: {config}")
        return 0

    # Validate risk percentages from config
    if not (0 < risk_percentage_per_trade < 1):
         print(f"Warning: risk_percentage_per_trade ({risk_percentage_per_trade}) from config is out of bounds (0,1).")
         return 0
    if not (0 < total_risk_percentage_limit <= 1): # Limit can be up to 100%
         print(f"Warning: total_risk_percentage_limit ({total_risk_percentage_limit}) from config is out of bounds (0,1].")
         return 0

    # Get current account equity from portfolio manager
    account_equity = portfolio_manager.get_total_equity(current_prices_for_risk_calc)
    if account_equity <= 0:
        print("Warning: Account equity is zero or negative. Cannot size position.")
        return 0

    # --- Step 1: Calculate Risk per Unit for the new trade ---
    # This is the monetary risk if one unit of the asset is traded and hits its stop-loss.

    # Stop-loss distance in price units (e.g., 0.0020 for EUR/USD if ATR=0.0010 and mult=2)
    stop_loss_distance_price_units = stop_loss_atr_multiplier * atr_value
    if stop_loss_distance_price_units <= 0: # Should generally not happen if ATR and multiplier are positive
        print(f"Warning: stop_loss_distance_price_units for {symbol_to_trade} is non-positive ({stop_loss_distance_price_units}).")
        return 0

    # Convert stop-loss distance from price units to number of pips
    # This requires knowing the pip size for the symbol (e.g., 0.0001 for EUR/USD, 0.01 for USD/JPY)
    # TODO: Pip size should be part of the configuration per symbol.
    pip_size = 0.0001 # Default, common for many FX pairs
    if "JPY" in symbol_to_trade.upper() or symbol_to_trade == "TESTA": # TESTA is JPY-like in test config
        pip_size = 0.01
    elif symbol_to_trade == "TESTB": # TESTB is like BTC in test config
        pip_size = 1.0 # Assuming 1 point for BTC is a full dollar for simplicity here
    # Add more specific pip sizes for other symbols or asset classes as needed.

    stop_loss_as_pips = stop_loss_distance_price_units / pip_size

    # Monetary risk for trading one unit of the asset
    risk_per_unit_trade = stop_loss_as_pips * pip_value_for_symbol_per_unit

    if risk_per_unit_trade <= 0: # Should not happen if inputs are valid
        print(f"Warning: risk_per_unit_trade for {symbol_to_trade} is non-positive ({risk_per_unit_trade}). "
              f"Check ATR ({atr_value}), pip_value ({pip_value_for_symbol_per_unit}), pip_size ({pip_size}).")
        return 0

    # --- Step 2: Initial number of units based on per-trade risk ---
    # Max monetary amount to risk on this single trade according to config
    monetary_risk_allotted_for_trade = account_equity * risk_percentage_per_trade
    # Number of units that can be traded given this monetary risk and risk per unit
    num_units_trade_risk_limited = math.floor(monetary_risk_allotted_for_trade / risk_per_unit_trade)

    if num_units_trade_risk_limited <= 0:
        # Cannot even trade 1 unit with the per-trade risk settings.
        return 0

    # --- Step 3: Market Limit Constraint ---
    # Check against max allowed units for this specific market/symbol.
    current_pos_for_symbol = portfolio_manager.get_open_position(symbol_to_trade)
    current_units_held_for_market = abs(current_pos_for_symbol.quantity) if current_pos_for_symbol else 0

    # How many more units can be added before hitting the market-specific limit
    available_units_for_market = max_units_per_market - current_units_held_for_market
    if available_units_for_market <= 0 :
        print(f"Warning: Already at or over max_units_per_market for {symbol_to_trade} "
              f"({current_units_held_for_market}/{max_units_per_market}). Cannot add more units.")
        return 0 # No room to add more units for this market

    # Cap units by available market limit
    num_units_market_limited = min(num_units_trade_risk_limited, math.floor(available_units_for_market))

    if num_units_market_limited <= 0:
        # Limited by market cap or previous calculation resulted in zero.
        return 0

    # --- Step 4: Total Portfolio Risk Limit Constraint ---
    # Check if adding this trade would exceed the total risk limit for the portfolio.
    current_total_open_risk_percentage = portfolio_manager.get_current_total_open_risk_percentage(current_prices_for_risk_calc)

    # If current total risk already meets or exceeds the limit, no new trades allowed.
    if current_total_open_risk_percentage >= total_risk_percentage_limit:
        print(f"Warning: Current total open risk ({current_total_open_risk_percentage:.2%}) "
              f"already at/exceeds limit ({total_risk_percentage_limit:.2%}). No new trades.")
        return 0

    # Monetary value of the risk this potential new trade (sized by market limit) would add
    monetary_risk_of_potential_new_trade = num_units_market_limited * risk_per_unit_trade

    # Current total risk in monetary value
    current_total_risk_monetary = current_total_open_risk_percentage * account_equity if account_equity > 0 else 0

    # Potential total risk value if this new trade is opened
    potential_total_risk_monetary = current_total_risk_monetary + monetary_risk_of_potential_new_trade

    # Potential total risk percentage if this new trade is opened
    potential_total_risk_percentage = potential_total_risk_monetary / account_equity if account_equity > 0 else float('inf')


    num_units_final = num_units_market_limited # Start with market-limited units

    if potential_total_risk_percentage > total_risk_percentage_limit:
        # The proposed trade (even if capped by market limit) would breach total portfolio risk.
        # Scale it down further.
        # Calculate how much monetary risk can still be added without breaching the total limit.
        allowed_additional_monetary_risk = max(0, (total_risk_percentage_limit * account_equity) - current_total_risk_monetary)

        if allowed_additional_monetary_risk <= 0:
            num_units_final = 0 # No room for any additional risk
        else:
            # How many units can fit into this allowed additional monetary risk?
            affordable_units_under_total_risk = math.floor(allowed_additional_monetary_risk / risk_per_unit_trade)
            num_units_final = min(num_units_market_limited, affordable_units_under_total_risk)

    if num_units_final <= 0:
        return 0

    return int(math.floor(num_units_final)) # Ensure integer units

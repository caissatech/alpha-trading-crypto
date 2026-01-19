"""Backtest engine for strategy testing."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.infrastructure.exceptions import BacktestError, InvalidDataError


class BacktestResult(BaseModel):
    """
    Backtest result.

    Contains performance metrics and trade history.
    """

    initial_capital: float = Field(..., description="Initial capital")
    final_capital: float = Field(..., description="Final capital")
    total_return: float = Field(..., description="Total return (percentage)")
    total_pnl: float = Field(..., description="Total PnL")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown (percentage)")
    win_rate: float = Field(..., description="Win rate (percentage)")
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(..., description="Number of winning trades")
    losing_trades: int = Field(..., description="Number of losing trades")
    average_win: float = Field(..., description="Average winning trade PnL")
    average_loss: float = Field(..., description="Average losing trade PnL")
    profit_factor: float = Field(..., description="Profit factor (gross profit / gross loss)")
    equity_curve: List[float] = Field(default_factory=list, description="Equity curve over time")
    trades: List[Dict[str, Any]] = Field(default_factory=list, description="Trade history")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")


class BacktestEngine:
    """
    Backtest engine.

    Simulates trading strategies with historical data.
    """

    def __init__(
        self,
        slippage: float = 0.001,
        commission: float = 0.0002,
        funding_rate: float = 0.0001,
    ) -> None:
        """
        Initialize backtest engine.

        Args:
            slippage: Slippage percentage (default 0.1%)
            commission: Commission percentage per trade (default 0.02%)
            funding_rate: Funding rate per 8 hours (default 0.01%)
        """
        self.slippage = slippage
        self.commission = commission
        self.funding_rate = funding_rate

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float = 100000.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestResult:
        """
        Run backtest.

        Args:
            prices: DataFrame with columns: timestamp, symbol, open, high, low, close, volume
            signals: DataFrame with columns: timestamp, symbol, side (BUY/SELL), quantity
            initial_capital: Initial capital
            start_date: Start date (if None, use first date in prices)
            end_date: End date (if None, use last date in prices)

        Returns:
            BacktestResult with performance metrics

        Raises:
            InvalidDataError: If data format is invalid
            BacktestError: If backtest fails
        """
        # Validate inputs
        self._validate_data(prices, signals)

        # Filter by date range
        if start_date:
            prices = prices[prices["timestamp"] >= start_date]
            signals = signals[signals["timestamp"] >= start_date]
        if end_date:
            prices = prices[prices["timestamp"] <= end_date]
            signals = signals[signals["timestamp"] <= end_date]

        if len(prices) == 0:
            raise BacktestError("No price data in date range")

        # Initialize state
        capital = initial_capital
        positions: Dict[str, Position] = {}
        trades: List[Dict[str, Any]] = []
        equity_curve: List[float] = [initial_capital]
        pnl_history: List[float] = []

        # Sort by timestamp
        prices = prices.sort_values("timestamp")
        signals = signals.sort_values("timestamp")

        # Process each timestamp
        for timestamp in prices["timestamp"].unique():
            # Get current prices
            current_prices = prices[prices["timestamp"] == timestamp]

            # Update positions with current mark prices
            for symbol, position in positions.items():
                price_data = current_prices[current_prices["symbol"] == symbol]
                if len(price_data) > 0:
                    mark_price = float(price_data.iloc[0]["close"])
                    position.mark_price = mark_price
                    position.update_pnl()

            # Process signals for this timestamp
            current_signals = signals[signals["timestamp"] == timestamp]
            for _, signal in current_signals.iterrows():
                symbol = signal["symbol"]
                side = OrderSide(signal["side"])
                quantity = float(signal["quantity"])

                # Get current price
                price_data = current_prices[current_prices["symbol"] == symbol]
                if len(price_data) == 0:
                    continue

                current_price = float(price_data.iloc[0]["close"])

                # Execute order with slippage
                execution_price = self._apply_slippage(current_price, side, quantity)

                # Calculate cost
                cost = execution_price * quantity
                commission_cost = cost * self.commission
                total_cost = cost + commission_cost

                # Check if we have enough capital
                if side == OrderSide.BUY and total_cost > capital:
                    continue  # Skip if insufficient capital

                # Update position
                position = positions.get(symbol)
                if position is None:
                    # Open new position
                    position = Position(
                        symbol=symbol,
                        size=quantity if side == OrderSide.BUY else -quantity,
                        entry_price=execution_price,
                        mark_price=execution_price,
                    )
                    positions[symbol] = position
                else:
                    # Update existing position
                    if side == OrderSide.BUY:
                        new_size = position.size + quantity
                    else:
                        new_size = position.size - quantity

                    # Calculate realized PnL if closing/reducing position
                    if (position.size > 0 and new_size < position.size) or (position.size < 0 and new_size > position.size):
                        closed_size = abs(position.size - new_size)
                        realized_pnl = closed_size * (execution_price - position.entry_price)
                        position.realized_pnl += realized_pnl
                        capital += realized_pnl

                        # Record trade
                        trades.append(
                            {
                                "timestamp": timestamp,
                                "symbol": symbol,
                                "side": side.value,
                                "quantity": closed_size,
                                "entry_price": position.entry_price,
                                "exit_price": execution_price,
                                "pnl": realized_pnl,
                                "commission": commission_cost,
                            }
                        )

                    # Update position
                    if abs(new_size) < 1e-8:
                        del positions[symbol]
                    else:
                        # Update average entry price
                        if (position.size > 0 and new_size > position.size) or (position.size < 0 and new_size < position.size):
                            # Adding to position
                            total_cost_old = abs(position.size) * position.entry_price
                            total_cost_new = quantity * execution_price
                            position.entry_price = (total_cost_old + total_cost_new) / abs(new_size)

                        position.size = new_size
                        position.mark_price = execution_price
                        position.update_pnl()

                # Update capital
                if side == OrderSide.BUY:
                    capital -= total_cost
                else:
                    capital += cost - commission_cost

            # Apply funding costs (every 8 hours)
            if len(equity_curve) % 3 == 0:  # Approximate 8 hours
                for position in positions.values():
                    funding_cost = abs(position.size) * position.mark_price * self.funding_rate
                    if position.size > 0:
                        capital -= funding_cost
                    else:
                        capital += funding_cost
                    position.funding_paid += funding_cost

            # Calculate total equity
            total_equity = capital
            for position in positions.values():
                total_equity += position.unrealized_pnl

            equity_curve.append(total_equity)
            pnl_history.append(total_equity - initial_capital)

        # Calculate final capital
        final_capital = equity_curve[-1] if equity_curve else initial_capital

        # Calculate metrics
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        total_pnl = final_capital - initial_capital

        # Calculate Sharpe ratio
        if len(pnl_history) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # Calculate max drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0

        # Calculate trade statistics
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] < 0]
        total_trades = len(trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
        average_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0.0
        average_loss = np.mean([t["pnl"] for t in losing_trades]) if losing_trades else 0.0

        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl"] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # Get date range
        if start_date is None:
            start_date = prices["timestamp"].min()
        if end_date is None:
            end_date = prices["timestamp"].max()

        return BacktestResult(
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            equity_curve=equity_curve,
            trades=trades,
            start_date=start_date,
            end_date=end_date,
        )

    def _validate_data(self, prices: pd.DataFrame, signals: pd.DataFrame) -> None:
        """
        Validate input data.

        Args:
            prices: Price DataFrame
            signals: Signals DataFrame

        Raises:
            InvalidDataError: If data format is invalid
        """
        # Validate prices
        required_price_columns = ["timestamp", "symbol", "close"]
        missing_columns = [col for col in required_price_columns if col not in prices.columns]
        if missing_columns:
            raise InvalidDataError(f"Missing required columns in prices: {missing_columns}", data={"prices": list(prices.columns)})

        # Validate signals
        required_signal_columns = ["timestamp", "symbol", "side", "quantity"]
        missing_columns = [col for col in required_signal_columns if col not in signals.columns]
        if missing_columns:
            raise InvalidDataError(f"Missing required columns in signals: {missing_columns}", data={"signals": list(signals.columns)})

        # Validate data types
        if not pd.api.types.is_datetime64_any_dtype(prices["timestamp"]):
            try:
                prices["timestamp"] = pd.to_datetime(prices["timestamp"])
            except Exception as e:
                raise InvalidDataError(f"Invalid timestamp format in prices: {e}", data={"prices": prices.head()}) from e

        if not pd.api.types.is_datetime64_any_dtype(signals["timestamp"]):
            try:
                signals["timestamp"] = pd.to_datetime(signals["timestamp"])
            except Exception as e:
                raise InvalidDataError(f"Invalid timestamp format in signals: {e}", data={"signals": signals.head()}) from e

        # Validate side values
        valid_sides = ["BUY", "SELL"]
        invalid_sides = signals[~signals["side"].isin(valid_sides)]
        if len(invalid_sides) > 0:
            raise InvalidDataError(f"Invalid side values: {invalid_sides['side'].unique()}", data={"signals": invalid_sides.head()})

    def _apply_slippage(self, price: float, side: OrderSide, quantity: float) -> float:
        """
        Apply slippage to execution price.

        Args:
            price: Base price
            side: Order side
            quantity: Order quantity

        Returns:
            Execution price with slippage
        """
        slippage_factor = self.slippage * (1 + quantity / 100)  # Slippage increases with quantity
        if side == OrderSide.BUY:
            return price * (1 + slippage_factor)  # Pay more when buying
        else:
            return price * (1 - slippage_factor)  # Receive less when selling


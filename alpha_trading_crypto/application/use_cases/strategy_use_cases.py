"""Strategy use cases."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

from alpha_trading_crypto.application.ports.backtest_port import BacktestPort
from alpha_trading_crypto.application.ports.exchange_port import ExchangePort
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager
from alpha_trading_crypto.infrastructure.backtest.backtest_engine import BacktestResult
from alpha_trading_crypto.infrastructure.exceptions import BacktestError, InvalidDataError

logger = structlog.get_logger()


class ExecuteStrategy:
    """
    Execute strategy use case.

    Executes a trading strategy live on the exchange.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
        position_manager: PositionManager,
    ) -> None:
        """
        Initialize ExecuteStrategy use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
            position_manager: Position manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager

    async def execute(
        self,
        signals: List[Dict[str, Any]],
    ) -> List[Order]:
        """
        Execute strategy with given signals.

        Args:
            signals: List of signal dictionaries with keys: symbol, side, quantity, price (optional)

        Returns:
            List of placed Order entities

        Raises:
            ValueError: If signals are invalid
            APIError: If order placement fails
        """
        logger.info("Executing strategy", signal_count=len(signals))

        placed_orders = []

        for signal in signals:
            try:
                symbol = signal.get("symbol")
                side_str = signal.get("side")
                quantity = signal.get("quantity")
                price = signal.get("price")
                order_type_str = signal.get("order_type", "MARKET")

                if not symbol or not side_str or not quantity:
                    logger.warning("Invalid signal, skipping", signal=signal)
                    continue

                # Parse side
                try:
                    side = OrderSide(side_str.upper())
                except ValueError:
                    logger.warning("Invalid side, skipping", side=side_str)
                    continue

                # Parse order type
                try:
                    order_type = OrderType(order_type_str.upper())
                except ValueError:
                    order_type = OrderType.MARKET

                # Place order
                order = await self.exchange.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=float(quantity),
                    order_type=order_type,
                    price=float(price) if price else None,
                )

                # Track order
                self.order_manager.add_order(order)
                placed_orders.append(order)

                logger.info("Order placed from strategy", order_id=order.id, symbol=symbol)

            except Exception as e:
                logger.error("Failed to execute signal", error=str(e), signal=signal)
                continue

        logger.info("Strategy execution completed", orders_placed=len(placed_orders))

        return placed_orders

    async def update_positions(self) -> None:
        """
        Update positions from exchange.

        Raises:
            APIError: If position update fails
        """
        logger.info("Updating positions")

        try:
            positions = await self.exchange.get_positions()

            for position in positions:
                existing_position = self.position_manager.get_position(position.symbol)
                if existing_position:
                    self.position_manager.update_position(
                        position.symbol,
                        size=position.size,
                        mark_price=position.mark_price,
                        funding_rate=position.funding_rate,
                    )
                else:
                    self.position_manager.add_position(position)

            logger.info("Positions updated", count=len(positions))

        except Exception as e:
            logger.error("Failed to update positions", error=str(e))
            raise


class BacktestStrategy:
    """
    Backtest strategy use case.

    Backtests a trading strategy with historical data.
    """

    def __init__(
        self,
        backtest: BacktestPort,
    ) -> None:
        """
        Initialize BacktestStrategy use case.

        Args:
            backtest: Backtest port implementation
        """
        self.backtest = backtest

    def execute(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float = 100000.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestResult:
        """
        Execute backtest strategy use case.

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
        logger.info(
            "Running backtest",
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
        )

        try:
            result = self.backtest.run_backtest(
                prices=prices,
                signals=signals,
                initial_capital=initial_capital,
                start_date=start_date,
                end_date=end_date,
            )

            logger.info(
                "Backtest completed",
                total_return=result.total_return,
                sharpe_ratio=result.sharpe_ratio,
                max_drawdown=result.max_drawdown,
                total_trades=result.total_trades,
            )

            return result

        except Exception as e:
            logger.error("Backtest failed", error=str(e))
            raise


class MonitorStrategy:
    """
    Monitor strategy use case.

    Monitors a live trading strategy (positions, orders, PnL).
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
        position_manager: PositionManager,
    ) -> None:
        """
        Initialize MonitorStrategy use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
            position_manager: Position manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager
        self.position_manager = position_manager

    async def execute(self) -> Dict[str, Any]:
        """
        Execute monitor strategy use case.

        Returns:
            Dictionary with monitoring data (positions, orders, PnL, etc.)

        Raises:
            APIError: If monitoring fails
        """
        logger.info("Monitoring strategy")

        try:
            # Get current state
            positions = await self.exchange.get_positions()
            orders = await self.exchange.get_open_orders()
            balances = await self.exchange.get_balances()

            # Update managers
            for position in positions:
                existing = self.position_manager.get_position(position.symbol)
                if existing:
                    self.position_manager.update_position(
                        position.symbol,
                        size=position.size,
                        mark_price=position.mark_price,
                        funding_rate=position.funding_rate,
                    )
                else:
                    self.position_manager.add_position(position)

            for order in orders:
                existing = self.order_manager.get_order(order.id)
                if existing:
                    self.order_manager.update_order(
                        order.id,
                        status=order.status,
                        filled_quantity=order.filled_quantity,
                    )
                else:
                    self.order_manager.add_order(order)

            # Calculate metrics
            total_unrealized_pnl = self.position_manager.get_total_unrealized_pnl()
            total_notional = self.position_manager.get_total_notional_value()
            open_positions_count = len(self.position_manager.get_open_positions())
            open_orders_count = len(self.order_manager.get_open_orders())

            # Calculate total balance
            total_balance = sum(inv.total for inv in balances)

            monitoring_data = {
                "positions": {
                    "count": open_positions_count,
                    "total_unrealized_pnl": total_unrealized_pnl,
                    "total_notional": total_notional,
                    "positions": [p.dict() for p in positions],
                },
                "orders": {
                    "count": open_orders_count,
                    "orders": [o.dict() for o in orders],
                },
                "balances": {
                    "total": total_balance,
                    "inventories": [inv.dict() for inv in balances],
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Strategy monitoring completed",
                positions_count=open_positions_count,
                orders_count=open_orders_count,
                total_pnl=total_unrealized_pnl,
            )

            return monitoring_data

        except Exception as e:
            logger.error("Failed to monitor strategy", error=str(e))
            raise


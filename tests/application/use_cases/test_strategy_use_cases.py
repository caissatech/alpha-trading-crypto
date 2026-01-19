"""Tests for strategy use cases."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from alpha_trading_crypto.application.use_cases.strategy_use_cases import (
    BacktestStrategy,
    ExecuteStrategy,
    MonitorStrategy,
)
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager
from alpha_trading_crypto.infrastructure.backtest.backtest_engine import BacktestResult


@pytest.fixture
def mock_exchange() -> MagicMock:
    """Create mock exchange port."""
    exchange = MagicMock()
    exchange.place_order = AsyncMock()
    exchange.get_positions = AsyncMock(return_value=[])
    exchange.get_open_orders = AsyncMock(return_value=[])
    exchange.get_balances = AsyncMock(return_value=[])
    return exchange


@pytest.fixture
def mock_backtest() -> MagicMock:
    """Create mock backtest port."""
    backtest = MagicMock()
    return backtest


@pytest.fixture
def order_manager() -> OrderManager:
    """Create order manager."""
    return OrderManager()


@pytest.fixture
def position_manager() -> PositionManager:
    """Create position manager."""
    return PositionManager()


class TestExecuteStrategy:
    """Test ExecuteStrategy use case."""

    @pytest.fixture
    def execute_strategy(
        self, mock_exchange: MagicMock, order_manager: OrderManager, position_manager: PositionManager
    ) -> ExecuteStrategy:
        """Create ExecuteStrategy use case."""
        return ExecuteStrategy(
            exchange=mock_exchange,
            order_manager=order_manager,
            position_manager=position_manager,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, execute_strategy: ExecuteStrategy, mock_exchange: MagicMock) -> None:
        """Test successful strategy execution."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
        )
        mock_exchange.place_order.return_value = order

        signals = [
            {"symbol": "BTC", "side": "BUY", "quantity": 0.1},
            {"symbol": "ETH", "side": "SELL", "quantity": 1.0},
        ]

        result = await execute_strategy.execute(signals)

        assert len(result) == 2
        assert mock_exchange.place_order.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_invalid_signal(self, execute_strategy: ExecuteStrategy) -> None:
        """Test execution with invalid signal."""
        signals = [
            {"symbol": "BTC"},  # Missing side and quantity
            {"symbol": "ETH", "side": "BUY", "quantity": 1.0},
        ]

        result = await execute_strategy.execute(signals)

        # Should skip invalid signal
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_with_limit_order(self, execute_strategy: ExecuteStrategy, mock_exchange: MagicMock) -> None:
        """Test execution with limit order."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            order_type=OrderType.LIMIT,
        )
        mock_exchange.place_order.return_value = order

        signals = [{"symbol": "BTC", "side": "BUY", "quantity": 0.1, "price": 50000.0, "order_type": "LIMIT"}]

        result = await execute_strategy.execute(signals)

        assert len(result) == 1
        mock_exchange.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_positions_success(
        self, execute_strategy: ExecuteStrategy, mock_exchange: MagicMock, position_manager: PositionManager
    ) -> None:
        """Test updating positions."""
        positions = [
            Position(
                symbol="BTC",
                size=0.1,
                entry_price=50000.0,
                mark_price=51000.0,
                unrealized_pnl=100.0,
            ),
        ]
        mock_exchange.get_positions.return_value = positions

        await execute_strategy.update_positions()

        assert position_manager.get_position("BTC") is not None
        assert position_manager.get_position("BTC").size == 0.1


class TestBacktestStrategy:
    """Test BacktestStrategy use case."""

    @pytest.fixture
    def backtest_strategy(self, mock_backtest: MagicMock) -> BacktestStrategy:
        """Create BacktestStrategy use case."""
        return BacktestStrategy(backtest=mock_backtest)

    def test_execute_success(self, backtest_strategy: BacktestStrategy, mock_backtest: MagicMock) -> None:
        """Test successful backtest."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 10,
                "open": [50000.0] * 10,
                "high": [51000.0] * 10,
                "low": [49000.0] * 10,
                "close": [50000.0] * 10,
                "volume": [1000.0] * 10,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0]],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [0.1],
            }
        )

        result = BacktestResult(
            initial_capital=100000.0,
            final_capital=101000.0,
            total_return=1.0,
            total_pnl=1000.0,
            sharpe_ratio=1.5,
            max_drawdown=5.0,
            win_rate=60.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            average_win=200.0,
            average_loss=-100.0,
            profit_factor=3.0,
            start_date=dates[0],
            end_date=dates[-1],
        )
        mock_backtest.run_backtest.return_value = result

        backtest_result = backtest_strategy.execute(prices, signals, initial_capital=100000.0)

        assert backtest_result.total_return == 1.0
        assert backtest_result.sharpe_ratio == 1.5
        mock_backtest.run_backtest.assert_called_once()

    def test_execute_with_date_range(self, backtest_strategy: BacktestStrategy, mock_backtest: MagicMock) -> None:
        """Test backtest with date range."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 100,
                "open": [50000.0] * 100,
                "high": [51000.0] * 100,
                "low": [49000.0] * 100,
                "close": [50000.0] * 100,
                "volume": [1000.0] * 100,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0]],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [0.1],
            }
        )

        result = BacktestResult(
            initial_capital=100000.0,
            final_capital=101000.0,
            total_return=1.0,
            total_pnl=1000.0,
            sharpe_ratio=1.5,
            max_drawdown=5.0,
            win_rate=60.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            average_win=200.0,
            average_loss=-100.0,
            profit_factor=3.0,
            start_date=dates[0],
            end_date=dates[-1],
        )
        mock_backtest.run_backtest.return_value = result

        start_date = datetime(2024, 1, 1, 12, 0, 0)
        end_date = datetime(2024, 1, 5, 0, 0, 0)

        backtest_result = backtest_strategy.execute(
            prices, signals, initial_capital=100000.0, start_date=start_date, end_date=end_date
        )

        assert backtest_result is not None
        mock_backtest.run_backtest.assert_called_once()


class TestMonitorStrategy:
    """Test MonitorStrategy use case."""

    @pytest.fixture
    def monitor_strategy(
        self, mock_exchange: MagicMock, order_manager: OrderManager, position_manager: PositionManager
    ) -> MonitorStrategy:
        """Create MonitorStrategy use case."""
        return MonitorStrategy(
            exchange=mock_exchange,
            order_manager=order_manager,
            position_manager=position_manager,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self, monitor_strategy: MonitorStrategy, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test successful strategy monitoring."""
        positions = [
            Position(
                symbol="BTC",
                size=0.1,
                entry_price=50000.0,
                mark_price=51000.0,
                unrealized_pnl=100.0,
            ),
        ]
        orders = [
            Order(
                id="order1",
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
            ),
        ]
        from alpha_trading_crypto.domain.entities.inventory import Inventory

        balances = [
            Inventory(token="USDC", free=1000.0, locked=100.0, total=1100.0, chain="hyperliquid"),
        ]

        mock_exchange.get_positions.return_value = positions
        mock_exchange.get_open_orders.return_value = orders
        mock_exchange.get_balances.return_value = balances

        result = await monitor_strategy.execute()

        assert "positions" in result
        assert "orders" in result
        assert "balances" in result
        assert result["positions"]["count"] == 1
        assert result["orders"]["count"] == 1
        assert result["balances"]["total"] == 1100.0

    @pytest.mark.asyncio
    async def test_execute_updates_managers(
        self, monitor_strategy: MonitorStrategy, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test monitoring updates managers."""
        positions = []
        orders = [
            Order(
                id="order1",
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
            ),
        ]
        balances = []

        mock_exchange.get_positions.return_value = positions
        mock_exchange.get_open_orders.return_value = orders
        mock_exchange.get_balances.return_value = balances

        await monitor_strategy.execute()

        assert order_manager.get_order("order1") is not None


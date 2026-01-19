"""Tests for order use cases."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from alpha_trading_crypto.application.use_cases.order_use_cases import (
    CancelOrder,
    ModifyOrder,
    PlaceOrder,
    QueryOrders,
)
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from alpha_trading_crypto.domain.services.order_manager import OrderManager


@pytest.fixture
def mock_exchange() -> MagicMock:
    """Create mock exchange port."""
    exchange = MagicMock()
    exchange.place_order = AsyncMock()
    exchange.cancel_order = AsyncMock(return_value=True)
    exchange.get_open_orders = AsyncMock(return_value=[])
    return exchange


@pytest.fixture
def order_manager() -> OrderManager:
    """Create order manager."""
    return OrderManager()


@pytest.fixture
def place_order_use_case(mock_exchange: MagicMock, order_manager: OrderManager) -> PlaceOrder:
    """Create PlaceOrder use case."""
    return PlaceOrder(exchange=mock_exchange, order_manager=order_manager)


@pytest.fixture
def cancel_order_use_case(mock_exchange: MagicMock, order_manager: OrderManager) -> CancelOrder:
    """Create CancelOrder use case."""
    return CancelOrder(exchange=mock_exchange, order_manager=order_manager)


class TestPlaceOrder:
    """Test PlaceOrder use case."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, place_order_use_case: PlaceOrder, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test successful order placement."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
        )
        mock_exchange.place_order.return_value = order

        result = await place_order_use_case.execute(
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
        )

        assert result.id == "order123"
        assert result.symbol == "BTC"
        mock_exchange.place_order.assert_called_once()
        assert order_manager.get_order("order123") is not None

    @pytest.mark.asyncio
    async def test_execute_with_limit_order(
        self, place_order_use_case: PlaceOrder, mock_exchange: MagicMock
    ) -> None:
        """Test placing limit order."""
        order = Order(
            id="order456",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            order_type=OrderType.LIMIT,
        )
        mock_exchange.place_order.return_value = order

        result = await place_order_use_case.execute(
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.LIMIT,
            price=50000.0,
        )

        assert result.price == 50000.0
        mock_exchange.place_order.assert_called_once_with(
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.LIMIT,
            price=50000.0,
            reduce_only=False,
            post_only=False,
            client_order_id=None,
        )

    @pytest.mark.asyncio
    async def test_execute_with_all_options(
        self, place_order_use_case: PlaceOrder, mock_exchange: MagicMock
    ) -> None:
        """Test placing order with all options."""
        order = Order(
            id="order789",
            symbol="ETH",
            side=OrderSide.SELL,
            quantity=1.0,
            price=3000.0,
            order_type=OrderType.LIMIT,
            reduce_only=True,
            post_only=True,
            client_order_id="client123",
        )
        mock_exchange.place_order.return_value = order

        result = await place_order_use_case.execute(
            symbol="ETH",
            side=OrderSide.SELL,
            quantity=1.0,
            order_type=OrderType.LIMIT,
            price=3000.0,
            reduce_only=True,
            post_only=True,
            client_order_id="client123",
        )

        assert result.reduce_only is True
        assert result.post_only is True
        assert result.client_order_id == "client123"


class TestCancelOrder:
    """Test CancelOrder use case."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, cancel_order_use_case: CancelOrder, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test successful order cancellation."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            status=OrderStatus.OPEN,
        )
        order_manager.add_order(order)

        result = await cancel_order_use_case.execute("order123")

        assert result is True
        mock_exchange.cancel_order.assert_called_once_with("order123")
        cancelled_order = order_manager.get_order("order123")
        assert cancelled_order is not None
        assert cancelled_order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_execute_order_not_in_manager(
        self, cancel_order_use_case: CancelOrder, mock_exchange: MagicMock
    ) -> None:
        """Test cancelling order not in manager."""
        result = await cancel_order_use_case.execute("order999")

        assert result is True
        mock_exchange.cancel_order.assert_called_once_with("order999")

    @pytest.mark.asyncio
    async def test_execute_exchange_error(
        self, cancel_order_use_case: CancelOrder, mock_exchange: MagicMock
    ) -> None:
        """Test cancellation with exchange error."""
        from alpha_trading_crypto.infrastructure.exceptions import APIError

        mock_exchange.cancel_order.side_effect = APIError("Cancellation failed")

        with pytest.raises(APIError):
            await cancel_order_use_case.execute("order123")


class TestModifyOrder:
    """Test ModifyOrder use case."""

    @pytest.fixture
    def modify_order_use_case(self, mock_exchange: MagicMock, order_manager: OrderManager) -> ModifyOrder:
        """Create ModifyOrder use case."""
        return ModifyOrder(exchange=mock_exchange, order_manager=order_manager)

    @pytest.mark.asyncio
    async def test_execute_success(
        self, modify_order_use_case: ModifyOrder, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test successful order modification."""
        existing_order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
        )
        order_manager.add_order(existing_order)

        new_order = Order(
            id="order456",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.2,
            price=51000.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
        )
        mock_exchange.place_order.return_value = new_order

        result = await modify_order_use_case.execute("order123", quantity=0.2, price=51000.0)

        assert result.id == "order456"
        assert result.quantity == 0.2
        assert result.price == 51000.0
        mock_exchange.cancel_order.assert_called_once_with("order123")
        mock_exchange.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_order_not_found(
        self, modify_order_use_case: ModifyOrder, order_manager: OrderManager
    ) -> None:
        """Test modification of non-existent order."""
        with pytest.raises(ValueError, match="Order not found"):
            await modify_order_use_case.execute("order999", quantity=0.2)

    @pytest.mark.asyncio
    async def test_execute_order_not_open(
        self, modify_order_use_case: ModifyOrder, order_manager: OrderManager
    ) -> None:
        """Test modification of non-open order."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
        )
        order_manager.add_order(order)

        with pytest.raises(ValueError, match="Order is not open"):
            await modify_order_use_case.execute("order123", quantity=0.2)

    @pytest.mark.asyncio
    async def test_execute_invalid_quantity(
        self, modify_order_use_case: ModifyOrder, order_manager: OrderManager
    ) -> None:
        """Test modification with invalid quantity."""
        order = Order(
            id="order123",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            status=OrderStatus.OPEN,
        )
        order_manager.add_order(order)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            await modify_order_use_case.execute("order123", quantity=-0.1)


class TestQueryOrders:
    """Test QueryOrders use case."""

    @pytest.fixture
    def query_orders_use_case(self, mock_exchange: MagicMock, order_manager: OrderManager) -> QueryOrders:
        """Create QueryOrders use case."""
        return QueryOrders(exchange=mock_exchange, order_manager=order_manager)

    @pytest.mark.asyncio
    async def test_execute_success(
        self, query_orders_use_case: QueryOrders, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test successful order query."""
        orders = [
            Order(
                id="order1",
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
            ),
            Order(
                id="order2",
                symbol="ETH",
                side=OrderSide.SELL,
                quantity=1.0,
                order_type=OrderType.LIMIT,
                price=3000.0,
                status=OrderStatus.OPEN,
            ),
        ]
        mock_exchange.get_open_orders.return_value = orders

        result = await query_orders_use_case.execute()

        assert len(result) == 2
        mock_exchange.get_open_orders.assert_called_once()
        assert order_manager.get_order("order1") is not None
        assert order_manager.get_order("order2") is not None

    @pytest.mark.asyncio
    async def test_execute_with_symbol_filter(
        self, query_orders_use_case: QueryOrders, mock_exchange: MagicMock
    ) -> None:
        """Test query with symbol filter."""
        orders = [
            Order(
                id="order1",
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
            ),
            Order(
                id="order2",
                symbol="ETH",
                side=OrderSide.SELL,
                quantity=1.0,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
            ),
        ]
        mock_exchange.get_open_orders.return_value = orders

        result = await query_orders_use_case.execute(symbol="BTC")

        assert len(result) == 1
        assert result[0].symbol == "BTC"

    @pytest.mark.asyncio
    async def test_execute_updates_existing_order(
        self, query_orders_use_case: QueryOrders, mock_exchange: MagicMock, order_manager: OrderManager
    ) -> None:
        """Test query updates existing order."""
        existing_order = Order(
            id="order1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            status=OrderStatus.OPEN,
            filled_quantity=0.0,
        )
        order_manager.add_order(existing_order)

        updated_order = Order(
            id="order1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            status=OrderStatus.PARTIALLY_FILLED,
            filled_quantity=0.05,
            average_fill_price=50000.0,
        )
        mock_exchange.get_open_orders.return_value = [updated_order]

        result = await query_orders_use_case.execute()

        assert len(result) == 1
        updated = order_manager.get_order("order1")
        assert updated is not None
        assert updated.status == OrderStatus.PARTIALLY_FILLED
        assert updated.filled_quantity == 0.05


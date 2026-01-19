"""Tests for market making use cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from alpha_trading_crypto.application.use_cases.market_making_use_cases import (
    StartMarketMaking,
    StopMarketMaking,
    UpdateMarketMaking,
)
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter import (
    AvellanedaStoikov,
    AvellanedaStoikovParams,
)
from alpha_trading_crypto.domain.services.market_making_service import MarketMakingService
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager


@pytest.fixture
def mock_exchange() -> MagicMock:
    """Create mock exchange port."""
    exchange = MagicMock()
    exchange.place_order = AsyncMock()
    exchange.cancel_order = AsyncMock(return_value=True)
    return exchange


@pytest.fixture
def as_model() -> AvellanedaStoikov:
    """Create Avellaneda-Stoikov model."""
    from unittest.mock import MagicMock, patch

    params = AvellanedaStoikovParams(
        risk_aversion=0.1,
        volatility=0.02,
        arrival_rate=10.0,
        reservation_spread=0.001,
    )
    with patch("alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter.qk") as mock_qk:
        mock_qk_model = MagicMock()
        mock_qk_model.calculate_optimal_spread.return_value = (49900.0, 50100.0)
        mock_qk_model.calculate_spread.return_value = 200.0
        mock_qk_model.calculate_optimal_quantities.return_value = (1.0, 1.0)
        mock_qk.PyAvellanedaStoikovParams.return_value = MagicMock()
        mock_qk.PyAvellanedaStoikov.return_value = mock_qk_model
        return AvellanedaStoikov(params=params)


@pytest.fixture
def market_making_service(
    as_model: AvellanedaStoikov,
    order_manager: OrderManager,
    position_manager: PositionManager,
) -> MarketMakingService:
    """Create market making service."""
    return MarketMakingService(
        as_model=as_model,
        order_manager=order_manager,
        position_manager=position_manager,
    )


@pytest.fixture
def start_market_making(
    mock_exchange: MagicMock,
    market_making_service: MarketMakingService,
    order_manager: OrderManager,
) -> StartMarketMaking:
    """Create StartMarketMaking use case."""
    return StartMarketMaking(
        exchange=mock_exchange,
        market_making_service=market_making_service,
        order_manager=order_manager,
    )


class TestStartMarketMaking:
    """Test StartMarketMaking use case."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        start_market_making: StartMarketMaking,
        mock_exchange: MagicMock,
        order_manager: OrderManager,
    ) -> None:
        """Test successful market making start."""
        bid_order = Order(
            id="bid1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=1.0,
            price=49900.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )
        ask_order = Order(
            id="ask1",
            symbol="BTC",
            side=OrderSide.SELL,
            quantity=1.0,
            price=50100.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )

        mock_exchange.place_order.side_effect = [bid_order, ask_order]

        result = await start_market_making.execute(
            symbol="BTC",
            mid_price=50000.0,
            base_quantity=1.0,
            max_inventory=10.0,
        )

        assert "bid_order" in result
        assert "ask_order" in result
        assert mock_exchange.place_order.call_count == 2
        assert order_manager.get_order("bid1") is not None
        assert order_manager.get_order("ask1") is not None

    @pytest.mark.asyncio
    async def test_execute_inventory_at_limit(
        self,
        start_market_making: StartMarketMaking,
        position_manager: PositionManager,
    ) -> None:
        """Test start market making when inventory at limit."""
        from alpha_trading_crypto.domain.entities.position import Position

        position = Position(
            symbol="BTC",
            size=10.0,  # At limit
            entry_price=50000.0,
            mark_price=51000.0,
        )
        position_manager.add_position(position)

        with pytest.raises(ValueError, match="Inventory at limit"):
            await start_market_making.execute(
                symbol="BTC",
                mid_price=50000.0,
                base_quantity=1.0,
                max_inventory=10.0,
            )


class TestUpdateMarketMaking:
    """Test UpdateMarketMaking use case."""

    @pytest.fixture
    def update_market_making(
        self,
        mock_exchange: MagicMock,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> UpdateMarketMaking:
        """Create UpdateMarketMaking use case."""
        return UpdateMarketMaking(
            exchange=mock_exchange,
            market_making_service=market_making_service,
            order_manager=order_manager,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        update_market_making: UpdateMarketMaking,
        mock_exchange: MagicMock,
        order_manager: OrderManager,
    ) -> None:
        """Test successful market making update."""
        # Add existing orders
        existing_bid = Order(
            id="bid1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=1.0,
            price=49900.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )
        existing_ask = Order(
            id="ask1",
            symbol="BTC",
            side=OrderSide.SELL,
            quantity=1.0,
            price=50100.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )
        order_manager.add_order(existing_bid)
        order_manager.add_order(existing_ask)

        # New orders
        new_bid = Order(
            id="bid2",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=1.0,
            price=49800.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )
        new_ask = Order(
            id="ask2",
            symbol="BTC",
            side=OrderSide.SELL,
            quantity=1.0,
            price=50200.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )

        mock_exchange.place_order.side_effect = [new_bid, new_ask]

        result = await update_market_making.execute(
            symbol="BTC",
            mid_price=50000.0,
            base_quantity=1.0,
            max_inventory=10.0,
        )

        assert result["bid_order"] is not None
        assert result["ask_order"] is not None
        assert mock_exchange.cancel_order.call_count == 2


class TestStopMarketMaking:
    """Test StopMarketMaking use case."""

    @pytest.fixture
    def stop_market_making(
        self,
        mock_exchange: MagicMock,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> StopMarketMaking:
        """Create StopMarketMaking use case."""
        return StopMarketMaking(
            exchange=mock_exchange,
            market_making_service=market_making_service,
            order_manager=order_manager,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        stop_market_making: StopMarketMaking,
        mock_exchange: MagicMock,
        order_manager: OrderManager,
    ) -> None:
        """Test successful market making stop."""
        bid_order = Order(
            id="bid1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=1.0,
            price=49900.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )
        ask_order = Order(
            id="ask1",
            symbol="BTC",
            side=OrderSide.SELL,
            quantity=1.0,
            price=50100.0,
            order_type=OrderType.LIMIT,
            post_only=True,
        )

        order_manager.add_order(bid_order)
        order_manager.add_order(ask_order)

        result = await stop_market_making.execute("BTC")

        assert result == 2
        assert mock_exchange.cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_no_orders(
        self, stop_market_making: StopMarketMaking, mock_exchange: MagicMock
    ) -> None:
        """Test stop market making with no orders."""
        result = await stop_market_making.execute("BTC")

        assert result == 0
        assert mock_exchange.cancel_order.call_count == 0


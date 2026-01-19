"""Tests for MarketMakingService."""

from unittest.mock import MagicMock

import pytest

from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter import (
    AvellanedaStoikov,
    AvellanedaStoikovParams,
)
from alpha_trading_crypto.domain.services.market_making_service import MarketMakingService
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager


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
def order_manager() -> OrderManager:
    """Create order manager."""
    return OrderManager()


@pytest.fixture
def position_manager() -> PositionManager:
    """Create position manager."""
    return PositionManager()


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


class TestMarketMakingService:
    """Test MarketMakingService."""

    def test_calculate_quotes_flat_inventory(
        self, market_making_service: MarketMakingService
    ) -> None:
        """Test calculating quotes with flat inventory."""
        quotes = market_making_service.calculate_quotes(
            symbol="BTC",
            mid_price=50000.0,
            base_quantity=1.0,
            max_inventory=10.0,
        )

        assert "bid_price" in quotes
        assert "ask_price" in quotes
        assert "bid_quantity" in quotes
        assert "ask_quantity" in quotes
        assert quotes["bid_price"] < 50000.0
        assert quotes["ask_price"] > 50000.0
        assert quotes["ask_price"] > quotes["bid_price"]

    def test_calculate_quotes_with_position(
        self, market_making_service: MarketMakingService, position_manager: PositionManager
    ) -> None:
        """Test calculating quotes with existing position."""
        position = Position(
            symbol="BTC",
            size=5.0,  # Long position
            entry_price=50000.0,
            mark_price=51000.0,
        )
        position_manager.add_position(position)

        quotes = market_making_service.calculate_quotes(
            symbol="BTC",
            mid_price=51000.0,
            base_quantity=1.0,
            max_inventory=10.0,
        )

        assert quotes["inventory"] == 5.0
        # With long inventory, ask quantity should be higher (want to sell)
        assert quotes["ask_quantity"] >= quotes["bid_quantity"]

    def test_should_adjust_quotes_no_existing(self, market_making_service: MarketMakingService) -> None:
        """Test should adjust when no existing quotes."""
        should_adjust = market_making_service.should_adjust_quotes(
            symbol="BTC",
            current_bid=None,
            current_ask=None,
            new_bid=49900.0,
            new_ask=50100.0,
        )

        assert should_adjust is True

    def test_should_adjust_quotes_small_change(
        self, market_making_service: MarketMakingService
    ) -> None:
        """Test should not adjust for small changes."""
        should_adjust = market_making_service.should_adjust_quotes(
            symbol="BTC",
            current_bid=49900.0,
            current_ask=50100.0,
            new_bid=49901.0,  # Very small change
            new_ask=50099.0,
            min_spread_change=0.01,  # 1% threshold
        )

        assert should_adjust is False

    def test_should_adjust_quotes_large_change(
        self, market_making_service: MarketMakingService
    ) -> None:
        """Test should adjust for large changes."""
        should_adjust = market_making_service.should_adjust_quotes(
            symbol="BTC",
            current_bid=49900.0,
            current_ask=50100.0,
            new_bid=49500.0,  # Large change (>1%)
            new_ask=50500.0,
            min_spread_change=0.01,
        )

        assert should_adjust is True

    def test_get_maker_orders_no_orders(
        self, market_making_service: MarketMakingService
    ) -> None:
        """Test getting maker orders when none exist."""
        bid_order, ask_order = market_making_service.get_maker_orders("BTC")

        assert bid_order is None
        assert ask_order is None

    def test_get_maker_orders_with_orders(
        self,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> None:
        """Test getting maker orders."""
        bid_order = Order(
            id="bid1",
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=1.0,
            price=49900.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            post_only=True,
        )
        ask_order = Order(
            id="ask1",
            symbol="BTC",
            side=OrderSide.SELL,
            quantity=1.0,
            price=50100.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            post_only=True,
        )

        order_manager.add_order(bid_order)
        order_manager.add_order(ask_order)

        found_bid, found_ask = market_making_service.get_maker_orders("BTC")

        assert found_bid is not None
        assert found_ask is not None
        assert found_bid.id == "bid1"
        assert found_ask.id == "ask1"

    def test_check_inventory_limits_safe(
        self, market_making_service: MarketMakingService
    ) -> None:
        """Test checking inventory limits when safe."""
        status = market_making_service.check_inventory_limits(
            symbol="BTC",
            max_inventory=10.0,
        )

        assert status["is_at_limit"] is False
        assert status["is_near_limit"] is False
        assert status["should_reduce"] is False

    def test_check_inventory_limits_near_limit(
        self,
        market_making_service: MarketMakingService,
        position_manager: PositionManager,
    ) -> None:
        """Test checking inventory limits when near limit."""
        position = Position(
            symbol="BTC",
            size=8.5,  # 85% of max
            entry_price=50000.0,
            mark_price=51000.0,
        )
        position_manager.add_position(position)

        status = market_making_service.check_inventory_limits(
            symbol="BTC",
            max_inventory=10.0,
            warning_threshold=0.8,
        )

        assert status["is_near_limit"] is True
        assert status["should_reduce"] is False  # 85% < 90%

    def test_check_inventory_limits_at_limit(
        self,
        market_making_service: MarketMakingService,
        position_manager: PositionManager,
    ) -> None:
        """Test checking inventory limits when at limit."""
        position = Position(
            symbol="BTC",
            size=10.0,  # At limit
            entry_price=50000.0,
            mark_price=51000.0,
        )
        position_manager.add_position(position)

        status = market_making_service.check_inventory_limits(
            symbol="BTC",
            max_inventory=10.0,
        )

        assert status["is_at_limit"] is True
        assert status["should_reduce"] is True


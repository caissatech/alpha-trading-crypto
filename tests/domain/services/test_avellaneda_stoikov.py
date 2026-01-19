"""Tests for Avellaneda-Stoikov model."""

import pytest

from alpha_trading_crypto.domain.services.avellaneda_stoikov import (
    AvellanedaStoikov,
    AvellanedaStoikovParams,
)


@pytest.fixture
def as_params() -> AvellanedaStoikovParams:
    """Create Avellaneda-Stoikov parameters."""
    return AvellanedaStoikovParams(
        risk_aversion=0.1,
        volatility=0.02,
        arrival_rate=10.0,
        reservation_spread=0.001,
    )


@pytest.fixture
def as_model(as_params: AvellanedaStoikovParams) -> AvellanedaStoikov:
    """Create Avellaneda-Stoikov model."""
    return AvellanedaStoikov(params=as_params)


class TestAvellanedaStoikovParams:
    """Test AvellanedaStoikovParams."""

    def test_init_success(self) -> None:
        """Test successful initialization."""
        params = AvellanedaStoikovParams(
            risk_aversion=0.1,
            volatility=0.02,
            arrival_rate=10.0,
        )
        assert params.risk_aversion == 0.1
        assert params.volatility == 0.02
        assert params.arrival_rate == 10.0

    def test_init_with_reservation_spread(self) -> None:
        """Test initialization with reservation spread."""
        params = AvellanedaStoikovParams(
            risk_aversion=0.1,
            volatility=0.02,
            arrival_rate=10.0,
            reservation_spread=0.002,
        )
        assert params.reservation_spread == 0.002

    def test_init_invalid_risk_aversion(self) -> None:
        """Test initialization with invalid risk aversion."""
        with pytest.raises(ValueError):
            AvellanedaStoikovParams(
                risk_aversion=-0.1,
                volatility=0.02,
                arrival_rate=10.0,
            )

    def test_init_invalid_volatility(self) -> None:
        """Test initialization with invalid volatility."""
        with pytest.raises(ValueError):
            AvellanedaStoikovParams(
                risk_aversion=0.1,
                volatility=-0.02,
                arrival_rate=10.0,
            )


class TestAvellanedaStoikov:
    """Test Avellaneda-Stoikov model."""

    def test_calculate_optimal_spread_flat_inventory(
        self, as_model: AvellanedaStoikov
    ) -> None:
        """Test calculating optimal spread with flat inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=0.0,
        )

        assert bid_price < 50000.0
        assert ask_price > 50000.0
        assert ask_price > bid_price
        assert (ask_price - bid_price) >= as_model.params.reservation_spread

    def test_calculate_optimal_spread_long_inventory(
        self, as_model: AvellanedaStoikov
    ) -> None:
        """Test calculating optimal spread with long inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=1.0,  # Long position
        )

        # With long inventory, bid should be lower (less willing to buy)
        # and ask should be lower (more willing to sell)
        assert bid_price < 50000.0
        assert ask_price > 50000.0

    def test_calculate_optimal_spread_short_inventory(
        self, as_model: AvellanedaStoikov
    ) -> None:
        """Test calculating optimal spread with short inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=-1.0,  # Short position
        )

        # With short inventory, bid should be higher (more willing to buy)
        # and ask should be higher (less willing to sell)
        assert bid_price < 50000.0
        assert ask_price > 50000.0

    def test_calculate_optimal_spread_invalid_price(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating spread with invalid price."""
        with pytest.raises(ValueError, match="Mid price must be positive"):
            as_model.calculate_optimal_spread(mid_price=-100.0, inventory=0.0)

    def test_calculate_spread(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating spread."""
        spread = as_model.calculate_spread(inventory=0.0)
        assert spread >= as_model.params.reservation_spread

    def test_calculate_optimal_quantities_flat(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating optimal quantities with flat inventory."""
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=0.0,
            max_inventory=10.0,
            base_quantity=1.0,
        )

        assert bid_qty > 0
        assert ask_qty > 0
        # With flat inventory, quantities should be similar
        assert abs(bid_qty - ask_qty) < 0.5

    def test_calculate_optimal_quantities_long(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating optimal quantities with long inventory."""
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=8.0,  # Long position (80% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # With long inventory, bid quantity should be higher (want to sell)
        # and ask quantity should be lower (don't want to buy more)
        assert bid_qty > ask_qty

    def test_calculate_optimal_quantities_short(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating optimal quantities with short inventory."""
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=-8.0,  # Short position (80% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # With short inventory, ask quantity should be higher (want to buy)
        # and bid quantity should be lower (don't want to sell more)
        assert ask_qty > bid_qty

    def test_calculate_optimal_quantities_at_limit(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating quantities at inventory limit."""
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=9.5,  # Very close to limit (95% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # Quantities should be reduced when near limit
        assert bid_qty < 1.0
        assert ask_qty < 1.0

    def test_calculate_optimal_quantities_invalid_base(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating quantities with invalid base quantity."""
        with pytest.raises(ValueError, match="Base quantity must be positive"):
            as_model.calculate_optimal_quantities(
                mid_price=50000.0,
                inventory=0.0,
                max_inventory=10.0,
                base_quantity=-1.0,
            )

    def test_calculate_optimal_quantities_invalid_max(self, as_model: AvellanedaStoikov) -> None:
        """Test calculating quantities with invalid max inventory."""
        with pytest.raises(ValueError, match="Max inventory must be positive"):
            as_model.calculate_optimal_quantities(
                mid_price=50000.0,
                inventory=0.0,
                max_inventory=-10.0,
                base_quantity=1.0,
            )


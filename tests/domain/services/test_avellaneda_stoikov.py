"""Tests for Avellaneda-Stoikov model."""

from unittest.mock import MagicMock, patch

import pytest

from alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter import (
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
def mock_qk_model() -> MagicMock:
    """Create mock quant-kit model."""
    mock = MagicMock()
    mock.calculate_optimal_spread.return_value = (49900.0, 50100.0)
    mock.calculate_spread.return_value = 200.0
    mock.calculate_optimal_quantities.return_value = (1.0, 1.0)
    return mock


@pytest.fixture
def as_model(as_params: AvellanedaStoikovParams, mock_qk_model: MagicMock) -> AvellanedaStoikov:
    """Create Avellaneda-Stoikov model."""
    with patch("alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter.qk") as mock_qk:
        mock_qk.PyAvellanedaStoikovParams.return_value = MagicMock()
        mock_qk.PyAvellanedaStoikov.return_value = mock_qk_model
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
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal spread with flat inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=0.0,
        )

        assert bid_price == 49900.0
        assert ask_price == 50100.0
        assert ask_price > bid_price
        mock_qk_model.calculate_optimal_spread.assert_called_once_with(50000.0, 0.0, 1.0)

    def test_calculate_optimal_spread_long_inventory(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal spread with long inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=1.0,  # Long position
        )

        assert bid_price == 49900.0
        assert ask_price == 50100.0
        mock_qk_model.calculate_optimal_spread.assert_called_once_with(50000.0, 1.0, 1.0)

    def test_calculate_optimal_spread_short_inventory(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal spread with short inventory."""
        bid_price, ask_price = as_model.calculate_optimal_spread(
            mid_price=50000.0,
            inventory=-1.0,  # Short position
        )

        assert bid_price == 49900.0
        assert ask_price == 50100.0
        mock_qk_model.calculate_optimal_spread.assert_called_once_with(50000.0, -1.0, 1.0)

    def test_calculate_optimal_spread_invalid_price(
        self, as_params: AvellanedaStoikovParams, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating spread with invalid price."""
        with patch("alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter.qk") as mock_qk:
            mock_qk.PyAvellanedaStoikovParams.return_value = MagicMock()
            mock_qk.PyAvellanedaStoikov.return_value = mock_qk_model
            as_model = AvellanedaStoikov(params=as_params)
            with pytest.raises(ValueError, match="Mid price must be positive"):
                as_model.calculate_optimal_spread(mid_price=-100.0, inventory=0.0)

    def test_calculate_spread(self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock) -> None:
        """Test calculating spread."""
        spread = as_model.calculate_spread(inventory=0.0)
        assert spread == 200.0
        mock_qk_model.calculate_spread.assert_called_once_with(0.0, 1.0)

    def test_calculate_optimal_quantities_flat(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal quantities with flat inventory."""
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=0.0,
            max_inventory=10.0,
            base_quantity=1.0,
        )

        assert bid_qty == 1.0
        assert ask_qty == 1.0
        mock_qk_model.calculate_optimal_quantities.assert_called_once_with(50000.0, 0.0, 10.0, 1.0, 1.0)

    def test_calculate_optimal_quantities_long(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal quantities with long inventory."""
        # Mock return value for long inventory
        mock_qk_model.calculate_optimal_quantities.return_value = (1.5, 0.5)
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=8.0,  # Long position (80% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # With long inventory, bid quantity should be higher (want to sell)
        assert bid_qty == 1.5
        assert ask_qty == 0.5

    def test_calculate_optimal_quantities_short(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating optimal quantities with short inventory."""
        # Mock return value for short inventory
        mock_qk_model.calculate_optimal_quantities.return_value = (0.5, 1.5)
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=-8.0,  # Short position (80% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # With short inventory, ask quantity should be higher (want to buy)
        assert ask_qty == 1.5
        assert bid_qty == 0.5

    def test_calculate_optimal_quantities_at_limit(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating quantities at inventory limit."""
        # Mock return value for near limit
        mock_qk_model.calculate_optimal_quantities.return_value = (0.3, 0.3)
        bid_qty, ask_qty = as_model.calculate_optimal_quantities(
            mid_price=50000.0,
            inventory=9.5,  # Very close to limit (95% of max)
            max_inventory=10.0,
            base_quantity=1.0,
        )

        # Quantities should be reduced when near limit
        assert bid_qty == 0.3
        assert ask_qty == 0.3

    def test_calculate_optimal_quantities_invalid_base(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating quantities with invalid base quantity."""
        with pytest.raises(ValueError, match="Base quantity must be positive"):
            as_model.calculate_optimal_quantities(
                mid_price=50000.0,
                inventory=0.0,
                max_inventory=10.0,
                base_quantity=-1.0,
            )

    def test_calculate_optimal_quantities_invalid_max(
        self, as_model: AvellanedaStoikov, mock_qk_model: MagicMock
    ) -> None:
        """Test calculating quantities with invalid max inventory."""
        with pytest.raises(ValueError, match="Max inventory must be positive"):
            as_model.calculate_optimal_quantities(
                mid_price=50000.0,
                inventory=0.0,
                max_inventory=-10.0,
                base_quantity=1.0,
            )


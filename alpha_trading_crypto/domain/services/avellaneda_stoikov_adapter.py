"""Adapter for Avellaneda-Stoikov model from quant-kit."""

from typing import Tuple

try:
    import quant_kit as qk
except ImportError:
    qk = None  # type: ignore

from pydantic import BaseModel, Field


class AvellanedaStoikovParams(BaseModel):
    """
    Parameters for Avellaneda-Stoikov model.

    Attributes:
        risk_aversion: Risk aversion parameter (gamma)
        volatility: Volatility of the asset
        arrival_rate: Arrival rate of orders (lambda/kappa)
        reservation_spread: Reservation spread (minimum spread)
        time_horizon: Time horizon (T, default 1.0)
    """

    risk_aversion: float = Field(..., gt=0, description="Risk aversion parameter (gamma)")
    volatility: float = Field(..., gt=0, description="Volatility of the asset")
    arrival_rate: float = Field(..., gt=0, description="Arrival rate of orders (lambda/kappa)")
    reservation_spread: float = Field(default=0.0, ge=0, description="Reservation spread (minimum spread)")
    time_horizon: float = Field(default=1.0, gt=0, description="Time horizon (T)")

    class Config:
        """Pydantic config."""

        frozen = True


class AvellanedaStoikov:
    """
    Avellaneda-Stoikov model adapter.

    Wraps the quant-kit implementation for use in alpha-trading-crypto.
    """

    def __init__(self, params: AvellanedaStoikovParams) -> None:
        """
        Initialize Avellaneda-Stoikov model.

        Args:
            params: Model parameters

        Raises:
            ImportError: If quant-kit is not installed
        """
        if qk is None:
            raise ImportError(
                "quant-kit is not installed. Please install it with: "
                "cd /home/schachk/Code/quant-kit/python && maturin develop"
            )

        # Create quant-kit params
        qk_params = qk.PyAvellanedaStoikovParams(
            risk_aversion=params.risk_aversion,
            volatility=params.volatility,
            arrival_rate=params.arrival_rate,
            time_horizon=params.time_horizon,
            reservation_spread=params.reservation_spread,
        )

        # Create quant-kit model
        self._qk_model = qk.PyAvellanedaStoikov(qk_params)
        self.params = params

    def calculate_optimal_spread(
        self,
        mid_price: float,
        inventory: float,
        time_to_maturity: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid and ask prices.

        Args:
            mid_price: Current mid price
            inventory: Current inventory (positive = long, negative = short)
            time_to_maturity: Time to maturity (normalized, default 1.0)

        Returns:
            Tuple of (bid_price, ask_price)
        """
        return self._qk_model.calculate_optimal_spread(mid_price, inventory, time_to_maturity)

    def calculate_spread(self, inventory: float, time_to_maturity: float = 1.0) -> float:
        """
        Calculate optimal spread.

        Args:
            inventory: Current inventory
            time_to_maturity: Time to maturity (normalized)

        Returns:
            Optimal spread
        """
        return self._qk_model.calculate_spread(inventory, time_to_maturity)

    def calculate_optimal_quantities(
        self,
        mid_price: float,
        inventory: float,
        max_inventory: float,
        base_quantity: float,
        time_to_maturity: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid and ask quantities.

        Args:
            mid_price: Current mid price
            inventory: Current inventory
            max_inventory: Maximum allowed inventory
            base_quantity: Base quantity to place
            time_to_maturity: Time to maturity

        Returns:
            Tuple of (bid_quantity, ask_quantity)
        """
        return self._qk_model.calculate_optimal_quantities(
            mid_price, inventory, max_inventory, base_quantity, time_to_maturity
        )


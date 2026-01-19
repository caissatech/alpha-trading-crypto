"""Avellaneda-Stoikov model for optimal market making."""

import math
from typing import Tuple

from pydantic import BaseModel, Field


class AvellanedaStoikovParams(BaseModel):
    """
    Parameters for Avellaneda-Stoikov model.

    Attributes:
        risk_aversion: Risk aversion parameter (gamma)
        volatility: Volatility of the asset
        arrival_rate: Arrival rate of orders (lambda)
        reservation_spread: Reservation spread (minimum spread)
    """

    risk_aversion: float = Field(..., gt=0, description="Risk aversion parameter (gamma)")
    volatility: float = Field(..., gt=0, description="Volatility of the asset")
    arrival_rate: float = Field(..., gt=0, description="Arrival rate of orders (lambda)")
    reservation_spread: float = Field(default=0.0, ge=0, description="Reservation spread (minimum spread)")

    class Config:
        """Pydantic config."""

        frozen = True


class AvellanedaStoikov:
    """
    Avellaneda-Stoikov model for optimal market making.

    Calculates optimal bid/ask prices and spreads based on inventory, volatility,
    and risk parameters.
    """

    def __init__(self, params: AvellanedaStoikovParams) -> None:
        """
        Initialize Avellaneda-Stoikov model.

        Args:
            params: Model parameters
        """
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
        if mid_price <= 0:
            raise ValueError("Mid price must be positive")

        # Calculate reservation price
        reservation_price = self._calculate_reservation_price(mid_price, inventory, time_to_maturity)

        # Calculate optimal spread
        optimal_spread = self._calculate_optimal_spread(inventory, time_to_maturity)

        # Calculate bid and ask prices
        bid_price = reservation_price - optimal_spread / 2.0
        ask_price = reservation_price + optimal_spread / 2.0

        # Ensure spread is at least reservation spread
        if ask_price - bid_price < self.params.reservation_spread:
            spread = self.params.reservation_spread
            bid_price = reservation_price - spread / 2.0
            ask_price = reservation_price + spread / 2.0

        return (bid_price, ask_price)

    def calculate_spread(self, inventory: float, time_to_maturity: float = 1.0) -> float:
        """
        Calculate optimal spread.

        Args:
            inventory: Current inventory
            time_to_maturity: Time to maturity (normalized)

        Returns:
            Optimal spread
        """
        spread = self._calculate_optimal_spread(inventory, time_to_maturity)
        return max(spread, self.params.reservation_spread)

    def _calculate_reservation_price(
        self,
        mid_price: float,
        inventory: float,
        time_to_maturity: float,
    ) -> float:
        """
        Calculate reservation price (price at which we're indifferent to trading).

        Args:
            mid_price: Current mid price
            inventory: Current inventory
            time_to_maturity: Time to maturity

        Returns:
            Reservation price
        """
        # Reservation price = mid_price - gamma * sigma^2 * inventory * time_to_maturity
        adjustment = (
            self.params.risk_aversion * self.params.volatility**2 * inventory * time_to_maturity
        )
        return mid_price - adjustment

    def _calculate_optimal_spread(self, inventory: float, time_to_maturity: float) -> float:
        """
        Calculate optimal spread.

        Args:
            inventory: Current inventory
            time_to_maturity: Time to maturity

        Returns:
            Optimal spread
        """
        # Optimal spread = gamma * sigma^2 * time_to_maturity + (2/gamma) * ln(1 + gamma/k)
        # where k = lambda / (gamma * sigma^2)
        gamma = self.params.risk_aversion
        sigma_sq = self.params.volatility**2
        lambda_rate = self.params.arrival_rate

        # Base spread component
        base_spread = gamma * sigma_sq * time_to_maturity

        # Inventory adjustment
        # As inventory increases, we want to reduce ask spread and increase bid spread
        # This is handled by the reservation price adjustment

        # Intensity adjustment
        if lambda_rate > 0 and gamma > 0:
            k = lambda_rate / (gamma * sigma_sq)
            intensity_component = (2.0 / gamma) * math.log(1.0 + gamma / k) if k > 0 else 0.0
        else:
            intensity_component = 0.0

        total_spread = base_spread + intensity_component

        return max(total_spread, self.params.reservation_spread)

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
        if base_quantity <= 0:
            raise ValueError("Base quantity must be positive")

        if max_inventory <= 0:
            raise ValueError("Max inventory must be positive")

        # Calculate inventory ratio
        inventory_ratio = abs(inventory) / max_inventory if max_inventory > 0 else 0.0

        # Calculate reservation price
        reservation_price = self._calculate_reservation_price(mid_price, inventory, time_to_maturity)

        # Calculate optimal prices
        bid_price, ask_price = self.calculate_optimal_spread(mid_price, inventory, time_to_maturity)

        # Adjust quantities based on inventory
        # If we're long (inventory > 0), reduce ask quantity and increase bid quantity
        # If we're short (inventory < 0), reduce bid quantity and increase ask quantity

        if inventory > 0:
            # Long position: reduce ask, increase bid
            bid_quantity = base_quantity * (1.0 + inventory_ratio * 0.5)
            ask_quantity = base_quantity * (1.0 - inventory_ratio * 0.5)
        elif inventory < 0:
            # Short position: reduce bid, increase ask
            bid_quantity = base_quantity * (1.0 - inventory_ratio * 0.5)
            ask_quantity = base_quantity * (1.0 + inventory_ratio * 0.5)
        else:
            # Flat position: equal quantities
            bid_quantity = base_quantity
            ask_quantity = base_quantity

        # Ensure quantities are positive
        bid_quantity = max(0.0, bid_quantity)
        ask_quantity = max(0.0, ask_quantity)

        # Scale down if inventory is near limits
        if inventory_ratio > 0.8:
            # Very close to limit: reduce both quantities
            scale = 1.0 - (inventory_ratio - 0.8) * 2.0  # Scale from 1.0 to 0.0
            scale = max(0.1, scale)  # Minimum 10% of base quantity
            bid_quantity *= scale
            ask_quantity *= scale

        return (bid_quantity, ask_quantity)


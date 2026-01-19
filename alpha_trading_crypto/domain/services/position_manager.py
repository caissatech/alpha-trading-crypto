"""Position Manager service."""

from typing import Dict, List, Optional

from alpha_trading_crypto.domain.entities.position import Position


class PositionManager:
    """
    Position Manager service.

    Manages positions: update, calculate PnL, funding.
    """

    def __init__(self) -> None:
        """Initialize PositionManager."""
        self._positions: Dict[str, Position] = {}

    def add_position(self, position: Position) -> None:
        """
        Add a position to tracking.

        Args:
            position: Position to add
        """
        self._positions[position.symbol] = position

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position if found, None otherwise
        """
        return self._positions.get(symbol)

    def update_position(
        self,
        symbol: str,
        size: Optional[float] = None,
        mark_price: Optional[float] = None,
        funding_rate: Optional[float] = None,
    ) -> Optional[Position]:
        """
        Update position.

        Args:
            symbol: Trading symbol
            size: Position size
            mark_price: Mark price
            funding_rate: Funding rate

        Returns:
            Updated position if found, None otherwise
        """
        position = self.get_position(symbol)
        if position is None:
            return None

        if size is not None:
            position.size = size
        if mark_price is not None:
            position.mark_price = mark_price
        if funding_rate is not None:
            position.funding_rate = funding_rate

        # Update PnL
        position.update_pnl()

        from datetime import datetime

        position.updated_at = datetime.utcnow()

        return position

    def calculate_funding(self, symbol: str, time_period_hours: float = 8.0) -> Optional[float]:
        """
        Calculate funding payment for a position.

        Args:
            symbol: Trading symbol
            time_period_hours: Time period in hours (default 8h for perp funding)

        Returns:
            Funding payment (positive = we pay, negative = we receive) if position found, None otherwise
        """
        position = self.get_position(symbol)
        if position is None or position.is_flat():
            return None

        # Funding = position_size * mark_price * funding_rate * time_period
        funding = position.size * position.mark_price * position.funding_rate * (time_period_hours / 24.0)

        return funding

    def get_all_positions(self) -> List[Position]:
        """
        Get all positions.

        Returns:
            List of all positions
        """
        return list(self._positions.values())

    def get_open_positions(self) -> List[Position]:
        """
        Get all open (non-flat) positions.

        Returns:
            List of open positions
        """
        return [position for position in self._positions.values() if not position.is_flat()]

    def get_total_unrealized_pnl(self) -> float:
        """
        Get total unrealized PnL across all positions.

        Returns:
            Total unrealized PnL
        """
        return sum(position.unrealized_pnl for position in self._positions.values())

    def get_total_notional_value(self) -> float:
        """
        Get total notional value across all positions.

        Returns:
            Total notional value
        """
        return sum(position.notional_value() for position in self._positions.values())


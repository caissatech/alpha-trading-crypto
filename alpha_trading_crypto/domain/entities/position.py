"""Position entity."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    """
    Position entity.

    Represents an open position on Hyperliquid.
    """

    symbol: str = Field(..., description="Trading symbol (e.g., 'BTC')")
    size: float = Field(..., description="Position size (positive = long, negative = short)")
    entry_price: float = Field(..., gt=0, description="Average entry price")
    mark_price: float = Field(..., gt=0, description="Current mark price")
    unrealized_pnl: float = Field(default=0.0, description="Unrealized PnL")
    realized_pnl: float = Field(default=0.0, description="Realized PnL")
    funding_rate: float = Field(default=0.0, description="Current funding rate")
    funding_paid: float = Field(default=0.0, description="Total funding paid")
    leverage: float = Field(default=1.0, ge=1.0, description="Leverage")
    liquidation_price: Optional[float] = Field(None, gt=0, description="Liquidation price")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Position timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Pydantic config."""

        frozen = False  # Allow updates

    def is_long(self) -> bool:
        """Check if position is long."""
        return self.size > 0

    def is_short(self) -> bool:
        """Check if position is short."""
        return self.size < 0

    def is_flat(self) -> bool:
        """Check if position is flat."""
        return abs(self.size) < 1e-8

    def notional_value(self) -> float:
        """Get notional value of position."""
        return abs(self.size * self.mark_price)

    def update_pnl(self) -> None:
        """Update unrealized PnL based on current mark price."""
        if self.is_flat():
            self.unrealized_pnl = 0.0
        else:
            price_diff = self.mark_price - self.entry_price
            self.unrealized_pnl = self.size * price_diff


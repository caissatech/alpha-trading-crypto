"""Inventory entity."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Inventory(BaseModel):
    """
    Inventory entity.

    Represents the inventory (balance) of a token.
    """

    token: str = Field(..., description="Token symbol (e.g., 'USDC', 'BTC')")
    free: float = Field(default=0.0, ge=0, description="Free balance (available)")
    locked: float = Field(default=0.0, ge=0, description="Locked balance (in orders)")
    total: float = Field(default=0.0, ge=0, description="Total balance (free + locked)")
    chain: str = Field(default="hyperliquid", description="Chain (hyperliquid, ethereum, etc.)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Inventory timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Pydantic config."""

        frozen = False  # Allow updates

    def update_total(self) -> None:
        """Update total balance from free + locked."""
        self.total = self.free + self.locked

    def available(self) -> float:
        """Get available balance (free)."""
        return self.free

    def is_positive(self) -> bool:
        """Check if inventory is positive."""
        return self.total > 0

    def verify_consistency(self) -> bool:
        """Verify consistency between free, locked, and total."""
        expected_total = self.free + self.locked
        return abs(self.total - expected_total) < 1e-8


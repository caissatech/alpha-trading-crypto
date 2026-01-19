"""Order entity."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order(BaseModel):
    """
    Order entity.

    Represents a trading order on Hyperliquid.
    """

    id: str = Field(..., description="Order ID (from exchange)")
    symbol: str = Field(..., description="Trading symbol (e.g., 'BTC')")
    side: OrderSide = Field(..., description="Order side (BUY or SELL)")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Order price (for limit orders)")
    order_type: OrderType = Field(..., description="Order type (MARKET, LIMIT, etc.)")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    filled_quantity: float = Field(default=0.0, ge=0, description="Filled quantity")
    average_fill_price: Optional[float] = Field(None, gt=0, description="Average fill price")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Order timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    client_order_id: Optional[str] = Field(None, description="Client order ID")
    reduce_only: bool = Field(default=False, description="Reduce only flag")
    post_only: bool = Field(default=False, description="Post only flag (maker)")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        frozen = False  # Allow updates

    def is_open(self) -> bool:
        """Check if order is open."""
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]

    def is_filled(self) -> bool:
        """Check if order is filled."""
        return self.status == OrderStatus.FILLED

    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return self.status == OrderStatus.CANCELLED

    def remaining_quantity(self) -> float:
        """Get remaining quantity to fill."""
        return max(0.0, self.quantity - self.filled_quantity)


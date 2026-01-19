"""Transfer entity."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransferStatus(str, Enum):
    """Transfer status."""

    PENDING = "PENDING"
    INITIATED = "INITIATED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transfer(BaseModel):
    """
    Transfer entity.

    Represents a token transfer between chains (Ethereum ↔ Hyperliquid).
    """

    id: str = Field(..., description="Transfer ID")
    from_chain: str = Field(..., description="Source chain (ethereum, hyperliquid)")
    to_chain: str = Field(..., description="Destination chain (ethereum, hyperliquid)")
    token: str = Field(..., description="Token symbol (e.g., 'USDC')")
    amount: float = Field(..., gt=0, description="Transfer amount")
    status: TransferStatus = Field(default=TransferStatus.PENDING, description="Transfer status")
    tx_hash: Optional[str] = Field(None, description="Transaction hash")
    block_number: Optional[int] = Field(None, ge=0, description="Block number")
    gas_fee: Optional[float] = Field(None, ge=0, description="Gas fee paid")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Transfer timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        frozen = False  # Allow updates

    def is_completed(self) -> bool:
        """Check if transfer is completed."""
        return self.status == TransferStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if transfer failed."""
        return self.status == TransferStatus.FAILED

    def is_pending(self) -> bool:
        """Check if transfer is pending."""
        return self.status in [TransferStatus.PENDING, TransferStatus.INITIATED, TransferStatus.CONFIRMED]


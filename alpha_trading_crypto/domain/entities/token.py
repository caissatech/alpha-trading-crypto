"""Token entity."""

from typing import Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Token entity.

    Represents a token configuration.
    """

    symbol: str = Field(..., description="Token symbol (e.g., 'BTC', 'USDC')")
    decimals: int = Field(..., ge=0, le=18, description="Token decimals")
    chain: str = Field(..., description="Chain (hyperliquid, ethereum, etc.)")
    address: Optional[str] = Field(None, description="Token contract address (for Ethereum)")
    is_quote: bool = Field(default=False, description="Is quote currency (e.g., USDC)")
    min_order_size: float = Field(default=0.0, ge=0, description="Minimum order size")
    tick_size: float = Field(default=0.01, gt=0, description="Price tick size")
    step_size: float = Field(default=0.0001, gt=0, description="Quantity step size")

    class Config:
        """Pydantic config."""

        frozen = True  # Immutable


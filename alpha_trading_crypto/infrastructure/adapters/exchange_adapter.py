"""Exchange adapter implementing ExchangePort."""

from typing import List, Optional

from alpha_trading_crypto.application.ports.exchange_port import ExchangePort
from alpha_trading_crypto.domain.entities.inventory import Inventory
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.infrastructure.adapters.hyperliquid_api import HyperliquidAPI


class ExchangeAdapter(ExchangePort):
    """
    Exchange adapter.

    Implements ExchangePort using HyperliquidAPI.
    """

    def __init__(self, api: HyperliquidAPI) -> None:
        """
        Initialize exchange adapter.

        Args:
            api: HyperliquidAPI instance
        """
        self.api = api

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        reduce_only: bool = False,
        post_only: bool = False,
        client_order_id: Optional[str] = None,
    ) -> Order:
        """Place an order."""
        return await self.api.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            reduce_only=reduce_only,
            post_only=post_only,
            client_order_id=client_order_id,
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return await self.api.cancel_order(order_id)

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """Cancel all orders."""
        return await self.api.cancel_all_orders(symbol=symbol)

    async def get_open_orders(self) -> List[Order]:
        """Get open orders."""
        return await self.api.get_open_orders()

    async def get_balances(self) -> List[Inventory]:
        """Get account balances."""
        return await self.api.get_balances()

    async def get_positions(self) -> List[Position]:
        """Get open positions."""
        return await self.api.get_positions()

    async def get_ticker(self, symbol: str) -> dict:
        """Get ticker information."""
        return await self.api.get_ticker(symbol=symbol)

    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate."""
        data = await self.api.get_funding_rate(symbol)
        return float(data.get("fundingRate", 0.0))


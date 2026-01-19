"""Exchange port (interface) for trading operations."""

from abc import ABC, abstractmethod
from typing import List, Optional

from alpha_trading_crypto.domain.entities.inventory import Inventory
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.entities.position import Position


class ExchangePort(ABC):
    """
    Exchange port interface.

    Defines the contract for exchange operations (trading, account info, etc.).
    """

    @abstractmethod
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
        """
        Place an order.

        Args:
            symbol: Trading symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            price: Limit price (required for LIMIT orders)
            reduce_only: Reduce only flag
            post_only: Post only flag (maker)
            client_order_id: Client order ID

        Returns:
            Placed Order entity

        Raises:
            ValueError: If invalid parameters
            APIError: If API returns error
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully

        Raises:
            APIError: If cancellation fails
        """
        pass

    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """
        Cancel all orders (optionally for a symbol).

        Args:
            symbol: Symbol to cancel orders for (None for all symbols)

        Returns:
            True if cancelled successfully

        Raises:
            APIError: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """
        Get open orders.

        Returns:
            List of open Order entities

        Raises:
            APIError: If API returns error
        """
        pass

    @abstractmethod
    async def get_balances(self) -> List[Inventory]:
        """
        Get account balances.

        Returns:
            List of Inventory entities

        Raises:
            APIError: If API returns error
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get open positions.

        Returns:
            List of Position entities

        Raises:
            APIError: If API returns error
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data dictionary

        Raises:
            APIError: If API returns error
        """
        pass

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> float:
        """
        Get current funding rate for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate

        Raises:
            APIError: If API returns error
        """
        pass


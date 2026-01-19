"""Order use cases."""

from typing import List, Optional

import structlog

from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.application.ports.exchange_port import ExchangePort
from alpha_trading_crypto.infrastructure.exceptions import APIError

logger = structlog.get_logger()


class PlaceOrder:
    """
    Place order use case.

    Places an order on the exchange and tracks it in the order manager.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize PlaceOrder use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager

    async def execute(
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
        Execute place order use case.

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
            APIError: If order placement fails
        """
        logger.info(
            "Placing order",
            symbol=symbol,
            side=side.value,
            quantity=quantity,
            order_type=order_type.value,
            price=price,
        )

        try:
            # Place order on exchange
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                reduce_only=reduce_only,
                post_only=post_only,
                client_order_id=client_order_id,
            )

            # Track order in order manager
            self.order_manager.add_order(order)

            logger.info("Order placed successfully", order_id=order.id, symbol=symbol)

            return order

        except Exception as e:
            logger.error("Failed to place order", error=str(e), symbol=symbol)
            raise


class CancelOrder:
    """
    Cancel order use case.

    Cancels an order on the exchange and updates it in the order manager.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize CancelOrder use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager

    async def execute(self, order_id: str) -> bool:
        """
        Execute cancel order use case.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully

        Raises:
            APIError: If cancellation fails
        """
        logger.info("Cancelling order", order_id=order_id)

        # Check if order exists in manager
        order = self.order_manager.get_order(order_id)
        if not order:
            logger.warning("Order not found in manager", order_id=order_id)

        try:
            # Cancel order on exchange
            result = await self.exchange.cancel_order(order_id)

            # Update order in manager
            if order:
                self.order_manager.cancel_order(order_id)

            logger.info("Order cancelled successfully", order_id=order_id)

            return result

        except Exception as e:
            logger.error("Failed to cancel order", error=str(e), order_id=order_id)
            raise


class ModifyOrder:
    """
    Modify order use case.

    Modifies an existing order (cancel old, place new).
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize ModifyOrder use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager

    async def execute(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
    ) -> Order:
        """
        Execute modify order use case.

        Args:
            order_id: Order ID to modify
            quantity: New quantity (if None, keep existing)
            price: New price (if None, keep existing)

        Returns:
            Modified Order entity

        Raises:
            ValueError: If order not found or invalid parameters
            APIError: If modification fails
        """
        logger.info("Modifying order", order_id=order_id, quantity=quantity, price=price)

        # Get existing order
        existing_order = self.order_manager.get_order(order_id)
        if not existing_order:
            raise ValueError(f"Order not found: {order_id}")

        if not existing_order.is_open():
            raise ValueError(f"Order is not open: {order_id}")

        # Use existing values if not provided
        new_quantity = quantity if quantity is not None else existing_order.quantity
        new_price = price if price is not None else existing_order.price

        if new_quantity <= 0:
            raise ValueError("Quantity must be positive")

        if existing_order.order_type == OrderType.LIMIT and (new_price is None or new_price <= 0):
            raise ValueError("Price is required for LIMIT orders")

        try:
            # Cancel existing order
            await self.exchange.cancel_order(order_id)
            self.order_manager.cancel_order(order_id)

            # Place new order with updated parameters
            new_order = await self.exchange.place_order(
                symbol=existing_order.symbol,
                side=existing_order.side,
                quantity=new_quantity,
                order_type=existing_order.order_type,
                price=new_price,
                reduce_only=existing_order.reduce_only,
                post_only=existing_order.post_only,
            )

            # Track new order
            self.order_manager.add_order(new_order)

            logger.info("Order modified successfully", old_order_id=order_id, new_order_id=new_order.id)

            return new_order

        except Exception as e:
            logger.error("Failed to modify order", error=str(e), order_id=order_id)
            raise


class QueryOrders:
    """
    Query orders use case.

    Queries orders from exchange and updates order manager.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize QueryOrders use case.

        Args:
            exchange: Exchange port implementation
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.order_manager = order_manager

    async def execute(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Execute query orders use case.

        Args:
            symbol: Symbol to filter orders (None for all)

        Returns:
            List of Order entities

        Raises:
            APIError: If query fails
        """
        logger.info("Querying orders", symbol=symbol)

        try:
            # Get orders from exchange
            orders = await self.exchange.get_open_orders()

            # Filter by symbol if provided
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]

            # Update order manager with latest orders
            for order in orders:
                existing_order = self.order_manager.get_order(order.id)
                if existing_order:
                    # Update existing order
                    self.order_manager.update_order(
                        order.id,
                        status=order.status,
                        filled_quantity=order.filled_quantity,
                        average_fill_price=order.average_fill_price,
                    )
                else:
                    # Add new order
                    self.order_manager.add_order(order)

            logger.info("Orders queried successfully", count=len(orders), symbol=symbol)

            return orders

        except Exception as e:
            logger.error("Failed to query orders", error=str(e), symbol=symbol)
            raise


"""Order Manager service."""

from typing import Dict, List, Optional

from alpha_trading_crypto.domain.entities.order import Order, OrderStatus


class OrderManager:
    """
    Order Manager service.

    Manages orders: create, cancel, update, track.
    """

    def __init__(self) -> None:
        """Initialize OrderManager."""
        self._orders: Dict[str, Order] = {}

    def add_order(self, order: Order) -> None:
        """
        Add an order to tracking.

        Args:
            order: Order to add
        """
        self._orders[order.id] = order

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get an order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order if found, None otherwise
        """
        return self._orders.get(order_id)

    def get_open_orders(self) -> List[Order]:
        """
        Get all open orders.

        Returns:
            List of open orders
        """
        return [order for order in self._orders.values() if order.is_open()]

    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """
        Get all orders for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of orders for symbol
        """
        return [order for order in self._orders.values() if order.symbol == symbol]

    def update_order(self, order_id: str, **updates: any) -> Optional[Order]:
        """
        Update an order.

        Args:
            order_id: Order ID
            **updates: Fields to update

        Returns:
            Updated order if found, None otherwise
        """
        order = self._orders.get(order_id)
        if order is None:
            return None

        for key, value in updates.items():
            if hasattr(order, key):
                setattr(order, key, value)

        return order

    def cancel_order(self, order_id: str) -> Optional[Order]:
        """
        Cancel an order.

        Args:
            order_id: Order ID

        Returns:
            Cancelled order if found, None otherwise
        """
        order = self._orders.get(order_id)
        if order is None:
            return None

        if order.is_open():
            order.status = OrderStatus.CANCELLED
            from datetime import datetime

            order.updated_at = datetime.utcnow()

        return order

    def clear_completed_orders(self) -> int:
        """
        Clear completed orders (filled, cancelled, rejected, expired).

        Returns:
            Number of orders cleared
        """
        to_remove = [
            order_id
            for order_id, order in self._orders.items()
            if order.status
            in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        ]

        for order_id in to_remove:
            del self._orders[order_id]

        return len(to_remove)

    def get_all_orders(self) -> List[Order]:
        """
        Get all orders.

        Returns:
            List of all orders
        """
        return list(self._orders.values())


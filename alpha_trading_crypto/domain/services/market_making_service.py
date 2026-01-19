"""Market making service."""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.domain.services.avellaneda_stoikov_adapter import (
    AvellanedaStoikov,
    AvellanedaStoikovParams,
)
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager

logger = structlog.get_logger()


class MarketMakingService:
    """
    Market making service.

    Manages market making operations using Avellaneda-Stoikov model.
    """

    def __init__(
        self,
        as_model: AvellanedaStoikov,
        order_manager: OrderManager,
        position_manager: PositionManager,
    ) -> None:
        """
        Initialize market making service.

        Args:
            as_model: Avellaneda-Stoikov model instance
            order_manager: Order manager service
            position_manager: Position manager service
        """
        self.as_model = as_model
        self.order_manager = order_manager
        self.position_manager = position_manager

    def calculate_quotes(
        self,
        symbol: str,
        mid_price: float,
        base_quantity: float,
        max_inventory: float,
        time_to_maturity: float = 1.0,
    ) -> Dict[str, float]:
        """
        Calculate optimal bid/ask quotes.

        Args:
            symbol: Trading symbol
            mid_price: Current mid price
            base_quantity: Base quantity for orders
            max_inventory: Maximum allowed inventory
            time_to_maturity: Time to maturity (normalized)

        Returns:
            Dictionary with bid_price, ask_price, bid_quantity, ask_quantity
        """
        # Get current inventory from position
        position = self.position_manager.get_position(symbol)
        inventory = position.size if position else 0.0

        # Calculate optimal prices and quantities
        bid_price, ask_price = self.as_model.calculate_optimal_spread(
            mid_price=mid_price,
            inventory=inventory,
            time_to_maturity=time_to_maturity,
        )

        bid_quantity, ask_quantity = self.as_model.calculate_optimal_quantities(
            mid_price=mid_price,
            inventory=inventory,
            max_inventory=max_inventory,
            base_quantity=base_quantity,
            time_to_maturity=time_to_maturity,
        )

        logger.debug(
            "Calculated quotes",
            symbol=symbol,
            mid_price=mid_price,
            inventory=inventory,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_quantity=bid_quantity,
            ask_quantity=ask_quantity,
        )

        return {
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_quantity": bid_quantity,
            "ask_quantity": ask_quantity,
            "inventory": inventory,
            "spread": ask_price - bid_price,
        }

    def should_adjust_quotes(
        self,
        symbol: str,
        current_bid: Optional[float],
        current_ask: Optional[float],
        new_bid: float,
        new_ask: float,
        min_spread_change: float = 0.001,
    ) -> bool:
        """
        Check if quotes should be adjusted.

        Args:
            symbol: Trading symbol
            current_bid: Current bid price (None if no bid order)
            current_ask: Current ask price (None if no ask order)
            new_bid: New bid price
            new_ask: New ask price
            min_spread_change: Minimum spread change to trigger adjustment (percentage)

        Returns:
            True if quotes should be adjusted
        """
        if current_bid is None or current_ask is None:
            return True  # No existing quotes, should place new ones

        # Calculate price changes
        bid_change = abs(new_bid - current_bid) / current_bid if current_bid > 0 else float("inf")
        ask_change = abs(new_ask - current_ask) / current_ask if current_ask > 0 else float("inf")

        # Adjust if change exceeds threshold
        should_adjust = bid_change > min_spread_change or ask_change > min_spread_change

        logger.debug(
            "Checking quote adjustment",
            symbol=symbol,
            bid_change=bid_change,
            ask_change=ask_change,
            should_adjust=should_adjust,
        )

        return should_adjust

    def get_maker_orders(self, symbol: str) -> Tuple[Optional[Order], Optional[Order]]:
        """
        Get current maker orders for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Tuple of (bid_order, ask_order) or (None, None) if not found
        """
        orders = self.order_manager.get_orders_by_symbol(symbol)
        open_orders = [o for o in orders if o.is_open() and o.post_only]

        bid_order = next((o for o in open_orders if o.side == OrderSide.BUY), None)
        ask_order = next((o for o in open_orders if o.side == OrderSide.SELL), None)

        return (bid_order, ask_order)

    def check_inventory_limits(
        self,
        symbol: str,
        max_inventory: float,
        warning_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Check inventory limits and return status.

        Args:
            symbol: Trading symbol
            max_inventory: Maximum allowed inventory
            warning_threshold: Warning threshold (percentage of max)

        Returns:
            Dictionary with inventory status
        """
        position = self.position_manager.get_position(symbol)
        current_inventory = position.size if position else 0.0

        inventory_ratio = abs(current_inventory) / max_inventory if max_inventory > 0 else 0.0

        status = {
            "symbol": symbol,
            "current_inventory": current_inventory,
            "max_inventory": max_inventory,
            "inventory_ratio": inventory_ratio,
            "is_at_limit": inventory_ratio >= 1.0,
            "is_near_limit": inventory_ratio >= warning_threshold,
            "should_reduce": inventory_ratio > 0.9,  # Reduce quotes if > 90%
        }

        if status["is_at_limit"]:
            logger.warning("Inventory at limit", **status)
        elif status["is_near_limit"]:
            logger.warning("Inventory near limit", **status)

        return status


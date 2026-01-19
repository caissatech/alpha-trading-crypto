"""Market making use cases."""

from typing import Dict, List, Optional

import structlog

from alpha_trading_crypto.application.ports.exchange_port import ExchangePort
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderType
from alpha_trading_crypto.domain.services.market_making_service import MarketMakingService
from alpha_trading_crypto.domain.services.order_manager import OrderManager
from alpha_trading_crypto.domain.services.position_manager import PositionManager
from alpha_trading_crypto.infrastructure.exceptions import APIError

logger = structlog.get_logger()


class StartMarketMaking:
    """
    Start market making use case.

    Starts market making for a symbol with optimal bid/ask quotes.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize StartMarketMaking use case.

        Args:
            exchange: Exchange port implementation
            market_making_service: Market making service
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.market_making_service = market_making_service
        self.order_manager = order_manager

    async def execute(
        self,
        symbol: str,
        mid_price: float,
        base_quantity: float,
        max_inventory: float,
        time_to_maturity: float = 1.0,
    ) -> Dict[str, Order]:
        """
        Execute start market making use case.

        Args:
            symbol: Trading symbol
            mid_price: Current mid price
            base_quantity: Base quantity for orders
            max_inventory: Maximum allowed inventory
            time_to_maturity: Time to maturity (normalized)

        Returns:
            Dictionary with 'bid_order' and 'ask_order' keys

        Raises:
            ValueError: If parameters are invalid
            APIError: If order placement fails
        """
        logger.info(
            "Starting market making",
            symbol=symbol,
            mid_price=mid_price,
            base_quantity=base_quantity,
        )

        # Check inventory limits
        inventory_status = self.market_making_service.check_inventory_limits(symbol, max_inventory)
        if inventory_status["is_at_limit"]:
            raise ValueError(f"Inventory at limit for {symbol}")

        # Calculate optimal quotes
        quotes = self.market_making_service.calculate_quotes(
            symbol=symbol,
            mid_price=mid_price,
            base_quantity=base_quantity,
            max_inventory=max_inventory,
            time_to_maturity=time_to_maturity,
        )

        # Check if we should place orders
        bid_order, ask_order = self.market_making_service.get_maker_orders(symbol)
        should_adjust = self.market_making_service.should_adjust_quotes(
            symbol=symbol,
            current_bid=bid_order.price if bid_order else None,
            current_ask=ask_order.price if ask_order else None,
            new_bid=quotes["bid_price"],
            new_ask=quotes["ask_price"],
        )

        if not should_adjust and bid_order and ask_order:
            logger.info("Quotes already optimal, no adjustment needed", symbol=symbol)
            return {"bid_order": bid_order, "ask_order": ask_order}

        # Cancel existing orders if needed
        if bid_order:
            try:
                await self.exchange.cancel_order(bid_order.id)
                self.order_manager.cancel_order(bid_order.id)
            except Exception as e:
                logger.warning("Failed to cancel existing bid order", error=str(e), order_id=bid_order.id)

        if ask_order:
            try:
                await self.exchange.cancel_order(ask_order.id)
                self.order_manager.cancel_order(ask_order.id)
            except Exception as e:
                logger.warning("Failed to cancel existing ask order", error=str(e), order_id=ask_order.id)

        # Place new orders
        placed_orders = {}

        try:
            # Place bid order
            if quotes["bid_quantity"] > 0:
                bid_order = await self.exchange.place_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=quotes["bid_quantity"],
                    order_type=OrderType.LIMIT,
                    price=quotes["bid_price"],
                    post_only=True,
                )
                self.order_manager.add_order(bid_order)
                placed_orders["bid_order"] = bid_order
                logger.info("Bid order placed", order_id=bid_order.id, price=quotes["bid_price"])

            # Place ask order
            if quotes["ask_quantity"] > 0:
                ask_order = await self.exchange.place_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=quotes["ask_quantity"],
                    order_type=OrderType.LIMIT,
                    price=quotes["ask_price"],
                    post_only=True,
                )
                self.order_manager.add_order(ask_order)
                placed_orders["ask_order"] = ask_order
                logger.info("Ask order placed", order_id=ask_order.id, price=quotes["ask_price"])

        except Exception as e:
            logger.error("Failed to place market making orders", error=str(e), symbol=symbol)
            raise

        return placed_orders


class UpdateMarketMaking:
    """
    Update market making use case.

    Updates market making quotes based on current market conditions.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize UpdateMarketMaking use case.

        Args:
            exchange: Exchange port implementation
            market_making_service: Market making service
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.market_making_service = market_making_service
        self.order_manager = order_manager

    async def execute(
        self,
        symbol: str,
        mid_price: float,
        base_quantity: float,
        max_inventory: float,
        time_to_maturity: float = 1.0,
    ) -> Dict[str, Optional[Order]]:
        """
        Execute update market making use case.

        Args:
            symbol: Trading symbol
            mid_price: Current mid price
            base_quantity: Base quantity for orders
            max_inventory: Maximum allowed inventory
            time_to_maturity: Time to maturity (normalized)

        Returns:
            Dictionary with updated orders

        Raises:
            ValueError: If parameters are invalid
            APIError: If order update fails
        """
        logger.info("Updating market making", symbol=symbol, mid_price=mid_price)

        # Check inventory limits
        inventory_status = self.market_making_service.check_inventory_limits(symbol, max_inventory)
        if inventory_status["should_reduce"]:
            logger.warning("Inventory near limit, reducing quotes", symbol=symbol, **inventory_status)

        # Calculate optimal quotes
        quotes = self.market_making_service.calculate_quotes(
            symbol=symbol,
            mid_price=mid_price,
            base_quantity=base_quantity,
            max_inventory=max_inventory,
            time_to_maturity=time_to_maturity,
        )

        # Get current orders
        bid_order, ask_order = self.market_making_service.get_maker_orders(symbol)

        # Check if adjustment is needed
        should_adjust = self.market_making_service.should_adjust_quotes(
            symbol=symbol,
            current_bid=bid_order.price if bid_order else None,
            current_ask=ask_order.price if ask_order else None,
            new_bid=quotes["bid_price"],
            new_ask=quotes["ask_price"],
        )

        if not should_adjust:
            logger.debug("No adjustment needed", symbol=symbol)
            return {"bid_order": bid_order, "ask_order": ask_order}

        # Update orders
        updated_orders = {"bid_order": None, "ask_order": None}

        # Update bid order
        if quotes["bid_quantity"] > 0:
            if bid_order:
                # Cancel and replace
                try:
                    await self.exchange.cancel_order(bid_order.id)
                    self.order_manager.cancel_order(bid_order.id)
                except Exception as e:
                    logger.warning("Failed to cancel bid order", error=str(e))

            # Place new bid order
            try:
                new_bid_order = await self.exchange.place_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=quotes["bid_quantity"],
                    order_type=OrderType.LIMIT,
                    price=quotes["bid_price"],
                    post_only=True,
                )
                self.order_manager.add_order(new_bid_order)
                updated_orders["bid_order"] = new_bid_order
            except Exception as e:
                logger.error("Failed to place bid order", error=str(e))
        elif bid_order:
            # Cancel bid order if quantity is 0
            try:
                await self.exchange.cancel_order(bid_order.id)
                self.order_manager.cancel_order(bid_order.id)
            except Exception as e:
                logger.warning("Failed to cancel bid order", error=str(e))

        # Update ask order
        if quotes["ask_quantity"] > 0:
            if ask_order:
                # Cancel and replace
                try:
                    await self.exchange.cancel_order(ask_order.id)
                    self.order_manager.cancel_order(ask_order.id)
                except Exception as e:
                    logger.warning("Failed to cancel ask order", error=str(e))

            # Place new ask order
            try:
                new_ask_order = await self.exchange.place_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=quotes["ask_quantity"],
                    order_type=OrderType.LIMIT,
                    price=quotes["ask_price"],
                    post_only=True,
                )
                self.order_manager.add_order(new_ask_order)
                updated_orders["ask_order"] = new_ask_order
            except Exception as e:
                logger.error("Failed to place ask order", error=str(e))
        elif ask_order:
            # Cancel ask order if quantity is 0
            try:
                await self.exchange.cancel_order(ask_order.id)
                self.order_manager.cancel_order(ask_order.id)
            except Exception as e:
                logger.warning("Failed to cancel ask order", error=str(e))

        logger.info("Market making updated", symbol=symbol)

        return updated_orders


class StopMarketMaking:
    """
    Stop market making use case.

    Stops market making by cancelling all maker orders for a symbol.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        market_making_service: MarketMakingService,
        order_manager: OrderManager,
    ) -> None:
        """
        Initialize StopMarketMaking use case.

        Args:
            exchange: Exchange port implementation
            market_making_service: Market making service
            order_manager: Order manager service
        """
        self.exchange = exchange
        self.market_making_service = market_making_service
        self.order_manager = order_manager

    async def execute(self, symbol: str) -> int:
        """
        Execute stop market making use case.

        Args:
            symbol: Trading symbol

        Returns:
            Number of orders cancelled

        Raises:
            APIError: If cancellation fails
        """
        logger.info("Stopping market making", symbol=symbol)

        # Get current maker orders
        bid_order, ask_order = self.market_making_service.get_maker_orders(symbol)

        cancelled_count = 0

        # Cancel bid order
        if bid_order:
            try:
                await self.exchange.cancel_order(bid_order.id)
                self.order_manager.cancel_order(bid_order.id)
                cancelled_count += 1
                logger.info("Bid order cancelled", order_id=bid_order.id)
            except Exception as e:
                logger.error("Failed to cancel bid order", error=str(e), order_id=bid_order.id)

        # Cancel ask order
        if ask_order:
            try:
                await self.exchange.cancel_order(ask_order.id)
                self.order_manager.cancel_order(ask_order.id)
                cancelled_count += 1
                logger.info("Ask order cancelled", order_id=ask_order.id)
            except Exception as e:
                logger.error("Failed to cancel ask order", error=str(e), order_id=ask_order.id)

        logger.info("Market making stopped", symbol=symbol, orders_cancelled=cancelled_count)

        return cancelled_count


"""Hyperliquid API adapter."""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from alpha_trading_crypto.domain.entities.inventory import Inventory
from alpha_trading_crypto.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from alpha_trading_crypto.domain.entities.position import Position
from alpha_trading_crypto.infrastructure.exceptions import (
    APIError,
    AuthenticationError,
    InvalidDataError,
    NetworkError,
    RateLimitError,
)


class HyperliquidAPI:
    """
    Hyperliquid API client.

    Handles authentication, market data, account info, order placement, and order management.
    """

    # API endpoints
    BASE_URL_MAINNET = "https://api.hyperliquid.xyz"
    BASE_URL_TESTNET = "https://api.hyperliquid-testnet.xyz"

    def __init__(
        self,
        private_key: str,
        testnet: bool = True,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Hyperliquid API client.

        Args:
            private_key: Private key for authentication (hex string with 0x prefix)
            testnet: Use testnet if True, mainnet otherwise
            timeout: Request timeout in seconds

        Raises:
            ValueError: If private key is invalid
        """
        if not private_key.startswith("0x"):
            raise ValueError("Private key must start with 0x")

        try:
            self.account = Account.from_key(private_key)
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}") from e

        self.testnet = testnet
        self.base_url = self.BASE_URL_TESTNET if testnet else self.BASE_URL_MAINNET
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _sign_message(self, message: Dict[str, Any]) -> str:
        """
        Sign a message for authentication.

        Args:
            message: Message to sign

        Returns:
            Signature as hex string
        """
        message_str = json.dumps(message, separators=(",", ":"), sort_keys=True)
        message_encoded = encode_defunct(text=message_str)
        signed_message = self.account.sign_message(message_encoded)
        return signed_message.signature.hex()

    def _get_auth_headers(self, action: Dict[str, Any]) -> Dict[str, str]:
        """
        Get authentication headers for API request.

        Args:
            action: Action to authenticate

        Returns:
            Headers with authentication
        """
        signature = self._sign_message(action)
        return {
            "Content-Type": "application/json",
            "X-Hyperliquid-Auth": signature,
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        requires_auth: bool = False,
    ) -> Dict[str, Any]:
        """
        Make API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            requires_auth: Whether authentication is required

        Returns:
            Response data

        Raises:
            NetworkError: If network error occurs
            APIError: If API returns error
            RateLimitError: If rate limit exceeded
            AuthenticationError: If authentication fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if requires_auth and data:
            headers.update(self._get_auth_headers(data))

        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout: {e}") from e
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise AuthenticationError(f"Authentication failed: {e}", status_code=status_code) from e
            elif status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}", status_code=status_code) from e
            else:
                try:
                    error_data = e.response.json()
                except Exception:
                    error_data = None
                raise APIError(
                    f"API error: {e}",
                    status_code=status_code,
                    response_data=error_data,
                ) from e
        except Exception as e:
            raise NetworkError(f"Unexpected error: {e}") from e

    # Market Data Methods

    async def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information (symbols, tick sizes, etc.).

        Returns:
            Exchange information

        Raises:
            APIError: If API returns error
            InvalidDataError: If response format is invalid
        """
        response = await self._request("GET", "/info", data={"type": "meta"})

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        return response

    async def get_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        Get ticker information.

        Args:
            symbol: Symbol to get ticker for (None for all symbols)

        Returns:
            Ticker data

        Raises:
            APIError: If API returns error
            InvalidDataError: If response format is invalid
        """
        data = {"type": "ticker"}
        if symbol:
            data["symbol"] = symbol

        response = await self._request("GET", "/info", data=data)

        if not isinstance(response, (dict, list)):
            raise InvalidDataError("Invalid response format: expected dict or list", data=response)

        return response

    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """
        Get orderbook for a symbol.

        Args:
            symbol: Trading symbol
            depth: Orderbook depth

        Returns:
            Orderbook data

        Raises:
            APIError: If API returns error
            InvalidDataError: If response format is invalid
        """
        response = await self._request("GET", "/info", data={"type": "orderbook", "symbol": symbol, "depth": depth})

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        if "bids" not in response or "asks" not in response:
            raise InvalidDataError("Invalid orderbook format: missing bids or asks", data=response)

        return response

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of trades to retrieve

        Returns:
            List of recent trades

        Raises:
            APIError: If API returns error
            InvalidDataError: If response format is invalid
        """
        response = await self._request("GET", "/info", data={"type": "trades", "symbol": symbol, "limit": limit})

        if not isinstance(response, list):
            raise InvalidDataError("Invalid response format: expected list", data=response)

        return response

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current funding rate for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate data

        Raises:
            APIError: If API returns error
            InvalidDataError: If response format is invalid
        """
        response = await self._request("GET", "/info", data={"type": "fundingRate", "symbol": symbol})

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        return response

    # Account Methods

    async def get_user_state(self) -> Dict[str, Any]:
        """
        Get user state (balances, positions, orders).

        Returns:
            User state data

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
            InvalidDataError: If response format is invalid
        """
        action = {
            "type": "clearinghouseState",
            "user": self.account.address,
        }

        response = await self._request("POST", "/info", data=action, requires_auth=True)

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        return response

    async def get_balances(self) -> List[Inventory]:
        """
        Get account balances.

        Returns:
            List of Inventory entities

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
            InvalidDataError: If response format is invalid
        """
        user_state = await self.get_user_state()

        if "assetPositions" not in user_state:
            raise InvalidDataError("Invalid user state format: missing assetPositions", data=user_state)

        inventories = []
        for asset_pos in user_state.get("assetPositions", []):
            if "position" not in asset_pos or "coin" not in asset_pos:
                continue

            position = asset_pos["position"]
            coin = asset_pos["coin"]

            # Parse balance data
            free = float(position.get("szi", 0.0))
            locked = float(position.get("marginUsed", 0.0))
            total = free + locked

            inventory = Inventory(
                token=coin,
                free=max(0.0, free),
                locked=max(0.0, locked),
                total=max(0.0, total),
                chain="hyperliquid",
            )
            inventories.append(inventory)

        return inventories

    async def get_positions(self) -> List[Position]:
        """
        Get open positions.

        Returns:
            List of Position entities

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
            InvalidDataError: If response format is invalid
        """
        user_state = await self.get_user_state()

        if "assetPositions" not in user_state:
            raise InvalidDataError("Invalid user state format: missing assetPositions", data=user_state)

        positions = []
        for asset_pos in user_state.get("assetPositions", []):
            if "position" not in asset_pos or "coin" not in asset_pos:
                continue

            position_data = asset_pos["position"]
            symbol = asset_pos["coin"]

            # Parse position data
            size = float(position_data.get("szi", 0.0))
            entry_price = float(position_data.get("entryPx", 0.0))
            mark_price = float(position_data.get("markPx", entry_price))
            unrealized_pnl = float(position_data.get("unrealizedPnl", 0.0))
            funding_rate = float(position_data.get("fundingRate", 0.0))

            if abs(size) < 1e-8:  # Skip flat positions
                continue

            position = Position(
                symbol=symbol,
                size=size,
                entry_price=entry_price if entry_price > 0 else mark_price,
                mark_price=mark_price,
                unrealized_pnl=unrealized_pnl,
                funding_rate=funding_rate,
            )
            positions.append(position)

        return positions

    async def get_open_orders(self) -> List[Order]:
        """
        Get open orders.

        Returns:
            List of Order entities

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
            InvalidDataError: If response format is invalid
        """
        user_state = await self.get_user_state()

        if "openOrders" not in user_state:
            raise InvalidDataError("Invalid user state format: missing openOrders", data=user_state)

        orders = []
        for order_data in user_state.get("openOrders", []):
            try:
                order = self._parse_order(order_data)
                if order:
                    orders.append(order)
            except Exception as e:
                # Log error but continue processing other orders
                continue

        return orders

    def _parse_order(self, order_data: Dict[str, Any]) -> Optional[Order]:
        """
        Parse order data from API response.

        Args:
            order_data: Order data from API

        Returns:
            Order entity or None if invalid
        """
        try:
            # Map API fields to Order entity
            order_id = str(order_data.get("oid", ""))
            if not order_id:
                return None

            symbol = str(order_data.get("coin", ""))
            if not symbol:
                return None

            # Parse side
            side_str = str(order_data.get("side", "")).upper()
            side = OrderSide.BUY if side_str == "B" or side_str == "BUY" else OrderSide.SELL

            # Parse order type
            order_type_str = str(order_data.get("orderType", "")).upper()
            if "MARKET" in order_type_str:
                order_type = OrderType.MARKET
            elif "LIMIT" in order_type_str:
                order_type = OrderType.LIMIT
            else:
                order_type = OrderType.LIMIT  # Default

            # Parse quantities and prices
            quantity = float(order_data.get("sz", 0.0))
            price = float(order_data.get("limitPx", 0.0)) if order_data.get("limitPx") else None
            filled_quantity = float(order_data.get("filledSz", 0.0))
            average_fill_price = float(order_data.get("avgPx", 0.0)) if order_data.get("avgPx") else None

            # Parse status
            status_str = str(order_data.get("status", "")).upper()
            if "FILLED" in status_str or filled_quantity >= quantity:
                status = OrderStatus.FILLED
            elif "CANCELLED" in status_str:
                status = OrderStatus.CANCELLED
            elif filled_quantity > 0:
                status = OrderStatus.PARTIALLY_FILLED
            else:
                status = OrderStatus.OPEN

            order = Order(
                id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type=order_type,
                status=status,
                filled_quantity=filled_quantity,
                average_fill_price=average_fill_price,
                client_order_id=order_data.get("cloid"),
                reduce_only=bool(order_data.get("reduceOnly", False)),
                post_only=bool(order_data.get("postOnly", False)),
            )

            return order

        except (KeyError, ValueError, TypeError) as e:
            return None

    # Order Management Methods

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
            AuthenticationError: If authentication fails
            InvalidDataError: If response format is invalid
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if order_type == OrderType.LIMIT and (price is None or price <= 0):
            raise ValueError("Price is required for LIMIT orders")

        # Build order action
        order_spec = {
            "a": int(quantity * 1e6),  # Convert to integer (assuming 6 decimals)
            "b": side.value == "BUY",
            "p": int(price * 1e6) if price else None,
            "r": reduce_only,
            "s": symbol,
            "t": {"limit": {"tif": "Gtc"}} if order_type == OrderType.LIMIT else {"market": {}},
        }

        if post_only:
            order_spec["t"] = {"limit": {"tif": "PostOnly"}}

        if client_order_id:
            order_spec["c"] = client_order_id

        action = {
            "type": "order",
            "orders": [order_spec],
            "grouping": "na",
        }

        response = await self._request("POST", "/exchange", data=action, requires_auth=True)

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        # Check for errors in response
        if "status" in response and response["status"] == "err":
            error_msg = response.get("response", {}).get("data", "Unknown error")
            raise APIError(f"Order placement failed: {error_msg}", response_data=response)

        # Parse response to get order ID
        order_id = response.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid")

        if not order_id:
            # Try to get order from open orders
            open_orders = await self.get_open_orders()
            if open_orders and client_order_id:
                matching_order = next((o for o in open_orders if o.client_order_id == client_order_id), None)
                if matching_order:
                    return matching_order

            raise InvalidDataError("Order ID not found in response", data=response)

        # Create Order entity
        order = Order(
            id=str(order_id),
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            status=OrderStatus.PENDING,
            client_order_id=client_order_id,
            reduce_only=reduce_only,
            post_only=post_only,
        )

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
        """
        action = {
            "type": "cancel",
            "cancels": [{"oid": order_id}],
        }

        response = await self._request("POST", "/exchange", data=action, requires_auth=True)

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        # Check for errors
        if "status" in response and response["status"] == "err":
            error_msg = response.get("response", {}).get("data", "Unknown error")
            raise APIError(f"Order cancellation failed: {error_msg}", response_data=response)

        return True

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> bool:
        """
        Cancel all orders (optionally for a symbol).

        Args:
            symbol: Symbol to cancel orders for (None for all symbols)

        Returns:
            True if cancelled successfully

        Raises:
            APIError: If API returns error
            AuthenticationError: If authentication fails
        """
        open_orders = await self.get_open_orders()

        if symbol:
            open_orders = [o for o in open_orders if o.symbol == symbol]

        if not open_orders:
            return True

        # Cancel all orders
        cancels = [{"oid": order.id} for order in open_orders]

        action = {
            "type": "cancel",
            "cancels": cancels,
        }

        response = await self._request("POST", "/exchange", data=action, requires_auth=True)

        if not isinstance(response, dict):
            raise InvalidDataError("Invalid response format: expected dict", data=response)

        # Check for errors
        if "status" in response and response["status"] == "err":
            error_msg = response.get("response", {}).get("data", "Unknown error")
            raise APIError(f"Order cancellation failed: {error_msg}", response_data=response)

        return True

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "HyperliquidAPI":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


"""Tests for HyperliquidAPI."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from eth_account import Account

from alpha_trading_crypto.domain.entities.order import OrderSide, OrderType
from alpha_trading_crypto.infrastructure.adapters.hyperliquid_api import HyperliquidAPI
from alpha_trading_crypto.infrastructure.exceptions import (
    APIError,
    AuthenticationError,
    InvalidDataError,
    NetworkError,
    RateLimitError,
)


@pytest.fixture
def private_key() -> str:
    """Generate a test private key."""
    account = Account.create()
    return account.key.hex()


@pytest.fixture
def api(private_key: str) -> HyperliquidAPI:
    """Create HyperliquidAPI instance."""
    return HyperliquidAPI(private_key=private_key, testnet=True)


@pytest.fixture
def mock_response() -> MagicMock:
    """Create mock HTTP response."""
    response = MagicMock()
    response.json.return_value = {"status": "ok"}
    response.raise_for_status = MagicMock()
    return response


class TestHyperliquidAPIInitialization:
    """Test HyperliquidAPI initialization."""

    def test_init_with_valid_private_key(self, private_key: str) -> None:
        """Test initialization with valid private key."""
        api = HyperliquidAPI(private_key=private_key, testnet=True)
        assert api.testnet is True
        assert api.base_url == HyperliquidAPI.BASE_URL_TESTNET
        assert api.account is not None

    def test_init_with_invalid_private_key(self) -> None:
        """Test initialization with invalid private key."""
        with pytest.raises(ValueError, match="Invalid private key"):
            HyperliquidAPI(private_key="0xinvalid", testnet=True)

    def test_init_without_0x_prefix(self) -> None:
        """Test initialization without 0x prefix."""
        with pytest.raises(ValueError, match="must start with 0x"):
            HyperliquidAPI(private_key="invalid_key", testnet=True)

    def test_init_mainnet(self, private_key: str) -> None:
        """Test initialization with mainnet."""
        api = HyperliquidAPI(private_key=private_key, testnet=False)
        assert api.testnet is False
        assert api.base_url == HyperliquidAPI.BASE_URL_MAINNET

    def test_init_custom_timeout(self, private_key: str) -> None:
        """Test initialization with custom timeout."""
        api = HyperliquidAPI(private_key=private_key, testnet=True, timeout=60.0)
        assert api.timeout == 60.0


class TestHyperliquidAPIAuthentication:
    """Test HyperliquidAPI authentication."""

    def test_sign_message(self, api: HyperliquidAPI) -> None:
        """Test message signing."""
        message = {"type": "test", "data": "test"}
        signature = api._sign_message(message)
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_get_auth_headers(self, api: HyperliquidAPI) -> None:
        """Test getting authentication headers."""
        action = {"type": "test", "data": "test"}
        headers = api._get_auth_headers(action)
        assert "Content-Type" in headers
        assert "X-Hyperliquid-Auth" in headers
        assert isinstance(headers["X-Hyperliquid-Auth"], str)


class TestHyperliquidAPIRequest:
    """Test HyperliquidAPI request handling."""

    @pytest.mark.asyncio
    async def test_request_success_get(self, api: HyperliquidAPI, mock_response: MagicMock) -> None:
        """Test successful GET request."""
        mock_response.json.return_value = {"status": "ok", "data": "test"}
        mock_response.status_code = 200

        with patch.object(api.client, "get", new_callable=AsyncMock, return_value=mock_response):
            result = await api._request("GET", "/test", data={"param": "value"})
            assert result == {"status": "ok", "data": "test"}

    @pytest.mark.asyncio
    async def test_request_success_post(self, api: HyperliquidAPI, mock_response: MagicMock) -> None:
        """Test successful POST request."""
        mock_response.json.return_value = {"status": "ok"}
        mock_response.status_code = 200

        with patch.object(api.client, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await api._request("POST", "/test", data={"type": "test"})
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_request_with_auth(self, api: HyperliquidAPI, mock_response: MagicMock) -> None:
        """Test request with authentication."""
        mock_response.json.return_value = {"status": "ok"}
        mock_response.status_code = 200

        with patch.object(api.client, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await api._request("POST", "/test", data={"type": "test"}, requires_auth=True)
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_request_timeout(self, api: HyperliquidAPI) -> None:
        """Test request timeout."""
        import httpx

        with patch.object(api.client, "get", side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(NetworkError, match="Request timeout"):
                await api._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_network_error(self, api: HyperliquidAPI) -> None:
        """Test network error."""
        import httpx

        with patch.object(api.client, "get", side_effect=httpx.NetworkError("Network error")):
            with pytest.raises(NetworkError, match="Network error"):
                await api._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_authentication_error(self, api: HyperliquidAPI) -> None:
        """Test authentication error."""
        import httpx

        error_response = MagicMock()
        error_response.status_code = 401
        error_response.json.return_value = {"error": "Unauthorized"}

        http_error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=error_response)

        with patch.object(api.client, "post", side_effect=http_error):
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                await api._request("POST", "/test", data={"type": "test"}, requires_auth=True)

    @pytest.mark.asyncio
    async def test_request_rate_limit_error(self, api: HyperliquidAPI) -> None:
        """Test rate limit error."""
        import httpx

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.json.return_value = {"error": "Rate limit exceeded"}

        http_error = httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=error_response)

        with patch.object(api.client, "get", side_effect=http_error):
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                await api._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_api_error(self, api: HyperliquidAPI) -> None:
        """Test API error."""
        import httpx

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.json.return_value = {"error": "Internal server error"}

        http_error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=error_response)

        with patch.object(api.client, "get", side_effect=http_error):
            with pytest.raises(APIError, match="API error"):
                await api._request("GET", "/test")


class TestHyperliquidAPIMarketData:
    """Test HyperliquidAPI market data methods."""

    @pytest.mark.asyncio
    async def test_get_exchange_info_success(self, api: HyperliquidAPI) -> None:
        """Test getting exchange info successfully."""
        mock_data = {
            "universe": [
                {"name": "BTC", "maxLeverage": 20, "onlyIsolated": False},
            ],
            "meta": {"type": "meta"},
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_exchange_info()
            assert result == mock_data
            assert "universe" in result

    @pytest.mark.asyncio
    async def test_get_exchange_info_invalid_format(self, api: HyperliquidAPI) -> None:
        """Test getting exchange info with invalid format."""
        with patch.object(api, "_request", new_callable=AsyncMock, return_value="invalid"):
            with pytest.raises(InvalidDataError, match="Invalid response format"):
                await api.get_exchange_info()

    @pytest.mark.asyncio
    async def test_get_ticker_success(self, api: HyperliquidAPI) -> None:
        """Test getting ticker successfully."""
        mock_data = {"BTC": {"last": 50000.0, "volume": 1000.0}}

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_ticker()
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_ticker_with_symbol(self, api: HyperliquidAPI) -> None:
        """Test getting ticker for specific symbol."""
        mock_data = {"last": 50000.0, "volume": 1000.0}

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_ticker(symbol="BTC")
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_ticker_invalid_format(self, api: HyperliquidAPI) -> None:
        """Test getting ticker with invalid format."""
        with patch.object(api, "_request", new_callable=AsyncMock, return_value=123):
            with pytest.raises(InvalidDataError, match="Invalid response format"):
                await api.get_ticker()

    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, api: HyperliquidAPI) -> None:
        """Test getting orderbook successfully."""
        mock_data = {
            "bids": [[50000.0, 1.0], [49999.0, 2.0]],
            "asks": [[50001.0, 1.0], [50002.0, 2.0]],
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_orderbook("BTC")
            assert result == mock_data
            assert "bids" in result
            assert "asks" in result

    @pytest.mark.asyncio
    async def test_get_orderbook_missing_bids_asks(self, api: HyperliquidAPI) -> None:
        """Test getting orderbook with missing bids/asks."""
        mock_data = {"data": "invalid"}

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            with pytest.raises(InvalidDataError, match="Invalid orderbook format"):
                await api.get_orderbook("BTC")

    @pytest.mark.asyncio
    async def test_get_recent_trades_success(self, api: HyperliquidAPI) -> None:
        """Test getting recent trades successfully."""
        mock_data = [
            {"price": 50000.0, "size": 1.0, "time": 1234567890},
            {"price": 50001.0, "size": 2.0, "time": 1234567891},
        ]

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_recent_trades("BTC")
            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_recent_trades_invalid_format(self, api: HyperliquidAPI) -> None:
        """Test getting recent trades with invalid format."""
        with patch.object(api, "_request", new_callable=AsyncMock, return_value={"not": "list"}):
            with pytest.raises(InvalidDataError, match="Invalid response format"):
                await api.get_recent_trades("BTC")

    @pytest.mark.asyncio
    async def test_get_funding_rate_success(self, api: HyperliquidAPI) -> None:
        """Test getting funding rate successfully."""
        mock_data = {"fundingRate": 0.0001, "nextFundingTime": 1234567890}

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_funding_rate("BTC")
            assert result == mock_data
            assert "fundingRate" in result


class TestHyperliquidAPIAccountData:
    """Test HyperliquidAPI account data methods."""

    @pytest.mark.asyncio
    async def test_get_user_state_success(self, api: HyperliquidAPI) -> None:
        """Test getting user state successfully."""
        mock_data = {
            "assetPositions": [
                {
                    "position": {
                        "coin": "USDC",
                        "szi": 1000.0,
                        "marginUsed": 100.0,
                    },
                },
            ],
            "openOrders": [],
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await api.get_user_state()
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_user_state_invalid_format(self, api: HyperliquidAPI) -> None:
        """Test getting user state with invalid format."""
        with patch.object(api, "_request", new_callable=AsyncMock, return_value="invalid"):
            with pytest.raises(InvalidDataError, match="Invalid response format"):
                await api.get_user_state()

    @pytest.mark.asyncio
    async def test_get_balances_success(self, api: HyperliquidAPI) -> None:
        """Test getting balances successfully."""
        mock_data = {
            "assetPositions": [
                {
                    "coin": "USDC",
                    "position": {
                        "szi": 1000.0,
                        "marginUsed": 100.0,
                    },
                },
                {
                    "coin": "BTC",
                    "position": {
                        "szi": 0.1,
                        "marginUsed": 0.0,
                    },
                },
            ],
        }

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            inventories = await api.get_balances()
            assert len(inventories) == 2
            assert inventories[0].token == "USDC"
            assert inventories[0].free == 1000.0
            assert inventories[0].locked == 100.0
            assert inventories[0].total == 1100.0

    @pytest.mark.asyncio
    async def test_get_balances_missing_asset_positions(self, api: HyperliquidAPI) -> None:
        """Test getting balances with missing assetPositions."""
        mock_data = {}

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            with pytest.raises(InvalidDataError, match="Invalid user state format"):
                await api.get_balances()

    @pytest.mark.asyncio
    async def test_get_positions_success(self, api: HyperliquidAPI) -> None:
        """Test getting positions successfully."""
        mock_data = {
            "assetPositions": [
                {
                    "coin": "BTC",
                    "position": {
                        "szi": 0.1,
                        "entryPx": 50000.0,
                        "markPx": 51000.0,
                        "unrealizedPnl": 100.0,
                        "fundingRate": 0.0001,
                    },
                },
            ],
        }

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            positions = await api.get_positions()
            assert len(positions) == 1
            assert positions[0].symbol == "BTC"
            assert positions[0].size == 0.1
            assert positions[0].entry_price == 50000.0
            assert positions[0].mark_price == 51000.0
            assert positions[0].unrealized_pnl == 100.0

    @pytest.mark.asyncio
    async def test_get_positions_skip_flat(self, api: HyperliquidAPI) -> None:
        """Test getting positions skips flat positions."""
        mock_data = {
            "assetPositions": [
                {
                    "coin": "BTC",
                    "position": {
                        "szi": 0.0,
                        "entryPx": 50000.0,
                        "markPx": 51000.0,
                    },
                },
            ],
        }

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            positions = await api.get_positions()
            assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_get_open_orders_success(self, api: HyperliquidAPI) -> None:
        """Test getting open orders successfully."""
        mock_data = {
            "openOrders": [
                {
                    "oid": "order123",
                    "coin": "BTC",
                    "side": "B",
                    "sz": 0.1,
                    "limitPx": 50000.0,
                    "orderType": "Limit",
                    "filledSz": 0.0,
                    "status": "open",
                },
            ],
        }

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            orders = await api.get_open_orders()
            assert len(orders) == 1
            assert orders[0].id == "order123"
            assert orders[0].symbol == "BTC"
            assert orders[0].side == OrderSide.BUY

    @pytest.mark.asyncio
    async def test_get_open_orders_invalid_format(self, api: HyperliquidAPI) -> None:
        """Test getting open orders with invalid format."""
        mock_data = {}

        with patch.object(api, "get_user_state", new_callable=AsyncMock, return_value=mock_data):
            with pytest.raises(InvalidDataError, match="Invalid user state format"):
                await api.get_open_orders()


class TestHyperliquidAPIOrderParsing:
    """Test HyperliquidAPI order parsing."""

    def test_parse_order_valid(self, api: HyperliquidAPI) -> None:
        """Test parsing valid order."""
        order_data = {
            "oid": "order123",
            "coin": "BTC",
            "side": "B",
            "sz": 0.1,
            "limitPx": 50000.0,
            "orderType": "Limit",
            "filledSz": 0.0,
            "status": "open",
            "cloid": "client123",
            "reduceOnly": False,
            "postOnly": False,
        }

        order = api._parse_order(order_data)
        assert order is not None
        assert order.id == "order123"
        assert order.symbol == "BTC"
        assert order.side == OrderSide.BUY
        assert order.quantity == 0.1
        assert order.price == 50000.0

    def test_parse_order_missing_id(self, api: HyperliquidAPI) -> None:
        """Test parsing order with missing ID."""
        order_data = {"coin": "BTC", "side": "B"}

        order = api._parse_order(order_data)
        assert order is None

    def test_parse_order_missing_symbol(self, api: HyperliquidAPI) -> None:
        """Test parsing order with missing symbol."""
        order_data = {"oid": "order123", "side": "B"}

        order = api._parse_order(order_data)
        assert order is None

    def test_parse_order_sell_side(self, api: HyperliquidAPI) -> None:
        """Test parsing sell order."""
        order_data = {
            "oid": "order123",
            "coin": "BTC",
            "side": "S",
            "sz": 0.1,
            "limitPx": 50000.0,
            "orderType": "Limit",
            "filledSz": 0.0,
        }

        order = api._parse_order(order_data)
        assert order is not None
        assert order.side == OrderSide.SELL

    def test_parse_order_market_type(self, api: HyperliquidAPI) -> None:
        """Test parsing market order."""
        order_data = {
            "oid": "order123",
            "coin": "BTC",
            "side": "B",
            "sz": 0.1,
            "orderType": "Market",
            "filledSz": 0.0,
        }

        order = api._parse_order(order_data)
        assert order is not None
        assert order.order_type == OrderType.MARKET

    def test_parse_order_filled_status(self, api: HyperliquidAPI) -> None:
        """Test parsing filled order."""
        order_data = {
            "oid": "order123",
            "coin": "BTC",
            "side": "B",
            "sz": 0.1,
            "limitPx": 50000.0,
            "orderType": "Limit",
            "filledSz": 0.1,
            "status": "filled",
        }

        order = api._parse_order(order_data)
        assert order is not None
        assert order.status.value == "FILLED"

    def test_parse_order_partially_filled(self, api: HyperliquidAPI) -> None:
        """Test parsing partially filled order."""
        order_data = {
            "oid": "order123",
            "coin": "BTC",
            "side": "B",
            "sz": 0.1,
            "limitPx": 50000.0,
            "orderType": "Limit",
            "filledSz": 0.05,
            "status": "open",
        }

        order = api._parse_order(order_data)
        assert order is not None
        assert order.status.value == "PARTIALLY_FILLED"


class TestHyperliquidAPIOrderManagement:
    """Test HyperliquidAPI order management methods."""

    @pytest.mark.asyncio
    async def test_place_order_market_success(self, api: HyperliquidAPI) -> None:
        """Test placing market order successfully."""
        mock_response = {
            "response": {
                "data": {
                    "statuses": [
                        {
                            "resting": {
                                "oid": "order123",
                            },
                        },
                    ],
                },
            },
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
            order = await api.place_order(
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.MARKET,
            )
            assert order.id == "order123"
            assert order.symbol == "BTC"
            assert order.side == OrderSide.BUY
            assert order.quantity == 0.1

    @pytest.mark.asyncio
    async def test_place_order_limit_success(self, api: HyperliquidAPI) -> None:
        """Test placing limit order successfully."""
        mock_response = {
            "response": {
                "data": {
                    "statuses": [
                        {
                            "resting": {
                                "oid": "order123",
                            },
                        },
                    ],
                },
            },
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
            order = await api.place_order(
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.LIMIT,
                price=50000.0,
            )
            assert order.id == "order123"
            assert order.price == 50000.0

    @pytest.mark.asyncio
    async def test_place_order_invalid_quantity(self, api: HyperliquidAPI) -> None:
        """Test placing order with invalid quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await api.place_order(
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=-0.1,
                order_type=OrderType.MARKET,
            )

    @pytest.mark.asyncio
    async def test_place_order_limit_missing_price(self, api: HyperliquidAPI) -> None:
        """Test placing limit order without price."""
        with pytest.raises(ValueError, match="Price is required for LIMIT orders"):
            await api.place_order(
                symbol="BTC",
                side=OrderSide.BUY,
                quantity=0.1,
                order_type=OrderType.LIMIT,
            )

    @pytest.mark.asyncio
    async def test_place_order_api_error(self, api: HyperliquidAPI) -> None:
        """Test placing order with API error."""
        mock_response = {
            "status": "err",
            "response": {
                "data": "Insufficient balance",
            },
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(APIError, match="Order placement failed"):
                await api.place_order(
                    symbol="BTC",
                    side=OrderSide.BUY,
                    quantity=0.1,
                    order_type=OrderType.MARKET,
                )

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, api: HyperliquidAPI) -> None:
        """Test cancelling order successfully."""
        mock_response = {"status": "ok"}

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await api.cancel_order("order123")
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_api_error(self, api: HyperliquidAPI) -> None:
        """Test cancelling order with API error."""
        mock_response = {
            "status": "err",
            "response": {
                "data": "Order not found",
            },
        }

        with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(APIError, match="Order cancellation failed"):
                await api.cancel_order("order123")

    @pytest.mark.asyncio
    async def test_cancel_all_orders_success(self, api: HyperliquidAPI) -> None:
        """Test cancelling all orders successfully."""
        mock_open_orders = [
            MagicMock(id="order1", symbol="BTC"),
            MagicMock(id="order2", symbol="ETH"),
        ]

        mock_response = {"status": "ok"}

        with patch.object(api, "get_open_orders", new_callable=AsyncMock, return_value=mock_open_orders):
            with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
                result = await api.cancel_all_orders()
                assert result is True

    @pytest.mark.asyncio
    async def test_cancel_all_orders_for_symbol(self, api: HyperliquidAPI) -> None:
        """Test cancelling all orders for a symbol."""
        mock_open_orders = [
            MagicMock(id="order1", symbol="BTC"),
            MagicMock(id="order2", symbol="ETH"),
        ]

        mock_response = {"status": "ok"}

        with patch.object(api, "get_open_orders", new_callable=AsyncMock, return_value=mock_open_orders):
            with patch.object(api, "_request", new_callable=AsyncMock, return_value=mock_response):
                result = await api.cancel_all_orders(symbol="BTC")
                assert result is True


class TestHyperliquidAPIContextManager:
    """Test HyperliquidAPI context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self, private_key: str) -> None:
        """Test async context manager."""
        async with HyperliquidAPI(private_key=private_key, testnet=True) as api:
            assert api is not None
            # Client should be closed after context exit
        # Verify client is closed (would raise error if trying to use)


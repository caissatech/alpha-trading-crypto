"""Alpha Trading Crypto - Trading system for crypto perp futures on Hyperliquid."""

__version__ = "0.1.0"

from alpha_trading_crypto.domain.entities import (
    Inventory,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Token,
    Transfer,
    TransferStatus,
)
from alpha_trading_crypto.domain.services import (
    InventoryManager,
    OrderManager,
    PositionManager,
    TransferManager,
)
from alpha_trading_crypto.infrastructure import (
    BacktestEngine,
    BacktestResult,
    EthereumProvider,
    HyperliquidAPI,
    TokenTransferService,
)

__all__ = [
    "__version__",
    # Entities
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "Position",
    "Inventory",
    "Token",
    "Transfer",
    "TransferStatus",
    # Services
    "OrderManager",
    "InventoryManager",
    "PositionManager",
    "TransferManager",
    # Infrastructure
    "HyperliquidAPI",
    "BacktestEngine",
    "BacktestResult",
    "EthereumProvider",
    "TokenTransferService",
]

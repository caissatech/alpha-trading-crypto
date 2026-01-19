"""Blockchain port (interface) for blockchain operations."""

from abc import ABC, abstractmethod
from typing import Optional

from alpha_trading_crypto.domain.entities.transfer import Transfer


class BlockchainPort(ABC):
    """
    Blockchain port interface.

    Defines the contract for blockchain operations (transfers, etc.).
    """

    @abstractmethod
    def initiate_transfer_to_hyperliquid(
        self,
        token: str,
        amount: float,
        decimals: int = 6,
    ) -> Transfer:
        """
        Initiate transfer from Ethereum to Hyperliquid.

        Args:
            token: Token symbol (e.g., "USDC")
            amount: Amount to transfer
            decimals: Token decimals (default 6 for USDC)

        Returns:
            Transfer entity

        Raises:
            ValueError: If parameters are invalid
            TransactionError: If transfer fails
        """
        pass

    @abstractmethod
    def initiate_transfer_to_ethereum(
        self,
        token: str,
        amount: float,
        recipient_address: str,
        decimals: int = 6,
    ) -> Transfer:
        """
        Initiate transfer from Hyperliquid to Ethereum.

        Args:
            token: Token symbol (e.g., "USDC")
            amount: Amount to transfer
            recipient_address: Ethereum address to receive tokens
            decimals: Token decimals (default 6 for USDC)

        Returns:
            Transfer entity

        Raises:
            ValueError: If parameters are invalid
            TransactionError: If transfer fails
        """
        pass

    @abstractmethod
    def track_transfer(self, transfer: Transfer) -> Transfer:
        """
        Track transfer status.

        Args:
            transfer: Transfer entity to track

        Returns:
            Updated transfer entity

        Raises:
            TransactionError: If tracking fails
        """
        pass


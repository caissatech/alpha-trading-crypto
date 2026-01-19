"""Blockchain adapter implementing BlockchainPort."""

from typing import Optional

from alpha_trading_crypto.application.ports.blockchain_port import BlockchainPort
from alpha_trading_crypto.domain.entities.transfer import Transfer
from alpha_trading_crypto.infrastructure.blockchain.token_transfer_service import TokenTransferService


class BlockchainAdapter(BlockchainPort):
    """
    Blockchain adapter.

    Implements BlockchainPort using TokenTransferService.
    """

    def __init__(self, transfer_service: TokenTransferService) -> None:
        """
        Initialize blockchain adapter.

        Args:
            transfer_service: TokenTransferService instance
        """
        self.transfer_service = transfer_service

    def initiate_transfer_to_hyperliquid(
        self,
        token: str,
        amount: float,
        decimals: int = 6,
    ) -> Transfer:
        """Initiate transfer from Ethereum to Hyperliquid."""
        return self.transfer_service.initiate_transfer_to_hyperliquid(
            token=token,
            amount=amount,
            decimals=decimals,
        )

    def initiate_transfer_to_ethereum(
        self,
        token: str,
        amount: float,
        recipient_address: str,
        decimals: int = 6,
    ) -> Transfer:
        """Initiate transfer from Hyperliquid to Ethereum."""
        return self.transfer_service.initiate_transfer_to_ethereum(
            token=token,
            amount=amount,
            recipient_address=recipient_address,
            decimals=decimals,
        )

    def track_transfer(self, transfer: Transfer) -> Transfer:
        """Track transfer status."""
        return self.transfer_service.track_transfer(transfer)


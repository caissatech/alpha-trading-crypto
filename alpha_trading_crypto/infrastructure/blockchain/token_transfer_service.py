"""Token transfer service for Ethereum ↔ Hyperliquid transfers."""

import uuid
from datetime import datetime
from typing import Dict, Optional

from web3 import Web3

from alpha_trading_crypto.domain.entities.transfer import Transfer, TransferStatus
from alpha_trading_crypto.infrastructure.blockchain.ethereum_provider import EthereumProvider
from alpha_trading_crypto.infrastructure.exceptions import BlockchainError, TransactionError


class TokenTransferService:
    """
    Token transfer service.

    Handles token transfers between Ethereum and Hyperliquid.
    """

    # Common token addresses (mainnet)
    TOKEN_ADDRESSES = {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    }

    # Hyperliquid bridge address
    HYPERLIQUID_BRIDGE_ADDRESS = "0x0000000000000000000000000000000000000000"  # TODO: Replace with actual address

    def __init__(self, ethereum_provider: EthereumProvider) -> None:
        """
        Initialize token transfer service.

        Args:
            ethereum_provider: Ethereum provider instance

        Raises:
            ValueError: If ethereum provider is invalid
        """
        if not isinstance(ethereum_provider, EthereumProvider):
            raise ValueError("Ethereum provider is required")

        if not ethereum_provider.account:
            raise ValueError("Ethereum provider must have a private key")

        self.ethereum_provider = ethereum_provider
        self.web3 = ethereum_provider.web3

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
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if token not in self.TOKEN_ADDRESSES:
            raise ValueError(f"Token {token} not supported")

        token_address = self.TOKEN_ADDRESSES[token]
        amount_wei = int(amount * (10**decimals))

        # Create transfer entity
        transfer = Transfer(
            id=str(uuid.uuid4()),
            from_chain="ethereum",
            to_chain="hyperliquid",
            token=token,
            amount=amount,
            status=TransferStatus.INITIATED,
        )

        try:
            # Build transaction
            # Note: This is a simplified version. Actual implementation would need
            # to interact with Hyperliquid bridge contract
            transaction = {
                "to": self.HYPERLIQUID_BRIDGE_ADDRESS,
                "value": 0,
                "data": self._encode_transfer_data(token_address, amount_wei),
            }

            # Estimate gas
            gas = self.ethereum_provider.estimate_gas(transaction)
            transaction["gas"] = gas

            # Send transaction
            tx_hash = self.ethereum_provider.send_transaction(transaction)
            transfer.tx_hash = tx_hash
            transfer.status = TransferStatus.INITIATED

            return transfer

        except Exception as e:
            transfer.status = TransferStatus.FAILED
            raise TransactionError(f"Failed to initiate transfer: {e}") from e

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
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if not self.web3.is_address(recipient_address):
            raise ValueError(f"Invalid recipient address: {recipient_address}")

        # Create transfer entity
        transfer = Transfer(
            id=str(uuid.uuid4()),
            from_chain="hyperliquid",
            to_chain="ethereum",
            token=token,
            amount=amount,
            status=TransferStatus.INITIATED,
        )

        # Note: Actual implementation would need to interact with Hyperliquid API
        # to initiate withdrawal. This is a placeholder.
        transfer.status = TransferStatus.PENDING

        return transfer

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
        if transfer.from_chain == "ethereum" and transfer.tx_hash:
            # Track Ethereum transaction
            receipt = self.ethereum_provider.get_transaction_receipt(transfer.tx_hash)

            if receipt:
                if receipt.status == 1:
                    transfer.status = TransferStatus.CONFIRMED
                    transfer.block_number = receipt.blockNumber
                    transfer.confirmed_at = datetime.utcnow()

                    # Get gas fee
                    tx = self.ethereum_provider.get_transaction(transfer.tx_hash)
                    if tx:
                        gas_used = receipt.gasUsed
                        gas_price = tx.get("gasPrice", 0)
                        transfer.gas_fee = float(self.web3.from_wei(gas_used * gas_price, "ether"))

                    # Check if transfer is completed (would need to check bridge status)
                    # For now, mark as confirmed
                    transfer.status = TransferStatus.CONFIRMED
                else:
                    transfer.status = TransferStatus.FAILED

        elif transfer.from_chain == "hyperliquid":
            # Track Hyperliquid withdrawal
            # Note: Would need to query Hyperliquid API for withdrawal status
            # This is a placeholder
            pass

        return transfer

    def _encode_transfer_data(self, token_address: str, amount: int) -> str:
        """
        Encode transfer data for bridge contract.

        Args:
            token_address: Token contract address
            amount: Amount in token's smallest unit

        Returns:
            Encoded data as hex string
        """
        # Simplified encoding. Actual implementation would need ABI encoding
        # This is a placeholder
        return "0x" + token_address[2:] + hex(amount)[2:].zfill(64)

    def get_token_balance(self, token: str, address: Optional[str] = None) -> float:
        """
        Get token balance for an address.

        Args:
            token: Token symbol
            address: Ethereum address (default: provider's address)

        Returns:
            Token balance

        Raises:
            ValueError: If token is not supported
            BlockchainError: If balance check fails
        """
        if token not in self.TOKEN_ADDRESSES:
            raise ValueError(f"Token {token} not supported")

        if not address:
            if not self.ethereum_provider.address:
                raise BlockchainError("No address available")
            address = self.ethereum_provider.address

        token_address = self.TOKEN_ADDRESSES[token]

        try:
            # ERC20 balanceOf(address) function
            # This is a simplified version. Actual implementation would need
            # to call the contract's balanceOf function
            # For now, return 0 as placeholder
            return 0.0
        except Exception as e:
            raise BlockchainError(f"Failed to get token balance: {e}") from e


"""Ethereum provider for Web3 interactions."""

from typing import Any, Dict, Optional

from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from alpha_trading_crypto.infrastructure.exceptions import BlockchainError, NetworkError, TransactionError


class EthereumProvider:
    """
    Ethereum provider.

    Handles Web3 interactions for Ethereum blockchain.
    """

    # Common RPC endpoints
    MAINNET_RPC = "https://eth.llamarpc.com"
    SEPOLIA_RPC = "https://sepolia.infura.io/v3/YOUR_PROJECT_ID"

    def __init__(
        self,
        rpc_url: str,
        private_key: Optional[str] = None,
        chain_id: Optional[int] = None,
    ) -> None:
        """
        Initialize Ethereum provider.

        Args:
            rpc_url: RPC endpoint URL
            private_key: Private key for signing transactions (optional)
            chain_id: Chain ID (optional, will be fetched if not provided)

        Raises:
            ValueError: If RPC URL is invalid
            BlockchainError: If connection fails
        """
        if not rpc_url:
            raise ValueError("RPC URL is required")

        try:
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not self.web3.is_connected():
                raise BlockchainError(f"Failed to connect to Ethereum RPC: {rpc_url}")
        except Exception as e:
            raise BlockchainError(f"Failed to initialize Ethereum provider: {e}") from e

        self.rpc_url = rpc_url
        self.account = None
        if private_key:
            try:
                if not private_key.startswith("0x"):
                    private_key = "0x" + private_key
                self.account = Account.from_key(private_key)
            except Exception as e:
                raise ValueError(f"Invalid private key: {e}") from e

        self.chain_id = chain_id or self.web3.eth.chain_id

    def get_balance(self, address: str) -> int:
        """
        Get balance for an address.

        Args:
            address: Ethereum address

        Returns:
            Balance in wei

        Raises:
            ValueError: If address is invalid
            NetworkError: If network error occurs
        """
        if not self.web3.is_address(address):
            raise ValueError(f"Invalid Ethereum address: {address}")

        try:
            balance = self.web3.eth.get_balance(address)
            return balance
        except Exception as e:
            raise NetworkError(f"Failed to get balance: {e}") from e

    def get_balance_eth(self, address: str) -> float:
        """
        Get balance in ETH for an address.

        Args:
            address: Ethereum address

        Returns:
            Balance in ETH
        """
        balance_wei = self.get_balance(address)
        return self.web3.from_wei(balance_wei, "ether")

    def get_transaction_count(self, address: str) -> int:
        """
        Get transaction count (nonce) for an address.

        Args:
            address: Ethereum address

        Returns:
            Transaction count

        Raises:
            ValueError: If address is invalid
            NetworkError: If network error occurs
        """
        if not self.web3.is_address(address):
            raise ValueError(f"Invalid Ethereum address: {address}")

        try:
            nonce = self.web3.eth.get_transaction_count(address)
            return nonce
        except Exception as e:
            raise NetworkError(f"Failed to get transaction count: {e}") from e

    def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Gas price in wei

        Raises:
            NetworkError: If network error occurs
        """
        try:
            gas_price = self.web3.eth.gas_price
            return gas_price
        except Exception as e:
            raise NetworkError(f"Failed to get gas price: {e}") from e

    def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for a transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Estimated gas

        Raises:
            TransactionError: If gas estimation fails
        """
        try:
            gas = self.web3.eth.estimate_gas(transaction)
            return gas
        except Exception as e:
            raise TransactionError(f"Failed to estimate gas: {e}") from e

    def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Send a signed transaction.

        Args:
            transaction: Signed transaction dictionary

        Returns:
            Transaction hash

        Raises:
            TransactionError: If transaction fails
        """
        if not self.account:
            raise BlockchainError("Private key not provided, cannot send transaction")

        try:
            # Build transaction
            if "nonce" not in transaction:
                transaction["nonce"] = self.get_transaction_count(self.account.address)

            if "chainId" not in transaction:
                transaction["chainId"] = self.chain_id

            if "gasPrice" not in transaction:
                transaction["gasPrice"] = self.get_gas_price()

            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            return tx_hash.hex()
        except Exception as e:
            raise TransactionError(f"Failed to send transaction: {e}") from e

    def wait_for_transaction(self, tx_hash: str, timeout: int = 300) -> TxReceipt:
        """
        Wait for transaction to be mined.

        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds

        Returns:
            Transaction receipt

        Raises:
            TransactionError: If transaction fails or times out
        """
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            if receipt.status == 0:
                raise TransactionError(f"Transaction failed: {tx_hash}")
            return receipt
        except Exception as e:
            raise TransactionError(f"Failed to wait for transaction: {e}") from e

    def get_transaction_receipt(self, tx_hash: str) -> Optional[TxReceipt]:
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt or None if not found

        Raises:
            NetworkError: If network error occurs
        """
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            return receipt
        except Exception:
            return None

    def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction details.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction dictionary or None if not found

        Raises:
            NetworkError: If network error occurs
        """
        try:
            tx = self.web3.eth.get_transaction(tx_hash)
            return dict(tx)
        except Exception:
            return None

    def is_connected(self) -> bool:
        """
        Check if connected to Ethereum network.

        Returns:
            True if connected
        """
        return self.web3.is_connected()

    @property
    def address(self) -> Optional[str]:
        """
        Get account address.

        Returns:
            Account address or None if no account
        """
        return self.account.address if self.account else None


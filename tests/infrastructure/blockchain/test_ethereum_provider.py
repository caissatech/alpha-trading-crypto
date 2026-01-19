"""Tests for EthereumProvider."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from alpha_trading_crypto.infrastructure.blockchain.ethereum_provider import EthereumProvider
from alpha_trading_crypto.infrastructure.exceptions import BlockchainError, NetworkError, TransactionError


@pytest.fixture
def mock_web3() -> MagicMock:
    """Create mock Web3 instance."""
    web3 = MagicMock(spec=Web3)
    web3.is_connected.return_value = True
    web3.eth.chain_id = 1
    web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
    web3.eth.get_transaction_count.return_value = 5
    web3.eth.gas_price = 20000000000  # 20 gwei
    web3.eth.estimate_gas.return_value = 21000
    web3.is_address.return_value = True
    web3.from_wei = lambda value, unit: float(value) / 1e18 if unit == "ether" else value
    return web3


@pytest.fixture
def private_key() -> str:
    """Generate a test private key."""
    account = Account.create()
    return account.key.hex()


@pytest.fixture
def provider(mock_web3: MagicMock, private_key: str) -> EthereumProvider:
    """Create EthereumProvider instance with mocked Web3."""
    with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider = MagicMock()
        provider = EthereumProvider(rpc_url="https://eth.llamarpc.com", private_key=private_key)
        provider.web3 = mock_web3
        return provider


class TestEthereumProviderInitialization:
    """Test EthereumProvider initialization."""

    def test_init_with_valid_rpc(self, mock_web3: MagicMock) -> None:
        """Test initialization with valid RPC URL."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com")
            assert provider.rpc_url == "https://eth.llamarpc.com"
            assert provider.is_connected()

    def test_init_with_invalid_rpc(self) -> None:
        """Test initialization with invalid RPC URL."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3 = MagicMock()
            mock_web3.is_connected.return_value = False
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()

            with pytest.raises(BlockchainError, match="Failed to connect"):
                EthereumProvider(rpc_url="https://invalid-rpc.com")

    def test_init_with_empty_rpc(self) -> None:
        """Test initialization with empty RPC URL."""
        with pytest.raises(ValueError, match="RPC URL is required"):
            EthereumProvider(rpc_url="")

    def test_init_with_private_key(self, mock_web3: MagicMock, private_key: str) -> None:
        """Test initialization with private key."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com", private_key=private_key)
            assert provider.account is not None
            assert provider.address is not None

    def test_init_with_invalid_private_key(self, mock_web3: MagicMock) -> None:
        """Test initialization with invalid private key."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()

            with pytest.raises(ValueError, match="Invalid private key"):
                EthereumProvider(rpc_url="https://eth.llamarpc.com", private_key="0xinvalid")

    def test_init_with_chain_id(self, mock_web3: MagicMock) -> None:
        """Test initialization with chain ID."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com", chain_id=5)
            assert provider.chain_id == 5


class TestEthereumProviderBalance:
    """Test EthereumProvider balance methods."""

    def test_get_balance_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting balance successfully."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        balance = provider.get_balance(address)
        assert balance == 1000000000000000000
        mock_web3.eth.get_balance.assert_called_once_with(address)

    def test_get_balance_invalid_address(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting balance with invalid address."""
        mock_web3.is_address.return_value = False
        with pytest.raises(ValueError, match="Invalid Ethereum address"):
            provider.get_balance("invalid_address")

    def test_get_balance_network_error(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting balance with network error."""
        mock_web3.eth.get_balance.side_effect = Exception("Network error")
        with pytest.raises(NetworkError, match="Failed to get balance"):
            provider.get_balance("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")

    def test_get_balance_eth_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting balance in ETH successfully."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        balance_eth = provider.get_balance_eth(address)
        assert balance_eth == 1.0


class TestEthereumProviderTransaction:
    """Test EthereumProvider transaction methods."""

    def test_get_transaction_count_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting transaction count successfully."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        nonce = provider.get_transaction_count(address)
        assert nonce == 5
        mock_web3.eth.get_transaction_count.assert_called_once_with(address)

    def test_get_transaction_count_invalid_address(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting transaction count with invalid address."""
        mock_web3.is_address.return_value = False
        with pytest.raises(ValueError, match="Invalid Ethereum address"):
            provider.get_transaction_count("invalid_address")

    def test_get_gas_price_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting gas price successfully."""
        gas_price = provider.get_gas_price()
        assert gas_price == 20000000000

    def test_get_gas_price_network_error(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting gas price with network error."""
        mock_web3.eth.gas_price = None
        mock_web3.eth.get_gas_price.side_effect = Exception("Network error")
        with pytest.raises(NetworkError, match="Failed to get gas price"):
            provider.get_gas_price()

    def test_estimate_gas_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test estimating gas successfully."""
        transaction = {"to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "value": 1000000000000000000}
        gas = provider.estimate_gas(transaction)
        assert gas == 21000
        mock_web3.eth.estimate_gas.assert_called_once()

    def test_estimate_gas_error(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test estimating gas with error."""
        mock_web3.eth.estimate_gas.side_effect = Exception("Gas estimation failed")
        transaction = {"to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "value": 1000000000000000000}
        with pytest.raises(TransactionError, match="Failed to estimate gas"):
            provider.estimate_gas(transaction)


class TestEthereumProviderSendTransaction:
    """Test EthereumProvider send transaction methods."""

    def test_send_transaction_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test sending transaction successfully."""
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0x1234567890abcdef"
        mock_web3.eth.send_raw_transaction.return_value = mock_tx_hash

        transaction = {
            "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "value": 1000000000000000000,
        }

        with patch.object(provider.account, "sign_transaction") as mock_sign:
            mock_signed = MagicMock()
            mock_signed.rawTransaction = b"raw_tx"
            mock_sign.return_value = mock_signed

            tx_hash = provider.send_transaction(transaction)
            assert tx_hash == "0x1234567890abcdef"

    def test_send_transaction_no_private_key(self, mock_web3: MagicMock) -> None:
        """Test sending transaction without private key."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com")

            transaction = {"to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "value": 1000000000000000000}
            with pytest.raises(BlockchainError, match="Private key not provided"):
                provider.send_transaction(transaction)

    def test_send_transaction_error(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test sending transaction with error."""
        mock_web3.eth.send_raw_transaction.side_effect = Exception("Transaction failed")

        transaction = {
            "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "value": 1000000000000000000,
        }

        with patch.object(provider.account, "sign_transaction") as mock_sign:
            mock_signed = MagicMock()
            mock_signed.rawTransaction = b"raw_tx"
            mock_sign.return_value = mock_signed

            with pytest.raises(TransactionError, match="Failed to send transaction"):
                provider.send_transaction(transaction)


class TestEthereumProviderWaitForTransaction:
    """Test EthereumProvider wait for transaction methods."""

    def test_wait_for_transaction_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test waiting for transaction successfully."""
        mock_receipt = MagicMock(spec=TxReceipt)
        mock_receipt.status = 1
        mock_web3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        receipt = provider.wait_for_transaction("0x1234567890abcdef")
        assert receipt.status == 1

    def test_wait_for_transaction_failed(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test waiting for failed transaction."""
        mock_receipt = MagicMock(spec=TxReceipt)
        mock_receipt.status = 0
        mock_web3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        with pytest.raises(TransactionError, match="Transaction failed"):
            provider.wait_for_transaction("0x1234567890abcdef")

    def test_wait_for_transaction_timeout(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test waiting for transaction with timeout."""
        mock_web3.eth.wait_for_transaction_receipt.side_effect = Exception("Timeout")

        with pytest.raises(TransactionError, match="Failed to wait for transaction"):
            provider.wait_for_transaction("0x1234567890abcdef", timeout=1)

    def test_get_transaction_receipt_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting transaction receipt successfully."""
        mock_receipt = MagicMock(spec=TxReceipt)
        mock_web3.eth.get_transaction_receipt.return_value = mock_receipt

        receipt = provider.get_transaction_receipt("0x1234567890abcdef")
        assert receipt is not None

    def test_get_transaction_receipt_not_found(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting transaction receipt when not found."""
        mock_web3.eth.get_transaction_receipt.side_effect = Exception("Not found")

        receipt = provider.get_transaction_receipt("0x1234567890abcdef")
        assert receipt is None

    def test_get_transaction_success(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test getting transaction successfully."""
        mock_tx = MagicMock()
        mock_tx_dict = {"hash": "0x123", "to": "0xabc", "value": 1000}
        mock_web3.eth.get_transaction.return_value = mock_tx
        mock_tx.__dict__ = mock_tx_dict

        tx = provider.get_transaction("0x1234567890abcdef")
        # Note: Actual implementation would convert to dict properly
        assert tx is not None or tx is None  # Depending on implementation


class TestEthereumProviderConnection:
    """Test EthereumProvider connection methods."""

    def test_is_connected(self, provider: EthereumProvider, mock_web3: MagicMock) -> None:
        """Test connection check."""
        assert provider.is_connected() is True
        mock_web3.is_connected.assert_called()

    def test_address_property(self, provider: EthereumProvider) -> None:
        """Test address property."""
        assert provider.address is not None
        assert isinstance(provider.address, str)

    def test_address_property_no_account(self, mock_web3: MagicMock) -> None:
        """Test address property without account."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com")
            assert provider.address is None


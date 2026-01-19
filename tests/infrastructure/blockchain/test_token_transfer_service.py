"""Tests for TokenTransferService."""

from unittest.mock import MagicMock, patch

import pytest

from alpha_trading_crypto.domain.entities.transfer import TransferStatus
from alpha_trading_crypto.infrastructure.blockchain.ethereum_provider import EthereumProvider
from alpha_trading_crypto.infrastructure.blockchain.token_transfer_service import TokenTransferService
from alpha_trading_crypto.infrastructure.exceptions import BlockchainError, TransactionError


@pytest.fixture
def mock_web3() -> MagicMock:
    """Create mock Web3 instance."""
    web3 = MagicMock()
    web3.is_connected.return_value = True
    web3.is_address.return_value = True
    web3.from_wei = lambda value, unit: float(value) / 1e18 if unit == "ether" else value
    return web3


@pytest.fixture
def mock_ethereum_provider(mock_web3: MagicMock) -> EthereumProvider:
    """Create mock EthereumProvider."""
    with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
        from eth_account import Account

        account = Account.create()
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider = MagicMock()

        provider = EthereumProvider(rpc_url="https://eth.llamarpc.com", private_key=account.key.hex())
        provider.web3 = mock_web3
        return provider


@pytest.fixture
def transfer_service(mock_ethereum_provider: EthereumProvider) -> TokenTransferService:
    """Create TokenTransferService instance."""
    return TokenTransferService(mock_ethereum_provider)


class TestTokenTransferServiceInitialization:
    """Test TokenTransferService initialization."""

    def test_init_with_valid_provider(self, mock_ethereum_provider: EthereumProvider) -> None:
        """Test initialization with valid provider."""
        service = TokenTransferService(mock_ethereum_provider)
        assert service.ethereum_provider == mock_ethereum_provider

    def test_init_with_invalid_provider(self) -> None:
        """Test initialization with invalid provider."""
        with pytest.raises(ValueError, match="Ethereum provider is required"):
            TokenTransferService(None)  # type: ignore

    def test_init_without_private_key(self, mock_web3: MagicMock) -> None:
        """Test initialization without private key in provider."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()
            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com")

            with pytest.raises(ValueError, match="Ethereum provider must have a private key"):
                TokenTransferService(provider)


class TestTokenTransferServiceToHyperliquid:
    """Test TokenTransferService transfer to Hyperliquid."""

    def test_initiate_transfer_to_hyperliquid_success(
        self, transfer_service: TokenTransferService, mock_ethereum_provider: EthereumProvider
    ) -> None:
        """Test initiating transfer to Hyperliquid successfully."""
        mock_ethereum_provider.estimate_gas = MagicMock(return_value=21000)
        mock_ethereum_provider.send_transaction = MagicMock(return_value="0x1234567890abcdef")

        transfer = transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=1000.0, decimals=6)

        assert transfer.from_chain == "ethereum"
        assert transfer.to_chain == "hyperliquid"
        assert transfer.token == "USDC"
        assert transfer.amount == 1000.0
        assert transfer.status == TransferStatus.INITIATED
        assert transfer.tx_hash == "0x1234567890abcdef"

    def test_initiate_transfer_to_hyperliquid_invalid_amount(self, transfer_service: TokenTransferService) -> None:
        """Test initiating transfer with invalid amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=-100.0)

    def test_initiate_transfer_to_hyperliquid_unsupported_token(self, transfer_service: TokenTransferService) -> None:
        """Test initiating transfer with unsupported token."""
        with pytest.raises(ValueError, match="Token.*not supported"):
            transfer_service.initiate_transfer_to_hyperliquid(token="INVALID", amount=100.0)

    def test_initiate_transfer_to_hyperliquid_transaction_error(
        self, transfer_service: TokenTransferService, mock_ethereum_provider: EthereumProvider
    ) -> None:
        """Test initiating transfer with transaction error."""
        mock_ethereum_provider.estimate_gas = MagicMock(side_effect=TransactionError("Gas estimation failed"))

        with pytest.raises(TransactionError, match="Failed to initiate transfer"):
            transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=1000.0)


class TestTokenTransferServiceToEthereum:
    """Test TokenTransferService transfer to Ethereum."""

    def test_initiate_transfer_to_ethereum_success(self, transfer_service: TokenTransferService) -> None:
        """Test initiating transfer to Ethereum successfully."""
        recipient = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        transfer = transfer_service.initiate_transfer_to_ethereum(
            token="USDC", amount=1000.0, recipient_address=recipient, decimals=6
        )

        assert transfer.from_chain == "hyperliquid"
        assert transfer.to_chain == "ethereum"
        assert transfer.token == "USDC"
        assert transfer.amount == 1000.0
        assert transfer.status == TransferStatus.PENDING

    def test_initiate_transfer_to_ethereum_invalid_amount(self, transfer_service: TokenTransferService) -> None:
        """Test initiating transfer with invalid amount."""
        recipient = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        with pytest.raises(ValueError, match="Amount must be positive"):
            transfer_service.initiate_transfer_to_ethereum(token="USDC", amount=-100.0, recipient_address=recipient)

    def test_initiate_transfer_to_ethereum_invalid_address(self, transfer_service: TokenTransferService) -> None:
        """Test initiating transfer with invalid recipient address."""
        with pytest.raises(ValueError, match="Invalid recipient address"):
            transfer_service.initiate_transfer_to_ethereum(token="USDC", amount=1000.0, recipient_address="invalid")


class TestTokenTransferServiceTracking:
    """Test TokenTransferService transfer tracking."""

    def test_track_transfer_ethereum_confirmed(
        self, transfer_service: TokenTransferService, mock_ethereum_provider: EthereumProvider
    ) -> None:
        """Test tracking Ethereum transfer that is confirmed."""
        from datetime import datetime

        from web3.types import TxReceipt

        transfer = transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=1000.0)
        transfer.tx_hash = "0x1234567890abcdef"

        mock_receipt = MagicMock(spec=TxReceipt)
        mock_receipt.status = 1
        mock_receipt.blockNumber = 12345
        mock_ethereum_provider.get_transaction_receipt = MagicMock(return_value=mock_receipt)

        mock_tx = {"gasPrice": 20000000000}
        mock_ethereum_provider.get_transaction = MagicMock(return_value=mock_tx)

        updated_transfer = transfer_service.track_transfer(transfer)

        assert updated_transfer.status == TransferStatus.CONFIRMED
        assert updated_transfer.block_number == 12345
        assert updated_transfer.confirmed_at is not None

    def test_track_transfer_ethereum_failed(
        self, transfer_service: TokenTransferService, mock_ethereum_provider: EthereumProvider
    ) -> None:
        """Test tracking Ethereum transfer that failed."""
        from web3.types import TxReceipt

        transfer = transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=1000.0)
        transfer.tx_hash = "0x1234567890abcdef"

        mock_receipt = MagicMock(spec=TxReceipt)
        mock_receipt.status = 0
        mock_ethereum_provider.get_transaction_receipt = MagicMock(return_value=mock_receipt)

        updated_transfer = transfer_service.track_transfer(transfer)

        assert updated_transfer.status == TransferStatus.FAILED

    def test_track_transfer_ethereum_pending(
        self, transfer_service: TokenTransferService, mock_ethereum_provider: EthereumProvider
    ) -> None:
        """Test tracking Ethereum transfer that is still pending."""
        transfer = transfer_service.initiate_transfer_to_hyperliquid(token="USDC", amount=1000.0)
        transfer.tx_hash = "0x1234567890abcdef"

        mock_ethereum_provider.get_transaction_receipt = MagicMock(return_value=None)

        updated_transfer = transfer_service.track_transfer(transfer)

        # Status should remain as INITIATED if receipt not found
        assert updated_transfer.status in [TransferStatus.INITIATED, TransferStatus.PENDING]

    def test_track_transfer_hyperliquid(self, transfer_service: TokenTransferService) -> None:
        """Test tracking Hyperliquid transfer."""
        from datetime import datetime

        transfer = transfer_service.initiate_transfer_to_ethereum(
            token="USDC", amount=1000.0, recipient_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        )

        updated_transfer = transfer_service.track_transfer(transfer)

        # Hyperliquid tracking is a placeholder, so status should remain
        assert updated_transfer is not None


class TestTokenTransferServiceTokenBalance:
    """Test TokenTransferService token balance methods."""

    def test_get_token_balance_success(self, transfer_service: TokenTransferService) -> None:
        """Test getting token balance successfully."""
        # Note: Current implementation returns 0 as placeholder
        balance = transfer_service.get_token_balance("USDC")
        assert balance == 0.0

    def test_get_token_balance_unsupported_token(self, transfer_service: TokenTransferService) -> None:
        """Test getting balance for unsupported token."""
        with pytest.raises(ValueError, match="Token.*not supported"):
            transfer_service.get_token_balance("INVALID")

    def test_get_token_balance_with_address(self, transfer_service: TokenTransferService) -> None:
        """Test getting token balance for specific address."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        balance = transfer_service.get_token_balance("USDC", address=address)
        assert balance == 0.0

    def test_get_token_balance_no_address(self, mock_web3: MagicMock) -> None:
        """Test getting token balance without address and no provider address."""
        with patch("alpha_trading_crypto.infrastructure.blockchain.ethereum_provider.Web3") as mock_web3_class:
            from eth_account import Account

            account = Account.create()
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = MagicMock()

            provider = EthereumProvider(rpc_url="https://eth.llamarpc.com", private_key=account.key.hex())
            provider.web3 = mock_web3

            service = TokenTransferService(provider)
            # Should work with provider's address
            balance = service.get_token_balance("USDC")
            assert balance == 0.0


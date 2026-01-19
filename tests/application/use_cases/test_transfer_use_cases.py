"""Tests for transfer use cases."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from alpha_trading_crypto.application.use_cases.transfer_use_cases import (
    ReconcileBalances,
    TrackTransfer,
    TransferTokens,
)
from alpha_trading_crypto.domain.entities.inventory import Inventory
from alpha_trading_crypto.domain.entities.transfer import Transfer, TransferStatus
from alpha_trading_crypto.domain.services.inventory_manager import InventoryManager
from alpha_trading_crypto.domain.services.transfer_manager import TransferManager


@pytest.fixture
def mock_blockchain() -> MagicMock:
    """Create mock blockchain port."""
    blockchain = MagicMock()
    return blockchain


@pytest.fixture
def mock_exchange() -> MagicMock:
    """Create mock exchange port."""
    exchange = MagicMock()
    return exchange


@pytest.fixture
def transfer_manager() -> TransferManager:
    """Create transfer manager."""
    return TransferManager()


@pytest.fixture
def inventory_manager() -> InventoryManager:
    """Create inventory manager."""
    return InventoryManager()


class TestTransferTokens:
    """Test TransferTokens use case."""

    @pytest.fixture
    def transfer_tokens(
        self, mock_blockchain: MagicMock, transfer_manager: TransferManager, inventory_manager: InventoryManager
    ) -> TransferTokens:
        """Create TransferTokens use case."""
        return TransferTokens(
            blockchain=mock_blockchain,
            transfer_manager=transfer_manager,
            inventory_manager=inventory_manager,
        )

    def test_execute_to_hyperliquid_success(
        self, transfer_tokens: TransferTokens, mock_blockchain: MagicMock, transfer_manager: TransferManager
    ) -> None:
        """Test successful transfer to Hyperliquid."""
        transfer = Transfer(
            id="transfer123",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.INITIATED,
            tx_hash="0x1234567890abcdef",
        )
        mock_blockchain.initiate_transfer_to_hyperliquid.return_value = transfer

        result = transfer_tokens.execute_to_hyperliquid(token="USDC", amount=1000.0)

        assert result.id == "transfer123"
        assert result.token == "USDC"
        assert result.amount == 1000.0
        assert transfer_manager.get_transfer("transfer123") is not None
        mock_blockchain.initiate_transfer_to_hyperliquid.assert_called_once_with(
            token="USDC", amount=1000.0, decimals=6
        )

    def test_execute_to_ethereum_success(
        self, transfer_tokens: TransferTokens, mock_blockchain: MagicMock, transfer_manager: TransferManager
    ) -> None:
        """Test successful transfer to Ethereum."""
        transfer = Transfer(
            id="transfer456",
            from_chain="hyperliquid",
            to_chain="ethereum",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.PENDING,
        )
        mock_blockchain.initiate_transfer_to_ethereum.return_value = transfer

        result = transfer_tokens.execute_to_ethereum(
            token="USDC", amount=1000.0, recipient_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        )

        assert result.id == "transfer456"
        assert result.token == "USDC"
        assert transfer_manager.get_transfer("transfer456") is not None

    def test_execute_to_hyperliquid_invalid_amount(self, transfer_tokens: TransferTokens) -> None:
        """Test transfer with invalid amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            transfer_tokens.execute_to_hyperliquid(token="USDC", amount=-100.0)


class TestTrackTransfer:
    """Test TrackTransfer use case."""

    @pytest.fixture
    def track_transfer(self, mock_blockchain: MagicMock, transfer_manager: TransferManager) -> TrackTransfer:
        """Create TrackTransfer use case."""
        return TrackTransfer(blockchain=mock_blockchain, transfer_manager=transfer_manager)

    def test_execute_success(
        self, track_transfer: TrackTransfer, mock_blockchain: MagicMock, transfer_manager: TransferManager
    ) -> None:
        """Test successful transfer tracking."""
        transfer = Transfer(
            id="transfer123",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.INITIATED,
            tx_hash="0x1234567890abcdef",
        )
        transfer_manager.add_transfer(transfer)

        updated_transfer = Transfer(
            id="transfer123",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.CONFIRMED,
            tx_hash="0x1234567890abcdef",
            block_number=12345,
            gas_fee=0.001,
        )
        mock_blockchain.track_transfer.return_value = updated_transfer

        result = track_transfer.execute("transfer123")

        assert result.status == TransferStatus.CONFIRMED
        assert result.block_number == 12345
        assert result.gas_fee == 0.001
        mock_blockchain.track_transfer.assert_called_once()

    def test_execute_transfer_not_found(self, track_transfer: TrackTransfer, transfer_manager: TransferManager) -> None:
        """Test tracking non-existent transfer."""
        with pytest.raises(ValueError, match="Transfer not found"):
            track_transfer.execute("transfer999")

    def test_execute_all_pending_success(
        self, track_transfer: TrackTransfer, mock_blockchain: MagicMock, transfer_manager: TransferManager
    ) -> None:
        """Test tracking all pending transfers."""
        transfer1 = Transfer(
            id="transfer1",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.INITIATED,
        )
        transfer2 = Transfer(
            id="transfer2",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=500.0,
            status=TransferStatus.INITIATED,
        )
        transfer_manager.add_transfer(transfer1)
        transfer_manager.add_transfer(transfer2)

        updated_transfer = Transfer(
            id="transfer1",
            from_chain="ethereum",
            to_chain="hyperliquid",
            token="USDC",
            amount=1000.0,
            status=TransferStatus.CONFIRMED,
        )
        mock_blockchain.track_transfer.return_value = updated_transfer

        result = track_transfer.execute_all_pending()

        assert len(result) == 2
        assert mock_blockchain.track_transfer.call_count == 2


class TestReconcileBalances:
    """Test ReconcileBalances use case."""

    @pytest.fixture
    def reconcile_balances(self, mock_exchange: MagicMock, inventory_manager: InventoryManager) -> ReconcileBalances:
        """Create ReconcileBalances use case."""
        return ReconcileBalances(exchange=mock_exchange, inventory_manager=inventory_manager)

    @pytest.mark.asyncio
    async def test_execute_success(
        self, reconcile_balances: ReconcileBalances, mock_exchange: MagicMock, inventory_manager: InventoryManager
    ) -> None:
        """Test successful balance reconciliation."""
        exchange_balances = [
            Inventory(token="USDC", free=1000.0, locked=100.0, total=1100.0, chain="hyperliquid"),
            Inventory(token="BTC", free=0.1, locked=0.0, total=0.1, chain="hyperliquid"),
        ]
        mock_exchange.get_balances.return_value = exchange_balances

        result = await reconcile_balances.execute()

        assert "reconciled" in result
        assert "divergences" in result
        assert "missing" in result
        assert len(result["missing"]) == 2  # Both are new

    @pytest.mark.asyncio
    async def test_execute_with_divergence(
        self, reconcile_balances: ReconcileBalances, mock_exchange: MagicMock, inventory_manager: InventoryManager
    ) -> None:
        """Test reconciliation with divergence."""
        # Add local inventory
        local_inv = Inventory(token="USDC", free=900.0, locked=100.0, total=1000.0, chain="hyperliquid")
        inventory_manager.add_inventory(local_inv)

        # Exchange has different balance
        exchange_balances = [
            Inventory(token="USDC", free=1000.0, locked=100.0, total=1100.0, chain="hyperliquid"),
        ]
        mock_exchange.get_balances.return_value = exchange_balances

        result = await reconcile_balances.execute()

        assert len(result["divergences"]) == 1
        assert result["divergences"][0]["difference"] == 100.0

    @pytest.mark.asyncio
    async def test_execute_with_symbol_filter(
        self, reconcile_balances: ReconcileBalances, mock_exchange: MagicMock
    ) -> None:
        """Test reconciliation with symbol filter."""
        exchange_balances = [
            Inventory(token="USDC", free=1000.0, locked=100.0, total=1100.0, chain="hyperliquid"),
            Inventory(token="BTC", free=0.1, locked=0.0, total=0.1, chain="hyperliquid"),
        ]
        mock_exchange.get_balances.return_value = exchange_balances

        result = await reconcile_balances.execute(token="USDC")

        # Should only process USDC
        assert all(item["token"] == "USDC" for item in result["missing"])


"""Transfer Manager service."""

from typing import Dict, List, Optional

from alpha_trading_crypto.domain.entities.transfer import Transfer, TransferStatus


class TransferManager:
    """
    Transfer Manager service.

    Manages transfers: initiate, track, verify.
    """

    def __init__(self) -> None:
        """Initialize TransferManager."""
        self._transfers: Dict[str, Transfer] = {}

    def add_transfer(self, transfer: Transfer) -> None:
        """
        Add a transfer to tracking.

        Args:
            transfer: Transfer to add
        """
        self._transfers[transfer.id] = transfer

    def get_transfer(self, transfer_id: str) -> Optional[Transfer]:
        """
        Get a transfer by ID.

        Args:
            transfer_id: Transfer ID

        Returns:
            Transfer if found, None otherwise
        """
        return self._transfers.get(transfer_id)

    def update_transfer(
        self,
        transfer_id: str,
        status: Optional[TransferStatus] = None,
        tx_hash: Optional[str] = None,
        block_number: Optional[int] = None,
        gas_fee: Optional[float] = None,
    ) -> Optional[Transfer]:
        """
        Update a transfer.

        Args:
            transfer_id: Transfer ID
            status: Transfer status
            tx_hash: Transaction hash
            block_number: Block number
            gas_fee: Gas fee

        Returns:
            Updated transfer if found, None otherwise
        """
        transfer = self._transfers.get(transfer_id)
        if transfer is None:
            return None

        if status is not None:
            transfer.status = status
        if tx_hash is not None:
            transfer.tx_hash = tx_hash
        if block_number is not None:
            transfer.block_number = block_number
        if gas_fee is not None:
            transfer.gas_fee = gas_fee

        from datetime import datetime

        if status == TransferStatus.CONFIRMED:
            transfer.confirmed_at = datetime.utcnow()
        elif status == TransferStatus.COMPLETED:
            transfer.completed_at = datetime.utcnow()

        return transfer

    def get_pending_transfers(self) -> List[Transfer]:
        """
        Get all pending transfers.

        Returns:
            List of pending transfers
        """
        return [transfer for transfer in self._transfers.values() if transfer.is_pending()]

    def get_all_transfers(self) -> List[Transfer]:
        """
        Get all transfers.

        Returns:
            List of all transfers
        """
        return list(self._transfers.values())

    def get_transfers_by_token(self, token: str) -> List[Transfer]:
        """
        Get all transfers for a token.

        Args:
            token: Token symbol

        Returns:
            List of transfers for token
        """
        return [transfer for transfer in self._transfers.values() if transfer.token == token]


"""Transfer use cases."""

from typing import Any, Dict, List, Optional

import structlog

from alpha_trading_crypto.application.ports.blockchain_port import BlockchainPort
from alpha_trading_crypto.application.ports.exchange_port import ExchangePort
from alpha_trading_crypto.domain.entities.inventory import Inventory
from alpha_trading_crypto.domain.entities.transfer import Transfer
from alpha_trading_crypto.domain.services.inventory_manager import InventoryManager
from alpha_trading_crypto.domain.services.transfer_manager import TransferManager
from alpha_trading_crypto.infrastructure.exceptions import TransactionError

logger = structlog.get_logger()


class TransferTokens:
    """
    Transfer tokens use case.

    Transfers tokens between Ethereum and Hyperliquid.
    """

    def __init__(
        self,
        blockchain: BlockchainPort,
        transfer_manager: TransferManager,
        inventory_manager: InventoryManager,
    ) -> None:
        """
        Initialize TransferTokens use case.

        Args:
            blockchain: Blockchain port implementation
            transfer_manager: Transfer manager service
            inventory_manager: Inventory manager service
        """
        self.blockchain = blockchain
        self.transfer_manager = transfer_manager
        self.inventory_manager = inventory_manager

    def execute_to_hyperliquid(
        self,
        token: str,
        amount: float,
        decimals: int = 6,
    ) -> Transfer:
        """
        Execute transfer to Hyperliquid use case.

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
        logger.info("Transferring tokens to Hyperliquid", token=token, amount=amount)

        try:
            # Initiate transfer
            transfer = self.blockchain.initiate_transfer_to_hyperliquid(
                token=token,
                amount=amount,
                decimals=decimals,
            )

            # Track transfer
            self.transfer_manager.add_transfer(transfer)

            logger.info("Transfer initiated", transfer_id=transfer.id, token=token)

            return transfer

        except Exception as e:
            logger.error("Failed to transfer tokens to Hyperliquid", error=str(e), token=token)
            raise

    def execute_to_ethereum(
        self,
        token: str,
        amount: float,
        recipient_address: str,
        decimals: int = 6,
    ) -> Transfer:
        """
        Execute transfer to Ethereum use case.

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
        logger.info(
            "Transferring tokens to Ethereum",
            token=token,
            amount=amount,
            recipient=recipient_address,
        )

        try:
            # Initiate transfer
            transfer = self.blockchain.initiate_transfer_to_ethereum(
                token=token,
                amount=amount,
                recipient_address=recipient_address,
                decimals=decimals,
            )

            # Track transfer
            self.transfer_manager.add_transfer(transfer)

            logger.info("Transfer initiated", transfer_id=transfer.id, token=token)

            return transfer

        except Exception as e:
            logger.error("Failed to transfer tokens to Ethereum", error=str(e), token=token)
            raise


class TrackTransfer:
    """
    Track transfer use case.

    Tracks the status of a token transfer.
    """

    def __init__(
        self,
        blockchain: BlockchainPort,
        transfer_manager: TransferManager,
    ) -> None:
        """
        Initialize TrackTransfer use case.

        Args:
            blockchain: Blockchain port implementation
            transfer_manager: Transfer manager service
        """
        self.blockchain = blockchain
        self.transfer_manager = transfer_manager

    def execute(self, transfer_id: str) -> Transfer:
        """
        Execute track transfer use case.

        Args:
            transfer_id: Transfer ID to track

        Returns:
            Updated Transfer entity

        Raises:
            ValueError: If transfer not found
            TransactionError: If tracking fails
        """
        logger.info("Tracking transfer", transfer_id=transfer_id)

        # Get transfer from manager
        transfer = self.transfer_manager.get_transfer(transfer_id)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_id}")

        try:
            # Track transfer
            updated_transfer = self.blockchain.track_transfer(transfer)

            # Update in manager
            self.transfer_manager.update_transfer(
                transfer_id,
                status=updated_transfer.status,
                tx_hash=updated_transfer.tx_hash,
                block_number=updated_transfer.block_number,
                gas_fee=updated_transfer.gas_fee,
            )

            logger.info(
                "Transfer tracked",
                transfer_id=transfer_id,
                status=updated_transfer.status.value,
            )

            return updated_transfer

        except Exception as e:
            logger.error("Failed to track transfer", error=str(e), transfer_id=transfer_id)
            raise

    def execute_all_pending(self) -> List[Transfer]:
        """
        Track all pending transfers.

        Returns:
            List of updated Transfer entities

        Raises:
            TransactionError: If tracking fails
        """
        logger.info("Tracking all pending transfers")

        pending_transfers = self.transfer_manager.get_pending_transfers()
        updated_transfers = []

        for transfer in pending_transfers:
            try:
                updated = self.execute(transfer.id)
                updated_transfers.append(updated)
            except Exception as e:
                logger.warning("Failed to track transfer", error=str(e), transfer_id=transfer.id)
                continue

        logger.info("Pending transfers tracked", count=len(updated_transfers))

        return updated_transfers


class ReconcileBalances:
    """
    Reconcile balances use case.

    Reconciles balances between exchange and local inventory.
    """

    def __init__(
        self,
        exchange: ExchangePort,
        inventory_manager: InventoryManager,
    ) -> None:
        """
        Initialize ReconcileBalances use case.

        Args:
            exchange: Exchange port implementation
            inventory_manager: Inventory manager service
        """
        self.exchange = exchange
        self.inventory_manager = inventory_manager

    async def execute(self, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute reconcile balances use case.

        Args:
            token: Token to reconcile (None for all tokens)

        Returns:
            Dictionary with reconciliation results

        Raises:
            APIError: If reconciliation fails
        """
        logger.info("Reconciling balances", token=token)

        try:
            # Get balances from exchange
            exchange_balances = await self.exchange.get_balances()

            reconciliation_results = {
                "reconciled": [],
                "divergences": [],
                "missing": [],
            }

            for exchange_inv in exchange_balances:
                if token and exchange_inv.token != token:
                    continue

                local_inv = self.inventory_manager.get_inventory(exchange_inv.token, exchange_inv.chain)

                if not local_inv:
                    # Missing inventory
                    reconciliation_results["missing"].append(
                        {
                            "token": exchange_inv.token,
                            "chain": exchange_inv.chain,
                            "exchange_total": exchange_inv.total,
                        }
                    )
                    # Add to manager
                    self.inventory_manager.add_inventory(exchange_inv)
                    continue

                # Check for divergence
                tolerance = 1e-8
                difference = abs(local_inv.total - exchange_inv.total)

                if difference > tolerance:
                    # Divergence detected
                    reconciliation_results["divergences"].append(
                        {
                            "token": exchange_inv.token,
                            "chain": exchange_inv.chain,
                            "local_total": local_inv.total,
                            "exchange_total": exchange_inv.total,
                            "difference": difference,
                        }
                    )
                    # Reconcile
                    self.inventory_manager.reconcile(
                        exchange_inv.token,
                        exchange_inv.total,
                        exchange_inv.chain,
                    )
                else:
                    # Reconciled
                    reconciliation_results["reconciled"].append(
                        {
                            "token": exchange_inv.token,
                            "chain": exchange_inv.chain,
                            "total": exchange_inv.total,
                        }
                    )

            logger.info(
                "Balances reconciled",
                reconciled=len(reconciliation_results["reconciled"]),
                divergences=len(reconciliation_results["divergences"]),
                missing=len(reconciliation_results["missing"]),
            )

            return reconciliation_results

        except Exception as e:
            logger.error("Failed to reconcile balances", error=str(e))
            raise


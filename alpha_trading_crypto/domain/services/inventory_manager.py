"""Inventory Manager service."""

from typing import Dict, List, Optional

from alpha_trading_crypto.domain.entities.inventory import Inventory


class InventoryManager:
    """
    Inventory Manager service.

    Manages inventory: update, verify, reconcile.
    """

    def __init__(self) -> None:
        """Initialize InventoryManager."""
        self._inventories: Dict[str, Inventory] = {}

    def add_inventory(self, inventory: Inventory) -> None:
        """
        Add an inventory to tracking.

        Args:
            inventory: Inventory to add
        """
        key = f"{inventory.token}_{inventory.chain}"
        self._inventories[key] = inventory

    def get_inventory(self, token: str, chain: str = "hyperliquid") -> Optional[Inventory]:
        """
        Get inventory for a token.

        Args:
            token: Token symbol
            chain: Chain name

        Returns:
            Inventory if found, None otherwise
        """
        key = f"{token}_{chain}"
        return self._inventories.get(key)

    def update_inventory(
        self,
        token: str,
        free: Optional[float] = None,
        locked: Optional[float] = None,
        total: Optional[float] = None,
        chain: str = "hyperliquid",
    ) -> Optional[Inventory]:
        """
        Update inventory.

        Args:
            token: Token symbol
            free: Free balance
            locked: Locked balance
            total: Total balance
            chain: Chain name

        Returns:
            Updated inventory if found, None otherwise
        """
        inventory = self.get_inventory(token, chain)
        if inventory is None:
            return None

        if free is not None:
            inventory.free = free
        if locked is not None:
            inventory.locked = locked
        if total is not None:
            inventory.total = total

        # Update total if free or locked changed
        if free is not None or locked is not None:
            inventory.update_total()

        from datetime import datetime

        inventory.updated_at = datetime.utcnow()

        return inventory

    def verify_inventory(self, token: str, chain: str = "hyperliquid") -> bool:
        """
        Verify inventory consistency.

        Args:
            token: Token symbol
            chain: Chain name

        Returns:
            True if consistent, False otherwise
        """
        inventory = self.get_inventory(token, chain)
        if inventory is None:
            return False

        return inventory.verify_consistency()

    def get_all_inventories(self) -> List[Inventory]:
        """
        Get all inventories.

        Returns:
            List of all inventories
        """
        return list(self._inventories.values())

    def reconcile(self, token: str, expected_total: float, chain: str = "hyperliquid") -> bool:
        """
        Reconcile inventory with expected total.

        Args:
            token: Token symbol
            expected_total: Expected total balance
            chain: Chain name

        Returns:
            True if reconciled, False otherwise
        """
        inventory = self.get_inventory(token, chain)
        if inventory is None:
            return False

        # Check if difference is within tolerance
        tolerance = 1e-8
        difference = abs(inventory.total - expected_total)

        if difference > tolerance:
            # Update inventory to expected total
            inventory.total = expected_total
            inventory.update_total()

        return difference <= tolerance


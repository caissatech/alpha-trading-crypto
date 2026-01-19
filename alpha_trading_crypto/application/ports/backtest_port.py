"""Backtest port (interface) for backtesting operations."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd

from alpha_trading_crypto.infrastructure.backtest.backtest_engine import BacktestResult


class BacktestPort(ABC):
    """
    Backtest port interface.

    Defines the contract for backtesting operations.
    """

    @abstractmethod
    def run_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float = 100000.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestResult:
        """
        Run a backtest.

        Args:
            prices: DataFrame with columns: timestamp, symbol, open, high, low, close, volume
            signals: DataFrame with columns: timestamp, symbol, side (BUY/SELL), quantity
            initial_capital: Initial capital
            start_date: Start date (if None, use first date in prices)
            end_date: End date (if None, use last date in prices)

        Returns:
            BacktestResult with performance metrics

        Raises:
            InvalidDataError: If data format is invalid
            BacktestError: If backtest fails
        """
        pass


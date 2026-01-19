"""Backtest adapter implementing BacktestPort."""

from datetime import datetime
from typing import Optional

import pandas as pd

from alpha_trading_crypto.application.ports.backtest_port import BacktestPort
from alpha_trading_crypto.infrastructure.backtest.backtest_engine import BacktestEngine, BacktestResult


class BacktestAdapter(BacktestPort):
    """
    Backtest adapter.

    Implements BacktestPort using BacktestEngine.
    """

    def __init__(self, engine: BacktestEngine) -> None:
        """
        Initialize backtest adapter.

        Args:
            engine: BacktestEngine instance
        """
        self.engine = engine

    def run_backtest(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float = 100000.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestResult:
        """Run a backtest."""
        return self.engine.run(
            prices=prices,
            signals=signals,
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
        )


"""Tests for BacktestEngine."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from alpha_trading_crypto.domain.entities.order import OrderSide
from alpha_trading_crypto.infrastructure.backtest.backtest_engine import BacktestEngine, BacktestResult
from alpha_trading_crypto.infrastructure.exceptions import BacktestError, InvalidDataError


@pytest.fixture
def engine() -> BacktestEngine:
    """Create BacktestEngine instance."""
    return BacktestEngine(slippage=0.001, commission=0.0002, funding_rate=0.0001)


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Create sample price data."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
    return pd.DataFrame(
        {
            "timestamp": dates,
            "symbol": ["BTC"] * 100,
            "open": [50000.0 + i * 10 for i in range(100)],
            "high": [50100.0 + i * 10 for i in range(100)],
            "low": [49900.0 + i * 10 for i in range(100)],
            "close": [50000.0 + i * 10 for i in range(100)],
            "volume": [1000.0] * 100,
        }
    )


@pytest.fixture
def sample_signals() -> pd.DataFrame:
    """Create sample signal data."""
    dates = pd.date_range(start="2024-01-01", periods=10, freq="10H")
    return pd.DataFrame(
        {
            "timestamp": dates,
            "symbol": ["BTC"] * 10,
            "side": ["BUY", "SELL"] * 5,
            "quantity": [0.1] * 10,
        }
    )


class TestBacktestEngineInitialization:
    """Test BacktestEngine initialization."""

    def test_init_default(self) -> None:
        """Test initialization with default parameters."""
        engine = BacktestEngine()
        assert engine.slippage == 0.001
        assert engine.commission == 0.0002
        assert engine.funding_rate == 0.0001

    def test_init_custom(self) -> None:
        """Test initialization with custom parameters."""
        engine = BacktestEngine(slippage=0.002, commission=0.0005, funding_rate=0.0002)
        assert engine.slippage == 0.002
        assert engine.commission == 0.0005
        assert engine.funding_rate == 0.0002


class TestBacktestEngineValidation:
    """Test BacktestEngine data validation."""

    def test_validate_data_success(self, engine: BacktestEngine, sample_prices: pd.DataFrame, sample_signals: pd.DataFrame) -> None:
        """Test successful data validation."""
        engine._validate_data(sample_prices, sample_signals)
        # Should not raise

    def test_validate_data_missing_price_columns(self, engine: BacktestEngine, sample_signals: pd.DataFrame) -> None:
        """Test validation with missing price columns."""
        invalid_prices = pd.DataFrame({"timestamp": [datetime.now()], "symbol": ["BTC"]})
        with pytest.raises(InvalidDataError, match="Missing required columns in prices"):
            engine._validate_data(invalid_prices, sample_signals)

    def test_validate_data_missing_signal_columns(self, engine: BacktestEngine, sample_prices: pd.DataFrame) -> None:
        """Test validation with missing signal columns."""
        invalid_signals = pd.DataFrame({"timestamp": [datetime.now()], "symbol": ["BTC"]})
        with pytest.raises(InvalidDataError, match="Missing required columns in signals"):
            engine._validate_data(sample_prices, invalid_signals)

    def test_validate_data_invalid_timestamp(self, engine: BacktestEngine, sample_signals: pd.DataFrame) -> None:
        """Test validation with invalid timestamp."""
        invalid_prices = pd.DataFrame(
            {
                "timestamp": ["invalid"],
                "symbol": ["BTC"],
                "close": [50000.0],
            }
        )
        with pytest.raises(InvalidDataError, match="Invalid timestamp format"):
            engine._validate_data(invalid_prices, sample_signals)

    def test_validate_data_invalid_side(self, engine: BacktestEngine, sample_prices: pd.DataFrame) -> None:
        """Test validation with invalid side values."""
        invalid_signals = pd.DataFrame(
            {
                "timestamp": [datetime.now()],
                "symbol": ["BTC"],
                "side": ["INVALID"],
                "quantity": [0.1],
            }
        )
        with pytest.raises(InvalidDataError, match="Invalid side values"):
            engine._validate_data(sample_prices, invalid_signals)


class TestBacktestEngineSlippage:
    """Test BacktestEngine slippage application."""

    def test_apply_slippage_buy(self, engine: BacktestEngine) -> None:
        """Test slippage for buy orders."""
        price = 50000.0
        execution_price = engine._apply_slippage(price, OrderSide.BUY, 0.1)
        assert execution_price > price  # Should pay more

    def test_apply_slippage_sell(self, engine: BacktestEngine) -> None:
        """Test slippage for sell orders."""
        price = 50000.0
        execution_price = engine._apply_slippage(price, OrderSide.SELL, 0.1)
        assert execution_price < price  # Should receive less

    def test_apply_slippage_larger_quantity(self, engine: BacktestEngine) -> None:
        """Test slippage increases with quantity."""
        price = 50000.0
        small_slippage = engine._apply_slippage(price, OrderSide.BUY, 0.1)
        large_slippage = engine._apply_slippage(price, OrderSide.BUY, 10.0)
        assert large_slippage > small_slippage


class TestBacktestEngineRun:
    """Test BacktestEngine run method."""

    def test_run_simple_backtest(self, engine: BacktestEngine, sample_prices: pd.DataFrame, sample_signals: pd.DataFrame) -> None:
        """Test running a simple backtest."""
        result = engine.run(sample_prices, sample_signals, initial_capital=100000.0)
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 100000.0
        assert result.final_capital > 0
        assert len(result.equity_curve) > 0
        assert result.start_date is not None
        assert result.end_date is not None

    def test_run_with_date_range(self, engine: BacktestEngine, sample_prices: pd.DataFrame, sample_signals: pd.DataFrame) -> None:
        """Test running backtest with date range."""
        start_date = datetime(2024, 1, 1, 12, 0, 0)
        end_date = datetime(2024, 1, 5, 0, 0, 0)
        result = engine.run(sample_prices, sample_signals, initial_capital=100000.0, start_date=start_date, end_date=end_date)
        assert result.start_date >= start_date
        assert result.end_date <= end_date

    def test_run_empty_date_range(self, engine: BacktestEngine, sample_prices: pd.DataFrame, sample_signals: pd.DataFrame) -> None:
        """Test running backtest with empty date range."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        with pytest.raises(BacktestError, match="No price data in date range"):
            engine.run(sample_prices, sample_signals, initial_capital=100000.0, start_date=start_date, end_date=end_date)

    def test_run_buy_and_hold(self, engine: BacktestEngine) -> None:
        """Test buy and hold strategy."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 100,
                "open": [50000.0] * 100,
                "high": [51000.0] * 100,
                "low": [49000.0] * 100,
                "close": [50000.0 + i * 100 for i in range(100)],  # Price increases
                "volume": [1000.0] * 100,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0]],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [1.0],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert result.final_capital > result.initial_capital  # Should be profitable
        assert result.total_return > 0

    def test_run_round_trip(self, engine: BacktestEngine) -> None:
        """Test round trip trade (buy then sell)."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 10,
                "open": [50000.0] * 10,
                "high": [51000.0] * 10,
                "low": [49000.0] * 10,
                "close": [50000.0] * 10,
                "volume": [1000.0] * 10,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0], dates[5]],
                "symbol": ["BTC", "BTC"],
                "side": ["BUY", "SELL"],
                "quantity": [0.1, 0.1],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert result.total_trades == 1
        assert len(result.trades) == 1

    def test_run_insufficient_capital(self, engine: BacktestEngine) -> None:
        """Test backtest with insufficient capital."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 10,
                "open": [50000.0] * 10,
                "high": [51000.0] * 10,
                "low": [49000.0] * 10,
                "close": [50000.0] * 10,
                "volume": [1000.0] * 10,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0]],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [100.0],  # Very large quantity
            }
        )
        result = engine.run(prices, signals, initial_capital=1000.0)  # Small capital
        # Should skip the order due to insufficient capital
        assert result.final_capital == result.initial_capital or result.final_capital < result.initial_capital


class TestBacktestEngineMetrics:
    """Test BacktestEngine metrics calculation."""

    def test_metrics_calculation(self, engine: BacktestEngine, sample_prices: pd.DataFrame, sample_signals: pd.DataFrame) -> None:
        """Test metrics are calculated correctly."""
        result = engine.run(sample_prices, sample_signals, initial_capital=100000.0)
        assert result.total_return is not None
        assert result.total_pnl is not None
        assert result.sharpe_ratio is not None
        assert result.max_drawdown >= 0
        assert result.win_rate >= 0
        assert result.win_rate <= 100
        assert result.total_trades >= 0
        assert result.winning_trades >= 0
        assert result.losing_trades >= 0
        assert result.profit_factor >= 0

    def test_win_rate_calculation(self, engine: BacktestEngine) -> None:
        """Test win rate calculation."""
        dates = pd.date_range(start="2024-01-01", periods=20, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 20,
                "open": [50000.0] * 20,
                "high": [51000.0] * 20,
                "low": [49000.0] * 20,
                "close": [50000.0 + i * 100 for i in range(20)],  # Increasing price
                "volume": [1000.0] * 20,
            }
        )
        # Create profitable trades
        signals = pd.DataFrame(
            {
                "timestamp": [dates[i] for i in range(0, 10, 2)],
                "symbol": ["BTC"] * 5,
                "side": ["BUY", "SELL"] * 2 + ["BUY"],
                "quantity": [0.1] * 5,
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        # Should have some winning trades if price is increasing
        assert result.total_trades > 0

    def test_sharpe_ratio_calculation(self, engine: BacktestEngine) -> None:
        """Test Sharpe ratio calculation."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 100,
                "open": [50000.0] * 100,
                "high": [51000.0] * 100,
                "low": [49000.0] * 100,
                "close": [50000.0 + i * 10 for i in range(100)],
                "volume": [1000.0] * 100,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0], dates[50]],
                "symbol": ["BTC", "BTC"],
                "side": ["BUY", "SELL"],
                "quantity": [0.1, 0.1],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert isinstance(result.sharpe_ratio, float)

    def test_max_drawdown_calculation(self, engine: BacktestEngine) -> None:
        """Test max drawdown calculation."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        # Create price that goes up then down
        close_prices = [50000.0 + i * 100 for i in range(50)] + [50000.0 + (50 - i) * 100 for i in range(50)]
        prices = pd.DataFrame(
            {
                "timestamp": dates,
                "symbol": ["BTC"] * 100,
                "open": [50000.0] * 100,
                "high": [51000.0] * 100,
                "low": [49000.0] * 100,
                "close": close_prices,
                "volume": [1000.0] * 100,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0]],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [1.0],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert result.max_drawdown >= 0


class TestBacktestEngineEdgeCases:
    """Test BacktestEngine edge cases."""

    def test_run_no_signals(self, engine: BacktestEngine, sample_prices: pd.DataFrame) -> None:
        """Test backtest with no signals."""
        empty_signals = pd.DataFrame(columns=["timestamp", "symbol", "side", "quantity"])
        result = engine.run(sample_prices, empty_signals, initial_capital=100000.0)
        assert result.final_capital == result.initial_capital
        assert result.total_trades == 0

    def test_run_single_timestamp(self, engine: BacktestEngine) -> None:
        """Test backtest with single timestamp."""
        prices = pd.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1)],
                "symbol": ["BTC"],
                "open": [50000.0],
                "high": [51000.0],
                "low": [49000.0],
                "close": [50000.0],
                "volume": [1000.0],
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1)],
                "symbol": ["BTC"],
                "side": ["BUY"],
                "quantity": [0.1],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert result is not None

    def test_run_multiple_symbols(self, engine: BacktestEngine) -> None:
        """Test backtest with multiple symbols."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="1H")
        prices = pd.DataFrame(
            {
                "timestamp": dates.tolist() * 2,
                "symbol": ["BTC"] * 10 + ["ETH"] * 10,
                "open": [50000.0] * 20,
                "high": [51000.0] * 20,
                "low": [49000.0] * 20,
                "close": [50000.0] * 20,
                "volume": [1000.0] * 20,
            }
        )
        signals = pd.DataFrame(
            {
                "timestamp": [dates[0], dates[0]],
                "symbol": ["BTC", "ETH"],
                "side": ["BUY", "BUY"],
                "quantity": [0.1, 0.1],
            }
        )
        result = engine.run(prices, signals, initial_capital=100000.0)
        assert result is not None


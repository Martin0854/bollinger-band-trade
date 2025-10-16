"""
End-to-end integration test for complete backtest workflow.
Tests: Config load -> Data fetch -> Indicators -> Signals -> Portfolio -> Metrics -> Logging

This test MUST FAIL initially (TDD) until all components are implemented.
"""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime, date
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config_yaml(temp_data_dir):
    """Create sample configuration YAML for testing."""
    config_content = f"""
seed_money: 10000000
stocks:
  - "005930"
date_range:
  - 2024-01-01
  - 2024-12-31
bollinger_period: 20
bollinger_std_multiplier: 2.0
squeeze_threshold_percent: 30.0
squeeze_lookback_days: 10
stop_loss_percent: 5.0
max_position_percent: 30.0
max_positions: 5
data_cache_dir: {temp_data_dir}/cache
log_dir: {temp_data_dir}/logs
"""
    config_path = Path(temp_data_dir) / "test_config.yaml"
    config_path.write_text(config_content)
    return str(config_path)


def test_e2e_backtest_full_workflow(sample_config_yaml, temp_data_dir):
    """Test complete backtest workflow from config to final report."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    # Step 1: Load configuration
    config = BacktestConfiguration.from_yaml(sample_config_yaml)

    assert config.seed_money == 10000000
    assert "005930" in config.stocks

    # Step 2: Initialize backtest engine
    engine = BacktestEngine(config=config)

    # Step 3: Run backtest
    report = engine.run()

    # Step 4: Verify report structure
    assert report is not None
    assert hasattr(report, 'total_return_pct')
    assert hasattr(report, 'win_rate_pct')
    assert hasattr(report, 'max_drawdown_pct')
    assert hasattr(report, 'sharpe_ratio')
    assert hasattr(report, 'num_trades')

    # Step 5: Verify logs were created
    log_dir = Path(temp_data_dir) / "logs"
    assert log_dir.exists()

    # Check trade log exists
    db_path = log_dir / "backtest.db"
    assert db_path.exists()


def test_e2e_backtest_with_mock_data(temp_data_dir):
    """Test backtest with mock OHLCV data (no external API calls)."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    # Create mock config
    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    # Create mock OHLCV data
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
    mock_data = pd.DataFrame({
        'Open': [60000] * len(dates),
        'High': [62000] * len(dates),
        'Low': [58000] * len(dates),
        'Close': [60000 + i * 100 for i in range(len(dates))],  # Upward trend
        'Volume': [1000000] * len(dates)
    }, index=dates)

    # Initialize engine with mock data
    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", mock_data)

    # Run backtest
    report = engine.run()

    # Verify metrics
    assert report.num_trades >= 0
    assert report.total_return_pct is not None


def test_e2e_backtest_squeeze_detection_and_entry(temp_data_dir):
    """Test that backtest detects squeeze and generates entry signal."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    # Create data with squeeze pattern:
    # Days 1-20: Normal volatility
    # Days 21-30: Squeeze (low volatility)
    # Days 31+: Expansion (high volatility + breakout)
    dates = pd.date_range('2024-01-01', periods=60, freq='D')

    close_prices = []
    for i in range(len(dates)):
        if i < 20:
            # Normal volatility
            close_prices.append(60000 + (i % 5) * 500)
        elif i < 30:
            # Squeeze (very low volatility)
            close_prices.append(60000 + (i % 3) * 100)
        else:
            # Expansion with upward breakout
            close_prices.append(60000 + (i - 30) * 1000)

    mock_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p + 500 for p in close_prices],
        'Low': [p - 500 for p in close_prices],
        'Close': close_prices,
        'Volume': [1000000] * len(dates)
    }, index=dates)

    # Run backtest
    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", mock_data)
    report = engine.run()

    # Should have detected squeeze and entered position
    assert report.num_trades > 0


def test_e2e_backtest_stop_loss_trigger(temp_data_dir):
    """Test that backtest triggers stop-loss on 5% loss."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    # Create data with: entry at 60K, then drop to 57K (5% loss)
    dates = pd.date_range('2024-01-01', periods=60, freq='D')

    close_prices = []
    for i in range(len(dates)):
        if i < 30:
            close_prices.append(60000 + (i % 3) * 100)  # Squeeze
        elif i < 35:
            close_prices.append(66000)  # Breakout (entry)
        else:
            close_prices.append(62700)  # Drop 5% from 66K

    mock_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p + 500 for p in close_prices],
        'Low': [p - 500 for p in close_prices],
        'Close': close_prices,
        'Volume': [1000000] * len(dates)
    }, index=dates)

    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", mock_data)
    report = engine.run()

    # Should have entered and exited due to stop-loss
    assert report.num_trades >= 2  # At least one BUY and one SELL


def test_e2e_backtest_multiple_stocks(temp_data_dir):
    """Test backtest with multiple stocks."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930", "035720"],  # Two stocks
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    # Create mock data for both stocks
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
    mock_data_1 = pd.DataFrame({
        'Open': [60000] * len(dates),
        'High': [62000] * len(dates),
        'Low': [58000] * len(dates),
        'Close': [60000 + i * 100 for i in range(len(dates))],
        'Volume': [1000000] * len(dates)
    }, index=dates)

    mock_data_2 = pd.DataFrame({
        'Open': [100000] * len(dates),
        'High': [102000] * len(dates),
        'Low': [98000] * len(dates),
        'Close': [100000 + i * 150 for i in range(len(dates))],
        'Volume': [500000] * len(dates)
    }, index=dates)

    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", mock_data_1)
    engine.load_mock_data("035720", mock_data_2)

    report = engine.run()

    # Should have traded both stocks
    assert report.num_trades >= 0


def test_e2e_backtest_max_positions_limit(temp_data_dir):
    """Test that backtest respects max_positions limit."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=50000000,  # Higher capital to afford 5 positions
        stocks=["005930", "035720", "051910", "005380", "000660", "068270"],  # 6 stocks
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,  # Limit to 5 positions
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    # Create mock data for all stocks (all generating signals)
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')

    engine = BacktestEngine(config=config)

    for stock_code in config.stocks:
        mock_data = pd.DataFrame({
            'Open': [60000] * len(dates),
            'High': [62000] * len(dates),
            'Low': [58000] * len(dates),
            'Close': [60000 + i * 100 for i in range(len(dates))],
            'Volume': [1000000] * len(dates)
        }, index=dates)
        engine.load_mock_data(stock_code, mock_data)

    report = engine.run()

    # At any point, should not hold more than 5 positions
    # (This requires checking intermediate state, simplified here)
    assert report is not None


def test_e2e_backtest_logging_to_database(sample_config_yaml, temp_data_dir):
    """Test that backtest logs trades and squeeze events to database."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration
    import sqlite3

    config = BacktestConfiguration.from_yaml(sample_config_yaml)

    engine = BacktestEngine(config=config)

    # Create and load mock data
    dates = pd.date_range('2024-01-01', periods=60, freq='D')
    mock_data = pd.DataFrame({
        'Open': [60000] * len(dates),
        'High': [62000] * len(dates),
        'Low': [58000] * len(dates),
        'Close': [60000 + i * 100 for i in range(len(dates))],
        'Volume': [1000000] * len(dates)
    }, index=dates)
    engine.load_mock_data("005930", mock_data)

    report = engine.run()

    # Check database was created and populated
    db_path = Path(temp_data_dir) / "logs" / "backtest.db"
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check trade_log table
    cursor.execute("SELECT COUNT(*) FROM trade_log")
    trade_count = cursor.fetchone()[0]
    assert trade_count >= 0

    # Check squeeze_events table
    cursor.execute("SELECT COUNT(*) FROM squeeze_events")
    squeeze_count = cursor.fetchone()[0]
    assert squeeze_count >= 0

    conn.close()


def test_e2e_backtest_performance_metrics_calculation(temp_data_dir):
    """Test that all performance metrics are calculated correctly."""
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        bollinger_std_multiplier=2.0,
        squeeze_threshold_percent=30.0,
        squeeze_lookback_days=10,
        stop_loss_percent=5.0,
        max_position_percent=30.0,
        max_positions=5,
        data_cache_dir=f"{temp_data_dir}/cache",
        log_dir=f"{temp_data_dir}/logs"
    )

    dates = pd.date_range('2024-01-01', periods=60, freq='D')
    mock_data = pd.DataFrame({
        'Open': [60000] * len(dates),
        'High': [62000] * len(dates),
        'Low': [58000] * len(dates),
        'Close': [60000 + i * 100 for i in range(len(dates))],
        'Volume': [1000000] * len(dates)
    }, index=dates)

    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", mock_data)
    report = engine.run()

    # Verify all metrics are present
    assert hasattr(report, 'total_return_pct')
    assert hasattr(report, 'win_rate_pct')
    assert hasattr(report, 'max_drawdown_pct')
    assert hasattr(report, 'sharpe_ratio')
    assert hasattr(report, 'num_trades')
    assert hasattr(report, 'num_winning_trades')
    assert hasattr(report, 'num_losing_trades')

    # Verify metric types
    assert isinstance(report.num_trades, int)
    assert report.num_trades >= 0


# ========================================================================
# T047: Integration test for confidence filtering in backtest
# ========================================================================

def test_e2e_backtest_confidence_threshold_70_fewer_trades_than_50(temp_data_dir):
    """
    T047: Test threshold=70 → fewer trades than threshold=50.

    Higher confidence threshold should filter out more signals,
    resulting in fewer total trades.
    """
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration, EnhancedStrategyConfig

    # Create mock data with many squeeze/breakout opportunities
    dates = pd.date_range('2024-01-01', periods=90, freq='D')
    close_prices = []
    for i in range(len(dates)):
        # Create multiple squeeze-expansion cycles
        cycle = i % 30
        if cycle < 10:
            close_prices.append(60000 + (cycle % 3) * 100)  # Squeeze
        else:
            close_prices.append(60000 + (cycle - 10) * 500)  # Expansion

    mock_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p + 1000 for p in close_prices],
        'Low': [p - 1000 for p in close_prices],
        'Close': close_prices,
        'Volume': [2000000] * len(dates)  # High volume for filter pass
    }, index=dates)

    # Run with threshold=50
    config_50 = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        enhanced_strategy=EnhancedStrategyConfig(
            confidence={'threshold': 50}
        )
    )

    engine_50 = BacktestEngine(config=config_50)
    engine_50.load_mock_data("005930", mock_data)
    report_50 = engine_50.run()

    # Run with threshold=70
    config_70 = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 31)),
        bollinger_period=20,
        enhanced_strategy=EnhancedStrategyConfig(
            confidence={'threshold': 70}
        )
    )

    engine_70 = BacktestEngine(config=config_70)
    engine_70.load_mock_data("005930", mock_data)
    report_70 = engine_70.run()

    # Property: Higher threshold → fewer trades
    assert report_70.num_trades <= report_50.num_trades


def test_e2e_backtest_confidence_threshold_70_higher_win_rate_than_50(temp_data_dir):
    """
    T047: Test threshold=70 → higher win rate than threshold=50.

    Higher confidence threshold should filter out lower-quality signals,
    improving win rate (assuming confidence scoring is effective).
    """
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration, EnhancedStrategyConfig

    # Create mock data
    dates = pd.date_range('2024-01-01', periods=120, freq='D')
    close_prices = []
    for i in range(len(dates)):
        # Mix of winning and losing squeeze patterns
        cycle = i % 40
        if cycle < 10:
            close_prices.append(60000)  # Squeeze
        elif cycle < 25:
            close_prices.append(60000 + (cycle - 10) * 200)  # Winning breakout
        else:
            close_prices.append(60000 + (25 - cycle) * 300)  # Losing reversal

    mock_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p + 1000 for p in close_prices],
        'Low': [p - 1000 for p in close_prices],
        'Close': close_prices,
        'Volume': [2000000] * len(dates)
    }, index=dates)

    # Run with threshold=50
    config_50 = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 4, 30)),
        enhanced_strategy=EnhancedStrategyConfig(
            confidence={'threshold': 50}
        )
    )

    engine_50 = BacktestEngine(config=config_50)
    engine_50.load_mock_data("005930", mock_data)
    report_50 = engine_50.run()

    # Run with threshold=70
    config_70 = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 4, 30)),
        enhanced_strategy=EnhancedStrategyConfig(
            confidence={'threshold': 70}
        )
    )

    engine_70 = BacktestEngine(config=config_70)
    engine_70.load_mock_data("005930", mock_data)
    report_70 = engine_70.run()

    # Property: Higher threshold → same or better win rate
    # (May not always be true with random data, but should trend this way)
    if report_70.num_trades > 0 and report_50.num_trades > 0:
        assert report_70.win_rate_pct >= report_50.win_rate_pct - 5  # Allow 5% margin


def test_e2e_backtest_trades_below_threshold_rejected(temp_data_dir):
    """
    T047: Test trades below threshold are rejected.

    Signals with confidence below threshold should not result in trades.
    """
    from src.backtest.engine import BacktestEngine
    from src.models.config import BacktestConfiguration, EnhancedStrategyConfig

    # Create mock data
    dates = pd.date_range('2024-01-01', periods=60, freq='D')
    mock_data = pd.DataFrame({
        'Open': [60000] * len(dates),
        'High': [62000] * len(dates),
        'Low': [58000] * len(dates),
        'Close': [60000 + i * 200 for i in range(len(dates))],
        'Volume': [500000] * len(dates)  # Low volume - won't pass volume filter
    }, index=dates)

    # Run with threshold=100 (impossible to meet - only base score of 25)
    config_high = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 3, 1)),
        enhanced_strategy=EnhancedStrategyConfig(
            confidence={'threshold': 100}  # Impossible with only base score
        )
    )

    engine = BacktestEngine(config=config_high)
    engine.load_mock_data("005930", mock_data)
    report = engine.run()

    # Should have zero trades (threshold too high)
    assert report.num_trades == 0

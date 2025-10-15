"""
Contract tests for BacktestConfiguration Pydantic validation.
Tests validation rules from FR-045 (spec.md).

These tests MUST FAIL initially (TDD approach) until src/models/config.py is implemented.
"""

import pytest
from datetime import date
from pydantic import ValidationError


def test_valid_configuration():
    """Test that valid configuration is accepted."""
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930", "000660"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        bollinger_period=20,
        bollinger_std_dev=2.0,
        squeeze_threshold_percent=30,
        squeeze_lookback_days=10,
        stop_loss_percent=5,
        max_position_percent=30,
    )

    assert config.seed_money == 10000000
    assert len(config.stocks) == 2
    assert config.bollinger_period == 20


def test_seed_money_must_be_positive():
    """Test FR-045: seed_money > 0"""
    from src.models.config import BacktestConfiguration

    with pytest.raises(ValidationError) as exc_info:
        BacktestConfiguration(
            seed_money=-1000,  # Invalid: negative
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )

    assert "seed_money" in str(exc_info.value)


def test_stock_codes_must_be_6_digits():
    """Test FR-045: stock codes match ^\\d{6}$"""
    from src.models.config import BacktestConfiguration

    # Invalid: 5 digits
    with pytest.raises(ValidationError) as exc_info:
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["12345"],  # Invalid: only 5 digits
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )

    assert "stock" in str(exc_info.value).lower()

    # Invalid: 7 digits
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["1234567"],  # Invalid: 7 digits
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )

    # Invalid: contains letters
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["00593A"],  # Invalid: contains letter
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )


def test_date_range_start_must_be_before_end():
    """Test FR-045: start date < end date"""
    from src.models.config import BacktestConfiguration

    with pytest.raises(ValidationError) as exc_info:
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 12, 31), date(2024, 1, 1)),  # Invalid: start after end
        )

    assert "date" in str(exc_info.value).lower()


def test_bollinger_period_constraints():
    """Test FR-045: 5 <= bollinger_period <= 200"""
    from src.models.config import BacktestConfiguration

    # Too small
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            bollinger_period=4,  # Invalid: < 5
        )

    # Too large
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            bollinger_period=201,  # Invalid: > 200
        )

    # Valid boundaries
    config_min = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        bollinger_period=5,  # Valid: minimum
    )
    assert config_min.bollinger_period == 5

    config_max = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        bollinger_period=200,  # Valid: maximum
    )
    assert config_max.bollinger_period == 200


def test_squeeze_threshold_constraints():
    """Test FR-045: 5 <= squeeze_threshold_percent <= 100"""
    from src.models.config import BacktestConfiguration

    # Too small
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            squeeze_threshold_percent=4,  # Invalid: < 5
        )

    # Too large
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            squeeze_threshold_percent=101,  # Invalid: > 100
        )


def test_stop_loss_percent_constraints():
    """Test FR-045: 0 <= stop_loss_percent <= 100"""
    from src.models.config import BacktestConfiguration

    # Negative (invalid)
    with pytest.raises(ValidationError):
        BacktestConfiguration(
            seed_money=10000000,
            stocks=["005930"],
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            stop_loss_percent=-1,  # Invalid: < 0
        )

    # Zero is valid (no stop-loss)
    config_zero = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        stop_loss_percent=0,  # Valid: 0 means no stop-loss
    )
    assert config_zero.stop_loss_percent == 0


def test_from_yaml_classmethod():
    """Test BacktestConfiguration.from_yaml() loads config from YAML file."""
    from src.models.config import BacktestConfiguration
    import tempfile
    import os

    yaml_content = """
seed_money: 10000000
stocks:
  - "005930"
  - "000660"
date_range:
  start: "2024-01-01"
  end: "2024-12-31"
bollinger_period: 20
bollinger_std_dev: 2.0
squeeze_threshold_percent: 30
squeeze_lookback_days: 10
stop_loss_percent: 5
max_position_percent: 30
risk_free_rate: 0.03
transaction_cost_percent: 0.0
initial_positions: {}
"""

    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = BacktestConfiguration.from_yaml(temp_path)
        assert config.seed_money == 10000000
        assert config.stocks == ["005930", "000660"]
        assert config.bollinger_period == 20
        assert config.squeeze_threshold_percent == 30
    finally:
        os.unlink(temp_path)


def test_default_values():
    """Test that default values are applied correctly."""
    from src.models.config import BacktestConfiguration

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        # All other fields should use defaults
    )

    assert config.bollinger_period == 20  # Default
    assert config.bollinger_std_dev == 2.0  # Default
    assert config.squeeze_threshold_percent == 30  # Default
    assert config.squeeze_lookback_days == 10  # Default
    assert config.stop_loss_percent == 5  # Default
    assert config.max_position_percent == 30  # Default
    assert config.risk_free_rate == 0.03  # Default
    assert config.transaction_cost_percent == 0.0  # Default
    assert config.initial_positions == {}  # Default


# ========================================================================
# T014: Contract tests for Enhanced Strategy Configuration (Phase 1-4)
# ========================================================================

def test_volume_filter_config_valid():
    """T014: Test valid volume filter configuration."""
    from src.models.config import VolumeFilterConfig

    config = VolumeFilterConfig(
        enabled=True,
        window_days=20,
        multiplier=1.5
    )

    assert config.enabled is True
    assert config.window_days == 20
    assert config.multiplier == 1.5


def test_volume_filter_window_days_bounds():
    """T014: Test window_days bounds (5-252)."""
    from src.models.config import VolumeFilterConfig

    # Valid boundaries
    VolumeFilterConfig(window_days=5)  # Min
    VolumeFilterConfig(window_days=252)  # Max

    # Invalid: below minimum
    with pytest.raises(ValidationError):
        VolumeFilterConfig(window_days=4)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        VolumeFilterConfig(window_days=253)


def test_volume_filter_multiplier_bounds():
    """T014: Test multiplier bounds (>0, ≤10.0)."""
    from src.models.config import VolumeFilterConfig

    # Valid boundaries
    VolumeFilterConfig(multiplier=0.1)  # Just above 0
    VolumeFilterConfig(multiplier=10.0)  # Max

    # Invalid: zero
    with pytest.raises(ValidationError):
        VolumeFilterConfig(multiplier=0.0)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        VolumeFilterConfig(multiplier=10.1)


def test_enhanced_strategy_config_defaults():
    """T014: Test EnhancedStrategyConfig loads with defaults."""
    from src.models.config import EnhancedStrategyConfig

    config = EnhancedStrategyConfig()

    # Defaults per config-schema.yaml
    assert config.volume_filter.enabled is True
    assert config.volume_filter.window_days == 20
    assert config.volume_filter.multiplier == 1.5

    assert config.rsi.enabled is True
    assert config.rsi.period == 14
    assert config.rsi.overbought == 70
    assert config.rsi.oversold == 30

    assert config.macd.enabled is False  # Phase 2
    assert config.atr.enabled is False   # Phase 4

    assert config.confidence.threshold == 60


def test_enhanced_strategy_at_least_one_filter_enabled():
    """T014: Test validation - at least one filter must be enabled."""
    from src.models.config import (
        EnhancedStrategyConfig,
        VolumeFilterConfig,
        RSIConfig,
        MACDConfig
    )

    # Invalid: All filters disabled
    with pytest.raises(ValidationError) as exc_info:
        EnhancedStrategyConfig(
            volume_filter=VolumeFilterConfig(enabled=False),
            rsi=RSIConfig(enabled=False),
            macd=MACDConfig(enabled=False)
        )
    assert "At least one indicator filter must be enabled" in str(exc_info.value)


def test_backtest_config_backward_compatibility():
    """T014: Test enhanced_strategy is optional (backward compatibility)."""
    from src.models.config import BacktestConfiguration

    # Old config WITHOUT enhanced_strategy
    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31))
    )

    # Should load successfully
    assert config.enhanced_strategy is None  # Optional


def test_backtest_config_with_enhanced_strategy():
    """T014: Test backtest config with enhanced_strategy section."""
    from src.models.config import BacktestConfiguration, EnhancedStrategyConfig

    config = BacktestConfiguration(
        seed_money=10000000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        enhanced_strategy=EnhancedStrategyConfig()  # Use defaults
    )

    assert config.enhanced_strategy is not None
    assert config.enhanced_strategy.volume_filter.enabled is True

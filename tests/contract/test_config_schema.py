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


# ========================================================================
# T036: Contract tests for MACD Configuration (User Story 3)
# ========================================================================

def test_macd_config_valid():
    """T036: Test valid MACD configuration loads correctly."""
    from src.models.config import MACDConfig

    config = MACDConfig(
        enabled=True,
        fast_period=12,
        slow_period=26,
        signal_period=9
    )

    assert config.enabled is True
    assert config.fast_period == 12
    assert config.slow_period == 26
    assert config.signal_period == 9


def test_macd_fast_period_bounds():
    """T036: Test fast_period bounds (5-50)."""
    from src.models.config import MACDConfig

    # Valid boundaries
    MACDConfig(fast_period=5, slow_period=10)  # Min
    MACDConfig(fast_period=50, slow_period=60)  # Max

    # Invalid: below minimum
    with pytest.raises(ValidationError):
        MACDConfig(fast_period=4, slow_period=10)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        MACDConfig(fast_period=51, slow_period=60)


def test_macd_slow_period_bounds():
    """T036: Test slow_period bounds (10-100)."""
    from src.models.config import MACDConfig

    # Valid boundaries
    MACDConfig(fast_period=5, slow_period=10)  # Min
    MACDConfig(fast_period=50, slow_period=100)  # Max

    # Invalid: below minimum
    with pytest.raises(ValidationError):
        MACDConfig(fast_period=5, slow_period=9)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        MACDConfig(fast_period=50, slow_period=101)


def test_macd_signal_period_bounds():
    """T036: Test signal_period bounds (5-50)."""
    from src.models.config import MACDConfig

    # Valid boundaries
    MACDConfig(signal_period=5)  # Min
    MACDConfig(signal_period=50)  # Max

    # Invalid: below minimum
    with pytest.raises(ValidationError):
        MACDConfig(signal_period=4)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        MACDConfig(signal_period=51)


def test_macd_validation_slow_greater_than_fast():
    """T036: Test validation - slow_period > fast_period."""
    from src.models.config import MACDConfig

    # Valid: slow > fast
    config = MACDConfig(fast_period=12, slow_period=26)
    assert config.slow_period > config.fast_period

    # Invalid: slow <= fast
    with pytest.raises(ValidationError) as exc_info:
        MACDConfig(fast_period=26, slow_period=26)  # Equal
    # Check for key parts of the error message (pydantic v2 adds extra formatting)
    error_str = str(exc_info.value).lower()
    assert "slow_period" in error_str
    assert "fast_period" in error_str
    assert "greater" in error_str

    with pytest.raises(ValidationError):
        MACDConfig(fast_period=30, slow_period=20)  # Slow < fast


# ========================================================================
# T048: Contract tests for Confidence Configuration (User Story 4)
# ========================================================================

def test_confidence_config_valid():
    """T048: Test valid confidence config loads correctly."""
    from src.models.config import ConfidenceConfig

    config = ConfidenceConfig(
        threshold=60,
        scoring={
            'base_score': 25,
            'volume_score': 25,
            'rsi_score': 20,
            'macd_score': 30
        }
    )

    assert config.threshold == 60
    assert config.scoring['base_score'] == 25
    assert config.scoring['volume_score'] == 25
    assert config.scoring['rsi_score'] == 20
    assert config.scoring['macd_score'] == 30


def test_confidence_threshold_bounds():
    """T048: Test threshold bounds (0-100)."""
    from src.models.config import ConfidenceConfig

    # Valid boundaries
    ConfidenceConfig(threshold=0)  # Min (accept all)
    ConfidenceConfig(threshold=100)  # Max (only perfect signals)

    # Invalid: negative
    with pytest.raises(ValidationError):
        ConfidenceConfig(threshold=-1)

    # Invalid: above maximum
    with pytest.raises(ValidationError):
        ConfidenceConfig(threshold=101)


def test_confidence_scoring_section_validation():
    """T048: Test scoring section validation."""
    from src.models.config import ConfidenceConfig

    # Valid scoring
    config = ConfidenceConfig(
        threshold=60,
        scoring={
            'base_score': 25,
            'volume_score': 25,
            'rsi_score': 20,
            'macd_score': 30
        }
    )
    assert config.scoring is not None

    # Test that all required scoring keys are present
    required_keys = {'base_score', 'volume_score', 'rsi_score', 'macd_score'}
    assert set(config.scoring.keys()) == required_keys


def test_confidence_total_scoring_le_100():
    """T048: Test base_score + volume_score + rsi_score + macd_score ≤ 100."""
    from src.models.config import ConfidenceConfig

    # Valid: total = 100
    config_100 = ConfidenceConfig(
        threshold=60,
        scoring={
            'base_score': 25,
            'volume_score': 25,
            'rsi_score': 25,
            'macd_score': 25
        }
    )
    total = sum(config_100.scoring.values())
    assert total == 100

    # Valid: total < 100
    config_70 = ConfidenceConfig(
        threshold=60,
        scoring={
            'base_score': 20,
            'volume_score': 20,
            'rsi_score': 15,
            'macd_score': 15
        }
    )
    total = sum(config_70.scoring.values())
    assert total == 70

    # Invalid: total > 100
    with pytest.raises(ValidationError) as exc_info:
        ConfidenceConfig(
            threshold=60,
            scoring={
                'base_score': 30,
                'volume_score': 30,
                'rsi_score': 30,
                'macd_score': 30  # Total = 120
            }
        )
    assert "100" in str(exc_info.value) or "total" in str(exc_info.value).lower()


def test_confidence_config_defaults():
    """T048: Test ConfidenceConfig defaults."""
    from src.models.config import ConfidenceConfig

    # Create with defaults
    config = ConfidenceConfig()

    # Should have default threshold
    assert config.threshold == 60

    # Should have default scoring
    assert config.scoring['base_score'] == 25
    assert config.scoring['volume_score'] == 25
    assert config.scoring['rsi_score'] == 20
    assert config.scoring['macd_score'] == 30
    assert sum(config.scoring.values()) == 100


# ========================================================================
# T060: ATR Configuration Schema Tests (User Story 5)
# ========================================================================

def test_atr_config_valid():
    """T060: Test valid ATR config loads correctly."""
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.models.config import ATRConfig

    # # Valid ATR configuration
    # config = ATRConfig(
    #     enabled=True,
    #     period=14,
    #     multiplier=2.0
    # )

    # assert config.enabled is True
    # assert config.period == 14
    # assert config.multiplier == 2.0


def test_atr_config_period_bounds():
    """T060: Test period bounds (5-100)."""
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.models.config import ATRConfig
    # from pydantic import ValidationError

    # # Valid: period=5 (lower bound)
    # config_min = ATRConfig(enabled=True, period=5, multiplier=2.0)
    # assert config_min.period == 5

    # # Valid: period=100 (upper bound)
    # config_max = ATRConfig(enabled=True, period=100, multiplier=2.0)
    # assert config_max.period == 100

    # # Invalid: period < 5
    # with pytest.raises(ValidationError) as exc_info:
    #     ATRConfig(enabled=True, period=3, multiplier=2.0)
    # assert "5" in str(exc_info.value) or "period" in str(exc_info.value).lower()

    # # Invalid: period > 100
    # with pytest.raises(ValidationError) as exc_info:
    #     ATRConfig(enabled=True, period=150, multiplier=2.0)
    # assert "100" in str(exc_info.value) or "period" in str(exc_info.value).lower()


def test_atr_config_multiplier_bounds():
    """T060: Test multiplier bounds (0.5-10.0)."""
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.models.config import ATRConfig
    # from pydantic import ValidationError

    # # Valid: multiplier=0.5 (lower bound)
    # config_min = ATRConfig(enabled=True, period=14, multiplier=0.5)
    # assert config_min.multiplier == 0.5

    # # Valid: multiplier=10.0 (upper bound)
    # config_max = ATRConfig(enabled=True, period=14, multiplier=10.0)
    # assert config_max.multiplier == 10.0

    # # Invalid: multiplier < 0.5
    # with pytest.raises(ValidationError) as exc_info:
    #     ATRConfig(enabled=True, period=14, multiplier=0.3)
    # assert "0.5" in str(exc_info.value) or "multiplier" in str(exc_info.value).lower()

    # # Invalid: multiplier > 10.0
    # with pytest.raises(ValidationError) as exc_info:
    #     ATRConfig(enabled=True, period=14, multiplier=15.0)
    # assert "10" in str(exc_info.value) or "multiplier" in str(exc_info.value).lower()


def test_atr_config_enabled_flag():
    """T060: Test enabled flag toggles dynamic stop-loss."""
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.models.config import ATRConfig

    # # Enabled
    # config_on = ATRConfig(enabled=True, period=14, multiplier=2.0)
    # assert config_on.enabled is True

    # # Disabled
    # config_off = ATRConfig(enabled=False, period=14, multiplier=2.0)
    # assert config_off.enabled is False


def test_atr_config_defaults():
    """T060: Test ATRConfig defaults."""
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.models.config import ATRConfig

    # # Create with defaults
    # config = ATRConfig()

    # # Should have default values
    # assert config.enabled is False  # Disabled by default
    # assert config.period == 14
    # assert config.multiplier == 2.0

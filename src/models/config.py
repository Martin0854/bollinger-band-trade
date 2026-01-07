"""
Backtest Configuration model using Pydantic for validation.
Implements data-model.md Entity 7: BacktestConfiguration
Validates all configuration values per FR-045 (spec.md)
Enhanced with auxiliary indicator configuration for Phase 1-4 rollout.
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# ========================================================================
# Enhanced Strategy Configuration Models (Entity 7: EnhancedStrategyConfig)
# Implements Phase 1-4 auxiliary indicator configuration
# ========================================================================


class TakeProfitConfig(BaseModel):
    """
    Take profit (익절) configuration.
    Controls partial profit-taking when position reaches target.
    """
    enabled: bool = Field(default=True, description="Enable take profit feature")
    target_pct: float = Field(
        default=10.0, ge=5.0, le=50.0, description="Take profit target percentage"
    )
    ratio: float = Field(
        default=0.5, ge=0.1, le=1.0, description="Partial sell ratio (0.5 = 50%)"
    )


class SqueezeAdvancedConfig(BaseModel):
    """
    Advanced squeeze detection configuration.
    Extends basic squeeze settings with expansion and tolerance parameters.
    """
    expansion_threshold_percent: float = Field(
        default=20.0, ge=5.0, le=100.0, description="Band expansion confirmation threshold (%)"
    )
    band_touch_tolerance: float = Field(
        default=0.001, ge=0.0, le=0.01, description="Band touch tolerance (0.001 = 0.1%)"
    )


class MetricsConfig(BaseModel):
    """
    Performance metrics calculation configuration.
    Controls parameters for Sharpe ratio, CAGR, and other calculations.
    """
    trading_days_per_year: int = Field(
        default=252, ge=200, le=365, description="Trading days per year for annualization"
    )
    days_per_year: int = Field(
        default=365, ge=360, le=366, description="Calendar days per year for CAGR"
    )


class VolumeFilterConfig(BaseModel):
    """
    Volume filter configuration (Phase 1).
    Filters signals based on volume spike detection.
    """
    enabled: bool = Field(default=True, description="Enable volume filter")
    window_days: int = Field(
        default=20, ge=5, le=252, description="Rolling average window (trading days)"
    )
    multiplier: float = Field(
        default=1.5, gt=0, le=10.0, description="Volume spike threshold multiplier"
    )


class RSIConfig(BaseModel):
    """
    RSI indicator configuration (Phase 1).
    Filters overbought/oversold conditions.
    """
    enabled: bool = Field(default=True, description="Enable RSI filter")
    period: int = Field(default=14, ge=5, le=100, description="RSI calculation period (days)")
    overbought: int = Field(default=70, ge=50, le=100, description="Overbought threshold")
    oversold: int = Field(default=30, ge=0, le=50, description="Oversold threshold")

    @model_validator(mode='after')
    def validate_thresholds(self):
        """Validate overbought > oversold."""
        if self.overbought <= self.oversold:
            raise ValueError(
                f"RSI overbought ({self.overbought}) must be greater than "
                f"oversold ({self.oversold})"
            )
        return self


class MACDConfig(BaseModel):
    """
    MACD indicator configuration (Phase 2).
    Confirms trend direction before entry.
    """
    enabled: bool = Field(default=False, description="Enable MACD filter (Phase 2)")
    fast_period: int = Field(default=12, ge=5, le=50, description="Fast EMA period (days)")
    slow_period: int = Field(default=26, ge=10, le=100, description="Slow EMA period (days)")
    signal_period: int = Field(default=9, ge=5, le=50, description="Signal line EMA period (days)")

    @model_validator(mode='after')
    def validate_periods(self):
        """Validate slow_period > fast_period."""
        if self.slow_period <= self.fast_period:
            raise ValueError(
                f"MACD slow_period ({self.slow_period}) must be greater than "
                f"fast_period ({self.fast_period})"
            )
        return self


class ATRConfig(BaseModel):
    """
    ATR indicator configuration (Phase 4).
    Dynamic stop-loss based on market volatility.
    """
    enabled: bool = Field(default=False, description="Enable ATR dynamic stop-loss (Phase 4)")
    period: int = Field(default=14, ge=5, le=100, description="ATR calculation period (days)")
    multiplier: float = Field(default=2.0, ge=0.5, le=10.0, description="Stop-loss distance multiplier")


class ConfidenceConfig(BaseModel):
    """
    Signal confidence scoring configuration (Phase 3).
    Weights for each filter in 0-100 point system.
    """
    threshold: int = Field(
        default=60, ge=0, le=100, description="Minimum confidence score to enter trade"
    )
    scoring: Optional[Dict[str, int]] = Field(
        default_factory=lambda: {
            'base_score': 25,      # Bollinger breakout
            'volume_score': 25,    # Volume filter pass
            'rsi_score': 20,       # RSI filter pass
            'macd_score': 30,      # MACD filter pass
        },
        description="Point allocation for each filter"
    )

    @model_validator(mode='after')
    def validate_scoring(self):
        """Validate total scoring ≤ 100 and threshold achievable."""
        if self.scoring:
            total_possible = sum(self.scoring.values())
            if total_possible > 100:
                raise ValueError(
                    f"Total confidence scoring ({total_possible}) exceeds 100 points. "
                    f"Breakdown: {self.scoring}"
                )
            if self.threshold > total_possible:
                raise ValueError(
                    f"Confidence threshold ({self.threshold}) exceeds maximum "
                    f"achievable score ({total_possible})"
                )
        return self


class EnhancedStrategyConfig(BaseModel):
    """
    Enhanced strategy configuration (Entity 7).
    Aggregates all auxiliary indicator settings for Phase 1-4 rollout.

    Backward compatible: Optional section in existing config files.
    """
    volume_filter: VolumeFilterConfig = Field(default_factory=VolumeFilterConfig)
    rsi: RSIConfig = Field(default_factory=RSIConfig)
    macd: MACDConfig = Field(default_factory=MACDConfig)
    atr: ATRConfig = Field(default_factory=ATRConfig)
    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)

    @model_validator(mode='after')
    def validate_at_least_one_filter(self):
        """At least one filter (volume, rsi, macd) must be enabled."""
        if not (self.volume_filter.enabled or self.rsi.enabled or self.macd.enabled):
            raise ValueError(
                "At least one indicator filter must be enabled "
                "(volume_filter, rsi, or macd)"
            )
        return self


# ========================================================================
# Original Backtest Configuration (Backward Compatible)
# ========================================================================


class BacktestConfiguration(BaseModel):
    """
    Configuration for Bollinger Band squeeze backtesting strategy.

    All fields validated per FR-045 requirements:
    - seed_money > 0
    - stocks: 6-digit codes matching ^\\d{6}$
    - date_range: start < end
    - bollinger_period: 5-200
    - bollinger_std_dev: 0-5
    - squeeze_threshold_percent: 5-100
    - squeeze_lookback_days: 2-30
    - stop_loss_percent: 0-100
    - max_position_size_percent: 0-100
    """

    # Portfolio Settings
    seed_money: int = Field(gt=0, description="Initial capital (KRW)")

    # Stock Selection
    stocks: List[str] = Field(min_length=1, description="6-digit Korean stock codes")

    # Backtest Period
    date_range: Tuple[date, date] = Field(description="(start_date, end_date)")

    # Bollinger Band Parameters
    bollinger_period: int = Field(ge=5, le=200, default=20, description="Moving average window")
    bollinger_std_dev: float = Field(gt=0, le=5, default=2.0, description="Std dev multiplier")

    # Squeeze Detection
    squeeze_threshold_percent: float = Field(
        ge=5, le=100, default=30, description="Band width decrease threshold (%)"
    )
    squeeze_lookback_days: int = Field(
        ge=2, le=30, default=10, description="Comparison window (days)"
    )

    # Risk Management
    stop_loss_percent: float = Field(
        ge=0, le=100, default=5, description="Maximum loss per position (%)"
    )
    max_position_percent: float = Field(
        gt=0, le=100, default=30, description="Max portfolio allocation per stock (%)"
    )
    max_positions: int = Field(default=5, description="Maximum concurrent positions")

    # Advanced Settings
    initial_positions: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Existing positions at backtest start"
    )
    risk_free_rate: float = Field(default=0.03, description="Annual risk-free rate (3%)")
    transaction_cost_percent: float = Field(ge=0, default=0.0, description="Commission + slippage (%)")

    # Optional File Paths
    data_cache_dir: Optional[str] = Field(default="data/cache", description="Data cache directory")
    log_dir: Optional[str] = Field(default="data/logs", description="Log output directory")

    # Enhanced Strategy Configuration (Phase 1-4, optional for backward compatibility)
    enhanced_strategy: Optional[EnhancedStrategyConfig] = Field(
        default=None, description="Auxiliary indicator configuration (Volume, RSI, MACD, ATR)"
    )

    # Take Profit Configuration (optional for backward compatibility)
    take_profit: Optional[TakeProfitConfig] = Field(
        default_factory=TakeProfitConfig, description="Take profit (익절) configuration"
    )

    # Advanced Squeeze Detection Configuration (optional)
    squeeze_advanced: Optional[SqueezeAdvancedConfig] = Field(
        default_factory=SqueezeAdvancedConfig, description="Advanced squeeze detection settings"
    )

    # Performance Metrics Configuration (optional)
    metrics: Optional[MetricsConfig] = Field(
        default_factory=MetricsConfig, description="Performance calculation parameters"
    )

    @field_validator('stocks')
    @classmethod
    def validate_stock_codes(cls, v: List[str]) -> List[str]:
        """Validate stock codes (Korean or US)."""
        from src.utils.validation import validate_stock_code
        for code in v:
            validate_stock_code(code)
        return v

    @field_validator('date_range')
    @classmethod
    def validate_date_range(cls, v: Tuple[date, date]) -> Tuple[date, date]:
        """Validate that start date is before end date."""
        start, end = v
        if start >= end:
            raise ValueError(
                f"Start date must be before end date: {start} >= {end}"
            )
        return v

    @classmethod
    def from_yaml(cls, path: str) -> 'BacktestConfiguration':
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            BacktestConfiguration instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is malformed or validation fails
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert date strings to date objects if needed
        if 'date_range' in data and isinstance(data['date_range'], dict):
            start_str = data['date_range']['start']
            end_str = data['date_range']['end']
            data['date_range'] = (
                date.fromisoformat(start_str),
                date.fromisoformat(end_str)
            )

        return cls(**data)

    class Config:
        """Pydantic configuration."""
        frozen = False  # Allow modification after creation
        validate_assignment = True  # Validate on field updates

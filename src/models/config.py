"""
Backtest Configuration model using Pydantic for validation.
Implements data-model.md Entity 7: BacktestConfiguration
Validates all configuration values per FR-045 (spec.md)
"""

from datetime import date
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel, Field, field_validator
import yaml


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

    @field_validator('stocks')
    @classmethod
    def validate_stock_codes(cls, v: List[str]) -> List[str]:
        """Validate that all stock codes are exactly 6 digits (Korean market format)."""
        for code in v:
            if not (code.isdigit() and len(code) == 6):
                raise ValueError(
                    f"Invalid stock code: '{code}'. "
                    f"Korean stock codes must be exactly 6 digits (e.g., '005930')"
                )
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

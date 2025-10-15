# Quick Start Guide: Enhanced Bollinger Band Squeeze Strategy

**Feature**: 002-spec-md | **Date**: 2025-10-15
**For**: Developers implementing the enhanced strategy with auxiliary indicators

## Overview

This guide provides step-by-step instructions for implementing and testing the enhanced Bollinger Band squeeze strategy with auxiliary indicators (Volume, RSI, MACD, ATR). The implementation follows a phased approach from basic filters (Phase 1) to advanced dynamic stop-loss (Phase 4).

## Prerequisites

- Python 3.11+ installed
- Poetry for dependency management
- Basic understanding of technical indicators
- Existing project structure from `bollinger-band-trade` repository

## Phase 1: Volume Filter + RSI (MVP)

### Step 1: Configure Enhanced Strategy

Create a new configuration file `config/examples/phase1_volume_rsi.yaml`:

```yaml
bollinger:
  period: 20
  std_dev: 2.0

squeeze:
  lookback_days: 10
  threshold_percent: 30.0

backtest:
  start_date: "2023-01-01"
  end_date: "2023-12-31"

portfolio:
  initial_capital: 10000000
  max_position_size: 0.3
  stop_loss_percent: 5.0

# Enhanced strategy configuration
enhanced_strategy:
  volume_filter:
    enabled: true          # Enable volume filter
    window_days: 20        # 20-day rolling average
    multiplier: 1.5        # 1.5x average volume threshold

  rsi:
    enabled: true          # Enable RSI filter
    period: 14             # Standard 14-day RSI
    overbought: 70         # Overbought threshold
    oversold: 30           # Oversold threshold

  macd:
    enabled: false         # Disable for Phase 1

  atr:
    enabled: false         # Disable for Phase 1

  confidence:
    threshold: 60          # Minimum confidence score to enter trade

stocks:
  - ticker: "005930.KS"
    name: "삼성전자"
  - ticker: "000660.KS"
    name: "SK하이닉스"
```

### Step 2: Implement Volume Filter

Create `src/indicators/volume.py`:

```python
import pandas as pd
from typing import Optional

class VolumeFilter:
    """
    Filters trading signals based on volume spike detection.

    A signal is valid only if current volume exceeds the rolling
    average by the specified multiplier.
    """

    def __init__(self, window_days: int = 20, multiplier: float = 1.5):
        """
        Args:
            window_days: Rolling window for average volume calculation
            multiplier: Volume must be >= (avg_volume * multiplier)
        """
        self.window_days = window_days
        self.multiplier = multiplier

    def calculate_average_volume(self, volumes: pd.Series) -> pd.Series:
        """Calculate rolling average volume."""
        return volumes.rolling(window=self.window_days).mean()

    def check_volume_spike(
        self,
        current_volume: float,
        avg_volume: float
    ) -> bool:
        """Check if current volume meets threshold."""
        if pd.isna(avg_volume) or avg_volume == 0:
            return False
        return current_volume >= (avg_volume * self.multiplier)
```

**Test First** (TDD requirement): Create `tests/unit/test_volume_filter.py`:

```python
import pytest
import pandas as pd
from src.indicators.volume import VolumeFilter

def test_volume_filter_spike_detection():
    # Given: 20 days of volume data with a spike on day 21
    volumes = pd.Series([1000] * 20 + [2000])
    filter = VolumeFilter(window_days=20, multiplier=1.5)

    # When: Calculate average and check spike
    avg_volume = filter.calculate_average_volume(volumes)
    has_spike = filter.check_volume_spike(
        current_volume=2000,
        avg_volume=avg_volume.iloc[-1]
    )

    # Then: Spike should be detected (2000 >= 1000 * 1.5)
    assert has_spike is True

def test_volume_filter_no_spike():
    # Given: Stable volume with no spike
    volumes = pd.Series([1000] * 21)
    filter = VolumeFilter(window_days=20, multiplier=1.5)

    # When: Check for spike
    avg_volume = filter.calculate_average_volume(volumes)
    has_spike = filter.check_volume_spike(
        current_volume=1000,
        avg_volume=avg_volume.iloc[-1]
    )

    # Then: No spike detected
    assert has_spike is False

def test_volume_filter_insufficient_data():
    # Given: Less than window_days of data
    volumes = pd.Series([1000] * 10)
    filter = VolumeFilter(window_days=20, multiplier=1.5)

    # When: Calculate average
    avg_volume = filter.calculate_average_volume(volumes)

    # Then: Should return NaN for insufficient data
    assert pd.isna(avg_volume.iloc[-1])
```

### Step 3: Implement RSI Indicator

Create `src/indicators/momentum.py`:

```python
import pandas as pd
import numpy as np

class RSIIndicator:
    """
    Relative Strength Index (RSI) using Wilder's smoothing method.

    RSI measures momentum on a 0-100 scale:
    - Above 70: Overbought (potential reversal down)
    - Below 30: Oversold (potential reversal up)
    """

    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
        """
        Args:
            period: Lookback period for RSI calculation
            overbought: Upper threshold for overbought condition
            oversold: Lower threshold for oversold condition
        """
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI using Wilder's exponential smoothing.

        Formula:
            RSI = 100 - (100 / (1 + RS))
            RS = Average Gain / Average Loss
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Wilder's smoothing (EMA with alpha = 1/period)
        avg_gain = gain.ewm(span=self.period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def is_neutral(self, rsi_value: float) -> bool:
        """Check if RSI is in neutral zone (30 < RSI < 70)."""
        if pd.isna(rsi_value):
            return False
        return self.oversold < rsi_value < self.overbought
```

**Test First**: Create `tests/unit/test_momentum.py`:

```python
import pytest
import pandas as pd
from src.indicators.momentum import RSIIndicator

def test_rsi_calculation_basic():
    # Given: Simple price series with upward trend
    prices = pd.Series([100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                        111, 113, 112, 114, 116])
    rsi = RSIIndicator(period=14)

    # When: Calculate RSI
    rsi_values = rsi.calculate(prices)

    # Then: RSI should be above 50 (uptrend)
    assert rsi_values.iloc[-1] > 50
    assert not pd.isna(rsi_values.iloc[-1])

def test_rsi_neutral_zone():
    # Given: RSI indicator with standard thresholds
    rsi = RSIIndicator(period=14, overbought=70, oversold=30)

    # When: Check neutral zone
    assert rsi.is_neutral(50) is True
    assert rsi.is_neutral(75) is False  # Overbought
    assert rsi.is_neutral(25) is False  # Oversold

def test_rsi_insufficient_data():
    # Given: Less than period days of data
    prices = pd.Series([100, 102, 104])
    rsi = RSIIndicator(period=14)

    # When: Calculate RSI
    rsi_values = rsi.calculate(prices)

    # Then: Early values should be NaN
    assert pd.isna(rsi_values.iloc[0])
```

### Step 4: Integrate with Signal Generator

Update `src/signals/generator.py` to use enhanced filters:

```python
from typing import Optional
from src.indicators.volume import VolumeFilter
from src.indicators.momentum import RSIIndicator
from src.models.trade import EnhancedSignal

class EnhancedSignalGenerator:
    """
    Generates trading signals with auxiliary indicator filters.
    """

    def __init__(
        self,
        volume_filter: Optional[VolumeFilter] = None,
        rsi_indicator: Optional[RSIIndicator] = None,
        confidence_threshold: int = 60
    ):
        self.volume_filter = volume_filter
        self.rsi_indicator = rsi_indicator
        self.confidence_threshold = confidence_threshold

    def generate_signal(
        self,
        price: float,
        volume: float,
        avg_volume: float,
        rsi: float,
        bollinger_breakout: bool
    ) -> Optional[EnhancedSignal]:
        """
        Generate signal only if confidence score exceeds threshold.
        """
        if not bollinger_breakout:
            return None

        # Calculate confidence score
        score = 25  # Base score for Bollinger breakout

        # Volume filter (25 points)
        volume_pass = False
        if self.volume_filter and self.volume_filter.check_volume_spike(volume, avg_volume):
            score += 25
            volume_pass = True

        # RSI filter (20 points)
        rsi_pass = False
        if self.rsi_indicator and self.rsi_indicator.is_neutral(rsi):
            score += 20
            rsi_pass = True

        # Check threshold
        if score < self.confidence_threshold:
            return None

        return EnhancedSignal(
            price=price,
            confidence_score=score,
            volume_pass=volume_pass,
            rsi_pass=rsi_pass,
            macd_pass=False,  # Phase 2
            rsi_value=rsi
        )
```

### Step 5: Run Phase 1 Backtest

```bash
# Run backtest with Phase 1 configuration
python scripts/main.py backtest --config config/examples/phase1_volume_rsi.yaml

# Expected output structure:
# results/
# └── backtest_phase1_2025-10-15.xlsx
#     ├── Summary (승률, 수익률, 신뢰도)
#     ├── Trades (각 거래 + confidence_score)
#     └── Daily (일별 수익률)
```

### Step 6: Verify Results

Expected improvements over baseline:
- **Win Rate**: 50-55% (baseline) → 55-60% (Phase 1)
- **Annual Return**: -2%~0% (baseline) → +5~8% (Phase 1)
- **Signal Count**: Reduced by 30-40% (fewer false signals)

Check the Excel output for:
1. `confidence_score` column in Trades sheet (should be ≥60)
2. `volume_pass` and `rsi_pass` columns showing filter results
3. Summary sheet showing improved metrics

## Phase 2: Add MACD Filter

### Step 7: Enable MACD in Configuration

Update `config/examples/phase2_with_macd.yaml`:

```yaml
enhanced_strategy:
  volume_filter:
    enabled: true
  rsi:
    enabled: true
  macd:
    enabled: true           # NEW: Enable MACD
    fast_period: 12
    slow_period: 26
    signal_period: 9
  atr:
    enabled: false
  confidence:
    threshold: 70           # Increase threshold with additional filter
    scoring:
      base_score: 25
      volume_score: 25
      rsi_score: 20
      macd_score: 30        # MACD adds 30 points
```

### Step 8: Implement MACD Indicator

Add to `src/indicators/momentum.py`:

```python
from dataclasses import dataclass

@dataclass
class MACDResult:
    macd_line: float
    signal_line: float
    histogram: float

class MACDIndicator:
    """
    Moving Average Convergence Divergence (MACD).

    Detects trend direction and momentum:
    - MACD > Signal: Bullish (uptrend)
    - MACD < Signal: Bearish (downtrend)
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def calculate(self, prices: pd.Series) -> pd.DataFrame:
        """Calculate MACD, signal line, and histogram."""
        ema_fast = prices.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })

    def is_bullish(self, macd: float, signal: float) -> bool:
        """Check if MACD indicates bullish trend."""
        if pd.isna(macd) or pd.isna(signal):
            return False
        return macd > signal
```

**Test First**: Add to `tests/unit/test_momentum.py`:

```python
def test_macd_bullish_signal():
    # Given: Uptrending price series
    prices = pd.Series(range(100, 150))
    macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)

    # When: Calculate MACD
    result = macd.calculate(prices)

    # Then: Should be bullish (MACD > signal)
    assert macd.is_bullish(
        result['macd'].iloc[-1],
        result['signal'].iloc[-1]
    ) is True
```

### Step 9: Run Phase 2 Backtest

```bash
python scripts/main.py backtest --config config/examples/phase2_with_macd.yaml
```

Expected improvements:
- **Win Rate**: 60-65%
- **Annual Return**: +8~12%
- **Signal Count**: Further reduced by 20-30%

## Phase 3: Confidence Scoring System

Phase 3 uses the existing confidence scoring implemented in Phases 1-2. Verify by:

1. Checking `confidence_score` values in output
2. Testing different threshold values (50, 60, 70)
3. Analyzing relationship between confidence and win rate

```bash
# Test with lower threshold
sed -i 's/threshold: 70/threshold: 50/' config/examples/phase2_with_macd.yaml
python scripts/main.py backtest --config config/examples/phase2_with_macd.yaml
```

## Phase 4: Dynamic Stop-Loss with ATR

### Step 10: Enable ATR-based Stop-Loss

Update `config/examples/phase4_dynamic_stop.yaml`:

```yaml
portfolio:
  initial_capital: 10000000
  # stop_loss_percent is ignored when atr.enabled = true

enhanced_strategy:
  volume_filter:
    enabled: true
  rsi:
    enabled: true
  macd:
    enabled: true
  atr:
    enabled: true          # NEW: Enable ATR stop-loss
    period: 14
    multiplier: 2.0        # Stop-loss = entry_price - (ATR * 2)
  confidence:
    threshold: 60
```

### Step 11: Implement ATR Indicator

Add to `src/indicators/momentum.py`:

```python
class ATRIndicator:
    """
    Average True Range (ATR) - volatility measure for dynamic stop-loss.

    ATR measures market volatility by calculating the average of true ranges
    over a specified period.
    """

    def __init__(self, period: int = 14, multiplier: float = 2.0):
        self.period = period
        self.multiplier = multiplier

    def calculate(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate ATR using Wilder's smoothing."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=self.period, adjust=False).mean()

        return atr

    def calculate_stop_loss(self, entry_price: float, atr_value: float) -> float:
        """Calculate dynamic stop-loss price."""
        return entry_price - (atr_value * self.multiplier)
```

### Step 12: Update Risk Controls

Update `src/risk/controls.py`:

```python
from src.indicators.momentum import ATRIndicator

class RiskManager:
    def __init__(self, atr_indicator: Optional[ATRIndicator] = None):
        self.atr_indicator = atr_indicator

    def calculate_stop_loss(
        self,
        entry_price: float,
        fixed_percent: float = 0.05,
        atr_value: Optional[float] = None
    ) -> float:
        """
        Calculate stop-loss price.
        Uses ATR if available, otherwise falls back to fixed percentage.
        """
        if self.atr_indicator and atr_value:
            return self.atr_indicator.calculate_stop_loss(entry_price, atr_value)
        else:
            return entry_price * (1 - fixed_percent)
```

### Step 13: Run Phase 4 Backtest

```bash
python scripts/main.py backtest --config config/examples/phase4_dynamic_stop.yaml
```

Expected improvements:
- **Win Rate**: 65-70%
- **Annual Return**: +12~15%
- **Max Drawdown**: Reduced by 20-30%

## Testing Strategy

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific indicator tests
pytest tests/unit/test_volume_filter.py -v
pytest tests/unit/test_momentum.py -v
```

### Integration Tests

```bash
# Run end-to-end backtest tests
pytest tests/integration/test_backtest_e2e.py -v

# Run performance benchmarks
pytest tests/unit/ --benchmark-only
```

### Property-Based Testing with Hypothesis

Example from `tests/unit/test_volume_filter.py`:

```python
from hypothesis import given, strategies as st

@given(
    volumes=st.lists(st.floats(min_value=1000, max_value=100000), min_size=21, max_size=21),
    multiplier=st.floats(min_value=1.0, max_value=5.0)
)
def test_volume_filter_properties(volumes, multiplier):
    """Property: If current volume >= avg * multiplier, spike is detected."""
    filter = VolumeFilter(window_days=20, multiplier=multiplier)
    volumes_series = pd.Series(volumes)
    avg_volume = filter.calculate_average_volume(volumes_series).iloc[-1]

    if volumes[-1] >= avg_volume * multiplier:
        assert filter.check_volume_spike(volumes[-1], avg_volume) is True
```

## Performance Optimization

### Vectorization

All indicator calculations use pandas vectorized operations:

```python
# Good: Vectorized
rsi = 100 - (100 / (1 + rs))  # Entire series at once

# Bad: Loop-based
rsi = pd.Series([100 - (100 / (1 + r)) for r in rs])  # Avoid!
```

### Caching

Enable caching for repeated calculations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_rsi_cached(ticker: str, period: int):
    # Expensive calculation
    pass
```

## Troubleshooting

### Issue: "Insufficient data for indicator calculation"

**Solution**: Ensure backtest period includes enough warmup data:

```yaml
backtest:
  start_date: "2023-01-01"  # Add 30+ days before actual test period
  end_date: "2023-12-31"
```

### Issue: "No signals generated"

**Solution**: Check confidence threshold and enabled filters:

```yaml
confidence:
  threshold: 60  # Lower if too restrictive

# Ensure at least volume OR rsi is enabled
volume_filter:
  enabled: true
rsi:
  enabled: true
```

### Issue: "Validation error: confidence score exceeds 100"

**Solution**: Verify scoring configuration:

```yaml
confidence:
  scoring:
    base_score: 25
    volume_score: 25
    rsi_score: 20
    macd_score: 30
    # Total: 100 (valid)
```

## Next Steps

1. **Run baseline comparison**: Compare Phase 1 results vs original strategy
2. **Parameter tuning**: Experiment with RSI thresholds (60/40), volume multipliers (1.2-2.0)
3. **Multi-stock testing**: Test across KOSPI 100 stocks
4. **Performance profiling**: Use `pytest-benchmark` to identify bottlenecks
5. **Production deployment**: Follow `/speckit.implement` workflow for task execution

## References

- **Specification**: [specs/002-spec-md/spec.md](./spec.md)
- **Data Model**: [specs/002-spec-md/data-model.md](./data-model.md)
- **Research**: [specs/002-spec-md/research.md](./research.md)
- **Configuration Schema**: [specs/002-spec-md/contracts/config-schema.yaml](./contracts/config-schema.yaml)
- **Implementation Plan**: [specs/002-spec-md/plan.md](./plan.md)

## Support

For issues or questions:
1. Check existing tests for examples: `tests/unit/test_*.py`
2. Review data model for entity definitions: `data-model.md`
3. Validate configuration against schema: `contracts/config-schema.yaml`
4. Consult research notes for algorithm details: `research.md`

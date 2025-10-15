# Usage Guide - Bollinger Band Backtester

This guide shows you how to use the Bollinger Band squeeze backtesting system.

## Quick Start

### 1. Run the Simple Example

The easiest way to get started:

```bash
poetry run python examples/simple_backtest.py
```

This will run a backtest with mock data and display results like:

```
Running backtest...

============================================================
BACKTEST RESULTS
============================================================
Initial Capital:     ₩10,000,000
Total Return:        5.23%
Win Rate:            66.67%
Max Drawdown:        -2.15%
Sharpe Ratio:        1.45

Total Trades:        6
  - Winning:         4
  - Losing:          2
Average Win:         ₩85,000
Average Loss:        ₩-35,000
Win/Loss Ratio:      2.43
Profit Factor:       3.25
============================================================
```

## Configuration Options

### YAML Configuration

Create a YAML file (see `examples/config_example.yaml`):

```yaml
# Portfolio
seed_money: 10000000  # Starting capital (KRW)

# Stocks (6-digit Korean stock codes)
stocks:
  - "005930"  # Samsung Electronics
  - "035720"  # Kakao

# Backtest period
date_range:
  start: "2024-01-01"
  end: "2024-12-31"

# Strategy parameters
bollinger_period: 20           # Moving average window
bollinger_std_dev: 2.0         # Std dev multiplier
squeeze_threshold_percent: 30  # Squeeze detection threshold
squeeze_lookback_days: 10      # Days to compare for squeeze
stop_loss_percent: 5           # Stop loss trigger
max_position_percent: 30       # Max % per position
max_positions: 5               # Max concurrent positions
```

### Programmatic Configuration

```python
from datetime import date
from src.models.config import BacktestConfiguration

config = BacktestConfiguration(
    seed_money=10_000_000,
    stocks=["005930", "035720"],
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    bollinger_period=20,
    bollinger_std_dev=2.0,
    squeeze_threshold_percent=30.0,
    squeeze_lookback_days=10,
    stop_loss_percent=5.0,
    max_position_percent=30.0,
    max_positions=5
)
```

## Loading Data

### Option 1: Mock Data (Testing)

```python
import pandas as pd
from src.backtest.engine import BacktestEngine

engine = BacktestEngine(config=config)

# Create mock OHLCV data
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
mock_data = pd.DataFrame({
    'Open': [60000] * len(dates),
    'High': [61000] * len(dates),
    'Low': [59000] * len(dates),
    'Close': [60000 + i * 100 for i in range(len(dates))],
    'Volume': [1_000_000] * len(dates)
}, index=dates)

engine.load_mock_data("005930", mock_data)
```

### Option 2: Real Data (TODO - User Story 3)

Real data fetching is not yet implemented. You'll need to:

1. Fetch data from Korean exchanges (KRW-API, Yahoo Finance, etc.)
2. Convert to pandas DataFrame with columns: `Open, High, Low, Close, Volume`
3. Ensure index is DatetimeIndex
4. Load into engine using `load_mock_data()` (will be renamed to `load_data()`)

Example placeholder:

```python
# TODO: Implement in User Story 3
def fetch_korean_stock_data(stock_code, start_date, end_date):
    """
    Fetch OHLCV data from Korean exchange API.
    Returns: pd.DataFrame with OHLCV columns
    """
    pass  # To be implemented
```

## Running the Backtest

```python
# Run the backtest
report = engine.run()

# Access results
print(f"Total Return: {report.total_return_pct}%")
print(f"Win Rate: {report.win_rate_pct}%")
print(f"Sharpe Ratio: {report.sharpe_ratio}")
print(f"Number of Trades: {report.num_trades}")

# View trade history
for trade in engine.trades:
    print(f"{trade.action} {trade.quantity} @ ₩{trade.execution_price}")
    if trade.realized_pnl:
        print(f"  P&L: ₩{trade.realized_pnl}")
```

## Understanding the Strategy

### How It Works

1. **Calculate Bollinger Bands**
   - Middle band = 20-day SMA
   - Upper/Lower bands = Middle ± (2 × Standard Deviation)

2. **Detect Squeeze**
   - Bandwidth decreases by 30% over 10 days
   - OR bandwidth is within 20% of historical minimum (consolidation)

3. **Entry Signal**
   - Squeeze/consolidation detected
   - Price breaks above upper Bollinger Band
   - Bandwidth is expanding (>10% above minimum)
   - Portfolio has capacity

4. **Exit Signals**
   - **Stop Loss**: Position loses 5% (configurable)
   - **Middle Band Cross**: Price drops below middle band
   - Manual exit (not yet implemented)

### Risk Management

- **Position Sizing**: Maximum 30% of portfolio per stock
- **Max Positions**: Up to 5 concurrent positions
- **Stop Loss**: Automatic 5% stop loss on all positions
- **Portfolio Limits**: Respects cash balance and position limits

## Viewing Results

### Performance Metrics

```python
report = engine.run()

# Returns
report.total_return_pct  # Total return percentage
report.cagr_pct          # Compound annual growth rate

# Win Rate
report.win_rate_pct           # Percentage of winning trades
report.num_winning_trades     # Count of winning trades
report.num_losing_trades      # Count of losing trades

# Risk Metrics
report.max_drawdown_pct  # Maximum drawdown
report.sharpe_ratio      # Risk-adjusted return

# Trade Statistics
report.avg_win           # Average winning trade P&L
report.avg_loss          # Average losing trade P&L
report.win_loss_ratio    # Ratio of avg win to avg loss
report.profit_factor     # Gross profit / gross loss
```

### Trade Log Database

Trade logs are automatically saved to SQLite:

```python
import sqlite3

# Connect to trade log
conn = sqlite3.connect('data/logs/backtest.db')

# Query trades
trades_df = pd.read_sql_query("SELECT * FROM trade_log", conn)
print(trades_df)

# Query squeeze events
squeezes_df = pd.read_sql_query("SELECT * FROM squeeze_events", conn)
print(squeezes_df)

conn.close()
```

### Export to JSON

```python
# Convert report to JSON-serializable dict
report_dict = report.to_dict()

import json
with open('backtest_results.json', 'w') as f:
    json.dump(report_dict, f, indent=2)
```

## Examples

### Example 1: Conservative Strategy

```python
config = BacktestConfiguration(
    seed_money=10_000_000,
    stocks=["005930"],
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    bollinger_period=30,        # Longer period = less sensitive
    bollinger_std_dev=2.5,      # Wider bands = fewer signals
    squeeze_threshold_percent=40,  # Stricter squeeze detection
    stop_loss_percent=3.0,      # Tighter stop loss
    max_position_percent=20.0,  # Smaller positions
    max_positions=3             # Fewer concurrent trades
)
```

### Example 2: Aggressive Strategy

```python
config = BacktestConfiguration(
    seed_money=10_000_000,
    stocks=["005930", "035720", "000660", "051910", "005380"],
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    bollinger_period=10,        # Shorter period = more sensitive
    bollinger_std_dev=1.5,      # Narrower bands = more signals
    squeeze_threshold_percent=20,  # Looser squeeze detection
    stop_loss_percent=10.0,     # Wider stop loss
    max_position_percent=40.0,  # Larger positions
    max_positions=5             # More concurrent trades
)
```

### Example 3: Multiple Stocks

```python
config = BacktestConfiguration(
    seed_money=50_000_000,  # Higher capital for multiple stocks
    stocks=[
        "005930",  # Samsung Electronics
        "035720",  # Kakao
        "000660",  # SK Hynix
        "051910",  # LG Chem
        "005380",  # Hyundai Motor
        "068270",  # Celltrion
    ],
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    max_positions=5  # Will diversify across multiple stocks
)

engine = BacktestEngine(config=config)

# Load data for each stock
for stock_code in config.stocks:
    # Fetch data for this stock
    data = fetch_data(stock_code)  # Your data fetching function
    engine.load_mock_data(stock_code, data)

report = engine.run()
```

## Troubleshooting

### No Trades Executed

If `report.num_trades == 0`:

1. **Check data quality**: Ensure OHLCV data has sufficient volatility
2. **Adjust squeeze threshold**: Try lowering `squeeze_threshold_percent` to 20-25%
3. **Check date range**: Ensure you have at least 30+ days of data
4. **Verify data format**: Must have `Open, High, Low, Close, Volume` columns with DatetimeIndex

### Validation Errors

```python
from pydantic import ValidationError

try:
    config = BacktestConfiguration(...)
except ValidationError as e:
    print(e.errors())
```

Common validation errors:
- `seed_money` must be positive
- Stock codes must be exactly 6 digits
- `date_range[0]` must be before `date_range[1]`
- `bollinger_period` must be between 5 and 200
- `stop_loss_percent` must be between 0 and 100

### Insufficient Data

Bollinger Bands require at least `bollinger_period` days of data (default: 20 days).
Squeeze detection requires an additional `squeeze_lookback_days` (default: 10 days).

**Minimum recommended**: 50+ days of OHLCV data

## Next Steps

### Implemented (User Story 1) ✅
- ✅ Core models (Portfolio, Position, Trade, Config)
- ✅ Bollinger Band calculation
- ✅ Squeeze detection
- ✅ Signal generation
- ✅ Risk controls
- ✅ Backtest engine
- ✅ Performance metrics
- ✅ Database logging
- ✅ CLI interface

### Coming Soon (Optional)
- 📋 **User Story 2**: Multi-stock portfolio optimization
- 📋 **User Story 3**: Automated data fetching from Korean exchanges
- 📋 **User Story 4**: Parameter optimization (grid search, genetic algorithms)
- 📋 **User Story 5**: Visualization dashboard (equity curve, trade markers, etc.)

## Resources

- **Project Spec**: `specs/001-readme-md/spec.md`
- **Architecture**: `specs/001-readme-md/data-model.md`
- **Implementation Plan**: `specs/001-readme-md/plan.md`
- **Tests**: Run `poetry run pytest tests/` to see all test cases
- **Korean Stock Codes**: [KRX Market Data](http://kind.krx.co.kr)

## Support

- Issues: File an issue with reproduction steps
- Tests: Run `poetry run pytest -v` to see which components work
- Coverage: Run `poetry run pytest --cov=src --cov-report=html` to see test coverage

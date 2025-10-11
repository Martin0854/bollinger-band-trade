# Quickstart Guide: Bollinger Band Auto-Trading Bot

**Feature**: Bollinger Band Squeeze Strategy Backtesting
**Target Users**: Traders, quantitative analysts, Python developers
**Estimated Setup Time**: 10-15 minutes

---

## Overview

This guide walks you through installing the backtesting system, running your first backtest with Korean stock market data (KOSPI/KOSDAQ), and interpreting the results.

**What You'll Build**: A backtesting simulation that detects Bollinger Band squeezes (volatility contractions), generates buy/sell signals when bands expand, and measures strategy performance with risk-adjusted metrics.

---

## Prerequisites

- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **pip** or **Poetry** for dependency management
- Internet connection (to fetch Korean market data)
- Basic familiarity with command-line tools

**Verify Python version**:
```bash
python --version  # Should show 3.11 or higher
```

---

## Step 1: Installation

### Option A: Using pip (Recommended for Users)

```bash
# Clone the repository
git clone https://github.com/your-org/bollinger-band-trade.git
cd bollinger-band-trade

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option B: Using Poetry (Recommended for Developers)

```bash
# Clone the repository
git clone https://github.com/your-org/bollinger-band-trade.git
cd bollinger-band-trade

# Install dependencies via Poetry
poetry install

# Activate virtual environment
poetry shell
```

**Expected Installation Time**: 2-3 minutes (downloads ~500MB of dependencies)

---

## Step 2: Create Your First Configuration

Create a configuration file at `config/my_first_backtest.yaml`:

```yaml
# Portfolio Settings
seed_money: 10000000  # 10 million KRW (~$7,500 USD)

# Stock Selection (Korean stock codes)
stocks:
  - "005930"  # Samsung Electronics
  - "000660"  # SK Hynix

# Backtest Period
date_range:
  start: "2024-01-01"
  end: "2024-12-31"

# Bollinger Band Parameters
bollinger_period: 20          # 20-day moving average
bollinger_std_dev: 2.0        # 2 standard deviations

# Squeeze Detection
squeeze_threshold_percent: 30  # Detect 30% band width decrease
squeeze_lookback_days: 10      # Over 10-day window

# Risk Management
stop_loss_percent: 5           # Auto-exit at 5% loss
max_position_size_percent: 30  # Max 30% per stock

# Advanced (Optional)
risk_free_rate: 0.03           # 3% for Sharpe ratio
transaction_cost_percent: 0.0  # Zero fees (simplified)
```

**Configuration Tips**:
- **stocks**: Use 6-digit Korean stock codes (find codes at [KRX website](http://www.krx.co.kr))
- **date_range**: Must be historical dates (backtesting uses past data)
- **squeeze_threshold_percent**: Higher values = fewer, stronger signals (try 20-40%)
- **stop_loss_percent**: Lower values = tighter risk control but more frequent exits

---

## Step 3: Run Your First Backtest

```bash
# Run backtest with your configuration
python -m src.cli.main backtest --config config/my_first_backtest.yaml

# Expected output:
# [2025-10-11 14:30:00] Loading configuration from config/my_first_backtest.yaml
# [2025-10-11 14:30:01] Fetching data for stocks: 005930, 000660
# [2025-10-11 14:30:03] Data validation: PASS (250 trading days, 0 missing)
# [2025-10-11 14:30:03] Calculating Bollinger Bands...
# [2025-10-11 14:30:03] Detecting squeeze events...
# [2025-10-11 14:30:03] Running backtest simulation...
# [2025-10-11 14:30:04] Backtest complete!
#
# === Performance Report ===
# Final Portfolio Value: 11,250,000 KRW
# Total Return:          +12.50%
# Win Rate:              58.33% (7/12 trades)
# Maximum Drawdown:      -8.20%
# Sharpe Ratio:          1.35
# Total Trades:          12
# Squeeze Events:        8
#
# Reports saved to:
# - data/logs/report_abc123.json
# - data/logs/trades_abc123.csv
```

**Execution Time**: 3-5 seconds for 1 year, 2 stocks (per performance target)

---

## Step 4: Analyze Results

### 4.1 View Trade Log

```bash
# Open trade log CSV
cat data/logs/trades_abc123.csv

# Sample output:
# trade_id,timestamp,stock_code,action,quantity,price,reason,realized_pnl
# 1,2024-02-15 15:30:00,005930,buy,50,60000,squeeze_expansion_buy,
# 2,2024-03-10 15:30:00,005930,sell,50,65000,band_upper_exit,250000
# 3,2024-04-22 15:30:00,000660,buy,80,45000,squeeze_expansion_buy,
# 4,2024-05-05 15:30:00,000660,sell,80,43000,stop_loss,-160000
```

**Key Columns**:
- **reason**: Why the trade happened (e.g., `squeeze_expansion_buy`, `stop_loss`)
- **realized_pnl**: Profit/loss in KRW (only for sell trades)

### 4.2 View Performance Report (JSON)

```bash
# View full report
cat data/logs/report_abc123.json | python -m json.tool

# Sample output (formatted):
{
  "report_id": "abc123",
  "backtest_date": "2025-10-11T14:30:04",
  "final_portfolio_value": 11250000,
  "total_return_pct": 12.50,
  "win_rate_pct": 58.33,
  "max_drawdown_pct": 8.20,
  "sharpe_ratio": 1.35,
  "num_trades": 12,
  "num_squeeze_events": 8,
  "trades": [...]
}
```

### 4.3 Visualize Equity Curve (Optional)

```bash
# Generate equity curve chart (requires matplotlib)
python -m src.cli.main visualize --report data/logs/report_abc123.json

# Opens a browser window with:
# - Portfolio value over time (line chart)
# - Drawdown chart
# - Trade markers on price chart with Bollinger Bands
```

---

## Step 5: Optimize Parameters (Advanced)

Want to find the best Bollinger Band settings? Run parameter optimization:

```bash
# Create optimization config
cat > config/optimize.yaml << EOF
base_config: config/my_first_backtest.yaml

# Parameter grid to test
parameter_grid:
  bollinger_period: [10, 20, 30]
  bollinger_std_dev: [1.5, 2.0, 2.5]
  squeeze_threshold_percent: [20, 30, 40]

# Optimization metric (what to maximize)
optimize_for: sharpe_ratio
EOF

# Run optimization
python -m src.cli.main optimize --config config/optimize.yaml

# Expected output:
# Testing 27 combinations (3 × 3 × 3)...
# [1/27] period=10, std=1.5, threshold=20 → Sharpe: 0.85
# [2/27] period=10, std=1.5, threshold=30 → Sharpe: 1.10
# ...
# [27/27] period=30, std=2.5, threshold=40 → Sharpe: 1.45
#
# === Top 3 Configurations ===
# 1. period=20, std=2.0, threshold=30 → Sharpe: 1.52 ⭐
# 2. period=30, std=2.5, threshold=40 → Sharpe: 1.45
# 3. period=20, std=2.5, threshold=30 → Sharpe: 1.38
```

**Warning**: Parameter optimization uses past data. Always validate results on a separate time period to avoid overfitting.

---

## Understanding Key Metrics

### Total Return
- **What**: Percentage gain/loss from initial capital
- **Formula**: `(final_value - initial_capital) / initial_capital × 100`
- **Good**: > 10% annual
- **Excellent**: > 20% annual

### Win Rate
- **What**: Percentage of profitable trades
- **Formula**: `(winning_trades / total_trades) × 100`
- **Good**: > 50%
- **Note**: High win rate ≠ profitability (one big loss can wipe out many small wins)

### Maximum Drawdown (MDD)
- **What**: Largest peak-to-trough decline during backtest
- **Formula**: `max((peak - trough) / peak)`
- **Good**: < 15%
- **Critical**: If MDD > 30%, strategy may be too risky

### Sharpe Ratio
- **What**: Risk-adjusted return (higher = better return per unit of risk)
- **Formula**: `(avg_return - risk_free_rate) / std_dev_returns`
- **Good**: > 1.0
- **Excellent**: > 2.0
- **Note**: Uses 3% risk-free rate (Korean government bonds)

---

## Common Issues & Troubleshooting

### Issue 1: "No data available for stock code"

**Cause**: Invalid stock code or network error

**Solution**:
1. Verify stock code is 6 digits (e.g., "005930", not "5930")
2. Check internet connection
3. Try alternative data source:
   ```bash
   python -m src.cli.main backtest --config config/my_first_backtest.yaml --data-source pykrx
   ```

### Issue 2: "Missing trading days detected"

**Cause**: Data source returned incomplete data (holidays, API issues)

**Solution**:
1. Check date range doesn't include weekends/recent dates (data may not be available yet)
2. Allow gaps with `--allow-incomplete` flag:
   ```bash
   python -m src.cli.main backtest --config config/my_first_backtest.yaml --allow-incomplete
   ```

### Issue 3: "Backtest too slow (>5 seconds)"

**Cause**: Large date range or too many stocks

**Solution**:
1. Reduce date range (test with 1 year first)
2. Reduce number of stocks (max 10 for MVP)
3. Enable caching (automatic after first run)

### Issue 4: "No trades executed"

**Cause**: No squeeze events detected with current parameters

**Solution**:
1. Lower `squeeze_threshold_percent` (try 20% instead of 30%)
2. Increase `squeeze_lookback_days` (try 15 instead of 10)
3. Check if stock is low-volatility (try different stocks)

---

## Next Steps

### Learn the Strategy
- Read [Bollinger Band Squeeze Strategy](https://www.investopedia.com/articles/trading/09/bollinger-band-squeeze.asp)
- Review [spec.md](./spec.md) for detailed requirements
- Understand [data-model.md](./data-model.md) for entity definitions

### Customize
- Modify configuration parameters (see [config-schema.yaml](./contracts/config-schema.yaml))
- Add more stocks (KOSPI/KOSDAQ codes)
- Test different time periods (2020-2024 for longer backtests)

### Contribute
- Run tests: `pytest tests/`
- Follow TDD workflow (see [constitution.md](../.specify/memory/constitution.md))
- Submit pull requests with new features

### Deploy (Future)
- Connect to live market data feeds
- Implement paper trading (simulated real-time)
- Add alert system for squeeze detection

---

## Configuration Examples

### Conservative Strategy (Lower Risk)
```yaml
stop_loss_percent: 3            # Tighter stop-loss
max_position_size_percent: 20   # Smaller positions
squeeze_threshold_percent: 40   # Fewer, stronger signals
```

### Aggressive Strategy (Higher Risk)
```yaml
stop_loss_percent: 10           # Wider stop-loss
max_position_size_percent: 50   # Larger positions
squeeze_threshold_percent: 20   # More frequent signals
```

### Long-Only Blue Chips
```yaml
stocks:
  - "005930"  # Samsung Electronics
  - "000660"  # SK Hynix
  - "035420"  # NAVER
  - "035720"  # Kakao
  - "051910"  # LG Chem
```

---

## Getting Help

- **Documentation**: See [README.md](../../README.md)
- **Issues**: Report bugs at [GitHub Issues](https://github.com/your-org/bollinger-band-trade/issues)
- **Discussions**: Join [Discussions](https://github.com/your-org/bollinger-band-trade/discussions)
- **Constitution**: Review project principles at [constitution.md](../.specify/memory/constitution.md)

---

## Disclaimer

⚠️ **EDUCATIONAL PURPOSE ONLY**: This system is for backtesting and research. It does not execute real trades. Past performance does not guarantee future results. Trading stocks involves risk of loss. Always consult a financial advisor before making investment decisions.

**Risk Acknowledgment**: By using this software, you acknowledge:
- No guarantees of profitability
- You are solely responsible for trading decisions
- Backtesting may not reflect real-world slippage/costs
- Future market conditions may differ from historical data

---

**Ready to backtest?** Start with Step 1 and run your first simulation in under 15 minutes! 🚀

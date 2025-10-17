# Quickstart Guide: Cryptocurrency Backtesting

**Feature**: 003-crypto-backtest-support
**Purpose**: Get started with cryptocurrency backtesting in 5 minutes

## Prerequisites

Before running cryptocurrency backtests, ensure you have:

- Python 3.11+ installed
- Poetry dependency manager
- Existing bollinger-band-trade repository cloned
- Internet connection (for Binance API access)

## Installation

### 1. Install New Dependencies

```bash
# Add python-binance to your project
poetry add python-binance

# Install dependencies
poetry install
```

### 2. Verify Installation

```python
# Test Binance API connectivity
python -c "from binance.client import Client; c = Client(); print('Binance API OK')"
```

If this succeeds, you're ready to run crypto backtests.

## Running Your First Crypto Backtest

### Quick Start (5 minutes)

```bash
# Run the example crypto backtest
poetry run python examples/crypto_btc_eth_backtest.py
```

Expected output:
```
Market Type: crypto
Symbols: ['BTCUSDT', 'ETHUSDT']
Fee: 0.1%
Fetching BTCUSDT... ✅ 365 candles
Fetching ETHUSDT... ✅ 365 candles
Running backtest...
================================================================================
Crypto Backtest Results
================================================================================
Total Return: 15.32%
Win Rate: 42.5%
Max Drawdown: -8.7%
Sharpe Ratio: 1.23
...
```

## Configuration

### Create a Custom Crypto Config

Create `config/my_crypto_backtest.yaml`:

```yaml
# Market Configuration
market_type: crypto
symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT

# Backtest Period
date_range:
  start: "2023-01-01"
  end: "2024-01-01"

# Initial Capital
seed_money: 10000  # 10,000 USDT

# Bollinger Band Strategy
bollinger_period: 20
bollinger_std_dev: 2.0

# Risk Management
stop_loss_percent: 5.0
max_position_percent: 30.0
max_positions: 3

# Crypto-Specific Settings
crypto_config:
  trading_fee_percent: 0.1  # Binance default
  min_order_value_usdt: 10.0
  quote_currency: USDT

# Enhanced Strategy (Optional)
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 20
    multiplier: 1.5

  rsi:
    enabled: true
    period: 14
    overbought: 70
    oversold: 30

  macd:
    enabled: false

  atr:
    enabled: true
    period: 14
    multiplier: 2.0

  confidence_scoring:
    enabled: true
    min_confidence: 60
```

### Run with Custom Config

```python
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from src.data.providers.factory import DataProviderFactory

# Load config
config = BacktestConfiguration.from_yaml("config/my_crypto_backtest.yaml")

# Create data provider
provider = DataProviderFactory.create_provider(config.market_type)

# Initialize engine
engine = BacktestEngine(config=config)

# Fetch data for all symbols
for symbol in config.symbols:
    df = provider.fetch_ohlcv(
        symbol=symbol,
        start_date=config.date_range[0],
        end_date=config.date_range[1]
    )
    if df is not None:
        engine.load_market_data(symbol, df)

# Run backtest
report = engine.run()

# Display results
print(f"Total Return: {report.total_return_pct:.2f}%")
print(f"Win Rate: {report.win_rate_pct:.2f}%")
print(f"Sharpe Ratio: {report.sharpe_ratio:.2f}")
```

## Key Differences: Crypto vs Stock

### Symbol Format
```python
# Stock symbols: 6-digit codes
symbols: ["005930", "000660", "035720"]  # Samsung, SK Hynix, Kakao

# Crypto symbols: Pair notation
symbols: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # BTC, ETH, BNB vs USDT
```

### Trading Hours
```yaml
# Stocks: Weekdays only (9:30 AM - 3:30 PM KST)
# Crypto: 24/7 (includes weekends)

# Example: Crypto backtest will show weekend trades
# 2024-01-06 (Saturday) - BUY BTCUSDT @ 45,000
# 2024-01-07 (Sunday) - SELL ETHUSDT @ 2,400
```

### Fractional Quantities
```python
# Stock trades: Integer quantities
Trade(symbol="005930", quantity=10)  # 10 shares

# Crypto trades: Decimal quantities
Trade(symbol="BTCUSDT", quantity=Decimal("0.0222"))  # 0.0222 BTC
```

### Trading Fees
```yaml
# Stock config
transaction_cost_percent: 0.3  # Korean stock trading fee

# Crypto config
crypto_config:
  trading_fee_percent: 0.1  # Binance spot fee (maker/taker avg)
```

## Common Use Cases

### 1. Compare Crypto vs Stock Performance

Run the same strategy on both markets:

```bash
# Run stock backtest (existing)
poetry run python examples/phase1_mvp_kospi100.py

# Run crypto backtest (new)
poetry run python examples/crypto_btc_eth_backtest.py

# Compare results
```

### 2. Test Different Crypto Pairs

Modify `symbols` in config:

```yaml
# Major coins
symbols: ["BTCUSDT", "ETHUSDT"]

# Altcoins
symbols: ["BNBUSDT", "ADAUSDT", "SOLUSDT"]

# Mix
symbols: ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
```

### 3. Adjust Strategy for Crypto Volatility

Crypto markets are more volatile - adjust parameters:

```yaml
# Recommended crypto settings
bollinger_std_dev: 2.5  # Wider bands (vs 2.0 for stocks)
stop_loss_percent: 8.0  # Larger stop loss (vs 5.0 for stocks)
max_position_percent: 25.0  # Smaller positions (vs 30.0 for stocks)

enhanced_strategy:
  volume_filter:
    multiplier: 2.0  # Higher threshold (vs 1.5 for stocks)
```

### 4. Backtest Specific Time Periods

Test bull vs bear markets:

```yaml
# Bull market (2023)
date_range:
  start: "2023-01-01"
  end: "2023-12-31"

# Bear market (2022)
date_range:
  start: "2022-01-01"
  end: "2022-12-31"
```

## Troubleshooting

### Error: "Invalid crypto symbol"

```python
# Problem:
symbols: ["BTC", "ETH"]  # Too short

# Solution:
symbols: ["BTCUSDT", "ETHUSDT"]  # Must include quote currency
```

### Error: "Binance API unavailable"

```python
# Check network connectivity
ping api.binance.com

# Check if data is cached
ls data/cache/crypto_*.parquet

# If cached, backtest will use cache even if API is down
```

### Error: "No data returned for symbol"

```python
# Possible causes:
# 1. Symbol doesn't exist on Binance
symbols: ["INVALID"]  # Fix: Use valid Binance pair

# 2. Date range before crypto existed
date_range:
  start: "2010-01-01"  # BTC existed, but not on Binance
  end: "2010-12-31"
# Fix: Use dates after Binance launch (2017+)

# 3. Symbol delisted
# Fix: Check Binance for currently traded pairs
```

### Warning: "crypto_config ignored for market_type='stock'"

```yaml
# Problem: Mixed configuration
market_type: stock
symbols: ["005930"]
crypto_config:  # This will be ignored
  trading_fee_percent: 0.1

# Solution: Remove crypto_config for stock backtests
```

## Performance Optimization

### 1. Use Data Caching

```python
# First run: Fetches from Binance API (~2-5 seconds per symbol)
provider.fetch_ohlcv("BTCUSDT", start, end)  # API call

# Second run: Loads from cache (~100ms)
provider.fetch_ohlcv("BTCUSDT", start, end)  # Cache hit

# Cache location: data/cache/crypto_BTCUSDT_2023-01-01_2024-01-01.parquet
```

### 2. Parallel Symbol Fetching (Future)

```python
# Currently: Sequential fetching
for symbol in symbols:
    df = provider.fetch_ohlcv(symbol, start, end)

# Future optimization: Parallel fetching
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(provider.fetch_ohlcv, s, start, end)
               for s in symbols]
    results = [f.result() for f in futures]
```

### 3. Reduce Date Range for Testing

```yaml
# Full backtest (slower)
date_range:
  start: "2020-01-01"
  end: "2024-12-31"  # 5 years

# Quick test (faster)
date_range:
  start: "2024-01-01"
  end: "2024-03-31"  # 3 months
```

## Validation Checklist

Before running a production-quality crypto backtest:

- [ ] Verify symbol format (e.g., "BTCUSDT" not "BTC")
- [ ] Check date range is within data availability (2017+ for Binance)
- [ ] Set appropriate crypto_config fees (default 0.1% is reasonable)
- [ ] Adjust strategy parameters for crypto volatility (wider bands, larger stops)
- [ ] Run quick test on small date range first
- [ ] Verify trades include weekend dates (24/7 validation)
- [ ] Check trade quantities are fractional (e.g., 0.0222 BTC)
- [ ] Compare results against stock backtest for sanity check

## Next Steps

After running your first crypto backtest:

1. **Analyze Results**: Review trade logs, confidence scores, squeeze events
2. **Optimize Parameters**: Tune bollinger_std_dev, stop_loss for crypto volatility
3. **Add More Symbols**: Test with different crypto pairs
4. **Compare Markets**: Run identical strategy on stocks vs crypto
5. **Backtest Multiple Periods**: Test bull/bear/sideways markets

## Additional Resources

### Documentation
- `/specs/003-crypto-backtest-support/spec.md` - Feature specification
- `/specs/003-crypto-backtest-support/data-model.md` - Entity models
- `/specs/003-crypto-backtest-support/contracts/` - API contracts

### Example Code
- `examples/crypto_btc_eth_backtest.py` - Working crypto backtest
- `config/examples/crypto_btc_eth.yaml` - Sample config

### API References
- [Binance API Docs](https://binance-docs.github.io/apidocs/spot/en/)
- [python-binance](https://python-binance.readthedocs.io/)

## Support

### Common Questions

**Q: Can I mix stocks and crypto in one backtest?**
A: No, each backtest must have a single market_type. Run separate backtests and compare results.

**Q: Do I need a Binance account?**
A: No, public OHLCV data doesn't require authentication.

**Q: What about other exchanges (Coinbase, Kraken)?**
A: Currently only Binance is supported. Future versions may add more providers via CCXT.

**Q: Can I use minute/hour candles instead of daily?**
A: Not in current implementation. Daily candles are used for long-term backtests.

**Q: How do I backtest with real trading fees from my exchange?**
A: Set `crypto_config.trading_fee_percent` to your actual fee rate (e.g., 0.075% for Binance VIP1).

---

**Happy Backtesting!** 🚀

For issues or questions, refer to the migration guide: `docs/crypto_migration_guide.md`

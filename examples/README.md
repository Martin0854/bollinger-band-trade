# Examples

This directory contains examples showing how to use the Bollinger Band backtester.

## Files

### 1. `simple_backtest.py`
**Recommended starting point!** A complete, self-contained example that demonstrates:
- Creating a configuration
- Generating mock OHLCV data with squeeze/breakout pattern
- Running a backtest
- Displaying results and trade details

**Run it:**
```bash
poetry run python examples/simple_backtest.py
```

### 2. `config_example.yaml`
Sample YAML configuration file with all available parameters documented.

**Customize it:**
```bash
cp examples/config_example.yaml my_backtest.yaml
# Edit my_backtest.yaml with your preferred settings
```

### 3. `backtest_from_yaml.py`
Demonstrates loading configuration from YAML file and running a backtest.

**Run it:**
```bash
poetry run python examples/backtest_from_yaml.py
```

### 4. `cli_example.sh`
Example shell commands for using the CLI interface.

**Note**: CLI currently requires manual data loading. Full CLI support requires implementing data fetching (User Story 3).

## Quick Start

1. **Try the simple example:**
   ```bash
   poetry run python examples/simple_backtest.py
   ```

2. **Customize your own:**
   - Copy `simple_backtest.py`
   - Modify the configuration parameters
   - Adjust the mock data generation to match your test scenario
   - Run it!

3. **Use YAML configs:**
   - Copy `config_example.yaml` to your own file
   - Edit parameters
   - Load it with `BacktestConfiguration.from_yaml("your_config.yaml")`

## Next Steps

- **Read the full guide**: See `USAGE.md` in the project root for comprehensive documentation
- **Understand the strategy**: Read `specs/001-readme-md/spec.md` for the complete specification
- **Run the tests**: `poetry run pytest tests/` to see how everything works
- **Add real data**: Replace mock data generation with actual Korean stock market data

## Common Scenarios

### Test Different Timeframes

```python
# Short-term (3 months)
date_range=(date(2024, 1, 1), date(2024, 3, 31))

# Medium-term (6 months)
date_range=(date(2024, 1, 1), date(2024, 6, 30))

# Long-term (1 year)
date_range=(date(2024, 1, 1), date(2024, 12, 31))
```

### Test Different Stock Codes

```python
# Large cap tech
stocks=["005930", "035720"]  # Samsung, Kakao

# Diversified portfolio
stocks=["005930", "000660", "051910", "005380", "068270"]

# Single stock focus
stocks=["005930"]  # Samsung only
```

### Adjust Risk Parameters

```python
# Conservative (lower risk)
stop_loss_percent=3.0
max_position_percent=20.0
max_positions=3

# Moderate (balanced)
stop_loss_percent=5.0
max_position_percent=30.0
max_positions=5

# Aggressive (higher risk)
stop_loss_percent=10.0
max_position_percent=40.0
max_positions=7
```

## Getting Help

- **Documentation**: See `USAGE.md`
- **Tests**: Run `poetry run pytest tests/integration/ -v` to see integration test examples
- **Spec**: Read `specs/001-readme-md/spec.md` for strategy details

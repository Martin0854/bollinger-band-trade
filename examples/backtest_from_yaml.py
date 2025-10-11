"""
Example: Run a backtest using YAML configuration.
"""

import pandas as pd
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

# Step 1: Load configuration from YAML
config = BacktestConfiguration.from_yaml("examples/config_example.yaml")

print(f"Loaded configuration:")
print(f"  - Starting capital: ₩{config.seed_money:,}")
print(f"  - Stocks: {', '.join(config.stocks)}")
print(f"  - Period: {config.date_range[0]} to {config.date_range[1]}")
print(f"  - Bollinger period: {config.bollinger_period}")
print(f"  - Stop loss: {config.stop_loss_percent}%")

# Step 2: Load data for each stock
# TODO: Replace with actual data fetching from KRW-API
engine = BacktestEngine(config=config)

for stock_code in config.stocks:
    # Create mock data (replace with real data fetching)
    dates = pd.date_range(str(config.date_range[0]), str(config.date_range[1]), freq='D')

    # Different price levels for different stocks
    base_price = {
        "005930": 60000,  # Samsung
        "035720": 50000,  # Kakao
        "000660": 100000  # SK Hynix
    }.get(stock_code, 50000)

    close_prices = [base_price + i * 100 for i in range(len(dates))]

    mock_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p * 1.01 for p in close_prices],
        'Low': [p * 0.99 for p in close_prices],
        'Close': close_prices,
        'Volume': [1_000_000] * len(dates)
    }, index=dates)

    engine.load_mock_data(stock_code, mock_data)
    print(f"  - Loaded {len(mock_data)} days of data for {stock_code}")

# Step 3: Run backtest
print("\nRunning backtest...\n")
report = engine.run()

# Step 4: Display results
print("=" * 60)
print("BACKTEST RESULTS")
print("=" * 60)
print(f"Total Return:        {report.total_return_pct:.2f}%")
print(f"Win Rate:            {report.win_rate_pct:.2f}%")
print(f"Total Trades:        {report.num_trades}")
print("=" * 60)

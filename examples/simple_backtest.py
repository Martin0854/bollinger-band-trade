"""
Simple example: Run a backtest with mock data.
This demonstrates the basic workflow without needing real market data.
"""

import pandas as pd
from datetime import date
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

# Step 1: Create configuration
config = BacktestConfiguration(
    seed_money=10_000_000,  # 10 million KRW starting capital
    stocks=["005930"],  # Samsung Electronics
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    bollinger_period=20,
    bollinger_std_dev=2.0,
    squeeze_threshold_percent=30.0,
    squeeze_lookback_days=10,
    stop_loss_percent=5.0,
    max_position_percent=30.0,
    max_positions=5
)

# Step 2: Create mock OHLCV data
# In real usage, you'd fetch this from KRW-API or other data sources
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')

# Create realistic price movement with squeeze and breakout pattern
close_prices = []
for i in range(len(dates)):
    if i < 50:
        # Normal volatility period
        price = 60000 + (i % 10) * 500
    elif i < 80:
        # Squeeze period (low volatility)
        price = 60000 + (i % 3) * 100
    else:
        # Breakout and expansion
        price = 60000 + (i - 80) * 200
    close_prices.append(price)

mock_data = pd.DataFrame({
    'Open': close_prices,
    'High': [p * 1.01 for p in close_prices],  # 1% higher than close
    'Low': [p * 0.99 for p in close_prices],   # 1% lower than close
    'Close': close_prices,
    'Volume': [1_000_000] * len(dates)
}, index=dates)

# Step 3: Initialize engine and load data
engine = BacktestEngine(config=config)
engine.load_mock_data("005930", mock_data)

# Step 4: Run the backtest
print("Running backtest...")
report = engine.run()

# Step 5: Display results
print("\n" + "=" * 60)
print("BACKTEST RESULTS")
print("=" * 60)
print(f"Initial Capital:     ₩{config.seed_money:,}")
print(f"Total Return:        {report.total_return_pct:.2f}%")
print(f"Win Rate:            {report.win_rate_pct:.2f}%")
print(f"Max Drawdown:        {report.max_drawdown_pct:.2f}%")
print(f"Sharpe Ratio:        {report.sharpe_ratio:.2f}")
print(f"\nTotal Trades:        {report.num_trades}")
print(f"  - Winning:         {report.num_winning_trades}")
print(f"  - Losing:          {report.num_losing_trades}")
if report.avg_win > 0:
    print(f"Average Win:         ₩{report.avg_win:,.0f}")
if report.avg_loss != 0:
    print(f"Average Loss:        ₩{report.avg_loss:,.0f}")
if report.win_loss_ratio:
    print(f"Win/Loss Ratio:      {report.win_loss_ratio:.2f}")
if report.profit_factor:
    print(f"Profit Factor:       {report.profit_factor:.2f}")
print("=" * 60)

# Step 6: View trade details
print(f"\n{len(engine.trades)} trades executed:")
for i, trade in enumerate(engine.trades, 1):
    action = "BUY " if trade.action.value == "buy" else "SELL"
    print(f"{i}. {action} {trade.quantity} shares @ ₩{trade.execution_price:,} "
          f"on {trade.execution_timestamp.strftime('%Y-%m-%d')}")
    if trade.realized_pnl:
        pnl_sign = "+" if trade.realized_pnl > 0 else ""
        print(f"   P&L: {pnl_sign}₩{trade.realized_pnl:,}")

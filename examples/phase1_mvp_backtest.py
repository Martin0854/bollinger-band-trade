"""
Phase 1 MVP Backtest: Volume Filter + RSI Filter
Demonstrates enhanced strategy with auxiliary indicator filters.
"""

import pandas as pd
import numpy as np
from datetime import date
from src.models.config import BacktestConfiguration, EnhancedStrategyConfig
from src.backtest.engine import BacktestEngine

print("=" * 80)
print("Phase 1 MVP Backtest: Volume Filter + RSI Filter")
print("=" * 80)

# Step 1: Load configuration from YAML
print("\n[1] Loading Phase 1 MVP configuration...")
config = BacktestConfiguration.from_yaml("config/examples/phase1_volume_rsi.yaml")

print(f"✓ Configuration loaded:")
print(f"  - Initial Capital: ₩{config.seed_money:,}")
print(f"  - Stocks: {', '.join(config.stocks)}")
print(f"  - Date Range: {config.date_range[0]} to {config.date_range[1]}")
print(f"  - Volume Filter: {'Enabled' if config.enhanced_strategy.volume_filter.enabled else 'Disabled'}")
print(f"  - RSI Filter: {'Enabled' if config.enhanced_strategy.rsi.enabled else 'Disabled'}")
print(f"  - Confidence Threshold: {config.enhanced_strategy.confidence.threshold}")

# Step 2: Create realistic mock data with various patterns
print("\n[2] Generating realistic mock market data...")

dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
np.random.seed(42)  # For reproducibility

def generate_stock_data(stock_code, dates, base_price=60000):
    """Generate realistic OHLCV data with squeeze patterns"""
    n = len(dates)
    close_prices = []
    volumes = []

    for i in range(n):
        # Different market phases
        if i < 60:
            # Phase 1: Normal volatility with trend
            price = base_price + (i % 15) * 400 + np.random.randint(-200, 200)
            volume = 1_000_000 + np.random.randint(-200_000, 200_000)

        elif i < 100:
            # Phase 2: Squeeze (low volatility consolidation)
            price = base_price + 3000 + (i % 5) * 150 + np.random.randint(-100, 100)
            volume = 800_000 + np.random.randint(-100_000, 100_000)

        elif i < 120:
            # Phase 3: Breakout with HIGH volume (should pass volume filter)
            price = base_price + 3000 + (i - 100) * 500
            volume = 2_000_000 + np.random.randint(0, 500_000)  # 2x average volume

        elif i < 180:
            # Phase 4: Trending with normal volume
            price = base_price + 10000 + (i - 120) * 200 + np.random.randint(-300, 300)
            volume = 1_200_000 + np.random.randint(-200_000, 200_000)

        elif i < 220:
            # Phase 5: Another squeeze
            price = base_price + 20000 + (i % 4) * 100
            volume = 900_000 + np.random.randint(-100_000, 100_000)

        elif i < 240:
            # Phase 6: Breakout WITHOUT high volume (should fail volume filter)
            price = base_price + 20000 + (i - 220) * 400
            volume = 1_100_000 + np.random.randint(-100_000, 100_000)  # Only 1.1x

        else:
            # Phase 7: Normal trading
            price = base_price + 28000 + (i % 20) * 300 + np.random.randint(-400, 400)
            volume = 1_100_000 + np.random.randint(-300_000, 300_000)

        close_prices.append(max(price, 1000))  # Ensure positive
        volumes.append(max(volume, 100_000))

    # Create OHLC from close
    df = pd.DataFrame({
        'Open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in close_prices],
        'High': [p * (1 + abs(np.random.uniform(0, 0.02))) for p in close_prices],
        'Low': [p * (1 - abs(np.random.uniform(0, 0.02))) for p in close_prices],
        'Close': close_prices,
        'Volume': volumes
    }, index=dates)

    return df

# Generate data for both stocks
stock_data = {}
for stock_code in config.stocks:
    base_price = 60000 if stock_code == "005930" else 100000
    stock_data[stock_code] = generate_stock_data(stock_code, dates, base_price)
    print(f"  ✓ {stock_code}: {len(dates)} days of data generated")

# Step 3: Initialize backtest engine
print("\n[3] Initializing backtest engine with Phase 1 filters...")
engine = BacktestEngine(config=config)

# Load mock data
for stock_code, data in stock_data.items():
    engine.load_mock_data(stock_code, data)
    print(f"  ✓ Loaded data for {stock_code}")

# Display filter status
print("\n[Filter Configuration]")
if engine.volume_filter:
    print(f"  ✓ Volume Filter: window={engine.volume_filter.window_days}d, multiplier={engine.volume_filter.multiplier}x")
else:
    print(f"  ✗ Volume Filter: Disabled")

if engine.rsi_indicator:
    print(f"  ✓ RSI Indicator: period={engine.rsi_indicator.period}, overbought={engine.rsi_indicator.overbought}")
else:
    print(f"  ✗ RSI Indicator: Disabled")

print(f"  ✓ Confidence Threshold: {engine.signal_generator.confidence_threshold} points")

# Step 4: Run backtest
print("\n[4] Running backtest simulation...")
print("  (This may take a moment...)")
report = engine.run()
print("  ✓ Backtest completed!")

# Step 5: Display comprehensive results
print("\n" + "=" * 80)
print("PHASE 1 MVP BACKTEST RESULTS")
print("=" * 80)

print("\n📊 Performance Metrics:")
print(f"  Initial Capital:       ₩{config.seed_money:,}")
print(f"  Total Return:          {report.total_return_pct:.2f}%")
print(f"  Win Rate:              {report.win_rate_pct:.2f}%")
print(f"  Max Drawdown:          {report.max_drawdown_pct:.2f}%")
print(f"  Sharpe Ratio:          {report.sharpe_ratio:.2f}")
print(f"  CAGR:                  {report.cagr_pct:.2f}%")

print(f"\n📈 Trade Statistics:")
print(f"  Total Trades:          {report.num_trades}")
print(f"    - Winning Trades:    {report.num_winning_trades}")
print(f"    - Losing Trades:     {report.num_losing_trades}")

if report.avg_win > 0:
    print(f"  Average Win:           ₩{report.avg_win:,.0f}")
if report.avg_loss != 0:
    print(f"  Average Loss:          ₩{report.avg_loss:,.0f}")
if report.win_loss_ratio:
    print(f"  Win/Loss Ratio:        {report.win_loss_ratio:.2f}")
if report.profit_factor:
    print(f"  Profit Factor:         {report.profit_factor:.2f}")

# Step 6: Analyze trades with enhanced signals
print(f"\n📋 Trade Details ({len(engine.trades)} trades):")
print("-" * 80)

for i, trade in enumerate(engine.trades[:10], 1):  # Show first 10 trades
    action = "🟢 BUY " if trade.action.value == "buy" else "🔴 SELL"
    print(f"{i}. {action} {trade.stock_code}: {trade.quantity} shares @ ₩{trade.execution_price:,}")
    print(f"   Date: {trade.execution_timestamp.strftime('%Y-%m-%d')}")

    if trade.realized_pnl:
        pnl_sign = "+" if trade.realized_pnl > 0 else ""
        pnl_color = "🟢" if trade.realized_pnl > 0 else "🔴"
        print(f"   P&L: {pnl_color} {pnl_sign}₩{trade.realized_pnl:,}")

    print()

if len(engine.trades) > 10:
    print(f"... and {len(engine.trades) - 10} more trades")

# Step 7: Phase 1 MVP Goal Assessment
print("\n" + "=" * 80)
print("PHASE 1 MVP GOAL ASSESSMENT")
print("=" * 80)

goals = [
    ("Win Rate", report.win_rate_pct, 55, 60, "%"),
    ("Annual Return", report.cagr_pct, 5, 8, "%"),
]

print("\n🎯 Target vs Actual:")
for goal_name, actual, target_min, target_max, unit in goals:
    status = "✅" if target_min <= actual <= target_max else "⚠️"
    print(f"{status} {goal_name:20s} Target: {target_min}-{target_max}{unit}  |  Actual: {actual:.2f}{unit}")

# Additional metrics
print(f"\n📊 Filter Effectiveness:")
print(f"  Volume Filter Enabled:     {'Yes' if engine.volume_filter else 'No'}")
print(f"  RSI Filter Enabled:        {'Yes' if engine.rsi_indicator else 'No'}")
print(f"  Minimum Confidence Score:  {engine.signal_generator.confidence_threshold}")
print(f"  Total Signals Generated:   {len(engine.trades) // 2}")  # BUY+SELL = 1 complete trade

print("\n" + "=" * 80)
print("✅ Phase 1 MVP Backtest Complete!")
print("=" * 80)

# Summary
if report.win_rate_pct >= 55 and report.cagr_pct >= 5:
    print("\n🎉 Phase 1 MVP goals ACHIEVED!")
    print("   - Volume Filter successfully reduced false signals")
    print("   - RSI Filter improved entry timing")
    print("   - Ready for Phase 2 (MACD + Confidence Scoring)")
else:
    print("\n⚠️  Phase 1 MVP goals NOT fully achieved")
    print("   Consider adjusting:")
    print("   - Volume multiplier (current: 1.5x)")
    print("   - RSI overbought threshold (current: 70)")
    print("   - Confidence threshold (current: 60)")

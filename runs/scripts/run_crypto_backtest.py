#!/usr/bin/env python3
"""
Cryptocurrency Backtest Runner
Runs backtests on crypto assets using real market data from Binance.

Usage:
    python runs/scripts/run_crypto_backtest.py [config_path]

Examples:
    # Run with default config (BTC+ETH 2023)
    python runs/scripts/run_crypto_backtest.py

    # Run with specific config
    python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_major_coins_2024.yaml

    # Run with custom config
    python runs/scripts/run_crypto_backtest.py my_custom_crypto_config.yaml
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.engine import BacktestEngine
from src.models.config import BacktestConfiguration


def print_banner(title: str) -> None:
    """Print formatted banner."""
    print("\n" + "=" * 80)
    print(f"{title:^80}")
    print("=" * 80)


def print_config_summary(config: BacktestConfiguration) -> None:
    """Print configuration summary."""
    print("\n📊 Configuration Summary")
    print("-" * 80)
    print(f"Market Type:         {config.market_type.upper()}")
    print(f"Assets:              {', '.join(config.symbols)}")
    print(f"Period:              {config.date_range[0]} to {config.date_range[1]}")
    print(f"Initial Capital:     ${config.seed_money:,.2f} {config.crypto_config.quote_currency}")
    print(f"Trading Fee:         {config.crypto_config.trading_fee_percent}%")
    print(f"Stop Loss:           {config.stop_loss_percent}%")
    print(f"Max Position:        {config.max_position_percent}%")
    print(f"Max Positions:       {config.max_positions}")

    # Enhanced strategy info
    if config.enhanced_strategy:
        print(f"\n📈 Enhanced Strategy")
        print(f"  Volume Filter:     {'✓ Enabled' if config.enhanced_strategy.volume_filter.enabled else '✗ Disabled'}")
        print(f"  RSI Filter:        {'✓ Enabled' if config.enhanced_strategy.rsi.enabled else '✗ Disabled'}")
        print(f"  MACD Filter:       {'✓ Enabled' if config.enhanced_strategy.macd.enabled else '✗ Disabled'}")
        print(f"  ATR Stop-Loss:     {'✓ Enabled' if config.enhanced_strategy.atr.enabled else '✗ Disabled'}")
        print(f"  Confidence Thresh: {config.enhanced_strategy.confidence.threshold}/100")

    print("-" * 80)


def print_backtest_results(report, config: BacktestConfiguration, trades: list) -> None:
    """Print detailed backtest results."""
    print_banner("Backtest Results")

    # Calculate final values
    initial_capital = config.seed_money
    total_return_pct = float(report.total_return_pct)
    final_value = initial_capital * (1 + total_return_pct / 100)
    profit_loss = final_value - initial_capital

    # Performance metrics
    print(f"\n💰 Performance")
    print(f"  Initial Capital:   ${initial_capital:>12,.2f}")
    print(f"  Final Value:       ${final_value:>12,.2f}")
    print(f"  Total Return:      {total_return_pct:>12,.2f}%")
    print(f"  Profit/Loss:       ${profit_loss:>12,.2f}")

    if report.cagr_pct:
        print(f"  CAGR:              {float(report.cagr_pct):>12,.2f}%")

    # Trading statistics
    print(f"\n📊 Trading Statistics")
    print(f"  Total Trades:      {report.num_trades:>12,}")
    print(f"  Winning Trades:    {report.num_winning_trades:>12,}")
    print(f"  Losing Trades:     {report.num_losing_trades:>12,}")

    if report.win_rate_pct:
        print(f"  Win Rate:          {float(report.win_rate_pct):>12,.2f}%")

    if report.avg_win:
        print(f"  Avg Win:           ${float(report.avg_win):>12,.2f}")
    if report.avg_loss:
        print(f"  Avg Loss:          ${abs(float(report.avg_loss)):>12,.2f}")
    if report.win_loss_ratio:
        print(f"  Win/Loss Ratio:    {float(report.win_loss_ratio):>12,.2f}")
    if report.profit_factor:
        print(f"  Profit Factor:     {float(report.profit_factor):>12,.2f}")

    # Risk metrics
    print(f"\n⚠️  Risk Metrics")
    if report.max_drawdown_pct:
        print(f"  Max Drawdown:      {float(report.max_drawdown_pct):>12,.2f}%")
    if report.sharpe_ratio:
        print(f"  Sharpe Ratio:      {report.sharpe_ratio:>12,.4f}")

    # Trade details
    if trades:
        print(f"\n📝 Trade History (Last 10)")
        print("-" * 80)
        print(f"{'Date':<12} {'Action':<6} {'Symbol':<10} {'Qty':<12} {'Price':<15} {'Reason':<25}")
        print("-" * 80)

        for trade in trades[-10:]:
            action = trade.action.value.upper()
            symbol = trade.symbol
            qty = float(trade.quantity)
            price = float(trade.execution_price)
            timestamp = trade.execution_timestamp.strftime('%Y-%m-%d')

            # Get reason
            if action == "BUY":
                reason = trade.entry_reason or "N/A"
            else:
                reason = trade.exit_reason or "N/A"

            # Truncate reason if too long
            if len(reason) > 24:
                reason = reason[:21] + "..."

            print(f"{timestamp:<12} {action:<6} {symbol:<10} {qty:<12.6f} ${price:<14,.2f} {reason:<25}")

        if len(trades) > 10:
            print(f"\n... and {len(trades) - 10} more trades")
    else:
        print(f"\n⚠️  No trades executed")

    print("-" * 80)


def run_crypto_backtest(config_path: str) -> None:
    """
    Run cryptocurrency backtest with given configuration.

    Args:
        config_path: Path to YAML configuration file
    """
    try:
        # Print header
        print_banner("Cryptocurrency Backtest Runner")
        print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Config: {config_path}")

        # Load configuration
        print(f"\n🔄 Loading configuration...")
        config = BacktestConfiguration.from_yaml(config_path)

        # Validate market type
        if config.market_type != 'crypto':
            print(f"\n❌ Error: Configuration must have market_type='crypto'")
            print(f"   Found: market_type='{config.market_type}'")
            sys.exit(1)

        # Print configuration
        print_config_summary(config)

        # Initialize engine
        print(f"\n🚀 Initializing backtest engine...")
        engine = BacktestEngine(config)

        # Run backtest
        print(f"\n⏳ Running backtest (fetching data from Binance)...")
        print(f"   This may take 1-2 minutes for real market data...")
        report = engine.run()

        # Print results
        print_backtest_results(report, config, engine.trades)

        # Additional crypto-specific notes
        print(f"\n💡 Notes:")
        print(f"  • 24/7 Market: Trades can occur on weekends")
        print(f"  • Fractional Quantities: Crypto allows decimal quantities")
        print(f"  • Trading Fees: {config.crypto_config.trading_fee_percent}% applied to all trades")
        print(f"  • Data Source: Binance historical klines (daily)")
        print(f"  • Database: Logs saved to {config.log_dir}/backtest.db")

        print(f"\n✅ Backtest completed successfully!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    except FileNotFoundError:
        print(f"\n❌ Error: Configuration file not found: {config_path}")
        print(f"   Please check the file path and try again.")
        sys.exit(1)

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    # Default configuration
    default_config = "runs/configs/examples/crypto_major_coins_2024.yaml"

    # Get config path from command line or use default
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = default_config
        print(f"\nℹ️  No config specified, using default: {default_config}")

    # Run backtest
    run_crypto_backtest(config_path)


if __name__ == "__main__":
    main()

"""
Command-line interface for the Bollinger Band backtester.
"""

import argparse
import sys
from pathlib import Path

from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from src.utils.logging import setup_logging


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Bollinger Band Squeeze Backtesting System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Backtest command
    backtest_parser = subparsers.add_parser(
        'backtest',
        help='Run a backtest simulation'
    )
    backtest_parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to configuration YAML file'
    )
    backtest_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level=log_level)

    # Execute command
    if args.command == 'backtest':
        run_backtest(args)


def run_backtest(args):
    """
    Run a backtest simulation.

    Args:
        args: Parsed command-line arguments
    """
    try:
        # Load configuration
        print(f"Loading configuration from: {args.config}")
        config = BacktestConfiguration.from_yaml(args.config)

        print(f"Configuration loaded:")
        print(f"  - Seed money: {config.seed_money:,} KRW")
        print(f"  - Stocks: {', '.join(config.stocks)}")
        print(f"  - Date range: {config.date_range[0]} to {config.date_range[1]}")
        print(f"  - Bollinger period: {config.bollinger_period}")
        print(f"  - Squeeze threshold: {config.squeeze_threshold_percent}%")

        # Initialize engine
        print("\nInitializing backtest engine...")
        engine = BacktestEngine(config=config)

        # Run backtest
        print("Running backtest...")
        report = engine.run()

        # Display results
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Total Return: {report.total_return_pct:.2f}%")
        print(f"Win Rate: {report.win_rate_pct:.2f}%")
        print(f"Max Drawdown: {report.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio: {report.sharpe_ratio:.2f}")
        print(f"Total Trades: {report.num_trades}")
        print(f"  - Winning: {report.num_winning_trades}")
        print(f"  - Losing: {report.num_losing_trades}")
        print("=" * 60)

        print("\n✓ Backtest completed successfully")

    except FileNotFoundError as e:
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    except Exception as e:
        print(f"Error running backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
Cryptocurrency Top 100 Backtest Analysis (2024)
Analyzes top 100 cryptocurrencies by 24h trading volume with Bollinger Band Squeeze strategy
"""

from src.backtest.engine import BacktestEngine
from src.models.config import BacktestConfiguration
from decimal import Decimal


def main():
    """Run backtest for top 100 cryptocurrencies in 2024."""
    config_path = 'runs/configs/examples/crypto_top100_2024.yaml'

    try:
        config = BacktestConfiguration.from_yaml(config_path)
        engine = BacktestEngine(config)

        print(f"\n{'='*80}")
        print(f"Cryptocurrency Top 100 Backtest: 2024")
        print(f"{'='*80}")
        print(f"Total Symbols: {len(config.symbols)}")
        print(f"Top 10 Symbols: {', '.join(config.symbols[:10])}")
        print(f"Period: {config.date_range[0]} to {config.date_range[1]}")
        print(f"Initial Capital: ${config.seed_money:,.2f} USDT")
        print(f"Max Positions: {config.max_positions}")
        print(f"Max Position %: {config.max_position_percent}%")
        print(f"\nRunning backtest... (this may take 5-10 minutes)")
        print(f"Progress will be displayed for each symbol...")

        report = engine.run()

        # Calculate metrics
        initial_capital = config.seed_money
        total_return_pct = float(report.total_return_pct)
        final_value = initial_capital * (1 + total_return_pct / 100)

        print(f"\n{'='*80}")
        print(f"Results for Top 100 Cryptocurrencies (2024)")
        print(f"{'='*80}")
        print(f"Initial Capital:      ${initial_capital:>12,.2f}")
        print(f"Final Value:          ${final_value:>12,.2f}")
        print(f"Total Return:         {total_return_pct:>12.2f}%")
        print(f"Number of Trades:     {report.num_trades:>12}")

        if report.win_rate_pct:
            print(f"Win Rate:             {float(report.win_rate_pct):>12.2f}%")
        if report.max_drawdown_pct:
            print(f"Max Drawdown:         {float(report.max_drawdown_pct):>12.2f}%")
        if report.sharpe_ratio:
            print(f"Sharpe Ratio:         {float(report.sharpe_ratio):>12.4f}")

        print(f"{'='*80}")

        # Show sample trades
        if engine.trades:
            print(f"\nSample Trades ({min(10, len(engine.trades))} of {len(engine.trades)}):")
            print("-" * 80)
            for trade in engine.trades[:10]:
                action = trade.action.value.upper()
                symbol = trade.symbol
                qty = float(trade.quantity)
                price = float(trade.execution_price)
                timestamp = trade.execution_timestamp.strftime('%Y-%m-%d')

                print(f"{timestamp} | {action:4s} | {symbol:12s} | "
                      f"Qty: {qty:>12.8f} | Price: ${price:>10,.2f}")
            print("-" * 80)

        # Symbol participation analysis
        if engine.trades:
            print(f"\n{'='*80}")
            print("Symbol Participation Analysis")
            print(f"{'='*80}")

            from collections import Counter
            symbol_trades = Counter([trade.symbol for trade in engine.trades])

            print(f"Total Unique Symbols Traded: {len(symbol_trades)}/{len(config.symbols)}")
            print(f"\nTop 10 Most Traded Symbols:")
            print(f"{'Symbol':<15} {'Trades':<10}")
            print("-" * 25)

            for symbol, count in symbol_trades.most_common(10):
                print(f"{symbol:<15} {count:<10}")

            print(f"{'='*80}")

        # Compare with 5-coin backtest
        print(f"\n{'='*80}")
        print("Comparison: Top 100 vs Original 5 Coins")
        print(f"{'='*80}")
        print(f"{'Metric':<30} {'Original 5':<15} {'Top 100':<15}")
        print("-" * 60)
        print(f"{'Symbols':<30} {'5':<15} {len(config.symbols):<15}")
        print(f"{'2024 Return':<30} {'+0.26%':<15} {f'{total_return_pct:.2f}%':<15}")
        print(f"{'Total Trades':<30} {'2':<15} {report.num_trades:<15}")
        print(f"{'='*80}")

    except FileNotFoundError:
        print(f"\n⚠️  Config file not found: {config_path}")
        return None
    except Exception as e:
        print(f"\n❌ Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

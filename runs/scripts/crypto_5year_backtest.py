"""
Cryptocurrency 5-Year Backtest Analysis (2020-2024)
Analyzes BTC, ETH, BNB, SOL, ADA performance with Bollinger Band Squeeze strategy
"""

from src.backtest.engine import BacktestEngine
from src.models.config import BacktestConfiguration
from decimal import Decimal


def run_yearly_backtest(year: int):
    """Run backtest for a specific year."""
    config_path = f'runs/configs/examples/crypto_5year_{year}.yaml'

    try:
        config = BacktestConfiguration.from_yaml(config_path)
        engine = BacktestEngine(config)

        print(f"\n{'='*70}")
        print(f"Cryptocurrency Backtest: {year}")
        print(f"{'='*70}")
        print(f"Symbols: {', '.join(config.symbols)}")
        print(f"Period: {config.date_range[0]} to {config.date_range[1]}")
        print(f"Initial Capital: ${config.seed_money:,.2f} USDT")
        print(f"\nRunning backtest for {year}... (this may take 1-2 minutes)")

        report = engine.run()

        # Calculate metrics
        initial_capital = config.seed_money
        total_return_pct = float(report.total_return_pct)
        final_value = initial_capital * (1 + total_return_pct / 100)

        print(f"\n{'='*70}")
        print(f"Results for {year}")
        print(f"{'='*70}")
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

        print(f"{'='*70}")

        # Show sample trades
        if engine.trades:
            print(f"\nSample Trades ({min(5, len(engine.trades))} of {len(engine.trades)}):")
            print("-" * 70)
            for trade in engine.trades[:5]:
                action = trade.action.value.upper()
                symbol = trade.symbol
                qty = float(trade.quantity)
                price = float(trade.execution_price)
                timestamp = trade.execution_timestamp.strftime('%Y-%m-%d')

                print(f"{timestamp} | {action:4s} | {symbol:8s} | "
                      f"Qty: {qty:>10.6f} | Price: ${price:>10,.2f}")
            print("-" * 70)

        return {
            'year': year,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return_pct': total_return_pct,
            'num_trades': report.num_trades,
            'win_rate_pct': float(report.win_rate_pct) if report.win_rate_pct else 0,
            'max_drawdown_pct': float(report.max_drawdown_pct) if report.max_drawdown_pct else 0,
            'sharpe_ratio': float(report.sharpe_ratio) if report.sharpe_ratio else 0,
        }

    except FileNotFoundError:
        print(f"\n⚠️  Config file not found: {config_path}")
        return None
    except Exception as e:
        print(f"\n❌ Error running backtest for {year}: {e}")
        return None


def main():
    """Run 5-year cryptocurrency backtest analysis."""
    print("\n" + "="*70)
    print("CRYPTOCURRENCY 5-YEAR BACKTEST ANALYSIS (2020-2024)")
    print("="*70)
    print("\nStrategy: Bollinger Band Squeeze")
    print("Assets: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT")
    print("Capital: $10,000 USDT per year")
    print("\n" + "="*70)

    years = [2020, 2021, 2022, 2023, 2024]
    results = []

    for year in years:
        result = run_yearly_backtest(year)
        if result:
            results.append(result)

    # Summary table
    if results:
        print("\n\n" + "="*70)
        print("5-YEAR SUMMARY")
        print("="*70)
        print(f"{'Year':<8} {'Return':<12} {'Trades':<10} {'Win Rate':<12} {'Sharpe':<10} {'MDD':<10}")
        print("-" * 70)

        total_return = 0
        total_trades = 0

        for r in results:
            print(f"{r['year']:<8} {r['total_return_pct']:>10.2f}% "
                  f"{r['num_trades']:>8} {r['win_rate_pct']:>10.2f}% "
                  f"{r['sharpe_ratio']:>9.2f} {r['max_drawdown_pct']:>9.2f}%")
            total_return += r['total_return_pct']
            total_trades += r['num_trades']

        print("-" * 70)
        avg_return = total_return / len(results)
        print(f"{'Average':<8} {avg_return:>10.2f}% {total_trades:>8} "
              f"{'':>10} {'':>9} {'':>9}")
        print("="*70)

        # Calculate compound return
        compound_value = 10000
        for r in results:
            compound_value *= (1 + r['total_return_pct'] / 100)

        compound_return = ((compound_value - 10000) / 10000) * 100
        cagr = (pow(compound_value / 10000, 1/len(results)) - 1) * 100

        print(f"\n5-Year Compound Performance:")
        print(f"  Initial Investment:   $10,000")
        print(f"  Final Value:          ${compound_value:,.2f}")
        print(f"  Total Return:         {compound_return:.2f}%")
        print(f"  CAGR:                 {cagr:.2f}%")
        print(f"  Total Trades:         {total_trades}")
        print("="*70)

        print("\n💡 Note: Results are cached. Delete data/cache/crypto_*.parquet to refetch data.")


if __name__ == "__main__":
    main()

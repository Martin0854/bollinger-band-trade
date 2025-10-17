"""
Cryptocurrency Backtest Example: BTC & ETH
Demonstrates crypto market backtesting with Bollinger Band Squeeze strategy.
"""

from src.backtest.engine import BacktestEngine
from src.models.config import BacktestConfiguration


def main():
    """Run cryptocurrency backtest for BTC and ETH."""

    # Load configuration
    config = BacktestConfiguration.from_yaml('config/examples/crypto_btc_eth.yaml')

    print("=" * 60)
    print("Cryptocurrency Backtest: BTC & ETH")
    print("=" * 60)
    print(f"Market Type: {config.market_type}")
    print(f"Symbols: {', '.join(config.symbols)}")
    print(f"Period: {config.date_range[0]} to {config.date_range[1]}")
    print(f"Initial Capital: ${config.seed_money:,.2f} USDT")
    print(f"Trading Fee: {config.crypto_config.trading_fee_percent}%")
    print(f"Min Order Value: ${config.crypto_config.min_order_value_usdt} {config.crypto_config.quote_currency}")
    print("=" * 60)
    print()

    # Initialize backtest engine
    # The BacktestEngine will automatically select BinanceCryptoProvider
    # for market_type='crypto' via DataProviderFactory
    engine = BacktestEngine(config)

    print(f"\n📊 Data Provider: BinanceCryptoProvider (auto-selected for crypto)")
    print(f"🌍 Timezone: UTC (24/7 trading)")
    print(f"📡 Data Source: Binance historical klines API\n")

    # Run backtest
    print("Running backtest... (this may take a minute to fetch crypto data)")
    report = engine.run()

    # Display results
    print("\n" + "=" * 60)
    print("Backtest Results")
    print("=" * 60)

    # Calculate final portfolio value
    initial_capital = config.seed_money
    total_return_pct = float(report.total_return_pct)
    final_value = initial_capital * (1 + total_return_pct / 100)

    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Total Return: {total_return_pct:.2f}%")
    print(f"Number of Trades: {report.num_trades}")

    if report.win_rate_pct:
        print(f"Win Rate: {float(report.win_rate_pct):.2f}%")
    if report.max_drawdown_pct:
        print(f"Max Drawdown: {float(report.max_drawdown_pct):.2f}%")
    if report.sharpe_ratio:
        print(f"Sharpe Ratio: {float(report.sharpe_ratio):.4f}")

    print("=" * 60)
    print()

    # Display trades
    if engine.trades:
        print("Recent Trades:")
        print("-" * 60)
        for trade in engine.trades[:10]:  # Show first 10 trades
            action = trade.action.value.upper()
            symbol = trade.symbol
            qty = float(trade.quantity)
            price = float(trade.execution_price)
            timestamp = trade.execution_timestamp.strftime('%Y-%m-%d')

            print(f"{timestamp} | {action:4s} | {symbol:8s} | "
                  f"Qty: {qty:8.6f} | Price: ${price:10,.2f}")

        if len(engine.trades) > 10:
            print(f"... and {len(engine.trades) - 10} more trades")
        print("-" * 60)
    else:
        print("No trades executed.")

    print("\nNote: 24/7 crypto market - trades can occur on weekends!")
    print("Database logs saved to: data/logs/backtest.db")


if __name__ == "__main__":
    main()

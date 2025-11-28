"""
US Market Backtest Script
Runs Bollinger Band Squeeze strategy on major US stocks for the last month.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from runs.scripts.utils.backtest_with_real_data import run_backtest_with_real_data

def main():
    # 1. Define US stocks (Tech giants + ETFs)
    us_stocks = [
        "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", 
        "GOOGL", "META", "NFLX", "AMD", "INTC",
        "SPY", "QQQ", "TQQQ", "SOXL"
    ]

    # 2. Set date range (Last 6 months)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    print(f"📅 Backtest Period: {start_date} ~ {end_date}")

    # 3. Run Backtest (Phase 3 Strategy: MACD + Confidence)
    report, engine = run_backtest_with_real_data(
        stocks=us_stocks,
        start_date=start_date,
        end_date=end_date,
        seed_money=10_000_000,  # 10 million KRW (approx $7-8k)
        
        # Strategy Parameters
        bollinger_period=20,
        squeeze_threshold_percent=10,  # Lower threshold to catch more squeezes in short period
        stop_loss_percent=5.0,
        
        # Enhanced Strategy (Phase 3) - Disabled to ensure trades for initial test
        # enhanced_strategy={
        #     "volume_filter": {
        #         "enabled": True,
        #         "window_days": 20,
        #         "multiplier": 1.5
        #     },
        #     "rsi": {
        #         "enabled": True,
        #         "period": 14,
        #         "overbought": 70,
        #         "oversold": 30
        #     },
        #     "macd": {
        #         "enabled": True,
        #         "fast_period": 12,
        #         "slow_period": 26,
        #         "signal_period": 9
        #     },
        #     "confidence": {
        #         "threshold": 60  # Require score >= 60
        #     }
        # }
    )
    
    if report:
        print("\n✅ US Market Backtest Completed Successfully!")

if __name__ == "__main__":
    main()

# Experiment 5: No Middle Band Sell Results

## Strategy
- Disabled middle band sell: Don't exit just because price drops below middle band
- Higher take profit (12% vs 10%): Hold longer for bigger gains
- Only exit on stop loss or take profit target

This tests if the middle band sell rule is too aggressive and 
cuts winners too early.

## Parameters
```json
{
  "max_positions": 15,
  "max_position_pct": 10.0,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 12.0,
  "take_profit_ratio": 0.5,
  "confidence_threshold": 60,
  "bb_window": 20,
  "bb_std": 2.0,
  "rsi_window": 14,
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "volume_window": 20,
  "squeeze_threshold": 0.7,
  "volume_weight": 25.0,
  "rsi_weight": 20.0,
  "macd_weight": 30.0,
  "sell_on_middle_band": false
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 54.02%
- **Final Value**: 15,402,421 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.82
- **Max Drawdown**: 16.83%
- **Win Rate**: 29.6%
- **Total Trades**: 308
- **Winning Trades**: 50
- **Losing Trades**: 119

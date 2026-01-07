# Experiment 6: Volume Focus Results

## Strategy
- Higher volume weight (40 vs 25): Emphasize volume breakouts
- Lower RSI weight (15 vs 20): Less focus on RSI
- Lower MACD weight (20 vs 30): Less focus on MACD
- Shorter volume window (15 vs 20): More responsive volume average
- Lower confidence threshold (55 vs 60): Capture more signals

Volume is often the most reliable indicator of breakout strength.
This tests if emphasizing volume improves results.

## Parameters
```json
{
  "max_positions": 15,
  "max_position_pct": 10.0,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "take_profit_ratio": 0.5,
  "confidence_threshold": 55,
  "bb_window": 20,
  "bb_std": 2.0,
  "rsi_window": 14,
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "volume_window": 15,
  "squeeze_threshold": 0.7,
  "volume_weight": 40.0,
  "rsi_weight": 15.0,
  "macd_weight": 20.0,
  "sell_on_middle_band": true
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 46.49%
- **Final Value**: 14,649,384 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.82
- **Max Drawdown**: 22.45%
- **Win Rate**: 46.2%
- **Total Trades**: 1450
- **Winning Trades**: 371
- **Losing Trades**: 428

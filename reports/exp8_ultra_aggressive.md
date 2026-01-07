# Experiment 8: Ultra Aggressive BB Results

## Strategy
Push BB parameters even further:
- bb_window=10 (very short)
- bb_std=1.2 (very tight)
- squeeze_threshold=0.5 (very sensitive)
- confidence_threshold=45 (capture more signals)

## Parameters
```json
{
  "max_positions": 20,
  "max_position_pct": 10.0,
  "stop_loss_pct": 4.0,
  "take_profit_pct": 8.0,
  "take_profit_ratio": 0.5,
  "confidence_threshold": 45,
  "bb_window": 10,
  "bb_std": 1.2,
  "rsi_window": 14,
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "volume_window": 20,
  "squeeze_threshold": 0.5,
  "volume_weight": 25.0,
  "rsi_weight": 20.0,
  "macd_weight": 30.0,
  "sell_on_middle_band": true
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 41.47%
- **Final Value**: 14,147,068 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.72
- **Max Drawdown**: 20.87%
- **Win Rate**: 43.7%
- **Total Trades**: 3447

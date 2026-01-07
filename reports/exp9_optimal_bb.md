# Experiment 9: Optimal BB Results

## Strategy
Fine-tune between Exp4 (best return) and Exp8 (ultra aggressive):
- bb_window=12 (between 10 and 15)
- bb_std=1.3 (between 1.2 and 1.5)
- squeeze_threshold=0.55
- No middle band sell (from exp5)

## Parameters
```json
{
  "max_positions": 15,
  "max_position_pct": 10.0,
  "stop_loss_pct": 4.5,
  "take_profit_pct": 9.0,
  "take_profit_ratio": 0.5,
  "confidence_threshold": 50,
  "bb_window": 12,
  "bb_std": 1.3,
  "rsi_window": 14,
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "volume_window": 20,
  "squeeze_threshold": 0.55,
  "volume_weight": 25.0,
  "rsi_weight": 20.0,
  "macd_weight": 30.0,
  "sell_on_middle_band": false
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 112.11%
- **Final Value**: 21,211,381 KRW (from 10,000,000)
- **Sharpe Ratio**: 1.38
- **Max Drawdown**: 15.94%
- **Win Rate**: 31.3%
- **Total Trades**: 270

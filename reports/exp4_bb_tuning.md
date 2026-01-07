# Experiment 4: Bollinger Band Tuning Results

## Strategy
- Shorter BB window (15 vs 20): More responsive to recent price action
- Tighter bands (1.5 std vs 2.0): Earlier breakout signals
- More sensitive squeeze (0.6 vs 0.7): Detect squeeze earlier
- Slightly lower confidence (55 vs 60): Capture more opportunities

## Parameters
```json
{
  "max_positions": 15,
  "max_position_pct": 10.0,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "take_profit_ratio": 0.5,
  "confidence_threshold": 55,
  "bb_window": 15,
  "bb_std": 1.5,
  "rsi_window": 14,
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "volume_window": 20,
  "squeeze_threshold": 0.6,
  "volume_weight": 25.0,
  "rsi_weight": 20.0,
  "macd_weight": 30.0,
  "sell_on_middle_band": true
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 66.99%
- **Final Value**: 16,698,825 KRW (from 10,000,000)
- **Sharpe Ratio**: 1.07
- **Max Drawdown**: 20.32%
- **Win Rate**: 45.1%
- **Total Trades**: 1977
- **Winning Trades**: 487
- **Losing Trades**: 585

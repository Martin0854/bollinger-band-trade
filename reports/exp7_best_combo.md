# Experiment 7: Best Combo Results

## Strategy
Combines the two best performing strategies:
- From Exp4 (BB Tuning): bb_window=15, bb_std=1.5, squeeze_threshold=0.6
- From Exp5 (No Middle Sell): sell_on_middle_band=False, take_profit=12%

## Parameters
```json
{
  "max_positions": 15,
  "max_position_pct": 10.0,
  "stop_loss_pct": 5.0,
  "take_profit_pct": 12.0,
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
  "sell_on_middle_band": false
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 47.55%
- **Final Value**: 14,755,350 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.76
- **Max Drawdown**: 21.52%
- **Win Rate**: 26.5%
- **Total Trades**: 298
- **Winning Trades**: 43
- **Losing Trades**: 119

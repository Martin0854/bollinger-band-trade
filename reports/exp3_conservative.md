# Experiment 3: Conservative Strategy Results

## Strategy
- Higher confidence threshold (70 vs 60): Only high-quality signals
- Wider stop loss (7% vs 5%): Allow more room for volatility
- Higher take profit (15% vs 10%): Hold for bigger gains
- Fewer positions (10 vs 15): More concentrated
- Larger position size (15% vs 10%): More conviction

## Parameters
```json
{
  "max_positions": 10,
  "max_position_pct": 15.0,
  "stop_loss_pct": 7.0,
  "take_profit_pct": 15.0,
  "take_profit_ratio": 0.3,
  "confidence_threshold": 70,
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
  "sell_on_middle_band": true
}
```

## Performance Metrics (2023-2025)
- **Total Return**: 7.25%
- **Final Value**: 10,725,491 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.22
- **Max Drawdown**: 32.04%
- **Win Rate**: 41.6%
- **Total Trades**: 877
- **Winning Trades**: 193
- **Losing Trades**: 269

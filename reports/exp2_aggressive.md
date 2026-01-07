# Experiment 2: Aggressive Strategy Results

## Strategy
- Lower confidence threshold (50 vs 60): More trading signals
- Tighter stop loss (3% vs 5%): Quick exits on losing trades
- Lower take profit (8% vs 10%): Take profits earlier
- More positions (20 vs 15): Greater diversification
- Smaller position size (8% vs 10%): Less concentrated

## Parameters
```json
{
  "max_positions": 20,
  "max_position_pct": 8.0,
  "stop_loss_pct": 3.0,
  "take_profit_pct": 8.0,
  "take_profit_ratio": 0.7,
  "confidence_threshold": 50,
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
- **Total Return**: 34.32%
- **Final Value**: 13,431,741 KRW (from 10,000,000)
- **Sharpe Ratio**: 0.75
- **Max Drawdown**: 19.98%
- **Win Rate**: 43.7%
- **Total Trades**: 2151
- **Winning Trades**: 523
- **Losing Trades**: 671

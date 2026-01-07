# Robust Parameter Search Results

Generated: 2026-01-07

## Robustness Ranking

| Rank | Strategy | 2023-25 | 2020-23 | Gap | Avg | Robust Score |
|------|----------|---------|---------|-----|-----|--------------|
| 1 | robust_9_standard_bb | 79.33% | 89.09% | 9.77% | 84.21% | 79.33 |
| 2 | robust_2_50ma_filter | 102.41% | 47.82% | 54.59% | 75.12% | 47.82 |
| 3 | original_optimal | 112.11% | 46.43% | 65.69% | 79.27% | 46.43 |
| 4 | robust_3_conservative | 52.38% | 45.45% | 6.93% | 48.91% | 45.45 |
| 5 | robust_6_both_ma | 77.87% | 40.42% | 37.45% | 59.14% | 40.42 |
| 6 | robust_5_balanced | 69.52% | 37.89% | 31.63% | 53.70% | 37.89 |
| 7 | robust_4_trailing | 36.97% | 33.73% | 3.24% | 35.35% | 33.73 |
| 8 | robust_1_trend_filter | 73.43% | 30.52% | 42.91% | 51.98% | 30.52 |
| 9 | robust_8_high_conf | 67.03% | 26.89% | 40.14% | 46.96% | 26.89 |
| 10 | robust_7_wider_stop | 99.92% | 26.65% | 73.26% | 63.28% | 26.65 |
| 11 | baseline | 25.15% | 54.53% | 29.38% | 39.84% | 25.15 |

## Best Strategy: robust_9_standard_bb

```python
params = {'max_positions': 15, 'max_position_pct': 10.0, 'stop_loss_pct': 5.0, 'take_profit_pct': 10.0, 'take_profit_ratio': 0.5, 'confidence_threshold': 55, 'bb_window': 20, 'bb_std': 2.0, 'squeeze_threshold': 0.7, 'sell_on_middle_band': False, 'use_trailing_stop': False, 'trailing_stop_pct': 7.0, 'use_atr_stop': False, 'atr_multiplier': 2.0, 'require_trend_up': True, 'require_50ma_up': False, 'name': 'robust_9_standard_bb'}
```


## Key Findings

1. **Overfitting Alert**: original_optimal shows high 2023-25 return but poor robustness

2. **Trend Filter helps**: Strategies with require_trend_up=True show more consistent results

3. **BB parameters**: Moderate BB settings (16-18 window, 1.6-1.8 std) more robust than aggressive (12, 1.3)

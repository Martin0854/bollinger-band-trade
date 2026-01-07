# Parameter Validation Report

Generated: 2026-01-07

## Summary Table

| Experiment | Period | Return | Sharpe | MDD | Win Rate | Trades |
|------------|--------|--------|--------|-----|----------|--------|
| optimal_2023_2025 | 2020-2023 | 46.43% | 0.56 | 41.05% | 29.9% | 262 |
| optimal_2023_2025 | 2023-2025 | 112.11% | 1.38 | 15.94% | 31.3% | 270 |
| baseline | 2023-2025 | 25.15% | 0.52 | 25.37% | 45.6% | 1436 |
| baseline | 2020-2023 | 54.53% | 0.87 | 26.62% | 46.9% | 1774 |
| optimal_with_trend_filter | 2023-2025 | 68.78% | 0.96 | 19.10% | 30.5% | 277 |
| optimal_with_trend_filter | 2020-2023 | 61.46% | 0.67 | 36.62% | 33.0% | 185 |
| optimal_with_trailing_stop | 2023-2025 | 43.34% | 0.80 | 24.47% | 49.4% | 1809 |
| optimal_with_trailing_stop | 2020-2023 | 36.04% | 0.59 | 30.71% | 50.3% | 2140 |
| optimal_with_atr_stop | 2023-2025 | 140.54% | 1.50 | 16.17% | 31.0% | 262 |
| optimal_with_atr_stop | 2020-2023 | 18.97% | 0.34 | 24.83% | 31.7% | 225 |
| conservative_optimal | 2023-2025 | 84.74% | 1.12 | 19.90% | 32.0% | 280 |
| conservative_optimal | 2020-2023 | 45.67% | 0.59 | 42.30% | 34.3% | 192 |
| aggressive_optimal | 2023-2025 | 111.59% | 1.35 | 20.05% | 26.5% | 340 |
| aggressive_optimal | 2020-2023 | 3.91% | 0.14 | 22.14% | 24.6% | 239 |
| bb_tuning_1 | 2023-2025 | 130.44% | 1.44 | 19.42% | 34.6% | 237 |
| bb_tuning_1 | 2020-2023 | 2.84% | 0.14 | 41.15% | 26.4% | 321 |
| bb_tuning_2 | 2023-2025 | 97.37% | 1.30 | 14.58% | 33.1% | 248 |
| bb_tuning_2 | 2020-2023 | 26.07% | 0.38 | 45.54% | 28.6% | 334 |

## Validation Analysis

### Is 2023-2025 Optimal Valid for 2020-2023?

- **2023-2025 Return**: 112.11%
- **2020-2023 Return**: 46.43%
- **Verdict**: DEGRADED - Parameters work worse in earlier period (-65.69%)

**vs Baseline (2020-2023)**:
- Baseline: 54.53%
- Optimal: 46.43%
- Improvement: -8.10%

## Experiment Details

### optimal_2023_2025

**2020-2023**:
- Return: 46.43%
- Sharpe: 0.56
- MDD: 41.05%
- Win Rate: 29.9%
- Trades: 262

**2023-2025**:
- Return: 112.11%
- Sharpe: 1.38
- MDD: 15.94%
- Win Rate: 31.3%
- Trades: 270

### baseline

**2023-2025**:
- Return: 25.15%
- Sharpe: 0.52
- MDD: 25.37%
- Win Rate: 45.6%
- Trades: 1436

**2020-2023**:
- Return: 54.53%
- Sharpe: 0.87
- MDD: 26.62%
- Win Rate: 46.9%
- Trades: 1774

### optimal_with_trend_filter

**2023-2025**:
- Return: 68.78%
- Sharpe: 0.96
- MDD: 19.10%
- Win Rate: 30.5%
- Trades: 277

**2020-2023**:
- Return: 61.46%
- Sharpe: 0.67
- MDD: 36.62%
- Win Rate: 33.0%
- Trades: 185

### optimal_with_trailing_stop

**2023-2025**:
- Return: 43.34%
- Sharpe: 0.80
- MDD: 24.47%
- Win Rate: 49.4%
- Trades: 1809

**2020-2023**:
- Return: 36.04%
- Sharpe: 0.59
- MDD: 30.71%
- Win Rate: 50.3%
- Trades: 2140

### optimal_with_atr_stop

**2023-2025**:
- Return: 140.54%
- Sharpe: 1.50
- MDD: 16.17%
- Win Rate: 31.0%
- Trades: 262

**2020-2023**:
- Return: 18.97%
- Sharpe: 0.34
- MDD: 24.83%
- Win Rate: 31.7%
- Trades: 225

### conservative_optimal

**2023-2025**:
- Return: 84.74%
- Sharpe: 1.12
- MDD: 19.90%
- Win Rate: 32.0%
- Trades: 280

**2020-2023**:
- Return: 45.67%
- Sharpe: 0.59
- MDD: 42.30%
- Win Rate: 34.3%
- Trades: 192

### aggressive_optimal

**2023-2025**:
- Return: 111.59%
- Sharpe: 1.35
- MDD: 20.05%
- Win Rate: 26.5%
- Trades: 340

**2020-2023**:
- Return: 3.91%
- Sharpe: 0.14
- MDD: 22.14%
- Win Rate: 24.6%
- Trades: 239

### bb_tuning_1

**2023-2025**:
- Return: 130.44%
- Sharpe: 1.44
- MDD: 19.42%
- Win Rate: 34.6%
- Trades: 237

**2020-2023**:
- Return: 2.84%
- Sharpe: 0.14
- MDD: 41.15%
- Win Rate: 26.4%
- Trades: 321

### bb_tuning_2

**2023-2025**:
- Return: 97.37%
- Sharpe: 1.30
- MDD: 14.58%
- Win Rate: 33.1%
- Trades: 248

**2020-2023**:
- Return: 26.07%
- Sharpe: 0.38
- MDD: 45.54%
- Win Rate: 28.6%
- Trades: 334

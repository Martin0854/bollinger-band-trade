# Cryptocurrency Backtest Quick Start Guide

이 가이드는 실제 Binance 데이터를 사용하여 암호화폐 백테스트를 실행하는 방법을 설명합니다.

## 📋 목차

- [빠른 시작](#빠른-시작)
- [설정 파일 설명](#설정-파일-설명)
- [사용 예제](#사용-예제)
- [결과 해석](#결과-해석)
- [문제 해결](#문제-해결)

## 🚀 빠른 시작

### 1. 기본 백테스트 실행

가장 간단한 방법으로 BTC+ETH 2023년 백테스트 실행:

```bash
python runs/scripts/run_crypto_backtest.py
```

### 2. 특정 설정으로 실행

```bash
# 공격적 전략 (더 많은 거래)
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_btc_eth_2023_aggressive.yaml

# 다중 코인 백테스트 (5개 메이저 코인)
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_major_coins_2024.yaml
```

### 3. 커스텀 설정 파일 사용

```bash
python runs/scripts/run_crypto_backtest.py path/to/your/config.yaml
```

## 📊 설정 파일 설명

### 사용 가능한 설정 파일

#### 1. `crypto_btc_eth_2023.yaml` (기본 설정)
- **자산**: BTC, ETH
- **기간**: 2023년 전체
- **자본금**: $10,000 USDT
- **전략**: 보수적 (Volume + RSI 필터)
- **특징**:
  - 높은 confidence threshold (50/100)
  - 엄격한 volume filter (1.8x)
  - 표준 RSI 범위 (30-70)

#### 2. `crypto_btc_eth_2023_aggressive.yaml` (공격적 전략)
- **자산**: BTC, ETH
- **기간**: 2023년 전체
- **자본금**: $10,000 USDT
- **전략**: 공격적 (더 많은 거래 신호)
- **특징**:
  - 낮은 confidence threshold (40/100)
  - 완화된 volume filter (1.3x)
  - 넓은 RSI 범위 (20-80)
  - 더 짧은 squeeze lookback (7일)

#### 3. `crypto_major_coins_2024.yaml` (다중 코인)
- **자산**: BTC, ETH, BNB, SOL, ADA (시가총액 상위 5개)
- **기간**: 2024년 Q1-Q3
- **자본금**: $50,000 USDT
- **전략**: 보수적 (품질 위주)
- **특징**:
  - 높은 confidence threshold (60/100)
  - 매우 높은 volume filter (2.0x)
  - 보수적 RSI 범위 (25-75)
  - 5개 포지션 동시 허용

## 🎯 주요 설정 파라미터

### 포트폴리오 설정
```yaml
seed_money: 10000          # 초기 자본 (USDT)
market_type: crypto        # 반드시 'crypto'
symbols:                   # 거래할 코인 목록
  - BTCUSDT
  - ETHUSDT
```

### 리스크 관리
```yaml
stop_loss_percent: 7.0        # 손절매 (%)
max_position_percent: 40.0    # 최대 포지션 크기 (%)
max_positions: 3              # 최대 동시 포지션 수
```

### 암호화폐 특화 설정
```yaml
crypto_config:
  trading_fee_percent: 0.1      # 거래 수수료 (Binance 기본값)
  min_order_value_usdt: 10.0    # 최소 주문 금액
  quote_currency: USDT          # 기준 화폐
```

### 전략 설정
```yaml
enhanced_strategy:
  # Volume Filter (거래량 필터)
  volume_filter:
    enabled: true
    multiplier: 1.8             # 평균 거래량의 1.8배 이상

  # RSI Filter (과매수/과매도 필터)
  rsi:
    enabled: true
    overbought: 70              # 과매수 기준
    oversold: 30                # 과매도 기준

  # Confidence Scoring (신호 품질 점수)
  confidence:
    threshold: 50               # 최소 신뢰도 점수
```

## 📈 사용 예제

### 예제 1: 2023년 BTC+ETH 백테스트

```bash
python runs/scripts/run_crypto_backtest.py
```

**예상 결과:**
```
💰 Performance
  Initial Capital:   $   10,000.00
  Final Value:       $    9,540.65
  Total Return:             -4.59%

📊 Trading Statistics
  Total Trades:                 8
  Win Rate:                 25.00%
```

### 예제 2: 커스텀 설정으로 실행

1. 설정 파일 생성 (`my_crypto_config.yaml`):
```yaml
seed_money: 20000
market_type: crypto
symbols:
  - BTCUSDT
date_range:
  start: "2024-01-01"
  end: "2024-06-30"
# ... (나머지 설정)
```

2. 실행:
```bash
python runs/scripts/run_crypto_backtest.py my_crypto_config.yaml
```

### 예제 3: 다양한 파라미터 테스트

```bash
# 1. 보수적 전략 (기본값)
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_btc_eth_2023.yaml

# 2. 공격적 전략 (더 많은 거래)
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_btc_eth_2023_aggressive.yaml

# 3. 다중 코인 분산 투자
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_major_coins_2024.yaml
```

## 📊 결과 해석

### 성과 지표

- **Total Return**: 전체 수익률 (%)
- **CAGR**: 연환산 복리 수익률
- **Win Rate**: 승률 (수익 거래 / 전체 거래)
- **Profit Factor**: 총수익 / 총손실 비율
- **Sharpe Ratio**: 위험 대비 수익률 (높을수록 좋음)
- **Max Drawdown**: 최대 손실 폭 (%)

### 거래 통계

```
📊 Trading Statistics
  Total Trades:                 8      # 총 거래 횟수
  Winning Trades:               1      # 수익 거래
  Losing Trades:                3      # 손실 거래
  Win Rate:                 25.00%     # 승률
  Avg Win:           $      115.32     # 평균 수익
  Avg Loss:          $      186.90     # 평균 손실
  Win/Loss Ratio:            0.62      # 승패 비율
  Profit Factor:             0.21      # 수익 팩터
```

### 거래 내역

```
📝 Trade History (Last 10)
Date         Action Symbol     Qty          Price           Reason
2023-03-17   BUY    ETHUSDT    2.000000     $1,789.27       squeeze_breakout_buy
2023-04-21   SELL   ETHUSDT    2.000000     $1,848.78       middle_band_cross
```

- **Date**: 거래 실행일
- **Action**: BUY (매수) / SELL (매도)
- **Symbol**: 거래 코인
- **Qty**: 거래량 (소수점 가능)
- **Price**: 체결 가격
- **Reason**: 거래 이유
  - `squeeze_breakout_buy`: 스퀴즈 브레이크아웃 매수
  - `middle_band_cross`: 중간 밴드 교차 매도
  - `stop_loss`: 손절매

## 🔧 파라미터 튜닝 가이드

### 더 많은 거래를 원할 때

```yaml
squeeze_threshold_percent: 20    # 낮출수록 더 많은 신호
squeeze_lookback_days: 7         # 짧을수록 더 많은 신호

enhanced_strategy:
  volume_filter:
    multiplier: 1.3              # 낮출수록 더 많은 신호 통과
  confidence:
    threshold: 40                # 낮을수록 더 많은 거래
```

### 더 안정적인 거래를 원할 때

```yaml
squeeze_threshold_percent: 30    # 높일수록 더 강한 신호만
squeeze_lookback_days: 14        # 길수록 신호 검증 강화

enhanced_strategy:
  volume_filter:
    multiplier: 2.0              # 높일수록 강한 거래량 요구
  rsi:
    overbought: 75               # 보수적 범위
    oversold: 25
  confidence:
    threshold: 60                # 높을수록 품질 높은 거래만
```

### 리스크 조절

```yaml
# 보수적 (낮은 리스크)
stop_loss_percent: 5.0           # 빠른 손절
max_position_percent: 25.0       # 작은 포지션

# 공격적 (높은 리스크)
stop_loss_percent: 15.0          # 여유 있는 손절
max_position_percent: 50.0       # 큰 포지션
```

## 🐛 문제 해결

### 1. "No trades executed"

**원인**: 신호 발생 조건이 너무 엄격함

**해결책**:
- `squeeze_threshold_percent` 낮추기 (30 → 20)
- `confidence.threshold` 낮추기 (50 → 40)
- `volume_filter.multiplier` 낮추기 (1.8 → 1.3)

### 2. Binance API 에러

**원인**: 네트워크 또는 API 제한

**해결책**:
```bash
# 재시도 또는 데이터 캐시 확인
ls data/cache/

# 캐시 삭제 후 재실행
rm -rf data/cache/*
python runs/scripts/run_crypto_backtest.py
```

### 3. "Invalid crypto symbol"

**원인**: 심볼 형식 오류

**해결책**:
```yaml
# ❌ 잘못된 형식
symbols:
  - btcusdt        # 소문자
  - BTC-USDT       # 하이픈 포함

# ✅ 올바른 형식
symbols:
  - BTCUSDT        # 대문자, 하이픈 없음
  - ETHUSDT
```

### 4. 메모리 부족

**원인**: 너무 많은 코인 또는 긴 백테스트 기간

**해결책**:
```yaml
# 코인 수 줄이기
symbols:
  - BTCUSDT        # 1-2개로 시작

# 기간 단축
date_range:
  start: "2024-01-01"
  end: "2024-06-30"  # 6개월로 시작
```

## 📚 추가 리소스

### 지원되는 암호화폐

Binance에서 지원하는 모든 USDT 페어 거래 가능:
- **메이저**: BTCUSDT, ETHUSDT, BNBUSDT
- **알트코인**: ADAUSDT, SOLUSDT, DOTUSDT, MATICUSDT, etc.

전체 목록: https://www.binance.com/en/markets/spot-USDT

### 데이터 기간

- **최소 기간**: 30일 (Bollinger Bands 계산용)
- **권장 기간**: 6개월 이상
- **사용 가능**: 2017년 ~ 현재

### 성능 최적화

```bash
# 1. 캐시 활용 (재실행 시 빠름)
data_cache_dir: data/cache

# 2. 병렬 처리 (향후 구현 예정)
# 3. 기간 분할 백테스트
```

## 💡 팁

1. **처음 시작할 때**
   - 기본 설정으로 시작 (`crypto_btc_eth_2023.yaml`)
   - 소액 자본으로 테스트 (seed_money: 1000)
   - 짧은 기간으로 실험 (3-6개월)

2. **전략 개선**
   - 여러 설정으로 A/B 테스트
   - 승률과 Sharpe Ratio에 주목
   - Max Drawdown 관리

3. **코인 선택**
   - 시가총액 상위 코인 우선
   - 유동성 높은 코인 (거래량 체크)
   - 2-3개 코인으로 분산 투자

4. **백테스트 검증**
   - 여러 기간에서 테스트 (2022, 2023, 2024)
   - Bull/Bear 마켓 모두 확인
   - Out-of-sample 테스트

## 📞 지원

문제가 발생하면:
1. 이 문서의 [문제 해결](#문제-해결) 섹션 참조
2. GitHub Issues에 문의
3. 로그 파일 확인: `data/logs/backtest.db`

---

**Last Updated**: 2025-10-17
**Version**: 1.0.0

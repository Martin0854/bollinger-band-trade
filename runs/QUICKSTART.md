# Quick Start Guide

백테스트 실행을 위한 빠른 시작 가이드입니다.

## 📋 사전 준비

```bash
# 프로젝트 루트 디렉토리에서 실행
poetry install
```

## 🚀 Phase별 백테스트 실행

### Phase 1: Volume + RSI 필터
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py \
  --config runs/configs/phases/phase1_volume_rsi.yaml
```

### Phase 2: MACD 추가
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py \
  --config runs/configs/phases/phase2_with_macd.yaml
```

### Phase 3: Confidence 점수
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py \
  --config runs/configs/phases/phase3_confidence.yaml
```

### Phase 4: ATR 동적 손절
```bash
poetry run python runs/scripts/phases/run_phase4_backtest.py
```

## ✅ 전체 검증

모든 Phase를 한 번에 검증:
```bash
poetry run python runs/scripts/phases/validate_all_phases.py
```

## 📊 결과 분석

백테스트 결과 분석:
```bash
poetry run python runs/scripts/analysis/analyze_trades.py \
  runs/results/phase4/backtest_result_YYYYMMDD_HHMMSS.xlsx
```

## 📂 결과 파일 위치

백테스트 결과는 자동으로 다음 위치에 저장됩니다:
- Phase 1: `runs/results/phase1/`
- Phase 2: `runs/results/phase2/`
- Phase 3: `runs/results/phase3/`
- Phase 4: `runs/results/phase4/`

## 🔧 커스텀 백테스트

### 단일 종목 테스트
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py \
  --config runs/configs/examples/single_stock.yaml
```

### 다중 종목 테스트
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py \
  --config runs/configs/examples/multi_stock.yaml
```

### KOSPI Top 100 테스트
```bash
poetry run python runs/scripts/utils/run_kospi100_real_data.py
```

## 📝 설정 파일 수정

Phase별 설정 파일을 직접 수정하여 파라미터 조정:
- `runs/configs/phases/phase1_volume_rsi.yaml` - Volume/RSI 임계값
- `runs/configs/phases/phase2_with_macd.yaml` - MACD 파라미터
- `runs/configs/phases/phase3_confidence.yaml` - 신뢰도 점수 가중치
- `runs/configs/phases/phase4_dynamic_stop.yaml` - ATR 승수 조정

## ⚠️ 문제 해결

### 거래가 발생하지 않는 경우
1. `confidence.threshold` 값을 낮춰보세요 (60 → 50)
2. `squeeze_threshold_percent` 값을 낮춰보세요 (40 → 30)
3. 백테스트 기간을 늘려보세요

### 데이터 다운로드 실패
- 인터넷 연결 확인
- Yahoo Finance API 상태 확인
- 종목 코드가 올바른지 확인 (6자리 코드.KS 형식)

## 💡 팁

- 먼저 Phase 1부터 순서대로 실행하여 각 Phase의 효과를 확인하세요
- `validate_all_phases.py`로 전체 Phase의 성능을 한눈에 비교하세요
- 결과 Excel 파일에서 신뢰도 점수와 필터 통과 여부를 확인하세요

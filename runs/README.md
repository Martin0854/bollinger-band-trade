# Runs 디렉토리

백테스트 실행과 관련된 모든 파일들을 포함하는 통합 디렉토리입니다.

## 디렉토리 구조

```
runs/
├── scripts/          # 실행 스크립트
│   ├── phases/       # Phase별 백테스트 스크립트
│   ├── analysis/     # 분석 도구
│   └── utils/        # 유틸리티 스크립트
├── configs/          # 설정 파일
│   ├── phases/       # Phase 1-4 설정 파일
│   └── examples/     # 예제 설정 파일
└── results/          # 실행 결과
    ├── phase1/       # Phase 1 백테스트 결과
    ├── phase2/       # Phase 2 백테스트 결과
    ├── phase3/       # Phase 3 백테스트 결과
    └── phase4/       # Phase 4 백테스트 결과
```

## 빠른 시작

### 🪙 암호화폐 백테스트 (NEW!) ⭐

**기본 실행 (BTC+ETH 2023)**
```bash
python runs/scripts/run_crypto_backtest.py
```

**공격적 전략 (더 많은 거래)**
```bash
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_btc_eth_2023_aggressive.yaml
```

**다중 코인 백테스트 (BTC, ETH, BNB, SOL, ADA)**
```bash
python runs/scripts/run_crypto_backtest.py runs/configs/examples/crypto_major_coins_2024.yaml
```

📚 **상세 가이드**: [CRYPTO_QUICKSTART.md](CRYPTO_QUICKSTART.md)

---

### Phase별 백테스트 실행 (한국 주식)

**Phase 1: Volume + RSI (Mock 데이터)**
```bash
poetry run python runs/scripts/phases/run_phase1_backtest.py
```

**Phase 3: MACD + Confidence (KOSPI 100, 2020-2024) ⭐ 권장**
```bash
poetry run python runs/scripts/phases/run_phase3_backtest.py
```

**Phase 4: Full Strategy with ATR (KOSPI 100, 2020-2024)**
```bash
poetry run python runs/scripts/phases/run_phase4_backtest.py
```

### 전체 Phase 검증
```bash
poetry run python runs/scripts/phases/validate_all_phases.py
```

### 유틸리티 도구

**실제 데이터로 백테스트**
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py
```

**거래 분석**
```bash
poetry run python runs/scripts/analysis/analyze_trades.py <result_file>
```

## 설정 파일

### Phase별 설정
- `configs/phases/phase1_volume_rsi.yaml` - Phase 1: Volume + RSI 필터
- `configs/phases/phase2_with_macd.yaml` - Phase 2: MACD 추가
- `configs/phases/phase3_confidence.yaml` - Phase 3: 신뢰도 점수 (권장) ⭐
- `configs/phases/phase4_dynamic_stop.yaml` - Phase 4: ATR 동적 손절

### 암호화폐 예제 설정 (NEW!)
- `configs/examples/crypto_btc_eth_2023.yaml` - BTC+ETH 2023년 (기본값)
- `configs/examples/crypto_btc_eth_2023_aggressive.yaml` - 공격적 전략 (더 많은 거래)
- `configs/examples/crypto_major_coins_2024.yaml` - 5개 메이저 코인 2024년

### 주식 예제 설정
- `configs/examples/single_stock.yaml` - 단일 종목 백테스트
- `configs/examples/multi_stock.yaml` - 다중 종목 백테스트

## Phase별 백테스트 스크립트

### Phase 1 - Volume + RSI (MVP)
**스크립트**: `runs/scripts/phases/run_phase1_backtest.py`
**설정 파일**: `runs/configs/phases/phase1_volume_rsi.yaml`
**데이터**: Mock 데이터 (1년, 2종목)
**목적**: 기본 필터 검증, 학습용

### Phase 3 - MACD + Confidence Scoring (권장) ⭐
**스크립트**: `runs/scripts/phases/run_phase3_backtest.py`
**설정 파일**: `runs/configs/phases/phase3_confidence.yaml`
**데이터**: KOSPI 100 실제 데이터 (2020-2024, 5년)
**실제 성과**: 평균 수익률 +2.82%, 승률 31.1%
**목적**: 실전 투자 전략 검증

### Phase 4 - Full Strategy with ATR
**스크립트**: `runs/scripts/phases/run_phase4_backtest.py`
**설정 파일**: `runs/configs/phases/phase4_dynamic_stop.yaml`
**데이터**: KOSPI 100 실제 데이터 (2020-2024, 5년)
**실제 성과**: 평균 수익률 +2.89%, 승률 31.1% (Phase 3 대비 +0.07%p)
**목적**: ATR 효과 연구 (효과 제한적 확인)

## 결과 파일

백테스트 결과는 자동으로 `results/phase{N}/` 디렉토리에 저장됩니다.

결과 파일 형식: `backtest_[type]_[date_range]_[timestamp].xlsx`

예시:
- `backtest_real_data_2023-01-01_2023-12-31_20251017_135649.xlsx`

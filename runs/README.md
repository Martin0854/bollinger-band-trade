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

### Phase 4 백테스트 실행
```bash
poetry run python runs/scripts/phases/run_phase4_backtest.py
```

### 전체 Phase 검증
```bash
poetry run python runs/scripts/phases/validate_all_phases.py
```

### 실제 데이터로 백테스트
```bash
poetry run python runs/scripts/utils/backtest_with_real_data.py
```

### 거래 분석
```bash
poetry run python runs/scripts/analysis/analyze_trades.py <result_file>
```

## 설정 파일

### Phase별 설정
- `configs/phases/phase1_volume_rsi.yaml` - Volume + RSI 필터
- `configs/phases/phase2_with_macd.yaml` - MACD 추가
- `configs/phases/phase3_confidence.yaml` - 신뢰도 점수
- `configs/phases/phase4_dynamic_stop.yaml` - ATR 동적 손절

### 예제 설정
- `configs/examples/single_stock.yaml` - 단일 종목 백테스트
- `configs/examples/multi_stock.yaml` - 다중 종목 백테스트

## 결과 파일

백테스트 결과는 자동으로 `results/phase{N}/` 디렉토리에 저장됩니다.

결과 파일 형식: `backtest_[type]_[date_range]_[timestamp].xlsx`

예시:
- `backtest_real_data_2023-01-01_2023-12-31_20251017_135649.xlsx`

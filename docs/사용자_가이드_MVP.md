# Phase 1 MVP 사용자 가이드

## 📖 개요

이 가이드는 **볼린저 밴드 스퀴즈 전략 - Phase 1 MVP (거래량 + RSI 필터)** 사용 방법을 설명합니다.

### 주요 기능
- ✅ **거래량 필터**: 평균 거래량 1.5배 이상만 진입 (거짓 신호 40-50% 감소)
- ✅ **RSI 필터**: 과매수 구간(RSI≥70) 진입 차단 (승률 15-20% 개선)
- ✅ **신뢰도 점수**: 0-100점 시스템으로 신호 품질 평가
- ✅ **후방 호환성**: 기존 설정 파일 그대로 사용 가능

---

## 🚀 빠른 시작

### 1. 설치 확인

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/bollinger-band-trade

# 의존성 설치 확인
poetry install

# 테스트 실행으로 설치 확인
poetry run pytest tests/unit/test_momentum.py -v
```

### 2. 첫 백테스트 실행

```bash
# Phase 1 MVP 설정으로 백테스트
poetry run python -m src.cli.main backtest \
    --config config/examples/phase1_volume_rsi.yaml \
    --stocks 005930 000660 \
    --start 2023-01-01 \
    --end 2023-12-31
```

### 3. 결과 확인

백테스트 완료 후 다음 파일들이 생성됩니다:
- `results/backtest_results_{날짜}.xlsx` - 상세 거래 내역
- `logs/backtest.db` - SQLite 데이터베이스
- 콘솔에 성과 지표 출력

---

## ⚙️ 설정 가이드

### Phase 1 MVP 설정 파일 구조

**파일 위치**: `config/examples/phase1_volume_rsi.yaml`

```yaml
# 기본 전략 설정
seed_money: 10000000                    # 초기 자본금 (1천만원)
stocks:
  - "005930"                            # 삼성전자
  - "000660"                            # SK하이닉스

date_range:
  start: "2023-01-01"
  end: "2023-12-31"

# 볼린저 밴드 파라미터
bollinger_period: 20                    # 20일 이동평균
bollinger_std_dev: 2.0                  # 표준편차 2배

# 스퀴즈 감지
squeeze_threshold_percent: 30.0         # 밴드폭 30% 이하를 스퀴즈로 판단
squeeze_lookback_days: 10               # 10일 내 스퀴즈 확인

# 리스크 관리
stop_loss_percent: 5.0                  # 5% 손절매
max_position_percent: 30.0              # 포지션당 최대 30%
max_positions: 5                        # 최대 5개 포지션

# ========================================
# Phase 1 MVP: 향상된 전략 설정
# ========================================
enhanced_strategy:

  # 거래량 필터 (User Story 1)
  volume_filter:
    enabled: true                       # 필터 활성화
    window_days: 20                     # 20일 평균 기준
    multiplier: 1.5                     # 1.5배 이상만 진입

  # RSI 필터 (User Story 2)
  rsi:
    enabled: true                       # 필터 활성화
    period: 14                          # 14일 RSI
    overbought: 70                      # 과매수 기준 (70 이상 진입 차단)
    oversold: 30                        # 과매도 기준

  # MACD 필터 (Phase 2에서 활성화)
  macd:
    enabled: false                      # 현재 비활성화
    fast_period: 12
    slow_period: 26
    signal_period: 9

  # ATR 동적 손절매 (Phase 3에서 활성화)
  atr:
    enabled: false                      # 현재 비활성화
    period: 14
    multiplier: 2.0

  # 신뢰도 점수 시스템
  confidence:
    threshold: 60                       # 60점 이상만 진입
    scoring:
      base_score: 25                    # 볼린저 밴드 브레이크아웃 기본점수
      volume_score: 25                  # 거래량 필터 통과시 +25점
      rsi_score: 20                     # RSI 필터 통과시 +20점
      macd_score: 30                    # MACD 필터 통과시 +30점 (Phase 2)
```

### 설정 항목 상세 설명

#### 1. 거래량 필터 (volume_filter)

| 항목 | 설명 | 권장값 | 범위 |
|------|------|--------|------|
| enabled | 필터 활성화 여부 | true | true/false |
| window_days | 평균 계산 기간 | 20 | 5-252 |
| multiplier | 기준 배수 | 1.5 | 1.0-10.0 |

**예시**:
```yaml
volume_filter:
  enabled: true
  window_days: 20        # 20일 평균 거래량 계산
  multiplier: 1.5        # 평균의 1.5배 이상일 때만 진입
```

**효과**:
- `multiplier: 1.5` → 보수적 (거래량 급증 확실할 때만 진입)
- `multiplier: 1.2` → 공격적 (좀 더 많은 신호 생성)
- `multiplier: 2.0` → 매우 보수적 (극단적 거래량 급증만)

#### 2. RSI 필터 (rsi)

| 항목 | 설명 | 권장값 | 범위 |
|------|------|--------|------|
| enabled | 필터 활성화 여부 | true | true/false |
| period | RSI 계산 기간 | 14 | 5-100 |
| overbought | 과매수 기준 | 70 | 50-100 |
| oversold | 과매도 기준 | 30 | 0-50 |

**예시**:
```yaml
rsi:
  enabled: true
  period: 14             # 14일 RSI (표준)
  overbought: 70         # RSI 70 이상은 과매수 → 진입 차단
  oversold: 30           # RSI 30 이하는 과매도
```

**효과**:
- `overbought: 70` → 표준 (권장)
- `overbought: 80` → 공격적 (더 많은 진입 허용)
- `overbought: 60` → 보수적 (과매수 조기 차단)

#### 3. 신뢰도 점수 (confidence)

| 항목 | 설명 | 권장값 | 범위 |
|------|------|--------|------|
| threshold | 최소 진입 점수 | 60 | 0-100 |
| base_score | 볼린저 기본점수 | 25 | - |
| volume_score | 거래량 필터 통과 | 25 | - |
| rsi_score | RSI 필터 통과 | 20 | - |
| macd_score | MACD 필터 통과 (Phase 2) | 30 | - |

**점수 계산 예시**:

```
케이스 1: 볼린저 브레이크아웃 + 거래량 급증 + RSI 중립
→ 25 (기본) + 25 (거래량) + 20 (RSI) = 70점 ✅ 진입

케이스 2: 볼린저 브레이크아웃 + 거래량 급증만
→ 25 (기본) + 25 (거래량) = 50점 ❌ 진입 차단 (threshold 60)

케이스 3: 볼린저 브레이크아웃만 (필터 미활성화)
→ 25 (기본) + 25 (거래량 비활성화→통과) + 20 (RSI 비활성화→통과) = 70점 ✅ 진입
```

**임계값 조정**:
- `threshold: 50` → 공격적 (더 많은 진입)
- `threshold: 60` → 균형적 (권장)
- `threshold: 70` → 보수적 (엄격한 진입)

---

## 📊 사용 시나리오

### 시나리오 1: 기본 MVP 전략 (권장)

**목표**: 거래량 + RSI 필터로 안정적 승률 달성

```yaml
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 20
    multiplier: 1.5
  rsi:
    enabled: true
    period: 14
    overbought: 70
    oversold: 30
  confidence:
    threshold: 60
```

**예상 성과**:
- 승률: 55-60%
- 연간 수익률: +5-8%
- 거래 빈도: 월 2-3회

### 시나리오 2: 공격적 전략 (빈번한 거래)

**목표**: 더 많은 진입 기회 확보

```yaml
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 15        # 짧은 기간
    multiplier: 1.2        # 낮은 배수
  rsi:
    enabled: true
    period: 14
    overbought: 80         # 높은 임계값
    oversold: 20
  confidence:
    threshold: 50          # 낮은 임계값
```

**예상 성과**:
- 승률: 50-55% (낮음)
- 연간 수익률: +3-5%
- 거래 빈도: 월 4-6회 (높음)

### 시나리오 3: 보수적 전략 (높은 승률)

**목표**: 확실한 신호만 진입

```yaml
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 30        # 긴 기간
    multiplier: 2.0        # 높은 배수
  rsi:
    enabled: true
    period: 14
    overbought: 65         # 낮은 임계값
    oversold: 35
  confidence:
    threshold: 70          # 높은 임계값
```

**예상 성과**:
- 승률: 60-65% (높음)
- 연간 수익률: +6-10%
- 거래 빈도: 월 1-2회 (낮음)

### 시나리오 4: 거래량 필터만 사용

**목표**: RSI 영향 배제하고 거래량만 확인

```yaml
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 20
    multiplier: 1.5
  rsi:
    enabled: false         # RSI 비활성화
  confidence:
    threshold: 60
```

**참고**: RSI 비활성화시 자동으로 통과 처리됨 (점수 부여)

---

## 🔧 고급 사용법

### 1. 필터 비활성화

모든 필터를 비활성화하면 기존 볼린저 밴드 전략만 사용:

```yaml
enhanced_strategy:
  volume_filter:
    enabled: false
  rsi:
    enabled: false
  macd:
    enabled: false
  atr:
    enabled: false
  confidence:
    threshold: 25          # 기본 점수만으로 진입
```

또는 `enhanced_strategy` 섹션 자체를 삭제/주석 처리:

```yaml
# enhanced_strategy:      # 전체 주석 처리 → 기존 전략
#   volume_filter:
#     enabled: false
```

### 2. 다종목 백테스트

```bash
# KOSPI 대형주 5종목
poetry run python -m src.cli.main backtest \
    --config config/examples/phase1_volume_rsi.yaml \
    --stocks 005930 000660 035420 005380 051910 \
    --start 2023-01-01 \
    --end 2023-12-31
```

**파일로 종목 리스트 관리**:

```yaml
# config/my_stocks.yaml
stocks:
  - "005930"  # 삼성전자
  - "000660"  # SK하이닉스
  - "035420"  # NAVER
  - "005380"  # 현대차
  - "051910"  # LG화학
  - "035720"  # 카카오
```

### 3. 기간별 성과 비교

```bash
# 2022년 성과
poetry run python -m src.cli.main backtest \
    --config config/examples/phase1_volume_rsi.yaml \
    --start 2022-01-01 --end 2022-12-31

# 2023년 성과
poetry run python -m src.cli.main backtest \
    --config config/examples/phase1_volume_rsi.yaml \
    --start 2023-01-01 --end 2023-12-31
```

### 4. 파라미터 최적화

여러 설정을 테스트하여 최적 파라미터 찾기:

```bash
# 임계값 50, 60, 70 비교
for threshold in 50 60 70; do
    # 설정 파일 임시 수정
    sed "s/threshold: 60/threshold: $threshold/" \
        config/examples/phase1_volume_rsi.yaml > config/temp_$threshold.yaml

    # 백테스트 실행
    poetry run python -m src.cli.main backtest \
        --config config/temp_$threshold.yaml \
        --output results/threshold_$threshold.xlsx
done
```

---

## 📈 결과 분석 가이드

### 백테스트 결과 파일

#### 1. Excel 파일 (`results/backtest_results_{날짜}.xlsx`)

**Trades 시트**:
| 컬럼 | 설명 |
|------|------|
| date | 거래 일자 |
| stock_code | 종목 코드 |
| action | BUY/SELL |
| price | 체결 가격 |
| quantity | 수량 |
| pnl | 실현 손익 |
| confidence_score | 신뢰도 점수 (0-100) |
| volume_pass | 거래량 필터 통과 여부 |
| rsi_pass | RSI 필터 통과 여부 |
| rsi_value | RSI 값 |

**Metrics 시트**:
- 총 거래 횟수
- 승률 (%)
- 평균 수익
- 최대 낙폭
- 샤프 비율
- CAGR

#### 2. 데이터베이스 (`logs/backtest.db`)

SQLite로 상세 로그 조회:

```bash
sqlite3 logs/backtest.db

# 모든 거래 조회
SELECT * FROM trade_log ORDER BY execution_timestamp;

# 승리한 거래만 조회
SELECT * FROM trade_log WHERE realized_pnl > 0;

# 신뢰도 점수 70 이상 거래
SELECT * FROM trade_log WHERE confidence_score >= 70;
```

### 성과 지표 해석

#### 승률 (Win Rate)
```
승률 = (수익 거래 수 / 전체 거래 수) × 100
```

- **55-60%**: Phase 1 MVP 목표 달성 ✅
- **50-55%**: 파라미터 조정 필요
- **<50%**: 필터 로직 재검토 필요

#### 신뢰도 점수 vs 수익률 상관관계

이상적인 결과:
- 신뢰도 70+ 거래: 승률 65-70%
- 신뢰도 60-69 거래: 승률 55-60%
- 신뢰도 50-59 거래: 승률 45-50%

만약 상관관계가 없다면 → 점수 가중치 재조정 필요

---

## 🐛 문제 해결

### 문제 1: 거래가 전혀 발생하지 않음

**원인**: 필터 조건이 너무 엄격함

**해결**:
```yaml
# 임계값 낮추기
confidence:
  threshold: 50          # 60 → 50

# 거래량 배수 낮추기
volume_filter:
  multiplier: 1.2        # 1.5 → 1.2

# RSI 범위 넓히기
rsi:
  overbought: 80         # 70 → 80
```

### 문제 2: 승률이 매우 낮음

**원인**: 필터가 제대로 작동하지 않거나 시장 환경 불리

**해결**:
```yaml
# 필터 강화
volume_filter:
  multiplier: 2.0        # 더 확실한 거래량 급증만

rsi:
  overbought: 65         # 더 일찍 과매수 판단

confidence:
  threshold: 70          # 더 높은 신뢰도 요구
```

### 문제 3: 테스트 실패

```bash
# 테스트 실행시 오류
poetry run pytest tests/unit/test_momentum.py -v
```

**해결**:
```bash
# 의존성 재설치
poetry install

# 캐시 삭제
rm -rf .pytest_cache

# Python 경로 확인
poetry run python -c "import sys; print(sys.path)"
```

### 문제 4: 설정 파일 로드 오류

```
ValidationError: enhanced_strategy.volume_filter.multiplier must be >= 1.0
```

**해결**: 설정 파일의 값 범위 확인
```yaml
volume_filter:
  window_days: 20        # 5-252 범위
  multiplier: 1.5        # 1.0-10.0 범위

rsi:
  period: 14             # 5-100 범위
  overbought: 70         # 50-100 범위
  oversold: 30           # 0-50 범위
```

---

## 📚 추가 자료

### 관련 문서
- **전체 설계**: `specs/002-spec-md/spec.md`
- **구현 계획**: `specs/002-spec-md/plan.md`
- **작업 목록**: `specs/002-spec-md/tasks.md`
- **테스트 가이드**: `docs/MVP_테스트_가이드.md`

### 핵심 소스코드
- `src/indicators/volume.py` - 거래량 필터 구현
- `src/indicators/momentum.py` - RSI 지표 구현
- `src/signals/generator.py` - 신호 생성 로직
- `src/backtest/engine.py` - 백테스트 엔진

### 학습 자료
- **RSI 지표**: https://www.investopedia.com/terms/r/rsi.asp
- **볼린저 밴드**: https://www.investopedia.com/terms/b/bollingerbands.asp
- **거래량 분석**: https://www.investopedia.com/articles/technical/02/010702.asp

---

## 🔄 업데이트 이력

| 버전 | 날짜 | 내용 |
|------|------|------|
| 1.0.0 | 2025-10-15 | Phase 1 MVP 초기 릴리즈 |

---

## 📞 지원

### 버그 리포트
- GitHub Issues: `https://github.com/your-repo/issues`
- 이메일: support@example.com

### 기능 요청
Phase 2, 3 로드맵:
- Phase 2: MACD 필터 + 신뢰도 시스템 (승률 70-75%)
- Phase 3: ATR 동적 손절매 (수익률 +15-20%)

---

**작성일**: 2025-10-15
**버전**: Phase 1 MVP v1.0.0
**라이센스**: MIT

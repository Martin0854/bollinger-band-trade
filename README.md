# 볼린저 밴드 Squeeze 트레이딩 전략

한국 주식시장(KOSPI)을 대상으로 **Bollinger Band Squeeze 전략**을 활용한 백테스팅 시스템입니다.

## 프로젝트 개요

이 프로젝트는 볼린저 밴드의 **Squeeze(수축) 패턴**을 활용하여 변동성 돌파 시점을 포착하고, Volume 및 RSI 필터로 신호 품질을 개선한 트레이딩 전략입니다. 실제 한국 주식시장 데이터로 백테스팅하여 전략의 성과를 검증합니다.

### 핵심 전략: Bollinger Band Squeeze

**Squeeze(수축)**란 볼린저 밴드의 상단과 하단 밴드 간격이 좁아지는 현상으로, 변동성이 낮아진 상태를 의미합니다. 이후 큰 가격 움직임(돌파)이 발생할 확률이 높아 매매 기회를 제공합니다.

## Phase 1 MVP 완료 ✅

### 구현된 기능

**1. Bollinger Band Squeeze 탐지**
- 밴드폭이 과거 10일 대비 30% 이하로 수축 시 Squeeze 감지
- Squeeze 후 상단 밴드 돌파 시 매수 신호 생성

**2. Volume Filter (User Story 1)**
- 20일 평균 거래량 대비 1.5배 이상 급증 시에만 진입
- 거짓 신호 필터링으로 승률 개선

**3. RSI Filter (User Story 2)**
- RSI 14일 기준, 70 미만일 때만 매수 진입
- 과매수 구간 진입 방지

**4. 신뢰도 스코어링 시스템**
- Base (25점) + Volume (25점) + RSI (20점) = 총 70점
- 임계값 60점 이상 신호만 실행

**5. 백테스팅 엔진**
- 실제 한국 주식 데이터 (Yahoo Finance)
- 포트폴리오 관리 (최대 15종목 동시 보유)
- 리스크 관리 (5% 손절매, 포지션당 30% 제한)

**6. 성과 지표**
- 총 수익률, CAGR (연평균 수익률)
- 승률, 손익비, 수익 팩터
- 최대 낙폭(MDD), 샤프 비율
- 거래별 상세 분석

### Phase 1 백테스트 결과 (KOSPI 100, 2023년)

```
수익률:    +11.75%
승률:      40.9%
CAGR:      34.7%
샤프 비율: 2.93
MDD:       -4.40%
거래:      23건
```

**5년 평균 (2020-2024)**
- 평균 수익률: -0.80%
- 수익 연도: 3년 (2020, 2021, 2023)
- 손실 연도: 2년 (2022, 2024)
- **발견**: 상승장에만 유효, 하락장 대응 필요

## 프로젝트 구조

```
bollinger-band-trade/
├── src/                    # 소스 코드
│   ├── backtest/          # 백테스트 엔진
│   ├── cli/               # CLI 인터페이스
│   ├── data/              # 데이터 저장소
│   ├── indicators/        # 기술적 지표 (볼린저 밴드, 스퀴즈 등)
│   ├── models/            # 데이터 모델 (설정, 포트폴리오, 거래 등)
│   ├── risk/              # 리스크 관리
│   ├── signals/           # 매매 신호 생성
│   └── utils/             # 유틸리티 함수
├── examples/              # 실행 가능한 백테스트 예제
│   ├── phase1_mvp_backtest.py           # Phase 1 Mock 데이터 백테스트
│   ├── phase1_mvp_real_data.py          # 실제 데이터 백테스트 (2종목)
│   ├── phase1_mvp_real_data_relaxed.py  # 완화된 파라미터 백테스트
│   ├── phase1_mvp_kospi100.py           # KOSPI 100 종목 백테스트
│   └── phase1_yearly_comparison.py      # 5년 연도별 비교 분석
├── scripts/               # 유틸리티 스크립트
│   ├── fetch_kospi_top100.py      # KOSPI TOP100 종목 가져오기
│   ├── kospi_top100.txt           # KOSPI TOP100 종목 리스트
│   └── fetch_data_yfinance.py     # Yahoo Finance 데이터 수집
├── tests/                 # 테스트 코드
│   ├── unit/             # 유닛 테스트
│   ├── integration/      # 통합 테스트
│   └── contract/         # 계약 테스트
├── config/               # 설정 파일
│   ├── default.yaml      # 기본 설정
│   └── examples/         # Phase 1 MVP 설정 예제
│       ├── phase1_volume_rsi.yaml         # 표준 파라미터
│       └── phase1_volume_rsi_relaxed.yaml # 완화된 파라미터
├── docs/                 # 문서 (한글/영문)
│   ├── Phase1_MVP_백테스트_결과_보고서.md  # Phase 1 상세 결과
│   ├── MVP_테스트_가이드.md                # 테스트 실행 가이드
│   └── 사용자_가이드_MVP.md                # MVP 사용 시나리오
├── specs/                # 기능 명세서 (SpecKit)
│   ├── spec.md           # Phase 1 MVP 명세
│   ├── constitution.md   # 프로젝트 원칙
│   └── templates/        # 설계 템플릿
├── logs/                 # 백테스트 로그 (gitignore)
└── data/                 # 데이터 캐시 (gitignore)
```

## 기술 스택

- **언어**: Python 3.12+
- **의존성 관리**: Poetry
- **데이터 수집**: yfinance (Yahoo Finance API)
- **데이터 분석**: pandas, numpy
- **백테스팅**: 자체 구현 엔진 (포트폴리오 관리, 리스크 관리)
- **기술 지표**: Bollinger Bands, RSI, Volume 분석
- **테스팅**: pytest (unit/integration), hypothesis (property-based)
- **문서화**: SpecKit (명세 기반 개발)

## 설치 방법

```bash
# 저장소 클론
git clone https://github.com/yourusername/bollinger-band-trade.git
cd bollinger-band-trade

# Poetry로 의존성 설치
poetry install

# 또는 pip 사용
pip install -e .
```

## 빠른 시작

### 1. Phase 1 MVP 백테스트 실행

```bash
# Mock 데이터로 빠른 테스트 (2종목, 1년)
poetry run python examples/phase1_mvp_backtest.py

# 실제 데이터 백테스트 (삼성전자, SK하이닉스)
poetry run python examples/phase1_mvp_real_data.py

# KOSPI 100 종목 백테스트 (표준 파라미터)
poetry run python examples/phase1_mvp_kospi100.py

# 5년 연도별 비교 분석 (2020-2024)
poetry run python examples/phase1_yearly_comparison.py
```

### 2. 테스트 실행

```bash
# 전체 테스트 스위트 실행 (33개 테스트)
poetry run pytest tests/

# 커버리지 포함
poetry run pytest tests/ --cov=src --cov-report=html

# 특정 테스트만 실행
poetry run pytest tests/unit/test_volume_filter.py -v
```

### 3. 설정 파일 수정

`config/examples/phase1_volume_rsi.yaml`을 편집하여 파라미터 조정:

```yaml
# 백테스트 기간
date_range:
  start: "2023-01-01"
  end: "2023-12-31"

# Squeeze 임계값 (낮을수록 신호 많음)
squeeze_threshold_percent: 30.0

# Volume Filter
enhanced_strategy:
  volume_filter:
    multiplier: 1.5  # 1.2-2.0 범위 조정

  # RSI Filter
  rsi:
    overbought: 70   # 65-75 범위 조정

  # 신뢰도 임계값
  confidence:
    threshold: 60    # 50-70 범위 조정
```

### 4. 상세 문서

- [Phase 1 백테스트 결과 보고서](docs/Phase1_MVP_백테스트_결과_보고서.md)
- [MVP 테스트 가이드](docs/MVP_테스트_가이드.md)
- [사용자 가이드](docs/사용자_가이드_MVP.md)

## 전략 상세

### Bollinger Band Squeeze 전략

**1. Squeeze 탐지**
- 밴드폭 = (상단밴드 - 하단밴드) / 중간선 × 100
- Squeeze: 현재 밴드폭이 과거 10일 최소값 대비 30% 이하

**2. 매수 신호**
- Squeeze 상태에서 주가가 상단 밴드 돌파
- AND Volume이 20일 평균 대비 1.5배 이상
- AND RSI < 70 (과매수 아님)
- AND 신뢰도 점수 ≥ 60점

**3. 매도 신호**
- 5% 손절매 (stop_loss_percent)
- 또는 다음 Squeeze 발생 시

**4. 리스크 관리**
- 종목당 최대 포지션: 30%
- 동시 보유: 최대 15종목
- 손절매: -5%

### 신뢰도 스코어링

```
Base Score    25점  (Bollinger Squeeze 발생)
+ Volume      25점  (거래량 1.5배 이상)
+ RSI         20점  (RSI < 70)
+ MACD        30점  (Phase 2 예정)
= Total      100점

임계값: 60점 이상 신호만 실행
```

## 백테스트 결과 요약

### 연도별 성과 (KOSPI 100, 표준 파라미터)

| 연도 | 수익률 | 승률 | CAGR | 샤프 | MDD | 거래 |
|------|--------|------|------|------|-----|------|
| 2020 | +5.59% | 23.1% | 28.97% | 1.23 | -5.49% | 14건 |
| 2021 | +1.51% | 35.5% | 4.45% | 0.24 | -22.80% | 63건 |
| 2022 | -8.92% | 25.7% | -42.84% | -1.87 | -14.81% | 36건 |
| **2023** | **+11.75%** | **40.9%** | **34.74%** | **2.93** | **-4.40%** | **23건** |
| 2024 | -13.94% | 25.0% | 0.00% | -0.53 | -24.03% | 65건 |

**5년 평균**: -0.80% (수익 3년 / 손실 2년)

### 핵심 인사이트

✅ **상승장에 강함** (2023년 최고 성과)
- 승률 40.9%, CAGR 34.7%
- 샤프 비율 2.93 (위험 대비 수익 우수)

❌ **하락장에 취약** (2022, 2024년 손실)
- 평균 -11.4% 손실
- 현재 전략은 롱 온리 (매수만 가능)

💡 **개선 필요**
- 시장 추세 필터 (200일 이동평균)
- MACD 추세 확인 (Phase 2)
- 하락장 대응 로직

## 주의사항

⚠️ **이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.**

- 실제 투자에 사용 시 발생하는 손실에 대해 책임지지 않습니다
- 과거 데이터 기반 백테스팅 결과가 미래 수익을 보장하지 않습니다
- **현재 전략은 상승장에만 유효**하며 하락장 대응이 필요합니다
- 실제 투자 전 충분한 검증과 리스크 관리가 필수입니다

## 로드맵

### ✅ Phase 1 MVP (완료)
- [x] Bollinger Band Squeeze 탐지
- [x] Volume Filter (거래량 급증 필터)
- [x] RSI Filter (과매수 방지)
- [x] 신뢰도 스코어링 시스템
- [x] 백테스팅 엔진 (포트폴리오 관리)
- [x] KOSPI 100 실제 데이터 백테스트
- [x] 5년 연도별 비교 분석

### 🔄 Phase 2 (계획)
- [ ] MACD 필터 추가 (추세 확인)
- [ ] 목표: 승률 70-75%
- [ ] 하락장 감지 로직

### 🔄 Phase 3 (계획)
- [ ] 다단계 신뢰도 평가 시스템
- [ ] 포지션 크기 동적 조정

### 🔄 Phase 4 (계획)
- [ ] ATR 기반 동적 손절매
- [ ] 목표: 수익률 +15-20%
- [ ] 변동성 기반 리스크 관리

## 테스트 커버리지

- **Unit Tests**: 23개 (볼린저 밴드, Volume, RSI, 신호 생성)
- **Integration Tests**: 10개 (엔진, 파이프라인, 설정)
- **전체**: 33/34 통과 (97%)

```bash
poetry run pytest tests/ -v
```

## 참고 자료

- [Bollinger Bands](https://en.wikipedia.org/wiki/Bollinger_Bands) - Wikipedia
- [Bollinger Band Squeeze](https://www.investopedia.com/articles/trading/09/bollinger-band-squeeze.asp) - Investopedia
- [RSI (Relative Strength Index)](https://www.investopedia.com/terms/r/rsi.asp)
- [Yahoo Finance API](https://github.com/ranaroussi/yfinance) - yfinance

## 라이선스

MIT License

## 문의

프로젝트 관련 문의나 버그 리포트는 GitHub Issues를 이용해주세요.

# 볼린저 밴드 오토 트레이딩 봇

한국 주식시장을 대상으로 볼린저 밴드(Bollinger Bands) 전략을 활용한 자동 매매 시스템입니다.

## 프로젝트 개요

이 프로젝트는 기술적 분석 지표인 볼린저 밴드를 활용하여 한국 주식시장에서 자동으로 매매 신호를 생성하고, 과거 데이터를 기반으로 전략의 성과를 평가하는 트레이딩 봇입니다.

## 주요 기능

### 1. 종목 선정
- 한국 주식시장(KOSPI/KOSDAQ) 종목 선택 기능
- 관심 종목 리스트 관리

### 2. 초기 상태 지정
- **시드머니(Seed Money)**: 초기 투자 자금 설정
- **포지션 현황**: 현재 보유 종목 및 수량 입력

### 3. 실제 주식시장 과거 데이터 수집
- 한국 주식시장 과거 가격 데이터 수집
- 일봉, 분봉 등 다양한 시간 프레임 지원
- 거래량, 시가, 고가, 저가, 종가 데이터 포함

### 4. 볼린저 밴드 수치 계산
- **중심선(Middle Band)**: 이동평균선 계산
- **상단 밴드(Upper Band)**: 중심선 + (표준편차 × 2)
- **하단 밴드(Lower Band)**: 중심선 - (표준편차 × 2)
- 사용자 정의 파라미터 설정 가능 (기간, 표준편차 배수)

### 5. 현재 포지션 결정
- 볼린저 밴드 기반 매수/매도 신호 생성
  - **매수 신호**: 주가가 하단 밴드 돌파 시
  - **매도 신호**: 주가가 상단 밴드 도달 시
- 현재 보유 포지션 자동 업데이트

### 6. 매매 이력을 통한 점수 스코어링
- 각 거래의 수익률 추적
- 전체 포트폴리오 성과 지표 계산
  - 총 수익률
  - 승률
  - 최대 낙폭(MDD: Maximum Drawdown)
  - 샤프 비율(Sharpe Ratio)
- 거래 이력 로그 기록 및 분석

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
├── scripts/               # 실행 스크립트
│   ├── my_first_backtest.py       # 첫 백테스트 예제
│   ├── run_multi_backtest.py      # 다종목 백테스트
│   ├── run_with_yaml.py           # YAML 설정 기반 실행
│   ├── analyze_trades.py          # 거래 분석 도구
│   ├── check_my_trades.py         # 거래 내역 확인
│   ├── fetch_kospi_top100.py      # KOSPI TOP100 종목 가져오기
│   └── fetch_data_yfinance.py     # Yahoo Finance 데이터 수집
├── tests/                 # 테스트 코드
│   ├── unit/             # 유닛 테스트
│   ├── integration/      # 통합 테스트
│   └── contract/         # 계약 테스트
├── config/               # 설정 파일
│   ├── default.yaml      # 기본 설정
│   └── examples/         # 설정 예제
├── docs/                 # 문서
│   ├── 사용법.md
│   ├── 전략_상세_설명.md
│   ├── 거래내역_확인_가이드.md
│   ├── 코스피100_백테스트_가이드.md
│   ├── 데이터_가져오기_가이드.md
│   ├── 기간_변경_가이드.md
│   ├── USAGE.md
│   └── TEST_SUMMARY.md
├── examples/             # 사용 예제
├── results/              # 백테스트 결과 (gitignore)
├── data/                 # 데이터 캐시 (gitignore)
└── specs/                # 기능 명세서
```

## 기술 스택

- **언어**: Python 3.x
- **의존성 관리**: Poetry
- **데이터 수집**: yfinance, FinanceDataReader
- **데이터 분석**: pandas, numpy
- **백테스팅**: 자체 구현 엔진
- **테스팅**: pytest, hypothesis

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

## 사용 방법

### 1. 빠른 시작

```bash
# 첫 백테스트 실행
python scripts/my_first_backtest.py

# YAML 설정 파일로 실행
python scripts/run_with_yaml.py --config config/examples/single_stock.yaml

# 다종목 백테스트
python scripts/run_multi_backtest.py
```

### 2. CLI 사용

```bash
# CLI 도구 사용
python -m src.cli.main --help
```

### 3. 상세 가이드

- [사용법 가이드](docs/사용법.md)
- [전략 상세 설명](docs/전략_상세_설명.md)
- [KOSPI100 백테스트 가이드](docs/코스피100_백테스트_가이드.md)
- [거래내역 확인 가이드](docs/거래내역_확인_가이드.md)

## 설정

YAML 설정 파일 예시 (`config/examples/single_stock.yaml`):

```yaml
seed_money: 10000000
stocks:
  - ticker: "005930.KS"  # 삼성전자
    name: "삼성전자"
bollinger:
  period: 20
  std_dev: 2.0
backtest:
  start_date: "2023-01-01"
  end_date: "2023-12-31"
```

## 볼린저 밴드 전략 설명

### 기본 원리
볼린저 밴드는 주가의 변동성을 기반으로 매수/매도 타이밍을 포착하는 기술적 지표입니다.

### 매매 규칙
1. **매수 조건**: 주가가 하단 밴드를 하향 돌파할 때 (과매도 구간)
2. **매도 조건**: 주가가 상단 밴드에 도달할 때 (과매수 구간)
3. **손절 조건**: 설정된 손실률 도달 시 자동 손절

### 리스크 관리
- 최대 포지션 크기 제한
- 손절/익절 비율 설정
- 자금 관리 규칙 적용

## 주의사항

⚠️ **이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.**

- 실제 투자에 사용 시 발생하는 손실에 대해 책임지지 않습니다
- 과거 데이터 기반 백테스팅 결과가 미래 수익을 보장하지 않습니다
- 실제 투자 전 충분한 검증과 리스크 관리가 필요합니다

## 로드맵

- [ ] 백테스팅 엔진 구현
- [ ] 실시간 데이터 연동
- [ ] 웹 대시보드 개발
- [ ] 다양한 기술적 지표 추가 (RSI, MACD 등)
- [ ] 알림 기능 (텔레그램, 이메일 등)

## 라이선스

MIT License

## 기여

버그 리포트 및 기능 제안은 이슈로 등록해 주세요.

## 참고 자료

- [볼린저 밴드란?](https://ko.wikipedia.org/wiki/%EB%B3%BC%EB%A6%B0%EC%A0%80_%EB%B0%B4%EB%93%9C)
- 한국거래소(KRX) 데이터 활용 가이드

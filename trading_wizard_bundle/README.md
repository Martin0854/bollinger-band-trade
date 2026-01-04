# 데일리 트레이딩 위자드

볼린저 밴드 스퀴즈 전략 기반 한국 주식 매매 시스템

## 문서

- **[설치가이드.md](설치가이드.md)** - Python 설치부터 패키지 설치까지 상세 안내
- **[사용법.md](사용법.md)** - 일일 사용법, 워크플로우, JSON 수정 방법, FAQ

## 파일 구조

```
trading_wizard_bundle/
├── README.md                      # 이 문서
├── 설치가이드.md                   # Python 설치 및 환경 설정
├── 사용법.md                       # 상세 사용법 및 FAQ
├── daily_wizard.py                # 일일 매수/매도 추천 생성
├── backtest_wizard.py             # 백테스트 실행
├── visualize_portfolio.py         # 포트폴리오 시각화
├── get_historical_top100.py       # 연도별 KOSPI Top 100 생성
├── portfolio_state.json           # 현재 포트폴리오 상태
├── data/
│   └── stock_names_kr.json        # 한국어 종목명 매핑
├── src/wizard/                    # 핵심 모듈
│   ├── portfolio_manager.py       # 포트폴리오 관리
│   ├── signal_scanner.py          # 시그널 스캔
│   └── recommendation.py          # 추천 생성
├── kospi_top100_2023jan.txt       # 2023년 1월 기준 Top 100
├── kospi_top100_2024jan.txt       # 2024년 1월 기준 Top 100
├── kospi_top100_2025jan.txt       # 2025년 1월 기준 Top 100
├── kospi_top100_2026jan.txt       # 2026년 1월 기준 Top 100
├── backtest_2023_jan_result.json  # 2023년 백테스트 결과
├── backtest_2024_jan_result.json  # 2024년 백테스트 결과
└── backtest_2025_jan_result.json  # 2025년 백테스트 결과
```

## 3개년 백테스트 결과 요약

| 연도 | 수익률 | 최대 낙폭 | 거래수 | 승률 |
|------|--------|-----------|--------|------|
| 2023 | +10.12% | -10.82% | 176 | 19.8% |
| 2024 | +3.99% | -21.86% | 208 | 20.0% |
| 2025 | +66.11% | -12.65% | 135 | 36.1% |
| **3년 누적** | **+90.21%** | | | |

* 각 연도 1월 기준 KOSPI Top 100 사용 (생존자 편향 제거)

## 사용법

### 1. 일일 위자드 실행 (장 마감 후 오후 3:30 이후)

```bash
# 포트폴리오 초기화 (최초 1회만)
python daily_wizard.py --init

# 일일 추천 생성
python daily_wizard.py

# 현재 상태만 확인
python daily_wizard.py --status
```

### 2. 포트폴리오 시각화

```bash
# 실시간 현재가 조회 (실제 운용 시)
python visualize_portfolio.py

# 백테스트 결과 확인 (저장된 종료일 가격 사용)
python visualize_portfolio.py --file backtest_2025_jan_result.json

# 현재가 조회 없이 (빠른 확인)
python visualize_portfolio.py --no-fetch
```

### 3. 백테스트 실행

```bash
# 연도 지정 백테스트
python backtest_wizard.py --year 2025 --stocks kospi_top100_2025jan.txt

# 결과 파일 지정
python backtest_wizard.py --year 2024 --stocks kospi_top100_2024jan.txt --output my_backtest.json

# 기간 직접 지정
python backtest_wizard.py --start 2024-06-01 --end 2024-12-31 --stocks kospi_top100_2024jan.txt
```

### 4. 연도별 KOSPI Top 100 생성

```bash
python get_historical_top100.py --year 2025
# 결과: kospi_top100_2025jan.txt
```

## 전략 설정

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| 초기 자본 | 1,000,000 KRW | 시드 머니 |
| 최대 포지션 | 15개 | 분산 투자 |
| 포지션당 비중 | 10% | 약 100,000원/종목 |
| 신뢰도 임계값 | 60점 | 매수 최소 기준 |
| 손절선 | -5% | 손실 제한 |

## 매수 신호 조건

1. **볼린저 밴드 상단 돌파** (Squeeze Breakout)
   - 종가가 상단 밴드(20일 MA + 2σ)를 돌파

2. **신뢰도 점수 60점 이상**
   - 기본: 25점
   - 거래량 1.5배 이상: +25점
   - RSI 30~70 (중립구간): +20점
   - MACD 히스토그램 > 0 (상승추세): +30점

## 매도 신호 조건

1. **손절**: 매수가 대비 -5% 이하
2. **기술적 매도**: 종가가 볼린저 밴드 하단 이탈

## 워크플로우

```
[장 마감 후 오후 4시]
    │
    ▼
python daily_wizard.py
    │
    ├── 전일 주문 처리 (executed=true 인 것)
    ├── 매도 시그널 스캔 (보유 종목)
    ├── 매수 시그널 스캔 (KOSPI 100)
    └── 추천 출력 & JSON 저장
    │
    ▼
[다음날 장 시작 전]
    │
    ├── 추천 종목 주문 (시장가 또는 지정가)
    └── 체결 가격 기록
    │
    ▼
[저녁]
    │
    └── portfolio_state.json 수정
        - actual_price: 실제 체결가
        - executed: true
    │
    ▼
[반복]
```

## 의존성

```bash
pip install yfinance pandas numpy
```

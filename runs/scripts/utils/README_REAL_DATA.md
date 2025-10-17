# KOSPI 100 실제 데이터 백테스트

## 개요

Yahoo Finance에서 **실제 한국 주식 시장 데이터**를 다운로드하여 Phase 3 Confidence Scoring 시스템을 테스트합니다.

## 특징

- ✅ **실제 시장 데이터** (Yahoo Finance API)
- ✅ **외부 파일에서 종목 로드** (`data/kospi_top100.txt`)
- ✅ **KOSPI 100개 종목** (사용자 정의 가능)
- ✅ **자동 데이터 다운로드** (인터넷 연결 필요)
- ✅ **Phase 3 필터 시스템** (Volume + RSI + MACD + Confidence)

## 빠른 실행

```bash
# Poetry 환경에서 실행
poetry run python scripts/run_kospi100_real_data.py

# 또는 직접 실행
chmod +x scripts/run_kospi100_real_data.py
./scripts/run_kospi100_real_data.py
```

## 최근 실행 결과 (2023년)

```
================================================================================
📊 백테스트 결과
================================================================================
총 수익률:                        1.28%
승률:                           32.14%
총 거래:                           59회
승리 거래:                          9회
패배 거래:                         19회
================================================================================

📈 거래 분석:
거래 발생 종목: 28개
거래가 없는 종목: 22개

종목별 거래 수 (Top 5):
  012330:  4건  (현대모비스)
  000660:  3건  (SK하이닉스)
  207940:  2건  (삼성바이오로직스)
  105560:  2건  (KB금융)
  ...

신뢰도 점수 통계:
  평균: 100.0/100
  최대: 100/100
  최소: 100/100
```

## 시뮬레이션 vs 실제 데이터

### 이전 (시뮬레이션 데이터)

- ❌ 인위적인 스퀴즈 → 브레이크아웃 패턴
- ❌ 랜덤 생성 데이터
- ❌ 실제 시장 동작과 다름

**파일**: `scripts/run_kospi100_backtest.py`

### 현재 (실제 Yahoo Finance 데이터)

- ✅ 2023년 실제 KOSPI 시장 데이터
- ✅ 245일 거래 데이터
- ✅ 실제 가격, 거래량, 변동성
- ✅ 현실적인 백테스트 결과

**파일**: `scripts/run_kospi100_real_data.py`

## 설정

### 백테스트 기간 변경

`config/examples/phase3_confidence.yaml` 파일에서:

```yaml
date_range:
  start: "2023-01-01"  # 시작일
  end: "2023-12-31"    # 종료일
```

### 종목 수 조정

#### 방법 1: 파일 편집 (권장)

`data/kospi_top100.txt` 파일을 직접 수정:

```txt
# 원하는 종목만 남기기
005930  # 삼성전자
000660  # SK하이닉스
035420  # NAVER
```

#### 방법 2: 스크립트 수정

스크립트 내 147번째 줄:

```python
# 50개 종목만 테스트 (기본값)
config_dict['stocks'] = kospi_stocks[:50]

# 전체 100개 종목 테스트 (다운로드 시간 증가)
config_dict['stocks'] = kospi_stocks

# 처음 10개만 빠른 테스트
config_dict['stocks'] = kospi_stocks[:10]
```

### 필터 설정

`config/examples/phase3_confidence.yaml` 파일에서:

```yaml
enhanced_strategy:
  confidence:
    threshold: 60  # 50으로 낮추면 더 많은 거래
```

## 데이터 소스

### Yahoo Finance 티커 형식

한국 주식: `종목코드.KS`
- 삼성전자: `005930.KS`
- SK하이닉스: `000660.KS`
- NAVER: `035420.KS`

### 다운로드 데이터

- **OHLCV**: Open, High, Low, Close, Volume
- **시간대**: Asia/Seoul (자동 변환)
- **기간**: 설정 파일에서 지정

## 성능

### 실행 시간

- **데이터 다운로드**: ~30초 (50개 종목)
- **백테스트 실행**: ~1-2분
- **전체**: ~2-3분

### 네트워크

- 인터넷 연결 필수
- Yahoo Finance API 사용 (무료)
- API 제한: 초당 2,000 요청 (충분함)

## 문제 해결

### "데이터 없음" 오류

일부 종목은 Yahoo Finance에 상장되지 않을 수 있습니다:

```
다운로드 중: 012345 (012345.KS)... ❌ 데이터 없음
```

**해결**: 자동으로 스킵되며 다른 종목 계속 처리

### "거래가 발생하지 않음"

필터가 너무 엄격할 수 있습니다:

```yaml
# 해결 방법 1: Threshold 낮추기
confidence:
  threshold: 50  # 60 → 50

# 해결 방법 2: MACD 비활성화
macd:
  enabled: false

# 해결 방법 3: 백테스트 기간 늘리기
date_range:
  start: "2022-01-01"  # 2년 데이터
  end: "2023-12-31"
```

### 네트워크 오류

```python
# 타임아웃 증가 또는 재시도
stock = yf.Ticker(ticker)
df = stock.history(start=start_date, end=end_date, timeout=30)
```

## 결과 파일

### Excel 파일

- **위치**: `results/backtest_real_data_2023-01-01_2023-12-31_YYYYMMDD_HHMMSS.xlsx`
- **컬럼**: 날짜, 종목, 가격, 수량, 신뢰도점수, 필터 통과 여부, 손익 등

### 파일명 형식

```
backtest_real_data_{시작일}_{종료일}_{타임스탬프}.xlsx
```

예: `backtest_real_data_2023-01-01_2023-12-31_20251016_173045.xlsx`

## 다음 단계

### 더 많은 종목

```python
# 전체 KOSPI 100
config_dict['stocks'] = KOSPI_100_STOCKS  # 100개
```

### 더 긴 기간

```yaml
date_range:
  start: "2020-01-01"
  end: "2023-12-31"  # 4년
```

### 다른 데이터 소스

- **FinanceDataReader**: 한국 주식 전문
- **pykrx**: KRX 공식 데이터
- **증권사 API**: 실시간 데이터

## 비교

| 항목 | 시뮬레이션 | 실제 데이터 |
|------|-----------|------------|
| 데이터 | 랜덤 생성 | Yahoo Finance |
| 현실성 | 낮음 | 높음 |
| 실행 시간 | 빠름 (~30초) | 보통 (~3분) |
| 인터넷 | 불필요 | 필수 |
| 신뢰성 | 테스트용 | 실전용 |

## 참고

- Yahoo Finance API: https://github.com/ranaroussi/yfinance
- KOSPI 종목 코드: https://finance.naver.com
- 전체 작업: `specs/002-spec-md/tasks.md`

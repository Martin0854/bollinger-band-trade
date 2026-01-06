# 볼린저 밴드 스퀴즈 전략 v2: 하이브리드 점수제

**Version**: 2.0
**Created**: 2026-01-06
**Based on**: Gemini 리뷰 피드백 수용
**Status**: Proposed

---

## 1. 개요

### 1.1 기존 전략 (v1) 문제점

| 항목 | v1 (단순 점수 합산) | 문제점 |
|------|-------------------|--------|
| 구조 | 모든 지표 점수 단순 합산 | 필수 조건 없이 유연성만 추구 |
| 거래량 | 가산점 부여 (0-25점) | 거래량 없는 가짜 돌파 진입 가능 |
| 스퀴즈 검증 | BB_Width < MA*0.7 | 최저치 여부 미확인 |
| 신뢰도 | 중등 | 가짜 돌파(Fake-out) 취약 |

### 1.2 개선 방향: 하이브리드 점수제

**필수 조건(Filter) + 가중치 점수(Weighting) 결합**

- **Stage 1**: 필수 필터 (Pass/Fail) - 미충족 시 점수 계산 자체 스킵
- **Stage 2**: 방향성 가중치 점수 - 진입 품질 평가

---

## 2. Stage 1: 필수 필터 (Gate Conditions)

### 2.1 스퀴즈 품질 필터 (Squeeze Quality)

```
스퀴즈 확인 = BB_Width가 최근 N기간 중 최저치 OR 최저치 근접(5% 이내)
```

**현재 구현 vs 개선안**:

| 항목 | 현재 (v1) | 개선안 (v2) |
|------|-----------|-------------|
| 조건 | `BB_Width < BB_Width_MA * 0.7` | `BB_Width == min(BB_Width[-N:])` |
| 기간 | 10일 이동평균 대비 | 20일 중 최저치 |
| 의미 | 상대적 축소 | 절대적 극값 (에너지 축적 완료) |

**구현 예시**:

```python
def is_squeeze_mature(df: pd.DataFrame, lookback: int = 20) -> bool:
    """스퀴즈가 성숙했는지 (최저 변동성) 확인"""
    current_width = df["BB_Width"].iloc[-1]
    min_width = df["BB_Width"].iloc[-lookback:].min()

    # 현재 폭이 최저치이거나 5% 이내
    return current_width <= min_width * 1.05
```

### 2.2 거래량 분출 필터 (Volume Explosion)

> "거래량이 터지지 않는 스퀴즈 돌파는 무시한다. 이것만으로도 승률이 급상승한다." - Gemini

```
거래량 분출 = 현재 거래량 > Volume_MA * threshold (기본 1.5x)
```

**핵심 변경**: 가산점이 아닌 **입장권(Gate)**으로 사용

| 항목 | 현재 (v1) | 개선안 (v2) |
|------|-----------|-------------|
| 역할 | 점수 가산 (0-25점) | 필수 필터 (Pass/Fail) |
| 미충족 시 | 낮은 점수로 진입 가능 | 진입 자체 불가 |

**구현 예시**:

```python
def has_volume_explosion(df: pd.DataFrame, threshold: float = 1.5) -> bool:
    """거래량 분출 여부 확인 (필수 조건)"""
    current_volume = df["Volume"].iloc[-1]
    avg_volume = df["Volume_MA"].iloc[-1]

    return current_volume >= avg_volume * threshold
```

### 2.3 Stage 1 통합 로직

```python
def pass_stage1_filters(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Stage 1 필수 필터 통과 여부 확인

    Returns:
        (통과 여부, 실패 사유)
    """
    # 1. 스퀴즈 품질 확인
    if not is_squeeze_mature(df, lookback=20):
        return False, "squeeze_not_mature"

    # 2. 거래량 분출 확인
    if not has_volume_explosion(df, threshold=1.5):
        return False, "volume_insufficient"

    return True, "passed"
```

---

## 3. Stage 2: 방향성 가중치 점수 (Direction Scoring)

### 3.1 점수 배분 변경

| 지표 | v1 배점 | v2 배점 | 변경 사유 |
|------|---------|---------|-----------|
| Base (돌파) | 25점 | 0점 | Stage 1으로 이동 |
| Volume | 25점 | 0점 | Stage 1으로 이동 (필수 필터) |
| RSI | 20점 | **25점** | 방향성 확인 강화 |
| MACD | 30점 | **30점** | 추세 확인 유지 |
| Price Action | 0점 | **45점** | 돌파 강도 평가 (신규) |
| **합계** | 100점 | **100점** | - |

### 3.2 RSI 점수 (25점) - 방향성 기반

> "단순히 'RSI가 높으면 점수'가 아니라, 스퀴즈 시점의 지표 상태를 보아야 한다"

**v1 (현재)**: RSI 50에 가까울수록 높은 점수

**v2 (개선)**: **방향성 전환** 감지

```python
def calculate_rsi_score_v2(df: pd.DataFrame, direction: str = "LONG") -> float:
    """
    RSI 방향성 점수 계산 (0-25점)

    평가 기준:
    - 50선 돌파 여부 (기본 점수)
    - 과매수/과매도 탈출 방향
    - RSI 다이버전스 (추가 가산)
    """
    rsi = df["RSI"].iloc[-1]
    rsi_prev = df["RSI"].iloc[-2]
    score = 0.0

    if direction == "LONG":
        # 50선 상향 돌파
        if rsi > 50 and rsi_prev <= 50:
            score += 15.0  # 강한 신호
        elif rsi > 50:
            score += 10.0  # 상승 영역 유지

        # 과매도 탈출 (30 이하에서 회복)
        rsi_5d_min = df["RSI"].iloc[-5:].min()
        if rsi_5d_min < 30 and rsi > 35:
            score += 10.0  # 반등 신호

        # 과매수 근접 시 감점
        if rsi > 70:
            score -= 5.0  # 고점 매수 위험

    return max(0.0, min(25.0, score))
```

### 3.3 MACD 점수 (30점) - 추세 확인 강화

**v2 개선**: 히스토그램 **기울기** 추가 평가

```python
def calculate_macd_score_v2(df: pd.DataFrame) -> float:
    """
    MACD 추세 점수 계산 (0-30점)

    평가 기준:
    - 시그널 선 교차 (골든크로스)
    - 히스토그램 양수 여부
    - 히스토그램 기울기 (가속도)
    """
    macd = df["MACD"].iloc[-1]
    signal = df["MACD_Signal"].iloc[-1]
    histogram = df["MACD_Histogram"].iloc[-1]
    histogram_prev = df["MACD_Histogram"].iloc[-2]

    score = 0.0

    # 1. 기본: MACD > Signal (골든크로스 상태)
    if macd > signal:
        score += 15.0

    # 2. 히스토그램 양수
    if histogram > 0:
        score += 10.0

    # 3. 히스토그램 기울기 (가속)
    histogram_slope = histogram - histogram_prev
    if histogram_slope > 0:
        score += 5.0  # 상승 가속

    return min(30.0, score)
```

### 3.4 Price Action 점수 (45점) - 신규

> "밴드 상단/하단 돌파 강도" - Gemini

```python
def calculate_price_action_score(df: pd.DataFrame) -> float:
    """
    가격 행동 점수 계산 (0-45점)

    평가 기준:
    - 밴드 돌파 강도 (얼마나 강하게 돌파했는가)
    - 캔들 패턴 (양봉 여부, 몸통 크기)
    - 돌파 후 지지 여부
    """
    close = df["Close"].iloc[-1]
    open_price = df["Open"].iloc[-1]
    high = df["High"].iloc[-1]
    bb_upper = df["BB_Upper"].iloc[-1]
    bb_middle = df["BB_Middle"].iloc[-1]

    score = 0.0

    # 1. 돌파 강도 (0-20점)
    # 밴드 폭 대비 돌파 거리
    band_width = bb_upper - bb_middle
    breakout_distance = close - bb_upper

    if breakout_distance > 0 and band_width > 0:
        breakout_ratio = breakout_distance / band_width
        score += min(20.0, breakout_ratio * 40.0)  # 50% 돌파시 20점 만점

    # 2. 양봉 여부 (0-15점)
    if close > open_price:
        candle_body = close - open_price
        candle_range = high - df["Low"].iloc[-1]

        if candle_range > 0:
            body_ratio = candle_body / candle_range
            score += body_ratio * 15.0  # 몸통 비율에 따라

    # 3. 종가 위치 (0-10점)
    # 고가 근처에서 마감했는가?
    if high > df["Low"].iloc[-1]:
        close_position = (close - df["Low"].iloc[-1]) / (high - df["Low"].iloc[-1])
        score += close_position * 10.0  # 고가 마감시 10점

    return min(45.0, score)
```

### 3.5 Stage 2 통합 점수 계산

```python
def calculate_stage2_score(df: pd.DataFrame) -> dict:
    """
    Stage 2 방향성 점수 계산

    Returns:
        {
            "rsi_score": float,
            "macd_score": float,
            "price_action_score": float,
            "total_score": float
        }
    """
    rsi_score = calculate_rsi_score_v2(df, direction="LONG")
    macd_score = calculate_macd_score_v2(df)
    price_action_score = calculate_price_action_score(df)

    total_score = rsi_score + macd_score + price_action_score

    return {
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "price_action_score": price_action_score,
        "total_score": total_score
    }
```

---

## 4. 통합 알고리즘 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    볼린저 밴드 돌파 감지                        │
│              (Close > BB_Upper)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 STAGE 1: 필수 필터                           │
├─────────────────────────────────────────────────────────────┤
│  [Gate 1] 스퀴즈 품질: BB_Width == min(최근 20일)             │
│  [Gate 2] 거래량 분출: Volume > Volume_MA * 1.5              │
├─────────────────────────────────────────────────────────────┤
│  ❌ 하나라도 실패 → 신호 무시 (점수 계산 안 함)                  │
│  ✅ 모두 통과 → Stage 2로 진행                                │
└─────────────────────┬───────────────────────────────────────┘
                      │ Pass
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 STAGE 2: 방향성 점수                          │
├─────────────────────────────────────────────────────────────┤
│  RSI 점수 (0-25점)                                           │
│    - 50선 돌파: +15점                                        │
│    - 과매도 탈출: +10점                                       │
│    - 과매수 근접: -5점                                        │
├─────────────────────────────────────────────────────────────┤
│  MACD 점수 (0-30점)                                          │
│    - 골든크로스 상태: +15점                                    │
│    - 히스토그램 양수: +10점                                    │
│    - 히스토그램 상승: +5점                                     │
├─────────────────────────────────────────────────────────────┤
│  Price Action 점수 (0-45점)                                  │
│    - 돌파 강도: 0-20점                                        │
│    - 양봉/몸통 크기: 0-15점                                   │
│    - 종가 위치: 0-10점                                        │
├─────────────────────────────────────────────────────────────┤
│  총점: 0-100점                                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              임계값 확인 (기본 60점)                           │
├─────────────────────────────────────────────────────────────┤
│  총점 >= 60점 → ✅ 매수 신호 생성                              │
│  총점 < 60점  → ❌ 신호 필터링                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 반전 매매 (Reversal) 전략 추가

> "밴드 이탈 후 다시 회귀하는 시점의 RSI 다이버전스를 점수 항목에 넣는 것이 훨씬 논리적" - Gemini

### 5.1 RSI 다이버전스 감지

```python
def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 10) -> str:
    """
    RSI 다이버전스 감지

    Returns:
        "bullish": 가격 저점 하락, RSI 저점 상승 (상승 다이버전스)
        "bearish": 가격 고점 상승, RSI 고점 하락 (하락 다이버전스)
        "none": 다이버전스 없음
    """
    price_data = df["Close"].iloc[-lookback:]
    rsi_data = df["RSI"].iloc[-lookback:]

    # 저점 찾기
    price_lows = price_data.nsmallest(2)
    rsi_at_price_lows = rsi_data.iloc[price_data.nsmallest(2).index - df.index[-lookback]]

    # 상승 다이버전스: 가격 저점↓, RSI 저점↑
    if price_lows.iloc[-1] < price_lows.iloc[0]:  # 가격 저점 하락
        if rsi_at_price_lows.iloc[-1] > rsi_at_price_lows.iloc[0]:  # RSI 저점 상승
            return "bullish"

    # 고점 찾기 (하락 다이버전스용)
    price_highs = price_data.nlargest(2)
    rsi_at_price_highs = rsi_data.iloc[price_data.nlargest(2).index - df.index[-lookback]]

    # 하락 다이버전스: 가격 고점↑, RSI 고점↓
    if price_highs.iloc[-1] > price_highs.iloc[0]:
        if rsi_at_price_highs.iloc[-1] < rsi_at_price_highs.iloc[0]:
            return "bearish"

    return "none"
```

### 5.2 밴드 회귀 전략

```python
def check_band_reversion_signal(df: pd.DataFrame) -> dict:
    """
    밴드 이탈 후 회귀 신호 감지 (반전 매매용)

    조건:
    1. 최근 N일 내 하단 밴드 이탈 발생
    2. 현재 밴드 내로 회귀
    3. RSI 상승 다이버전스 확인
    """
    close = df["Close"].iloc[-1]
    bb_lower = df["BB_Lower"].iloc[-1]
    bb_middle = df["BB_Middle"].iloc[-1]

    # 최근 5일 내 하단 이탈 여부
    recent_below_lower = (df["Close"].iloc[-5:] < df["BB_Lower"].iloc[-5:]).any()

    # 현재 밴드 내 회귀
    currently_in_band = bb_lower <= close <= bb_middle

    # RSI 다이버전스
    divergence = detect_rsi_divergence(df)

    if recent_below_lower and currently_in_band and divergence == "bullish":
        return {
            "signal": "REVERSAL_BUY",
            "confidence": 70,  # 반전 매매는 높은 기본 신뢰도
            "reason": "band_reversion_with_bullish_divergence"
        }

    return {"signal": None}
```

---

## 6. 과적합 방지 (Overfitting Prevention)

### 6.1 Walk-Forward Analysis

> "2023년 데이터로 최적화하고 2024년 데이터로 검증하는 방식을 반복"

```python
def walk_forward_backtest(
    stock_codes: list[str],
    start_date: str,
    end_date: str,
    train_months: int = 12,
    test_months: int = 3
) -> dict:
    """
    Walk-Forward 백테스트

    Args:
        train_months: 학습 기간 (월)
        test_months: 검증 기간 (월)

    Returns:
        {
            "periods": [...],
            "average_train_winrate": float,
            "average_test_winrate": float,
            "degradation": float  # 학습 대비 테스트 성능 저하율
        }
    """
    # 구현 예시
    results = []
    current = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    while current + pd.DateOffset(months=train_months + test_months) <= end:
        train_start = current
        train_end = current + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)

        # 학습 기간에서 최적 파라미터 찾기
        best_params = optimize_parameters(train_start, train_end)

        # 테스트 기간에서 검증
        test_result = backtest_with_params(test_start, test_end, best_params)

        results.append({
            "train_period": f"{train_start} ~ {train_end}",
            "test_period": f"{test_start} ~ {test_end}",
            "train_winrate": best_params["winrate"],
            "test_winrate": test_result["winrate"]
        })

        current += pd.DateOffset(months=test_months)

    return aggregate_results(results)
```

### 6.2 변수 강건성 테스트 (Robustness Check)

> "가중치를 조금 바꿔도 수익률이 급격하게 변하지 않는 구간을 찾아야"

```python
def robustness_test(base_params: dict, variation_range: float = 0.2) -> dict:
    """
    파라미터 변동에 대한 강건성 테스트

    Args:
        base_params: 기본 파라미터 (예: {"rsi_weight": 25, "macd_weight": 30})
        variation_range: 변동 범위 (0.2 = ±20%)

    Returns:
        {
            "is_robust": bool,
            "stability_score": float,  # 0-100, 높을수록 안정
            "sensitive_params": [...]  # 민감한 파라미터 목록
        }
    """
    results = []

    for param_name, base_value in base_params.items():
        variations = [
            base_value * (1 - variation_range),
            base_value * (1 - variation_range/2),
            base_value,
            base_value * (1 + variation_range/2),
            base_value * (1 + variation_range)
        ]

        param_results = []
        for var_value in variations:
            test_params = base_params.copy()
            test_params[param_name] = var_value
            result = backtest_with_params(test_params)
            param_results.append(result["annual_return"])

        # 변동 계수 계산
        cv = np.std(param_results) / np.mean(param_results)
        results.append({
            "param": param_name,
            "coefficient_of_variation": cv,
            "is_sensitive": cv > 0.15  # 15% 이상 변동시 민감
        })

    return {
        "is_robust": all(not r["is_sensitive"] for r in results),
        "stability_score": 100 * (1 - np.mean([r["coefficient_of_variation"] for r in results])),
        "sensitive_params": [r["param"] for r in results if r["is_sensitive"]]
    }
```

---

## 7. 구현 우선순위

| 순위 | 항목 | 예상 효과 | 난이도 |
|------|------|----------|--------|
| 1 | Stage 1 필수 필터 (거래량 Gate) | 승률 급상승 | 낮음 |
| 2 | 스퀴즈 품질 필터 (최저치 확인) | 가짜 돌파 감소 | 낮음 |
| 3 | Price Action 점수 (신규) | 돌파 품질 평가 | 중간 |
| 4 | RSI 방향성 점수 (개선) | 타이밍 최적화 | 중간 |
| 5 | MACD 기울기 추가 | 가속도 감지 | 낮음 |
| 6 | RSI 다이버전스 (반전) | 추가 기회 발굴 | 높음 |
| 7 | Walk-Forward 백테스트 | 과적합 방지 | 높음 |
| 8 | 강건성 테스트 | 파라미터 안정성 | 중간 |

---

## 8. 성공 지표 (v2)

| 지표 | v1 목표 | v2 목표 | 비고 |
|------|---------|---------|------|
| 승률 | 55-60% | **70-75%** | MACD + Stage1 필터 |
| 거래당 평균 수익 | 1.0% | **1.4%** | 고품질 진입만 |
| 연간 수익률 | +8% | **+15~20%** | 복합 효과 |
| 최대 낙폭 (MDD) | 20% | **15%** | 손절 최적화 |
| 거래 횟수 (연간) | 200회 | **100회** | 50% 감소 |
| 샤프 비율 | 1.0 | **1.5** | 위험 대비 수익 |

---

## 9. 참고: v1 → v2 마이그레이션

### 9.1 코드 변경 요약

```python
# v1: signal_scanner.py의 scan_for_buy_signals()

# 기존
if price_breakout and (was_in_squeeze or bandwidth_expanding):
    confidence = calculate_confidence_score(...)
    if confidence >= self.confidence_threshold:
        # 신호 생성

# v2: 하이브리드 방식
if price_breakout:
    # Stage 1: 필수 필터
    passed, reason = pass_stage1_filters(df)
    if not passed:
        continue  # 점수 계산 없이 스킵

    # Stage 2: 방향성 점수
    scores = calculate_stage2_score(df)
    if scores["total_score"] >= self.confidence_threshold:
        # 신호 생성
```

### 9.2 설정 파라미터 추가

```python
# config.py (신규)
SIGNAL_CONFIG_V2 = {
    # Stage 1 필터
    "squeeze_lookback": 20,           # 스퀴즈 확인 기간
    "squeeze_tolerance": 0.05,        # 최저치 허용 오차 (5%)
    "volume_gate_threshold": 1.5,     # 거래량 필수 배수

    # Stage 2 점수
    "rsi_weight": 25,
    "macd_weight": 30,
    "price_action_weight": 45,

    # 임계값
    "confidence_threshold": 60,

    # 과적합 방지
    "walk_forward_train_months": 12,
    "walk_forward_test_months": 3,
}
```

---

## 10. 결론

Gemini 리뷰의 핵심 제안을 수용하여:

1. **거래량을 '입장권'으로** 사용 - 필수 필터로 승격
2. **스퀴즈 품질 강화** - 최저 변동성 확인
3. **Price Action 추가** - 돌파 강도 정량화
4. **방향성 기반 RSI** - 단순 수치가 아닌 전환 감지
5. **과적합 방지** - Walk-Forward + 강건성 테스트

이를 통해 v1 대비 **승률 15%p 향상**, **거래 횟수 50% 감소**, **샤프 비율 0.5 향상**을 목표로 한다.

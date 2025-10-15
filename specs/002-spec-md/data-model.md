# Data Model: 볼린저 밴드 스퀴즈 전략 개선 - 보조 지표 추가

**Feature**: 002-spec-md | **Date**: 2025-10-15
**Purpose**: Define entities, their attributes, relationships, and validation rules

---

## Entity 1: RSIIndicator

**Purpose**: RSI (Relative Strength Index) 모멘텀 지표 계산 및 과매수/과매도 판단

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `period` | int | > 0, ≤ 100, default=14 | RSI 계산 기간 (일수) |
| `overbought_threshold` | int | 50 ≤ x ≤ 100, default=70 | 과매수 판단 임계값 |
| `oversold_threshold` | int | 0 ≤ x ≤ 50, default=30 | 과매도 판단 임계값 |
| `values` | pandas.Series | 0 ≤ x ≤ 100 | 계산된 RSI 값 시계열 |

### Behavior

- `calculate(prices: pd.Series) -> pd.Series`: Wilder's smoothing 방식으로 RSI 계산
- `is_overbought(date: datetime) -> bool`: 특정 시점의 과매수 여부 판단
- `is_oversold(date: datetime) -> bool`: 특정 시점의 과매도 여부 판단
- `validate_data(prices: pd.Series) -> bool`: 최소 기간(period+1) 데이터 존재 확인

### Validation Rules

- `period` < 데이터 길이 (최소 15일 필요 for period=14)
- `overbought_threshold` > `oversold_threshold`
- 계산된 `values`는 항상 0~100 범위 내 (NaN 제외)

### State Transitions

```
[Not Calculated] --calculate()--> [Calculated]
[Calculated] --is_overbought()--> [Overbought Check Result]
[Calculated] --is_oversold()--> [Oversold Check Result]
```

### Example Usage

```python
rsi = RSIIndicator(period=14, overbought_threshold=70)
rsi.calculate(close_prices)
if rsi.is_overbought(datetime(2024, 10, 15)):
    # 과매수 청산 신호 생성
```

---

## Entity 2: MACDIndicator

**Purpose**: MACD (Moving Average Convergence Divergence) 추세 확인 지표

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `fast_period` | int | > 0, default=12 | 빠른 EMA 기간 |
| `slow_period` | int | > fast_period, default=26 | 느린 EMA 기간 |
| `signal_period` | int | > 0, default=9 | 시그널 라인 EMA 기간 |
| `macd_line` | pandas.Series | float | MACD 라인 (fast EMA - slow EMA) |
| `signal_line` | pandas.Series | float | 시그널 라인 (MACD 라인의 EMA) |
| `histogram` | pandas.Series | float | 히스토그램 (macd_line - signal_line) |

### Behavior

- `calculate(prices: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]`: MACD 라인, 시그널 라인, 히스토그램 계산
- `is_bullish(date: datetime) -> bool`: MACD선 > 시그널선 AND 히스토그램 > 0 확인
- `is_bearish(date: datetime) -> bool`: MACD선 < 시그널선 확인 (데드크로스)
- `validate_data(prices: pd.Series) -> bool`: 최소 기간(slow_period+1) 데이터 존재 확인

### Validation Rules

- `slow_period` > `fast_period` (필수)
- `slow_period` < 데이터 길이 (최소 27일 필요 for slow_period=26)
- 모든 기간 값 > 0

### State Transitions

```
[Not Calculated] --calculate()--> [Calculated]
[Calculated] --is_bullish()--> [Golden Cross Detected]
[Calculated] --is_bearish()--> [Death Cross Detected]
```

### Example Usage

```python
macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)
macd.calculate(close_prices)
if macd.is_bullish(datetime(2024, 10, 15)):
    # 상승 추세 확인, 매수 신호 강화
```

---

## Entity 3: ATRIndicator

**Purpose**: ATR (Average True Range) 변동성 지표 및 동적 손절가 계산

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `period` | int | > 0, ≤ 100, default=14 | ATR 계산 기간 |
| `multiplier` | float | > 0, ≤ 10, default=2.0 | 손절가 계산 배수 |
| `values` | pandas.Series | ≥ 0 | 계산된 ATR 값 시계열 |

### Behavior

- `calculate(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series`: True Range의 EMA 계산
- `calculate_stop_loss(entry_price: Decimal, date: datetime) -> Decimal`: 진입가 - (ATR × multiplier)
- `validate_data(high, low, close) -> bool`: 데이터 길이 및 유효성 확인

### Validation Rules

- 모든 입력 Series 길이 동일
- `high` ≥ `low` for all dates
- `close` between `low` and `high` (허용 오차 5%)
- `period` < 데이터 길이

### State Transitions

```
[Not Calculated] --calculate()--> [Calculated]
[Calculated] --calculate_stop_loss()--> [Stop Loss Price]
```

### Example Usage

```python
atr = ATRIndicator(period=14, multiplier=2.0)
atr.calculate(high_prices, low_prices, close_prices)
stop_price = atr.calculate_stop_loss(entry_price=Decimal('75000'), date=datetime(2024, 10, 15))
# stop_price = 75000 - (ATR(14) * 2)
```

---

## Entity 4: VolumeFilter

**Purpose**: 거래량 기반 신호 필터링 (거짓 돌파 제거)

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `window_days` | int | > 0, ≤ 252, default=20 | 평균 거래량 계산 기간 |
| `multiplier` | float | > 0, ≤ 10, default=1.5 | 임계값 배수 |
| `average_volume` | pandas.Series | > 0 | Rolling 평균 거래량 |

### Behavior

- `calculate_average(volume: pd.Series) -> pd.Series`: Rolling mean 계산
- `passes_filter(date: datetime, volume: pd.Series) -> bool`: 현재 거래량 ≥ 평균 × multiplier 확인
- `validate_data(volume: pd.Series) -> bool`: 음수 거래량 없음, 최소 기간 데이터 확인

### Validation Rules

- 거래량 ≥ 0 for all dates (0 허용은 데이터 누락 처리)
- `window_days` < 데이터 길이

### State Transitions

```
[Not Calculated] --calculate_average()--> [Calculated]
[Calculated] --passes_filter()--> [Pass/Fail Result]
```

### Example Usage

```python
volume_filter = VolumeFilter(window_days=20, multiplier=1.5)
volume_filter.calculate_average(volume_series)
if volume_filter.passes_filter(datetime(2024, 10, 15), volume_series):
    # 거래량 조건 충족, 진입 허용
```

---

## Entity 5: SignalConfidence

**Purpose**: 다중 지표 기반 신호 신뢰도 평가

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `base_score` | int | 0 ≤ x ≤ 100, default=25 | 볼린저 밴드 돌파 기본 점수 |
| `volume_score` | int | 0 ≤ x ≤ 100, default=25 | 거래량 필터 통과 시 점수 |
| `rsi_score` | int | 0 ≤ x ≤ 100, default=20 | RSI 필터 통과 시 점수 |
| `macd_score` | int | 0 ≤ x ≤ 100, default=30 | MACD 필터 통과 시 점수 |
| `threshold` | int | 0 ≤ x ≤ 100, default=60 | 진입 허용 최소 점수 |

### Behavior

- `calculate_score(has_volume: bool, has_rsi: bool, has_macd: bool) -> int`: 각 필터 통과 여부에 따라 점수 합산
- `should_enter(score: int) -> bool`: score ≥ threshold 확인
- `get_score_breakdown() -> dict[str, int]`: 각 조건별 기여 점수 반환

### Validation Rules

- `base_score` + `volume_score` + `rsi_score` + `macd_score` ≤ 100
- 모든 점수 ≥ 0
- `threshold` ≤ (최대 가능 점수)

### State Transitions

```
[FilterResults] --calculate_score()--> [Score Calculated]
[Score Calculated] --should_enter()--> [Entry Decision (boolean)]
```

### Example Usage

```python
confidence = SignalConfidence(threshold=60)
score = confidence.calculate_score(
    has_volume=True,  # +25
    has_rsi=True,     # +20
    has_macd=False    # +0
)
# score = 25 (base) + 25 + 20 = 70
if confidence.should_enter(score):
    # 신뢰도 60점 이상, 진입 허용
```

---

## Entity 6: EnhancedSignal (extends existing Signal)

**Purpose**: 기존 매매 신호에 보조 지표 정보 및 신뢰도 점수 추가

### Attributes (in addition to base Signal)

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `confidence_score` | int | 0 ≤ x ≤ 100 | 신호 신뢰도 점수 |
| `filters_passed` | dict[str, bool] | keys: volume, rsi, macd | 각 필터 통과 여부 |
| `dynamic_stop_loss` | Optional[Decimal] | > 0 if set | ATR 기반 손절가 (None이면 고정 손절) |
| `indicator_values` | dict[str, float] | keys: rsi, macd_line, macd_signal, atr | 신호 생성 시점의 지표 값 |

### Relationships

- **Has-a**: RSIIndicator, MACDIndicator, ATRIndicator 값 참조
- **Uses**: VolumeFilter, SignalConfidence for evaluation
- **Extends**: Base Signal 엔티티 (date, stock_code, signal_type, reason, price, bollinger_values)

### Behavior

- Inherits from base Signal
- `to_log_dict() -> dict`: 기존 Signal 필드 + 신규 필드 포함 로그 출력
- `validate() -> bool`: 모든 필수 필드 존재 및 제약 조건 확인

### Validation Rules

- All base Signal validation rules apply
- `confidence_score` must be calculated (not None)
- `filters_passed` keys must match enabled filters
- If `dynamic_stop_loss` is set, must be < entry price

### Example Usage

```python
enhanced_signal = EnhancedSignal(
    date=datetime(2024, 10, 15),
    stock_code='005930',
    signal_type='BUY',
    reason='squeeze_expansion_buy_conf_70',
    price=Decimal('75000'),
    bollinger_values={'upper': 73000, 'middle': 70000, 'lower': 67000},
    confidence_score=70,
    filters_passed={'volume': True, 'rsi': True, 'macd': False},
    dynamic_stop_loss=Decimal('73500'),  # ATR based
    indicator_values={'rsi': 65, 'macd_line': 120, 'macd_signal': 100, 'atr': 750}
)
```

---

## Entity 7: EnhancedStrategyConfig (extends base config)

**Purpose**: 개선된 전략의 설정 옵션 통합 관리

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `volume_filter` | VolumeFilterConfig | - | 거래량 필터 설정 |
| `rsi` | RSIConfig | - | RSI 지표 설정 |
| `macd` | MACDConfig | - | MACD 지표 설정 |
| `atr` | ATRConfig | - | ATR 지표 설정 |
| `confidence_threshold` | int | 0 ≤ x ≤ 100 | 진입 허용 최소 신뢰도 |
| `use_dynamic_stop_loss` | bool | default=False | ATR 기반 손절매 사용 여부 |

### Nested Configs

**VolumeFilterConfig**:
- `enabled: bool`
- `window_days: int` (default=20)
- `multiplier: float` (default=1.5)

**RSIConfig**:
- `enabled: bool`
- `period: int` (default=14)
- `overbought: int` (default=70)
- `oversold: int` (default=30)

**MACDConfig**:
- `enabled: bool`
- `fast_period: int` (default=12)
- `slow_period: int` (default=26, must be > fast_period)
- `signal_period: int` (default=9)

**ATRConfig**:
- `enabled: bool`
- `period: int` (default=14)
- `multiplier: float` (default=2.0)

### Validation Rules

- At least one filter must be enabled (volume, rsi, or macd)
- MACD slow_period > fast_period
- RSI overbought > oversold
- All period values > 0 and ≤ 252 (trading days per year)
- All multipliers > 0 and ≤ 10

### Example YAML

```yaml
volume_filter:
  enabled: true
  window_days: 20
  multiplier: 1.5

rsi:
  enabled: true
  period: 14
  overbought: 70
  oversold: 30

macd:
  enabled: true
  fast_period: 12
  slow_period: 26
  signal_period: 9

atr:
  enabled: false  # Phase 4에서 활성화
  period: 14
  multiplier: 2.0

confidence_threshold: 60
use_dynamic_stop_loss: false
```

---

## Relationships Diagram

```
EnhancedStrategyConfig
    ├── contains VolumeFilterConfig
    ├── contains RSIConfig
    ├── contains MACDConfig
    └── contains ATRConfig

EnhancedSignal (extends Signal)
    ├── uses VolumeFilter.passes_filter()
    ├── uses RSIIndicator.is_overbought()
    ├── uses MACDIndicator.is_bullish()
    ├── uses ATRIndicator.calculate_stop_loss()
    └── uses SignalConfidence.calculate_score()

SignalConfidence
    ├── receives results from VolumeFilter
    ├── receives results from RSIIndicator
    └── receives results from MACDIndicator
```

---

## Data Validation Matrix

| Entity | Validation Trigger | Failure Behavior |
|--------|-------------------|------------------|
| RSIIndicator | Before calculate() | Raise ValueError with message |
| MACDIndicator | Before calculate() | Raise ValueError with message |
| ATRIndicator | Before calculate() | Raise ValueError with message |
| VolumeFilter | Before calculate_average() | Raise ValueError with message |
| SignalConfidence | On initialization | Raise ValidationError (pydantic) |
| EnhancedSignal | On creation | Raise ValidationError (pydantic) |
| EnhancedStrategyConfig | On YAML load | Raise ValidationError (pydantic) with field details |

---

## Storage Considerations

### In-Memory (during backtest)
- All indicator calculations: pandas Series (efficient vectorization)
- SignalConfidence: singleton instance per strategy run
- EnhancedSignal: list of dataclass instances

### Persistent Storage

**SQLite (data/logs/backtest.db)**:
- EnhancedSignal → trades table with new columns:
  - `confidence_score INTEGER`
  - `volume_filter_passed BOOLEAN`
  - `rsi_filter_passed BOOLEAN`
  - `macd_filter_passed BOOLEAN`
  - `dynamic_stop_loss DECIMAL`

**Excel (results/*.xlsx)**:
- One row per trade with all EnhancedSignal fields
- New columns for Phase별 비교 (before/after metrics)

**YAML (config/*.yaml)**:
- EnhancedStrategyConfig serialized as human-readable YAML

---

## Migration from Existing Entities

### Backward Compatibility

**Signal → EnhancedSignal**:
- All existing Signal fields preserved
- New fields Optional (defaults to None/empty)
- Old backtests still readable

**Config → EnhancedStrategyConfig**:
- Existing config fields unchanged
- New sections optional (default disabled)
- Old YAML files still loadable

### Migration Strategy

1. Add new columns to trades table (NULL allowed)
2. Update Signal to EnhancedSignal incrementally
3. Old signals automatically upgraded (new fields = default)
4. No breaking changes to existing tests

---

## Summary

**Total Entities**: 7 (4 new indicators, 1 filter, 1 confidence evaluator, 1 enhanced signal)
**Key Relationships**: EnhancedSignal aggregates results from all 6 other entities
**Validation Strategy**: Fail-fast with clear error messages (Constitution VII)
**Storage**: Pandas Series (runtime) + SQLite/Excel (persistent)
**Backward Compatibility**: Full (existing code unaffected)

# Data Source API Contracts

**Version**: 1.0
**Date**: 2025-10-11
**Purpose**: Define expected API contracts for external data sources (FinanceDataReader, pykrx) to enable contract testing and validation.

---

## 1. FinanceDataReader API Contract

### 1.1 Stock Data Fetch

**Function**: `FinanceDataReader.DataReader(symbol, start, end)`

**Input**:
- `symbol` (str): 6-digit Korean stock code (e.g., "005930")
- `start` (str | date): Start date in "YYYY-MM-DD" format
- `end` (str | date): End date in "YYYY-MM-DD" format

**Expected Output**: pandas DataFrame with DatetimeIndex and columns:
```python
{
    'Open': float,    # Opening price (KRW)
    'High': float,    # Highest price (KRW)
    'Low': float,     # Lowest price (KRW)
    'Close': float,   # Closing price (KRW)
    'Volume': int,    # Number of shares traded
    'Change': float   # Daily change (may be present)
}
```

**Contract Assertions**:
```python
def test_finance_data_reader_contract():
    import FinanceDataReader as fdr
    import pandas as pd

    # Fetch data for Samsung (005930)
    df = fdr.DataReader('005930', '2024-01-01', '2024-01-31')

    # Assertions
    assert isinstance(df, pd.DataFrame)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
    assert (df[['Open', 'High', 'Low', 'Close', 'Volume']] > 0).all().all()
    assert (df['Low'] <= df['High']).all()
    assert len(df) > 0  # At least some trading days in January
```

**Error Scenarios**:
- Invalid stock code → Returns empty DataFrame or raises KeyError
- Future date range → Returns empty DataFrame
- Network error → Raises ConnectionError or Timeout

**Fallback Strategy**: If FinanceDataReader fails, retry with pykrx API.

---

## 2. pykrx API Contract

### 2.1 Stock Data Fetch

**Function**: `stock.get_market_ohlcv_by_date(fromdate, todate, ticker)`

**Input**:
- `fromdate` (str): Start date in "YYYYMMDD" format (note: no dashes)
- `todate` (str): End date in "YYYYMMDD" format
- `ticker` (str): 6-digit stock code (e.g., "005930")

**Expected Output**: pandas DataFrame with DatetimeIndex and columns:
```python
{
    '시가': int,    # Opening price (Korean column name)
    '고가': int,    # High price
    '저가': int,    # Low price
    '종가': int,    # Close price
    '거래량': int   # Volume
}
```

**Contract Assertions**:
```python
def test_pykrx_contract():
    from pykrx import stock
    import pandas as pd

    # Fetch data for Samsung (005930)
    df = stock.get_market_ohlcv_by_date("20240101", "20240131", "005930")

    # Assertions
    assert isinstance(df, pd.DataFrame)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert all(col in df.columns for col in ['시가', '고가', '저가', '종가', '거래량'])
    assert (df[['시가', '고가', '저가', '종가', '거래량']] > 0).all().all()
    assert len(df) > 0

    # Normalize column names to English
    df_normalized = df.rename(columns={
        '시가': 'Open',
        '고가': 'High',
        '저가': 'Low',
        '종가': 'Close',
        '거래량': 'Volume'
    })
    assert all(col in df_normalized.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
```

**Error Scenarios**:
- Invalid ticker → Raises ValueError or returns empty DataFrame
- Malformed date → Raises ValueError
- API rate limit → May block or raise HTTPError

**Normalization Required**: Column names are in Korean, must be translated to English for consistency with FinanceDataReader.

### 2.2 Trading Calendar

**Function**: `stock.get_market_trading_days(year, month)`

**Input**:
- `year` (int): Year (e.g., 2024)
- `month` (int): Month (1-12, optional)

**Expected Output**: List of datetime objects representing trading days
```python
[
    datetime.date(2024, 1, 2),
    datetime.date(2024, 1, 3),
    ...  # Excludes weekends and KRX holidays
]
```

**Contract Assertions**:
```python
def test_pykrx_trading_calendar():
    from pykrx import stock
    import datetime

    # Get January 2024 trading days
    days = stock.get_market_trading_days(2024, 1)

    # Assertions
    assert isinstance(days, list)
    assert all(isinstance(d, datetime.date) for d in days)
    assert len(days) > 15  # At least 15 trading days in a typical month
    # No weekends (Monday=0, Sunday=6)
    assert all(d.weekday() < 5 for d in days)
```

**Usage**: Compare fetched OHLCV data dates against trading calendar to detect missing days (data completeness check per FR-003).

---

## 3. Data Validation Contract

**Purpose**: Ensure fetched data meets quality standards before backtesting (FR-003, FR-004).

### 3.1 Completeness Validation

**Input**: DataFrame with OHLCV data, trading calendar
**Output**: Validation result (PASS/FAIL) + list of missing dates

**Contract**:
```python
def validate_data_completeness(df: pd.DataFrame, trading_calendar: List[date]) -> Tuple[bool, List[date]]:
    """
    Check if OHLCV data contains all expected trading days.

    Returns:
        (is_complete, missing_dates)
    """
    data_dates = set(df.index.date)
    expected_dates = set(trading_calendar)
    missing = expected_dates - data_dates

    return len(missing) == 0, sorted(missing)


def test_completeness_validation():
    # Assume df is fetched data, calendar is from pykrx
    is_complete, missing = validate_data_completeness(df, calendar)

    if not is_complete:
        raise ValueError(f"Missing {len(missing)} trading days: {missing[:5]}...")
```

**Failure Behavior**: Raise ValueError with missing dates, halt backtest per constitutional principle VII (defensive validation).

### 3.2 Outlier Detection

**Input**: DataFrame with OHLCV data
**Output**: Series of boolean flags (True = outlier)

**Contract**:
```python
def detect_price_outliers(df: pd.DataFrame, threshold_pct: float = 20.0) -> pd.Series:
    """
    Detect anomalous price movements (>20% change without volume confirmation).

    Returns:
        Boolean Series with True for outlier dates
    """
    daily_returns = df['Close'].pct_change() * 100
    volume_zscore = (df['Volume'] - df['Volume'].mean()) / df['Volume'].std()

    # Outlier: large price move without volume spike
    outliers = (daily_returns.abs() > threshold_pct) & (volume_zscore < 1)
    return outliers


def test_outlier_detection():
    # Create synthetic outlier (50% price jump, normal volume)
    test_data = pd.DataFrame({
        'Close': [100, 100, 150, 100],  # Day 2→3 is 50% jump
        'Volume': [1000, 1000, 1000, 1000]  # No volume spike
    })

    outliers = detect_price_outliers(test_data, threshold_pct=20)

    assert outliers.iloc[2] == True  # Day 3 flagged
    assert outliers.iloc[:2].sum() == 0  # Days 0-1 not flagged
```

**Behavior**: Flag outliers but proceed with data included (per FR-004: "warn and proceed"). User can review and exclude manually if needed.

---

## 4. Response Time Contract

**Performance Requirements** (from constitution):
- Data fetch (1 year, 1 stock): <2 seconds (network-dependent)
- Data validation (completeness + outliers): <100ms
- Total data pipeline (fetch + validate + cache): <3 seconds

**Contract Test**:
```python
def test_data_pipeline_performance(benchmark):
    def pipeline():
        # Fetch
        df = fdr.DataReader('005930', '2023-01-01', '2023-12-31')
        # Validate
        calendar = stock.get_market_trading_days(2023)
        is_complete, missing = validate_data_completeness(df, calendar)
        outliers = detect_price_outliers(df)
        # Cache (Parquet write)
        df.to_parquet('cache.parquet')
        return df

    result = benchmark(pipeline)
    assert benchmark.stats['mean'] < 3.0  # Must complete in <3s
```

---

## 5. Error Handling Contract

**All data source operations MUST handle these error scenarios**:

| Error Type | Expected Exception | Handling Strategy |
|------------|-------------------|-------------------|
| Invalid stock code | `ValueError` or empty DataFrame | Validate stock codes before API call (Pydantic) |
| Network timeout | `requests.exceptions.Timeout` | Retry 3 times with exponential backoff |
| API rate limit | `HTTPError 429` | Exponential backoff, fallback to pykrx if FDR fails |
| Empty response | Empty DataFrame | Raise ValueError("No data available for date range") |
| Malformed response | `KeyError`, `AttributeError` | Log error, raise ValueError with diagnostic info |
| Data type mismatch | `TypeError` | Pydantic schema validation catches, raise ValidationError |

**Contract Test Example**:
```python
def test_error_handling_invalid_stock_code():
    with pytest.raises(ValueError, match="No data available"):
        df = fdr.DataReader('999999', '2024-01-01', '2024-01-31')
        if df.empty:
            raise ValueError("No data available for stock code 999999")
```

---

## 6. Data Storage Contract (Parquet Cache)

**Purpose**: Persist fetched data to avoid redundant API calls (FR-005).

### 6.1 Cache Write

**Input**: DataFrame (OHLCV), stock_code, date_range
**Output**: Parquet file at `data/cache/{stock_code}_{start}_{end}.parquet`

**Contract**:
```python
def cache_stock_data(df: pd.DataFrame, stock_code: str, start: date, end: date):
    """Save fetched data to Parquet cache"""
    import pyarrow.parquet as pq

    filename = f"data/cache/{stock_code}_{start}_{end}.parquet"
    df.to_parquet(filename, engine='pyarrow', compression='snappy')


def test_parquet_cache_write_read():
    # Write
    cache_stock_data(df, '005930', date(2024, 1, 1), date(2024, 12, 31))

    # Read
    cached = pd.read_parquet('data/cache/005930_2024-01-01_2024-12-31.parquet')

    # Assertions
    assert cached.equals(df)  # Exact roundtrip
    assert isinstance(cached.index, pd.DatetimeIndex)
```

### 6.2 Cache Validation

**Before using cached data, validate it's still fresh and complete**:

```python
def is_cache_valid(filepath: str, expected_end_date: date) -> bool:
    """Check if cached file is up-to-date"""
    from pathlib import Path
    import datetime

    if not Path(filepath).exists():
        return False

    # Cache is valid if file modified within last 7 days
    # (allows for weekend/holiday gaps)
    mod_time = datetime.datetime.fromtimestamp(Path(filepath).stat().st_mtime)
    age_days = (datetime.datetime.now() - mod_time).days

    return age_days < 7
```

---

## Summary

All external API contracts are testable via pytest contract tests. These tests run against real APIs (not mocks) to verify integration stability. If any contract is violated (breaking API changes), tests fail immediately, preventing silent data corruption.

**Contract Test Suite Location**: `tests/contract/test_data_sources.py`

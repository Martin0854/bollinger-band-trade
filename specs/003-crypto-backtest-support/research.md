# Technical Research: Cryptocurrency Backtesting Support

**Feature**: 003-crypto-backtest-support | **Date**: 2025-10-17
**Purpose**: Document technical decisions and alternatives evaluated for adding cryptocurrency market support

## Research Areas

### 1. Cryptocurrency Data Provider Selection

**Decision**: Use `python-binance` library for Binance API access

**Rationale**:
- **Official support**: Maintained by Binance community with good documentation
- **No API key required**: Public OHLCV endpoints (Klines) don't need authentication
- **Rate limits**: 1200 requests/minute sufficient for backtest needs
- **Timezone handling**: Returns UTC timestamps (critical for 24/7 markets)
- **Proven reliability**: Widely used in crypto trading communities

**Alternatives Considered**:

1. **CCXT (CryptoCurrency eXchange Trading Library)**
   - Pros: Unified interface for 100+ exchanges, easy to add more exchanges later
   - Cons: Heavier dependency, slower performance, overkill for single-exchange needs
   - Rejected because: Project only needs Binance initially; can add CCXT later if multi-exchange support needed

2. **CoinGecko API**
   - Pros: Free, no API key, historical data available
   - Cons: Rate limit only 50 req/min, less reliable for high-frequency data
   - Rejected because: Rate limits too restrictive for batch backtests

3. **Direct REST API calls (requests library)**
   - Pros: No extra dependency, full control
   - Cons: Need to implement retry logic, error handling, pagination manually
   - Rejected because: Reinventing the wheel, python-binance provides this

**Implementation Notes**:
```python
# python-binance Klines endpoint example
from binance.client import Client
client = Client()  # No API key needed for public data
klines = client.get_historical_klines(
    "BTCUSDT",
    Client.KLINE_INTERVAL_1DAY,
    start_str="1 Jan, 2023",
    end_str="1 Jan, 2024"
)
# Returns: [[timestamp, open, high, low, close, volume, ...], ...]
```

---

### 2. Fractional Quantity Handling

**Decision**: Use Python's `Decimal` type for cryptocurrency quantities

**Rationale**:
- **Precision**: Decimal provides arbitrary precision (vs float's IEEE 754 rounding errors)
- **Financial accuracy**: Critical for crypto (BTC has 8 decimals, ETH has 18)
- **Existing pattern**: Project already uses Decimal for prices in `Trade` model
- **Type safety**: Pydantic supports Decimal validation

**Alternatives Considered**:

1. **Keep integer, multiply by 10^8 (satoshi units)**
   - Pros: Fast integer math, no floating point issues
   - Cons: Confusing API (users think in BTC not satoshis), unit conversion everywhere
   - Rejected because: Poor UX, error-prone conversions

2. **Use float**
   - Pros: Simple, Python native
   - Cons: Rounding errors accumulate (0.1 + 0.2 ≠ 0.3), unsuitable for finance
   - Rejected because: Unacceptable for financial calculations

**Migration Impact**:
- `Trade.quantity`: `int` → `Decimal`
- Database schema: `INTEGER` → `REAL` for quantity column
- Risk calculations: Update `calculate_trade_value()` to handle Decimal

**Precision Configuration**:
```python
from decimal import Decimal, getcontext
getcontext().prec = 28  # Support up to 28 decimal places
```

---

### 3. Database Schema Migration Strategy

**Decision**: Use runtime schema detection + ALTER TABLE for backward-compatible migration

**Rationale**:
- **Non-destructive**: Existing stock data preserved
- **Gradual migration**: No need to convert all data at once
- **Backward compatible**: Old code can still read new schema (with defaults)

**Alternatives Considered**:

1. **Alembic (migration framework)**
   - Pros: Version-controlled migrations, rollback support
   - Cons: Heavy dependency, overkill for simple schema changes
   - Rejected because: Project doesn't use Alembic yet, simple ALTER TABLE sufficient

2. **Create new tables (trade_log_v2)**
   - Pros: Zero risk to existing data
   - Cons: Duplication, complex query logic (UNION both tables)
   - Rejected because: Unnecessary complexity

**Migration Plan**:
```sql
-- Check if migration needed
PRAGMA table_info(trade_log);

-- Add new columns with defaults
ALTER TABLE trade_log ADD COLUMN market_type TEXT DEFAULT 'stock';
ALTER TABLE trade_log ADD COLUMN symbol TEXT;  -- Will copy from stock_code
UPDATE trade_log SET symbol = stock_code WHERE symbol IS NULL;

-- quantity stays as REAL (SQLite doesn't enforce types strictly)
-- Existing INTEGER values read as REAL automatically

-- Same for squeeze_events table
ALTER TABLE squeeze_events ADD COLUMN market_type TEXT DEFAULT 'stock';
ALTER TABLE squeeze_events ADD COLUMN symbol TEXT;
UPDATE squeeze_events SET symbol = stock_code WHERE symbol IS NULL;
```

**Backward Compatibility**:
- `stock_code` column kept (not dropped) for old code
- `market_type` defaults to 'stock' for existing rows
- `symbol` column populated from `stock_code` initially

---

### 4. Provider Abstraction Pattern

**Decision**: Use Abstract Base Class (ABC) with factory pattern

**Rationale**:
- **Pythonic**: ABC is standard Python pattern for interfaces
- **Type checking**: mypy can verify implementations
- **Extensibility**: Easy to add more providers (Upbit, Coinbase) later
- **Testability**: Mock providers for unit tests

**Alternatives Considered**:

1. **Protocol (PEP 544 structural subtyping)**
   - Pros: More flexible (duck typing), no inheritance needed
   - Cons: Less explicit, harder to discover implementations
   - Rejected because: Explicit ABC clearer for this use case

2. **No abstraction (if/else in engine)**
   - Pros: Simple, no extra files
   - Cons: Violates Open/Closed principle, hard to test, unmaintainable
   - Rejected because: Unacceptable code quality

**Interface Design**:
```python
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Returns DataFrame with columns: Open, High, Low, Close, Volume"""
        pass

    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """Returns True if symbol format valid for this market"""
        pass

    @abstractmethod
    def get_market_type(self) -> str:
        """Returns 'stock' or 'crypto'"""
        pass
```

**Factory Implementation**:
```python
class DataProviderFactory:
    @staticmethod
    def create_provider(market_type: str, **kwargs) -> MarketDataProvider:
        if market_type == "stock":
            return YahooFinanceStockProvider()
        elif market_type == "crypto":
            return BinanceCryptoProvider(**kwargs)
        else:
            raise ValueError(f"Unknown market_type: {market_type}")
```

---

### 5. Configuration Model Extension

**Decision**: Add optional `CryptoSpecificConfig` with Pydantic discriminated union pattern

**Rationale**:
- **Type safety**: Pydantic validates crypto_config only when market_type='crypto'
- **Backward compatible**: Existing configs don't need crypto_config
- **Clear separation**: Crypto settings isolated from stock settings

**Alternatives Considered**:

1. **Flat config (all fields at root level)**
   - Pros: Simpler YAML
   - Cons: Unclear which fields apply to which market, validation complex
   - Rejected because: Poor separation of concerns

2. **Separate config classes (StockConfig, CryptoConfig)**
   - Pros: Complete separation
   - Cons: Code duplication (date_range, strategy params shared)
   - Rejected because: Most config is shared, only fees/minimums differ

**Configuration Structure**:
```python
class CryptoSpecificConfig(BaseModel):
    trading_fee_percent: float = 0.1  # Binance default
    min_order_value_usdt: float = 10.0
    quote_currency: str = "USDT"

class BacktestConfiguration(BaseModel):
    market_type: str = "stock"  # "stock" or "crypto"
    symbols: List[str]  # Replaces "stocks"
    # ... shared fields (date_range, bollinger_period, etc.)

    crypto_config: Optional[CryptoSpecificConfig] = None

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str], info) -> List[str]:
        market_type = info.data.get('market_type', 'stock')
        if market_type == "stock":
            # Validate 6-digit stock codes
        elif market_type == "crypto":
            # Validate crypto pair format
```

---

### 6. 24/7 Market Handling

**Decision**: No code changes needed - existing indicator calculations are market-agnostic

**Rationale**:
- **Bollinger Bands**: Uses rolling window (e.g., 20 periods) - works on any continuous data
- **RSI/MACD**: Period-based calculations, no calendar assumptions
- **Volume Filter**: Compares current vs historical volume, no time-of-week logic
- **Key insight**: Crypto's 24/7 nature is handled at data level (no gaps), not calculation level

**What Changes**:
- Data timestamps: Must be timezone-aware (UTC) for crypto
- Date range iteration: Will include Sat/Sun dates (with actual data, not NaN)

**What Doesn't Change**:
- Indicator code in `src/indicators/`
- Backtest engine loop logic
- Signal generation

**Verification Strategy**:
- Integration test: Run backtest on crypto data spanning weekend
- Assert: Trades can occur on Saturday/Sunday
- Assert: Bollinger Band windows include weekend candles

---

### 7. Testing Strategy

**Decision**: Three-layer testing approach (unit, integration, contract)

**Test Coverage Plan**:

**Unit Tests** (isolate components):
- `test_crypto_provider.py`: Mock Binance API responses
  - Test OHLCV parsing
  - Test symbol validation (BTCUSDT valid, BTC invalid)
  - Test error handling (API down, invalid dates)
- `test_crypto_config.py`: Pydantic validation
  - Test market_type validation
  - Test symbol validation per market type
  - Test crypto_config defaults
- `test_data_provider_factory.py`: Factory logic
  - Test correct provider instantiation
  - Test unknown market_type raises error

**Integration Tests** (end-to-end flows):
- `test_crypto_backtest_flow.py`:
  - Fetch real BTC data from Binance (small date range)
  - Run backtest with crypto config
  - Verify trades executed correctly
  - Verify results contain fractional quantities
  - Verify cache files created with crypto_ prefix

**Contract Tests** (interface compliance):
- `test_provider_interface.py`:
  - Verify YahooFinanceStockProvider implements MarketDataProvider
  - Verify BinanceCryptoProvider implements MarketDataProvider
  - Test return types match interface (DataFrame columns, types)

---

## Technology Stack Summary

### New Dependencies
```toml
[tool.poetry.dependencies]
python-binance = "^1.0.19"  # Binance API client
# pyarrow already exists (for parquet)
```

### Updated Modules
- `src/models/config.py`: Add market_type, CryptoSpecificConfig
- `src/models/trade.py`: quantity int → Decimal
- `src/models/stock_data.py` → `src/models/market_data.py`: Rename StockData → MarketData
- `src/data/storage.py`: Schema migration, parquet naming
- `src/backtest/engine.py`: Use provider factory, crypto fee logic
- `src/risk/controls.py`: Handle Decimal quantities

### New Modules
- `src/data/providers/base.py`: MarketDataProvider ABC
- `src/data/providers/factory.py`: DataProviderFactory
- `src/data/providers/stock_provider.py`: YahooFinanceStockProvider
- `src/data/providers/crypto_provider.py`: BinanceCryptoProvider

---

## Performance Considerations

### Data Fetching
- **Binance API**: ~500ms per symbol for 1 year daily data
- **Caching**: First run fetches, subsequent runs < 100ms (parquet read)
- **Optimization**: Parallel fetching possible but not needed for 3-10 symbols

### Memory Usage
- **1 year daily crypto data**: ~365 rows × 6 columns × 8 bytes ≈ 17KB per symbol
- **10 symbols**: ~170KB (negligible)
- **No memory concerns** for typical backtest sizes

### Database
- **SQLite performance**: Adequate for backtest scale (hundreds of trades)
- **No indexing changes needed**: Primary queries by trade_id (already indexed)

---

## Risk Mitigation

### API Reliability
- **Risk**: Binance API downtime during backtest
- **Mitigation**: Graceful error handling, check cache first, retry logic in python-binance

### Data Quality
- **Risk**: Missing or invalid crypto data (delisted coins, gaps in history)
- **Mitigation**: Validate DataFrame completeness, warn user about gaps, skip symbol if insufficient data

### Backward Compatibility
- **Risk**: Breaking existing stock backtests
- **Mitigation**:
  - Comprehensive regression test suite
  - Default market_type='stock'
  - Keep stock_code column (don't drop)
  - Run existing examples as integration tests

---

## Open Questions (Resolved)

All technical unknowns from the specification have been researched and resolved:

1. ✅ **Data provider choice**: python-binance selected
2. ✅ **Fractional quantity handling**: Decimal type
3. ✅ **Database migration strategy**: ALTER TABLE with defaults
4. ✅ **Provider abstraction**: ABC + factory pattern
5. ✅ **24/7 handling**: No indicator changes needed
6. ✅ **Configuration extension**: Optional CryptoSpecificConfig
7. ✅ **Testing approach**: Unit/Integration/Contract layers

**Status**: Ready to proceed to Phase 1 (Design & Contracts)

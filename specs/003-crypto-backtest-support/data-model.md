# Data Model Design: Cryptocurrency Backtesting Support

**Feature**: 003-crypto-backtest-support | **Date**: 2025-10-17
**Purpose**: Define entity models, relationships, and validation rules for crypto market support

## Entity Overview

This feature extends existing entities to support both stock and cryptocurrency markets:

1. **MarketDataProvider** (NEW) - Abstract interface for data fetching
2. **CryptoSpecificConfig** (NEW) - Cryptocurrency trading parameters
3. **BacktestConfiguration** (MODIFIED) - Add market_type and crypto_config
4. **MarketData** (RENAMED) - Previously StockData, now market-agnostic
5. **Trade** (MODIFIED) - Support fractional quantities
6. **Database Schema** (MODIFIED) - Market-neutral columns

---

## 1. MarketDataProvider (Interface)

**Purpose**: Abstract interface defining how market data is fetched from different sources

**Type**: Abstract Base Class (Python ABC)

**Attributes**:
- None (interface only)

**Methods**:
```python
@abstractmethod
def fetch_ohlcv(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for given symbol and date range.

    Args:
        symbol: Asset identifier (6-digit code for stocks, "BTCUSDT" for crypto)
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        DataFrame with columns: [Open, High, Low, Close, Volume]
        Index: DatetimeIndex (timezone-aware for crypto, naive for stocks)
        None if data unavailable
    """

@abstractmethod
def validate_symbol(self, symbol: str) -> bool:
    """
    Validate symbol format for this market type.

    Args:
        symbol: Asset identifier to validate

    Returns:
        True if symbol format valid for this provider's market
    """

@abstractmethod
def get_market_type(self) -> str:
    """
    Return market type identifier.

    Returns:
        "stock" or "crypto"
    """
```

**Implementations**:
- `YahooFinanceStockProvider`: Fetches Korean stock data from Yahoo Finance
- `BinanceCryptoProvider`: Fetches cryptocurrency data from Binance API

**Validation Rules**:
- Implementations MUST return DataFrame with exact columns: Open, High, Low, Close, Volume
- All price/volume values MUST be numeric (float64)
- Index MUST be DatetimeIndex sorted ascending
- Empty/invalid data returns None (not empty DataFrame)

**Relationships**:
- Created by: `DataProviderFactory` based on market_type
- Used by: `BacktestEngine` (via factory, not direct instantiation)

---

## 2. CryptoSpecificConfig

**Purpose**: Hold cryptocurrency-specific trading parameters

**Type**: Pydantic BaseModel

**Attributes**:
```python
class CryptoSpecificConfig(BaseModel):
    trading_fee_percent: float = Field(
        default=0.1,
        ge=0.0,
        le=10.0,
        description="Trading fee percentage (maker/taker average)"
    )

    min_order_value_usdt: float = Field(
        default=10.0,
        ge=0.0,
        description="Minimum order value in USDT"
    )

    quote_currency: str = Field(
        default="USDT",
        pattern="^[A-Z]{3,5}$",
        description="Quote currency (USDT, BTC, ETH, etc.)"
    )
```

**Validation Rules**:
- `trading_fee_percent`: Must be between 0% and 10% (sanity check)
- `min_order_value_usdt`: Must be non-negative (0 = no minimum)
- `quote_currency`: Must be 3-5 uppercase letters (BTC, USDT, ETH, BUSD)

**Default Values**:
- `trading_fee_percent`: 0.1% (Binance spot trading default)
- `min_order_value_usdt`: 10.0 USDT (Binance minimum)
- `quote_currency`: "USDT" (most common crypto pair)

**Relationships**:
- Parent: `BacktestConfiguration` (optional field)
- Used by: `BacktestEngine._execute_buy()`, `_execute_sell()` for fee calculation

**State Transitions**: Immutable (created at config load time)

---

## 3. BacktestConfiguration (Modified)

**Purpose**: Root configuration object for backtest execution

**Existing Attributes** (unchanged):
- `seed_money: float` - Initial capital
- `date_range: Tuple[date, date]` - Backtest period
- `bollinger_period: int` - Bollinger Band window
- `bollinger_std_dev: float` - Standard deviation multiplier
- `stop_loss_percent: float` - Stop loss threshold
- `max_position_percent: float` - Max capital per position
- `max_positions: int` - Max concurrent positions
- `transaction_cost_percent: float` - Stock trading fees
- `enhanced_strategy: Optional[EnhancedStrategyConfig]` - Volume/RSI/MACD filters

**New Attributes**:
```python
class BacktestConfiguration(BaseModel):
    # NEW: Market type discriminator
    market_type: str = Field(
        default="stock",
        pattern="^(stock|crypto)$",
        description="Market type: 'stock' or 'crypto'"
    )

    # RENAMED: stocks → symbols (backward compatible via alias)
    symbols: List[str] = Field(
        min_length=1,
        description="Asset symbols (stock codes or crypto pairs)"
    )

    # NEW: Crypto-specific settings (optional)
    crypto_config: Optional[CryptoSpecificConfig] = Field(
        default=None,
        description="Crypto-specific settings (only for market_type='crypto')"
    )

    # DEPRECATED (kept for backward compatibility)
    stocks: Optional[List[str]] = Field(
        default=None,
        alias="symbols",
        description="DEPRECATED: Use 'symbols' instead"
    )
```

**Validation Rules**:
```python
@field_validator('market_type')
@classmethod
def validate_market_type(cls, v: str) -> str:
    if v not in ["stock", "crypto"]:
        raise ValueError(f"market_type must be 'stock' or 'crypto', got '{v}'")
    return v

@field_validator('symbols')
@classmethod
def validate_symbols(cls, v: List[str], info: ValidationInfo) -> List[str]:
    market_type = info.data.get('market_type', 'stock')

    if market_type == "stock":
        # Korean stock codes: exactly 6 digits
        for symbol in v:
            if not (symbol.isdigit() and len(symbol) == 6):
                raise ValueError(
                    f"Invalid stock code: '{symbol}'. "
                    f"Korean stock codes must be exactly 6 digits"
                )
    elif market_type == "crypto":
        # Crypto pairs: minimum 3 characters (e.g., BTC, BTCUSDT)
        for symbol in v:
            if not symbol or len(symbol) < 3:
                raise ValueError(
                    f"Invalid crypto symbol: '{symbol}'. "
                    f"Must be at least 3 characters"
                )

    return v

@model_validator(mode='after')
def validate_crypto_config_consistency(self) -> 'BacktestConfiguration':
    # Warn if crypto_config provided for stock market
    if self.market_type == "stock" and self.crypto_config is not None:
        import warnings
        warnings.warn(
            "crypto_config is ignored for market_type='stock'",
            UserWarning
        )

    return self
```

**Backward Compatibility**:
- `stocks` field kept as alias to `symbols`
- Existing YAML configs with `stocks:` continue to work
- `market_type` defaults to "stock" if not specified

**Relationships**:
- Contains: `CryptoSpecificConfig` (optional)
- Contains: `EnhancedStrategyConfig` (optional, existing)
- Used by: `BacktestEngine` constructor

---

## 4. MarketData (Renamed from StockData)

**Purpose**: Wrapper for OHLCV data and calculated indicators

**Type**: Python dataclass

**Attributes** (modified):
```python
@dataclass
class MarketData:
    symbol: str  # RENAMED from stock_code
    market_type: str  # NEW: "stock" or "crypto"
    ohlcv: pd.DataFrame
    start_date: date
    end_date: date

    # Calculated indicators (existing)
    bollinger_bands: Optional[pd.DataFrame] = None
    squeeze_events: list = field(default_factory=list)
    rsi: Optional[pd.Series] = None
    macd: Optional[pd.DataFrame] = None
    atr: Optional[pd.Series] = None
```

**Validation Rules** (in `__post_init__`):
```python
def __post_init__(self):
    # Validate OHLCV DataFrame structure
    validate_ohlcv_dataframe(self.ohlcv, self.symbol)

    # Validate market_type
    if self.market_type not in ["stock", "crypto"]:
        raise ValueError(f"Invalid market_type: {self.market_type}")

    # Validate symbol format matches market type
    if self.market_type == "stock":
        if not (self.symbol.isdigit() and len(self.symbol) == 6):
            raise ValueError(f"Stock symbol must be 6 digits: {self.symbol}")
    elif self.market_type == "crypto":
        if len(self.symbol) < 3:
            raise ValueError(f"Crypto symbol must be 3+ chars: {self.symbol}")

    # Validate timezone awareness for crypto
    if self.market_type == "crypto":
        if self.ohlcv.index.tz is None:
            raise ValueError(
                f"Crypto data must have timezone-aware index (UTC expected)"
            )
```

**Relationships**:
- Created from: `MarketDataProvider.fetch_ohlcv()` output
- Used by: `BacktestEngine` for strategy execution
- Contains: OHLCV DataFrame, indicator results

**State Transitions**:
1. Created with raw OHLCV data
2. Indicators calculated and stored in respective fields
3. Immutable after creation (indicators don't change during backtest)

**Migration Notes**:
- All references to `StockData` must be renamed to `MarketData`
- `stock_code` parameter → `symbol` in constructors
- Add `market_type` parameter to all instantiations

---

## 5. Trade (Modified)

**Purpose**: Represent a single buy or sell transaction

**Type**: Python dataclass

**Attributes** (modified):
```python
@dataclass
class Trade:
    trade_id: str
    execution_timestamp: datetime
    symbol: str  # RENAMED from stock_code
    action: TradeAction  # BUY or SELL
    quantity: Decimal  # CHANGED from int to Decimal
    execution_price: Decimal

    # Existing fields
    total_value: Decimal
    transaction_cost: Decimal
    confidence_score: Optional[int] = None

    # NEW: Market type metadata
    market_type: str = "stock"  # "stock" or "crypto"

    # Helper methods (existing)
    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.execution_timestamp.isoformat(),
            "symbol": self.symbol,
            "market_type": self.market_type,
            "action": self.action.value,
            "quantity": str(self.quantity),  # Decimal → str for JSON
            "price": str(self.execution_price),
            "total_value": str(self.total_value),
            "cost": str(self.transaction_cost),
            "confidence": self.confidence_score
        }
```

**Validation Rules**:
```python
def __post_init__(self):
    # Quantity must be positive
    if self.quantity <= 0:
        raise ValueError(f"Quantity must be positive: {self.quantity}")

    # Price must be positive
    if self.execution_price <= 0:
        raise ValueError(f"Price must be positive: {self.execution_price}")

    # For stocks, quantity should be integer (whole shares)
    if self.market_type == "stock":
        if self.quantity != int(self.quantity):
            raise ValueError(
                f"Stock quantity must be integer: {self.quantity}"
            )

    # Market type validation
    if self.market_type not in ["stock", "crypto"]:
        raise ValueError(f"Invalid market_type: {self.market_type}")
```

**Type Changes**:
- `quantity`: `int` → `Decimal` (supports fractional crypto quantities)
- All calculations involving quantity must use Decimal arithmetic

**Backward Compatibility**:
- Integer quantities still work (Decimal(5) == 5)
- Stock trades continue to use integer quantities (validated in `__post_init__`)

**Relationships**:
- Created by: `BacktestEngine._execute_buy()`, `_execute_sell()`
- Stored in: `TradeLogger.log_trade()` → SQLite database
- Part of: `BacktestReport.trades` list

---

## 6. Database Schema (Modified)

### 6.1 Trade Log Table

**Existing Schema**:
```sql
CREATE TABLE IF NOT EXISTS trade_log (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    stock_code TEXT NOT NULL,  -- To be kept for backward compatibility
    action TEXT NOT NULL,
    quantity INTEGER NOT NULL,  -- To be changed to REAL
    price REAL NOT NULL,
    total_value REAL NOT NULL,
    transaction_cost REAL NOT NULL,
    confidence_score INTEGER
);
```

**New Schema** (after migration):
```sql
CREATE TABLE IF NOT EXISTS trade_log (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    stock_code TEXT,  -- DEPRECATED: Kept for backward compatibility
    symbol TEXT NOT NULL,  -- NEW: Market-neutral column
    market_type TEXT NOT NULL DEFAULT 'stock',  -- NEW: Discriminator
    action TEXT NOT NULL,
    quantity REAL NOT NULL,  -- CHANGED from INTEGER
    price REAL NOT NULL,
    total_value REAL NOT NULL,
    transaction_cost REAL NOT NULL,
    confidence_score INTEGER
);
```

**Migration SQL**:
```sql
-- Add new columns with defaults
ALTER TABLE trade_log ADD COLUMN market_type TEXT DEFAULT 'stock';
ALTER TABLE trade_log ADD COLUMN symbol TEXT;

-- Populate symbol from stock_code for existing rows
UPDATE trade_log SET symbol = stock_code WHERE symbol IS NULL;

-- Note: SQLite allows REAL in quantity column even if created as INTEGER
-- No ALTER needed for quantity type (SQLite is dynamically typed)
```

### 6.2 Squeeze Events Table

**Existing Schema**:
```sql
CREATE TABLE IF NOT EXISTS squeeze_events (
    event_id TEXT PRIMARY KEY,
    stock_code TEXT NOT NULL,
    detection_date TEXT NOT NULL,
    -- other fields...
);
```

**New Schema** (after migration):
```sql
CREATE TABLE IF NOT EXISTS squeeze_events (
    event_id TEXT PRIMARY KEY,
    stock_code TEXT,  -- DEPRECATED
    symbol TEXT NOT NULL,  -- NEW
    market_type TEXT NOT NULL DEFAULT 'stock',  -- NEW
    detection_date TEXT NOT NULL,
    -- other fields unchanged...
);
```

**Migration SQL**:
```sql
ALTER TABLE squeeze_events ADD COLUMN market_type TEXT DEFAULT 'stock';
ALTER TABLE squeeze_events ADD COLUMN symbol TEXT;
UPDATE squeeze_events SET symbol = stock_code WHERE symbol IS NULL;
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────┐
│ BacktestConfiguration       │
├─────────────────────────────┤
│ + market_type: str          │
│ + symbols: List[str]        │
│ + crypto_config: Optional   │◄──┐
│ + enhanced_strategy         │   │
│ + seed_money, date_range... │   │
└────────────┬────────────────┘   │
             │                     │
             │ configures          │
             ▼                     │
┌─────────────────────────────┐   │
│ BacktestEngine              │   │
├─────────────────────────────┤   │
│ + run()                     │   │
│ + _execute_buy()            │   │ contains
│ + _execute_sell()           │   │
└──┬──────────────────────┬───┘   │
   │                      │        │
   │ uses                 │        │
   ▼                      │   ┌────┴──────────────────┐
┌─────────────────────┐   │   │ CryptoSpecificConfig  │
│ MarketDataProvider  │   │   ├───────────────────────┤
│ (ABC)               │   │   │ + trading_fee_percent │
├─────────────────────┤   │   │ + min_order_value     │
│ + fetch_ohlcv()     │   │   │ + quote_currency      │
│ + validate_symbol() │   │   └───────────────────────┘
│ + get_market_type() │   │
└──────▲──────────────┘   │
       │                  │ creates
       │                  ▼
       │          ┌───────────────┐
       │          │ Trade         │
       │          ├───────────────┤
       │          │ + symbol      │
       │          │ + quantity    │
       │          │ + market_type │
       │          └───────────────┘
       │
       │ implements
       │
   ┌───┴────────────────┐
   │                    │
┌──▼──────────────┐  ┌──▼──────────────────┐
│ YahooFinance    │  │ BinanceCrypto       │
│ StockProvider   │  │ Provider            │
├─────────────────┤  ├─────────────────────┤
│ + fetch_ohlcv() │  │ + fetch_ohlcv()     │
└─────────────────┘  └─────────────────────┘
        │                     │
        │ returns             │ returns
        ▼                     ▼
   ┌─────────────────────────────┐
   │ MarketData                  │
   ├─────────────────────────────┤
   │ + symbol                    │
   │ + market_type               │
   │ + ohlcv: DataFrame          │
   │ + bollinger_bands           │
   │ + squeeze_events            │
   └─────────────────────────────┘
```

---

## Data Flow

### 1. Configuration Loading
```
YAML file → Pydantic validation → BacktestConfiguration
                                   ├─ market_type: "crypto"
                                   ├─ symbols: ["BTCUSDT", "ETHUSDT"]
                                   └─ crypto_config: {...}
```

### 2. Data Provider Selection
```
BacktestConfiguration.market_type → DataProviderFactory.create_provider()
                                     └─ BinanceCryptoProvider instance
```

### 3. Data Fetching
```
BinanceCryptoProvider.fetch_ohlcv("BTCUSDT", start, end)
  → Binance API call
  → Parse JSON response
  → Convert to DataFrame (UTC timestamps)
  → Return OHLCV DataFrame
```

### 4. Market Data Creation
```
DataFrame + symbol + market_type → MarketData instance
                                   └─ Indicators calculated
```

### 5. Trade Execution
```
Signal detected → BacktestEngine._execute_buy()
                  ├─ Calculate quantity (Decimal)
                  ├─ Apply crypto_config.trading_fee_percent
                  ├─ Check crypto_config.min_order_value_usdt
                  └─ Create Trade(quantity=Decimal, market_type="crypto")
```

### 6. Persistence
```
Trade → TradeLogger.log_trade()
        └─ INSERT INTO trade_log (symbol, market_type, quantity, ...)
            VALUES ("BTCUSDT", "crypto", 0.0222, ...)
```

---

## Validation Summary

### Configuration Validation
- ✅ market_type in ["stock", "crypto"]
- ✅ symbols match market_type format rules
- ✅ crypto_config.trading_fee_percent in [0, 10]
- ✅ crypto_config.min_order_value_usdt >= 0

### Data Validation
- ✅ DataFrame has columns: Open, High, Low, Close, Volume
- ✅ Index is DatetimeIndex (timezone-aware for crypto)
- ✅ No NaN values in OHLCV columns
- ✅ Prices/volumes are numeric

### Trade Validation
- ✅ quantity > 0
- ✅ execution_price > 0
- ✅ Stock quantities are integers
- ✅ Crypto quantities are Decimal (can be fractional)
- ✅ market_type matches configuration

---

## Migration Checklist

### Code Changes
- [x] Rename `StockData` → `MarketData` globally
- [x] Rename `stock_code` → `symbol` in all entities
- [x] Change `Trade.quantity` from `int` to `Decimal`
- [x] Add `market_type` field to configuration, MarketData, Trade
- [x] Add `CryptoSpecificConfig` model
- [x] Extend `BacktestConfiguration` validation

### Database Changes
- [x] Add `market_type` column with default 'stock'
- [x] Add `symbol` column
- [x] Populate `symbol` from `stock_code` for existing data
- [x] Update insert statements to include market_type, symbol

### Backward Compatibility
- [x] Keep `stock_code` column (deprecated, not dropped)
- [x] Keep `stocks` field as alias to `symbols`
- [x] Default `market_type='stock'` if not specified
- [x] Integer quantities continue to work (Decimal compatible)

**Status**: Data model design complete. Ready for contract generation.

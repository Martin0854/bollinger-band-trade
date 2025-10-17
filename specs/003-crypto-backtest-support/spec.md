# Feature Specification: Cryptocurrency Backtesting Support

**Feature Branch**: `003-crypto-backtest-support`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "crypto_migration_guide.md 파일을 참고하여 암호화폐 백테스트를 수행할 수 있도록 변경하고자 한다."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Cryptocurrency Backtest (Priority: P1)

As a quantitative trader, I want to run a backtest on cryptocurrency pairs (BTC, ETH) using the same Bollinger Band squeeze strategy currently used for Korean stocks, so that I can evaluate strategy performance in 24/7 crypto markets.

**Why this priority**: This is the core functionality that enables the system to support cryptocurrency markets. Without this, none of the other user stories provide value. This represents the MVP.

**Independent Test**: Can be fully tested by configuring a crypto backtest in YAML (specifying BTCUSDT, ETHUSDT symbols and market_type='crypto'), running the backtest engine, and receiving results showing trades executed on cryptocurrency data with appropriate 24/7 market handling.

**Acceptance Scenarios**:

1. **Given** a configuration file specifying market_type='crypto' and symbols=['BTCUSDT', 'ETHUSDT'], **When** the backtest is executed, **Then** the system fetches cryptocurrency OHLCV data and runs the strategy
2. **Given** cryptocurrency data includes weekend trading (24/7), **When** calculating indicators, **Then** no days are skipped for weekends or holidays
3. **Given** a crypto backtest completes successfully, **When** viewing results, **Then** all trades show cryptocurrency symbols (e.g., BTCUSDT) and prices in USDT denomination
4. **Given** a backtest configuration with both crypto and stock symbols mixed, **When** validating configuration, **Then** the system rejects the configuration with a clear error message

---

### User Story 2 - Configure Crypto-Specific Trading Parameters (Priority: P2)

As a cryptocurrency trader, I want to configure crypto-specific parameters like trading fees (0.1% maker/taker), minimum order values (10 USDT), and quote currency, so that my backtest results accurately reflect real crypto trading conditions.

**Why this priority**: After basic crypto support (P1), realistic trading conditions are essential for meaningful backtesting results. This ensures the backtest reflects actual crypto exchange constraints.

**Independent Test**: Can be fully tested by creating a config with crypto_config section specifying trading fees and minimum order values, running a backtest, and verifying that trades respect these constraints (no trades below minimum, correct fee deductions).

**Acceptance Scenarios**:

1. **Given** a crypto_config specifying trading_fee_percent=0.1, **When** executing trades, **Then** each buy and sell incurs 0.1% fee on trade value
2. **Given** a crypto_config specifying min_order_value_usdt=10, **When** calculating position sizes, **Then** no trades are executed with values below 10 USDT
3. **Given** a stock market_type configuration, **When** crypto_config is specified, **Then** the system warns that crypto_config is ignored for stock backtests
4. **Given** no crypto_config is provided for a crypto backtest, **When** running backtest, **Then** reasonable defaults are applied (0.1% fee, 10 USDT minimum)

---

### User Story 3 - Support Multiple Data Providers (Priority: P2)

As a backtest operator, I want the system to automatically select the appropriate data provider based on market type (Yahoo Finance for stocks, Binance API for crypto), so that I don't need to manually manage data sources.

**Why this priority**: Clean abstraction of data sources makes the system maintainable and extensible. This enables future addition of more data providers without changing core backtest logic.

**Independent Test**: Can be fully tested by running backtests for both market types and verifying correct data provider is used (checking logs or data characteristics like timezone-aware UTC timestamps for crypto).

**Acceptance Scenarios**:

1. **Given** a configuration with market_type='stock', **When** backtest initializes, **Then** YahooFinanceStockProvider is used to fetch data
2. **Given** a configuration with market_type='crypto', **When** backtest initializes, **Then** BinanceCryptoProvider is used to fetch data
3. **Given** cryptocurrency data is fetched, **When** examining timestamps, **Then** all timestamps are timezone-aware (UTC) for proper 24/7 handling
4. **Given** stock data is fetched with Korean stock codes (6 digits), **When** data provider processes symbols, **Then** appropriate exchange suffix (.KS or .KQ) is added

---

### User Story 4 - Handle Fractional Quantities for Crypto (Priority: P3)

As a cryptocurrency trader, I want the system to support fractional quantities (e.g., 0.05 BTC) rather than only integer quantities, so that I can accurately model crypto trading where fractional positions are standard.

**Why this priority**: While important for accuracy, the system could function with integer-based approximations initially. This is a quality improvement that makes results more precise.

**Independent Test**: Can be fully tested by running a crypto backtest with a position size that would naturally result in fractional quantities, and verifying trade logs show decimal quantities with appropriate precision.

**Acceptance Scenarios**:

1. **Given** a BTC trade with available capital of 1000 USDT and BTC price of 45,000 USDT, **When** calculating position size, **Then** quantity is approximately 0.0222 BTC (fractional)
2. **Given** a completed crypto trade with fractional quantity, **When** storing trade in database, **Then** quantity is stored as REAL type preserving decimal precision
3. **Given** a stock market backtest, **When** calculating quantities, **Then** quantities remain integers (whole shares only)
4. **Given** fractional crypto quantities, **When** calculating portfolio value, **Then** all calculations use high-precision decimal arithmetic

---

### User Story 5 - Cache Crypto Market Data (Priority: P3)

As a backtest operator, I want cryptocurrency data to be cached locally after first fetch (similar to stock data), so that I can re-run backtests quickly without re-downloading large datasets.

**Why this priority**: Performance optimization that improves user experience but doesn't block core functionality. System works without this, just slower on repeated runs.

**Independent Test**: Can be fully tested by running a crypto backtest twice on the same date range and symbols, measuring that the second run is significantly faster and checking that parquet cache files exist for crypto symbols.

**Acceptance Scenarios**:

1. **Given** a crypto backtest runs for the first time, **When** data is fetched, **Then** parquet files are created in cache directory with naming pattern crypto_{symbol}_{start}_{end}.parquet
2. **Given** cached crypto data exists for requested date range, **When** backtest runs, **Then** data is loaded from cache instead of API
3. **Given** crypto symbol contains special characters (BTC-USD), **When** creating cache filename, **Then** special characters are sanitized (BTCUSD)
4. **Given** cached data is stale or corrupted, **When** loading fails, **Then** system re-fetches from API and updates cache

---

### Edge Cases

- What happens when Binance API is unavailable or rate-limited during data fetch?
  - System should fail gracefully with clear error message indicating API unavailable
  - If partial data was cached, system should inform user which date ranges are available

- How does the system handle cryptocurrency symbols that don't exist on Binance (e.g., newly listed or delisted coins)?
  - Data provider validation should catch invalid symbols before fetch
  - If symbol validation passes but data fetch returns empty, log warning and skip that symbol

- What happens when a crypto backtest configuration specifies a date range before the cryptocurrency existed (e.g., ETH data before July 2015)?
  - Data provider returns empty or partial data
  - System should warn user about missing data for specific symbols and continue with available data

- How does the system handle very large date ranges for 24/7 crypto data (e.g., 5 years of minute-level data)?
  - System should fetch data in chunks to avoid memory issues
  - Consider daily candles as default for long-term backtests (configurable interval)

- What happens when mixing very different market volatilities (e.g., BTC with a small-cap altcoin)?
  - Backtest runs normally but results may show very different behavior per symbol
  - Risk management parameters (stop_loss, position_size) apply uniformly - may need symbol-specific tuning in future

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a 'market_type' configuration field with valid values 'stock' or 'crypto'
- **FR-002**: System MUST validate symbols according to market type rules:
  - Stock symbols: exactly 6 digits (Korean stock codes)
  - Crypto symbols: minimum 3 characters with basic format validation
- **FR-003**: System MUST abstract data fetching behind a MarketDataProvider interface with methods: fetch_ohlcv(), validate_symbol(), get_market_type()
- **FR-004**: System MUST implement BinanceCryptoProvider for fetching cryptocurrency OHLCV data from Binance API
- **FR-005**: System MUST implement YahooFinanceStockProvider wrapping existing yfinance logic
- **FR-006**: System MUST use DataProviderFactory to instantiate the correct provider based on market_type
- **FR-007**: System MUST support cryptocurrency-specific configuration including trading_fee_percent, min_order_value_usdt, and quote_currency
- **FR-008**: System MUST apply crypto trading fees from crypto_config when market_type='crypto', falling back to transaction_cost_percent otherwise
- **FR-009**: System MUST handle fractional quantities for cryptocurrency trades (Decimal type instead of integer)
- **FR-010**: System MUST process 24/7 cryptocurrency data without skipping weekends or holidays
- **FR-011**: System MUST store cryptocurrency data with timezone-aware timestamps (UTC)
- **FR-012**: System MUST cache cryptocurrency data to parquet files with naming pattern: crypto_{sanitized_symbol}_{start}_{end}.parquet
- **FR-013**: System MUST update database schema to support:
  - market_type column (TEXT) in trade_log and squeeze_events tables
  - quantity as REAL type (instead of INTEGER) for fractional crypto quantities
  - symbol column (replacing stock_code)
- **FR-014**: System MUST rename 'stock_code' references to 'symbol' throughout codebase for market neutrality
- **FR-015**: System MUST rename StockData model to MarketData for terminology consistency
- **FR-016**: System MUST enforce minimum order value validation for crypto trades based on min_order_value_usdt
- **FR-017**: System MUST provide example YAML configuration files demonstrating crypto backtest setup
- **FR-018**: System MUST provide example Python scripts showing crypto backtest execution
- **FR-019**: System MUST maintain backward compatibility with existing stock market configurations
- **FR-020**: System MUST reject configurations that mix both stock and crypto symbols in the same backtest

### Key Entities

- **MarketDataProvider (interface)**: Abstract interface defining how market data is fetched. Key attributes: market type identifier, symbol validation rules. Relationships: implemented by concrete providers (YahooFinanceStockProvider, BinanceCryptoProvider).

- **CryptoSpecificConfig**: Configuration object holding cryptocurrency trading parameters. Key attributes: trading fee percentage, minimum order value in USDT, quote currency. Relationships: optional child of BacktestConfiguration, only used when market_type='crypto'.

- **MarketData**: Data wrapper holding OHLCV information for any asset (stock or crypto). Key attributes: symbol identifier, market type, OHLCV DataFrame, date range, calculated indicators. Relationships: contains reference to symbol traded, used by backtest engine.

- **Trade**: Represents a single buy or sell transaction. Key attributes: symbol, action (buy/sell), quantity (now Decimal for crypto), price, timestamp, market type. Relationships: belongs to a backtest run, references a specific symbol.

- **BacktestConfiguration**: Root configuration object for a backtest run. Key attributes: market type, symbols list, date range, strategy parameters, risk controls, optional crypto-specific config. Relationships: parent of CryptoSpecificConfig, validated before backtest execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully run a backtest on cryptocurrency pairs (BTC, ETH, BNB) and receive valid results showing trades and performance metrics
- **SC-002**: System correctly processes 24/7 cryptocurrency data without excluding weekends, evidenced by trades appearing on Saturday/Sunday in results
- **SC-003**: Cryptocurrency backtests apply correct trading fees (0.1% default) and minimum order values (10 USDT default), verified in trade execution logs
- **SC-004**: System supports fractional cryptocurrency quantities with precision up to 8 decimal places (Bitcoin standard), verified in trade records
- **SC-005**: Cached cryptocurrency data reduces second-run backtest execution time by at least 80% compared to first run (measuring data fetch time only)
- **SC-006**: All existing Korean stock backtests continue to work without modification after crypto support is added (backward compatibility validation)
- **SC-007**: Configuration validation catches and rejects invalid scenarios (mixed stock/crypto symbols, wrong symbol formats for market type) with clear error messages
- **SC-008**: Example crypto backtest scripts execute successfully and produce meaningful results on standard test cases (BTC/ETH 2023-2024 date range)

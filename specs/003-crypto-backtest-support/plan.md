# Implementation Plan: Cryptocurrency Backtesting Support

**Branch**: `003-crypto-backtest-support` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-crypto-backtest-support/spec.md`

## Summary

This feature extends the existing Korean stock (KOSPI/KOSDAQ) backtesting system to support cryptocurrency markets (BTC, ETH, etc.). The primary requirement is to enable users to run the same Bollinger Band squeeze strategy on 24/7 cryptocurrency markets with appropriate handling of crypto-specific characteristics: fractional quantities, different trading fees, continuous trading (no weekends), and alternative data sources (Binance API vs Yahoo Finance).

**Technical Approach**: Implement a provider abstraction pattern for market data fetching, extend the configuration model to support market type discrimination, migrate quantity handling from integer to Decimal for fractional crypto support, and update database schema to accommodate market-neutral terminology and data types.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Existing: pandas, numpy, yfinance, pydantic, pytest, hypothesis
- New: python-binance (Binance API client), pyarrow (parquet caching)

**Storage**:
- SQLite database for trade logs and squeeze events (existing)
- Parquet files for OHLCV data caching (existing, needs market_type prefix)

**Testing**: pytest with markers (unit, integration, contract)
**Target Platform**: Python CLI application (local execution)
**Project Type**: Single project (src/ structure)

**Performance Goals**:
- Crypto data fetch: < 5 seconds for 1 year of daily data per symbol
- Cache hit: < 100ms to load cached parquet data
- Backtest execution: similar to stock performance (~2-5 sec per symbol for 1 year)

**Constraints**:
- Must maintain backward compatibility with existing stock configurations
- No breaking changes to BacktestEngine API
- Database migrations must be non-destructive
- Binance API rate limits: 1200 requests/minute (no API key required for public OHLCV)

**Scale/Scope**:
- Support: 3-10 cryptocurrency symbols per backtest
- Timeframes: daily candles for 1-5 year backtests
- Data volume: ~365-1825 candles per symbol (24/7 vs stock's ~250 trading days/year)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: This project does not have a formal constitution.md defined. Applying general software engineering principles:

### Simplicity Principle
✅ **PASS** - Feature uses existing backtest engine without modifications. Only adds abstraction layer for data providers.

### Backward Compatibility
✅ **PASS** - All existing stock configurations continue to work. New `market_type` field defaults to "stock" if not specified.

### Single Responsibility
✅ **PASS** - Data provider abstraction cleanly separates data fetching from backtest logic. Each provider (Stock, Crypto) handles one market type.

### Testability
✅ **PASS** - Provider interface enables mocking. Existing test structure (unit/integration/contract) applies to new components.

### Type Safety
✅ **PASS** - Pydantic models enforce market_type validation. Decimal type for quantities provides precision safety.

**Gate Result**: ✅ All principles pass. Proceed to Phase 0.

---

## Post-Design Constitution Re-Check

*After Phase 1 design completion, re-evaluate against constitution principles:*

### Simplicity Principle
✅ **PASS** - Design maintains simplicity:
- Provider abstraction uses standard ABC pattern (well-known Python idiom)
- No complex architectural patterns introduced (factory is simple)
- Configuration extension uses optional fields (not full redesign)

### Backward Compatibility
✅ **PASS** - Design ensures zero breaking changes:
- `market_type` defaults to "stock" (existing configs work unchanged)
- `stocks` field kept as alias to `symbols`
- `stock_code` database column preserved (deprecated but not dropped)
- Integer quantities still work (Decimal is superset)
- All existing tests will pass with default values

### Single Responsibility
✅ **PASS** - Responsibilities well-separated:
- `MarketDataProvider`: Only data fetching
- `DataProviderFactory`: Only provider instantiation
- `BacktestEngine`: Only strategy execution (no data fetching logic)
- `CryptoSpecificConfig`: Only crypto trading parameters

### Testability
✅ **PASS** - Design is highly testable:
- Provider interface enables complete mocking
- Contract tests verify implementations match interface
- Integration tests use real Binance API (small date ranges)
- Unit tests isolate each component

### Type Safety
✅ **PASS** - Type safety maintained/improved:
- Pydantic validation for all config fields
- ABC enforces provider interface compliance
- Decimal type provides financial precision
- mypy can verify all type hints

**Final Gate Result**: ✅ All principles pass after design. Ready for implementation (`/speckit.tasks`).

## Project Structure

### Documentation (this feature)

```
specs/003-crypto-backtest-support/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entity designs)
├── quickstart.md        # Phase 1 output (getting started guide)
├── contracts/           # Phase 1 output (API schemas)
│   └── provider-interface.yaml  # MarketDataProvider contract
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```
src/
├── data/
│   ├── providers/              # NEW: Data provider abstraction
│   │   ├── __init__.py
│   │   ├── base.py            # MarketDataProvider interface
│   │   ├── factory.py         # DataProviderFactory
│   │   ├── stock_provider.py  # YahooFinanceStockProvider
│   │   └── crypto_provider.py # BinanceCryptoProvider
│   └── storage.py             # MODIFIED: Add market_type param, schema migration
│
├── models/
│   ├── config.py              # MODIFIED: Add market_type, CryptoSpecificConfig
│   ├── stock_data.py          # RENAMED TO: market_data.py
│   ├── market_data.py         # MODIFIED: StockData → MarketData
│   └── trade.py               # MODIFIED: quantity int → Decimal
│
├── backtest/
│   └── engine.py              # MODIFIED: Use provider factory, apply crypto fees
│
├── risk/
│   └── controls.py            # MODIFIED: Handle Decimal quantities
│
└── indicators/                # NO CHANGES (market-agnostic)
    ├── bollinger.py
    ├── squeeze.py
    ├── volume.py
    └── momentum.py

examples/
├── crypto_btc_eth_backtest.py     # NEW: Crypto backtest example
└── phase1_mvp_kospi100.py         # UNCHANGED

config/
└── examples/
    └── crypto_btc_eth.yaml        # NEW: Crypto config example

tests/
├── unit/
│   ├── test_crypto_provider.py       # NEW
│   ├── test_data_provider_factory.py # NEW
│   ├── test_crypto_config.py         # NEW
│   └── test_market_data.py           # MODIFIED (renamed from test_stock_data.py)
├── integration/
│   └── test_crypto_backtest_flow.py  # NEW
└── contract/
    └── test_provider_interface.py    # NEW
```

**Structure Decision**: This is a single-project Python application following the existing src/ layout. The feature adds a new `data/providers/` module for market data abstraction and modifies existing models to support both stock and crypto markets. No new top-level projects are needed.

## Complexity Tracking

*This section is empty because there are no constitutional violations requiring justification.*

The design follows the principle of minimal complexity:
- Reuses existing BacktestEngine without modification to core logic
- Adds abstraction only where needed (data providers)
- Extends models with optional fields (backward compatible)
- No new architectural patterns introduced (factory pattern is standard)

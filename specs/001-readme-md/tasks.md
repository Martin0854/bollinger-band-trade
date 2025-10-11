# Tasks: Bollinger Band Auto-Trading Bot

**Input**: Design documents from `/specs/001-readme-md/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: ✅ **REQUIRED** - Constitution Principle III (Test-First Development) is NON-NEGOTIABLE

**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5, Setup, Foundation)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [Setup] Create project directory structure per plan.md: `src/{models,indicators,signals,data,backtest,cli,utils}/`, `tests/{unit,integration,contract,fixtures}/`, `config/`, `data/{cache,logs}/`
- [x] T002 [Setup] Initialize Python project with pyproject.toml containing all dependencies: vectorbt 0.26+, FinanceDataReader 0.9+, pykrx 1.0+, pandas-ta 0.3+, numba 0.58+, pyarrow 14+, pydantic 2.0+, pyyaml 6.0+, quantstats, empyrical, pytest 8.0+, pytest-benchmark, hypothesis
- [x] T003 [P] [Setup] Create pytest.ini with test configuration (Asia/Seoul timezone, benchmark thresholds: <5s for backtest, <100ms for indicators)
- [x] T004 [P] [Setup] Create .gitignore for `data/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `venv/`
- [x] T005 [P] [Setup] Create example config files: `config/default.yaml`, `config/examples/single_stock.yaml`, `config/examples/multi_stock.yaml` per contracts/config-schema.yaml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation (TDD - Write First) ⚠️

- [x] T006 [P] [Foundation] **TEST**: Contract test for BacktestConfiguration Pydantic validation in `tests/contract/test_config_schema.py` - verify all validation rules from FR-045, test positive/negative cases, ensure tests FAIL before implementation
- [x] T007 [P] [Foundation] **TEST**: Unit tests for logging utility in `tests/unit/test_logging.py` - verify JSON formatter, structured log format, timezone handling (Asia/Seoul), ensure tests FAIL

### Implementation for Foundation

- [x] T008 [Foundation] Implement BacktestConfiguration Pydantic model in `src/models/config.py` - all 8 entities' config fields, field_validator for stock codes (6 digits), date_range validation, from_yaml classmethod per data-model.md Entity 7
- [x] T009 [Foundation] Implement structured logging setup in `src/utils/logging.py` - JSON formatter, Asia/Seoul timezone, log levels, file+console handlers per plan.md Principle V
- [x] T010 [Foundation] Implement defensive validation utilities in `src/utils/validation.py` - stock code validator, OHLCV validator, fail-fast error messages per plan.md Principle VII
- [x] T011 [Foundation] Create SQLite database schema initialization script in `src/data/storage.py` - tables: trade_log (FR-038), squeeze_events (FR-042), portfolio_snapshots, backtest_results, with proper indexes

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Historical Backtesting Simulation (Priority: P1) 🎯 MVP

**Goal**: Enable single-stock backtest with squeeze detection, signal generation, trade execution, and performance metrics

**Independent Test**: Load data for Samsung (005930), configure squeeze threshold 30% over 10 days, run 1-year backtest, verify metrics (total return, win rate, MDD, Sharpe ratio) calculated correctly

### Tests for User Story 1 (TDD - Write First) ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T012 [P] [US1] **TEST**: Unit test for Portfolio model in `tests/unit/test_portfolio.py` - verify cash_balance >= 0 validation, total_value computation, equity_curve ordering, ensure tests FAIL before T022
- [x] T013 [P] [US1] **TEST**: Unit test for Position model in `tests/unit/test_position.py` - verify quantity > 0, purchase_price > 0, stock_code regex, unrealized_pnl calculation, stop_loss check, ensure tests FAIL before T023
- [x] T014 [P] [US1] **TEST**: Unit test for Trade model in `tests/unit/test_trade.py` - verify immutability, BUY has entry_reason, SELL has exit_reason+realized_pnl, to_log_dict format, ensure tests FAIL before T024
- [x] T015 [P] [US1] **TEST**: Unit test for Bollinger Band calculation in `tests/unit/test_bollinger.py` - verify middle=SMA, upper/lower=middle±(std*multiplier), band_width=upper-lower, band ordering invariants, compare against pandas-ta reference, ensure tests FAIL before T027
- [x] T016 [P] [US1] **TEST**: Property-based test for Bollinger Bands using hypothesis in `tests/unit/test_bollinger.py` - generate random OHLCV, verify invariants (lower≤middle≤upper, width≥0), ensure tests FAIL before T027
- [x] T017 [P] [US1] **TEST**: Unit test for Squeeze detection in `tests/unit/test_squeeze.py` - verify 30% decrease detection over 10 days, direction_bias logic (lower band touch=bullish), expansion confirmation, ensure tests FAIL before T028
- [x] T018 [P] [US1] **TEST**: Unit test for Signal generation in `tests/unit/test_signals.py` - verify buy signal (squeeze→expansion, lower band touched, no position), sell signal (opposite band or stop-loss), signal prioritization (FR-023), ensure tests FAIL before T029
- [x] T019 [P] [US1] **TEST**: Unit test for Risk controls in `tests/unit/test_risk.py` - verify stop-loss triggers at exactly threshold%, position sizing min(cash/price, portfolio*max_pct/price), insufficient cash handling, ensure tests FAIL before T030
- [x] T020 [P] [US1] **TEST**: Unit test for Performance metrics in `tests/unit/test_metrics.py` - verify total_return, win_rate, MDD, Sharpe ratio formulas match industry standard, compare against manual calculation, ensure tests FAIL before T033
- [x] T021 [P] [US1] **TEST**: Integration test for full single-stock backtest E2E in `tests/integration/test_backtest_e2e.py` - load Samsung 005930 1-year data, run backtest with default config, verify all 4 acceptance scenarios from spec.md US1, ensure tests FAIL before backtest engine complete

### Implementation for User Story 1

#### Models (can parallelize)

- [x] T022 [P] [US1] Implement Portfolio model in `src/models/portfolio.py` - dataclass with cash_balance, positions, equity_curve, initial_capital, total_value property, record_snapshot method, validate_cash_nonnegative per data-model.md Entity 1
- [x] T023 [P] [US1] Implement Position model in `src/models/portfolio.py` - dataclass with stock_code, quantity, purchase_price, purchase_date, entry_reason, position_id (UUID), computed properties (market_value, unrealized_pnl, unrealized_pnl_pct), check_stop_loss method per data-model.md Entity 2
- [x] T024 [P] [US1] Implement Trade model in `src/models/trade.py` - frozen dataclass with trade_id (UUID), stock_code, action (Enum: BUY/SELL), execution_price, quantity, execution_timestamp (timezone-aware), bollinger_values dict, portfolio snapshots, to_log_dict method per data-model.md Entity 3
- [x] T025 [P] [US1] Implement StockData model in `src/models/stock_data.py` - dataclass with stock_code, date_range, data (DataFrame), validation_status (Enum), __post_init__ OHLCV validation (Low≤Close, High≥Close, all>0), detect_outliers method (>20% price change without volume spike) per data-model.md Entity 4

#### Indicators

- [x] T026 [US1] Implement BollingerBand model in `src/indicators/bollinger.py` - dataclass with stock_code, calculation_date, upper/middle/lower bands, band_width, period, std_dev_multiplier, squeeze_status (Enum), __post_init__ validation (lower≤middle≤upper), from_price_series classmethod using pandas-ta per data-model.md Entity 5
- [x] T027 [US1] Implement Bollinger Band calculation function in `src/indicators/bollinger.py` - wrapper around pandas-ta bbands(), ensure no lookahead bias with .shift(1), return BollingerBand instances, handle edge cases (insufficient data at start per FR-014)
- [x] T028 [US1] Implement Squeeze detection in `src/indicators/squeeze.py` - SqueezeEvent dataclass with event_id (UUID), detection_date, band widths, width_decrease_pct, direction_bias (Enum: BULLISH/BEARISH/NEUTRAL), expansion_confirmed_date, Numba-optimized detect_squeeze function ((width_past - width_now)/width_past * 100 >= threshold) per data-model.md Entity 6

#### Signals

- [x] T029 [US1] Implement Signal generator in `src/signals/generator.py` - functions: generate_entry_signal (checks squeeze→expansion, band touch direction, no existing position per FR-020/FR-021), generate_exit_signal (opposite band touch per FR-024), returns signal type + metadata
- [x] T030 [US1] Implement Risk controls in `src/risk/controls.py` - functions: calculate_position_size (min(cash/price, portfolio*max_pct/price) per FR-028), check_stop_loss (position.unrealized_pnl_pct <= -threshold per FR-022), prioritize_signals (stop-loss > squeeze per FR-023), validate_cash_sufficient per FR-032

#### Backtest Engine

- [x] T031 [US1] Implement Backtest engine core in `src/backtest/engine.py` - BacktestEngine class with run() method: load StockData, calculate BollingerBands for all dates, detect SqueezeEvents, generate signals per timestep, execute trades via vectorbt Portfolio.from_signals, update Portfolio state, log trades to SQLite, return PerformanceReport, ensure chronological processing (no lookahead bias)
- [x] T032 [US1] Integrate vectorbt for portfolio simulation in `src/backtest/engine.py` - use vectorbt.Portfolio.from_signals() with entry/exit boolean arrays, configure stop_loss via sl_stop parameter, transaction costs via fees parameter, extract trade log and equity curve from vectorbt results
- [x] T033 [US1] Implement Performance metrics calculation in `src/backtest/metrics.py` - PerformanceReport dataclass with report_id (UUID), all metrics (total_return_pct, win_rate_pct, max_drawdown_pct, sharpe_ratio per FR-033 to FR-036), from_backtest classmethod using QuantStats (qs.stats.max_drawdown, qs.stats.sharpe), export_to_dict for JSON per data-model.md Entity 8

#### CLI (Basic for US1)

- [x] T034 [US1] Implement CLI entry point in `src/cli/main.py` - argparse-based backtest subcommand, load config from YAML via BacktestConfiguration.from_yaml(), instantiate BacktestEngine, run backtest, display PerformanceReport metrics to console, handle errors gracefully with structured error messages

#### Logging & Storage

- [x] T035 [US1] Implement trade logging in `src/models/trade.py` - save_to_sqlite method: insert Trade.to_log_dict() into SQLite trade_log table with all fields (FR-038: date, stock_code, Bollinger values, band_width, signal type, portfolio snapshots), use timezone-aware timestamps (Asia/Seoul)
- [x] T036 [US1] Implement squeeze event logging in `src/indicators/squeeze.py` - save_to_sqlite method: insert SqueezeEvent into squeeze_events table (FR-042: detection date, width decrease %, direction bias)

**Checkpoint**: At this point, User Story 1 should be fully functional - run tests/integration/test_backtest_e2e.py to verify single-stock backtest with all acceptance criteria met

---

## Phase 4: User Story 2 - Multi-Stock Portfolio Management (Priority: P2)

**Goal**: Enable multi-stock backtests with portfolio-level risk controls and position size limits

**Independent Test**: Configure 3 stocks (005930, 000660, 035720), 30% max allocation each, run backtest, verify position sizing respects limits, total exposure doesn't exceed capital, portfolio-level metrics aggregate correctly

### Tests for User Story 2 (TDD - Write First) ⚠️

- [ ] T037 [P] [US2] **TEST**: Unit test for multi-stock position sizing in `tests/unit/test_risk.py` - verify allocation limits enforced across multiple stocks, insufficient capital handled correctly, ensure tests FAIL before T040
- [ ] T038 [P] [US2] **TEST**: Integration test for multi-stock backtest in `tests/integration/test_multi_stock.py` - 3 stocks, verify all 3 acceptance scenarios from spec.md US2 (simultaneous signals, capital constraints, aggregated metrics), ensure tests FAIL before T041

### Implementation for User Story 2

- [ ] T039 [US2] Extend BacktestConfiguration in `src/models/config.py` - add max_concurrent_positions field, total_portfolio_exposure_cap field, validate stocks list length (1-10 per plan.md Scale/Scope)
- [ ] T040 [US2] Extend Risk controls in `src/signals/risk.py` - add allocate_capital_across_stocks function: given multiple signals, allocate up to max_position_size_percent per stock, ensure total ≤ available cash, handle simultaneous signals (FR-P2 scenario 1), reduce position sizes if needed (FR-P2 scenario 2)
- [ ] T041 [US2] Extend Backtest engine in `src/backtest/engine.py` - modify run() to handle multiple stocks: loop over all stock_codes, calculate indicators for each, aggregate signals across stocks, apply multi-stock risk controls, use vectorbt multi-asset Portfolio, calculate portfolio-level metrics (FR-P2 scenario 3: overall win rate, portfolio MDD, aggregated Sharpe ratio)
- [ ] T042 [US2] Extend Performance metrics in `src/backtest/metrics.py` - add stock-level breakdown to PerformanceReport: per-stock returns, per-stock trade counts, correlation matrix (optional), ensure aggregated metrics correctly combine all positions

**Checkpoint**: User Stories 1 AND 2 should both work independently - verify with tests/integration/test_multi_stock.py

---

## Phase 5: User Story 3 - Historical Data Management (Priority: P3)

**Goal**: Automated data fetching, validation, and caching from Korean market sources

**Independent Test**: Request Samsung (005930) data for 2022-01-01 to 2024-12-31, verify OHLCV fetched, completeness validated (no missing days), outliers detected (>20% spike), data cached in Parquet

### Tests for User Story 3 (TDD - Write First) ⚠️

- [ ] T043 [P] [US3] **TEST**: Contract test for FinanceDataReader API in `tests/contract/test_data_sources.py` - verify API returns DataFrame with OHLCV columns, DatetimeIndex, positive values, OHLC relationships per contracts/data-source-api.md section 1, ensure tests FAIL before T048
- [ ] T044 [P] [US3] **TEST**: Contract test for pykrx API in `tests/contract/test_data_sources.py` - verify get_market_ohlcv_by_date returns data, column normalization (Korean→English), trading calendar fetch per contracts/data-source-api.md section 2, ensure tests FAIL before T048
- [ ] T045 [P] [US3] **TEST**: Unit test for data completeness validation in `tests/unit/test_validator.py` - verify validate_data_completeness detects missing trading days against KRX calendar, ensure tests FAIL before T050
- [ ] T046 [P] [US3] **TEST**: Unit test for outlier detection in `tests/unit/test_validator.py` - verify detect_price_outliers flags >20% price changes without volume spike (z-score<1), ensure tests FAIL before T050
- [ ] T047 [P] [US3] **TEST**: Integration test for data pipeline in `tests/integration/test_data_pipeline.py` - fetch Samsung 1-year data, validate, cache to Parquet, load from cache, verify all 3 acceptance scenarios from spec.md US3, ensure tests FAIL before pipeline complete

### Implementation for User Story 3

- [ ] T048 [P] [US3] Implement Data fetcher in `src/data/fetcher.py` - fetch_stock_data function: primary FinanceDataReader (fdr.DataReader), fallback pykrx (stock.get_market_ohlcv_by_date with column normalization), return StockData instance, handle errors (network timeout→retry 3x, invalid stock code→ValueError), fetch KRX trading calendar via pykrx per research.md section 1 & 2
- [ ] T049 [P] [US3] Implement Storage manager in `src/data/storage.py` - save_to_parquet function: write DataFrame to data/cache/{stock_code}_{start}_{end}.parquet via PyArrow with snappy compression, load_from_parquet function: read cached file, validate file age (<7 days per contracts/data-source-api.md 6.2), is_cache_valid function
- [ ] T050 [US3] Implement Data validator in `src/data/validator.py` - validate_data_completeness function: compare data dates against pykrx trading calendar, return (is_complete, missing_dates) per contracts/data-source-api.md 3.1, detect_price_outliers function: z-score analysis on daily returns and volume per contracts/data-source-api.md 3.2, update StockData.validation_status (VALID/OUTLIERS_DETECTED/INCOMPLETE)
- [ ] T051 [US3] Integrate data pipeline into Backtest engine in `src/backtest/engine.py` - modify run(): check cache first via load_from_parquet, if miss: fetch via fetch_stock_data, validate via validate_data_completeness + detect_price_outliers, save to cache, raise ValueError if incomplete data (FR-003), warn if outliers detected (FR-004)
- [ ] T052 [US3] Add CLI data management commands in `src/cli/main.py` - data fetch subcommand: fetch and cache data for stock codes, data refresh subcommand: force re-fetch ignoring cache, data validate subcommand: run validation and display outlier report

**Checkpoint**: Data pipeline fully automated - verify with tests/integration/test_data_pipeline.py, backtest can run without manual CSV files

---

## Phase 6: User Story 4 - Strategy Parameter Optimization (Priority: P4)

**Goal**: Test multiple parameter combinations to find optimal Bollinger Band settings

**Independent Test**: Define parameter grid (period: [10,20,30], std_dev: [1.5,2.0,2.5], threshold: [20%,30%,40%]), run 27 backtests on Samsung 1 year, rank by Sharpe ratio

### Tests for User Story 4 (TDD - Write First) ⚠️

- [ ] T053 [P] [US4] **TEST**: Unit test for parameter grid generation in `tests/unit/test_optimizer.py` - verify grid expansion (3x3x3=27 combinations), config cloning, ensure tests FAIL before T055
- [ ] T054 [P] [US4] **TEST**: Integration test for optimization workflow in `tests/integration/test_optimization.py` - verify all 2 acceptance scenarios from spec.md US4 (27 backtests executed, results ranked by Sharpe, negative returns included), ensure tests FAIL before T056

### Implementation for User Story 4

- [ ] T055 [US4] Implement Parameter optimizer in `src/backtest/optimizer.py` - ParameterOptimizer class: __init__(base_config, parameter_grid), expand_grid() method: generate all combinations (itertools.product), optimize() method: run backtest for each config, collect PerformanceReport for each, rank_results(metric='sharpe_ratio') method: sort by specified metric, top_n() method: return top N configs
- [ ] T056 [US4] Integrate optimizer into CLI in `src/cli/main.py` - optimize subcommand: load base config + parameter grid from YAML, run ParameterOptimizer.optimize(), display progress bar (1/27, 2/27...), save results to data/logs/optimization_{timestamp}.json with all configs + metrics, display top 3 configs to console
- [ ] T057 [US4] Add optimization result export in `src/backtest/optimizer.py` - export_results method: generate CSV with columns (period, std_dev, threshold, total_return, sharpe, win_rate, mdd, num_trades), enable filtering (e.g., only show configs with Sharpe > 1.0)

**Checkpoint**: Parameter optimization functional - run tests/integration/test_optimization.py to verify 27 backtests complete and rank correctly

---

## Phase 7: User Story 5 - Performance Reporting & Visualization (Priority: P5)

**Goal**: Visualizations for equity curve, drawdown, trade history, and Bollinger Bands with squeeze events

**Independent Test**: Run Samsung 1-year backtest, view report with (1) equity curve chart, (2) drawdown chart, (3) trade log table, (4) price chart with Bollinger Bands + buy/sell markers

### Tests for User Story 5 (TDD - Write First) ⚠️

- [ ] T058 [P] [US5] **TEST**: Unit test for visualization data preparation in `tests/unit/test_visualizer.py` - verify equity curve formatting, drawdown calculation, trade marker extraction, ensure tests FAIL before T060
- [ ] T059 [P] [US5] **TEST**: Integration test for full report generation in `tests/integration/test_visualization.py` - run backtest, generate all 4 chart types from spec.md US5 acceptance scenarios, save to HTML, ensure tests FAIL before T061

### Implementation for User Story 5

- [ ] T060 [P] [US5] Implement Visualization module in `src/backtest/visualizer.py` - VisualReportGenerator class: plot_equity_curve(portfolio, trades) using matplotlib/plotly: line chart with trade markers, plot_drawdown_chart(equity_curve) showing % drawdown over time, plot_price_with_bands(stock_data, bollinger_bands, trades, squeezes) with OHLC candlesticks + 3 Bollinger lines + shaded squeeze regions + green/red trade markers, plot_trade_log_table(trades) as formatted table
- [ ] T061 [US5] Integrate QuantStats HTML reports in `src/backtest/visualizer.py` - generate_html_report method: use QuantStats qs.reports.html(returns, output='report.html') for comprehensive tearsheet with all metrics, equity curve, drawdown, rolling metrics, monthly returns heatmap
- [ ] T062 [US5] Add visualize CLI command in `src/cli/main.py` - visualize subcommand: load PerformanceReport JSON from data/logs/report_{id}.json, generate all charts, save to data/logs/report_{id}.html, optionally open in browser (--open flag)

**Checkpoint**: All visualization features complete - verify with tests/integration/test_visualization.py, HTML report opens and displays all charts

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, final QA

- [ ] T063 [P] [Polish] Add performance benchmarks in `tests/benchmarks/` - pytest-benchmark tests: benchmark_bollinger_calculation (must complete <20ms for 250 days per research.md), benchmark_backtest_full (must complete <5s for 250 days per SC-002), benchmark_squeeze_detection (must complete <10ms per research.md)
- [ ] T064 [P] [Polish] Add property-based tests with hypothesis in `tests/unit/` - test_portfolio_invariants (cash always >=0, total_value always correct), test_position_invariants (quantity >0, market_value = quantity * price), test_bollinger_invariants (lower≤middle≤upper, width≥0), test_squeeze_invariants (width_decrease_pct calculation correctness)
- [ ] T065 [P] [Polish] Documentation updates - update README.md with installation instructions, usage examples, performance benchmarks, add docstrings to all public functions with type hints, generate API docs with Sphinx (optional)
- [ ] T066 [Polish] Code cleanup and refactoring - run Black formatter on all Python files, run mypy type checker (strict mode), run ruff linter, fix all linting errors, ensure consistent error handling (all raise ValueError/ValidationError with structured messages)
- [ ] T067 [Polish] Security hardening - validate all file paths to prevent directory traversal, sanitize stock codes before SQL queries (use parameterized queries), add rate limiting to data fetcher (max 10 requests/minute to avoid API blocks)
- [ ] T068 [Polish] Run quickstart.md validation - execute all commands from quickstart.md in clean environment, verify installation succeeds, verify first backtest completes in <15 minutes total (as promised in quickstart), update quickstart if any steps fail
- [ ] T069 [Polish] Create test fixtures in `tests/fixtures/` - sample_ohlcv.csv (synthetic 1-year daily data for deterministic testing), sample_configs/ directory with valid/invalid YAML examples for testing config validation, sample_squeeze_data.csv (known squeeze events for validating SC-004)
- [ ] T070 [Polish] Final integration smoke test - run full end-to-end backtest with default.yaml config, verify all logging works (trade_log.db populated, JSON reports exported), verify performance targets met (SC-001: <3 min user time, SC-002: <5s execution), verify deterministic execution (SC-010: run twice, identical results)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed) or sequentially in priority order (P1→P2→P3→P4→P5)
  - Each user story is independently testable
- **Polish (Phase 8)**: Depends on desired user stories being complete (minimum: US1 for MVP)

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) - **No dependencies on other stories** - Independent MVP
- **US2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 engine but independently testable
- **US3 (P3)**: Can start after Foundational (Phase 2) - Enhances data pipeline, US1 can work without it (manual CSV)
- **US4 (P4)**: Depends on US1 complete (needs backtest engine) - Independently testable
- **US5 (P5)**: Depends on US1 complete (needs PerformanceReport) - Independently testable

### Within Each User Story (TDD Order)

1. **Tests FIRST** (all marked **TEST**) - ensure they FAIL
2. Models (can parallelize if marked [P])
3. Services/business logic
4. Integration with other components
5. CLI commands (if applicable)
6. Verify tests now PASS

### Parallel Opportunities

- **Setup**: All tasks marked [P] can run in parallel (T003, T004, T005)
- **Foundation Tests**: T006, T007 can run in parallel
- **US1 Tests**: T012-T020 can all run in parallel (different test files)
- **US1 Models**: T022-T025 can run in parallel (different entities)
- **US1 Indicators**: T026 before T027, T027 before T028 (same file sequence)
- **US2**: Can start in parallel with US3, US4, US5 after US1 complete
- **Polish**: Most polish tasks (T063-T069) can run in parallel (different concerns)

---

## Parallel Example: User Story 1 Core

```bash
# Step 1: Launch all US1 tests together (TDD - these should FAIL):
Task T012: "Unit test Portfolio model in tests/unit/test_portfolio.py"
Task T013: "Unit test Position model in tests/unit/test_position.py"
Task T014: "Unit test Trade model in tests/unit/test_trade.py"
Task T015: "Unit test Bollinger Band calculation in tests/unit/test_bollinger.py"
Task T016: "Property-based test Bollinger with hypothesis"
Task T017: "Unit test Squeeze detection in tests/unit/test_squeeze.py"
Task T018: "Unit test Signal generation in tests/unit/test_signals.py"
Task T019: "Unit test Risk controls in tests/unit/test_risk.py"
Task T020: "Unit test Performance metrics in tests/unit/test_metrics.py"
Task T021: "Integration test E2E backtest in tests/integration/test_backtest_e2e.py"

# Step 2: Launch all US1 models together (after tests written):
Task T022: "Implement Portfolio model in src/models/portfolio.py"
Task T023: "Implement Position model in src/models/portfolio.py"
Task T024: "Implement Trade model in src/models/trade.py"
Task T025: "Implement StockData model in src/models/stock_data.py"

# Step 3: Indicators (sequential in same file):
Task T026: "Implement BollingerBand model in src/indicators/bollinger.py"
Task T027: "Implement Bollinger calculation in src/indicators/bollinger.py"
Task T028: "Implement Squeeze detection in src/indicators/squeeze.py"

# Step 4: Signals can run in parallel:
Task T029: "Implement Signal generator in src/signals/generator.py"
Task T030: "Implement Risk controls in src/signals/risk.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Fastest Path to Value)

1. Complete **Phase 1: Setup** (T001-T005)
2. Complete **Phase 2: Foundational** (T006-T011) ⚠️ **CRITICAL - BLOCKS US1**
3. Complete **Phase 3: User Story 1** (T012-T036)
   - Write ALL tests first (T012-T021), verify they FAIL
   - Implement models in parallel (T022-T025)
   - Implement indicators sequentially (T026-T028)
   - Implement signals in parallel (T029-T030)
   - Implement backtest engine (T031-T033)
   - Add CLI (T034)
   - Add logging (T035-T036)
4. **STOP and VALIDATE**: Run `pytest tests/integration/test_backtest_e2e.py` - all US1 acceptance criteria must pass
5. **Deploy/Demo MVP**: Single-stock backtest is now functional!

**Estimated Effort**: 40-50 tasks (Setup 5 + Foundation 6 + US1 25 + minimal polish)

### Incremental Delivery (Add Features Progressively)

1. **MVP**: Complete Setup + Foundation + US1 → Test independently → **DEMO** (single stock works!)
2. **v0.2**: Add US2 (T037-T042) → Test independently → **DEMO** (multi-stock works!)
3. **v0.3**: Add US3 (T043-T052) → Test independently → **DEMO** (automated data fetch works!)
4. **v0.4**: Add US4 (T053-T057) → Test independently → **DEMO** (parameter optimization works!)
5. **v0.5**: Add US5 (T058-T062) → Test independently → **DEMO** (visualizations work!)
6. **v1.0**: Complete Phase 8 (Polish) → Final QA → **RELEASE**

Each version adds value without breaking previous features - classic incremental delivery.

### Parallel Team Strategy (3 Developers)

With 3 developers after Foundation complete:

1. **Team completes Setup + Foundational together** (T001-T011) - everyone contributes
2. **Once Foundational done, split work**:
   - **Developer A**: User Story 1 (T012-T036) - core backtest engine (HIGHEST PRIORITY)
   - **Developer B**: User Story 2 (T037-T042) after US1 models ready + User Story 3 (T043-T052) in parallel
   - **Developer C**: Documentation, fixtures, polish tasks (T065, T069), then US4 after US1 complete
3. **Integration point**: All devs reconvene after US1-US3 complete, verify integration tests pass
4. **Final sprint**: US4, US5, remaining polish in parallel

---

## Task Count Summary

- **Setup**: 5 tasks (T001-T005)
- **Foundation**: 6 tasks (T006-T011) - **BLOCKING**
- **User Story 1 (MVP)**: 25 tasks (T012-T036) - 10 tests + 15 implementation
- **User Story 2**: 6 tasks (T037-T042) - 2 tests + 4 implementation
- **User Story 3**: 10 tasks (T043-T052) - 5 tests + 5 implementation
- **User Story 4**: 5 tasks (T053-T057) - 2 tests + 3 implementation
- **User Story 5**: 6 tasks (T058-T062) - 2 tests + 4 implementation
- **Polish**: 8 tasks (T063-T070)

**Total**: 70 tasks (21 test tasks + 49 implementation/polish tasks)

**Parallel Opportunities**: ~35 tasks marked [P] can run concurrently with proper staffing

**MVP Scope (US1 only)**: 36 tasks (Setup 5 + Foundation 6 + US1 25)

**Full Feature Set (US1-US5)**: 62 tasks (all except 8 polish tasks)

---

## Notes

- ✅ **Test-First Development (TDD) enforced** - Constitution Principle III (NON-NEGOTIABLE)
- All test tasks marked **TEST** must be written FIRST and verified to FAIL before implementation
- [P] tasks = different files, can run in parallel
- [Story] label maps task to user story for traceability
- Each user story independently completable and testable
- Constitutional requirements embedded: no lookahead bias (FR-014), defensive validation (Principle VII), structured logging (Principle V), configuration-driven (Principle VI)
- Performance targets validated in polish phase: <5s backtest (SC-002), <100ms indicators
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Focus on US1 for MVP** - delivers core value (single-stock backtest) with minimal dependencies

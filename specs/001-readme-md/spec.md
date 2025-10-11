# Feature Specification: Bollinger Band Auto-Trading Bot

**Feature Branch**: `001-readme-md`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "README.md 를 읽고 오토트레이딩 봇에대한 스펙을 작성하라"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Historical Backtesting Simulation (Priority: P1)

A trader wants to validate the Bollinger Band strategy using historical Korean stock market data before committing real capital. They configure initial capital, select target stocks, set Bollinger Band parameters, and run a simulation to see how the strategy would have performed.

**Why this priority**: This is the foundation of the system. Without backtesting capability, users cannot validate the strategy or build confidence. This delivers immediate value by answering "Would this strategy have worked?" and is essential for risk assessment.

**Independent Test**: Can be fully tested by loading historical data for a single stock (e.g., Samsung 005930), configuring strategy parameters, running a backtest for 1 year, and verifying performance metrics (total return, win rate, MDD, Sharpe ratio) are calculated correctly.

**Acceptance Scenarios**:

1. **Given** a trader has 10,000,000 KRW seed money and no existing positions, **When** they select Samsung (005930) stock, set Bollinger period to 20 days with 2 standard deviations, and run a backtest from 2023-01-01 to 2023-12-31, **Then** the system generates buy/sell signals based on band crossings, executes virtual trades, and displays final portfolio value, total return percentage, win rate, maximum drawdown, and Sharpe ratio.

2. **Given** historical data for a stock shows price touching the lower Bollinger Band on 2023-03-15, **When** the backtest engine processes this date and cash is available, **Then** a buy signal is generated, a position is opened at that day's closing price, and the transaction is logged with timestamp, price, quantity, and reason code.

3. **Given** the trader holds 10 shares of stock 005930 purchased at 60,000 KRW, **When** the price reaches the upper Bollinger Band at 70,000 KRW on 2023-06-20, **Then** a sell signal is generated, the position is closed, profit of 100,000 KRW is recorded, and portfolio cash balance is updated.

4. **Given** a trader configures stop-loss at 5%, **When** a held position loses more than 5% value, **Then** the position is automatically closed regardless of Bollinger Band position, the loss is recorded, and the stop-loss reason is logged.

---

### User Story 2 - Multi-Stock Portfolio Management (Priority: P2)

A trader wants to diversify risk by running the Bollinger Band strategy across multiple Korean stocks simultaneously with position size limits and portfolio-level risk controls.

**Why this priority**: Single-stock strategies carry concentration risk. Multi-stock portfolio management is critical for real-world trading but requires the core backtesting engine (P1) to be functional first.

**Independent Test**: Can be tested by configuring a portfolio with 3 stocks (e.g., 005930, 000660, 035720), allocating 30% maximum portfolio value per position, running a backtest, and verifying that position sizing respects limits, trades across stocks don't violate total capital constraints, and portfolio-level metrics aggregate correctly.

**Acceptance Scenarios**:

1. **Given** a trader has 10,000,000 KRW and selects 3 stocks with 30% max allocation per stock, **When** buy signals are generated for all 3 stocks simultaneously, **Then** the system allocates up to 3,000,000 KRW to each position, ensuring total exposure doesn't exceed available capital.

2. **Given** the portfolio holds positions in 2 stocks totaling 6,000,000 KRW exposure with 4,000,000 KRW cash remaining, **When** a third buy signal is generated requiring 5,000,000 KRW at 40% allocation, **Then** the system either skips the trade (insufficient capital) or reduces position size to fit within the 4,000,000 KRW constraint.

3. **Given** multiple stocks in the portfolio, **When** the backtest completes, **Then** the system displays aggregated portfolio metrics: total return, overall win rate, portfolio maximum drawdown, and Sharpe ratio calculated across all positions.

---

### User Story 3 - Historical Data Management (Priority: P3)

A trader needs to fetch, validate, and store historical Korean stock market data from reliable sources to ensure accurate backtesting without manual data preparation.

**Why this priority**: While essential for production use, initial backtesting can be done with manually prepared CSV files. Automated data fetching improves user experience but isn't required for MVP validation.

**Independent Test**: Can be tested by requesting historical data for a specific stock code (e.g., 005930) for a date range (2022-01-01 to 2023-12-31), verifying the system fetches OHLCV (Open, High, Low, Close, Volume) data, validates for completeness (no missing trading days), detects outliers (price spikes >20% without volume confirmation), and stores the data for reuse.

**Acceptance Scenarios**:

1. **Given** a trader enters stock code "005930" and date range 2023-01-01 to 2023-12-31, **When** they request data fetch, **Then** the system retrieves daily OHLCV data from a Korean market data source, validates there are no missing trading days, and confirms the data is ready for backtesting.

2. **Given** fetched data contains a day where closing price is 50% higher than previous day with normal volume, **When** the system validates the data, **Then** it flags this as a potential outlier, warns the user, and [NEEDS CLARIFICATION: should the system auto-correct, exclude the day, or just warn and proceed?].

3. **Given** historical data for a stock was fetched last week, **When** the trader runs a new backtest for the same date range, **Then** the system uses cached data without re-fetching, unless the user explicitly requests a refresh.

---

### User Story 4 - Strategy Parameter Optimization (Priority: P4)

A trader wants to test multiple Bollinger Band parameter combinations (e.g., periods of 10, 20, 30 days; standard deviations of 1.5, 2.0, 2.5) to identify the optimal configuration for a specific stock or portfolio.

**Why this priority**: Parameter optimization is valuable for advanced users but requires the core backtesting engine (P1) and stable performance metrics. It's an enhancement rather than a core requirement.

**Independent Test**: Can be tested by defining a parameter grid (period: [10, 20, 30], std_dev: [1.5, 2.0, 2.5]) for stock 005930 over 1 year, running 9 backtests (3×3 combinations), and comparing results to identify which parameter set yields the highest Sharpe ratio.

**Acceptance Scenarios**:

1. **Given** a trader selects stock 005930 and defines a parameter grid with 3 period values and 3 standard deviation values, **When** they run optimization, **Then** the system executes 9 separate backtests, ranks results by Sharpe ratio, and displays the top 3 parameter combinations with their performance metrics.

2. **Given** optimization runs 9 backtests, **When** one parameter combination results in negative returns, **Then** it is still included in the results table with clear indication of loss, allowing the trader to see which parameters to avoid.

---

### User Story 5 - Performance Reporting & Visualization (Priority: P5)

A trader wants to review detailed performance reports with visualizations showing equity curve, drawdown chart, trade history, and Bollinger Band signals overlaid on price charts to understand strategy behavior.

**Why this priority**: While valuable for analysis, basic numerical metrics (P1) are sufficient for initial validation. Visualization enhances understanding but isn't required for the strategy to function.

**Independent Test**: Can be tested by running a backtest for stock 005930 over 1 year, then viewing a report that includes: (1) line chart of portfolio value over time, (2) drawdown chart showing maximum drawdown periods, (3) trade log table with all entry/exit points, and (4) price chart with Bollinger Bands and buy/sell markers.

**Acceptance Scenarios**:

1. **Given** a completed backtest with 15 trades over 1 year, **When** the trader views the performance report, **Then** they see an equity curve showing portfolio value growth/decline over time, with clear markers indicating trade entry/exit points.

2. **Given** the strategy experienced a maximum drawdown of 12% from peak to trough, **When** the trader views the drawdown chart, **Then** they see a line graph starting at 0%, dropping to -12% at the lowest point, and recovering to show current drawdown status.

3. **Given** a backtest for stock 005930, **When** the trader views the price chart, **Then** they see candlesticks or line chart with three Bollinger Band lines (upper, middle, lower) overlaid, plus green markers for buy signals and red markers for sell signals at their actual execution dates.

---

### Edge Cases

- **Insufficient Capital for Trade**: What happens when a buy signal is generated but available cash is less than the minimum required for one share (e.g., share price 100,000 KRW but only 50,000 KRW available)? System should skip the trade and log the reason.

- **Data Gaps in Historical Series**: How does the system handle missing trading days (e.g., holidays, market closures) or data gaps in the middle of a backtest period? System should validate data completeness before backtesting and reject incomplete datasets or interpolate conservatively.

- **Extreme Volatility (Flash Crash)**: What happens when a stock price drops 30% in one day, triggering both stop-loss and a lower band crossing? System should prioritize stop-loss execution first, then ignore the lower band signal since the position was already closed.

- **Bollinger Band Calculation at Start**: How are Bollinger Bands calculated when there's insufficient historical data (e.g., 20-period moving average requires 20 days, but backtest starts on day 1)? System should either skip trading until minimum period is reached or use partial period calculation with a warning.

- **Simultaneous Buy/Sell Signals (Same Day)**: What happens if a stock's price crosses both upper and lower bands in the same trading session? System should process signals in chronological order (intraday if available) or use closing price as the reference point for daily data.

- **Position Already Open**: What happens when a buy signal is generated but the system already holds a position in that stock? System should either skip the signal (no pyramiding by default) or [NEEDS CLARIFICATION: allow position averaging/pyramiding up to a limit?].

- **Zero or Negative Cash Balance**: What happens if stop-losses or fees result in negative cash balance? System should enforce non-negative cash constraint and halt trading if balance approaches zero with mandatory reserve buffer.

## Requirements *(mandatory)*

### Functional Requirements

**Data Management**

- **FR-001**: System MUST allow users to configure a stock watchlist with Korean stock codes (6-digit KOSPI/KOSDAQ codes like "005930", "000660")
- **FR-002**: System MUST fetch historical OHLCV (Open, High, Low, Close, Volume) data for selected stocks with daily granularity at minimum
- **FR-003**: System MUST validate fetched data for completeness (no missing trading days within date range) before allowing backtesting
- **FR-004**: System MUST detect and flag price outliers (e.g., >20% single-day moves without corresponding volume increases)
- **FR-005**: System MUST persist historical data locally to avoid redundant fetches for repeated backtests

**Portfolio Configuration**

- **FR-006**: Users MUST be able to set initial seed money (cash balance at backtest start)
- **FR-007**: Users MUST be able to specify existing positions at backtest start (stock code, quantity, purchase price)
- **FR-008**: System MUST allow users to configure maximum position size as a percentage of total portfolio value (default 30%)
- **FR-009**: System MUST allow users to set stop-loss threshold as a percentage loss from purchase price (default 5%)
- **FR-010**: System MUST allow users to configure risk controls: maximum total portfolio exposure, maximum number of concurrent positions

**Bollinger Band Calculation**

- **FR-011**: System MUST calculate middle band (simple moving average) using user-specified period (default 20 periods)
- **FR-012**: System MUST calculate upper band as middle band + (standard deviation × multiplier), where multiplier is user-configurable (default 2.0)
- **FR-013**: System MUST calculate lower band as middle band - (standard deviation × multiplier)
- **FR-014**: System MUST use only historical data available up to each calculation date (no lookahead bias)
- **FR-015**: System MUST recalculate Bollinger Bands for each trading day in the backtest period

**Signal Generation**

- **FR-016**: System MUST generate a buy signal when closing price crosses below the lower Bollinger Band and no position is currently held
- **FR-017**: System MUST generate a sell signal when closing price crosses above the upper Bollinger Band and a position is currently held
- **FR-018**: System MUST generate a stop-loss sell signal when held position value drops below (purchase price × (1 - stop_loss_threshold))
- **FR-019**: System MUST prioritize stop-loss signals over Bollinger Band signals when both occur simultaneously

**Trade Execution (Simulated)**

- **FR-020**: System MUST execute buy orders using closing price of the signal day (or next day opening price if specified)
- **FR-021**: System MUST calculate position quantity as min(available_cash / share_price, max_position_size_in_shares)
- **FR-022**: System MUST update portfolio cash balance by subtracting (share_price × quantity) on buy execution
- **FR-023**: System MUST execute sell orders using closing price of the signal day and add proceeds to cash balance
- **FR-024**: System MUST record each trade with: timestamp, stock code, action (buy/sell), quantity, price, reason (band_lower, band_upper, stop_loss)
- **FR-025**: System MUST prevent trade execution if cash balance is insufficient for minimum one share purchase

**Performance Metrics**

- **FR-026**: System MUST calculate total return as ((final_portfolio_value - initial_capital) / initial_capital) × 100
- **FR-027**: System MUST calculate win rate as (number_of_profitable_trades / total_closed_trades) × 100
- **FR-028**: System MUST calculate maximum drawdown (MDD) as the largest peak-to-trough decline in portfolio value during the backtest period
- **FR-029**: System MUST calculate Sharpe ratio as (average_return - risk_free_rate) / standard_deviation_of_returns, assuming risk-free rate of 3% annualized
- **FR-030**: System MUST display performance metrics after backtest completion: total return, win rate, MDD, Sharpe ratio, total number of trades, final portfolio value

**Logging & Auditability**

- **FR-031**: System MUST log every trade decision with: date, stock code, Bollinger Band values (upper/middle/lower), closing price, signal type, action taken
- **FR-032**: System MUST maintain a trade history log showing all executed trades with entry/exit prices, holding period, and profit/loss per trade
- **FR-033**: System MUST log portfolio state changes: cash balance, position holdings, total portfolio value at each trade event
- **FR-034**: System MUST export trade logs and performance metrics in structured format (CSV or JSON)

**Configuration Management**

- **FR-035**: System MUST load configuration from a file specifying: seed_money, stock_list, bollinger_period, bollinger_std_dev, stop_loss_percent, max_position_size_percent, initial_positions
- **FR-036**: Users MUST be able to save and load multiple configuration presets for different strategies
- **FR-037**: System MUST validate configuration values: positive seed money, valid stock codes, positive Bollinger parameters, stop-loss between 0-100%, position size between 0-100%

### Key Entities

- **Portfolio**: Represents the trader's account state at any point in time. Contains cash balance (KRW), list of open positions, total portfolio value (cash + position values), and historical equity curve.

- **Position**: Represents ownership of shares in a specific stock. Contains stock code, quantity of shares, purchase price per share, purchase date, current market value, and unrealized profit/loss.

- **Trade**: Represents a completed transaction. Contains trade ID, stock code, action (buy/sell), execution price, quantity, execution timestamp, reason code (band_lower, band_upper, stop_loss), and profit/loss (for sells).

- **Stock Data**: Represents historical market data for a single stock. Contains stock code, date range, and time series of OHLCV values (Open, High, Low, Close, Volume) indexed by date.

- **Bollinger Band**: Represents calculated indicator values for a specific stock on a specific date. Contains calculation date, middle band value (moving average), upper band value, lower band value, and the parameters used (period, standard deviation multiplier).

- **Backtest Configuration**: Represents user-defined strategy parameters. Contains initial capital, stock watchlist, date range, Bollinger Band parameters (period, std_dev), risk parameters (stop-loss %, max position size), and initial positions.

- **Performance Report**: Represents the outcome of a backtest. Contains final portfolio value, total return percentage, win rate, maximum drawdown, Sharpe ratio, number of trades executed, trade history list, and equity curve data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a single-stock backtest (configure parameters, load data, run simulation, view results) in under 3 minutes for 1 year of daily data
- **SC-002**: System processes 1 year of daily historical data (250 trading days) and completes backtesting with signal generation and trade execution in under 5 seconds
- **SC-003**: Bollinger Band calculations produce mathematically correct results: middle band equals 20-period simple moving average, upper/lower bands equal middle ± (2 × standard deviation), verified against manual calculations or reference libraries
- **SC-004**: Performance metrics (total return, win rate, MDD, Sharpe ratio) match industry-standard calculation methods, validated against a reference implementation or manual verification
- **SC-005**: 100% of trades are logged with complete information (timestamp, price, quantity, reason, portfolio state before/after)
- **SC-006**: Stop-loss mechanism prevents losses from exceeding configured threshold (e.g., if 5% stop-loss is set, no closed trade should show >5.5% loss accounting for execution slippage)
- **SC-007**: Multi-stock backtests correctly enforce portfolio constraints: no single position exceeds max allocation, total exposure never exceeds available capital, and aggregate metrics reflect combined performance
- **SC-008**: System detects and alerts users to at least 95% of data quality issues (missing dates, outlier prices) before backtesting begins
- **SC-009**: Users can reproduce identical backtest results when running the same configuration multiple times (deterministic execution)
- **SC-010**: Backtest results include sufficient detail for audit: trade log, portfolio snapshots, and Bollinger Band values at decision points are exportable and human-readable

### Assumptions

- **Data Source Availability**: Historical Korean stock market data is accessible via public APIs or datasets (e.g., KRX API, FinanceDataReader, Yahoo Finance Korea). If unavailable, users can manually provide CSV files in a specified format.

- **Trading Hours**: Korean stock market trading hours (09:00-15:30 KST) and holidays follow official KRX calendar. For backtesting purposes, only trading days are considered (non-trading days are excluded from data).

- **Transaction Costs**: Initial implementation assumes zero transaction costs (no commissions, no slippage). Future iterations may add configurable cost models. This is documented as a simplification for MVP.

- **Execution Model**: Trades execute at closing price of the signal day. This assumes liquidity is available at closing price without slippage. Intraday price fluctuations are ignored for daily backtesting.

- **Risk-Free Rate**: Sharpe ratio calculation uses South Korean government bond rate (assumed 3% annualized) as the risk-free rate. Users cannot configure this in MVP but it's documented.

- **Single Account**: System models a single portfolio/account. No support for multiple accounts, sub-portfolios, or account consolidation in MVP.

- **Long-Only Strategy**: System only supports buying and selling stocks (long positions). Short selling is not supported.

- **Market Orders Only**: Simulated trades execute as market orders at closing price. No support for limit orders, stop orders, or other order types.

- **No Corporate Actions**: Stock splits, dividends, mergers, and other corporate actions are not handled in MVP. Data is assumed to be adjusted for splits if necessary.

- **Educational Purpose**: This system is for backtesting and research only. It does not connect to live trading APIs or execute real trades. Users acknowledge full responsibility for any real trading decisions.

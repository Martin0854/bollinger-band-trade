<!--
Sync Impact Report
==================
Version change: Initial → 1.0.0
New constitution established with 7 core principles

Added sections:
- Core Principles (7 principles defined)
- Risk Management & Compliance
- Development Workflow
- Governance

Templates status:
- ✅ plan-template.md: Constitution Check section aligned
- ✅ spec-template.md: Requirements structure compatible
- ✅ tasks-template.md: Task categorization supports all principles
- ✅ agent-file-template.md: Generic guidance maintained
- ✅ checklist-template.md: Checklist generation compatible

Follow-up TODOs:
- None - all placeholders filled with concrete values
-->

# Bollinger Band Trading Bot Constitution

## Core Principles

### I. Data Integrity First

All historical market data MUST be validated before use in calculations or backtesting. Data pipelines MUST include:
- Source verification (exchange/API authenticity)
- Completeness checks (no missing time periods)
- Outlier detection (anomalous price/volume spikes)
- Timestamp consistency (correct timezone handling)

**Rationale**: Financial decisions based on corrupted or incomplete data can lead to catastrophic losses. Data quality is non-negotiable in trading systems.

### II. Risk Management by Design

Every trading decision MUST enforce configurable risk controls:
- Maximum position size limits per trade
- Stop-loss thresholds MUST be honored automatically
- Total portfolio exposure caps
- Drawdown circuit breakers (halt trading on excessive losses)

**Rationale**: Automated trading without hard risk limits can result in uncontrolled losses. Risk management cannot be optional or post-hoc—it must be architectural.

### III. Test-First Development (NON-NEGOTIABLE)

All trading logic, indicator calculations, and position management MUST follow strict TDD:
1. Write test cases defining expected behavior
2. User/stakeholder approves test scenarios
3. Verify tests fail initially
4. Implement feature
5. Verify tests pass
6. Red-Green-Refactor cycle enforced

**Rationale**: Financial algorithms require mathematical precision. Test-first development catches calculation errors before they affect real capital.

### IV. Backtesting Integrity

Backtesting simulations MUST prevent lookahead bias and data snooping:
- Indicator calculations MUST use only past data available at that timestamp
- No future information leakage in signal generation
- Separate datasets for training/optimization vs. validation
- Transaction costs (slippage, commissions) MUST be included

**Rationale**: Overfitted backtests with lookahead bias create false confidence. Realistic simulations require strict temporal boundaries.

### V. Transparency & Auditability

All trading decisions, calculations, and state changes MUST be logged:
- Bollinger Band values (upper, middle, lower) at decision time
- Position entry/exit prices and timestamps
- Reason codes for each trade (signal type, rule triggered)
- Portfolio state before/after each transaction
- Structured logging format (JSON preferred) for analysis

**Rationale**: Post-mortem analysis and regulatory compliance require complete audit trails. Debugging trading logic demands full observability.

### VI. Configuration Over Code

Trading parameters MUST be externalized in configuration files:
- Bollinger Band period and standard deviation multiplier
- Risk parameters (stop-loss %, position size limits)
- Stock universe and market hours
- Initial capital and existing positions

Code changes MUST NOT be required for parameter tuning.

**Rationale**: Traders need rapid iteration on strategy parameters without redeployment. Configuration separation enables A/B testing and safe experimentation.

### VII. Defensive Validation

All external inputs MUST be validated before processing:
- Market data: price ranges, volume sanity checks
- User configuration: positive values, logical constraints
- API responses: schema validation, error handling
- State transitions: valid position changes only

Fail fast with clear error messages. Invalid states MUST halt execution.

**Rationale**: Financial systems cannot tolerate undefined behavior. Validation at boundaries prevents cascading failures.

## Risk Management & Compliance

### Legal & Ethical Boundaries

- This system is for EDUCATIONAL and RESEARCH purposes only
- Real-money trading requires explicit user acknowledgment of risks
- Disclaimer MUST be displayed prominently in all interfaces
- No guarantees of profitability—past performance ≠ future results
- Users retain full responsibility for trading decisions

### Performance Standards

- Indicator calculations MUST complete within 100ms for real-time data
- Backtesting MUST process 1 year of daily data within 5 seconds
- Position updates MUST be atomic (all-or-nothing state changes)
- Memory usage MUST stay under 500MB for typical workloads

### Data Storage Requirements

- Trade history MUST be persisted durably (database or file)
- Configuration files MUST use human-readable formats (JSON/YAML)
- Backups MUST be restorable to exact portfolio state
- Personal data (if any) MUST comply with data protection regulations

## Development Workflow

### Code Review Gates

All PRs MUST pass:
1. **Constitution compliance check**: Risk controls present, tests included, logging added
2. **Backtesting validation**: New strategies tested against historical data with realistic costs
3. **Performance benchmarks**: No regressions in calculation speed
4. **Documentation**: Algorithm explanations, parameter guidance

### Testing Requirements

- **Unit tests**: Bollinger Band calculations, signal generation logic
- **Integration tests**: End-to-end backtest scenarios, portfolio state management
- **Contract tests**: Market data API response handling
- **Edge case coverage**: Division by zero, empty datasets, extreme volatility

### Complexity Justification

Any introduction of the following MUST be explicitly justified:
- Machine learning models (overfitting risk, interpretability loss)
- Multi-asset strategies (correlation complexities)
- High-frequency trading logic (latency/infrastructure demands)
- External dependencies beyond standard data libraries

Simpler solutions MUST be evaluated first. Complexity requires documented rationale.

## Governance

### Amendment Procedure

Constitution changes require:
1. Proposed amendment documented with rationale
2. Impact analysis on existing templates and codebase
3. Approval from project maintainers
4. Version bump per semantic versioning rules
5. Synchronization of dependent artifacts

### Versioning Policy

- **MAJOR**: Breaking changes to risk management principles, removal of core safeguards
- **MINOR**: New principles added, expanded guidance on existing rules
- **PATCH**: Clarifications, wording improvements, typo fixes

### Compliance Reviews

- All feature branches MUST pass constitution check before implementation
- Quarterly audits of trade logs and risk control effectiveness
- Annual review of constitution relevance to project evolution

**Version**: 1.0.0 | **Ratified**: 2025-10-11 | **Last Amended**: 2025-10-11

# bollinger-band-trade Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-05

## Active Technologies
- Python 3.11+ + pandas, numpy, pydantic (validation), yfinance (data), pyyaml (config) (005-signal-strategy-v2)
- JSON files (portfolio_state.json, backtest results), TXT (stock lists), CSV cache (data/) (005-signal-strategy-v2)
- Python 3.11+ + pandas, yfinance, SQLAlchemy, FastAPI (006-advanced-sell-strategy)
- SQLite/PostgreSQL via SQLAlchemy ORM, JSON files for portfolio state (006-advanced-sell-strategy)

- Python 3.11+ (Backend), TypeScript 5.x (Frontend) (004-trading-wizard-web)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (Backend), TypeScript 5.x (Frontend): Follow standard conventions

## Recent Changes
- 006-advanced-sell-strategy: Added Python 3.11+ + pandas, yfinance, SQLAlchemy, FastAPI
- 005-signal-strategy-v2: Added Python 3.11+ + pandas, numpy, pydantic (validation), yfinance (data), pyyaml (config)

- 004-trading-wizard-web: Added Python 3.11+ (Backend), TypeScript 5.x (Frontend)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

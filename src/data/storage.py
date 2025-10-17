"""
SQLite database schema initialization and Parquet storage utilities.
Implements:
- FR-038: Trade logging with complete information
- FR-042: Squeeze event logging
- plan.md: Parquet cache for historical data
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd


def initialize_database(db_path: str = "data/logs/backtest.db") -> None:
    """
    Initialize SQLite database with required tables and indexes.

    Creates tables:
    - trade_log: All executed trades (FR-038)
    - squeeze_events: All detected squeeze events (FR-042)
    - portfolio_snapshots: Portfolio state at each trade
    - backtest_results: Summary metrics for each backtest run

    Args:
        db_path: Path to SQLite database file
    """
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 1: Trade Log (FR-038)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            trade_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            reason TEXT,
            bollinger_upper REAL,
            bollinger_middle REAL,
            bollinger_lower REAL,
            band_width REAL,
            squeeze_status TEXT,
            portfolio_value_before REAL,
            portfolio_value_after REAL,
            cash_after REAL,
            realized_pnl REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trade_timestamp
        ON trade_log(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trade_stock_code
        ON trade_log(stock_code)
    """)

    # Table 2: Squeeze Events (FR-042)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS squeeze_events (
            event_id TEXT PRIMARY KEY,
            stock_code TEXT NOT NULL,
            detection_date TEXT NOT NULL,
            band_width_at_detection REAL NOT NULL,
            band_width_N_days_ago REAL NOT NULL,
            width_decrease_pct REAL NOT NULL,
            lookback_days INTEGER NOT NULL,
            threshold_pct REAL NOT NULL,
            direction_bias TEXT,
            expansion_confirmed_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_squeeze_stock_code
        ON squeeze_events(stock_code)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_squeeze_detection_date
        ON squeeze_events(detection_date)
    """)

    # Table 3: Portfolio Snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_run_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            cash_balance REAL NOT NULL,
            total_value REAL NOT NULL,
            num_positions INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshot_run_id
        ON portfolio_snapshots(backtest_run_id)
    """)

    # Table 4: Backtest Results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            report_id TEXT PRIMARY KEY,
            backtest_date TEXT NOT NULL,
            config_yaml TEXT,
            final_portfolio_value REAL NOT NULL,
            total_return_pct REAL NOT NULL,
            win_rate_pct REAL,
            max_drawdown_pct REAL,
            sharpe_ratio REAL,
            num_trades INTEGER NOT NULL,
            num_squeeze_events INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_to_parquet(
    df: pd.DataFrame,
    stock_code: str,
    start_date: date,
    end_date: date,
    cache_dir: str = "data/cache"
) -> str:
    """
    Save DataFrame to Parquet file with compression.

    Args:
        df: DataFrame to save
        stock_code: Stock code
        start_date: Data start date
        end_date: Data end date
        cache_dir: Cache directory path

    Returns:
        Path to saved Parquet file
    """
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    filename = f"{stock_code}_{start_date}_{end_date}.parquet"
    filepath = Path(cache_dir) / filename

    df.to_parquet(filepath, engine='pyarrow', compression='snappy')

    return str(filepath)


def load_from_parquet(
    stock_code: str,
    start_date: date,
    end_date: date,
    cache_dir: str = "data/cache"
) -> Optional[pd.DataFrame]:
    """
    Load DataFrame from Parquet cache.

    Args:
        stock_code: Stock code
        start_date: Data start date
        end_date: Data end date
        cache_dir: Cache directory path

    Returns:
        DataFrame if cache exists, None otherwise
    """
    filename = f"{stock_code}_{start_date}_{end_date}.parquet"
    filepath = Path(cache_dir) / filename

    if not filepath.exists():
        return None

    return pd.read_parquet(filepath, engine='pyarrow')


def is_cache_valid(
    stock_code: str,
    start_date: date,
    end_date: date,
    max_age_days: int = 7,
    cache_dir: str = "data/cache"
) -> bool:
    """
    Check if cached Parquet file is valid (exists and not too old).

    Args:
        stock_code: Stock code
        start_date: Data start date
        end_date: Data end date
        max_age_days: Maximum cache age in days (default: 7)
        cache_dir: Cache directory path

    Returns:
        True if cache is valid, False otherwise
    """
    filename = f"{stock_code}_{start_date}_{end_date}.parquet"
    filepath = Path(cache_dir) / filename

    if not filepath.exists():
        return False

    # Check file age
    import datetime
    mod_time = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
    age_days = (datetime.datetime.now() - mod_time).days

    return age_days < max_age_days

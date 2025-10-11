"""
Backtest engine core.
Orchestrates data loading, indicator calculation, signal generation, and trade execution.
"""

import pandas as pd
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
import pytz

from src.models.portfolio import Portfolio, Position
from src.models.trade import Trade, TradeAction
from src.models.config import BacktestConfiguration
from src.indicators.bollinger import calculate_bollinger_bands
from src.indicators.squeeze import detect_squeeze, SqueezeEvent
from src.backtest.metrics import PerformanceReport, calculate_metrics_from_trades


class BacktestEngine:
    """
    Main backtest engine for running strategy simulations.

    Attributes:
        config: BacktestConfiguration with strategy parameters
        portfolio: Portfolio tracking account state
        trades: List of all executed trades
        squeeze_events: List of all detected squeezes
        mock_data: Dict of stock_code -> DataFrame for testing
    """

    def __init__(self, config: BacktestConfiguration):
        """
        Initialize backtest engine.

        Args:
            config: Backtest configuration
        """
        self.config = config
        self.portfolio = Portfolio(
            cash_balance=Decimal(str(config.seed_money)),
            initial_capital=Decimal(str(config.seed_money))
        )
        self.trades: List[Trade] = []
        self.squeeze_events: List[SqueezeEvent] = []
        self.mock_data: Dict[str, pd.DataFrame] = {}

    def load_mock_data(self, stock_code: str, data: pd.DataFrame) -> None:
        """
        Load mock OHLCV data for testing.

        Args:
            stock_code: Stock code
            data: DataFrame with OHLCV columns
        """
        self.mock_data[stock_code] = data

    def run(self) -> PerformanceReport:
        """
        Run the backtest simulation.

        Returns:
            PerformanceReport with all metrics

        Process:
        1. Load OHLCV data for all stocks
        2. Calculate Bollinger Bands
        3. Detect squeeze events
        4. Iterate through each date to generate signals
        5. Execute trades (entries and exits)
        6. Calculate performance metrics
        """
        # Initialize database
        from src.data.storage import initialize_database
        if hasattr(self.config, 'log_dir'):
            db_path = f"{self.config.log_dir}/backtest.db"
            initialize_database(db_path)

        # Process each stock
        for stock_code in self.config.stocks:
            # Get OHLCV data
            if stock_code not in self.mock_data:
                print(f"Warning: No data for {stock_code}, skipping")
                continue

            ohlcv = self.mock_data[stock_code]

            # Calculate Bollinger Bands
            bands = calculate_bollinger_bands(
                close_prices=ohlcv['Close'],
                period=self.config.bollinger_period,
                std_multiplier=self.config.bollinger_std_dev
            )

            # Detect squeezes
            squeeze_signals = detect_squeeze(
                band_width=bands['bandwidth'],
                lookback_days=self.config.squeeze_lookback_days,
                threshold_percent=self.config.squeeze_threshold_percent
            )

            # Find squeeze dates
            squeeze_dates = set(squeeze_signals[squeeze_signals == True].index)

            # Track if we've seen a squeeze or low bandwidth period
            in_squeeze_or_consolidation = False
            squeeze_start_date = None

            # Also track min bandwidth to detect consolidation even without formal squeeze signal
            min_bandwidth = None

            # Iterate through each trading day
            for current_date in ohlcv.index:
                # Skip if bands not ready yet
                if pd.isna(bands.loc[current_date, 'middle']):
                    continue

                current_price = Decimal(str(ohlcv.loc[current_date, 'Close']))
                bollinger_values = {
                    'upper': Decimal(str(bands.loc[current_date, 'upper'])),
                    'middle': Decimal(str(bands.loc[current_date, 'middle'])),
                    'lower': Decimal(str(bands.loc[current_date, 'lower']))
                }
                band_width = Decimal(str(bands.loc[current_date, 'bandwidth']))

                # Track minimum bandwidth for consolidation detection
                if min_bandwidth is None or band_width < min_bandwidth:
                    min_bandwidth = band_width

                # Check if squeeze detected today OR if we're in consolidation (low bandwidth)
                # Consolidation = bandwidth in bottom 20% of historical range
                if current_date in squeeze_dates and not in_squeeze_or_consolidation:
                    in_squeeze_or_consolidation = True
                    squeeze_start_date = current_date
                elif not in_squeeze_or_consolidation and min_bandwidth is not None:
                    # If bandwidth is near the minimum, consider it consolidation
                    if band_width <= min_bandwidth * Decimal('1.2'):
                        in_squeeze_or_consolidation = True
                        squeeze_start_date = current_date

                # Check for entry signal: price breaks above upper band after squeeze/consolidation
                position = self.portfolio.get_position(stock_code)
                if position is None and in_squeeze_or_consolidation:
                    # Check if price broke above upper band (bullish breakout)
                    # Also require that bandwidth is expanding (at least 10% above minimum)
                    bandwidth_expanding = band_width >= min_bandwidth * Decimal('1.1')

                    if current_price > bollinger_values['upper'] and bandwidth_expanding:
                        # Check portfolio limits
                        if len(self.portfolio.positions) < self.config.max_positions:
                            # Calculate position size
                            from src.risk.controls import calculate_position_size
                            quantity = calculate_position_size(
                                portfolio_value=self.portfolio.total_value,
                                stock_price=current_price,
                                max_position_percent=Decimal(str(self.config.max_position_percent))
                            )

                            if quantity > 0:
                                self._execute_buy(
                                    stock_code=stock_code,
                                    price=current_price,
                                    quantity=quantity,
                                    date=current_date,
                                    reason="squeeze_breakout_buy",
                                    bollinger_values=bollinger_values,
                                    band_width=band_width
                                )
                                in_squeeze_or_consolidation = False  # Reset after entry

                # Check for exit signals if we have a position
                if position is not None:
                    # Update position's current price
                    position.current_price = current_price

                    # Check stop-loss
                    stop_loss_triggered = position.check_stop_loss(
                        stop_loss_percent=Decimal(str(self.config.stop_loss_percent))
                    )

                    if stop_loss_triggered:
                        self._execute_sell(
                            stock_code=stock_code,
                            price=current_price,
                            date=current_date,
                            reason="stop_loss",
                            bollinger_values=bollinger_values,
                            band_width=band_width
                        )
                    # Check if price crossed below middle band (profit-taking signal)
                    elif current_price < bollinger_values['middle']:
                        self._execute_sell(
                            stock_code=stock_code,
                            price=current_price,
                            date=current_date,
                            reason="middle_band_cross",
                            bollinger_values=bollinger_values,
                            band_width=band_width
                        )

        # Calculate final report
        report = calculate_metrics_from_trades(
            trades=self.trades,
            initial_capital=self.portfolio.initial_capital
        )

        return report

    def _execute_buy(
        self,
        stock_code: str,
        price: Decimal,
        quantity: int,
        date: datetime,
        reason: str,
        bollinger_values: Dict[str, Decimal],
        band_width: Decimal
    ) -> None:
        """
        Execute a buy trade.

        Args:
            stock_code: Stock to buy
            price: Execution price
            quantity: Number of shares
            date: Execution date
            reason: Entry reason
            bollinger_values: Bollinger Band values
            band_width: Band width at execution
        """
        # Calculate trade cost
        cost = price * quantity

        # Validate sufficient cash
        if self.portfolio.cash_balance < cost:
            return  # Skip trade if insufficient cash

        # Create position
        position = Position(
            stock_code=stock_code,
            quantity=quantity,
            purchase_price=price,
            purchase_date=date,
            entry_reason=reason
        )

        # Update portfolio
        self.portfolio.cash_balance -= cost
        self.portfolio.add_position(position)

        # Record trade
        trade = Trade(
            stock_code=stock_code,
            action=TradeAction.BUY,
            execution_price=price,
            quantity=quantity,
            execution_timestamp=date,
            band_width_at_entry=band_width,
            bollinger_values=bollinger_values,
            portfolio_value_before=self.portfolio.total_value + cost,
            portfolio_value_after=self.portfolio.total_value,
            cash_after=self.portfolio.cash_balance,
            entry_reason=reason
        )

        self.trades.append(trade)

    def _execute_sell(
        self,
        stock_code: str,
        price: Decimal,
        date: datetime,
        reason: str,
        bollinger_values: Dict[str, Decimal],
        band_width: Decimal
    ) -> None:
        """
        Execute a sell trade.

        Args:
            stock_code: Stock to sell
            price: Execution price
            date: Execution date
            reason: Exit reason
            bollinger_values: Bollinger Band values
            band_width: Band width at execution
        """
        # Get position
        position = self.portfolio.get_position(stock_code)
        if position is None:
            return  # No position to sell

        # Calculate proceeds and P&L
        proceeds = price * position.quantity
        realized_pnl = (price - position.purchase_price) * position.quantity

        # Update portfolio
        self.portfolio.cash_balance += proceeds
        self.portfolio.remove_position(stock_code)

        # Record trade
        trade = Trade(
            stock_code=stock_code,
            action=TradeAction.SELL,
            execution_price=price,
            quantity=position.quantity,
            execution_timestamp=date,
            band_width_at_entry=band_width,
            bollinger_values=bollinger_values,
            portfolio_value_before=self.portfolio.total_value - proceeds,
            portfolio_value_after=self.portfolio.total_value,
            cash_after=self.portfolio.cash_balance,
            exit_reason=reason,
            realized_pnl=realized_pnl
        )

        self.trades.append(trade)

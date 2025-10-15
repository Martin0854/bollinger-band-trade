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
from src.models.trade import Trade, TradeAction, EnhancedSignal
from src.models.config import BacktestConfiguration
from src.indicators.bollinger import calculate_bollinger_bands
from src.indicators.squeeze import detect_squeeze, SqueezeEvent
from src.indicators.volume import VolumeFilter
from src.indicators.momentum import RSIIndicator
from src.signals.generator import EnhancedSignalGenerator
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
        volume_filter: Optional VolumeFilter instance
        rsi_indicator: Optional RSIIndicator instance
        signal_generator: EnhancedSignalGenerator for filtering signals
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

        # Initialize enhanced strategy filters (FR-001, FR-003)
        self.volume_filter: Optional[VolumeFilter] = None
        self.rsi_indicator: Optional[RSIIndicator] = None

        # Initialize filters from config
        if hasattr(config, 'enhanced_strategy') and config.enhanced_strategy is not None:
            # Initialize Volume Filter (User Story 1)
            if config.enhanced_strategy.volume_filter.enabled:
                self.volume_filter = VolumeFilter(
                    window_days=config.enhanced_strategy.volume_filter.window_days,
                    multiplier=config.enhanced_strategy.volume_filter.multiplier
                )

            # Initialize RSI Indicator (User Story 2)
            if config.enhanced_strategy.rsi.enabled:
                self.rsi_indicator = RSIIndicator(
                    period=config.enhanced_strategy.rsi.period,
                    overbought=config.enhanced_strategy.rsi.overbought,
                    oversold=config.enhanced_strategy.rsi.oversold
                )

        # Initialize EnhancedSignalGenerator
        confidence_threshold = 60  # Default
        if hasattr(config, 'enhanced_strategy') and config.enhanced_strategy is not None:
            confidence_threshold = config.enhanced_strategy.confidence.threshold

        self.signal_generator = EnhancedSignalGenerator(
            volume_filter=self.volume_filter,
            rsi_indicator=self.rsi_indicator,
            macd_indicator=None,  # Phase 2
            confidence_threshold=confidence_threshold
        )

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

            # Calculate Volume Average (for Volume Filter)
            volume_avg = None
            if self.volume_filter is not None and 'Volume' in ohlcv.columns:
                volume_avg = self.volume_filter.calculate_average_volume(ohlcv['Volume'])

            # Calculate RSI (for RSI Filter)
            rsi_values = None
            if self.rsi_indicator is not None:
                rsi_values = self.rsi_indicator.calculate(ohlcv['Close'])

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
                        # Get current volume and RSI for filtering
                        current_volume = None
                        avg_volume_value = None
                        rsi_value = None

                        if volume_avg is not None and 'Volume' in ohlcv.columns:
                            current_volume = float(ohlcv.loc[current_date, 'Volume'])
                            avg_volume_value = float(volume_avg.loc[current_date]) if current_date in volume_avg.index else None

                        if rsi_values is not None and current_date in rsi_values.index:
                            rsi_value = float(rsi_values.loc[current_date])

                        # Use EnhancedSignalGenerator to filter signal (FR-002, FR-004, FR-006, FR-007)
                        enhanced_signal = self.signal_generator.generate_enhanced_signal(
                            date=current_date,
                            stock_code=stock_code,
                            signal_type='BUY',
                            reason='squeeze_breakout_buy',
                            price=current_price,
                            bollinger_values=bollinger_values,
                            current_volume=current_volume,
                            avg_volume=avg_volume_value,
                            rsi_value=rsi_value,
                            macd_value=None  # Phase 2
                        )

                        # Only execute if signal passes filters
                        if enhanced_signal is not None:
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
                                        band_width=band_width,
                                        enhanced_signal=enhanced_signal
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
        # Get backtest start/end dates from config for accurate CAGR
        from datetime import datetime
        backtest_start = None
        backtest_end = None

        if hasattr(self.config, 'date_range') and self.config.date_range:
            # Handle both string and date objects
            start_val = self.config.date_range[0]
            end_val = self.config.date_range[1]

            if isinstance(start_val, str):
                backtest_start = datetime.strptime(start_val, '%Y-%m-%d')
            elif hasattr(start_val, 'year'):  # date or datetime object
                backtest_start = datetime(start_val.year, start_val.month, start_val.day)

            if isinstance(end_val, str):
                backtest_end = datetime.strptime(end_val, '%Y-%m-%d')
            elif hasattr(end_val, 'year'):  # date or datetime object
                backtest_end = datetime(end_val.year, end_val.month, end_val.day)

        report = calculate_metrics_from_trades(
            trades=self.trades,
            initial_capital=self.portfolio.initial_capital,
            backtest_start_date=backtest_start,
            backtest_end_date=backtest_end
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
        band_width: Decimal,
        enhanced_signal: Optional['EnhancedSignal'] = None
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
            enhanced_signal: Optional EnhancedSignal with filter results
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

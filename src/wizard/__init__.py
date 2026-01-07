"""
Daily Trading Wizard module.
Generates next-day buy/sell recommendations based on Bollinger Band strategy.
"""

from src.wizard.portfolio_manager import (
    PortfolioManager,
    WizardPortfolioState,
    WizardPosition,
    TradeRecord,
    PendingOrder,
)
from src.wizard.signal_scanner import SignalScanner, StockSignal
from src.wizard.recommendation import (
    RecommendationEngine,
    BuyRecommendation,
    SellRecommendation,
)

__all__ = [
    "PortfolioManager",
    "WizardPortfolioState",
    "WizardPosition",
    "TradeRecord",
    "PendingOrder",
    "SignalScanner",
    "StockSignal",
    "RecommendationEngine",
    "BuyRecommendation",
    "SellRecommendation",
]

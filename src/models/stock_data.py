"""
StockData model (DEPRECATED - use MarketData instead).
This module provides backward compatibility for existing code.
"""

# Import MarketData and alias it as StockData for backward compatibility
from src.models.market_data import MarketData as StockData

__all__ = ["StockData"]

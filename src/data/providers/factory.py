"""Factory for creating market data providers based on market type."""

from src.data.providers.base import MarketDataProvider


class DataProviderFactory:
    """
    Factory for instantiating the appropriate market data provider.

    Provides a single entry point for creating providers based on market type.
    This enables automatic provider selection without manual management.
    """

    @staticmethod
    def create_provider(market_type: str) -> MarketDataProvider:
        """
        Create and return the appropriate data provider for the given market type.

        Args:
            market_type: Market type ("stock" or "crypto")

        Returns:
            MarketDataProvider instance for the specified market

        Raises:
            ValueError: If market_type is not supported
        """
        import logging
        
        if market_type == "stock":
            from src.data.providers.stock_provider import YahooFinanceStockProvider
            provider = YahooFinanceStockProvider()
            logging.info(f"DataProviderFactory: Selected YahooFinanceStockProvider for market_type='{market_type}'")
            return provider
        elif market_type == "crypto":
            from src.data.providers.crypto_provider import BinanceCryptoProvider
            provider = BinanceCryptoProvider()
            logging.info(f"DataProviderFactory: Selected BinanceCryptoProvider for market_type='{market_type}'")
            return provider
        else:
            logging.error(f"DataProviderFactory: Unsupported market_type='{market_type}'")
            raise ValueError(
                f"Unsupported market_type: '{market_type}'. Must be 'stock' or 'crypto'"
            )

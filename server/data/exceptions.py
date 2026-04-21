"""Domain errors for market and external data providers."""


class MarketDataUnavailableError(RuntimeError):
    """Raised when no real OHLCV/quote could be fetched (synthetic data disabled)."""

class HotelSearchError(Exception):
    """Base error for hotel search agent."""


class AdapterUnavailableError(HotelSearchError):
    """Raised when adapter cannot run in current environment."""


class AdapterParsingError(HotelSearchError):
    """Raised when adapter page structure cannot be parsed."""

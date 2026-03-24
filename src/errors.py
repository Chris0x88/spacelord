"""
Space Lord Errors
=============

Standardized exception hierarchy for the Space Lord application.
These exceptions separate "expected failures" (User error, Market conditions)
from "unexpected crashes" (Bugs).
"""

class SpaceLordError(Exception):
    """Base class for all Space Lord exceptions."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ConfigurationError(SpaceLordError):
    """Raised when the environment or config is invalid."""
    pass

class TokenNotFoundError(SpaceLordError):
    """Raised when a requested token symbol cannot be resolved."""
    pass

class RouteNotFoundError(SpaceLordError):
    """Raised when no valid swap path exists between tokens."""
    pass

class InsufficientFundsError(SpaceLordError):
    """Raised when the wallet lacks funds for the operation."""
    pass

class ExecutionError(SpaceLordError):
    """Raised when a transaction fails on-chain or during simulation."""
    pass

class UserCancelledError(SpaceLordError):
    """Raised when the user declines a confirmation prompt."""
    pass

class SlippageExceededError(SpaceLordError):
    """Raised when slippage exceeds user's configured maximum."""
    pass

class PriceFetchError(SpaceLordError):
    """Raised when price data cannot be fetched from APIs."""
    pass

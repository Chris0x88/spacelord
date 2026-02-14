"""
Pacman Errors
=============

Standardized exception hierarchy for the Pacman application.
These exceptions separate "expected failures" (User error, Market conditions)
from "unexpected crashes" (Bugs).
"""

class PacmanError(Exception):
    """Base class for all Pacman exceptions."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ConfigurationError(PacmanError):
    """Raised when the environment or config is invalid."""
    pass

class TokenNotFoundError(PacmanError):
    """Raised when a requested token symbol cannot be resolved."""
    pass

class RouteNotFoundError(PacmanError):
    """Raised when no valid swap path exists between tokens."""
    pass

class InsufficientFundsError(PacmanError):
    """Raised when the wallet lacks funds for the operation."""
    pass

class ExecutionError(PacmanError):
    """Raised when a transaction fails on-chain or during simulation."""
    pass

class UserCancelledError(PacmanError):
    """Raised when the user declines a confirmation prompt."""
    pass

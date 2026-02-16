# Backward compatibility shim - import from new location
from src.config import PacmanConfig, SecureString, ConfigurationError

__all__ = ['PacmanConfig', 'SecureString', 'ConfigurationError']

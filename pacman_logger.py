# Backward compatibility shim - import from new location
from src.logger import logger, set_verbose, setup_logger

__all__ = ['logger', 'set_verbose', 'setup_logger']

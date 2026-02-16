# Backward compatibility shim - import from new location
from lib.prices import price_manager, PacmanPriceManager

__all__ = ['price_manager', 'PacmanPriceManager']

# Backward compatibility shim - import from new location
from src.router import PacmanVariantRouter, VariantRoute, RouteStep

__all__ = ['PacmanVariantRouter', 'VariantRoute', 'RouteStep']

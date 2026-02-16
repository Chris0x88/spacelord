# Backward compatibility shim - import from new location
from src.translator import translate, resolve_token, load_static_aliases, load_dynamic_aliases

__all__ = ['translate', 'resolve_token', 'load_static_aliases', 'load_dynamic_aliases']

# Backward compatibility shim - import from new location
from src.executor import PacmanExecutor, ExecutionResult

__all__ = ['PacmanExecutor', 'ExecutionResult']

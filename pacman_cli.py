# Backward compatibility shim - import from new location
from cli.main import main, cli

__all__ = ['main', 'cli']

if __name__ == "__main__":
    main()

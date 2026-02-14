import logging
import sys
from pathlib import Path

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name: str, log_file: str = "pacman.log", level=logging.INFO):
    """Set up a logger that outputs to both a file and the console."""
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler
    file_handler = logging.FileHandler(LOG_DIR / log_file)
    file_handler.setFormatter(formatter)

    # Console Handler (cleaner for CLI)
    console_handler = logging.StreamHandler(sys.stdout)
    # If level is DEBUG, show more detail in console
    if level == logging.DEBUG:
        console_handler.setFormatter(logging.Formatter('\033[90m[DEBUG] %(message)s\033[0m'))
    else:
        console_handler.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def set_verbose(enabled: bool = True):
    """Dynamically switch to verbose logging."""
    lvl = logging.DEBUG if enabled else logging.INFO
    logger.setLevel(lvl)
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            if enabled:
                h.setFormatter(logging.Formatter('\033[90m[DEBUG] %(message)s\033[0m'))
            else:
                h.setFormatter(logging.Formatter('%(message)s'))

# Primary app logger
logger = setup_logger("pacman")

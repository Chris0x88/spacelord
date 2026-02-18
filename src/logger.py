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

# Primary app logger (Console + File)
logger = setup_logger("pacman")

# UI Mirror Logger (File ONLY)
# We create a child logger or separate logger that only has the file handler
ui_logger = logging.getLogger("pacman.ui")
ui_logger.setLevel(logging.INFO)
ui_logger.propagate = False # Prevent double-logging to parent 'pacman' handlers

# Add ONLY the file handler to ui_logger
_file_formatter = logging.Formatter('%(asctime)s | UI | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_file_h = logging.FileHandler(LOG_DIR / "pacman.log")
_file_h.setFormatter(_file_formatter)
ui_logger.addHandler(_file_h)

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

def log_ui(message: str):
    """
    Log a UI message to the file without ANSI colors.
    Useful for mirroring the CLI experience in logs.
    """
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_message = ansi_escape.sub('', str(message))
    ui_logger.info(clean_message)

class MirrorStream:
    """Wraps a stream (like stdout) to also write to the logger."""
    def __init__(self, original_stream):
        self.original_stream = original_stream
        import re
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, data):
        self.original_stream.write(data)
        if data and data.strip():
            # Strip colors for the log file
            clean_data = self.ansi_escape.sub('', data)
            if clean_data.strip():
                # Write to the file-only ui_logger
                ui_logger.info(clean_data.strip())

    def flush(self):
        self.original_stream.flush()

def setup_mirror():
    """Redirect stdout to MirrorStream to capture all CLI output."""
    import sys
    if not isinstance(sys.stdout, MirrorStream):
        sys.stdout = MirrorStream(sys.stdout)

"""Project logger: Console + One rotating log file, configured once."""

import logging 
import sys
from logging.handlers import RotatingFileHandler

from .config import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3                # rotated files to keep
LOGGER_NAME = "ecommerce"
FORMAT = "[%(asctime)s] %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

def configure_logger(level = logging.INFO, to_file = True):
    """Configure the project logger once; later calls return the same logger."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:            # already configured (re-import, autoreload)
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False        # keep third-party logs out of our handlers
    formatter = logging.Formatter(FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if to_file:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes= MAX_LOG_SIZE,
                                           backupCount= BACKUP_COUNT, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def get_logger(name = None):
    """Return a child logger, for example get_logger('data_cleaning')."""
    configure_logger()
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)
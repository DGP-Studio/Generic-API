import logging
import os
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for Windows compatibility
colorama_init(autoreset=True)

log_dir = "log"
os.makedirs(log_dir, exist_ok=True)

# Formatter config
log_format = '%(levelname)s: %(asctime)s | %(name)s | %(funcName)s:%(lineno)d %(connector)s %(message)s'
date_format = '%Y-%m-%dT%H:%M:%S %z'


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        reset = Style.RESET_ALL
        record.levelname = f"{color}{record.levelname}{reset}"
        record.name = f"{Fore.GREEN}{record.name}{reset}"
        record.msg = f"{Fore.YELLOW + Style.BRIGHT}{record.msg}{reset}"
        record.connector = f"{Fore.YELLOW + Style.BRIGHT}->{reset}"
        return super().format(record)


def compress_old_log(source_path):
    gz_path = f"{source_path}.gz"
    with open(source_path, 'rb') as src_file:
        with gzip.open(gz_path, 'wb') as gz_file:
            shutil.copyfileobj(src_file, gz_file)
    os.remove(source_path)
    return gz_path


def setup_logger():
    logger = logging.getLogger()
    log_level = logging.INFO
    logger.setLevel(log_level)

    if logger.handlers:
        return logger  # Prevent duplicate handlers

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter(fmt=log_format, datefmt=date_format))
    logger.addHandler(console_handler)

    # File handler
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="H",
        interval=1,
        backupCount=168,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    def custom_namer(name):
        if name.endswith(".log"):
            compress_old_log(name)
        return name

    file_handler.namer = custom_namer
    logger.addHandler(file_handler)

    logger.propagate = False  # Optional: prevent bubbling to root

    return logger


# This will configure the root logger on first import
setup_logger()


# Modules should use this:
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

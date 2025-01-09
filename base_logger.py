import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

log_dir = "log"
os.makedirs(log_dir, exist_ok=True)


# Generate log file name
def get_log_filename():
    current_time = datetime.now().strftime("%Y-%m-%d_%H")
    return os.path.join(log_dir, f"{current_time}.log")


# Compose log file
def compress_old_log(source_path):
    gz_path = f"{source_path}.gz"
    with open(source_path, 'rb') as src_file:
        with gzip.open(gz_path, 'wb') as gz_file:
            shutil.copyfileobj(src_file, gz_file)
    os.remove(source_path)
    return gz_path


# Logging format
log_format = '%(levelname)s | %(asctime)s | %(name)s | %(funcName)s:%(lineno)d %(connector)s %(message)s'
date_format = '%Y-%m-%dT%H:%M:%S %z (%Z)'


# Define custom colors for each log level
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


# Create logger instance
logger = logging.getLogger()
log_level = logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO
logger.setLevel(log_level)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_formatter = ColoredFormatter(fmt=log_format, datefmt=date_format)
console_handler.setFormatter(console_formatter)

# Create file handler
log_file = get_log_filename()
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, "app.log"),
    when="H",  # Split log file every hour
    interval=1,  # Split log file every hour
    backupCount=168,  # Keep 7 days of logs
    encoding="utf-8"
)

file_handler.setLevel(log_level)

# Use a plain formatter for the file handler
file_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
file_handler.setFormatter(file_formatter)


# Custom log file namer with log compression
def custom_namer(name):
    if name.endswith(".log"):
        compress_old_log(name)
    return name


file_handler.namer = custom_namer

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

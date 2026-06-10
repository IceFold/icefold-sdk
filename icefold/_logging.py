import logging
from typing import Any


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Colors.GREEN,
        logging.INFO: Colors.BLUE,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Colors.RESET)
        formatted = super().format(record)
        return f"{color}{formatted}{Colors.RESET}"


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter(
    fmt='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
# We ship our own handler, so don't also bubble records to the root logger —
# otherwise anything that configures a root handler (e.g. alembic's
# ``fileConfig`` during the backend's startup migration) makes every line log
# twice. Persistence/fan-out hooks live on the call seam, not on propagation.
logger.propagate = False


def log_info(category: str, message: str, **kwargs: Any) -> None:
    extra_info = ""
    if kwargs:
        extra_parts = [f"{k}={v}" for k, v in kwargs.items()]
        extra_info = " | " + ", ".join(extra_parts)

    log_message = f"[{category}] {message}{extra_info}"
    logger.info(log_message)


def log_error(category: str, message: str, **kwargs: Any) -> None:
    extra_info = ""
    if kwargs:
        extra_parts = [f"{k}={v}" for k, v in kwargs.items()]
        extra_info = " | " + ", ".join(extra_parts)

    log_message = f"[{category}] {message}{extra_info}"
    logger.error(log_message)

    # Persisting errors (beyond stderr) is the server's job; on the server a
    # log_error override fans this out to its error sink.


def log_warning(category: str, message: str, **kwargs: Any) -> None:
    extra_info = ""
    if kwargs:
        extra_parts = [f"{k}={v}" for k, v in kwargs.items()]
        extra_info = " | " + ", ".join(extra_parts)

    log_message = f"[{category}] {message}{extra_info}"
    logger.warning(log_message)


def log_debug(category: str, message: str, **kwargs: Any) -> None:
    extra_info = ""
    if kwargs:
        extra_parts = [f"{k}={v}" for k, v in kwargs.items()]
        extra_info = " | " + ", ".join(extra_parts)

    log_message = f"[{category}] {message}{extra_info}"
    logger.debug(log_message)


if __name__ == "__main__":
    log_info("TEST", "info-level log line", user="alice")
    log_warning("TEST", "warning-level log line")
    log_error("TEST", "error-level log line", code=500)
    log_debug("TEST", "debug-level log line")
    print("logger: OK")

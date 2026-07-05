import logging
import os
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

    def __init__(self, *args: Any, use_color: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        formatted = super().format(record)
        # Only wrap in ANSI when the stream is a real terminal; a redirected
        # stream (systemd journal, log file, pipe) would otherwise get raw
        # escape codes littered through it.
        if not self.use_color:
            return formatted
        color = self.COLORS.get(record.levelno, Colors.RESET)
        return f"{color}{formatted}{Colors.RESET}"


handler = logging.StreamHandler()
_use_color = bool(getattr(handler.stream, "isatty", None)) and handler.stream.isatty()
handler.setFormatter(ColoredFormatter(
    fmt='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    use_color=_use_color,
))

logger = logging.getLogger(__name__)
# Default to INFO (not DEBUG) so importing the SDK doesn't force verbose logging
# on every consumer; override with ICEFOLD_LOG_LEVEL (e.g. DEBUG) when needed.
logger.setLevel(os.environ.get("ICEFOLD_LOG_LEVEL", "INFO").upper())
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

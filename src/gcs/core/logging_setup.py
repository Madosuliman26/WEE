import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level="INFO", log_file="logs/gcs.log", max_bytes=1_000_000, backup_count=3):
    root = logging.getLogger()
    root.setLevel(level)

    # if called twice, remove our old handlers first so lines are not printed twice
    for handler in list(root.handlers):
        if getattr(handler, "_gcs", False):
            root.removeHandler(handler)
            handler.close()

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(threadName)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    console_handler = logging.StreamHandler()

    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        handler._gcs = True
        root.addHandler(handler)


if __name__ == "__main__":
    setup_logging(level="DEBUG")
    log = logging.getLogger("demo")
    log.debug("debug message")
    log.info("info message")
    log.warning("warning message")
    log.error("error message")
import logging
from logging.handlers import RotatingFileHandler

import pytest

from gcs.core.logging_setup import setup_logging


def our_handlers():
    return [h for h in logging.getLogger().handlers if getattr(h, "_gcs", False)]


def flush_all():
    for handler in our_handlers():
        handler.flush()


@pytest.fixture(autouse=True)
def restore_root_logger():
    root = logging.getLogger()
    old_level = root.level
    yield
    for handler in our_handlers():
        root.removeHandler(handler)
        handler.close()
    root.setLevel(old_level)


@pytest.fixture
def log_file(tmp_path):
    return tmp_path / "logs" / "gcs.log"


def test_creates_the_log_folder_and_file(log_file):
    setup_logging(log_file=str(log_file))

    logging.getLogger("t").info("hello")
    flush_all()

    assert log_file.exists()
    assert "hello" in log_file.read_text(encoding="utf-8")


def test_adds_a_rotating_file_handler_and_a_console_handler(log_file):
    setup_logging(log_file=str(log_file))

    handlers = our_handlers()

    assert len(handlers) == 2
    assert any(isinstance(h, RotatingFileHandler) for h in handlers)
    assert any(type(h) is logging.StreamHandler for h in handlers)


def test_calling_twice_does_not_duplicate_handlers(log_file):
    setup_logging(log_file=str(log_file))
    setup_logging(log_file=str(log_file))

    assert len(our_handlers()) == 2


def test_default_level_is_info(log_file):
    setup_logging(log_file=str(log_file))

    assert logging.getLogger().level == logging.INFO


def test_level_is_applied(log_file):
    setup_logging(level="WARNING", log_file=str(log_file))

    assert logging.getLogger().level == logging.WARNING


def test_messages_below_the_level_are_not_written(log_file):
    setup_logging(level="WARNING", log_file=str(log_file))

    logging.getLogger("t").info("quiet")
    logging.getLogger("t").warning("loud")
    flush_all()

    text = log_file.read_text(encoding="utf-8")
    assert "quiet" not in text
    assert "loud" in text


def test_rotation_settings_are_applied(log_file):
    setup_logging(log_file=str(log_file), max_bytes=500, backup_count=2)

    handler = next(h for h in our_handlers() if isinstance(h, RotatingFileHandler))

    assert handler.maxBytes == 500
    assert handler.backupCount == 2


def test_file_rotates_when_it_gets_too_big(log_file):
    setup_logging(log_file=str(log_file), max_bytes=200, backup_count=2)

    for _ in range(30):
        logging.getLogger("t").info("x" * 50)
    flush_all()

    assert (log_file.parent / "gcs.log.1").exists()


def test_line_contains_level_thread_and_logger_name(log_file):
    setup_logging(log_file=str(log_file))

    logging.getLogger("demo.module").warning("check")
    flush_all()

    text = log_file.read_text(encoding="utf-8")
    assert "WARNING" in text
    assert "[MainThread]" in text
    assert "demo.module" in text
    assert "check" in text
import json
import logging

import pytest

from gcs.core.config import ConfigManager


def write_config(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "settings.json"
    write_config(
        path,
        {"input": {"rate_hz": 50, "default_deadzone": 0.1}, "logging": {"level": "INFO"}},
    )
    return path


# ---------- get ----------

def test_get_returns_value_from_file(config_file):
    config = ConfigManager(config_file)
    config.load()

    assert config.get("input.rate_hz") == 50
    assert config.get("logging.level") == "INFO"


def test_get_missing_key_returns_default(config_file):
    config = ConfigManager(config_file)
    config.load()

    assert config.get("input.nope", 10) == 10


def test_get_missing_key_without_default_returns_none(config_file):
    config = ConfigManager(config_file)
    config.load()

    assert config.get("input.nope") is None


def test_get_missing_section_returns_default(config_file):
    config = ConfigManager(config_file)
    config.load()

    assert config.get("network.rov_ip", "0.0.0.0") == "0.0.0.0"


def test_get_inside_a_value_that_is_not_a_section_returns_default(config_file):
    config = ConfigManager(config_file)
    config.load()

    assert config.get("input.rate_hz.extra", "x") == "x"


def test_get_before_load_returns_default(config_file):
    config = ConfigManager(config_file)

    assert config.get("input.rate_hz", 50) == 50


# ---------- load failures ----------

def test_missing_file_logs_warning_and_does_not_crash(tmp_path, caplog):
    config = ConfigManager(tmp_path / "nope.json")

    with caplog.at_level(logging.WARNING):
        config.load()

    assert "not found" in caplog.text
    assert config.get("input.rate_hz", 50) == 50


def test_invalid_json_logs_error_and_does_not_crash(tmp_path, caplog):
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json", encoding="utf-8")
    config = ConfigManager(path)

    with caplog.at_level(logging.ERROR):
        config.load()

    assert "not valid JSON" in caplog.text
    assert config.get("input.rate_hz", 50) == 50


# ---------- reload ----------

def test_reload_picks_up_changed_value(config_file):
    config = ConfigManager(config_file)
    config.load()

    write_config(config_file, {"input": {"rate_hz": 25}})
    config.reload()

    assert config.get("input.rate_hz") == 25


def test_invalid_json_on_reload_keeps_previous_values(config_file):
    config = ConfigManager(config_file)
    config.load()

    config_file.write_text("{ broken", encoding="utf-8")
    config.reload()

    assert config.get("input.rate_hz") == 50


def test_missing_file_on_reload_keeps_previous_values(config_file):
    config = ConfigManager(config_file)
    config.load()

    config_file.unlink()
    config.reload()

    assert config.get("input.rate_hz") == 50
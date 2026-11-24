import copy
import json
import logging
import os
import time

import pytest

from gcs.core.event_bus import EventBus
from gcs.core.events import ControllerConnected, ProfileChanged
from gcs.input.profiles import ProfileManager

DATA = {
    "default_profile": "keyboard_default",
    "controller_map": {"Wireless Controller": "pilot_ps4"},
    "profiles": {
        "pilot_ps4": {
            "buttons": {"cross": "claw_toggle"},
            "axes": {"righty": "surge"},
            "invert": ["righty"],
        },
        "keyboard_default": {"keys": {"w": "surge_forward"}},
    },
}


# ---------- helpers ----------

def write_profiles(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def touch_newer(path):
    """Give the file a newer modification time, so a change is always noticed."""
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 10))


def wait_until(condition, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def profiles_file(tmp_path):
    path = tmp_path / "profiles.json"
    write_profiles(path, DATA)
    return path


@pytest.fixture
def bus():
    b = EventBus()
    b.start()
    yield b
    b.stop()


# ---------- loading ----------

def test_load_selects_the_default_profile(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    assert manager.active_name == "keyboard_default"


def test_mapping_has_every_section_even_if_the_profile_omits_it(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    mapping = manager.get_mapping()

    assert mapping["keys"] == {"w": "surge_forward"}
    assert mapping["buttons"] == {}
    assert mapping["axes"] == {}
    assert mapping["invert"] == []


def test_missing_file_does_not_crash(tmp_path, caplog):
    manager = ProfileManager(tmp_path / "nope.json")

    with caplog.at_level(logging.WARNING):
        manager.load()

    assert "not found" in caplog.text
    assert manager.active_name is None


def test_invalid_json_at_start_does_not_crash(tmp_path, caplog):
    path = tmp_path / "profiles.json"
    path.write_text("{ not json", encoding="utf-8")
    manager = ProfileManager(path)

    with caplog.at_level(logging.ERROR):
        manager.load()

    assert "not valid JSON" in caplog.text
    assert manager.active_name is None


# ---------- switching ----------

def test_set_active_switches_the_mapping(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    assert manager.set_active("pilot_ps4") is True

    assert manager.active_name == "pilot_ps4"
    assert manager.get_mapping()["buttons"] == {"cross": "claw_toggle"}


def test_set_active_unknown_profile_keeps_the_old_one(profiles_file, caplog):
    manager = ProfileManager(profiles_file)
    manager.load()

    with caplog.at_level(logging.WARNING):
        assert manager.set_active("does_not_exist") is False

    assert manager.active_name == "keyboard_default"
    assert "unknown profile" in caplog.text


def test_profile_for_known_controller(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    assert manager.profile_for_controller("Wireless Controller") == "pilot_ps4"


def test_profile_for_unknown_controller_is_the_default(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    assert manager.profile_for_controller("Some Other Pad") == "keyboard_default"


# ---------- events and auto-load ----------

def test_set_active_publishes_profile_changed(bus, profiles_file):
    received = []
    bus.subscribe(ProfileChanged, received.append)
    manager = ProfileManager(profiles_file, bus)

    manager.load()
    manager.set_active("pilot_ps4")

    assert wait_until(lambda: len(received) == 2)
    assert [(e.profile, e.reason) for e in received] == [
        ("keyboard_default", "load"),
        ("pilot_ps4", "manual"),
    ]


def test_connecting_a_known_controller_loads_its_profile(bus, profiles_file):
    manager = ProfileManager(profiles_file, bus)
    manager.load()

    bus.publish(ControllerConnected("Wireless Controller"))

    assert wait_until(lambda: manager.active_name == "pilot_ps4")


def test_auto_load_publishes_a_change_with_reason_auto(bus, profiles_file):
    received = []
    bus.subscribe(ProfileChanged, received.append)
    manager = ProfileManager(profiles_file, bus)
    manager.load()

    bus.publish(ControllerConnected("Wireless Controller"))

    assert wait_until(lambda: any(e.reason == "auto" for e in received))


def test_connecting_an_unknown_controller_loads_the_default(bus, profiles_file):
    received = []
    bus.subscribe(ProfileChanged, received.append)
    manager = ProfileManager(profiles_file, bus)
    manager.load()
    manager.set_active("pilot_ps4")

    bus.publish(ControllerConnected("Some Other Pad"))

    assert wait_until(lambda: manager.active_name == "keyboard_default")


def test_unknown_controller_without_a_default_logs_a_warning(bus, tmp_path, caplog):
    data = copy.deepcopy(DATA)
    del data["default_profile"]
    path = tmp_path / "profiles.json"
    write_profiles(path, data)
    manager = ProfileManager(path, bus)
    manager.load()

    with caplog.at_level(logging.WARNING):
        bus.publish(ControllerConnected("Some Other Pad"))
        assert wait_until(lambda: "no profile for controller" in caplog.text)

    assert manager.active_name is None


# ---------- live reload ----------

def test_check_for_changes_returns_false_when_nothing_changed(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    assert manager.check_for_changes() is False


def test_edited_file_is_reloaded(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()
    manager.set_active("pilot_ps4")

    edited = copy.deepcopy(DATA)
    edited["profiles"]["pilot_ps4"]["buttons"] = {"cross": "lights"}
    write_profiles(profiles_file, edited)
    touch_newer(profiles_file)

    assert manager.check_for_changes() is True
    assert manager.active_name == "pilot_ps4"
    assert manager.get_mapping()["buttons"] == {"cross": "lights"}


def test_reload_publishes_profile_changed_with_reason_file_edit(bus, profiles_file):
    received = []
    bus.subscribe(ProfileChanged, received.append)
    manager = ProfileManager(profiles_file, bus)
    manager.load()

    edited = copy.deepcopy(DATA)
    edited["profiles"]["keyboard_default"]["keys"] = {"w": "something_else"}
    write_profiles(profiles_file, edited)
    touch_newer(profiles_file)
    manager.check_for_changes()

    assert wait_until(lambda: any(e.reason == "file_edit" for e in received))


def test_broken_edit_keeps_the_old_mapping(profiles_file, caplog):
    manager = ProfileManager(profiles_file)
    manager.load()
    manager.set_active("pilot_ps4")

    profiles_file.write_text("{ broken", encoding="utf-8")
    touch_newer(profiles_file)
    with caplog.at_level(logging.ERROR):
        manager.check_for_changes()

    assert "not valid JSON" in caplog.text
    assert manager.active_name == "pilot_ps4"
    assert manager.get_mapping()["buttons"] == {"cross": "claw_toggle"}


def test_broken_file_is_reported_once_not_on_every_check(profiles_file, caplog):
    manager = ProfileManager(profiles_file)
    manager.load()

    profiles_file.write_text("{ broken", encoding="utf-8")
    touch_newer(profiles_file)
    with caplog.at_level(logging.ERROR):
        manager.check_for_changes()
        manager.check_for_changes()
        manager.check_for_changes()

    assert caplog.text.count("not valid JSON") == 1


def test_fixing_the_file_after_a_broken_edit_reloads_it(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()

    profiles_file.write_text("{ broken", encoding="utf-8")
    touch_newer(profiles_file)
    manager.check_for_changes()

    edited = copy.deepcopy(DATA)
    edited["profiles"]["pilot_ps4"]["buttons"] = {"cross": "fixed"}
    write_profiles(profiles_file, edited)
    touch_newer(profiles_file)
    touch_newer(profiles_file)
    manager.check_for_changes()
    manager.set_active("pilot_ps4")

    assert manager.get_mapping()["buttons"] == {"cross": "fixed"}


def test_active_profile_removed_from_the_file_falls_back_to_the_default(profiles_file):
    manager = ProfileManager(profiles_file)
    manager.load()
    manager.set_active("pilot_ps4")

    edited = copy.deepcopy(DATA)
    del edited["profiles"]["pilot_ps4"]
    write_profiles(profiles_file, edited)
    touch_newer(profiles_file)
    manager.check_for_changes()

    assert manager.active_name == "keyboard_default"
import pytest

from gcs.input import keyboard as keyboard_module
from gcs.input.keyboard import KeyboardInput, key_name


# ---------- fakes ----------

class CharKey:
    """Looks like a pynput key for a letter, digit or symbol."""

    def __init__(self, char):
        self.char = char


class NamedKey:
    """Looks like a pynput special key (space, shift, arrows)."""

    def __init__(self, name):
        self.name = name


class FakeListener:
    def __init__(self, on_press, on_release):
        self.on_press = on_press
        self.on_release = on_release
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture
def kb(monkeypatch):
    monkeypatch.setattr(keyboard_module.keyboard, "Listener", FakeListener)
    return KeyboardInput()


# ---------- key_name ----------

@pytest.mark.parametrize(
    "key, expected",
    [
        (CharKey("w"), "w"),
        (CharKey("W"), "w"),      # Shift held: still lowercase
        (CharKey("5"), "5"),
        (NamedKey("space"), "space"),
        (NamedKey("shift"), "shift"),
    ],
)
def test_key_name(key, expected):
    assert key_name(key) == expected


def test_key_name_falls_back_to_str_for_unknown_objects():
    class Odd:
        def __str__(self):
            return "odd-key"

    assert key_name(Odd()) == "odd-key"


# ---------- KeyboardInput ----------

def test_name_is_keyboard(kb):
    assert kb.name == "keyboard"


def test_listener_is_started(kb):
    assert kb._listener.started


def test_nothing_pressed_at_start(kb):
    assert kb.poll() == {"keys": []}


def test_key_down_appears_in_poll(kb):
    kb._on_press(CharKey("w"))

    assert kb.poll() == {"keys": ["w"]}


def test_key_up_removes_it(kb):
    kb._on_press(CharKey("w"))
    kb._on_release(CharKey("w"))

    assert kb.poll() == {"keys": []}


def test_several_keys_at_once_are_sorted(kb):
    kb._on_press(CharKey("w"))
    kb._on_press(CharKey("a"))
    kb._on_press(NamedKey("space"))

    assert kb.poll() == {"keys": ["a", "space", "w"]}


def test_releasing_one_key_keeps_the_others(kb):
    kb._on_press(CharKey("w"))
    kb._on_press(CharKey("a"))
    kb._on_release(CharKey("w"))

    assert kb.poll() == {"keys": ["a"]}


def test_holding_a_key_does_not_duplicate_it(kb):
    for _ in range(5):          # the OS repeats key-down while a key is held
        kb._on_press(CharKey("w"))

    assert kb.poll() == {"keys": ["w"]}


def test_releasing_a_key_that_was_not_pressed_does_not_raise(kb):
    kb._on_release(CharKey("x"))

    assert kb.poll() == {"keys": []}


def test_shift_does_not_create_a_second_key(kb):
    kb._on_press(CharKey("w"))
    kb._on_press(CharKey("W"))      # same key with Shift held

    assert kb.poll() == {"keys": ["w"]}


def test_poll_returns_a_copy(kb):
    kb._on_press(CharKey("w"))

    kb.poll()["keys"].append("hacked")

    assert kb.poll() == {"keys": ["w"]}


def test_close_stops_the_listener(kb):
    kb.close()

    assert kb._listener.stopped
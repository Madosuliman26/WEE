import logging
import threading

from pynput import keyboard

from gcs.input.base import InputDevice

log = logging.getLogger(__name__)


def key_name(key):
    """Turn a pynput key into a plain lowercase string like 'w' or 'space'."""
    char = getattr(key, "char", None)
    if char is not None:
        return char.lower()
    name = getattr(key, "name", None)
    if name is not None:
        return name
    return str(key)


class KeyboardInput(InputDevice):
    def __init__(self):
        self._pressed = set()
        self._lock = threading.Lock()
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        log.info("keyboard listener started")

    @property
    def name(self):
        return "keyboard"

    def _on_press(self, key):
        with self._lock:
            self._pressed.add(key_name(key))

    def _on_release(self, key):
        with self._lock:
            self._pressed.discard(key_name(key))

    def poll(self):
        with self._lock:
            keys = sorted(self._pressed)
        return {"keys": keys}

    def close(self):
        self._listener.stop()
        log.info("keyboard listener stopped")



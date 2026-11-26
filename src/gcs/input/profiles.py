import copy
import json
import logging
import os
import threading
from pathlib import Path

from gcs.core.events import ControllerConnected, ProfileChanged

log = logging.getLogger(__name__)

EMPTY_MAPPING = {"buttons": {}, "axes": {}, "keys": {}, "invert": []}


class ProfileManager:
    def __init__(self, path, bus=None):
        self._path = Path(path)
        self._bus = bus
        self._lock = threading.Lock()
        self._profiles = {}
        self._controller_map = {}
        self._default = None
        self._active_name = None
        self._active = EMPTY_MAPPING
        self._mtime = None
        if bus is not None:
            bus.subscribe(ControllerConnected, self._on_controller_connected)

    @property
    def active_name(self):
        return self._active_name

    def _file_mtime(self):
        try:
            return self._path.stat().st_mtime
        except OSError:
            return None

    def load(self, reason="load"):
        self._mtime = self._file_mtime()
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            log.warning("profiles file not found: %s", self._path)
            return
        except json.JSONDecodeError:
            log.error("profiles file is not valid JSON, keeping the old profiles: %s", self._path)
            return

        profiles = data.get("profiles", {})
        with self._lock:
            self._profiles = profiles
            self._controller_map = data.get("controller_map", {})
            self._default = data.get("default_profile")

        wanted = self._active_name if self._active_name in profiles else self._default
        if wanted is not None:
            self.set_active(wanted, reason=reason)
        log.info("loaded %d profiles from %s", len(profiles), self._path)

    def save(self):
        """Write all profiles to the file. Returns True if it worked."""
        with self._lock:
            data = {
                "default_profile": self._default,
                "controller_map": dict(self._controller_map),
                "profiles": copy.deepcopy(self._profiles),
            }
        temp = self._path.with_name(self._path.name + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp, self._path)
        except (OSError, TypeError, ValueError):
            log.exception("could not save profiles to %s", self._path)
            try:
                temp.unlink()
            except OSError:
                pass
            return False
        self._mtime = self._file_mtime()
        log.info("saved %d profiles to %s", len(data["profiles"]), self._path)
        return True

    def update_profile(self, name, mapping):
        """Add or replace a profile in memory. Call save() to write it to the file."""
        if not isinstance(mapping, dict):
            raise ValueError("a profile mapping must be a dict")
        with self._lock:
            self._profiles[name] = copy.deepcopy(mapping)
            is_active = name == self._active_name
        if is_active:
            self.set_active(name, reason="edited")

    def check_for_changes(self):
        """Reload the file if it was saved since the last load. Returns True if it did."""
        mtime = self._file_mtime()
        if mtime is None or mtime == self._mtime:
            return False
        log.info("profiles file changed, reloading")
        self.load(reason="file_edit")
        return True

    def set_active(self, name, reason="manual"):
        with self._lock:
            profile = self._profiles.get(name)
            if profile is None:
                log.warning("unknown profile: %s", name)
                return False
            self._active = {**EMPTY_MAPPING, **profile}
            self._active_name = name
        log.info("active profile: %s (%s)", name, reason)
        if self._bus is not None:
                        self._bus.publish(ProfileChanged(name, reason))
        return True

    def get_mapping(self):
        with self._lock:
            return self._active

    def profile_for_controller(self, controller_name):
        with self._lock:
            return self._controller_map.get(controller_name, self._default)

    def _on_controller_connected(self, event):
        name = self.profile_for_controller(event.name)
        if name is None:
            log.warning("no profile for controller %s", event.name)
            return
        self.set_active(name, reason="auto")


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)
    profiles = ProfileManager("config/profiles.json")
    profiles.load()
    print("edit and save config/profiles.json now (20 seconds)")
    for _ in range(40):
        profiles.check_for_changes()
        time.sleep(0.5)
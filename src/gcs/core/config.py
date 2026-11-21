import json
import logging
import threading
from pathlib import Path

log = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, path):
        self._path = Path(path)
        self._data = {}
        self._lock = threading.Lock()

    def reload(self):
        self.load()

    def load(self):
        try:
            with open(self._path) as f:
                new_data = json.load(f)
        except FileNotFoundError:
            log.warning("config file not found: %s", self._path)
            return
        except json.JSONDecodeError:
            log.error("config file is not valid JSON: %s", self._path)
            return
        with self._lock:
            self._data = new_data
        log.info("config loaded from %s", self._path)


    def get(self, key, default=None):
        with self._lock:
            value = self._data
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

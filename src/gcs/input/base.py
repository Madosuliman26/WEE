from abc import ABC, abstractmethod


class InputDevice(ABC):
    """Anything that can be read every tick: a controller, a keyboard."""

    @property
    @abstractmethod
    def name(self):
        """A short label for logs, e.g. 'controller' or 'keyboard'."""

    @abstractmethod
    def poll(self):
        """Return the current state as a dict, or None if nothing is available."""

    @abstractmethod
    def close(self):
        """Release the device. Called once at shutdown."""
import logging
import time

import pyglet
from pyglet.input.base import Joystick
from pyglet.libs.win32 import dinput

from gcs.input.base import InputDevice
from gcs.input.labels import GENERIC_TABLE, table_for

log = logging.getLogger(__name__)

RESCAN_SECONDS = 1.0
GAMEPAD_TYPES = (
    dinput.DI8DEVTYPE_JOYSTICK,
    dinput.DI8DEVTYPE_1STPERSON,
    dinput.DI8DEVTYPE_GAMEPAD,
    dinput.DI8DEVTYPE_SUPPLEMENTAL,
)


def axis_to_direction(value, deadzone):
    """Turn an analogue axis into -1, 0 or 1. Inside the dead-zone it is 0."""
    if not 0 <= deadzone < 1:
        raise ValueError("deadzone must be at least 0 and less than 1")
    if value > deadzone:
        return 1
    if value < -deadzone:
        return -1
    return 0


class ControllerInput(InputDevice):
    def __init__(self, deadzone=0.5):
        self._deadzone = deadzone
        self._joystick = None
        self._device_name = None
        self._table = GENERIC_TABLE
        self._last_scan = 0.0
        self._loop = pyglet.app.platform_event_loop
        self._loop.start()
        self._scan(force=True)

    @property
    def name(self):
        return "controller"

    @property
    def connected(self):
        return self._joystick is not None

    @property
    def controller_name(self):
        return self._device_name

    @staticmethod
    def _attached_gamepads():
        """A fresh list of the gamepads/joysticks attached right now."""
        return [
            device
            for device in pyglet.input.get_devices()
            if getattr(device, "_type", None) in GAMEPAD_TYPES
        ]

    def _scan(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_scan < RESCAN_SECONDS:
            return
        self._last_scan = now
        try:
            gamepads = self._attached_gamepads()
        except Exception:
            log.exception("scanning for controllers failed")
            return
        log.debug("attached controllers: %s", [device.name for device in gamepads])

        if self._joystick is not None:
            if self._device_name not in [device.name for device in gamepads]:
                self._disconnect("it is no longer attached")
        elif gamepads:
            self._connect(Joystick(gamepads[0]))

    def _connect(self, joystick):
        try:
            joystick.open()
        except Exception:
            log.exception("could not open controller %s", joystick.device.name)
            return
        self._joystick = joystick
        self._device_name = joystick.device.name
        self._table = table_for(self._device_name)
        log.info("controller connected: %s", self._device_name)

    def _disconnect(self, reason):
        log.warning("controller disconnected: %s (%s)", self._device_name, reason)
        try:
            self._joystick.close()
        except Exception:
            log.debug("closing the old controller failed", exc_info=True)
        self._joystick = None
        self._device_name = None

    def poll(self):
        pyglet.clock.tick()
        self._loop.step(0.001)
        self._scan()
        if self._joystick is None:
            return None
        try:
            return self._read()
        except Exception:
            log.exception("reading the controller failed")
            self._disconnect("reading it raised an error")
            return None

    def _read(self):
        joystick = self._joystick
        button_names = self._table["buttons"]
        pressed = [
            button_names.get(index, f"button{index}")
            for index, down in enumerate(joystick.buttons)
            if down
        ]
        if joystick.hat_y > 0:
            pressed.append("dpup")
        elif joystick.hat_y < 0:
            pressed.append("dpdown")
        if joystick.hat_x < 0:
            pressed.append("dpleft")
        elif joystick.hat_x > 0:
            pressed.append("dpright")

        axes = {
            stick: axis_to_direction(getattr(joystick, axis), self._deadzone)
            for stick, axis in self._table["axes"].items()
        }
        return {"buttons": pressed, "axes": axes}

    def close(self):
        if self._joystick is not None:
            self._disconnect("shutting down")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    controller = ControllerInput(deadzone=0.5)
    print("press buttons, unplug and replug the pad (40 seconds)")
    for _ in range(400):
        print(controller.poll(), "          ", end="\r")
        time.sleep(0.1)
    print()
    controller.close()
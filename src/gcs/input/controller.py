import logging

import pyglet

from gcs.input.base import InputDevice
from gcs.input.labels import GENERIC_TABLE, table_for

log = logging.getLogger(__name__)


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
        self._table = GENERIC_TABLE
        self._loop = pyglet.app.platform_event_loop
        self._loop.start()
        self._open_first_joystick()

    @property
    def name(self):
        return "controller"

    def _open_first_joystick(self):
        joysticks = pyglet.input.get_joysticks()
        if not joysticks:
            log.warning("no controller found")
            return
        joystick = joysticks[0]
        joystick.open()
        self._joystick = joystick
        self._table = table_for(joystick.device.name)
        log.info("controller connected: %s", joystick.device.name)

    def poll(self):
        if self._joystick is None:
            return None
        pyglet.clock.tick()
        self._loop.step(0.001)
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
            self._joystick.close()
            self._joystick = None


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)
    controller = ControllerInput(deadzone=0.5)
    print("press buttons and move sticks for 15 seconds")
    for _ in range(150):
        print(controller.poll(), "          ", end="\r")
        time.sleep(0.1)
    print()
    controller.close()
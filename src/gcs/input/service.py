import logging
import threading
import time

from gcs.core.events import (
    AxesChanged,
    ButtonPressed,
    ButtonReleased,
    KeyDown,
    KeyUp,
)

log = logging.getLogger(__name__)


class InputService:
    def __init__(self, devices, bus, rate_hz=50):
        if rate_hz <= 0:
            raise ValueError("rate_hz must be greater than 0")
        self._devices = devices
        self._bus = bus
        self._rate_hz = rate_hz
        self._period = 1.0 / rate_hz
        self._stop = threading.Event()
        self._thread = None
        self._last_buttons = set()
        self._last_axes = {}
        self._last_keys = set()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="input", daemon=True)
        self._thread.start()
        log.info("input service started at %s Hz", self._rate_hz)

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        log.info("input service stopped")

    def _run(self):
        next_tick = time.perf_counter()
        while not self._stop.is_set():
            self._tick()
            next_tick += self._period
            delay = next_tick - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                next_tick = time.perf_counter()

    def _tick(self):
        for device in self._devices:
            try:
                state = device.poll()
            except Exception:
                log.exception("polling %s failed", device.name)
                continue
            if device.name == "controller":
                self._handle_controller(state)
            elif device.name == "keyboard":
                self._handle_keyboard(state)

    def _handle_controller(self, state):
        buttons = set(state["buttons"]) if state else set()
        axes = state["axes"] if state else {}

        for button in sorted(buttons - self._last_buttons):
            self._bus.publish(ButtonPressed(button))
        for button in sorted(self._last_buttons - buttons):
            self._bus.publish(ButtonReleased(button))
        if axes != self._last_axes:
            self._bus.publish(AxesChanged(axes))

        self._last_buttons = buttons
        self._last_axes = axes

    def _handle_keyboard(self, state):
        keys = set(state["keys"]) if state else set()

        for key in sorted(keys - self._last_keys):
            self._bus.publish(KeyDown(key))
        for key in sorted(self._last_keys - keys):
            self._bus.publish(KeyUp(key))

        self._last_keys = keys


if __name__ == "__main__":
    from gcs.core.event_bus import EventBus
    from gcs.input.controller import ControllerInput
    from gcs.input.keyboard import KeyboardInput

    logging.basicConfig(level=logging.INFO)

    bus = EventBus()
    for event_type in (ButtonPressed, ButtonReleased, AxesChanged, KeyDown, KeyUp):
        bus.subscribe(event_type, lambda event: print(type(event).__name__, vars(event)))
    bus.start()

    devices = [ControllerInput(deadzone=0.5), KeyboardInput()]
    service = InputService(devices, bus, rate_hz=50)
    service.start()

    print("press keys and buttons, move sticks - 15 seconds")
    time.sleep(15)

    service.stop()
    for device in devices:
        device.close()
    bus.stop()
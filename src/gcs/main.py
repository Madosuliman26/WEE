import logging
import signal
import threading

from gcs.core.config import ConfigManager
from gcs.core.event_bus import EventBus
from gcs.core.events import (
    AxesChanged,
    ButtonPressed,
    ButtonReleased,
    KeyDown,
    KeyUp,
)
from gcs.core.logging_setup import setup_logging
from gcs.input.controller import ControllerInput
from gcs.input.keyboard import KeyboardInput
from gcs.input.service import InputService

log = logging.getLogger(__name__)


def on_button_pressed(event):
    log.info("button %s is pressed", event.button)


def on_button_released(event):
    log.info("button %s is released", event.button)


def on_key_down(event):
    log.info("key %s is down", event.key)


def on_key_up(event):
    log.info("key %s is up", event.key)


def on_axes_changed(event):
    active = {name: value for name, value in event.axes.items() if value != 0}
    log.info("axes: %s", active if active else "centered")


def main():
    config = ConfigManager("config/settings.json")
    config.load()
    setup_logging(
        level=config.get("logging.level", "INFO"),
        log_file=config.get("logging.file", "logs/gcs.log"),
        max_bytes=config.get("logging.max_bytes", 1_000_000),
        backup_count=config.get("logging.backup_count", 3),
    )
    log.info("starting")

    stop_event = threading.Event()
    signal.signal(signal.SIGINT, lambda signum, frame: stop_event.set())

    bus = EventBus(queue_size=config.get("bus.queue_size", 1000))
    bus.subscribe(ButtonPressed, on_button_pressed)
    bus.subscribe(ButtonReleased, on_button_released)
    bus.subscribe(KeyDown, on_key_down)
    bus.subscribe(KeyUp, on_key_up)
    bus.subscribe(AxesChanged, on_axes_changed)
    bus.start()

    devices = [
        ControllerInput(deadzone=config.get("input.default_deadzone", 0.5)),
        KeyboardInput(),
    ]
    service = InputService(devices, bus, rate_hz=config.get("input.rate_hz", 50))
    service.start()

    log.info("running - press Ctrl+C to stop")
    try:
        while not stop_event.is_set():
            stop_event.wait(0.5)
    finally:
        log.info("shutting down")
        service.stop()
        for device in devices:
            device.close()
        bus.stop()
        log.info("stopped")


if __name__ == "__main__":
    main()
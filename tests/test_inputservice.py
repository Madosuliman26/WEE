import logging
import threading
import time

import pytest

from gcs.core.event_bus import EventBus
from gcs.core.events import (
    AxesChanged,
    ButtonPressed,
    ButtonReleased,
    KeyDown,
    KeyUp,
    Shutdown,
)
from gcs.input.base import InputDevice
from gcs.input.service import InputService


# ---------- helpers ----------

class FakeDevice(InputDevice):
    """A device with no hardware: poll() returns whatever `state` is set to."""

    def __init__(self, name, state=None):
        self._name = name
        self.state = state
        self.polls = 0

    @property
    def name(self):
        return self._name

    def poll(self):
        self.polls += 1
        return self.state

    def close(self):
        pass


class RaisingDevice(InputDevice):
    @property
    def name(self):
        return "controller"

    def poll(self):
        raise RuntimeError("device broke")

    def close(self):
        pass


def wait_until(condition, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def flush(bus):
    """Block until everything published so far has been delivered."""
    done = threading.Event()
    bus.subscribe(Shutdown, lambda event: done.set())
    bus.publish(Shutdown())
    assert done.wait(2.0), "bus did not deliver the flush event"


def pad_state(buttons=(), axes=None):
    return {"buttons": list(buttons), "axes": axes or {}}


@pytest.fixture
def bus():
    b = EventBus()
    b.start()
    yield b
    b.stop()


@pytest.fixture
def events(bus):
    received = []
    for event_type in (ButtonPressed, ButtonReleased, AxesChanged, KeyDown, KeyUp):
        bus.subscribe(event_type, received.append)
    return received


@pytest.fixture
def run(bus):
    """Start a service on the given devices, and stop it after the test."""
    services = []

    def _run(devices, rate_hz=100):
        service = InputService(devices, bus, rate_hz=rate_hz)
        service.start()
        services.append(service)
        return service

    yield _run
    for service in services:
        service.stop()


def of_type(events, event_type):
    return [e for e in events if isinstance(e, event_type)]


# ---------- buttons ----------

def test_button_press_and_release_publish_events(run, events, bus):
    pad = FakeDevice("controller", pad_state())
    run([pad])

    pad.state = pad_state(["cross"])
    assert wait_until(lambda: of_type(events, ButtonPressed))
    pad.state = pad_state()
    assert wait_until(lambda: of_type(events, ButtonReleased))

    assert [e.button for e in of_type(events, ButtonPressed)] == ["cross"]
    assert [e.button for e in of_type(events, ButtonReleased)] == ["cross"]


def test_held_button_publishes_only_one_press(run, events, bus):
    pad = FakeDevice("controller", pad_state(["cross"]))
    run([pad])

    assert wait_until(lambda: of_type(events, ButtonPressed))
    ticks_so_far = pad.polls
    assert wait_until(lambda: pad.polls >= ticks_so_far + 10)
    flush(bus)

    assert len(of_type(events, ButtonPressed)) == 1


def test_disconnected_controller_releases_held_buttons(run, events):
    pad = FakeDevice("controller", pad_state(["cross"]))
    run([pad])
    assert wait_until(lambda: of_type(events, ButtonPressed))

    pad.state = None      # controller unplugged: poll() returns None

    assert wait_until(lambda: of_type(events, ButtonReleased))
    assert of_type(events, ButtonReleased)[0].button == "cross"


# ---------- axes ----------

def test_axes_change_publishes_one_event(run, events, bus):
    pad = FakeDevice("controller", pad_state())
    run([pad])

    pad.state = pad_state(axes={"rightx": 1})
    assert wait_until(lambda: of_type(events, AxesChanged))
    ticks_so_far = pad.polls
    assert wait_until(lambda: pad.polls >= ticks_so_far + 10)
    flush(bus)

    changes = of_type(events, AxesChanged)
    assert len(changes) == 1
    assert changes[0].axes == {"rightx": 1}


# ---------- keyboard ----------

def test_key_down_and_up_publish_events(run, events):
    keyboard = FakeDevice("keyboard", {"keys": []})
    run([keyboard])

    keyboard.state = {"keys": ["w"]}
    assert wait_until(lambda: of_type(events, KeyDown))
    keyboard.state = {"keys": []}
    assert wait_until(lambda: of_type(events, KeyUp))

    assert [e.key for e in of_type(events, KeyDown)] == ["w"]
    assert [e.key for e in of_type(events, KeyUp)] == ["w"]


# ---------- resilience ----------

def test_failing_device_does_not_stop_the_others(run, events, caplog):
    keyboard = FakeDevice("keyboard", {"keys": []})

    with caplog.at_level(logging.ERROR):
        run([RaisingDevice(), keyboard])
        keyboard.state = {"keys": ["w"]}
        assert wait_until(lambda: of_type(events, KeyDown))

    assert "polling controller failed" in caplog.text


# ---------- rate ----------

def test_rate_is_close_to_the_configured_rate(bus):
    pad = FakeDevice("controller", pad_state())
    service = InputService([pad], bus, rate_hz=50)

    service.start()
    time.sleep(1.0)
    service.stop()

    assert 40 <= pad.polls <= 60


def test_slow_subscriber_does_not_slow_sampling(bus):
    class FlippingDevice(FakeDevice):
        """Changes its axes on every poll, so every tick publishes an event."""

        def poll(self):
            self.polls += 1
            return pad_state(axes={"rightx": self.polls % 2})

    bus.subscribe(AxesChanged, lambda event: time.sleep(0.05))
    pad = FlippingDevice("controller")
    service = InputService([pad], bus, rate_hz=50)

    service.start()
    time.sleep(1.0)
    service.stop()

    assert pad.polls >= 40


# ---------- lifecycle ----------

def test_stop_ends_the_thread(bus):
    service = InputService([FakeDevice("controller", pad_state())], bus)
    service.start()

    service.stop()

    assert not service._thread.is_alive()


def test_start_twice_does_not_create_a_second_thread(bus):
    service = InputService([FakeDevice("controller", pad_state())], bus)
    service.start()
    first_thread = service._thread

    service.start()

    assert service._thread is first_thread
    service.stop()


def test_stop_before_start_does_not_crash(bus):
    InputService([], bus).stop()


@pytest.mark.parametrize("bad_rate", [0, -5])
def test_invalid_rate_raises(bus, bad_rate):
    with pytest.raises(ValueError):
        InputService([], bus, rate_hz=bad_rate)
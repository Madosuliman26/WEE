import logging
import threading
import time
from dataclasses import dataclass

import pytest

from gcs.core.event_bus import EventBus


# ---------- small events used only by these tests ----------

@dataclass
class Ping:
    value: int


@dataclass
class Other:
    value: int


@dataclass
class Flush:
    pass


# ---------- helpers ----------

def wait_until(condition, timeout=2.0):
    """Check `condition` every 10 ms until it is True or the timeout passes."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def flush(bus):
    """Block until everything published so far has been delivered."""
    done = threading.Event()
    bus.subscribe(Flush, lambda event: done.set())
    bus.publish(Flush())
    assert done.wait(2.0), "bus did not deliver the flush event"


@pytest.fixture
def bus():
    b = EventBus()
    b.start()
    yield b
    b.stop()


# ---------- delivery ----------

def test_subscriber_receives_published_event(bus):
    received = []
    bus.subscribe(Ping, received.append)

    bus.publish(Ping(1))

    assert wait_until(lambda: received == [Ping(1)])


def test_two_subscribers_both_receive(bus):
    first, second = [], []
    bus.subscribe(Ping, first.append)
    bus.subscribe(Ping, second.append)

    bus.publish(Ping(1))

    assert wait_until(lambda: first == [Ping(1)] and second == [Ping(1)])


def test_other_event_type_is_not_delivered(bus):
    received = []
    bus.subscribe(Ping, received.append)

    bus.publish(Other(1))
    flush(bus)

    assert received == []


def test_publish_without_subscribers_does_not_raise(bus):
    bus.publish(Other(1))
    flush(bus)


def test_events_arrive_in_publish_order(bus):
    received = []
    bus.subscribe(Ping, received.append)

    for i in range(50):
        bus.publish(Ping(i))

    assert wait_until(lambda: len(received) == 50)
    assert received == [Ping(i) for i in range(50)]


# ---------- unsubscribe ----------

def test_unsubscribe_stops_delivery(bus):
    received = []
    bus.subscribe(Ping, received.append)
    bus.unsubscribe(Ping, received.append)

    bus.publish(Ping(1))
    flush(bus)

    assert received == []


def test_unsubscribe_unknown_callback_does_not_raise():
    bus = EventBus()
    bus.unsubscribe(Ping, print)   # never subscribed, must be harmless
    bus.unsubscribe(Ping, print)


# ---------- resilience ----------

def test_bad_subscriber_does_not_stop_others(bus, caplog):
    good = []

    def bad(event):
        raise ValueError("boom")

    bus.subscribe(Ping, bad)
    bus.subscribe(Ping, good.append)

    with caplog.at_level(logging.ERROR):
        bus.publish(Ping(1))
        assert wait_until(lambda: good == [Ping(1)])

    assert "subscriber failed" in caplog.text


def test_full_queue_drops_event_and_warns(caplog):
    bus = EventBus(queue_size=2)      # not started, so nothing drains the queue

    with caplog.at_level(logging.WARNING):
        bus.publish(Ping(1))
        bus.publish(Ping(2))
        bus.publish(Ping(3))          # queue is full: must not block or raise

    assert "dropped event" in caplog.text


# ---------- threads ----------

def test_three_threads_publish_without_loss(bus):
    received = []
    bus.subscribe(Ping, received.append)

    def worker(n):
        for i in range(100):
            bus.publish(Ping(n * 1000 + i))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert wait_until(lambda: len(received) == 300)


def test_stop_ends_the_thread():
    bus = EventBus()
    bus.start()

    bus.stop()

    assert not bus._thread.is_alive()


def test_stop_before_start_does_not_crash():
    EventBus().stop()
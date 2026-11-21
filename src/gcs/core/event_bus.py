import logging
import queue
import threading

log = logging.getLogger(__name__)

class EventBus:
    def __init__(self,queue_size=1000):
        self.subscribers={}
        self._queue = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def subscribe(self, event_type, callback):
        with self._lock:
            self.subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type, callback):
        with self._lock:
            callbacks = self.subscribers.get(event_type, [])
            if callback in callbacks:
                callbacks.remove(callback)

    def publish(self, event):
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            log.warning("bus queue full, dropped event %s", type(event).__name__)

    def start(self):
        self._thread = threading.Thread(target=self._run, name="bus", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._lock:
                callbacks = list(self.subscribers.get(type(event), []))
            for callback in callbacks:
                try:
                    callback(event)
                except Exception:
                    log.exception("subscriber failed for %s", type(event).__name__)
                    